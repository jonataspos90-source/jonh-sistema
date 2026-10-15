import {Router} from 'express';
import crypto from 'node:crypto';
import {z} from 'zod';
import {pool,transaction,fail} from '../db.js';
import {requireAuth,permit} from '../middleware/auth.js';
import {D,F,baseQty,averageCost,purchaseBaseCost} from '../services/math.js';
import {loadCostModel} from '../services/costing.js';
export const stock=Router();stock.use(requireAuth);
const wrap=fn=>(req,res,next)=>Promise.resolve(fn(req,res,next)).catch(next);
const id=z.coerce.number().int().positive(),positive=z.coerce.number().min(0.000001);
const receipt=z.object({productId:id,packages:positive,purchasePrice:z.coerce.number().min(0),reason:z.string().max(300).optional()});
const sale=z.object({productId:id,quantity:positive,unitPrice:z.coerce.number().min(0).optional(),type:z.enum(['sale','internal']).default('sale'),reason:z.string().trim().max(500).optional()});
const adjust=z.object({productId:id,delta:z.coerce.number().refine(n=>Math.abs(n)>=0.000001,'Variação mínima: 0,000001'),reason:z.string().trim().min(5).max(500),kind:z.enum(['adjust','loss']).default('adjust')});
const production=z.object({productId:id,outputQty:positive,reason:z.string().trim().max(500).optional()});
function valid(schema,body){const r=schema.safeParse(body);if(!r.success)throw fail(422,r.error.issues.map(i=>i.message).join('; '));return r.data;}
async function lockProducts(c,ids){
 const unique=[...new Set(ids.map(Number))].sort((a,b)=>a-b);
 const {rows}=await c.query('SELECT * FROM products WHERE id=ANY($1::bigint[]) AND active=true ORDER BY id FOR UPDATE',[unique]);
 if(rows.length!==unique.length)throw fail(422,'Produto inativo ou não cadastrado.');
 return new Map(rows.map(p=>[Number(p.id),p]));
}
async function record(c,{product,delta,kind,unitCost,userId,batchId,reason,newAvg}){
 const before=D(product.stock),after=before.plus(delta);
 if(after.lt(0))throw fail(422,`Estoque insuficiente de ${product.name}: disponível ${F(before)}, necessário ${F(D(delta).abs())} ${product.base_unit}.`);
 const price=newAvg===undefined?D(product.avg_cost):D(newAvg);
 // Preços/quantidades são valores numéricos no SQL; não confiar em mudanças do navegador.
 await c.query('UPDATE products SET stock=$2,avg_cost=$3,updated_at=now() WHERE id=$1',[product.id,F(after),F(price,8)]);
 const result=await c.query(`INSERT INTO stock_movements(batch_id,product_id,kind,delta,before_qty,after_qty,unit_cost,value_amount,actor_id,reason)
 VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9,$10) RETURNING *`,[batchId,product.id,kind,F(delta),F(before),F(after),F(unitCost,8),F(D(delta).abs().mul(unitCost)),userId,reason||null]);
 product.stock=F(after);product.avg_cost=F(price,8);
 return result.rows[0];
}
async function actualUnitCost(c,p){
 if(D(p.avg_cost).gt(0))return D(p.avg_cost);
 const packCost=purchaseBaseCost(p.purchase_price,p.package_qty,p.package_unit);
 if(packCost.gt(0))return packCost;
 // Ajuste inicial de subproduto/PA sem compra: usa custo teórico da ficha como estimativa.
 const model=await loadCostModel(c);
 const recipe=model.recipeMap.get(String(p.id));
 return recipe?D(model.recipeDetails(recipe).unitCost):packCost;
}
stock.get('/balances',wrap(async(req,res)=>res.json((await pool.query(`SELECT id,name,types,base_unit,stock,avg_cost,min_stock,
 ROUND(stock*avg_cost,2) AS stock_value,stock<min_stock AND min_stock>0 AS low_stock FROM products WHERE active=true ORDER BY name`)).rows)));
stock.get('/movements',wrap(async(req,res)=>{
 const args=[],filters=[];
 if(req.query.productId){args.push(req.query.productId);filters.push(`m.product_id=$${args.length}`);}
 if(req.query.start){args.push(req.query.start);filters.push(`m.created_at >= $${args.length}::date`);}
 if(req.query.end){args.push(req.query.end);filters.push(`m.created_at < ($${args.length}::date + interval '1 day')`);}
 const where=filters.length?'WHERE '+filters.join(' AND '):'';
 res.json((await pool.query(`SELECT m.*,p.name AS product_name,p.base_unit,u.name AS actor_name FROM stock_movements m JOIN products p ON p.id=m.product_id LEFT JOIN users u ON u.id=m.actor_id ${where} ORDER BY m.created_at DESC,m.id DESC LIMIT 1000`,args)).rows);
}));
stock.post('/purchase',permit('admin','operator'),wrap(async(req,res)=>{
 const p=valid(receipt,req.body),result=await transaction(async c=>{
  const product=(await lockProducts(c,[p.productId])).get(p.productId);
  const incoming=D(F(baseQty(product.package_qty,product.package_unit).mul(p.packages)));
  if(incoming.lte(0))throw fail(422,'Quantidade convertida inferior à precisão de 0,000001.');
  const perBase=D(p.purchasePrice).div(baseQty(product.package_qty,product.package_unit));
  const avg=averageCost(product.stock,product.avg_cost,incoming,perBase);
  const m=await record(c,{product,delta:incoming,kind:'purchase',unitCost:perBase,newAvg:avg,userId:req.user.id,batchId:crypto.randomUUID(),reason:p.reason});
  await c.query('UPDATE products SET purchase_price=$2,last_cost_at=now() WHERE id=$1',[p.productId,p.purchasePrice]);
  return m;
 });res.status(201).json(result);
}));
stock.post('/sale',permit('admin','operator'),wrap(async(req,res)=>{
 const p=valid(sale,req.body),result=await transaction(async c=>{
 const item=(await lockProducts(c,[p.productId])).get(p.productId);
 const cost=await actualUnitCost(c,item),saleQty=D(F(p.quantity)),price=p.unitPrice==null?D(item.practiced_price??0):D(p.unitPrice);
 if(p.type==='sale'&&!item.types.some(t=>['Produto Acabado','Subproduto','Revenda'].includes(t)))throw fail(422,'Venda permitida apenas para acabado, subproduto ou revenda.');
 if(p.type==='sale'&&p.unitPrice==null&&item.practiced_price==null)throw fail(422,'Informe um preço praticado para registrar a venda.');
 if(p.type==='internal'&&!p.reason?.trim())throw fail(422,'Informe o motivo da saída interna.');
 const m=await record(c,{product:item,delta:saleQty.neg(),kind:p.type,unitCost:cost,userId:req.user.id,batchId:crypto.randomUUID(),reason:p.reason});
 if(p.type==='sale')await c.query('INSERT INTO sales(movement_id,product_id,quantity,unit_price,revenue,cost_total,actor_id) VALUES($1,$2,$3,$4,$5,$6,$7)',[m.id,p.productId,F(saleQty),F(price,6),F(price.mul(saleQty)),F(cost.mul(saleQty)),req.user.id]);
 return m;
 });res.status(201).json(result);
}));
stock.post('/adjust',permit('admin','operator'),wrap(async(req,res)=>{
 const p=valid(adjust,req.body);if(p.kind==='loss'&&p.delta>=0)throw fail(422,'Perda / quebra requer variação negativa.');const result=await transaction(async c=>{
 const item=(await lockProducts(c,[p.productId])).get(p.productId);
 const cost=await actualUnitCost(c,item);
 return record(c,{product:item,delta:D(F(p.delta)),kind:p.kind,unitCost:cost,newAvg:D(item.avg_cost).gt(0)?item.avg_cost:cost,userId:req.user.id,batchId:crypto.randomUUID(),reason:p.reason});
 });res.status(201).json(result);
}));
stock.post('/production',permit('admin','operator'),wrap(async(req,res)=>{
 const p=valid(production,req.body),result=await transaction(async c=>{
 const recipe=(await c.query('SELECT * FROM recipes WHERE product_id=$1 AND active=true FOR UPDATE',[p.productId])).rows[0];
 if(!recipe)throw fail(422,'Produto sem ficha técnica ativa.');
 const items=(await c.query('SELECT * FROM recipe_items WHERE recipe_id=$1',[recipe.id])).rows;
 if(!items.length)throw fail(422,'Ficha técnica sem ingredientes.');
 const ids=[p.productId,...items.map(i=>Number(i.product_id))],products=await lockProducts(c,ids);
 const finished=products.get(p.productId);
 const outputQty=D(F(p.outputQty));const multiplier=outputQty.div(recipe.yield_qty);
 const usage=[];
 for(const i of items){
 const ingredient=products.get(Number(i.product_id));
 const gross=D(F(D(i.net_qty).mul(multiplier).mul(ingredient.fc)));
 if(gross.lte(0))throw fail(422,`Quantidade de ${ingredient.name} abaixo da precisão de estoque.`);
 // Insumos em estoque estão na unidade BRUTA de compra; FC aumenta a baixa.
 if(D(ingredient.stock).lt(gross))throw fail(422,`Faltam ${F(gross.minus(ingredient.stock))} ${ingredient.base_unit} de ${ingredient.name}.`);
 usage.push({ingredient,gross,cost:await actualUnitCost(c,ingredient)});
 }
 const batch=crypto.randomUUID();let total=D(0);const movements=[];
 for(const item of usage){
 total=total.plus(item.gross.mul(item.cost));
 movements.push(await record(c,{product:item.ingredient,delta:item.gross.neg(),kind:'production_out',unitCost:item.cost,userId:req.user.id,batchId:batch,reason:`Consumo para ${finished.name}`}));
 }
 const producedCost=total.div(outputQty),avg=averageCost(finished.stock,finished.avg_cost,outputQty,producedCost);
 movements.push(await record(c,{product:finished,delta:outputQty,kind:'production_in',unitCost:producedCost,newAvg:avg,userId:req.user.id,batchId:batch,reason:p.reason||`Produção de ${finished.name}`}));
 return {batchId:batch,productId:p.productId,producedQty:F(outputQty),batchCost:F(total,2),unitCost:F(producedCost,6),movements};
 });res.status(201).json(result);
}));
