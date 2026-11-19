"""Native positions/velocities at every exact Type2 boundary and ±1µs."""
import gzip,json
from pathlib import Path
from jplephem.spk import SPK
root=Path(__file__).resolve().parents[1];kernel=SPK.open(root/'data/de441-solar.bsp');rows=[]
for s in kernel.segments:
 init,step,coef=s._data
 for i in range(coef.shape[2]+1):
  for offset in [-.000001,0,.000001]:
   t=init+i*step+offset
   if t<s.start_second or t>s.end_second:continue
   days=t/86400;p,v=s.compute_and_differentiate(2451545,days)
   rows.append([s.center,s.target,days,*p.tolist(),*(v/86400).tolist()])
with gzip.open(root/'tests/spk-boundaries.json.gz','wt') as f:json.dump(rows,f,separators=(',',':'))
print(len(rows),'SPK boundary reference cases')
