'use strict';
const fs=require('fs'),path=require('path');
function createCounter({directory,allowedOrigin}){
const origin=new URL(allowedOrigin).origin;fs.mkdirSync(directory,{recursive:true});const file=path.join(directory,'page-views.json');
function load(){if(!fs.existsSync(file))return 0;const n=JSON.parse(fs.readFileSync(file,'utf8')).pageViews;if(!Number.isSafeInteger(n)||n<0)throw Error('Invalid persistent count');return n;}
return function handle({method,headers={},body=''}){let count=load();const reply=(status)=>({status,headers:{'Cache-Control':'no-store','Content-Type':'application/json'},body:{pageViews:count}});if(method==='GET')return reply(200);if(method!=='POST')return reply(405);if(headers.origin!==origin)return reply(403);if(typeof body!=='string'||body.length>1024)return reply(400);let event;try{event=JSON.parse(body);}catch{return reply(400);}if(!['/','/index.html'].includes(event.path))return reply(400);if(/bot|crawler|spider|headless|playwright|selenium|test/i.test(headers['user-agent']||'')||headers['x-workshop-test'])return reply(200);if(count>=Number.MAX_SAFE_INTEGER)return reply(503);count++;const temporary=file+'.pending';fs.writeFileSync(temporary,JSON.stringify({pageViews:count}));fs.renameSync(temporary,file);return reply(200);};
}
module.exports={createCounter};