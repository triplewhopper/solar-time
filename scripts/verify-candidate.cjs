/* Independent live-data gate. Does not overwrite the frozen regression report. */
const fs=require('fs'),vm=require('vm'),path=require('path'),zlib=require('zlib'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'..'),dir=path.resolve(process.argv[2]),read=p=>fs.readFileSync(p),c={};vm.createContext(c);
for(const name of ['vendor/erfa.min.js','solar-core.js'])vm.runInContext(read(path.join(root,name)).toString(),c);
const data=JSON.parse(read(path.join(dir,'candidate.json'))),b=read(path.join(root,'data/de441-solar.bsp'));
const engine=new c.SolarPrecision.Engine(b.buffer.slice(b.byteOffset,b.byteOffset+b.length),data,c.ERFA);
const wrap=(a,b)=>((a-b+43200)%86400+86400)%86400-43200;
const base=JSON.parse(zlib.gunzipSync(read(path.join(root,'tests/native-domain.json.gz'))));
const native=JSON.parse(zlib.gunzipSync(read(path.join(dir,'native.json.gz'))));
assert.equal(native.source_sha256,data.reconstructed.source_sha256);assert.equal(base.rows.length,native.rows.length);
let nativeMax=0,horizonsMax=0,horizonsCount=0,worst=null;
for(let i=0;i<base.rows.length;i++){
 const [ms,longitude,latitude,height]=base.rows[i],r=native.rows[i];
 const manual=base.rows[i][11]==='manual-stress'?{dut1:r[0],xp:r[1],yp:r[2],dx:r[3],dy:r[4],tai:r[5]}:null;
 const out=engine.calculate({ms,longitude,latitude,height,manual,extrapolate:true});
 nativeMax=Math.max(nativeMax,Math.abs(wrap(out.solar,r[6]))*1e6);
}
assert.ok(nativeMax<10,`Native mismatch ${nativeMax} us`);
const ref=JSON.parse(read(path.join(dir,'horizons.json')));
assert.equal(ref.eop_file,data.reconstructed.horizons_eop_file);
for(const group of ref.groups)for(const [ms,expected]of group.rows){
 const out=engine.calculate({ms,...group.site,extrapolate:true}),error=Math.abs(wrap(out.solar,expected))*1e6;
 assert.ok(Number.isFinite(error));horizonsCount++;if(error>horizonsMax){horizonsMax=error;worst={ms,...group.site,error_us:error};}
}
assert.ok(horizonsCount>=500,'Insufficient fresh Horizons cases');
assert.ok(horizonsMax<10,`Same-version Horizons mismatch ${horizonsMax} us`);
const end=(data.reconstructed.evaluation_end_mjd-40587)*86400000;
assert.throws(()=>engine.calculate({ms:end+1,longitude:0,latitude:0}));
const result={source_sha256:data.reconstructed.source_sha256,horizons_eop_file:ref.eop_file,native_cases:base.rows.length,native_max_us:nativeMax,horizons_cases:horizonsCount,horizons_max_us:horizonsMax,worst,threshold_us:10,scope:'Daily recovery interval, fresh boundary/polar probes and independent full-domain native checks; not exhaustive continuous-domain proof'};
fs.writeFileSync(path.join(dir,'verification.json'),JSON.stringify(result,null,2)+'\n');console.log(result);
