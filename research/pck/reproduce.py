"""Reproduce the independent PCK recovery in an isolated scratch directory.
Requires numpy, pyerfa, jplephem, skyfield, certifi. No Horizons calls.
"""
from pathlib import Path
import hashlib,shutil,subprocess,sys,urllib.request,ssl,argparse
import certifi
here=Path(__file__).resolve().parent;repo=here.parents[1]
ap=argparse.ArgumentParser();ap.add_argument('--scratch',type=Path,default=here/'scratch');args=ap.parse_args();scratch=args.scratch.resolve()
work=scratch/'work';target=work/'eop-followup';target.mkdir(parents=True,exist_ok=True)
for p in (here/'scripts').glob('*.py'):shutil.copy2(p,target/p.name)
(work/'horizons-original').mkdir(exist_ok=True);shutil.copy2(repo/'data/eop-2026-11-17.long',work/'horizons-original/latest.long')
(work/'precision-audit').mkdir(exist_ok=True);kernel=work/'precision-audit/earth_000101_270214_261118.bpc'
if not kernel.exists():
 with urllib.request.urlopen('https://naif.jpl.nasa.gov/pub/naif/generic_kernels/pck/earth_000101_270214_261118.bpc',context=ssl.create_default_context(cafile=certifi.where())) as response:kernel.write_bytes(response.read())
assert hashlib.sha256(kernel.read_bytes()).hexdigest()=='be55272f1c98da612196a9ce08b1131a6559c0262dc127079f0fb3c113b0293e','Kernel hash mismatch'
assert hashlib.sha256((work/'horizons-original/latest.long').read_bytes()).hexdigest()=='9010548bcfd1043fa7075133e3494dba8998693c0cd404ccdd04c7d7bde31b03','Original baseline hash mismatch'
for name in ['reconstruct-tail.py','validate-tail.py','validate-overlap-controls.py']:subprocess.run([sys.executable,str(target/name)],cwd=scratch,check=True)
print('Reconstructed records and validation:',target)
