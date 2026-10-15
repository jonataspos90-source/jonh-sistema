import test from 'node:test';
import assert from 'node:assert/strict';
import {baseQty,purchaseBaseCost,correctedCost,suggestedPrice,averageCost} from '../src/services/math.js';
import {buildCostModel,validateRecipeCycle} from '../src/services/costing.js';
test('conversão embalagem 500g por 12 = R$24/kg',()=>{
 assert.equal(baseQty(500,'g').toString(),'0.5');
 assert.equal(purchaseBaseCost(12,500,'g').toString(),'24');
 assert.equal(purchaseBaseCost(10,500,'ml').toString(),'20');
});
test('FC para carne com aproveitamento 75%',()=>assert.equal(correctedCost(35, '1.33333333333333').toDecimalPlaces(2).toString(),'46.67'));
test('margem de contribuição 30% é diferente de markup 30%',()=>{
 assert.equal(suggestedPrice(70,30,'margin').toString(),'100');
 assert.equal(suggestedPrice(70,30,'markup').toString(),'91');
});
test('custo médio ponderado',()=>assert.equal(averageCost(3,10,1,18).toString(),'12'));
test('subproduto encadeado custa corretamente sem circularidade',()=>{
 const p=[{id:1,package_qty:1,package_unit:'kg',purchase_price:5,avg_cost:5,fc:1},
 {id:2,package_qty:1,package_unit:'kg',purchase_price:0,avg_cost:0,fc:1},
 {id:3,package_qty:1,package_unit:'un',purchase_price:0,avg_cost:0,fc:1,practiced_price:20}];
 const r=[{id:11,product_id:2,yield_qty:4,margin:30,pricing_mode:'margin',active:true},
 {id:12,product_id:3,yield_qty:10,margin:30,pricing_mode:'margin',active:true}];
 const i=[{recipe_id:11,product_id:1,net_qty:4},{recipe_id:12,product_id:2,net_qty:2}];
 const m=buildCostModel(p,r,i);assert.equal(m.realCost(2).toString(),'5');assert.equal(m.realCost(3).toString(),'1');
});
test('bloqueia ciclo entre subprodutos',()=>assert.throws(()=>validateRecipeCycle([{id:10,product_id:1}], [{recipe_id:10,product_id:2}],2,[{productId:1}]),/circular/));
