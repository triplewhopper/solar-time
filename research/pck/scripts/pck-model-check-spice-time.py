import json,math,numpy as np,erfa
from pathlib import Path
from datetime import datetime,timezone,timedelta
from jplephem.pck import PCK
from skyfield.functions import rot_x,rot_z
root=Path('work/eop-followup')
config=json.loads((root/'config.json').read_text()) if (root/'config.json').exists() else {}
rows=np.array([[float(x) for x in l.split('$')[0].split(',') if x.strip()] for l in Path('work/horizons-original/latest.long').read_text().splitlines() if l.strip()[:1].isdigit()])
kernel_path=config.get('kernel_path','work/precision-audit/earth_000101_270214_261118.bpc')
k=PCK.open(kernel_path)
AS=math.pi/(180*3600)
def interp(mjd,kind):
 i=np.searchsorted(rows[:,0],mjd,side='right')-1;i=max(1,min(len(rows)-3,i));t=(mjd-rows[i,0])/(rows[i+1,0]-rows[i,0])
 def lag(a,n):
  p=rows[a:a+n];w=np.array([np.prod([(mjd-p[j,0])/(p[nn,0]-p[j,0]) for j in range(n) if j!=nn]) for nn in range(n)]);return w@p
 if kind=='lag4':return lag(i-1,4)
 if kind=='blend7':return (1-t)*lag(i-3,7)+t*lag(i-2,7)
 if kind=='hermite':
  p=rows[i-1:i+3];d0=(p[2]-p[0])/(p[2,0]-p[0,0]);d1=(p[3]-p[1])/(p[3,0]-p[1,0]);h=p[2,0]-p[1,0]
  return (2*t**3-3*t**2+1)*p[1]+(t**3-2*t**2+t)*h*d0+(-2*t**3+3*t**2)*p[2]+(t**3-t**2)*h*d1
 raise ValueError(kind)
def times(utc):
 dt=datetime.fromisoformat(utc.replace('Z','+00:00'));u=erfa.dtf2d('UTC',dt.year,dt.month,dt.day,dt.hour,dt.minute,dt.second+dt.microsecond/1e6);tai=erfa.utctai(*u);tt=erfa.taitt(*tai);tdb=(tt[0],tt[1]+erfa.dtdb(*tt,0,0,0,0)/86400)
 ettt=dt.timestamp()-946728000+round((tai[0]-u[0]+tai[1]-u[1])*86400)+32.184
 et=ettt
 for _ in range(5):
  M=6.239996+1.99096871e-7*et;et=ettt+1.657e-3*math.sin(M+1.671e-2*math.sin(M))
 days=math.floor(et/86400);tdb=(2451545.+days,(et-days*86400)/86400)
 return dt,u,tai,tt,tdb
def pck(tdb):
 et=(tdb[0]-2451545)*86400+tdb[1]*86400
 if et>k.segments[-1].final_second and et-k.segments[-1].final_second<1e-6:
  et=k.segments[-1].final_second;day=math.floor(et/86400);tdb=(2451545.+day,(et-day*86400)/86400)
 s=next(s for s in reversed(k.segments) if s.initial_second<=et<=s.final_second);a,b,c=s.compute(*tdb,False)
 return rot_z(-c)@rot_x(-b)@rot_z(-a)@rot_x(-84381.448*AS)
def model(tdb,ut1,v,mode):
 p=erfa.pmat76(*tdb);npsi,neps=erfa.nut80(*tdb);eps=erfa.obl80(*tdb);psi=npsi+v[5]*AS/1000;de=neps+v[6]*AS/1000
 n=erfa.numat(eps,psi,de);eq=psi*np.cos(eps+de if mode.startswith('true') else eps)
 if mode.endswith('Omega'):eq+=erfa.eqeq94(*tdb)-npsi*np.cos(eps)
 theta=erfa.gmst82(*ut1)+eq
 return erfa.pom00(v[1]*AS/1000,v[2]*AS/1000,0)@erfa.rz(theta,np.eye(3))@n@p
out=[]
for base in ['2000-01-02','2024-01-01','2026-10-01']:
 for hour in [0,6,12,18]:
  utc=f'{base}T{hour:02d}:00:00Z';dt,u,tai,tt,tdb=times(utc);mjd=(dt.timestamp()/86400+40587);ref=pck(tdb)
  for kind in ['lag4','blend7','hermite']:
   v=interp(mjd,kind);dut1=(tai[0]-u[0]+tai[1]-u[1])*86400-v[3];ut1=erfa.utcut1(*u,dut1)
   for mode in ['mean','true','meanOmega','trueOmega']:
    r=model(tdb,ut1,v,mode)@ref.T;w=np.array([r[2,1]-r[1,2],r[0,2]-r[2,0],r[1,0]-r[0,1]])/2/AS*1000
    out.append(dict(utc=utc,interpolator=kind,mode=mode,rotation_residual_mas=w.tolist(),norm_mas=float(np.linalg.norm(w))))
(root/'pck-model-check-spice-time.json').write_text(json.dumps(out,indent=2))
for kind in ['lag4','blend7','hermite']:
 for mode in ['mean','true','meanOmega','trueOmega']:
  rr=[r for r in out if r['interpolator']==kind and r['mode']==mode]
  print(kind,mode,'maxmas',max(r['norm_mas'] for r in rr),'rmsmas',np.sqrt(np.mean([r['norm_mas']**2 for r in rr])))
print('anchor details',[(r['mode'],r['rotation_residual_mas']) for r in out if r['utc']=='2024-01-01T00:00:00Z'and r['interpolator']=='lag4'])
