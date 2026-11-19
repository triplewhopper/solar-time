'use strict';
(()=>{
 const $=id=>document.getElementById(id),M=SolarPrecision;
 let engine,live=true,forceError=false,validation=null,runtime=null,geoid=null,geoidReady=null;
 const source=()=>$('eopSource').value;
 const snapshotName=()=>engine.data.reconstructed.source_file_obtained?'JPL原始快照':'PCK恢复快照';
 const coords=['lonD','lonM','lonS','lonH','latD','latM','latS','latH','height'];
 const manualIDs=['dut1','tai','xp','yp','dx','dy'];
 function loadGeoid(){if(geoid)return Promise.resolve(geoid);if(!geoidReady)geoidReady=GeoidGrid.load().then(value=>{geoid=value;return value;}).catch(error=>{geoidReady=null;throw error;});return geoidReady;}
 function setNow(){const c=M.clock(Date.now()+32400000);$('date').value=c.date;$('time').value=c.time;}
 function showClock(prefix,ms){const c=M.clock(ms);$(prefix+'Clock').textContent=c.time;$(prefix+'Date').textContent=c.date;}
 function clearResults(){for(const id of ['meanOffset','eot','meanClock','trueClock'])$(id).textContent='—';$('trueOffset').textContent='等待有效输入';$('direction').textContent='以东经 135° 为东九区标准子午线。';$('meanDate').textContent='含 UT1−UTC';$('trueDate').textContent='由太阳视时角计算';$('coordinate').textContent='输入经纬度后，结果会自动更新。';$('eopStatus').textContent='等待有效输入。';$('stabilityNote').textContent='';}
 function readCoordinate(prefix,max){
  const vals=['D','M','S'].map(k=>$(prefix+k).value.trim());
  if(vals[0]===''){ $(prefix+'D').setAttribute('aria-invalid','true');throw Error('请填写'+(prefix==='lon'?'经度':'纬度')+'的度数。');}
  try{return M.dms(...vals.map((v,i)=>v===''&&i>0?0:Number(v)),Number($(prefix+'H').value),max);}catch{['D','M','S'].forEach(k=>$(prefix+k).setAttribute('aria-invalid','true'));throw Error((prefix==='lon'?'经度':'纬度')+'的度、分须为整数，秒须在 0–60 之间（不含 60），并且不得超过 '+max+'°。');}
 }
 function manualValues(){if(!$('manual').checked)return null;const m={};for(const id of manualIDs){if($(id).value==='')throw Error('请完整填写手动修正参数。');m[id]=Number($(id).value);}if(Math.abs(m.dut1)>10||Math.abs(m.xp)>10||Math.abs(m.yp)>10||Math.abs(m.dx)>1000||Math.abs(m.dy)>1000||!Number.isInteger(m.tai)||m.tai<10||m.tai>100)throw Error('手动修正参数超出合理范围，请检查单位。');return m;}
 function updateLabels(){$('dxLabel').textContent=['legacy','reconstructed'].includes(source())?'dPsi（毫角秒）':'dX（毫角秒）';$('dyLabel').textContent=['legacy','reconstructed'].includes(source())?'dEps（毫角秒）':'dY（毫角秒）';}
 function dateRange(){const rows=engine.data.rows,j=engine.data.jpl,l=engine.data.legacy,fmt=ms=>new Date(ms+32400000).toISOString().replace('T',' ').slice(0,19);let from,to,note;if(source()==='reconstructed'){from=Date.UTC(1972,0,1,0,15);to=(engine.data.reconstructed.evaluation_end_mjd-40587)*86400000;const r=engine.data.reconstructed;note=(r.source_file_obtained?'已取得官方原始ASCII，并与独立PCK恢复结果核对。':'由官方PCK独立恢复，不是下载的原始ASCII。')+'版本：'+r.release_label+'；支撑终点 '+fmt((r.support_end_mjd-40587)*86400000)+'。';}else if(source()==='legacy'){from=Date.UTC(1972,0,1,0,15);to=(l.rows.at(-1)[0]-40587)*86400000;note='原始文件版本：'+l.release_label+'。与PCK快照可能不同。';}else if(source()==='jpl'){from=Date.UTC(1972,0,1,0,15);to=(j.rows.at(-1)[0]-40587)*86400000-engine.tai(Date.now())*1000;note='采用 ITRF2008 / IAU2006/2000A，与原始格式的参考框架不同。';}else{from=(rows[0][0]-40587)*86400000;to=(rows.at(-1)[0]-40587)*86400000-1;note='独立 IERS 数据与现代参考框架。';}$('dataRange').textContent='自动修正覆盖（东九区）：'+fmt(from)+' 至 '+fmt(to)+'。'+note;}
 function changeSource(){$('manual').checked=false;$('manualFields').hidden=true;updateLabels();if(engine)dateRange();render();}

 function render(){
  $('error').textContent='';coords.forEach(id=>$(id).removeAttribute('aria-invalid'));
  $('mode').textContent=live?'当前时间 · 每秒刷新':'指定时间 · 已暂停更新';
  let ms;try{ms=M.parseJST($('date').value,$('time').value);showClock('standard',ms+32400000);}catch(e){clearResults();$('standardClock').textContent='—';$('standardDate').textContent='UTC+9';$('error').textContent=e.message;return;}
  if(!engine){clearResults();$('trueOffset').textContent='正在加载星历';return;}
  try{
   if(!forceError&&$('lonD').value===''&&$('latD').value===''){clearResults();$('trueOffset').textContent='等待输入经纬度';return;}
   const longitude=readCoordinate('lon',180),latitude=readCoordinate('lat',90);if($('height').value==='')throw Error('请填写海拔；可直接使用罗盘显示的米数。');
   const elevation=Number($('height').value),converted=geoid.toEllipsoid(elevation,latitude,longitude),r=engine.calculate({ms,longitude,latitude,...converted,manual:manualValues(),source:source(),extrapolate:$('extrapolate').checked});
   $('trueOffset').textContent=M.duration(r.true,true);$('meanOffset').textContent=M.duration(r.mean);$('eot').textContent=M.duration(r.eot);
   $('direction').textContent='相对于东九区标准时 · '+$('date').value;
   showClock('mean',ms+32400000+r.mean*1000);showClock('true',ms+32400000+r.true*1000);
   $('coordinate').textContent='经度 '+longitude.toFixed(9)+'° / 纬度 '+latitude.toFixed(9)+'° / 海拔 '+elevation+' m';
   const release=engine.data.reconstructed.release_label,legacy=engine.data.legacy.release_label;
   const names={R:snapshotName()+'观测段 · '+release,RP:snapshotName()+'预测段 · '+release,RX:snapshotName()+'固定末值外推 · '+release,L:'JPL 原始格式观测数据 · '+legacy,LP:'JPL 原始格式预测数据 · '+legacy,LX:'JPL 原始格式固定末值外推 · '+legacy,J:'JPL EOP2 观测数据（固定备选快照）',JP:'JPL EOP2 预测数据（固定备选快照）',JX:'JPL EOP2 固定末值外推',B:'IERS B 最终数据',A:'IERS A 观测数据',P:'IERS A 预测数据',manual:'手动参数（精度由输入决定）'};
   $('eopStatus').textContent=names[r.eop.status]+'；UT1−UTC = '+r.dut1.toFixed(7)+' 秒；极移 xp / yp = '+r.eop.xp.toFixed(6)+'″ / '+r.eop.yp.toFixed(6)+'″。'+(r.eop.missingCIP?'缺少该时刻的 dX/dY，采用模型值（修正设为 0）。':(['legacy','reconstructed'].includes(source())?'已计入 dPsi/dEps 修正。':'已计入 dX/dY 修正。'))+(['P','JP','LP','RP'].includes(r.eop.status)?'未来预测可能变化。':'');
   $('stabilityNote').textContent=(r.polarSensitive?'近极区对实际位置和极移误差很敏感。恢复快照已通过微秒级数值对照，但这不代表同等物理准确度；切换到其他版本或参考框架时仍可能有明显差异。 ':'')+(r.eop.extrapolated?'已超出预测数据范围，使用固定末值；结果仅为模型外推。':'');
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
  engine.data={...engine.data,rows,leaps,source:'用户导入 IERS 文件'};$('eopSource').value='iers';changeSource();
 }
 const locationInput=LocationInput.bind({button:$('locate'),status:$('locationStatus'),field:$,onFilled:render,toElevation:async(height,latitude,longitude)=>height-(await loadGeoid()).undulation(latitude,longitude)});
 coords.forEach(id=>$(id).addEventListener('input',()=>locationInput.cancel()));
 coords.forEach(id=>$(id).addEventListener('input',render));manualIDs.forEach(id=>$(id).addEventListener('input',render));
 $('eopSource').addEventListener('change',changeSource);$('extrapolate').addEventListener('change',render);
 for(const id of ['date','time'])$(id).addEventListener('input',()=>{live=false;render();});
 $('form').addEventListener('submit',e=>{e.preventDefault();forceError=true;render();});
 $('now').addEventListener('click',()=>{live=true;setNow();render();});
 $('example').addEventListener('click',()=>{locationInput.cancel();for(const [id,value] of Object.entries({lonD:135,lonM:0,lonS:0,lonH:1,latD:35,latM:0,latS:0,latH:1,height:100}))$(id).value=value;render();});
 $('reset').addEventListener('click',()=>{locationInput.cancel();HTMLFormElement.prototype.reset.call($('form'));$('manualFields').hidden=true;live=true;forceError=false;setNow();updateLabels();if(engine)dateRange();render();});
 $('manual').addEventListener('change',()=>{const active=$('manual').checked;$('manualFields').hidden=!active;if(active&&engine){try{const e=engine.eop(M.parseJST($('date').value,$('time').value),null,source(),$('extrapolate').checked);manualIDs.forEach(id=>$(id).value=e[id]);}catch{}}render();});
 $('iersFile').addEventListener('change',async()=>{const f=$('iersFile').files[0];if(!f)return;try{if(f.size>15*1024*1024)throw Error('文件过大，请使用标准 IERS 文本文件。');importIERS(await f.text());$('engineStatus').textContent='已载入你选择的 IERS 数据；文件只在本页处理。';render();}catch(e){$('error').textContent=e.message;}});
 async function getJSON(url){const r=await fetch(url,{cache:'no-cache'});if(!r.ok)throw Error('更新信息暂时无法加载');return r.json();}
 function updateInfo(){
  if(!runtime)return;
  $('updateStatus').textContent='当前快照：'+runtime.release+' · 本版本检查时间：'+new Date(runtime.checked_at).toLocaleString('zh-CN',{timeZone:'Asia/Tokyo',hour12:false})+'（UTC+9）。';
 }
 async function boot(nextRuntime){
  try{
   let buffer,data;
   if($('offline-spk')){const bytes=atob($('offline-spk').textContent.trim()),array=new Uint8Array(bytes.length);for(let i=0;i<bytes.length;i++)array[i]=bytes.charCodeAt(i);buffer=array.buffer;data=JSON.parse($('offline-eop').textContent);validation=JSON.parse($('offline-validation').textContent);}
   else{
    const manifest=nextRuntime||await getJSON('data/runtime.json');
    const responses=await Promise.all(['data/de441-solar.bsp','data/eop.json?v='+manifest.eop_sha256,'data/validation.json'].map(url=>fetch(url)));
    if(responses.some(r=>!r.ok))throw Error('本地星历资源未能加载，请稍后重试。');
    const raw=await responses[1].arrayBuffer(),hash=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',raw)),x=>x.toString(16).padStart(2,'0')).join('');
    if(hash!==manifest.eop_sha256)throw Error('新版数据正在同步，暂不切换快照。');
    [buffer,validation]=await Promise.all([responses[0].arrayBuffer(),responses[2].json()]);data=JSON.parse(new TextDecoder().decode(raw));runtime=manifest;
   }
   await loadGeoid();
   engine=new M.Engine(buffer,data,ERFA);
   $('eopSource').querySelector('option[value="reconstructed"]').textContent=snapshotName()+' · '+data.reconstructed.release_label;
   $('eopSource').querySelector('option[value="legacy"]').textContent='JPL 原始格式 · '+data.legacy.release_label;
   dateRange();updateInfo();$('engineStatus').textContent='星历与修正数据已就绪 · 所有太阳时计算在当前浏览器内完成。';
   const v=runtime?.verification;
   $('precisionNote').textContent=(v?'当前版本：'+v.horizons_cases.toLocaleString()+'组同版本Horizons对照，最大差异 '+v.horizons_max_us.toFixed(3)+' 微秒。':'当前初始快照已通过42,200组Horizons对照，最大差异3.082微秒。')+'另保留2026-11-18固定快照的42,200组算法回归测试。样本误差不是连续定义域上界，也不是物理准确度保证。';render();
  }catch(e){$('engineStatus').textContent=e.message;if(!engine){$('engineStatus').classList.add('error-state');clearResults();$('trueOffset').textContent='星历加载失败';}}
 }
 async function checkUpdate(){
  if(!runtime)return;
  try{const next=await getJSON('data/runtime.json');if(next.eop_sha256!==runtime.eop_sha256)await boot(next);else{runtime=next;updateInfo();}}
  catch{$('updateStatus').textContent='检查更新暂时失败，继续使用已载入的 '+runtime.release+' 快照。';}
 }
 setNow();render();boot();setInterval(()=>{if(live){setNow();render();}},1000);
 setInterval(checkUpdate,300000);document.addEventListener('visibilitychange',()=>{if(!document.hidden)checkUpdate();});
})();
