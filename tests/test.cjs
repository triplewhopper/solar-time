const fs=require('fs'),vm=require('vm'),assert=require('node:assert/strict'),path=require('path');
const root=path.resolve(__dirname,'..'),read=p=>fs.readFileSync(path.join(root,p));
const c={console};vm.createContext(c);for(const file of ['vendor/erfa.min.js','solar-core.js'])vm.runInContext(read(file).toString(),c);
const b=read('data/de441-solar.bsp'),data=require('./snapshot.cjs')(),M=c.SolarPrecision,engine=new M.Engine(b.buffer.slice(b.byteOffset,b.byteOffset+b.length),data,c.ERFA);
const calculate=engine.calculate.bind(engine);engine.calculate=o=>calculate({...o,source:'iers'});
const reference=JSON.parse(read('tests/horizons-reference.json')),native=JSON.parse(read('tests/native-reference.json'));
const difference=(a,b)=>((a-b+43200)%86400+86400)%86400-43200;
let maxNative=0,maxPosition=0,maxVelocity=0;
const comparisons=reference.fixtures.map((f,i)=>{
 const ms=Date.parse(f.utc),r=engine.calculate({ms,longitude:f.longitude_deg,latitude:f.latitude_deg,height:f.height_km*1000});
 const err=difference(r.solar,f.solar_seconds)*1000;
 maxNative=Math.max(maxNative,Math.abs(difference(r.solar,native.fixtures[i].solar_seconds)*1000));
 const earth=engine.spk.earth(native.fixtures[i].tdb_days);
 for(let k=0;k<3;k++){maxPosition=Math.max(maxPosition,Math.abs(earth[0][k]-native.fixtures[i].earth_position_km[k]));maxVelocity=Math.max(maxVelocity,Math.abs(earth[1][k]*86400-native.fixtures[i].earth_velocity_km_day[k]));}
 assert.ok(Math.abs(err)<5,`Horizons discrepancy >5ms: ${f.utc},site${f.site_index}: ${err}`);
 assert.ok(Number.isFinite(r.true));assert.ok(Math.abs(r.eot)<1200);
 return {utc:f.utc,longitude:f.longitude_deg,latitude:f.latitude_deg,height_m:f.height_km*1000,local_solar_seconds:r.solar,horizons_solar_seconds:f.solar_seconds,error_ms:err,eop_status:r.eop.status};
});
assert.ok(maxNative<0.01,`JS/native mismatch ${maxNative}ms`);
assert.ok(maxPosition<1e-5,`SPK position mismatch ${maxPosition}km`);
assert.ok(maxVelocity<1e-5,`SPK velocity mismatch ${maxVelocity}km/day`);
assert.equal(M.dms(139,45,30,1,180),139.75833333333333);
assert.equal(M.dms(0,0,1,-1,180),-1/3600);
for(const args of [[180,0,1,1,180],[90,1,0,1,90],[135,60,0,1,180],[135,0,60,1,180],[135.5,0,0,1,180],[-1,0,0,1,180]])assert.throws(()=>M.dms(...args));
assert.equal(new Date(M.parseJST('2026-11-19','12:00:00.123')).toISOString(),'2026-11-19T03:00:00.123Z');
assert.throws(()=>M.parseJST('2025-02-29','12:00:00'));assert.throws(()=>M.parseJST('2026-11-19','24:00:00'));assert.doesNotThrow(()=>M.parseJST('2024-02-29','12:00:00'));
assert.throws(()=>engine.calculate({ms:Date.parse('2090-01-01'),longitude:135,latitude:35,height:0}));
assert.throws(()=>engine.calculate({ms:Date.parse('2024-01-01'),longitude:135,latitude:90,height:0}));
for(const lon of [-180,180,0]){const ms=Date.parse('2024-01-01T00:00:00Z'),r=engine.calculate({ms,longitude:lon,latitude:35});assert.ok(Math.abs(r.true-r.mean)<1200);}
const before=engine.calculate({ms:Date.parse('2016-12-31T23:59:59Z'),longitude:0,latitude:0});
const after=engine.calculate({ms:Date.parse('2017-01-01T00:00:00Z'),longitude:0,latitude:0});
assert.ok(Math.abs(difference(after.solar,before.solar)-2)<0.002,'Leap second must advance apparent solar time by two SI seconds');
const atNoon=engine.eop(Date.parse('2016-12-31T12:00:00Z'));assert.ok(Math.abs(atNoon.dut1+0.408)<0.01,'DUT1 interpolation must not smear leap jump');
const max=Math.max(...comparisons.map(r=>Math.abs(r.error_ms))),rms=Math.sqrt(comparisons.reduce((s,r)=>s+r.error_ms**2,0)/comparisons.length);
const report={generated:new Date().toISOString(),model:'JPL DE441 + ERFA IAU2006/2000A + IERS EOP; airless topocentric Sun center',horizons:{cases:comparisons.length,max_abs_ms:max,rms_ms:rms,reference_date:reference.fetched_utc,eop_file:reference.sites[0].eop_file},native:{cases:comparisons.length,max_abs_ms:maxNative,max_position_error_km:maxPosition,max_velocity_error_km_day:maxVelocity},limits:['Validation applies only to the listed synthetic sites and dates; not a certified global accuracy bound.','Horizons uses its own EOP fit and IAU1976/1980 orientation; these differ from this implementation.','IERS predictions, missing dX/dY, input coordinate errors, system clock error, future leap seconds and geophysical deformation add uncertainty.','UTC leap-second instants 23:59:60 are not accepted by the browser time input.'],comparisons};
fs.writeFileSync(path.join(root,'tests/legacy-validation.json'),JSON.stringify(report,null,2));
console.log(JSON.stringify({horizons:report.horizons,native:report.native,unit_checks:'passed'},null,2));
