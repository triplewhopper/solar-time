from pathlib import Path
import json,numpy as np,erfa
from datetime import datetime,timezone
exec(Path('work/eop-followup/recover-pck.py').read_text().split("out=[solve")[0])
root=Path('work/eop-followup');derived=json.loads((root/'pck-derived-eop-2026-11-18.json').read_text())
merged={r[0]:r.tolist() for r in rows}
for rr in derived['records']:
 v=rr['record'];v=[v[0],round(v[1],2),round(v[2],2),round(v[3],6),v[4],round(v[5],2),round(v[6],2)];rr['record']=v;merged[v[0]]=v
combined=np.array([merged[d] for d in sorted(merged)])
forcol=['mjd_utc','xp_mas','yp_mas','tai_minus_ut1_seconds','tai_minus_utc_seconds','dpsi_mas','deps_mas']
(root/'legacy-plus-derived-tail.json').write_text(json.dumps(dict(provenance=derived['provenance'],source_base=derived['baseline_file'],derived_range=[derived['derived_start'],derived['derived_end']],columns=forcol,rows=combined.tolist()),separators=(',',':'))+'\n')
held=[]
for day in range(61314,61450):
 for fraction in [.07321,.38321,.67321,.97321]:
  mjd=day+fraction;i=np.searchsorted(combined[:,0],mjd,side='right')-1;i=max(0,min(len(combined)-4,i-1));p=combined[i:i+4]
  ww=np.array([np.prod([(mjd-p[j,0])/(p[k,0]-p[j,0]) for j in range(4) if j!=k]) for k in range(4)]);v=ww@p
  dt=datetime.fromtimestamp((mjd-40587)*86400,timezone.utc);dt,u,tai,tt,tdb=times(dt.isoformat());dut1=(tai[0]-u[0]+tai[1]-u[1])*86400-v[3];res=vee(model(tdb,erfa.utcut1(*u,dut1),v,'true')@pck(tdb).T)
  held.append(dict(utc=dt.isoformat(),residual_rotation_mas=res.tolist()))
controls=[]
for center in ['2000-01-15','2016-07-15','2020-06-15','2024-01-01']:
 b=solve(center);base=np.array(b['base_rows']);rounded=np.array(b['rounded_rows']);mismatches=[];ut1res=[]
 for i,v in enumerate(rounded):
  v=v.copy();v[3]=base[i,3];dt=datetime.fromtimestamp((v[0]-40587)*86400,timezone.utc);dt,u,tai,tt,tdb=times(dt.isoformat());ref=pck(tdb)
  def residual(v):
   dut1=(tai[0]-u[0]+tai[1]-u[1])*86400-v[3];return vee(model(tdb,erfa.utcut1(*u,dut1),v,'true')@ref.T)
  for _ in range(3):
   lo=v.copy();hi=v.copy();lo[3]-=1e-5;hi[3]+=1e-5;j=(residual(hi)-residual(lo))/(2e-5);v[3]-=np.dot(residual(v),j)/np.dot(j,j)
  ut1res.append(float((v[3]-base[i,3])*1e6));v[3]=round(v[3]*1e6)/1e6
  for col,q in zip([1,2,3,5,6],[.01,.01,1e-6,.01,.01]):
   if abs(v[col]-base[i,col])>q*.1:mismatches.append(dict(mjd=float(v[0]),column=col,base=float(base[i,col]),derived=float(v[col]),quantum=q))
 controls.append(dict(center=center,known_record_count=len(base),known_parameter_count=len(base)*5,rounding_mismatches=mismatches,inferred_ut1_deviation_us=ut1res,condition_number=b['condition_number']))
v=np.array([r['residual_rotation_mas'] for r in held]);norm=np.linalg.norm(v,axis=1)
validation={'heldout':dict(count=len(held),fractions=[.07321,.38321,.67321,.97321],training_fractions=[.025,.125,.225,.325,.425,.525,.625,.725,.825,.925],max_axis_mas=np.max(abs(v),axis=0).tolist(),max_norm_mas=float(max(norm)),rms_norm_mas=float(np.sqrt(np.mean(norm**2))),worst=held[int(np.argmax(norm))]),'controls':controls,'overlap_conflicts':derived['conflict_count'],'boundary_note':'UTC2027Feb14ET differsfromkernelend by1doubleULP0.119209us; onlythat<1us boundary isclamped toexactPCKend. Notappliedtoothertimes. DerivedUTCanchorUT1 fitdistanceatboundary0.035741us.'}
(root/'tail-validation.json').write_text(json.dumps(validation,indent=2));(root/'tail-heldout-rotations.json').write_text(json.dumps(held))
derived['validation']=validation;(root/'pck-derived-eop-2026-11-18.json').write_text(json.dumps(derived,indent=2)+'\n')
print(json.dumps(validation,indent=2))
