// Screenshot every in-scope desktop screen. Usage: node cook/shoot.js <outdir> [w h ...]
const { chromium } = require('playwright'); const http=require('http'),fs=require('fs'),path=require('path');
const root=path.resolve(__dirname,'..'),OUT=process.argv[2];
const sizes=process.argv.length>3?[[+process.argv[3],+process.argv[4]]]:[[1366,768],[1630,1000]];
const srv=http.createServer((q,r)=>{let f=path.join(root,decodeURIComponent(q.url.split('?')[0]));if(f.endsWith('/'))f+='index.html';fs.readFile(f,(e,d)=>{if(e){r.writeHead(404);r.end();return;}r.writeHead(200,{'content-type':{'.html':'text/html','.js':'text/javascript','.woff2':'font/woff2'}[path.extname(f)]||'application/octet-stream'});r.end(d);});}).listen(8810);
(async()=>{const b=await chromium.launch();
 for(const [w,h] of sizes){
  const ctx=await b.newContext({viewport:{width:w,height:h},serviceWorkers:'block',colorScheme:'dark'});
  await ctx.addInitScript(()=>{try{localStorage.setItem('kingsrun-tour','1')}catch(e){}});
  const p=await ctx.newPage();const errs=[];p.on('pageerror',e=>errs.push(String(e)));const tag=`${w}x${h}`;
  const snap=async n=>{await p.waitForTimeout(450);await p.screenshot({path:`${OUT}/${n}-${tag}.png`});};
  await p.goto('http://localhost:8810/');await p.waitForTimeout(500);if(await p.isVisible('#title'))await p.click('#tplay');await p.waitForTimeout(600);
  // round 3: court figures + boss cards
  await p.evaluate(()=>{clearTimeout(timer);timer=null;newGame({mode:'run',count:2,names:[]});G.run.gold=47;G.turn=0;G.phase='discard';const me=G.players[0];me.hand=[{s:1,r:13},{s:2,r:12},{s:0,r:11},{s:3,r:13},{s:4,r:12},{s:1,r:11},{s:2,r:7}];G.discard.push({s:3,r:12});render();});await snap('8-court-hand-run');
  await p.evaluate(()=>{clearTimeout(timer);timer=null;newGame({mode:'ai',count:3,names:[],level:'normal'});G.turn=0;G.phase='discard';G.round=9;const me=G.players[0];me.hand=[{s:1,r:13},{s:2,r:12},{s:0,r:11},{s:3,r:13},{s:4,r:12},{s:1,r:11},{s:2,r:7},{s:0,r:6},{s:3,r:9}];G.discard.push({s:4,r:11});render();});await snap('9-court-hand-std');
  for(const k of ['miser','jester','usurper']){await p.evaluate(k=>{clearTimeout(timer);timer=null;newGame({mode:'run',count:2,names:[]});const b=BOSSES[k];G.players[1].name=b.name;G.players[1].boss=k;G.run.boss=k;G.run.gold=47;G.turn=0;G.phase='draw';render();openCourt&&0;},k);await snap('10-boss-'+k);}
  // 1 classic table, draw phase, then discard phase with a real hand
  await p.evaluate(()=>{seedRng(11);clearTimeout(timer);timer=null;newGame({mode:'ai',count:3,names:[],level:'normal'});G.turn=0;G.phase='draw';G.round=5;const me=G.players[0];me.hand=[];while(me.hand.length<7)me.hand.push(G.deck.pop());G.players.forEach((q,i)=>{q.score=[34,58,12,71][i]});render();});
  await snap('1-table-draw');
  await p.click('#deckBtn');await p.waitForTimeout(500);await p.click('#groups .card >> nth=2');await snap('2-table-discard');
  // 3 round results
  await p.evaluate(()=>{const me=G.players[0];G.outBy=1;G.phase='roundEnd';if(typeof endRound==='function'){try{endRound()}catch(e){}}render();});await snap('3-results');
  // 4-7 the Run
  await p.evaluate(()=>{clearTimeout(timer);timer=null;newGame({mode:'run',count:2,names:[]});G.run.regalia=['spyglass','patron'];G.run.decrees=['scout','fog'];G.run.gold=47;G.turn=0;G.phase='draw';render();});await snap('4-run-table');
  await p.evaluate(()=>{G.round=4;G.run.boss='miser';render();});await snap('5-boss-table');
  await p.evaluate(()=>{G.phase='roundEnd';openCourt&&openCourt();render();});await snap('6-court');
  await p.evaluate(()=>{G.round=3;G.run.boss=null;G.phase='roundEnd';openCourt&&openCourt();render();});await snap('11-court-boss-next');
  await p.evaluate(()=>{G.run.over='won';G.round=11;G.phase='gameEnd';G.result=G.result||G.players.map(()=>({melds:[],dead:[],pts:0}));G.outBy=0;render();});await snap('7-run-end');
  console.log(tag,errs.length?errs:'no errors');await ctx.close();}
 await b.close();srv.close();})();
