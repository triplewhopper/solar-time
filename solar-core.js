/* Local DE441 + ERFA solar-time calculation. No network calls in this module.
 * Units: SPK km/km-second; ERFA au/au-day, radians, meters; output seconds.
 * Earth orientation: IAU2006/2000A + IERS dX/dY, WGS84, airless solar center.
 */
(function(root){
'use strict';
const AU=149597870.7, C=299792.458, DAY=86400, J2000=2451545, J2000MS=946728000000;
const AS=Math.PI/(180*3600),rad=x=>x*Math.PI/180,mod=(x,n)=>((x%n)+n)%n;
const add=(a,b)=>a.map((v,i)=>v+b[i]),sub=(a,b)=>a.map((v,i)=>v-b[i]),scale=(a,k)=>a.map(v=>v*k);
class SPK {
 constructor(buffer){
  this.view=new DataView(buffer);this.little=true;this.segments=[];
  const text=(a,n)=>String.fromCharCode(...new Uint8Array(buffer,a,n));
  if(text(0,7)!=='DAF/SPK')throw Error('星历文件格式错误。');
  const format=text(88,8);if(format==='BIG-IEEE')this.little=false;else if(format!=='LTL-IEEE')throw Error('不支持此星历字节序。');
  const i=a=>this.view.getInt32(a,this.little),d=a=>this.view.getFloat64(a,this.little);
  if(i(8)!==2||i(12)!==6)throw Error('SPK 摘要格式不受支持。');
  let record=i(76),guard=0;
  while(record){
   if(++guard>10000)throw Error('SPK 摘要损坏。');
   const offset=(record-1)*1024,next=d(offset),count=d(offset+16);
   for(let n=0;n<count;n++){
    const a=offset+24+n*40,target=i(a+16),center=i(a+20),frame=i(a+24),type=i(a+28),start=i(a+32),end=i(a+36);
    if(frame!==1||type!==2)throw Error('只支持 J2000、SPK Type 2 星历。');
    const trailer=(end-4)*8,init=d(trailer),interval=d(trailer+8),rsize=d(trailer+16),records=d(trailer+24);
    this.segments.push({target,center,start,end,from:d(a),to:d(a+8),init,interval,rsize,records,degree:(rsize-2)/3});
   }
   record=next;
  }
 }
 state(center,target,tdbDays){
  const seconds=tdbDays*DAY,s=this.segments.find(s=>s.center===center&&s.target===target&&seconds>=s.from&&seconds<=s.to);
  if(!s)throw Error('日期超出内置 DE441 星历范围（1972–2099）。');
  const index=Math.min(s.records-1,Math.floor((seconds-s.init)/s.interval));
  const offset=(s.start-1+index*s.rsize)*8,d=a=>this.view.getFloat64(a,this.little);
  const middle=d(offset),radius=d(offset+8),x=(seconds-middle)/radius;
  const p=[],v=[];
  for(let axis=0;axis<3;axis++){
   const base=offset+16+axis*s.degree*8;
   let t0=1,t1=x,dt0=0,dt1=1,value=d(base),derivative=0;
   if(s.degree>1){value+=d(base+8)*t1;derivative+=d(base+8);}
   for(let k=2;k<s.degree;k++){const t=2*x*t1-t0,dt=2*t1+2*x*dt1-dt0,c=d(base+k*8);value+=c*t;derivative+=c*dt;t0=t1;t1=t;dt0=dt1;dt1=dt;}
   p.push(value);v.push(derivative/radius);
  }
  return [p,v];
 }
 earth(t){const a=this.state(0,3,t),b=this.state(3,399,t);return [add(a[0],b[0]),add(a[1],b[1])];}
}
function dms(d,m,s,h,max){
 if(![d,m,s,h].every(Number.isFinite)||!Number.isInteger(d)||!Number.isInteger(m)||d<0||d>max||m<0||m>=60||s<0||s>=60||![1,-1].includes(h)||(d===max&&(m!==0||s!==0)))throw Error('度分秒超出范围。');
 return h*(d+m/60+s/3600);
}
class Engine {
 constructor(buffer,data,erfa){this.spk=new SPK(buffer);this.data=data;this.erfa=erfa;}
 tai(ms){let out=null;for(const [epoch,n] of this.data.leaps){if(ms>=epoch)out=n;else break;}if(out===null)throw Error('支持 1972 年起的 UTC 日期。');return out;}
 eop(ms,manual,source='jpl',extrapolate=false){
  if(manual){for(const key of ['dut1','xp','yp','dx','dy','tai'])if(!Number.isFinite(manual[key]))throw Error('请完整填写手动地球自转参数。');if(Math.abs(manual.dut1)>10||Math.abs(manual.xp)>10||Math.abs(manual.yp)>10||Math.abs(manual.dx)>1000||Math.abs(manual.dy)>1000||!Number.isInteger(manual.tai)||manual.tai<10||manual.tai>100)throw Error('手动修正参数超出允许范围。');return {...manual,status:'manual',missingCIP:false};}
  if(source==='jpl'){
   const j=this.data.jpl;if(!j)throw Error('未加载 JPL 地球自转数据。');
   const tai=this.tai(ms),mjd=ms/86400000+40587+tai/DAY,rows=j.rows,first=rows[0][0],last=rows.at(-1)[0];
   const outside=mjd<first||mjd>last;
   if(outside&&!extrapolate)throw Error('日期超出 JPL 修正数据范围。请选择 IERS 数据、输入手动参数，或明确启用固定末值外推。');
   let i=Math.max(0,Math.min(rows.length-2,Math.floor(mjd-first))),a=rows[i],b=rows[i+1],f=Math.max(0,Math.min(1,(mjd-a[0])/(b[0]-a[0]))),v=k=>a[k]+(b[k]-a[k])*f;
   return {tai,dut1:tai-v(3)/1000,xp:v(1)/1000,yp:v(2)/1000,dx:v(4),dy:v(5),status:outside?'JX':ms>Date.parse(j.last_cip_data_utc)||ms>Date.parse(j.last_utpm_data_utc)?'JP':'J',missingCIP:false,error:v(8)/1000,extrapolated:outside};
  }
  if(source!=='iers')throw Error('未知地球自转数据来源。');
  const mjd=ms/86400000+40587,rows=this.data.rows,n=Math.floor(mjd),first=rows[0][0],i=n-first;
  if(i<0||i>=rows.length-1||rows[i][0]!==n)throw Error('所选日期没有内置 IERS 数据。请导入更新数据，或在高级设置中填写修正参数。');
  const a=rows[i],b=rows[i+1],f=mjd-n,inter=(k)=>a[k]+(b[k]-a[k])*f;
  const ta=this.tai((a[0]-40587)*86400000),tb=this.tai((b[0]-40587)*86400000),tai=this.tai(ms);
  // Interpolate UT1-TAI, not discontinuous UT1-UTC, across leap seconds.
  const dut1=(a[3]-ta)*(1-f)+(b[3]-tb)*f+tai;
  const missingCIP=[a[4],a[5],b[4],b[5]].some(v=>v===null);
  return {dut1,xp:inter(1),yp:inter(2),dx:missingCIP?0:inter(4),dy:missingCIP?0:inter(5),tai,
   status:a[6]==='P'||b[6]==='P'?'P':a[6]==='B'&&b[6]==='B'?'B':'A',missingCIP,error:Math.max(a[7]||0,b[7]||0)};
 }
 calculate({ms,longitude,latitude,height=0,manual=null,source='jpl',extrapolate=false}){
  if(!Number.isFinite(ms)||!Number.isFinite(longitude)||Math.abs(longitude)>180||!Number.isFinite(latitude)||Math.abs(latitude)>=90||!Number.isFinite(height)||height< -1000||height>100000)throw Error('请输入有效位置；纬度须在南北极之间，高度范围 −1000 至 100000 米。');
  if(ms<Date.UTC(1972,0,1,0,15)||ms>Date.UTC(2099,11,31,14,59,59,999))throw Error('计算范围（东九区）：1972-01-01 09:15:00 至 2099-12-31 23:59:59.999。首日预留太阳光行时。');
  const erfa=this.erfa,eop=this.eop(ms,manual,source,extrapolate),utc=(ms-J2000MS)/86400000,tt=utc+(eop.tai+32.184)/DAY,ut1=utc+eop.dut1/DAY;
  const lon=rad(longitude),lat=rad(latitude),gc=erfa.gd2gc(1,lon,lat,height);
  if(gc[0]!==0)throw Error('坐标转换失败。');
  const xyz=gc[1],dtr=erfa.dtdb(J2000,tt,mod(ms/86400000+eop.dut1/DAY,1),lon,Math.hypot(xyz[0],xyz[1])/1000,xyz[2]/1000),tdb=tt+dtr/DAY;
  const earth=this.spk.earth(tdb),sun=this.spk.state(0,10,tdb),ebpv=[scale(earth[0],1/AU),scale(earth[1],DAY/AU)],ehp=scale(sub(earth[0],sun[0]),1/AU);
  let [x,y,s]=erfa.xys06a(J2000,tt);x+=eop.dx*AS/1000;y+=eop.dy*AS/1000;s=erfa.s06(J2000,tt,x,y);
  const theta=erfa.era00(J2000,ut1),sp=erfa.sp00(J2000,tt);
  const astrom=erfa.apco(J2000,tdb,ebpv,ehp,x,y,s,theta,lon,lat,height,eop.xp*AS,eop.yp*AS,sp,0,0);
  let lt=0,vector;
  for(let k=0;k<5;k++){vector=sub(scale(this.spk.state(0,10,tdb-lt/DAY)[0],1/AU),astrom.eb);lt=Math.hypot(...vector)*AU/C;}
  const unit=scale(vector,1/Math.hypot(...vector)),aberrated=erfa.ab(unit,astrom.v,astrom.em,astrom.bm1),cirs=erfa.rxp(astrom.bpn,aberrated),[ra,dec]=erfa.c2s(cirs);
  // Horizons Q34/Q42 use the meridian about the celestial pole of date.
  // atioq's polar-motion-rotated observed HA is a different convention.
  const station=erfa.pvtob(lon,lat,height,eop.xp*AS,eop.yp*AS,sp,theta)[0];
  const hourAngle=erfa.anpm(Math.atan2(station[1],station[0])-ra),solar=mod(43200+hourAngle*43200/Math.PI,DAY);
  const jst=mod(ms/1000+32400,DAY),longitudeOffset=(longitude-135)*240,mean=longitudeOffset+eop.dut1;
  let offset=solar-jst;offset+=DAY*Math.round((mean-offset)/DAY);
  const meridianCondition=6378137/Math.hypot(station[0],station[1]);
  return {true:offset,mean,eot:offset-mean,longitudeOffset,dut1:eop.dut1,solar,hourAngle,eop,lightTime:lt,tdbMinusTT:dtr,ttDays:tt,tdbDays:tdb,cirsRA:ra,cirsDec:dec,meridianCondition,polarSensitive:Math.abs(latitude)>85};
 }
}
function parseJST(date,time){
 if(!/^\d{4}-\d{2}-\d{2}$/.test(date)||!/^\d{2}:\d{2}(:\d{2}(\.\d{1,3})?)?$/.test(time))throw Error('请填写完整日期与时间。');
 const [y,mo,d]=date.split('-').map(Number),[h,m,s=0]=time.split(':').map(Number),ms=Date.UTC(y,mo-1,d,h,m,Math.floor(s),Math.round((s%1)*1000))-32400000;
 if(y<1972||y>2099||h>23||m>59||s>=60||new Date(ms+32400000).toISOString().slice(0,10)!==date)throw Error('日期范围为 1972–2099；闰秒 23:59:60 请使用前后相邻时刻。');
 return ms;
}
function clock(ms){const iso=new Date(Math.round(ms)).toISOString();return {date:iso.slice(0,10),time:iso.slice(11,23)};}
function duration(s,words=false){let n=Math.round(Math.abs(s)*1000),h=Math.floor(n/3600000),m=Math.floor(n%3600000/60000),sec=(n%60000/1000).toFixed(3).padStart(6,'0');return (n===0?(words?'相同':''):(words?(s>0?'快 ':'慢 '):(s>0?'+':'−')))+(n===0&&words?'':(h?h+'小时 ':'')+m+'分 '+sec+'秒');}
root.SolarPrecision={Engine,SPK,dms,parseJST,clock,duration};
})(typeof globalThis!=='undefined'?globalThis:this);
