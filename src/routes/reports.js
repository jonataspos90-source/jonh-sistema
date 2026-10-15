import {Router} from 'express';
import {pool} from '../db.js';
import {requireAuth} from '../middleware/auth.js';
import {loadCostModel} from '../services/costing.js';
import {D,F,suggestedPrice} from '../services/math.js';
export const reports=Router();reports.use(requireAuth);
const wrap=f=>(req,res,next)=>Promise.resolve(f(req,res,next)).catch(next);
reports.get('/dashboard',wrap(async(req,res)=>{
 const [products,recipes,stock,alerts,old]=await Promise.all([
  pool.query('SELECT count(*)::int AS n FROM products WHERE active=true'),
  pool.query('SELECT count(*)::int AS n FROM recipes WHERE active=true'),
  pool.query('SELECT COALESCE(sum(stock*avg_cost),0) AS total FROM products WHERE active=true'),
  pool.query('SELECT id,name,stock,min_stock,base_unit FROM products WHERE active=true AND min_stock>0 AND stock<min_stock ORDER BY (min_stock-stock) DESC'),
  pool.query(`SELECT count(*)::int AS n FROM products WHERE active=true AND last_cost_at < now()-interval '30 days' OR active=true AND last_cost_at IS NULL`)
 ]);
 const m=await loadCostModel(pool);
 const r=[...m.recipeMap.values()].map(x=>{try{return m.recipeDetails(x);}catch(e){return {error:e.message};}});
 res.json({totalProducts:products.rows[0].n,totalRecipes:recipes.rows[0].n,stockValue:F(stock.rows[0].total,2),staleCosts:old.rows[0].n,lowStock:alerts.rows,belowMargin:r.filter(x=>x.belowTarget),subproducts:[...m.prodMap.values()].filter(p=>p.types.includes('Subproduto')).length});
}));
reports.get('/margins',wrap(async(req,res)=>{
 const m=await loadCostModel(pool);
 res.json([...m.recipeMap.values()].map(r=>{try{return m.recipeDetails(r);}catch(e){return {productId:r.product_id,error:e.message};}}));
}));
reports.get('/valuation',wrap(async(req,res)=>{
 const items=(await pool.query(`SELECT id,name,types,stock,base_unit,avg_cost,round(stock*avg_cost,2) AS value FROM products WHERE active=true ORDER BY name`)).rows;
 res.json({total:F(items.reduce((a,i)=>a.plus(D(i.stock).mul(i.avg_cost)),D(0)),2),items});
}));
reports.get('/abc',wrap(async(req,res)=>{
 const metric=req.query.metric==='cost'?'cost':'revenue';
 const [s,p]=await Promise.all([
  pool.query(`SELECT product_id,sum(revenue) AS revenue,sum(cost_total) AS cost FROM sales
     WHERE ($1::date IS NULL OR created_at >= $1::date) AND ($2::date IS NULL OR created_at < ($2::date+interval '1 day')) GROUP BY product_id`,[req.query.start||null,req.query.end||null]),
  pool.query('SELECT id,name,stock,avg_cost FROM products')
 ]);
 const sales=new Map(s.rows.map(x=>[String(x.product_id),x]));
 const salesExist=s.rows.some(x=>D(x.revenue).gt(0)||D(x.cost).gt(0));
 // Quando não há vendas no período, reporta ABC por VALOR EM ESTOQUE, sem apresentar como faturamento.
 const fallback=!salesExist;
 const items=p.rows.map(x=>({productId:Number(x.id),name:x.name,value:fallback?D(x.stock).mul(x.avg_cost):D(sales.get(String(x.id))?.[metric]||0)})).filter(x=>x.value.gt(0)).sort((a,b)=>b.value.comparedTo(a.value));
 const total=items.reduce((a,x)=>a.plus(x.value),D(0));let running=D(0);
 const mapped=items.map((x,i)=>{
 const before=running;running=running.plus(x.value);const pct=running.div(total).mul(100);
 // Faixas contínuas por participação do acumulado ANTES de entrar na próxima faixa.
 const klass=before.div(total).mul(100).lt(80)?'A':before.div(total).mul(100).lt(95)?'B':'C';
 return {...x,value:F(x.value,2),share:F(x.value.div(total).mul(100),2),cumulative:F(pct,2),class:klass};
 });res.json({metric:fallback?'inventory':metric,total:F(total,2),items:mapped});
}));
reports.get('/sensitivity',wrap(async(req,res)=>{
 const pct=Math.min(100,Math.max(0,Number(req.query.change||10))),m=await loadCostModel(pool);const data=[];
 for(const r of m.recipeMap.values()){
  try{
   const detail=m.recipeDetails(r),unit=D(detail.unitCost),increased=unit.mul(D(1).plus(D(pct).div(100)));
   const proposed=suggestedPrice(increased,r.margin,r.pricing_mode);
   data.push({productId:detail.productId,name:detail.productName,currentCost:detail.unitCost,costAfter:F(increased,6),priceNow:detail.suggestedPrice,priceAfter:F(proposed,2),changePct:pct});
  }catch(e){data.push({productId:r.product_id,error:e.message});}
 }
 res.json(data);
}));
