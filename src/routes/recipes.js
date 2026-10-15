import {Router} from 'express';
import {z} from 'zod';
import {pool,transaction,fail} from '../db.js';
import {requireAuth,permit} from '../middleware/auth.js';
import {loadCostModel,validateRecipeCycle} from '../services/costing.js';
export const recipes=Router();recipes.use(requireAuth);
const wrap=f=>(req,res,next)=>Promise.resolve(f(req,res,next)).catch(next);
const schema=z.object({
 productId:z.coerce.number().int().positive(),yieldQty:z.coerce.number().min(0.000001),
 margin:z.coerce.number().min(0).lt(100),pricingMode:z.enum(['margin','markup']).default('margin'),
 items:z.array(z.object({productId:z.coerce.number().int().positive(),netQty:z.coerce.number().min(0.000001)})).min(1)
});
recipes.get('/',wrap(async(req,res)=>{
 const m=await loadCostModel(pool);
 const out=[];for(const r of m.recipeMap.values()){
  try {out.push(m.recipeDetails(r));}catch(e){out.push({id:Number(r.id),productId:Number(r.product_id),error:e.message});}
 }
 res.json(out.sort((a,b)=>(a.productName||'').localeCompare(b.productName||'')));
}));
async function save(req,res){
 const parsed=schema.safeParse(req.body);if(!parsed.success)throw fail(422,parsed.error.issues.map(i=>i.message).join('; '));
 const p=parsed.data;
 if(new Set(p.items.map(i=>i.productId)).size!==p.items.length)throw fail(422,'Ingredientes duplicados; some as quantidades.');
 const output=await transaction(async c=>{
  // Serialize alterações de fichas concorrentes (inclusive edição simultânea).
  await c.query('SELECT pg_advisory_xact_lock(39010958)');
  const ps=(await c.query('SELECT * FROM products WHERE id = ANY($1::bigint[]) AND active=true',[ [p.productId,...p.items.map(i=>i.productId)] ])).rows;
  const selected=ps.find(x=>String(x.id)===String(p.productId));if(!selected)throw fail(422,'Produto final não encontrado.');
  if(!selected.types.some(t=>['Produto Acabado','Subproduto'].includes(t)))throw fail(422,'A ficha técnica exige Produto Acabado ou Subproduto.');
  if(ps.length!==1+p.items.length)throw fail(422,'Há ingredientes inexistentes ou inativos.');
  if(p.items.some(i=>i.productId===p.productId))throw fail(422,'Um produto não pode consumir a si mesmo.');
  const rr=(await c.query('SELECT * FROM recipes')).rows, allItems=(await c.query('SELECT * FROM recipe_items')).rows;
  validateRecipeCycle(rr,allItems,p.productId,p.items);
  const old=rr.find(r=>String(r.product_id)===String(p.productId));
  let r;
  if(old){
   r=(await c.query('UPDATE recipes SET yield_qty=$2,margin=$3,pricing_mode=$4,active=true,updated_at=now() WHERE product_id=$1 RETURNING *',[p.productId,p.yieldQty,p.margin,p.pricingMode])).rows[0];
   await c.query('DELETE FROM recipe_items WHERE recipe_id=$1',[r.id]);
  }else{
   r=(await c.query('INSERT INTO recipes(product_id,yield_qty,margin,pricing_mode) VALUES($1,$2,$3,$4) RETURNING *',[p.productId,p.yieldQty,p.margin,p.pricingMode])).rows[0];
  }
  for(const i of p.items)await c.query('INSERT INTO recipe_items(recipe_id,product_id,net_qty) VALUES($1,$2,$3)',[r.id,i.productId,i.netQty]);
  return r;
 });res.status(200).json({message:'Ficha técnica salva.',id:output.id});
}
recipes.post('/',permit('admin','operator'),wrap(save));
recipes.put('/:productId',permit('admin','operator'),wrap(async(req,res)=>{
 if(String(req.body?.productId)!==req.params.productId)throw fail(422,'Produto da ficha não corresponde ao informado na URL.');
 await save(req,res);
}));
recipes.delete('/:productId',permit('admin'),wrap(async(req,res)=>{
 const {rowCount}=await pool.query('DELETE FROM recipes WHERE product_id=$1',[req.params.productId]);if(!rowCount)throw fail(404,'Ficha não encontrada.');res.json({message:'Ficha excluída. Histórico de produção permanece preservado.'});
}));
