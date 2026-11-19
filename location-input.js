'use strict';
(()=>{
 function toDMS(value,max){
  if(!Number.isFinite(value)||Math.abs(value)>max)throw Error('定位返回了无效坐标，请重试。');
  const units=Math.round(Math.abs(value)*3600*1e6),degrees=Math.floor(units/3600000000),rest=units-degrees*3600000000;
  const minutes=Math.floor(rest/60000000),seconds=(rest-minutes*60000000)/1e6;
  return [degrees,minutes,seconds,value<0?-1:1];
 }
 function bind({button,status,field,onFilled,toElevation,geolocation=()=>navigator.geolocation}){
  let generation=0,pending=false;
  const idle=()=>{pending=false;button.disabled=false;button.textContent='使用当前位置';};
  const cancel=()=>{generation++;idle();status.textContent='';};
  button.addEventListener('click',()=>{
   if(pending)return;
   const id=++generation;field('height').value='';onFilled();let provider;
   try{provider=geolocation();}catch{}
   if(!provider){status.textContent='此浏览器无法定位，请手动填写经纬度。';return;}
   pending=true;button.disabled=true;button.textContent='正在定位…';status.textContent='正在获取当前位置…';
   const failure=error=>{
    if(id!==generation)return;idle();
    status.textContent=({1:'未获得位置权限。可在浏览器的网站设置中允许定位后重试。',2:'暂时无法获取位置，请稍后重试。',3:'定位超时，请重试。'})[error?.code]||'定位失败，请重试或手动填写。';
   };
   try{provider.getCurrentPosition(async position=>{
    if(id!==generation)return;
    try{
     const lon=toDMS(position.coords.longitude,180),lat=toDMS(position.coords.latitude,90);
     for(const [prefix,values]of [['lon',lon],['lat',lat]])['D','M','S','H'].forEach((suffix,i)=>{field(prefix+suffix).value=String(values[i]);});
     const {altitude,altitudeAccuracy,accuracy,latitude,longitude}=position.coords;
     let elevation=null;
     if(Number.isFinite(altitude)&&Number.isFinite(altitudeAccuracy)&&altitudeAccuracy>=0){
      try{elevation=await toElevation(altitude,latitude,longitude);}catch{}
      if(id!==generation)return;
     }
     const hasElevation=Number.isFinite(elevation)&&elevation>=-1000&&elevation<=100000;
     field('height').value=hasElevation?String(Math.round(elevation*1000)/1000):'';
     idle();status.textContent=(hasElevation?'已填入当前位置和海拔':'已填入经纬度，未取得海拔，请手动填写')+(Number.isFinite(accuracy)&&accuracy>=0?' · 定位精度约 ±'+Math.ceil(accuracy)+' 米':'');onFilled();
    }catch(error){idle();status.textContent=error.message;}
   },failure,{enableHighAccuracy:true,timeout:15000,maximumAge:0});}catch(error){failure(error);}
  });
  return {cancel};
 }
 const api={toDMS,bind};if(typeof module!=='undefined'&&module.exports)module.exports=api;else globalThis.LocationInput=api;
})();
