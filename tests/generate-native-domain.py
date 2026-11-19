"""Vectorized native ERFA+jplephem oracle across every input dimension.
No API calls. Fixed seed, daily coverage, all SPK segment boundaries, random
holdout and extreme manual-EOP stress. Outputs compressed reproducible cases.
"""
import gzip,json,math,random
from pathlib import Path
import numpy as np
import erfa
from jplephem.spk import SPK
root=Path(__file__).resolve().parents[1];data=json.loads((root/'data/eop.json').read_text());kernel=SPK.open(root/'data/de441-solar.bsp')
start=63159300000;end=4102412399999 # UTC1972-01-01 00:15 to JST2099-12-31end
from datetime import datetime,timezone
start=int(datetime(1972,1,1,0,15,tzinfo=timezone.utc).timestamp()*1000)
rng=random.Random(70620261119);cases=[];heights=[-1000,0,100,1000,10000,100000]
def location(i):return ((i*137.50776405003785)%360-180,math.degrees(math.asin(2*((i*.61803398875)%1)-1))*.999999,heights[i%6])
for i,row in enumerate(data['rows'][:-1]):
 ms=(row[0]-40587)*86400000+12345123
 cases.append([int(ms),*location(i),'daily'])
boundaries=set()
for seg in kernel.segments:
 init,length,coeff=seg._data
 for j in range(coeff.shape[2]+1):
  # Nominal TT boundary neighborhoods; ±90seconds straddle TDB boundaries.
  ms=946728000000+(init+j*length)*1000
  for delta in [-90000,-1,0,1,90000]:
   t=int(ms+delta)
   if start<t<end:boundaries.add(t)
for i,ms in enumerate(sorted(boundaries)):cases.append([ms,*location(i+73),'spk-boundary'])
for i in range(32768):
 ms=rng.randrange(start+1000,end);lon=rng.uniform(-180,180);lat=math.degrees(math.asin(rng.uniform(-1,1)));h=rng.uniform(-1000,100000)
 if i%16==0:lat=[-89.99999999999999,-89.999999,-89.99,89.99,89.999999,89.99999999999999][(i//16)%6]
 cases.append([ms,lon,lat,h,'random-holdout'])
for lon in [-180,0,135,180]:
 for lat in [-89.99999999999999,-89.999999,-85,0,85,89.999999,89.99999999999999]:
  for h in [-1000,100000]:
   for ms in [start,end,1483228799000,1483228800000]:cases.append([ms,lon,lat,h,'corner'])
for i in range(2048):cases.append([rng.randrange(start+1000,end),*location(i+222),'manual-stress'])
n=len(cases);arr=np.array([c[:4] for c in cases],float);ms,longitude,latitude,height=arr.T
leaps=np.array(data['leaps']);tai=leaps[np.searchsorted(leaps[:,0],ms,side='right')-1,1]
j=np.array(data['jpl']['rows']);mjd=ms/86400000+40587+tai/86400
v=lambda k:np.interp(mjd,j[:,0],j[:,k]);dut=tai-v(3)/1000;xp=v(1)/1000;yp=v(2)/1000;dx=v(4);dy=v(5)
for i,c in enumerate(cases):
 if c[4]=='manual-stress':
  dut[i]=rng.uniform(-10,10);xp[i]=rng.uniform(-10,10);yp[i]=rng.uniform(-10,10);dx[i]=rng.uniform(-1000,1000);dy[i]=rng.uniform(-1000,1000);tai[i]=rng.randint(10,100)
utc=(ms-946728000000)/86400000;tt=utc+(tai+32.184)/86400;ut1=utc+dut/86400;lon=np.radians(longitude);lat=np.radians(latitude)
xyz=erfa.gd2gc(1,lon,lat,height);dtr=erfa.dtdb(2451545,tt,(ms/86400000+dut/86400)%1,lon,np.hypot(xyz[:,0],xyz[:,1])/1000,xyz[:,2]/1000);tdb=tt+dtr/86400
p,vv=kernel[0,3].compute_and_differentiate(2451545,tdb);p1,v1=kernel[3,399].compute_and_differentiate(2451545,tdb);p=(p+p1).T;vv=(vv+v1).T
sun=kernel[0,10].compute(2451545,tdb).T;AU=149597870.7;AS=np.pi/648000
pv=np.zeros(n,dtype=erfa.dt_pv);pv['p']=p/AU;pv['v']=vv/AU
x,y,s=erfa.xys06a(2451545,tt);x+=dx*AS/1000;y+=dy*AS/1000;s=erfa.s06(2451545,tt,x,y)
theta=erfa.era00(2451545,ut1);spr=erfa.sp00(2451545,tt);ast=erfa.apco(2451545,tdb,pv,(p-sun)/AU,x,y,s,theta,lon,lat,height,xp*AS,yp*AS,spr,0,0)
lt=np.zeros(n)
for _ in range(5):
 vec=kernel[0,10].compute(2451545,tdb-lt/86400).T/AU-ast['eb'];lt=np.linalg.norm(vec,axis=1)*AU/299792.458
app=erfa.ab(vec/np.linalg.norm(vec,axis=1)[:,None],ast['v'],ast['em'],ast['bm1']);cirs=erfa.rxp(ast['bpn'],app);ra,dec=erfa.c2s(cirs)
st=erfa.pvtob(lon,lat,height,xp*AS,yp*AS,spr,theta)['p'];ha=erfa.anpm(np.arctan2(st[:,1],st[:,0])-ra);solar=(43200+ha*43200/np.pi)%86400
rows=[[int(c[0]),c[1],c[2],c[3],float(dut[i]),float(xp[i]),float(yp[i]),float(dx[i]),float(dy[i]),int(tai[i]),float(solar[i]),c[4]] for i,c in enumerate(cases)]
out={'seed':70620261119,'generator':'native pyerfa '+erfa.__version__+' + jplephem; no network','columns':['ms','longitude','latitude','height','dut1','xp','yp','dx','dy','tai','solar_seconds','stratum'],'rows':rows}
with gzip.open(root/'tests/native-domain.json.gz','wt') as f:json.dump(out,f,separators=(',',':'))
print('Native oracle cases:',n,flush=True)
from collections import Counter
print(dict(Counter(c[4] for c in cases)),flush=True)
