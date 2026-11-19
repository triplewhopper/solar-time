'use strict';
/* GeographicLib PGM: global 16-bit big-endian geoid undulations, north to south. */
(()=>{
 class GeoidGrid{
  constructor(buffer){
   const bytes=new Uint8Array(buffer);let pos=0;const comments=[];
   const line=()=>{const start=pos;while(pos<bytes.length&&bytes[pos]!==10)pos++;if(pos===bytes.length)throw Error('海拔修正数据格式错误。');return new TextDecoder().decode(bytes.subarray(start,pos++)).trim();};
   if(line()!=='P5')throw Error('海拔修正数据格式错误。');
   const tokens=[];while(tokens.length<3){const s=line();if(s.startsWith('#'))comments.push(s);else tokens.push(...s.split(/\s+/));}
   [this.width,this.height,this.maximum]=tokens.map(Number);
   const metadata=comments.join('\n'),value=name=>Number(metadata.match(new RegExp('^# '+name+' ([-+0-9.eE]+)$','m'))?.[1]);
   this.offset=value('Offset');this.scale=value('Scale');
   if(this.width!==4320||this.height!==2161||this.maximum!==65535||!Number.isFinite(this.offset)||!(this.scale>0)||bytes.length-pos!==this.width*this.height*2)throw Error('海拔修正数据不完整。');
   this.view=new DataView(buffer,pos);
  }
  undulation(latitude,longitude){
   if(!Number.isFinite(latitude)||Math.abs(latitude)>90||!Number.isFinite(longitude))throw Error('请输入有效经纬度。');
   const x=((longitude%360)+360)%360*this.width/360,y=(90-latitude)*(this.height-1)/180;
   const ix=Math.min(this.width-1,Math.floor(x)),iy=Math.min(this.height-2,Math.floor(y)),fx=x-ix,fy=y-iy;
   const at=(row,col)=>this.view.getUint16((row*this.width+col%this.width)*2,false);
   const a=at(iy,ix)*(1-fx)+at(iy,ix+1)*fx,b=at(iy+1,ix)*(1-fx)+at(iy+1,ix+1)*fx;
   return this.offset+this.scale*(a*(1-fy)+b*fy);
  }
  toEllipsoid(elevation,latitude,longitude){
   if(!Number.isFinite(elevation)||elevation< -1000||elevation>100000)throw Error('海拔须在 −1000 至 100000 米之间。');
   const geoidUndulation=this.undulation(latitude,longitude);
   return {height:elevation+geoidUndulation,geoidUndulation};
  }
  static async load(){
   const responses=await Promise.all([fetch('data/geoid.json'),fetch('data/egm2008-5.pgm.gz')]);
   if(responses.some(r=>!r.ok))throw Error('海拔修正数据加载失败，请重新加载页面。');
   const metadata=await responses[0].json(),packed=await responses[1].arrayBuffer();
   const sha=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',packed)),v=>v.toString(16).padStart(2,'0')).join('');
   if(sha!==metadata.gzip_sha256)throw Error('海拔修正数据校验失败，请重新加载页面。');
   const stream=new Blob([packed]).stream().pipeThrough(new DecompressionStream('gzip'));
   return new GeoidGrid(await new Response(stream).arrayBuffer());
  }
 }
 if(typeof module!=='undefined'&&module.exports)module.exports=GeoidGrid;
 else globalThis.GeoidGrid=GeoidGrid;
})();
