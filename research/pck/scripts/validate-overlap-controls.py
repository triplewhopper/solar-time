from pathlib import Path
import json,numpy as np,erfa
from datetime import datetime,timezone,timedelta
exec(Path('work/eop-followup/recover-pck.py').read_text().split("out=[solve")[0])
out=[]
for primary in ['2000-01-15','2016-07-15','2020-06-15','2024-01-01']:
 date=datetime.fromisoformat(primary).replace(tzinfo=timezone.utc);first=date.timestamp()/86400+40587-3;byday={}
 for shift in [-4,-2,0,2,4]:
  center=(date+timedelta(days=shift)).date().isoformat();b=solve(center);base=np.array(b['base_rows']);rounded=np.array(b['rounded_rows'])
  for i in range(2,len(base)-2):
   v=rounded[i].copy()
   if not first<=v[0]<=first+7:continue
   v[3]=base[i,3];dt=datetime.fromtimestamp((v[0]-40587)*86400,timezone.utc);dt,u,tai,tt,tdb=times(dt.isoformat());ref=pck(tdb)
   def residual(v):
    dut1=(tai[0]-u[0]+tai[1]-u[1])*86400-v[3];return vee(model(tdb,erfa.utcut1(*u,dut1),v,'true')@ref.T)
   for _ in range(3):
    lo=v.copy();hi=v.copy();lo[3]-=1e-5;hi[3]+=1e-5;j=(residual(hi)-residual(lo))/(2e-5);v[3]-=np.dot(residual(v),j)/np.dot(j,j)
   v[3]=round(v[3]*1e6)/1e6
   v=[v[0],round(v[1],2),round(v[2],2),round(v[3],6),v[4],round(v[5],2),round(v[6],2)];byday.setdefault(v[0],[]).append(v)
 conflicts=[];wrong=[]
 for day,rr in byday.items():
  if len(set(tuple(v) for v in rr))!=1:conflicts.append(day)
  orig=next(v for v in rows if v[0]==day)
  for v in rr:
   if any(abs(v[col]-orig[col])>q*.1 for col,q in zip([1,2,3,5,6],[.01,.01,1e-6,.01,.01])):wrong.append(dict(mjd=day,base=orig.tolist(),derived=v))
 out.append(dict(center=primary,known_records=len(byday),known_parameters=len(byday)*5,minimum_independent_windows=min(len(v) for v in byday.values()),overlap_conflicts=conflicts,rounding_mismatches=wrong))
p=Path('work/eop-followup/tail-validation.json');report=json.loads(p.read_text());report['overlapping_historical_controls']=out;report['single_window_edge_failures_retained']=True;p.write_text(json.dumps(report,indent=2))
p=Path('work/eop-followup/pck-derived-eop-2026-11-18.json');d=json.loads(p.read_text());d['validation']=report;p.write_text(json.dumps(d,indent=2)+'\n')
print(json.dumps(out,indent=2))
