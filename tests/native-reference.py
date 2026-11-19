"""Independent native ERFA + jplephem check; no network access."""
import json,math
from pathlib import Path
from datetime import datetime
import numpy as np
import erfa
from jplephem.spk import SPK
root=Path(__file__).resolve().parents[1]
data=json.loads((root/'data/eop.json').read_text())
fixtures=json.loads((root/'tests/horizons-reference.json').read_text())['fixtures']
spk=SPK.open(root/'data/de441-solar.bsp')
AU=149597870.7;AS=math.pi/648000

def tai(ms):return next(n for epoch,n in reversed(data['leaps']) if ms>=epoch)
def eop(ms):
    mjd=ms/86400000+40587;n=math.floor(mjd);f=mjd-n;a=data['rows'][n-data['rows'][0][0]];b=data['rows'][n-data['rows'][0][0]+1]
    interp=lambda i:a[i]+(b[i]-a[i])*f
    ut=(a[3]-tai((a[0]-40587)*86400000))*(1-f)+(b[3]-tai((b[0]-40587)*86400000))*f+tai(ms)
    dx,dy=(0,0) if any(v is None for v in [a[4],a[5],b[4],b[5]]) else (interp(4),interp(5))
    return ut,interp(1),interp(2),dx,dy

out=[]
for f in fixtures:
    ms=datetime.fromisoformat(f['utc'].replace('Z','+00:00')).timestamp()*1000
    dut,xp,yp,dx,dy=eop(ms);utc=(ms-946728000000)/86400000;tt=utc+(tai(ms)+32.184)/86400;ut1=utc+dut/86400
    lon,lat=map(math.radians,[f['longitude_deg'],f['latitude_deg']]);h=f['height_km']*1000
    xyz=erfa.gd2gc(1,lon,lat,h)
    dtr=erfa.dtdb(2451545,tt,(ms/86400000+dut/86400)%1,lon,math.hypot(xyz[0],xyz[1])/1000,xyz[2]/1000);tdb=tt+dtr/86400
    p,v=spk[0,3].compute_and_differentiate(2451545,tdb);p1,v1=spk[3,399].compute_and_differentiate(2451545,tdb);p+=p1;v+=v1
    sun=spk[0,10].compute(2451545,tdb);pv=np.array((p/AU,v/AU),dtype=erfa.dt_pv)
    x,y,s=erfa.xys06a(2451545,tt);x+=dx*AS/1000;y+=dy*AS/1000;s=erfa.s06(2451545,tt,x,y)
    theta=erfa.era00(2451545,ut1);spr=erfa.sp00(2451545,tt)
    ast=erfa.apco(2451545,tdb,pv,(p-sun)/AU,x,y,s,theta,lon,lat,h,xp*AS,yp*AS,spr,0,0)
    lt=0
    for _ in range(5):
        vec=spk[0,10].compute(2451545,tdb-lt/86400)/AU-ast['eb'];lt=np.linalg.norm(vec)*AU/299792.458
    app=erfa.ab(vec/np.linalg.norm(vec),ast['v'],ast['em'],ast['bm1']);cirs=erfa.rxp(ast['bpn'],app);ra,dec=erfa.c2s(cirs)
    st=erfa.pvtob(lon,lat,h,xp*AS,yp*AS,spr,theta)['p'];ha=erfa.anpm(math.atan2(st[1],st[0])-ra)
    solar=(43200+ha*43200/math.pi)%86400
    out.append({'site_index':f['site_index'],'utc':f['utc'],'solar_seconds':solar,'earth_position_km':p.tolist(),'earth_velocity_km_day':v.tolist(),'tdb_days':tdb})
path=root/'tests/native-reference.json';path.write_text(json.dumps({'generator':'pyerfa '+erfa.__version__+' + jplephem; independent native computation','fixtures':out},indent=2))
print('Wrote',len(out),'native reference cases')
