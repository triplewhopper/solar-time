const assert=require('node:assert/strict'),{toDMS,bind}=require('../location-input.js');
function setup(provider){
 const fields=Object.fromEntries(['lonD','lonM','lonS','lonH','latD','latM','latS','latH','height'].map(id=>[id,{value:id==='height'?'123':'old'}]));
 const status={textContent:''},button={disabled:false,textContent:'使用当前位置',addEventListener:(event,fn)=>{button.click=fn;}};let filled=0;
 const control=bind({button,status,field:id=>fields[id],onFilled:()=>filled++,geolocation:()=>provider});return {fields,status,button,control,filled:()=>filled};
}
let calls=0,success,failure,options;const ui=setup({getCurrentPosition:(a,b,o)=>{calls++;success=a;failure=b;options=o;}});
assert.equal(calls,0);ui.button.click();ui.button.click();assert.equal(calls,1);assert.equal(ui.button.disabled,true);
assert.deepEqual(options,{enableHighAccuracy:true,timeout:15000,maximumAge:0});
success({coords:{latitude:-35.5,longitude:-139.75,accuracy:12.1,altitude:9999}});
assert.equal(ui.fields.lonD.value,'139');assert.equal(ui.fields.lonM.value,'45');assert.equal(ui.fields.lonH.value,'-1');assert.equal(ui.fields.latD.value,'35');assert.equal(ui.fields.latM.value,'30');assert.equal(ui.fields.latH.value,'-1');assert.equal(ui.fields.height.value,'123');assert.equal(ui.filled(),1);assert.match(ui.status.textContent,/13 米/);assert.equal(ui.button.disabled,false);
for(const code of [1,2,3]){ui.button.click();failure({code});assert.equal(ui.button.disabled,false);assert.equal(ui.fields.height.value,'123');assert.ok(ui.status.textContent.length>0);}
ui.button.click();ui.control.cancel();ui.fields.lonD.value='42';success({coords:{latitude:1,longitude:2,accuracy:10}});assert.equal(ui.fields.lonD.value,'42');assert.equal(ui.filled(),1);
const unsupported=setup(null);unsupported.button.click();assert.match(unsupported.status.textContent,/无法定位/);
ui.button.click();success({coords:{latitude:NaN,longitude:10}});assert.equal(ui.fields.lonD.value,'42');assert.match(ui.status.textContent,/无效坐标/);
assert.deepEqual(toDMS(12+59/60+59.9999999/3600,180),[13,0,0,1]);assert.deepEqual(toDMS(-180,180),[180,0,0,-1]);
for(const value of [NaN,Infinity,181])assert.throws(()=>toDMS(value,180));
console.log('Single-request location, permission errors, stale callback cancellation, DMS carry and elevation preservation passed.');
