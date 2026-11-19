const fs=require('fs'),path=require('path'),zlib=require('zlib'),vm=require('vm'),assert=require('node:assert/strict'),crypto=require('crypto');
const root=path.resolve(__dirname,'..'),Geoid=require('../geoid.js'),read=p=>fs.readFileSync(path.join(root,p));
const packed=read('data/egm2008-5.pgm.gz'),raw=zlib.gunzipSync(packed),metadata=JSON.parse(read('data/geoid.json'));
assert.equal(crypto.createHash('sha256').update(raw).digest('hex'),metadata.pgm_sha256);
const geoid=new Geoid(raw.buffer.slice(raw.byteOffset,raw.byteOffset+raw.length));
let max=0;const ref=JSON.parse(read('tests/geoid-reference.json'));
for(const [lat,lon,n]of ref.points){const actual=geoid.undulation(lat,lon);max=Math.max(max,Math.abs(actual-n));assert.ok(Math.abs(actual-n)<1e-9);assert.ok(Math.abs(actual-geoid.undulation(lat,lon+360))<1e-9);}
for(const lat of [-90,-89.999999,0,35,89.999999,90])assert.equal(geoid.undulation(lat,-180),geoid.undulation(lat,180));
for(const elevation of [-1000,0,100,100000])for(const [lat,lon]of ref.points){const r=geoid.toEllipsoid(elevation,lat,lon);assert.ok(Math.abs(r.height-r.geoidUndulation-elevation)<2e-11);}
for(const h of [NaN,Infinity,-1000.01,100000.01])assert.throws(()=>geoid.toEllipsoid(h,0,0));
for(const lat of [NaN,Infinity,-90.1,90.1])assert.throws(()=>geoid.undulation(lat,0));
assert.throws(()=>new Geoid(new ArrayBuffer(0)));
const c={};vm.createContext(c);for(const file of ['vendor/erfa.min.js','solar-core.js'])vm.runInContext(read(file).toString(),c);
const b=read('data/de441-solar.bsp'),engine=new c.SolarPrecision.Engine(b.buffer.slice(b.byteOffset,b.byteOffset+b.length),JSON.parse(read('data/eop.json')),c.ERFA);
let cases=0;for(const [latitude,longitude]of ref.points.filter(p=>Math.abs(p[0])<90).slice(0,100))for(const elevation of [-1000,0,100,100000]){
 const converted=geoid.toEllipsoid(elevation,latitude,longitude),input={ms:Date.UTC(2026,10,19),latitude,longitude};
 const result=engine.calculate({...input,...converted});assert.ok(Number.isFinite(result.solar));
 if(converted.height>=-1000&&converted.height<=100000)assert.equal(result.solar,engine.calculate({...input,height:converted.height}).solar);cases++;
}
assert.throws(()=>engine.calculate({ms:Date.UTC(2026,10,19),latitude:35,longitude:135,height:0,geoidUndulation:201}));
const html=read('index.html').toString();assert.ok(html.includes('海拔（米）'));assert.ok(!html.includes('椭球高'));
console.log({reference_points:ref.points.length,max_grid_difference_m:max,solar_conversion_cases:cases,tokyo_geoid_m:geoid.undulation(35.68,139.76)});
