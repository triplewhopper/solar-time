const assert=require('node:assert/strict'),fs=require('fs'),path=require('path'),{toDMS,bind}=require('../location-input.js');
function setup(provider,toElevation=async h=>h-36){
 const fields=Object.fromEntries(['lonD','lonM','lonS','lonH','latD','latM','latS','latH','height'].map(id=>[id,{value:id==='height'?'123':'old'}]));
 const status={textContent:''},button={disabled:false,textContent:'使用当前位置',addEventListener:(event,fn)=>{button.click=fn;}};let calculated=0;
 const control=bind({button,status,field:id=>fields[id],onFilled:()=>{if(fields.height.value!=='')calculated++;},toElevation,geolocation:()=>provider});return {fields,status,button,control,calculated:()=>calculated};
}
(async()=>{
 let calls=0,success,failure,options;const ui=setup({getCurrentPosition:(a,b,o)=>{calls++;success=a;failure=b;options=o;}});
 assert.equal(calls,0);ui.button.click();ui.button.click();assert.equal(calls,1);assert.equal(ui.button.disabled,true);assert.equal(ui.fields.height.value,'');assert.equal(ui.calculated(),0);
 assert.deepEqual(options,{enableHighAccuracy:true,timeout:15000,maximumAge:0});
 await success({coords:{latitude:-35.5,longitude:-139.75,accuracy:12.1,altitude:null,altitudeAccuracy:null}});
 assert.equal(ui.fields.lonD.value,'139');assert.equal(ui.fields.lonM.value,'45');assert.equal(ui.fields.lonH.value,'-1');assert.equal(ui.fields.latD.value,'35');assert.equal(ui.fields.latM.value,'30');assert.equal(ui.fields.height.value,'');assert.equal(ui.calculated(),0);assert.match(ui.status.textContent,/未取得海拔/);
 for(const altitude of [undefined,null,NaN,Infinity]){ui.button.click();await success({coords:{latitude:1,longitude:2,accuracy:10,altitude,altitudeAccuracy:5}});assert.equal(ui.fields.height.value,'');assert.equal(ui.calculated(),0);}
 for(const altitudeAccuracy of [undefined,null,NaN,-1]){ui.button.click();await success({coords:{latitude:1,longitude:2,altitude:100,altitudeAccuracy}});assert.equal(ui.fields.height.value,'');}
 ui.button.click();await success({coords:{latitude:1,longitude:2,altitude:100,altitudeAccuracy:5}});assert.equal(ui.fields.height.value,'64');assert.equal(ui.calculated(),1);
 ui.button.click();await success({coords:{latitude:1,longitude:2,altitude:0,altitudeAccuracy:0}});assert.equal(ui.fields.height.value,'-36');assert.equal(ui.calculated(),2);
 for(const code of [1,2,3]){ui.button.click();failure({code});assert.equal(ui.button.disabled,false);assert.equal(ui.fields.height.value,'');assert.equal(ui.calculated(),2);}
 ui.button.click();ui.control.cancel();ui.fields.lonD.value='42';await success({coords:{latitude:1,longitude:2,altitude:100,altitudeAccuracy:5}});assert.equal(ui.fields.lonD.value,'42');
 let callback,resolve;const delayed=setup({getCurrentPosition:cb=>{callback=cb;}},()=>new Promise(r=>{resolve=r;}));delayed.button.click();const waiting=callback({coords:{latitude:1,longitude:2,altitude:100,altitudeAccuracy:5}});delayed.control.cancel();delayed.fields.height.value='77';resolve(64);await waiting;assert.equal(delayed.fields.height.value,'77');assert.equal(delayed.calculated(),0);
 const unsupported=setup(null);unsupported.button.click();assert.match(unsupported.status.textContent,/无法定位/);assert.equal(unsupported.fields.height.value,'');
 assert.deepEqual(toDMS(12+59/60+59.9999999/3600,180),[13,0,0,1]);assert.deepEqual(toDMS(-180,180),[180,0,0,-1]);
 for(const value of [NaN,Infinity,181])assert.throws(()=>toDMS(value,180));
 const html=fs.readFileSync(path.join(__dirname,'../index.html'),'utf8'),field=html.match(/<input id="height"[^>]+>/)[0];assert.ok(!field.includes('value="0"'));
 console.log('Missing/invalid altitude blocks calculation; real zero altitude, conversion, errors and stale async results passed.');
})().catch(e=>{console.error(e);process.exitCode=1;});
