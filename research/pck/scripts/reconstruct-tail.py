from pathlib import Path
import json,math,numpy as np,erfa,hashlib
from datetime import datetime,timezone,timedelta
exec(Path('work/eop-followup/recover-pck.py').read_text().split("out=[solve")[0])
# Extend only the numerical starting guess; appendedrecord is explicitly not originaldata.
last=rows[-1].copy();new=last+(rows[-1]-rows[-2])/(rows[-1,0]-rows[-2,0]);new[0]=last[0]+1;new[4]=last[4];rows=np.vstack([rows,new])
start=datetime(2026,10,1,tzinfo=timezone.utc);end=datetime(2027,2,14,tzinfo=timezone.utc)
centers=[];t=start-timedelta(days=2)
while t<=end-timedelta(days=4):centers.append((t.date().isoformat(),8));t+=timedelta(days=2)
for x in [('2027-02-10',8),('2027-02-09',10),('2027-02-08',12)]:
 if x not in centers:centers.append(x)
blocks=[]
for bi,(center,n) in enumerate(centers):
 block=solve(center,n);base=np.array(block['base_rows']);rr=np.array(block['rounded_rows']);anchor=[]
 for i in range(len(rr)):
  v=rr[i].copy();v[3]=base[i,3];dt=datetime.fromtimestamp((v[0]-40587)*86400,timezone.utc);dt,u,tai,tt,tdb=times(dt.isoformat());reference=pck(tdb)
  def residual(v):
   dut1=(tai[0]-u[0]+tai[1]-u[1])*86400-v[3];return vee(model(tdb,erfa.utcut1(*u,dut1),v,'true')@reference.T)
  for _ in range(3):
   before=v.copy();after=v.copy();before[3]-=1e-5;after[3]+=1e-5;der=(residual(after)-residual(before))/(2e-5);v[3]-=np.dot(residual(v),der)/np.dot(der,der)
  inferred=v[3];v[3]=round(inferred*1e6)/1e6;rr[i]=v
  anglefrac=[abs(block['delta_quantum'][i][k]-round(block['delta_quantum'][i][k])) for k in [0,1,3,4]]
  anchor.append(dict(utc=dt.isoformat(),mjd=float(v[0]),record=v.tolist(),index=i,window_size=n,interior=2<=i<n-2,ut1_distance_to_quantum_us=abs((inferred-v[3])*1e6),max_angular_distance_to_quantum=max(anglefrac),anchor_residual_mas=residual(v).tolist()))
 block['anchor_recovery']=anchor;block['quantized_reconstructed_records']=rr.tolist();blocks.append(block)
 if bi%8==0:print('windows',bi+1,'/',len(centers),'last',center,flush=True)
root=Path('work/eop-followup');(root/'tail-recovery-windows.json').write_text(json.dumps(blocks))
bydate={}
for bi,b in enumerate(blocks):
 for r in b['anchor_recovery']:
  if start<=datetime.fromisoformat(r['utc'])<=end:bydate.setdefault(r['utc'],[]).append({**r,'window':bi})
recovered=[];conflicts=[]
for utc,candidates in sorted(bydate.items()):
 use=[r for r in candidates if r['interior']] or candidates
 tuples=[tuple(r['record']) for r in use]
 counts={p:tuples.count(p) for p in set(tuples)};best=max(counts,key=counts.get)
 consistent=len(counts)==1
 if not consistent:conflicts.append(dict(utc=utc,alternatives=[dict(record=list(k),count=v) for k,v in counts.items()],candidates=use))
 chosen=min([r for r in use if tuple(r['record'])==best],key=lambda r:r['max_angular_distance_to_quantum'])
 recovered.append(dict(utc=utc,record=list(best),windows=len(use),consistent=consistent,all_window_count=len(candidates),source='Nov18PCKderived; nottheoriginalASCIIfile',uncertainty=dict(max_angular_distance_to_quantum=max(r['max_angular_distance_to_quantum'] for r in use),max_ut1_distance_to_quantum_us=max(r['ut1_distance_to_quantum_us'] for r in use)),chosen_window=chosen['window']))
out={'provenance':'ReconstructedfromofficialNov18PCKrotationsusinglegacyIAU76/80,FolknertrueobliquityEqEq,SPICELSKtime,andcubicLagrangeEOPinterpolation. NotdownloadedoriginalEOPASCII. NoHorizonsobservablesusedinfit. Nov17ASCIIusedasstartingguess.', 'PCK_file':'work/precision-audit/earth_000101_270214_261118.bpc','PCK_sha256':hashlib.sha256(Path('work/precision-audit/earth_000101_270214_261118.bpc').read_bytes()).hexdigest(),'baseline_file':'work/horizons-original/latest.long','baseline_sha256':hashlib.sha256(Path('work/horizons-original/latest.long').read_bytes()).hexdigest(),'derived_start':'2026-10-01','derived_end':'2027-02-14','baseline_preserved_outside_derived_range':True,'column_names':['mjd_utc','xp_mas','yp_mas','tai_minus_ut1_seconds','tai_minus_utc_seconds','dpsi_mas','deps_mas'],'record_quantum':[None,.01,.01,.000001,1,.01,.01],'record_count':len(recovered),'window_count':len(blocks),'conflict_count':len(conflicts),'records':recovered,'conflicts':conflicts}
(root/'pck-derived-eop-2026-11-18.json').write_text(json.dumps(out,indent=2)+'\n')
print('Records',len(recovered),'windows',len(blocks),'conflicts',len(conflicts));print('end',recovered[-2:]);print('conflict dates',[c['utc'] for c in conflicts])
