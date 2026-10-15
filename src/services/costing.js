import {D, F, purchaseBaseCost, suggestedPrice, contribution} from './math.js';
import {fail} from '../db.js';
const num=x=>D(x);
export function buildCostModel(products,recipes,items){
 const prodMap=new Map(products.map(p=>[String(p.id),p]));
 const recipeMap=new Map(recipes.map(r=>[String(r.product_id),r]));
 const itemMap=new Map();
 for(const item of items){let key=String(item.recipe_id);if(!itemMap.has(key))itemMap.set(key,[]);itemMap.get(key).push(item);}
 function realCost(id,trail=new Set()){
  const p=prodMap.get(String(id));if(!p)throw fail(422,'Produto inexistente na composição: '+id);
  if(trail.has(String(id)))throw fail(422,'Ciclo detectado entre fichas técnicas.');
  const r=recipeMap.get(String(id));
  if(r&&r.active){
   trail.add(String(id));
   try {
    const total=(itemMap.get(String(r.id))||[]).reduce((a,i)=>a.plus(realCost(i.product_id,trail).mul(i.net_qty)),D(0));
    return total.div(r.yield_qty).mul(p.fc);
   } finally {trail.delete(String(id));}
  }
  // Preço teórico de reposição: embalagem cadastrada / última compra.
  // O custo médio histórico é usado exclusivamente na valoração de estoque.
  const registered=purchaseBaseCost(p.purchase_price,p.package_qty,p.package_unit);
  const unitCost=registered.gt(0)?registered:num(p.avg_cost);
  return unitCost.mul(p.fc);
 }
 function recipeDetails(r){
  const p=prodMap.get(String(r.product_id));
  const lines=(itemMap.get(String(r.id))||[]).map(i=>{
   const ingredient=prodMap.get(String(i.product_id));
   if(!ingredient)throw fail(422,'Insumo ausente.');
   const unitCost=realCost(i.product_id,new Set([String(r.product_id)]));
   return {productId:Number(i.product_id),name:ingredient.name,baseUnit:ingredient.base_unit,netQty:F(i.net_qty),fc:F(ingredient.fc),grossQty:F(num(i.net_qty).mul(ingredient.fc)),unitCost:F(unitCost,8),total:F(unitCost.mul(i.net_qty))};
  });
  const total=lines.reduce((a,l)=>a.plus(l.total),D(0));
  const unit=total.div(r.yield_qty);
  const sug=suggestedPrice(unit,r.margin,r.pricing_mode);
  const selling=p.practiced_price==null?sug:num(p.practiced_price);
  const mc=contribution(unit,selling);
  // Margem desejada compara percentuais de contribuição reais, não markup.
  const target=r.pricing_mode==='margin'?num(r.margin):contribution(unit,sug).percentage;
  return {id:Number(r.id),productId:Number(r.product_id),productName:p.name,baseUnit:p.base_unit,yieldQty:F(r.yield_qty),margin:F(r.margin,2),pricingMode:r.pricing_mode,active:r.active,items:lines,totalCost:F(total),unitCost:F(unit,6),suggestedPrice:F(sug,2),practicedPrice:F(selling,2),contributionAmount:F(mc.amount,2),contributionPct:F(mc.percentage,2),targetMargin:F(target,2),belowTarget:mc.percentage.lt(target)};
 }
 return {realCost,recipeDetails,prodMap,recipeMap,itemMap};
}
export async function loadCostModel(c){
 const [p,r,i]=await Promise.all([
  c.query('SELECT * FROM products WHERE active=true'),
  c.query('SELECT * FROM recipes'),
  c.query('SELECT * FROM recipe_items')
 ]);
 return buildCostModel(p.rows,r.rows,i.rows);
}
export function validateRecipeCycle(existingRecipes,items,targetProductId,newItems){
 const edges=new Map();
 for(const r of existingRecipes){edges.set(String(r.product_id),items.filter(i=>String(i.recipe_id)===String(r.id)).map(i=>String(i.product_id)));}
 edges.set(String(targetProductId),newItems.map(i=>String(i.productId)));
 const visiting=new Set(),visited=new Set();
 function walk(id){if(visiting.has(id))throw fail(422,'Dependência circular entre receitas / subprodutos.');if(visited.has(id))return;
  visiting.add(id);for(const next of edges.get(id)||[])walk(next);visiting.delete(id);visited.add(id);
 }
 for(const id of edges.keys())walk(id);
}
