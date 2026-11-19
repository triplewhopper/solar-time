"""Independent NumPy reference from the distributed big-endian PGM grid."""
from pathlib import Path
import gzip,json,io,re
import numpy as np
root=Path(__file__).resolve().parents[1];raw=gzip.decompress((root/'data/egm2008-5.pgm.gz').read_bytes());f=io.BytesIO(raw)
header=[]
while True:
 line=f.readline();header.append(line)
 if line.strip()==b'65535':break
text=b''.join(header).decode();offset=float(re.search(r'# Offset (.*)',text)[1]);scale=float(re.search(r'# Scale (.*)',text)[1]);grid=np.frombuffer(raw[f.tell():],dtype='>u2').reshape(2161,4320)
rng=np.random.default_rng(20261119);points=[(float(lat),float(lon)) for lat,lon in zip(rng.uniform(-90,90,1024),rng.uniform(-180,180,1024))]
points += [(lat,lon) for lat in [-90,-89.999999,0,35,89.999999,90] for lon in [-180,-1e-9,0,1e-9,135,180]]
rows=[]
for lat,lon in points:
 y=(90-lat)*12;x=(lon%360)*12;iy=min(2159,int(y));ix=min(4319,int(x));fy=y-iy;fx=x-ix
 weights=np.outer([1-fy,fy],[1-fx,fx]);values=grid[np.ix_([iy,iy+1],[ix,(ix+1)%4320])]
 rows.append([lat,lon,float(offset+scale*np.sum(weights*values))])
(root/'tests/geoid-reference.json').write_text(json.dumps({'generator':'Independent NumPy weighted grid interpolation','points':rows},separators=(',',':'))+'\n')
