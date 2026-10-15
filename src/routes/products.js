import {Router} from 'express';
import {z} from 'zod';
import {pool,transaction,fail} from '../db.js';
import {requireAuth,permit} from '../middleware/auth.js';
import {BASE,baseQty,D,F} from '../services/math.js';
import {loadCostModel} from '../services/costing.js';
export const products=Router();products.use(requireAuth);
const wrap=f=>(req,res,next)=>Promise.resolve(f(req,res,next)).catch(next);
const productSchema=z.object({
 name:z.string().trim().min(2).max(180),
 types:z.array(z.enum(['Produto Acabado','Revenda','Embalagem','Uso e Consumo','Subproduto','Insumo'])).min(1),
 purchaseUnit:z.string().trim().min(1).max(15),
 packageQty:z.coerce.number().positive(),
 packageUnit:z.enum(['mg','g','kg','ml','l','un']),
 purchasePrice:z.coerce.number().min(0),
 fc:z.coerce.number().min(1).default(1),
 minStock:z.coerce.number().min(0).default(0),
 practicedPrice:z.union([z.null(),z.coerce.number().min(0)]).optional().default(null),
 testGross:z.union([z.coerce.number().positive(),z.null()]).optional().default(null),
 testNet:z.union([z.coerce.number().positive(),z.null()]).optional().default(null)
});
function valid(body){const p=productSchema.safeParse(body);if(!p.success)throw fail(422,p.error.issues.map(i=>i.message).join('; '));if(BASE[p.data.packageUnit]==='un' && p.data.fc!==1)throw fail(422,'Fator de correção não suportado para unidades; use FC=1.');
 if((p.data.testGross==null)!==(p.data.testNet==null))throw fail(422,'Informe peso bruto e líquido juntos.');
 if(p.data.testGross!=null){if(p.data.testGross<p.data.testNet)throw fail(422,'Peso líquido não pode superar peso bruto.');if(Math.abs(p.data.fc-p.data.testGross/p.data.testNet)>0.00001)throw fail(422,'FC deve corresponder a PB/PL no teste de rendimento.');}
 return p.data;}
products.get('/',wrap(async(req,res)=>{
 const [{rows},model]=await Promise.all([pool.query('SELECT * FROM products WHERE active=true ORDER BY name,id'),loadCostModel(pool)]);
 res.json(rows.map(p=>{let calculatedCost;try{calculatedCost=F(model.realCost(p.id),6);}catch{calculatedCost=null;}
 return {...p,costBase:F(D(p.purchase_price).div(baseQty(p.package_qty,p.package_unit)),6),theoreticalCost:calculatedCost,lowStock:D(p.min_stock).gt(0)&&D(p.stock).lt(p.min_stock)};}));
}));
products.post('/',permit('admin','operator'),wrap(async(req,res)=>{
 const p=valid(req.body),b=BASE[p.packageUnit];
 const {rows}=await pool.query(`INSERT INTO products(name,types,purchase_unit,package_qty,package_unit,base_unit,purchase_price,fc,min_stock,practiced_price,test_gross,test_net,last_cost_at)
 VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,now()) RETURNING *`,[p.name,[...new Set(p.types)],p.purchaseUnit,p.packageQty,p.packageUnit,b,p.purchasePrice,p.fc,p.minStock,p.practicedPrice,p.testGross,p.testNet]);res.status(201).json(rows[0]);
}));
products.put('/:id',permit('admin','operator'),wrap(async(req,res)=>{
 const p=valid(req.body);const id=req.params.id;
 const updated=await transaction(async c=>{
 const ex=(await c.query('SELECT * FROM products WHERE id=$1 AND active=true FOR UPDATE',[id])).rows[0];if(!ex)throw fail(404,'Produto não encontrado.');
 if(ex.base_unit!==BASE[p.packageUnit]){
  const refs=await c.query(`SELECT
  EXISTS(SELECT 1 FROM stock_movements WHERE product_id=$1) OR EXISTS(SELECT 1 FROM recipe_items WHERE product_id=$1) OR EXISTS(SELECT 1 FROM recipes WHERE product_id=$1) AS locked`,[id]);
  if(refs.rows[0].locked)throw fail(422,'Não é possível alterar a dimensão (kg/L/un) de um produto com histórico ou fichas vinculadas.');
 }
 if(ex.base_unit==='un' && p.fc!==1)throw fail(422,'Fator de correção para unidades exige definição técnica específica; use FC=1.');
 const result=await c.query(`UPDATE products SET name=$2,types=$3,purchase_unit=$4,package_qty=$5,package_unit=$6,base_unit=$7,purchase_price=$8,fc=$9,min_stock=$10,practiced_price=$11,test_gross=$12,test_net=$13,updated_at=now(),last_cost_at=CASE WHEN purchase_price<>$8 THEN now() ELSE last_cost_at END WHERE id=$1 RETURNING *`,[id,p.name,[...new Set(p.types)],p.purchaseUnit,p.packageQty,p.packageUnit,BASE[p.packageUnit],p.purchasePrice,p.fc,p.minStock,p.practicedPrice,p.testGross,p.testNet]);return result.rows[0];
 });res.json(updated);
}));
products.delete('/:id',permit('admin'),wrap(async(req,res)=>{
 const id=req.params.id;await transaction(async c=>{
  const p=(await c.query('SELECT * FROM products WHERE id=$1 FOR UPDATE',[id])).rows[0];if(!p)throw fail(404,'Produto não encontrado.');
  if(D(p.stock).gt(0))throw fail(422,'Zere o saldo por ajuste justificado antes de arquivar o produto.');
  const refs=await c.query('SELECT EXISTS(SELECT 1 FROM recipe_items WHERE product_id=$1) OR EXISTS(SELECT 1 FROM recipes WHERE product_id=$1) AS used',[id]);
  if(refs.rows[0].used)throw fail(422,'Produto vinculado a ficha técnica. Remova o vínculo primeiro.');
  await c.query('UPDATE products SET active=false,updated_at=now() WHERE id=$1',[id]);
 });res.json({message:'Produto arquivado, com histórico preservado.'});
}));
