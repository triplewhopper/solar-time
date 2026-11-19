"""Explicit Pages build for GITHUB_TOKEN commits; keeps legacy branch publishing."""
import json, os, subprocess, time
repo=os.environ['GITHUB_REPOSITORY']
def api(*args): return json.loads(subprocess.check_output(['gh','api',*args],text=True))
settings=api(f'repos/{repo}/pages')
if settings['build_type']!='legacy' or settings['source']!={'branch':'main','path':'/'}:
    raise RuntimeError('Unexpected Pages source; refuse to change hosting configuration')
head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
api('--method','POST',f'repos/{repo}/pages/builds')
for _ in range(60):
    build=api(f'repos/{repo}/pages/builds/latest')
    if build.get('commit')==head:
        if build['status']=='built': print('Published branch commit',head);break
        if build['status']=='errored': raise RuntimeError(str(build.get('error')))
    time.sleep(10)
else: raise RuntimeError('Pages did not confirm the committed revision within 10 minutes')
