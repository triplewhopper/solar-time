'use strict';
(()=>{
 const $=id=>document.getElementById(id),M=SolarPrecision;
 let engine,live=true,forceError=false,validation=null;
 const source=()=>$('eopSource').value;
 const coords=['lonD','lonM','lonS','lonH','latD','latM','latS','latH','height'];
 const manualIDs=['dut1','tai','xp','yp','dx','dy'];
 function setNow(){const c=M.clock(Date.now()+32400000);$('date').value=c.date;$('time').value=c.time;}
 function showClock(prefix,ms){const c=M.clock(ms);$(prefix+'Clock').textContent=c.time;$(prefix+'Date').textContent=c.date;}
 function clearResults(){for(const id of ['meanOffset','eot','meanClock','trueClock'])$(id).textContent='—';$('trueOffset').textContent='等待有效输入';$('direction').textContent='以东经 135° 为东九区标准子午线。';$('meanDate').textContent='含 UT1−UTC';$('trueDate').textContent='由太阳视时角计算';$('coordinate').textContent='输入经纬度后，结果会自动更新。';$('eopStatus').textContent='等待有效输入。';$('stabilityNote').textContent='';}
 function readCoordinate(prefix,max){
  const vals=['D','M','S'].map(k=>$(prefix+k).value.trim());
  if(vals[0]===''){ $(prefix+'D').setAttribute('aria-invalid','true');throw Error('请填写'+(prefix==='lon'?'经度':'纬度')+'的度数。');}
  try{return M.dms(...vals.map((v,i)=>v===''&&i>0?0:Number(v)),Number($(prefix+'H').value),max);}catch{['D','M','S'].forEach(k=>$(prefix+k).setAttribute('aria-invalid','true'));throw Error((prefix==='lon'?'经度':'纬度')+'的度、分须为整数，秒须在 0–60 之间（不含 60），并且不得超过 '+max+'°。');}
 }
 function manualValues(){if(!$('manual').checked)return null;const m={};for(const id of manualIDs){if($(id).value==='')throw Error('请完整填写手动修正参数。');m[id]=Number($(id).value);}if(Math.abs(m.dut1)>10||Math.abs(m.xp)>10||Math.abs(m.yp)>10||Math.abs(m.dx)>1000||Math.abs(m.dy)>1000||!Number.isInteger(m.tai)||m.tai<10||m.tai>100)throw Error('手动修正参数超出合理范围，请检查单位。');return m;}
 function dateRange(){const rows=engine.data.rows,j=engine.data.jpl;const fmt=ms=>new Date(ms+32400000).toISOString().replace('T',' ').slice(0,19);const from=source()==='jpl'?Date.UTC(1972,0,1,0,15):(rows[0][0]-40587)*86400000;const to=source()==='jpl'?(j.rows.at(-1)[0]-40587)*86400000-engine.tai(Date.now())*1000:(rows.at(-1)[0]-40587)*86400000-1;$('dataRange').textContent='自动修正覆盖（东九区）：'+fmt(from)+' 至 '+fmt(to)+'。JPL 观测/预测转换日期：'+j.last_utpm_data_utc.slice(0,10)+'（UTC）。';}

 function render(){
  $('error').textContent='';coords.forEach(id=>$(id).removeAttribute('aria-invalid'));
  $('mode').textContent=live?'当前时间 · 每秒刷新':'指定时间 · 已暂停更新';
  let ms;try{ms=M.parseJST($('date').value,$('time').value);showClock('standard',ms+32400000);}catch(e){clearResults();$('standardClock').textContent='—';$('standardDate').textContent='UTC+9';$('error').textContent=e.message;return;}
  if(!engine){clearResults();$('trueOffset').textContent='正在加载星历';return;}
  try{
   if(!forceError&&$('lonD').value===''&&$('latD').value===''){clearResults();$('trueOffset').textContent='等待输入经纬度';return;}
   const longitude=readCoordinate('lon',180),latitude=readCoordinate('lat',90);if($('height').value==='')throw Error('请填写椭球高；未知时可使用 0 米作为近似。');
   const height=Number($('height').value),r=engine.calculate({ms,longitude,latitude,height,manual:manualValues(),source:source(),extrapolate:$('extrapolate').checked});
   $('trueOffset').textContent=M.duration(r.true,true);$('meanOffset').textContent=M.duration(r.mean);$('eot').textContent=M.duration(r.eot);
   $('direction').textContent='相对于东九区标准时 · '+$('date').value;
   showClock('mean',ms+32400000+r.mean*1000);showClock('true',ms+32400000+r.true*1000);
   $('coordinate').textContent='经度 '+longitude.toFixed(9)+'° / 纬度 '+latitude.toFixed(9)+'° / 椭球高 '+height+' m';
   const names={J:'JPL EOP2 观测数据',JP:'JPL EOP2 含预测数据',JX:'JPL EOP2 固定末值外推（不保证未来准确）',B:'IERS B 最终数据',A:'IERS A 观测数据',P:'IERS A 预测数据',manual:'手动参数（精度由输入决定）'};
   $('eopStatus').textContent=names[r.eop.status]+'；UT1−UTC = '+r.dut1.toFixed(7)+' 秒；极移 xp / yp = '+r.eop.xp.toFixed(6)+'″ / '+r.eop.yp.toFixed(6)+'″。'+(r.eop.missingCIP?'缺少该时刻的 dX/dY，采用模型值（修正设为 0）。':'已计入 dX/dY 修正。')+(['P','JP'].includes(r.eop.status)?'未来预测可能变化。':'');
   $('stabilityNote').textContent=(r.polarSensitive?'近极区：子午面对极移和参考框架差异非常敏感，全球对照中出现秒至分钟级差异。本页不宣称此区域具有毫秒精度。 ':'')+(r.eop.extrapolated?'已超出预测数据范围，使用固定末值；结果仅为模型外推。':'');
  }catch(e){clearResults();$('error').textContent=e.message;}
 }
 function importIERS(text){
  const rows=[];
  for(const line of text.split(/\r?\n/)){
   const f=(a,b)=>{const t=line.slice(a-1,b).trim();return t!==''&&Number.isFinite(Number(t))?Number(t):null;};
   let [mjd,x,y,u,dx,dy]=[[7,15],[19,27],[38,46],[59,68],[98,106],[117,125]].map(([a,b])=>f(a,b));
   if([mjd,x,y,u].some(v=>v===null))continue;
   const [bx,by,bu,bdx,bdy]=[[135,144],[145,154],[155,165],[166,175],[176,185]].map(([a,b])=>f(a,b));
   const final=[bx,by,bu].every(v=>v!==null);if(final){x=bx;y=by;u=bu;if(bdx!==null&&bdy!==null){dx=bdx;dy=bdy;}}
   if(!Number.isInteger(mjd)||Math.abs(x)>10||Math.abs(y)>10||Math.abs(u)>10||(rows.length&&mjd!==rows.at(-1)[0]+1))throw Error('文件包含异常或不连续的地球自转参数。');
   rows.push([mjd,x,y,u,dx,dy,final?'B':line[57]==='P'||line[16]==='P'?'P':'A',f(69,78)]);
  }
  if(rows.length<2)throw Error('未读到有效 IERS 数据，请选择 finals2000A.all 格式的文本文件。');
  const leaps=engine.data.leaps.map(v=>v.slice());
  for(let i=1;i<rows.length;i++){const delta=rows[i][3]-rows[i-1][3],epoch=(rows[i][0]-40587)*86400000;if(Math.abs(delta)>0.5&&epoch>leaps.at(-1)[0])leaps.push([epoch,leaps.at(-1)[1]+Math.round(delta)]);}
  engine.data={...engine.data,rows,leaps,source:'用户导入 IERS 文件'};$('eopSource').value='iers';dateRange();
 }
 coords.forEach(id=>$(id).addEventListener('input',render));manualIDs.forEach(id=>$(id).addEventListener('input',render));
 $('eopSource').addEventListener('change',()=>{dateRange();render();});$('extrapolate').addEventListener('change',render);
 for(const id of ['date','time'])$(id).addEventListener('input',()=>{live=false;render();});
 $('form').addEventListener('submit',e=>{e.preventDefault();forceError=true;render();});
 $('now').addEventListener('click',()=>{live=true;setNow();render();});
 $('example').addEventListener('click',()=>{for(const [id,value] of Object.entries({lonD:135,lonM:0,lonS:0,lonH:1,latD:35,latM:0,latS:0,latH:1,height:100}))$(id).value=value;render();});
 $('reset').addEventListener('click',()=>{HTMLFormElement.prototype.reset.call($('form'));$('manualFields').hidden=true;live=true;forceError=false;setNow();if(engine)dateRange();render();});
 $('manual').addEventListener('change',()=>{const active=$('manual').checked;$('manualFields').hidden=!active;if(active&&engine){try{const e=engine.eop(M.parseJST($('date').value,$('time').value),null,source(),$('extrapolate').checked);manualIDs.forEach(id=>$(id).value=e[id]);}catch{}}render();});
 $('iersFile').addEventListener('change',async()=>{const f=$('iersFile').files[0];if(!f)return;try{if(f.size>15*1024*1024)throw Error('文件过大，请使用标准 IERS 文本文件。');importIERS(await f.text());$('engineStatus').textContent='已载入你选择的 IERS 数据；文件只在本页处理。';render();}catch(e){$('error').textContent=e.message;}});
 async function boot(){
  try{
   let buffer,data;
   if($('offline-spk')){const bytes=atob($('offline-spk').textContent.trim()),array=new Uint8Array(bytes.length);for(let i=0;i<bytes.length;i++)array[i]=bytes.charCodeAt(i);buffer=array.buffer;data=JSON.parse($('offline-eop').textContent);validation=JSON.parse($('offline-validation').textContent);}
   else{const responses=await Promise.all(['data/de441-solar.bsp','data/eop.json','data/validation.json'].map(url=>fetch(url)));if(responses.some(r=>!r.ok))throw Error('本地星历资源未能加载，请重新打开页面。');[buffer,data,validation]=await Promise.all([responses[0].arrayBuffer(),responses[1].json(),responses[2].json()]);}
   engine=new M.Engine(buffer,data,ERFA);dateRange();$('engineStatus').textContent='DE441、JPL 与 IERS 数据已就绪 · 所有计算在当前浏览器内完成。';
   $('precisionNote').textContent='默认 JPL 模式已完成 '+validation.horizons.cases.toLocaleString()+' 组 Horizons 全范围分层对照。|纬度|≤85° 的样本最大差异 '+validation.horizons.nonpolar.max_abs_ms.toFixed(3)+' 毫秒；全域含近极点样本最大差异 '+(validation.horizons.all.max_abs_ms/1000).toFixed(3)+' 秒。这里只报告样本统计，不是连续定义域误差上界。';render();
  }catch(e){$('engineStatus').textContent=e.message;$('engineStatus').classList.add('error-state');clearResults();$('trueOffset').textContent='星历加载失败';}
 }
 setNow();render();boot();setInterval(()=>{if(live){setNow();render();}},1000);
})();
