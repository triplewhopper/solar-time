from pathlib import Path
import json,numpy as np,math,erfa
from datetime import datetime,timezone,timedelta
source=Path('work/eop-followup/pck-model-check-spice-time.py').read_text();exec(source.split('out=[]')[0])
# All inferred quantities come from officialPCKrotation matrices, neverHorizonsoutputs.
quant=np.array([.01,.01,1e-6,.01,.01]); cols=[1,2,3,5,6]
def vee(R):return np.array([R[2,1]-R[1,2],R[0,2]-R[2,0],R[1,0]-R[0,1]])/2/AS*1000

def solve(center,n=8):
 mid=datetime.fromisoformat(center).replace(tzinfo=timezone.utc);mjd0=mid.timestamp()/86400+40587-(n//2-1);start=np.searchsorted(rows[:,0],mjd0);base=rows[start:start+n].copy();assert np.all(np.diff(base[:,0])==1)
 def setup(mjd):
  i=np.searchsorted(base[:,0],mjd,side='right')-1;ids=np.arange(i-1,i+3);p=base[ids]
  weights=np.array([np.prod([(mjd-p[j,0])/(p[k,0]-p[j,0]) for j in range(4) if j!=k]) for k in range(4)])
  dt=datetime.fromtimestamp((mjd-40587)*86400,timezone.utc);utc=dt.isoformat();dt,u,tai,tt,tdb=times(utc)
  return dict(mjd=mjd,ids=ids,w=weights,tdb=tdb,u=u,tai=tai,ref=pck(tdb),utc=utc)
 train=[setup(day+fraction) for day in base[1:-2,0] for fraction in [.025,.125,.225,.325,.425,.525,.625,.725,.825,.925]]
 held=[setup(day+fraction) for day in base[1:-2,0] for fraction in [.07321,.38321,.67321,.97321]]
 def eval_point(s,parameters):
  v=s['w']@parameters[s['ids']];dut1=(s['tai'][0]-s['u'][0]+s['tai'][1]-s['u'][1])*86400-v[3]
  ut1=erfa.utcut1(*s['u'],dut1);return vee(model(s['tdb'],ut1,v,'true')@s['ref'].T)
 r=np.concatenate([eval_point(s,base) for s in train]);J=np.zeros((len(r),n*5))
 for si,s in enumerate(train):
  v=s['w']@base[s['ids']]
  for ci,col in enumerate(cols):
   derivatives=[]
   for sign in [-1,1]:
    vv=v.copy();vv[col]+=sign*quant[ci];dut1=(s['tai'][0]-s['u'][0]+s['tai'][1]-s['u'][1])*86400-vv[3];ut1=erfa.utcut1(*s['u'],dut1)
    derivatives.append(vee(model(s['tdb'],ut1,vv,'true')@s['ref'].T))
   dv=(derivatives[1]-derivatives[0])/2
   for wi,ri in enumerate(s['ids']):J[si*3:si*3+3,ri*5+ci]=s['w'][wi]*dv
 delta,res,rank,singular=np.linalg.lstsq(J,-r,rcond=None);fit=base.copy();rounded=base.copy()
 for ri in range(n):
  for ci,col in enumerate(cols):fit[ri,col]+=delta[ri*5+ci]*quant[ci];rounded[ri,col]+=round(delta[ri*5+ci])*quant[ci]
 def metrics(samples,parameters):
  rr=np.array([eval_point(s,parameters) for s in samples]);norm=np.linalg.norm(rr,axis=1)
  return dict(max_mas=float(max(norm)),rms_mas=float(np.sqrt(np.mean(norm**2))),max_axis_mas=np.max(np.abs(rr),axis=0).tolist())
 out=dict(center=center,source='OfficialNov18EarthPCK; noHorizonsqueriesoroutputs',kernel='earth_000101_270214_261118.bpc',model='IAU1976/1980 + trueobliquityEqEq,noOmega;SPICELSKtime;cubicLagrangeEOPinterpolation',parameter_quantum=quant.tolist(),columns=cols,unknown_count=n*5,observations=len(r),rank=int(rank),condition_number=float(singular[0]/singular[-1]),singular_values=singular.tolist(),delta_quantum=delta.reshape(n,5).tolist(),base_rows=base.tolist(),reconstructed_rows=fit.tolist(),rounded_rows=rounded.tolist(),training=dict(original=metrics(train,base),fit=metrics(train,fit),rounded=metrics(train,rounded)),heldout=dict(original=metrics(held,base),fit=metrics(held,fit),rounded=metrics(held,rounded)))
 return out
out=[solve('2024-01-01'),solve('2026-11-19')]
Path('work/eop-followup/pck-reconstruction.json').write_text(json.dumps(out,indent=2))
for o in out:
 print(o['center'],'rank',o['rank'],'cond',o['condition_number']);print('deltasquantum',np.array(o['delta_quantum']));print('training',o['training']);print('heldout',o['heldout'])
