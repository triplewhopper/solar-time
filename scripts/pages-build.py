"""Explicit Pages build for GITHUB_TOKEN commits; keeps legacy branch publishing.
The legacy builds endpoint can report errored even after a successful deployment.
Confirm the actual deployment revision AND its published runtime manifest instead.
"""
import json, os, subprocess, time, urllib.request
from pathlib import Path
repo=os.environ['GITHUB_REPOSITORY']
def api(*args): return json.loads(subprocess.check_output(['gh','api',*args],text=True))
settings=api(f'repos/{repo}/pages')
if settings['build_type']!='legacy' or settings['source']!={'branch':'main','path':'/'}:
    raise RuntimeError('Unexpected Pages source; refuse to change hosting configuration')
head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
expected=json.loads(Path('data/runtime.json').read_text())
api('--method','POST',f'repos/{repo}/pages/builds')
url=settings['html_url'].rstrip('/')+'/data/runtime.json?revision='+head
for _ in range(60):
    result=subprocess.run(['gh','api',f'repos/{repo}/pages/deployments/{head}'],capture_output=True,text=True)
    status=json.loads(result.stdout).get('status') if result.returncode==0 else None
    if status=='succeed':
        try:
            with urllib.request.urlopen(url,timeout=30) as response:actual=json.load(response)
            if actual==expected: print('Published branch commit and runtime manifest verified:',head);break
        except Exception as e: print('Waiting for published manifest:',type(e).__name__)
    elif status in ['deployment_failed','deployment_content_failed','deployment_cancelled']:
        raise RuntimeError('Actual Pages deployment failed: '+status)
    time.sleep(10)
else: raise RuntimeError('Pages did not confirm the committed revision and runtime manifest within 10 minutes')
