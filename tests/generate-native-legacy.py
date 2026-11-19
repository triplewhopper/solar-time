"""Independent vectorized native oracle for the legacy chain. No network."""
import json,gzip,sys,os
from pathlib import Path
import numpy as np,erfa
from jplephem.spk import SPK
reconstructed='--reconstructed' in sys.argv
root=Path(__file__).resolve().parents[1];data=json.loads(Path(os.environ.get('SOLAR_TEST_DATA',root/'data/eop.json')).read_text())
with gzip.open(root/'tests/native-domain.json.gz','rt') as f:base=json.load(f)
arr=np.array([r[:11] for r in base['rows']],float);ms,longitude,latitude,height=arr[:,:4].T;n=len(ms)
leaps=np.array(data['leaps']);tai=leaps[np.searchsorted(leaps[:,0],ms,side='right')-1,1]
records={v[0]:v for v in data['legacy']['rows']}
if reconstructed:
 for v in data['reconstructed']['patch_records']: records[v[0]]=v
raw=np.array([records[k] for k in sorted(records)]);end=data['reconstructed']['evaluation_end_mjd'] if reconstructed else raw[-1,0];mjd=np.clip(ms/86400000+40587,raw[0,0],end);lo=np.clip(np.searchsorted(raw[:,0],mjd,side='right')-1,0,len(raw)-2);f=(mjd-raw[lo,0])/(raw[lo+1,0]-raw[lo,0])
def local(start):
 start=np.clip(start,0,len(raw)-7);out=np.zeros((n,7))
 for j in range(7):
  weight=np.ones(n)
  for k in range(7):
   if j!=k:weight*=(mjd-raw[start+k,0])/(raw[start+j,0]-raw[start+k,0])
  out+=weight[:,None]*raw[start+j]
 return out
v=(1-f[:,None])*local(lo-3)+f[:,None]*local(lo-2)
dut=tai-v[:,3];xp=v[:,1]/1000;yp=v[:,2]/1000;dpsi=v[:,5];deps=v[:,6]
for i,r in enumerate(base['rows']):
 if r[11]=='manual-stress':dut[i],xp[i],yp[i],dpsi[i],deps[i],tai[i]=r[4:10]
utc=(ms-946728000000)/86400000;tt=utc+(tai+32.184)/86400;ut1=utc+dut/86400;lon=np.radians(longitude);lat=np.radians(latitude);AS=np.pi/648000;AU=149597870.7
xyz=erfa.gd2gc(1,lon,lat,height);dtr=erfa.dtdb(2451545,tt,(ms/86400000+dut/86400)%1,lon,np.hypot(xyz[:,0],xyz[:,1])/1000,xyz[:,2]/1000);tdb=tt+dtr/86400
kernel=SPK.open(root/'data/de441-solar.bsp');p,pv=kernel[0,3].compute_and_differentiate(2451545,tdb);p1,v1=kernel[3,399].compute_and_differentiate(2451545,tdb);p=(p+p1).T;pv=(pv+v1).T;sun=kernel[0,10].compute(2451545,tdb).T
ebpv=np.zeros(n,dtype=erfa.dt_pv);ebpv['p']=p/AU;ebpv['v']=pv/AU
eps=erfa.obl80(2451545,tdb);npsi,neps=erfa.nut80(2451545,tdb);bpn=erfa.rxr(erfa.numat(eps,npsi+dpsi*AS/1000,neps+deps*AS/1000),erfa.pmat76(2451545,tdb))
gast=erfa.anp(erfa.gmst82(2451545,ut1)+erfa.eqeq94(2451545,tdb)+dpsi*AS/1000*np.cos(eps));station=erfa.pvtob(lon,lat,height,xp*AS,yp*AS,0,gast)
ast=erfa.apcs(2451545,tdb,erfa.trxpv(bpn,station),ebpv,(p-sun)/AU);lt=np.zeros(n)
for _ in range(5):
 vec=kernel[0,10].compute(2451545,tdb-lt/86400).T/AU-ast['eb'];lt=np.linalg.norm(vec,axis=1)*AU/299792.458
proper=erfa.ab(vec/np.linalg.norm(vec,axis=1)[:,None],ast['v'],ast['em'],ast['bm1']);ra,dec=erfa.c2s(erfa.rxp(bpn,proper));st=station['p'];ha=erfa.anpm(np.arctan2(st[:,1],st[:,0])-ra);solar=(43200+ha*43200/np.pi)%86400
out={'base_cases':'native-domain.json.gz','source_sha256':data['reconstructed']['source_sha256'] if reconstructed else data['legacy']['sha256'],'generator':'native pyerfa '+erfa.__version__+' + jplephem; independently vectorized seven-point blend','columns':['dut1','xp','yp','dpsi','deps','tai','solar_seconds'],'rows':np.column_stack([dut,xp,yp,dpsi,deps,tai,solar]).tolist()}
with gzip.open(Path(os.environ.get('SOLAR_NATIVE_OUTPUT',root/('tests/native-reconstructed.json.gz' if reconstructed else 'tests/native-legacy.json.gz'))),'wt') as f:json.dump(out,f,separators=(',',':'))
print('Generated',n,'independent native legacy reference cases')
