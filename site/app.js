'use strict';
const $=id=>document.getElementById(id);
const CACHE_KEY='russell-snapshot-v1';
const CHECKS=[['①EMA並び','EMA並び'],['②出来高急増','出来高急増'],['③RS優位','RS優位'],['④売買代金','売買代金'],['⑤高値圏10-30%','高値圏10–30%']];
const SECTOR_LABELS={'Technology':'テクノロジー','Healthcare':'ヘルスケア','Industrials':'資本財','Financial Services':'金融','Consumer Cyclical':'一般消費財','Consumer Defensive':'生活必需品','Basic Materials':'素材','Communication Services':'通信','Real Estate':'不動産','Energy':'エネルギー','Utilities':'公益'};
let state=null,tab='new',limit=60;
function node(tag,cls,value){const el=document.createElement(tag);if(cls)el.className=cls;if(value!==undefined)el.textContent=value;return el;}
function setText(id,value){$(id).textContent=value;}
function number(value,digits=0){const n=Number(value);return Number.isFinite(n)?n.toLocaleString('ja-JP',{maximumFractionDigits:digits}):'—';}
function pass(row){return row.all_pass==='True';}
function parseCsv(text){
  const rows=[];let row=[],field='',quoted=false;
  text=text.replace(/^\uFEFF/,'');
  for(let i=0;i<text.length;i++){
    const ch=text[i];
    if(quoted){if(ch==='"'&&text[i+1]==='"'){field+='"';i++;}else if(ch==='"'){quoted=false;}else{field+=ch;}}
    else if(ch==='"'){quoted=true;}
    else if(ch===','){row.push(field);field='';}
    else if(ch==='\n'||ch==='\r'){if(ch==='\r'&&text[i+1]==='\n')i++;row.push(field);if(row.some(v=>v!==''))rows.push(row);row=[];field='';}
    else{field+=ch;}
  }
  if(quoted)throw Error('CSVの引用符が閉じていません');
  row.push(field);if(row.some(v=>v!==''))rows.push(row);
  const [headers,...body]=rows;if(!headers?.length)throw Error('CSVが空です');
  return body.map(values=>Object.fromEntries(headers.map((key,i)=>[key,values[i]??''])));
}
function validate(snapshot){
  const {results,history,passes,date}=snapshot;
  if(!/^\d{4}-\d{2}-\d{2}$/.test(date)||!Array.isArray(results)||!results.length||!Array.isArray(history)||!Array.isArray(passes))throw Error('スキャンデータが不足しています');
  if(results.some(r=>!r.ticker||!/^\d$/.test(r.score)||!['True','False'].includes(r.all_pass)))throw Error('銘柄データに欠損があります');
  const tickers=results.map(r=>r.ticker);
  if(new Set(tickers).size!==tickers.length)throw Error('銘柄データが重複しています');
  const current=history.find(r=>r.date===date);
  if(!current||Number(current.total)!==results.length||Number(current.all_pass)!==results.filter(pass).length)throw Error('スキャン日・件数が履歴と一致しません');
  const fromPass=new Set(passes.filter(r=>r.date===date).map(r=>r.ticker));
  if(fromPass.size!==Number(current.all_pass)||results.some(r=>pass(r)!==fromPass.has(r.ticker)))throw Error('条件クリア履歴が結果と一致しません');
  return snapshot;
}
async function load(){
  $('refresh').disabled=true;setText('status','最新のスキャン結果を確認中…');
  try{
    const files=['results.csv','history.csv','pass_history.csv','last_updated.txt'];
    const texts=await Promise.all(files.map(async name=>{
      const response=await fetch('data/'+name+'?t='+Date.now(),{cache:'no-store'});
      if(!response.ok)throw Error(name+' の取得に失敗しました');return response.text();
    }));
    const snapshot=validate({results:parseCsv(texts[0]),history:parseCsv(texts[1]),passes:parseCsv(texts[2]),date:texts[3].trim()});
    state=snapshot;
    try{localStorage.setItem(CACHE_KEY,JSON.stringify(snapshot));}catch(_){/* 保存枠が小さい端末でも表示は続ける */}
    render('最新データ');
  }catch(error){
    let backup=null;
    try{backup=validate(JSON.parse(localStorage.getItem(CACHE_KEY)));}catch(_){}
    if(backup){state=backup;render('更新できません。前回保存した結果を表示中');}
    else if(state){render('更新できません。表示中の結果を維持');}
    else{setText('status','読み込めませんでした。通信状態を確認して ↻ を押してください。');}
    console.warn('スキャンデータの取得:',error);
  }finally{$('refresh').disabled=false;}
}
function derive(){
  const dates=state.history.map(r=>r.date).filter(d=>d<=state.date).sort();
  const prior=dates.filter(d=>d<state.date).at(-1);
  const currentSet=new Set(state.results.filter(pass).map(r=>r.ticker));
  const priorRows=prior?state.passes.filter(r=>r.date===prior):[];
  const priorSet=new Set(priorRows.map(r=>r.ticker));
  return {prior,currentSet,priorRows,priorSet,
    new:prior?state.results.filter(r=>pass(r)&&!priorSet.has(r.ticker)):[],
    pass:state.results.filter(pass),near:state.results.filter(r=>r.score==='4'&&!pass(r)),
    out:prior?priorRows.filter(r=>!currentSet.has(r.ticker)).map(r=>({...r,current:state.results.find(x=>x.ticker===r.ticker)})):[],
    all:state.results};
}
function render(status){
  const d=derive();
  const elapsed=(Date.now()-new Date(state.date+'T00:00:00+09:00').getTime())/86400000;
  setText('status','スキャン基準日 '+state.date+' ・ '+status+(elapsed>10?' ・ 更新が遅れています':''));
  const metrics=$('metrics');metrics.replaceChildren();
  for(const [label,value] of [['全条件',d.pass.length],['新規',d.new.length],['あと1条件',d.near.length],['対象銘柄',d.all.length]]){
    const box=node('div','metric');box.append(node('strong','',number(value)),node('span','',label));metrics.append(box);
  }
  metrics.hidden=false;$('tabs').hidden=false;$('results').hidden=false;
  for(const name of ['new','pass','near','out','all'])document.querySelector(`[data-count="${name}"]`).textContent=number(d[name].length);
  const select=$('sector'),selected=select.value;select.replaceChildren(new Option('全セクター',''));
  [...new Set(d.all.map(r=>r.sector).filter(Boolean))].sort().forEach(s=>select.add(new Option(SECTOR_LABELS[s]?`${SECTOR_LABELS[s]} (${s})`:s,s)));
  select.value=selected;
  renderTab();
}
function renderTab(){
  if(!state)return;
  const d=derive(),rows=d[tab]||[];
  document.querySelectorAll('#tabs button').forEach(button=>{
    const active=button.dataset.tab===tab;button.classList.toggle('active',active);
    if(active)button.setAttribute('aria-current','page');else button.removeAttribute('aria-current');
  });
  const titles={new:'新しく条件を満たした銘柄',pass:'全条件クリア',near:'あと1条件の銘柄',out:'今回条件から外れた銘柄',all:'スキャン対象の全銘柄',trend:'週次の推移・内訳'};
  setText('section-title',titles[tab]);
  setText('section-subtitle',tab==='new'||tab==='out'?(d.prior?`${state.date} と ${d.prior} を比較`:'比較する前回スキャンがありません'):tab==='near'?'4点で全条件クリアには届いていない銘柄':tab==='trend'?'保存されたスキャン履歴':'スコアは5条件の一致数です');
  $('filters').hidden=tab==='trend';$('trend').hidden=tab!=='trend';$('copy').hidden=tab==='trend'||tab==='out'||!rows.length;
  $('cards').hidden=tab==='trend';$('result-count').hidden=tab==='trend';$('more').hidden=true;
  if(tab==='trend'){renderTrend(d);return;}
  const q=$('search').value.trim().toUpperCase(),sector=$('sector').value,score=$('score').value;
  const filtered=rows.filter(r=>(!q||[r.ticker,r.industry,r.sector].some(s=>String(s||'').toUpperCase().includes(q)))&&(!sector||r.sector===sector)&&(!score||((score==='low')?Number(r.current?.score??r.score)<=2:(r.current?.score??r.score)===score)));
  setText('result-count',`${number(filtered.length)} 銘柄を表示`);
  const cards=$('cards');cards.replaceChildren();
  if(!filtered.length)cards.append(node('p','empty',rows.length?'この条件に合う銘柄はありません':'該当銘柄はありません'));
  for(const r of filtered.slice(0,limit))cards.append(makeCard(r,tab==='out'));
  $('more').hidden=filtered.length<=limit;
  $('copy').onclick=async()=>{try{await navigator.clipboard.writeText(filtered.map(r=>r.ticker).join(','));$('copy').textContent='コピーしました';setTimeout(()=>$('copy').textContent='銘柄をコピー',1800);}catch(_){$('copy').textContent='コピーできませんでした';}};
}
function makeCard(row,dropped){
  const card=node('article','card');
  const details=node('details');const summary=node('summary');
  const identity=node('div','identity');identity.append(node('strong','ticker',row.ticker),node('span','sector-name',SECTOR_LABELS[row.sector]||row.sector||'セクター不明'));
  const score=row.current?.score??row.score;
  summary.append(identity,node('span','score '+(dropped?'muted':Number(score)>=5?'best':Number(score)===4?'near':''),dropped?(row.current?'今回 '+score+'点':'未スキャン'):score+' / 5'),node('span','chevron','⌄'));
  const meta=node('div','card-meta');meta.append(node('span','',row.industry||'業種不明'),node('span','',dropped?'前回RS '+number(row['銘柄RS'],2):'高値から '+number(row['高値乖離%'],1)+'%'));
  details.append(summary,meta);
  const body=node('div','detail-body');
  if(dropped&&!row.current)body.append(node('p','notice','今回はスキャンされていません。条件による脱落かデータ取得失敗かは判別できません。'));
  const current=row.current||(!dropped?row:null);
  if(current){
    const checks=node('div','checks');for(const [field,label] of CHECKS){const value=current[field]??(field.startsWith('⑤')?current['⑤高値圏']:'');checks.append(node('span',value==='✅'?'ok':'fail',(value==='✅'?'✓ ':'× ')+label));}body.append(checks);
    const facts=node('div','facts');
    for(const [label,value] of [['現在値',number(current['現在値'],2)+' $'],['高値乖離',number(current['高値乖離%'],1)+' %'],['直近出来高倍率',number(current['出来高倍率'],2)+' 倍'],['20週平均・週次売買代金',number(current['売買代金(M$)'],1)+' M$'],['銘柄RS',number(current['銘柄RS'],2)]]){const item=node('div');item.append(node('span','',label),node('strong','',value));facts.append(item);}body.append(facts);
    body.append(node('p','hint','出来高の合格判定は過去15週以内。表示倍率は直近週の値です。'));
  }
  const actions=node('div','actions');const chart=node('a','primary','mychartを開く ↗');chart.href='https://nyokki0204-boop.github.io/mychart/mychart.html';chart.target='_blank';chart.rel='noopener';
  const tv=node('a','secondary','TradingView ↗');tv.href='https://www.tradingview.com/chart/?symbol='+encodeURIComponent(row.ticker);tv.target='_blank';tv.rel='noopener';
  actions.append(chart,tv);body.append(actions);details.append(body);card.append(details);return card;
}
function renderTrend(d){
  const target=$('trend');target.replaceChildren();const history=state.history.filter(r=>r.date<=state.date).sort((a,b)=>a.date.localeCompare(b.date));
  if(!history.length){target.append(node('p','empty','履歴データはありません'));return;}
  const box=node('section','panel');box.append(node('h3','','条件クリア数の推移'));
  const svg=document.createElementNS('http://www.w3.org/2000/svg','svg');svg.setAttribute('viewBox','0 0 640 240');svg.setAttribute('role','img');svg.setAttribute('aria-label','全条件クリアと4点以上の銘柄数の推移');
  const max=Math.max(1,...history.map(r=>Number(r.score4plus)||0),...history.map(r=>Number(r.all_pass)||0));
  for(const [key,color] of [['score4plus','#e4b969'],['all_pass','#4ce5af']]){
    const points=history.map((r,i)=>`${42+i*574/Math.max(1,history.length-1)},${200-(Number(r[key])||0)*160/max}`).join(' ');
    const line=document.createElementNS(svg.namespaceURI,'polyline');line.setAttribute('points',points);line.setAttribute('fill','none');line.setAttribute('stroke',color);line.setAttribute('stroke-width','3');line.setAttribute('stroke-linecap','round');line.setAttribute('stroke-linejoin','round');svg.append(line);
  }
  box.append(svg,node('p','legend','● 全条件クリア    ● 4点以上（全条件クリアを含む）'));
  const list=node('div','history-list');for(const r of [...history].reverse()){
    const item=node('div');item.append(node('time','',r.date),node('strong','','全条件 '+number(r.all_pass)),node('span','','4点以上 '+number(r.score4plus)));list.append(item);
  }box.append(list);target.append(box);
  const summary=node('section','panel');summary.append(node('h3','','セクター別・全条件クリア'));
  const groups=new Map();for(const r of d.pass)groups.set(r.sector||'その他',(groups.get(r.sector||'その他')||0)+1);
  for(const [sector,count] of [...groups].sort((a,b)=>b[1]-a[1])){const item=node('div','sector-row');item.append(node('span','',SECTOR_LABELS[sector]||sector),node('strong','',number(count)));summary.append(item);}
  target.append(summary);
}
document.querySelectorAll('#tabs button').forEach(button=>button.addEventListener('click',()=>{tab=button.dataset.tab;limit=60;renderTab();}));
$('search').addEventListener('input',()=>{limit=60;renderTab();});
$('sector').addEventListener('change',()=>{limit=60;renderTab();});
$('score').addEventListener('change',()=>{limit=60;renderTab();});
$('more').addEventListener('click',()=>{limit+=60;renderTab();});
$('refresh').addEventListener('click',load);
if('serviceWorker'in navigator)navigator.serviceWorker.register('sw.js').catch(()=>{});
load();
