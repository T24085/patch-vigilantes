'use strict';
(async()=>{
const status=document.getElementById('counter-status'),digits=document.getElementById('counter-digits');
const raw=document.querySelector('meta[name="counter-endpoint"]').content;
if(!raw)return;
try{
if(location.protocol==='file:')throw Error('Local preview');
const endpoint=new URL(raw,location.href);if(endpoint.origin!==location.origin)throw Error('Counter must be first-party');
const response=await fetch(endpoint,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({path:location.pathname}),credentials:'omit',cache:'no-store'});
if(!response.ok)throw Error('Counter unavailable');
const data=await response.json();if(!Number.isSafeInteger(data.pageViews)||data.pageViews<0)throw Error('Invalid count');
const count=String(data.pageViews).padStart(6,'0');digits.replaceChildren(...[...count].map(n=>{const span=document.createElement('span');span.textContent=n;return span;}));status.textContent=data.pageViews+' page views recorded.';
}catch(error){status.textContent='Counter unavailable. No count shown.';}
})();