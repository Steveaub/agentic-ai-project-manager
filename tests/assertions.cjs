// Count assertions actually executed, including loop and helper invocations.
const native=require('node:assert/strict');
let count=0;
const assert=new Proxy(native,{
 apply(target,receiver,args){count++;return Reflect.apply(target,receiver,args);},
 get(target,key){const value=Reflect.get(target,key);return typeof value==='function'?(...args)=>{count++;return Reflect.apply(value,target,args);}:value;}
});
module.exports={assert,assertionCount:()=>count};
