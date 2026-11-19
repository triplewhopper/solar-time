/* Offline replay: native oracle + cached Horizons. Never calls a service. */
const fs=require('fs'),vm=require('vm'),assert=require('node:assert/strict'),path=require('path'),zlib=require('zlib');
const root=path.resolve(__dirname,'..'),read=p=>fs.readFileSync(path.join(root,p)),c={};vm.createContext(c);
for(const f of ['vendor/erfa.min.js','solar-core.js'])vm.runInContext(read(f).toString(),c);
const b=read('data/de441-solar.bsp'),data=JSON.parse(read('data/eop.json')),M=c.SolarPrecision,engine=new M.Engine(b.buffer.slice(b.byteOffset,b.byteOffset+b.length),data,c.ERFA);
const wrap=(a,b)=>((a-b+43200)%86400+86400)%86400-43200;
const native=JSON.parse(zlib.gunzipSync(read('tests/native-domain.json.gz')));
let nativeMax=0,nativeWorst=null;const counts={};
for(const r of native.rows){const [ms,longitude,latitude,height,dut1,xp,yp,dx,dy,tai,solar,stratum]=r;
 const out=engine.calculate({ms,longitude,latitude,height,manual:{dut1,xp,yp,dx,dy,tai},source:'jpl'}),error=Math.abs(wrap(out.solar,solar))*1000;
 assert.ok(Number.isFinite(error));if(error>nativeMax){nativeMax=error;nativeWorst={ms,longitude,latitude,height,stratum,error_ms:error};}counts[stratum]=(counts[stratum]||0)+1;
}
assert.ok(nativeMax<0.01,'Native ERFA agreement exceeds 10 microseconds: '+nativeMax+'ms');
console.log('Native oracle',native.rows.length,'cases; max difference',nativeMax,'ms');
const ref=JSON.parse(read('tests/domain-horizons.json')),errors=[];
for(const group of ref.results){const s=group.site;for(const row of group.rows){const [ms,solar,dut1]=row;const out=engine.calculate({ms,longitude:s.lon,latitude:s.lat,height:s.height,extrapolate:true});
 errors.push({ms,longitude:s.lon,latitude:s.lat,height:s.height,stratum:s.stratum,error_ms:wrap(out.solar,solar)*1000,dut1_difference_ms:(out.dut1-dut1)*1000,eop_status:out.eop.status,condition:out.meridianCondition});
}console.log('Horizons replay site',s.id+1,'/',ref.results.length);}
function stats(a){const sorted=a.map(r=>Math.abs(r.error_ms)).sort((a,b)=>a-b);return {count:a.length,max_abs_ms:sorted.at(-1),p50_ms:sorted[Math.floor(sorted.length*.5)],p95_ms:sorted[Math.floor(sorted.length*.95)],p99_ms:sorted[Math.floor(sorted.length*.99)],rms_ms:Math.sqrt(a.reduce((s,r)=>s+r.error_ms**2,0)/a.length),worst:a.reduce((a,b)=>Math.abs(a.error_ms)>Math.abs(b.error_ms)?a:b)};}
const groups={all:stats(errors),historical_all:stats(errors.filter(r=>r.ms<Date.UTC(2026,10,1))),historical_polar:stats(errors.filter(r=>r.ms<Date.UTC(2026,10,1)&&Math.abs(r.latitude)>85)),recent_all:stats(errors.filter(r=>r.ms>=Date.UTC(2026,10,1))),nonpolar:stats(errors.filter(r=>Math.abs(r.latitude)<=85)),polar:stats(errors.filter(r=>Math.abs(r.latitude)>85)),observed_nonpolar:stats(errors.filter(r=>Math.abs(r.latitude)<=85&&r.eop_status==='R')),predicted_nonpolar:stats(errors.filter(r=>Math.abs(r.latitude)<=85&&r.eop_status==='RP')),extrapolated_nonpolar:stats(errors.filter(r=>Math.abs(r.latitude)<=85&&r.eop_status==='RX')),holdout:stats(errors.filter(r=>r.stratum==='holdout'))};
// Validation boundaries and invariants. Extrapolation is explicit, not silent.
let checks=0;const ok=(condition,msg)=>{assert.ok(condition,msg);checks++},throws=(fn)=>{assert.throws(fn);checks++};
const normal={ms:Date.parse('2024-01-01T00:00:00Z'),longitude:135,latitude:35,height:0};
for(const field of ['ms','longitude','latitude','height'])for(const val of [NaN,Infinity,-Infinity])throws(()=>engine.calculate({...normal,[field]:val}));
for(const lon of [-180.000001,180.000001])throws(()=>engine.calculate({...normal,longitude:lon}));
for(const lat of [-90,90,-90.000001,90.000001])throws(()=>engine.calculate({...normal,latitude:lat}));
for(const height of [-1000.0001,100000.0001])throws(()=>engine.calculate({...normal,height}));
for(const height of [-1000,100000])ok(Number.isFinite(engine.calculate({...normal,height}).solar));
const manual=engine.eop(normal.ms);
for(const [key,values] of Object.entries({dut1:[-10.0001,10.0001],xp:[-10.0001,10.0001],yp:[-10.0001,10.0001],dx:[-1000.0001,1000.0001],dy:[-1000.0001,1000.0001],tai:[9,101,37.5,NaN]}))for(const value of values)throws(()=>engine.calculate({...normal,manual:{...manual,[key]:value}}));
for(const args of [[180,0,1,1,180],[90,1,0,1,90],[1,60,0,1,180],[1,0,60,1,180],[1.1,0,0,1,180],[1,1.5,0,1,180],[1,0,0,0,180]])throws(()=>M.dms(...args));
ok(M.dms(180,0,0,1,180)===180);ok(M.dms(0,0,1,-1,180)===-1/3600);
throws(()=>M.parseJST('2025-02-29','12:00:00'));throws(()=>M.parseJST('2024-01-01','23:59:60'));throws(()=>M.parseJST('2024-01-01','24:00:00'));
ok(new Date(M.parseJST('2024-01-01','09:00:00.123')).toISOString()==='2024-01-01T00:00:00.123Z');
for(const ms of [Date.UTC(1972,0,1,0,14,59,999),Date.UTC(2099,11,31,15)])throws(()=>engine.calculate({...normal,ms,extrapolate:true}));
for(const ms of [Date.UTC(1972,0,1,0,15),Date.UTC(2099,11,31,14,59,59,999)])ok(Number.isFinite(engine.calculate({...normal,ms,extrapolate:true}).solar));
throws(()=>engine.calculate({...normal,ms:Date.parse('2090-01-01')}));ok(engine.calculate({...normal,ms:Date.parse('2090-01-01'),extrapolate:true}).eop.extrapolated);
for(const lat of [-89.999999,-85,0,85,89.999999]){const a=engine.calculate({...normal,latitude:lat,longitude:-180}),b=engine.calculate({...normal,latitude:lat,longitude:180});ok(Math.abs(wrap(a.solar,b.solar))<1e-5,'±180 physical longitude equivalence');ok(Math.abs((b.true-a.true)-86400)<1e-5,'unwrapped date-label convention');}
let leapChecks=0;for(const [epoch] of data.leaps){if(epoch<Date.parse('1973-01-02'))continue;const a=engine.calculate({...normal,ms:epoch-1000}),b=engine.calculate({...normal,ms:epoch});ok(Math.abs(wrap(b.solar,a.solar)-2)<.002,'Leap-step advance');leapChecks++;}
ok(engine.calculate({...normal,latitude:89.999999}).polarSensitive,'Polar warning');
const report={generated:new Date().toISOString(),model:'DE441 + IAU1976/1980 + independently PCK-reconstructed Nov18-equivalent EOP tail, original Nov17 historical baseline; seven-point blend; no fitted offsets',scope:'Stratified, random, daily, boundary and stress coverage of every declared input dimension; not exhaustive proof over continuous inputs',horizons:{cases:errors.length,sites:ref.results.length,times_per_site:ref.results[0].rows.length,reference_eop_files:[...new Set(ref.metadata.map(r=>r.eop_file))],...groups},native:{cases:native.rows.length,max_abs_ms:nativeMax,worst:nativeWorst,strata:counts},boundaries:{checks,leap_events:leapChecks},domain:{longitude:[-180,180],latitude_open:[-90,90],height_m:[-1000,100000],jst_start:'1972-01-01T09:15:00+09:00',jst_end:'2099-12-31T23:59:59.999+09:00',automatic_data:'intersection with selected JPL/IERS snapshot; outside stops unless manual or explicit fixed-value extrapolation',manual_ranges:{dut1_seconds:[-10,10],xp_yp_arcseconds:[-10,10],dX_dY_mas:[-1000,1000],TAI_minus_UTC_integer_seconds:[10,100]}},limits:['Historical holdout comparison is microsecond-level including near poles; near-pole predicted/extrapolated comparisons across different EOP releases can still differ by minutes.','Future fixed-EOP results are model extrapolations, not predictions with guaranteed accuracy.','The exact original Nov18 ASCII file is not obtained. The changed137dailyrecords are reconstructed from officialNov18PCK withoutHorizonsfit, then independently validated. Historical baseline isoriginalNov17.','Native agreement checks implementation consistency, not absolute physical truth.']};
fs.writeFileSync(path.join(root,'data/validation.json'),JSON.stringify(report,null,2));fs.writeFileSync(path.join(root,'tests/domain-errors.json.gz'),zlib.gzipSync(JSON.stringify(errors)));
console.log(JSON.stringify({native:report.native,horizons:{count:errors.length,global:groups.all.max_abs_ms,nonpolar:groups.nonpolar.max_abs_ms},boundaries:report.boundaries},null,2));
