"""Reproducible, sequential Horizons audit. Synthetic sites only; no runtime API.
Caches each raw response by request SHA. At most one network request at a time.
Usage: python capture-domain.py --cache /path/to/cache [--limit N]
"""
import argparse,calendar,csv,hashlib,json,math,random,re,ssl,time,urllib.request
from pathlib import Path
from datetime import datetime,timezone,timedelta
ap=argparse.ArgumentParser();ap.add_argument('--cache',required=True);ap.add_argument('--limit',type=int,default=1000);args=ap.parse_args()
root=Path(__file__).resolve().parents[1];cache=Path(args.cache);cache.mkdir(parents=True,exist_ok=True)
rng=random.Random(20261119);times=set()
def stamp(d):return d.astimezone(timezone.utc).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
def dt(y,m,d,h=0,mi=0,s=0,us=0):return datetime(y,m,d,h,mi,s,us,tzinfo=timezone.utc)
for y in range(1973,2028):
 for m in range(1,13):
  if y==2027 and m>11:continue
  times.add(stamp(dt(y,m,15,(y+m*7)%24,(y*11+m)%60,(m*13)%60,123000)))
for y in [1972,*range(2028,2100)]:
 for m in [3,6,12]:times.add(stamp(dt(y,m,15,(y+m)%24,17,31,456000)))
leaps=json.loads((root/'data/eop.json').read_text())['leaps']
for epoch,n in leaps:
 if epoch<dt(1973,1,2).timestamp()*1000:continue
 for sec in [-2,-1,0,1]:times.add(stamp(datetime.fromtimestamp(epoch/1000+sec,timezone.utc)))
for text in ['1973-01-02T00:00:00','2026-11-18T00:00:00','2027-02-14T00:00:00','2027-11-19T00:00:00']:
 base=datetime.fromisoformat(text).replace(tzinfo=timezone.utc)
 for sec in [-1,0,1]:
  if base+timedelta(seconds=sec)>=dt(1973,1,2):times.add(stamp(base+timedelta(seconds=sec)))
times.add('1972-01-01 00:20:00.000');times.add('2099-12-31 14:59:59.999')
for _ in range(64):
 a=dt(1973,1,2);b=dt(2027,11,18);times.add(stamp(a+(b-a)*rng.random()))
times=sorted(times)
sites=[];heights=[-1000,0,100,10000,100000]
for i in range(16):sites.append({'id':len(sites),'lon':round((i*137.50776405)%360-180,8),'lat':round(math.degrees(math.asin(-1+2*(i+.5)/16)),8),'height':heights[i%5],'stratum':'equal-area'})
for i,lat in enumerate([-89.999999,-89.99,-89,-85,85,89,89.99,89.999999]):
 sites.append({'id':len(sites),'lon':[-135,-45,45,135][i%4],'lat':lat,'height':heights[i%5],'stratum':'polar-boundary'})
for lon in [-180,180,0,135]:sites.append({'id':len(sites),'lon':lon,'lat':0,'height':heights[len(sites)%5],'stratum':'longitude-boundary'})
for i in range(12):sites.append({'id':len(sites),'lon':round(rng.uniform(-180,180),8),'lat':round(math.degrees(math.asin(rng.uniform(-1,1))),8),'height':round(rng.uniform(-1000,100000),3),'stratum':'holdout'})
plan={'seed':20261119,'sites':sites,'times_utc':times,'cases':len(sites)*len(times),'purpose':'stratified whole-domain coverage, not exhaustive continuum proof'}
(root/'tests/domain-plan.json').write_text(json.dumps(plan,indent=2))
base={'COMMAND':"'10'",'OBJ_DATA':"'NO'",'EPHEM_TYPE':"'OBSERVER'",'CENTER':"'coord@399'",'COORD_TYPE':"'GEODETIC'",'TLIST_TYPE':"'CAL'",'TIME_TYPE':"'UT'",'TIME_DIGITS':"'FRACSEC'",'QUANTITIES':"'1,2,7,34,42,49'",'APPARENT':"'AIRLESS'",'EXTRA_PREC':"'YES'",'CSV_FORMAT':"'YES'",'ANG_FORMAT':"'DEG'",'CAL_TYPE':"'GREGORIAN'"}
results=[];metadata=[]
for site in sites[:args.limit]:
 settings={**base,'SITE_COORD':"'%s,%s,%s'"%(site['lon'],site['lat'],site['height']/1000)}
 text='!$$SOF\n'+'\n'.join(k+'='+v for k,v in settings.items())+'\nTLIST= '+ '\n '.join("'%s'"%t for t in times)+'\n!$$EOF\n'
 key=hashlib.sha256(text.encode()).hexdigest();raw=cache/(key+'.json');(cache/(key+'.inp')).write_text(text)
 if not raw.exists():
  boundary='solar-time-domain-boundary';body=('--'+boundary+'\r\nContent-Disposition: form-data; name="format"\r\n\r\njson\r\n--'+boundary+'\r\nContent-Disposition: form-data; name="input"; filename="audit.inp"\r\nContent-Type: text/plain\r\n\r\n'+text+'\r\n--'+boundary+'--\r\n').encode()
  request=urllib.request.Request('https://ssd.jpl.nasa.gov/api/horizons_file.api',body,headers={'Content-Type':'multipart/form-data; boundary='+boundary,'User-Agent':'SolarTimeValidation/2.0 (https://github.com/triplewhopper)'})
  for attempt in range(3):
   try:
    with urllib.request.urlopen(request,timeout=120) as response:payload=response.read()
    raw.write_bytes(payload);break
   except Exception:
    if attempt==2:raise
    time.sleep(10*(attempt+1))
 obj=json.loads(raw.read_text());result=obj.get('result','')
 if obj.get('error') or '$$SOE' not in result:raise RuntimeError(str(obj)[:2000])
 lines=result.split('$$SOE')[1].split('$$EOE')[0].strip().splitlines();parsed=[]
 for line in lines:
  fields=next(csv.reader([line]));t=datetime.strptime(fields[0].strip(),'%Y-%b-%d %H:%M:%S.%f').replace(tzinfo=timezone.utc)
  parsed.append([int(round(t.timestamp()*1000)),float(fields[8])*3600,float(fields[10]),float(fields[3]),float(fields[4]),float(fields[5]),float(fields[6]),float(fields[7])*3600])
 if len(parsed)!=len(times):raise RuntimeError(f'Expected {len(times)} rows, got {len(parsed)} for site {site}')
 results.append({'site':site,'rows':parsed});metadata.append({'site_id':site['id'],'request_sha256':key,'response_sha256':hashlib.sha256(raw.read_bytes()).hexdigest(),'signature':obj.get('signature'),'eop_file':re.search(r'EOP file\s*:\s*(\S+)',result).group(1)})
 print(f"Site {site['id']+1}/{len(sites)}: {len(parsed)} cached reference rows",flush=True)
 (root/'tests/domain-horizons.json').write_text(json.dumps({'columns':['unix_ms','solar_seconds','dut1_sec','astrometric_ra_deg','astrometric_dec_deg','apparent_ra_deg','apparent_dec_deg','sidereal_seconds'],'source':'JPL Horizons, synthetic positions only','metadata':metadata,'results':results},separators=(',',':')))
print('Completed',sum(len(x['rows']) for x in results),'reference cases',flush=True)
