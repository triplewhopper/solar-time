import hashlib,importlib.util,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
p=Path(__file__).resolve().parents[1]/'scripts/update-eop.py'
spec=importlib.util.spec_from_file_location('noop_updater',p);u=importlib.util.module_from_spec(spec);spec.loader.exec_module(u)
class NoWrites(unittest.TestCase):
 def test_same_data_does_not_touch_published_timestamps(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);(root/'data').mkdir();raw=b'original';kernel=b'DAF/PCKtest';sha=lambda b:hashlib.sha256(b).hexdigest()
   data={'legacy':{'last_observation_utc':'2026-11-18T00:00:00Z'},'reconstructed':{'base_sha256':sha(raw),'pck_sha256':sha(kernel),'source_sha256':sha(raw),'release_label':'test'}}
   (root/'data/eop.json').write_text(json.dumps(data));(root/'data/runtime.json').write_text('{"checked_at":"old"}');(root/'data/update-status.json').write_text('{"checked_at":"old"}')
   before={p.name:p.read_bytes() for p in (root/'data').iterdir()}
   with patch.object(u,'ROOT',root),patch.object(sys,'argv',['update-eop.py']),patch.object(u,'fetch',side_effect=[raw,b'index',kernel]),patch.object(u,'parse_ascii',return_value=(u.date('2026-11-18'),[])),patch.object(u,'latest_kernel',return_value=('earth_000101_270214_261118.bpc',u.date('2027-02-14'),u.date('2026-11-18'))),patch.object(u,'write_json',side_effect=AssertionError('Unexpected write')),patch.object(u,'runtime_manifest',side_effect=AssertionError('Unexpected manifest update')):
    u.main()
   self.assertEqual(before,{p.name:p.read_bytes() for p in (root/'data').iterdir()})
if __name__=='__main__':unittest.main()
