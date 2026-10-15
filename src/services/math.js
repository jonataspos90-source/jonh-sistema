import Decimal from 'decimal.js';
export const D=(value)=>new Decimal(value ?? 0);
export const F=(value,scale=6)=>D(value).toDecimalPlaces(scale,Decimal.ROUND_HALF_UP).toFixed(scale);
export const BASE={mg:'kg',g:'kg',kg:'kg',ml:'l',l:'l',un:'un'};
export function baseQty(quantity,unit){
  if(!Object.hasOwn(BASE,unit))throw new Error('Unidade inválida');
  let q=D(quantity);
  if(!q.isFinite()||q.lte(0))throw new Error('Quantidade precisa ser positiva');
  if(unit==='g'||unit==='ml')q=q.div(1000);
  if(unit==='mg')q=q.div(1000000);
  return q;
}
export function purchaseBaseCost(price,qty,unit){return D(price).div(baseQty(qty,unit));}
export function correctedCost(baseCost,fc){return D(baseCost).mul(D(fc));}
export function suggestedPrice(cost,margin,mode='margin'){
  let m=D(margin).div(100);
  if(m.lt(0)||m.gte(1))throw new Error('Percentual deve ser entre 0 e 99,99');
  return mode==='markup'?D(cost).mul(m.plus(1)):D(cost).div(D(1).minus(m));
}
export function contribution(cost,price){
 const p=D(price);return {amount:p.minus(cost),percentage:p.gt(0)?p.minus(cost).div(p).mul(100):D(0)};
}
export function averageCost(previousQty,previousAvg,incomingQty,incomingCost){
 const newQty=D(previousQty).plus(incomingQty);
 if(newQty.lte(0))return D(0);
 return D(previousQty).mul(previousAvg).plus(D(incomingQty).mul(incomingCost)).div(newQty);
}
