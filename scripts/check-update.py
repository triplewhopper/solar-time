"""Cheap first stage: compare official bytes and the last validated algorithm fingerprint.
Only standard-library imports are needed. Downloads are reused by the update stage.
"""
import argparse, hashlib, importlib.util, json, os, subprocess
from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
STATE=ROOT/'data/regression-state.json'
PATTERNS=['solar-core.js','app.js','location-input.js','geoid.js','vendor/*','scripts/*.py','scripts/*.cjs','scripts/*.txt','research/pck/scripts/*.py','tests/**/*','data/de441-solar.bsp','data/egm2008-5.pgm.gz','data/geoid.json','.github/workflows/update-eop.yml']

def fingerprint(root=ROOT):
    files=sorted({p for pattern in PATTERNS for p in root.glob(pattern) if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc' and p.name!='domain-errors.json.gz'})
    h=hashlib.sha256()
    for p in files:
        h.update(p.relative_to(root).as_posix().encode()+b'\0');h.update(hashlib.sha256(p.read_bytes()).digest())
    return h.hexdigest()

def decision(current,ascii_sha,pck_sha,algorithm_sha,passed):
    changed=ascii_sha!=current['base_sha256'] or pck_sha!=current.get('pck_sha256',current['source_sha256'])
    algorithm_changed=algorithm_sha!=passed.get('algorithm_sha256')
    return {'data_changed':changed,'algorithm_changed':algorithm_changed,'needs_validation':changed or algorithm_changed}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--work',type=Path,default=ROOT/'test-cache/update/preflight');ap.add_argument('--mark-passed',action='store_true');a=ap.parse_args();a.work=a.work.resolve();a.work.mkdir(parents=True,exist_ok=True)
    if a.mark_passed:
        plan=json.loads((a.work/'plan.json').read_text())
        if fingerprint()!=plan['algorithm_sha256']:raise RuntimeError('Algorithm files changed during validation')
        STATE.write_text(json.dumps({'algorithm_sha256':plan['algorithm_sha256'],'validated_at':datetime.now(timezone.utc).isoformat(),'commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()},indent=2)+'\n');return
    spec=importlib.util.spec_from_file_location('update_eop',ROOT/'scripts/update-eop.py');u=importlib.util.module_from_spec(spec);spec.loader.exec_module(u)
    installed=json.loads((ROOT/'data/eop.json').read_text());current=installed['reconstructed']
    raw=u.fetch(u.ASCII_URL);raw_date,_=u.parse_ascii(raw)
    name,end,observed=u.latest_kernel(u.fetch(u.PCK_BASE).decode());payload=u.fetch(u.PCK_BASE+name)
    if not payload.startswith(b'DAF/PCK'):raise ValueError('Invalid PCK')
    if raw_date<u.date(installed['legacy']['last_observation_utc'].replace('Z','+00:00')) or observed<u.date(current['last_observation_utc'].replace('Z','+00:00')):raise ValueError('Refuse upstream version rollback')
    passed=json.loads(STATE.read_text()) if STATE.exists() else {}
    algorithm_sha=fingerprint();plan=decision(current,u.digest(raw),u.digest(payload),algorithm_sha,passed)
    plan.update(algorithm_sha256=algorithm_sha,ascii_sha256=u.digest(raw),pck_sha256=u.digest(payload),installed_eop_sha256=u.digest((ROOT/'data/eop.json').read_bytes()),pck_file=name,end=end.date().isoformat(),observed=observed.date().isoformat())
    (a.work/'latest.long').write_bytes(raw);(a.work/name).write_bytes(payload);u.write_json(a.work/'plan.json',plan)
    if os.environ.get('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'],'a') as f:
            for k in ['data_changed','algorithm_changed','needs_validation']:f.write(f'{k}={str(plan[k]).lower()}\n')
    print(json.dumps({k:plan[k] for k in ['data_changed','algorithm_changed','needs_validation']},indent=2))
if __name__=='__main__':main()
