/* Frozen inputs for historical reference outputs. Live updates cannot alter this pairing. */
const fs=require('fs'),path=require('path'),zlib=require('zlib'),crypto=require('crypto');
module.exports=()=>{
 if(process.env.SOLAR_TEST_DATA)return JSON.parse(fs.readFileSync(process.env.SOLAR_TEST_DATA));
 const dir=path.join(__dirname,'snapshots/2026-11-18'),manifest=JSON.parse(fs.readFileSync(path.join(dir,'manifest.json')));
 const bytes=zlib.gunzipSync(fs.readFileSync(path.join(dir,'eop.json.gz')));
 if(crypto.createHash('sha256').update(bytes).digest('hex')!==manifest.eop_sha256)throw Error('Frozen EOP checksum mismatch');
 const ref=fs.readFileSync(path.join(__dirname,'domain-horizons.json'));
 if(crypto.createHash('sha256').update(ref).digest('hex')!==manifest.horizons_reference_sha256)throw Error('Frozen Horizons checksum mismatch');
 return JSON.parse(bytes);
};
