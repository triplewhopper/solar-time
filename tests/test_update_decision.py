import importlib.util,tempfile,unittest
from pathlib import Path
p=Path(__file__).resolve().parents[1]/'scripts/check-update.py'
spec=importlib.util.spec_from_file_location('check_update',p);c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
class Decisions(unittest.TestCase):
 def test_unchanged_skips_full_validation(self):
  self.assertEqual(c.decision({'base_sha256':'a','source_sha256':'p'},'a','p','code',{'algorithm_sha256':'code'}),{'data_changed':False,'algorithm_changed':False,'needs_validation':False})
 def test_data_or_algorithm_change_each_requires_validation(self):
  for a,p,code in [('new','p','code'),('a','new','code'),('a','p','new')]:
   self.assertTrue(c.decision({'base_sha256':'a','source_sha256':'p'},a,p,code,{'algorithm_sha256':'code'})['needs_validation'])
 def test_missing_success_state_requires_validation(self):
  self.assertTrue(c.decision({'base_sha256':'a','source_sha256':'p'},'a','p','code',{})['algorithm_changed'])
 def test_fingerprint_tracks_nested_fixtures_but_not_daily_status(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);(root/'tests/nested').mkdir(parents=True);(root/'data').mkdir()
   f=root/'tests/nested/fixture.json';f.write_text('one');before=c.fingerprint(root)
   (root/'data/runtime.json').write_text('new daily timestamp');self.assertEqual(before,c.fingerprint(root))
   f.write_text('two');self.assertNotEqual(before,c.fingerprint(root))
if __name__=='__main__':unittest.main()
