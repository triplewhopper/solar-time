"""Download, independently verify, then promote one coherent EOP release.
No user coordinates. No credentials. A failed gate never replaces live data.
"""
import argparse, gzip, hashlib, json, math, os, re, shutil, ssl, subprocess, sys, time
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
try:
    import certifi
except ImportError:
    certifi = None

ROOT = Path(__file__).resolve().parents[1]
UTC = timezone.utc
PCK_BASE = 'https://naif.jpl.nasa.gov/pub/naif/generic_kernels/pck/'
ASCII_URL = 'https://ssd.jpl.nasa.gov/ftp/ssd/latest.long'

def digest(b): return hashlib.sha256(b).hexdigest()
def write_json(p, obj, compact=False): p.write_text(json.dumps(obj, ensure_ascii=False, indent=None if compact else 2, separators=(',',':') if compact else None)+'\n')
def date(s): return datetime.fromisoformat(s).replace(tzinfo=UTC)
def mjd(d): return round(d.timestamp()/86400+40587)
def fetch(url, body=None, headers=None):
    request=urllib.request.Request(url, data=body, headers={'User-Agent':'solar-time-updater/1.0 (https://github.com/triplewhopper/solar-time)', **(headers or {})})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=120, context=ssl.create_default_context(cafile=certifi.where() if certifi else None)) as r:
                return r.read()
        except Exception:
            if attempt==2: raise
            time.sleep(5*(attempt+1))

def parse_ascii(raw):
    text=raw.decode('ascii')
    if "EOPTRF='ITRF93'" not in text or "EOPCRF='ICRF93'" not in text or "EOPUT1='UT1'" not in text: raise ValueError('Unexpected ASCII reference frame')
    match=re.search(r'Last Data Point\s+(\d{2}-[A-Za-z]{3}-\d{4})', text)
    if not match: raise ValueError('Missing EOP date')
    observed=datetime.strptime(match[1],'%d-%b-%Y').replace(tzinfo=UTC)
    rows=[[float(x) for x in line.split('$')[0].split(',') if x.strip()] for line in text.splitlines() if line.strip()[:1].isdigit()]
    if len(rows)<10000: raise ValueError('Truncated ASCII')
    for i,r in enumerate(rows):
        if len(r)!=7 or not all(math.isfinite(x) for x in r): raise ValueError('Malformed EOP row')
        if i and r[0]<=rows[i-1][0]: raise ValueError('Non-monotonic EOP')
        if max(abs(r[j]) for j in [1,2,5,6])>10000 or abs(r[3])>100: raise ValueError('EOP outside bounds')
    return observed, rows

def latest_kernel(index):
    names=set(re.findall(r'href="(earth_000101_(\d{6})_(\d{6})\.bpc)"', index))
    if not names: raise ValueError('No dated Earth PCK listed')
    name,end,observed=max(names,key=lambda x:(x[2],x[1]))
    return name, datetime.strptime(end,'%y%m%d').replace(tzinfo=UTC), datetime.strptime(observed,'%y%m%d').replace(tzinfo=UTC)

def reference(directory, observed, end, start):
    # Every call is sequential and batched; sites are synthetic test coordinates.
    dates={date('1972-01-01')+timedelta(minutes=20),date('2000-01-15'),date('2024-01-01'),date('2099-12-31')+timedelta(hours=14,minutes=59)}
    t=start
    while t<end:
        dates.add(t+timedelta(hours=7,minutes=13,seconds=17,milliseconds=321));t+=timedelta(days=1)
    for anchor in [start,observed,end-timedelta(days=1),end]:
        for seconds in [-86400,-21600,-1,0,.001,1,21600,86400]: dates.add(anchor+timedelta(seconds=seconds))
    stamps=sorted(d.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3] for d in dates)
    sites=[dict(longitude=0,latitude=0,height=0),dict(longitude=135,latitude=35,height=100),dict(longitude=-135,latitude=-89.999999,height=-1000),dict(longitude=135,latitude=89.999999,height=100),dict(longitude=180,latitude=-23.4567,height=100000),dict(longitude=42.123456,latitude=-78.234567,height=8200)]
    expected=f'eop.{observed:%y%m%d}.p{end:%y%m%d}'
    groups=[];hashes=[]
    for i,site in enumerate(sites):
        settings={'COMMAND':"'10'",'OBJ_DATA':"'NO'",'EPHEM_TYPE':"'OBSERVER'",'CENTER':"'coord@399'",'COORD_TYPE':"'GEODETIC'",'SITE_COORD':"'%s,%s,%s'"%(site['longitude'],site['latitude'],site['height']/1000),'TLIST_TYPE':"'CAL'",'TIME_TYPE':"'UT'",'TIME_DIGITS':"'FRACSEC'",'QUANTITIES':"'34'",'APPARENT':"'AIRLESS'",'EXTRA_PREC':"'YES'",'CSV_FORMAT':"'YES'",'ANG_FORMAT':"'DEG'",'CAL_TYPE':"'GREGORIAN'"}
        inp='!$$SOF\n'+'\n'.join(k+'='+v for k,v in settings.items())+'\nTLIST= '+'\n '.join("'%s'"%t for t in stamps)+'\n!$$EOF\n'
        boundary='solar-time-update';body=('--'+boundary+'\r\nContent-Disposition: form-data; name="format"\r\n\r\njson\r\n--'+boundary+'\r\nContent-Disposition: form-data; name="input"; filename="check.inp"\r\nContent-Type: text/plain\r\n\r\n'+inp+'\r\n--'+boundary+'--\r\n').encode()
        cache=directory/f'horizons-{i}.json'
        raw=fetch('https://ssd.jpl.nasa.gov/api/horizons_file.api',body,{'Content-Type':'multipart/form-data; boundary='+boundary});cache.write_bytes(raw)
        result=json.loads(raw).get('result','');check_reference_version(result,expected)
        if '$$SOE' not in result: raise ValueError('Missing Horizons output')
        rows=[]
        for line in result.split('$$SOE')[1].split('$$EOE')[0].strip().splitlines():
            f=[s.strip() for s in line.split(',')]
            dt=datetime.strptime(f[0],'%Y-%b-%d %H:%M:%S.%f').replace(tzinfo=UTC)
            rows.append([round(dt.timestamp()*1000),float(f[3])*3600])
        if len(rows)!=len(stamps): raise ValueError('Incomplete Horizons response')
        groups.append({'site':site,'rows':rows});hashes.append({'request_sha256':digest(inp.encode()),'response_sha256':digest(raw)})
        print(f'Fresh Horizons site {i+1}/{len(sites)}: {len(rows)} cases, {expected}',flush=True)
    out={'eop_file':expected,'groups':groups,'hashes':hashes};write_json(directory/'horizons.json',out);return out

def recovery(directory, raw, kernel, observed, end, start):
    work=directory/'recovery';target=work/'work/eop-followup';target.mkdir(parents=True,exist_ok=True)
    for p in (ROOT/'research/pck/scripts').glob('*.py'): shutil.copy2(p,target/p.name)
    original=work/'work/horizons-original';original.mkdir(parents=True,exist_ok=True);(original/'latest.long').write_bytes(raw)
    write_json(target/'config.json',{'kernel_path':str(kernel.resolve()),'start':start.date().isoformat(),'end':end.date().isoformat()})
    for name in ['reconstruct-tail.py','validate-tail.py','validate-overlap-controls.py']:
        subprocess.run([sys.executable,str(target/name)],cwd=work,check=True)
    recovered=json.loads((target/'pck-derived-eop-2026-11-18.json').read_text());v=json.loads((target/'tail-validation.json').read_text())
    if recovered['conflict_count'] or recovered['record_count']!=(end-start).days+1: raise ValueError('Recovery conflicts or incomplete interval')
    if v['heldout']['max_norm_mas']>.1: raise ValueError('PCK held-out residual too large')
    for c in v['overlapping_historical_controls']:
        if c['rounding_mismatches'] or c['overlap_conflicts'] or c['minimum_independent_windows']<2: raise ValueError('Known historical control failed')
    blocks=json.loads((target/'tail-recovery-windows.json').read_text())
    if any(b['rank']!=b['unknown_count'] or b['condition_number']>10000 for b in blocks): raise ValueError('Unidentifiable recovery window')
    for r in recovered['records']:
        if r['uncertainty']['max_angular_distance_to_quantum']>.1 or r['uncertainty']['max_ut1_distance_to_quantum_us']>.49: raise ValueError('Ambiguous recovered record quantization')
    return recovered,v

def runtime_manifest(info, candidate=None):
    data=candidate or json.loads((ROOT/'data/eop.json').read_text())
    previous=json.loads((ROOT/'data/runtime.json').read_text()) if (ROOT/'data/runtime.json').exists() else {}
    current=data['reconstructed']
    write_json(ROOT/'data/runtime.json',{'eop_sha256':digest((ROOT/'data/eop.json').read_bytes()),'checked_at':info['checked_at'],'release':current['release_label'],'verification':info.get('verification',previous.get('verification')),'audit_url':'https://github.com/triplewhopper/solar-time/actions/workflows/update-eop.yml'})

def check_reference_version(result, expected):
    match=re.search(r'EOP file\s*:\s*(\S+)',result)
    if not match or match[1].lower()!=expected:
        raise ValueError(f'Horizons/PCK version mismatch: expected {expected}, got {match[1] if match else "missing"}; keep installed snapshot')

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--work',type=Path,default=ROOT/'test-cache/update');ap.add_argument('--prepared',type=Path);ap.add_argument('--force',action='store_true');ap.add_argument('--dry-run',action='store_true');args=ap.parse_args()
    args.work=args.work.resolve();args.work.mkdir(parents=True,exist_ok=True)
    installed=json.loads((ROOT/'data/eop.json').read_text());current=installed['reconstructed']
    checked=datetime.now(UTC).isoformat()
    if args.prepared:
        prepared=args.prepared.resolve();plan=json.loads((prepared/'plan.json').read_text())
        if digest((ROOT/'data/eop.json').read_bytes())!=plan['installed_eop_sha256']: raise ValueError('Installed snapshot changed after preflight')
        name=plan['pck_file']
        if not re.fullmatch(r'earth_000101_\d{6}_\d{6}\.bpc',name): raise ValueError('Invalid prepared kernel name')
        raw=(prepared/'latest.long').read_bytes();payload=(prepared/name).read_bytes()
        if digest(raw)!=plan['ascii_sha256'] or digest(payload)!=plan['pck_sha256']: raise ValueError('Prepared inputs changed after preflight')
        end=date(plan['end']);observed=date(plan['observed'])
    else:
        raw=fetch(ASCII_URL);index=fetch(PCK_BASE).decode();name,end,observed=latest_kernel(index);payload=fetch(PCK_BASE+name)
    raw_date,raw_rows=parse_ascii(raw)
    if raw_date<date(installed['legacy']['last_observation_utc'].replace('Z','+00:00')): raise ValueError('ASCII mirror would roll back the installed source date')
    kernel_sha=digest(payload)
    if not payload.startswith(b'DAF/PCK'): raise ValueError('Invalid PCK download')
    info={'checked_at':checked,'ascii_observed':raw_date.date().isoformat(),'ascii_sha256':digest(raw),'pck_file':name,'pck_sha256':kernel_sha,'installed_release':current['release_label'],'workflow_run':os.environ.get('GITHUB_RUN_ID')}
    if not args.force and kernel_sha==current.get('pck_sha256',current['source_sha256']) and digest(raw)==current['base_sha256']:
        previous=json.loads((ROOT/'data/update-status.json').read_text()) if (ROOT/'data/update-status.json').exists() else {}
        info={**previous,**info,'status':'unchanged'}
        if not args.dry_run:
            write_json(ROOT/'data/update-status.json',info);runtime_manifest(info)
        print('Official snapshot unchanged; calculation data retained.');return
    if observed<date(current['last_observation_utc'].replace('Z','+00:00')): raise ValueError('PCK would roll back the observation date')
    if (end-observed).days not in range(1,181): raise ValueError('Unexpected forecast horizon')
    # This updater deliberately uses the independently verified PCK route even if ASCII is newer.
    # A mismatched Horizons version blocks promotion until upstream products synchronize.
    start=observed-timedelta(days=48)
    directory=args.work/kernel_sha[:16];directory.mkdir(exist_ok=True);kernel=directory/name;kernel.write_bytes(payload)
    (directory/'latest.long').write_bytes(raw)
    # Check the live reference version BEFORE the expensive inversion.
    reference(directory,observed,end,start)
    recovered,rv=recovery(directory,raw,kernel,observed,end,start)
    candidate=json.loads(json.dumps(installed));legacy=candidate['legacy'];legacy.update(rows=raw_rows,sha256=digest(raw),last_observation_utc=raw_date.isoformat(),release_label=raw_date.date().isoformat(),file_size=len(raw),downloaded_utc=checked,release_utc=None,prediction_end_utc=datetime.fromtimestamp((raw_rows[-1][0]-40587)*86400,UTC).isoformat(),download_methods=['HTTPS with certificate verification'],horizons_reference_file=f'eop.{observed:%y%m%d}.p{end:%y%m%d}',exact_reference_release_available=raw_date==observed)
    patches=[r['record'] for r in recovered['records']]
    for r in patches:
        epoch=(r[0]-40587)*86400000
        tai=next(v for t,v in reversed(candidate['leaps']) if epoch>=t)
        if r[4]!=tai: raise ValueError('New leap-second table required; do not silently publish using an old time scale')
    candidate['reconstructed']={**current,'release_label':observed.date().isoformat()+'（PCK恢复）','source_url':PCK_BASE+name,'source_sha256':kernel_sha,'base_sha256':digest(raw),'derived_range':[start.date().isoformat(),end.date().isoformat()],'last_observation_utc':observed.isoformat(),'evaluation_end_mjd':mjd(end)-1,'support_end_mjd':mjd(end),'patch_records':patches,'record_count':len(patches),'window_count':recovered['window_count'],'overlap_conflicts':0,'horizons_eop_file':f'eop.{observed:%y%m%d}.p{end:%y%m%d}','source_file_obtained':False}
    # When the public original catches up, verify the recovered parameters against it.
    original_available=raw_date==observed and raw_rows[-1][0]==mjd(end)
    if original_available:
        byday={r[0]:r for r in raw_rows}
        if any(any(abs(a-b)>1e-9 for a,b in zip(r,byday[r[0]])) for r in patches):
            raise ValueError('Original ASCII disagrees with independent PCK reconstruction')
        candidate['reconstructed'].update(release_label=observed.date().isoformat()+'（JPL原始）',source_kind='original_ascii_verified_against_independent_pck_recovery',source_url=ASCII_URL,source_sha256=digest(raw),source_file_obtained=True,patch_records=[byday[r[0]] for r in patches])
    candidate['reconstructed']['pck_sha256']=kernel_sha
    candidate['reconstructed']['pck_source_url']=PCK_BASE+name
    rv['original_ascii_obtained']=original_available
    rv['original_records_compared']=len(patches) if original_available else 0
    write_json(directory/'candidate.json',candidate,compact=True)
    env={**os.environ,'SOLAR_TEST_DATA':str(directory/'candidate.json'),'SOLAR_NATIVE_OUTPUT':str(directory/'native.json.gz')}
    subprocess.run([sys.executable,str(ROOT/'tests/generate-native-legacy.py'),'--reconstructed'],env=env,check=True)
    subprocess.run(['node',str(ROOT/'scripts/verify-candidate.cjs'),str(directory)],check=True)
    verification=json.loads((directory/'verification.json').read_text());info.update(status='validated',installed_release=candidate['reconstructed']['release_label'],verification=verification)
    write_json(directory/'update-status.json',info)
    if args.dry_run: print('Dry run: all gates passed; live files untouched.');return
    release=observed.strftime('%Y-%m-%d')+'-'+candidate['reconstructed']['source_sha256'][:12];archive=ROOT/'data/releases'/release;archive.mkdir(parents=True,exist_ok=True)
    # Candidate files are committed together only after every gate succeeds.
    # Large native reference can be regenerated; preserve source, fresh oracle and result.
    (archive/'candidate.json.gz').write_bytes(gzip.compress((directory/'candidate.json').read_bytes(),mtime=0))
    for filename in ['horizons.json','verification.json']: shutil.copy2(directory/filename,archive/filename)
    write_json(archive/'recovery-validation.json',rv)
    (archive/'source.long').write_bytes(raw)
    shutil.copy2(directory/'candidate.json',ROOT/'data/eop.json')
    info['release_path']='data/releases/'+release;write_json(ROOT/'data/update-status.json',info);runtime_manifest(info,candidate)
    provenance=json.loads((ROOT/'data/provenance.json').read_text());provenance['current_snapshot']={k:v for k,v in candidate['reconstructed'].items() if k!='patch_records'};provenance['current_verification']=verification;write_json(ROOT/'data/provenance.json',provenance)
    # Keep at most 30 full releases in the published tree; Git history retains older audits.
    releases=sorted((ROOT/'data/releases').iterdir(),key=lambda p:p.name)
    for old in releases[:-30]:
        if old.is_dir() and re.fullmatch(r'\d{4}-\d{2}-\d{2}-[0-9a-f]{12}',old.name): shutil.rmtree(old)
    print('Promoted verified snapshot',release)

if __name__=='__main__': main()
