import io,json,os,runpy,subprocess,unittest
from pathlib import Path
from unittest.mock import patch,Mock
SCRIPT=Path(__file__).resolve().parents[1]/'scripts/pages-build.py'
class PagesChecks(unittest.TestCase):
    def run_build(self,manifests,source=None):
        expected={'eop_sha256':'new','checked_at':'today'}
        settings={'build_type':'legacy','source':source or {'branch':'main','path':'/'},'html_url':'https://example.test/solar/'}
        def output(args,**kwargs):
            if args[:2]==['git','rev-parse']:return 'abc123\n'
            if args[-1].endswith('/pages'):return json.dumps(settings)
            if args[-1].endswith('/pages/builds'):return '{"status":"queued"}'
            self.fail('Unexpected request '+str(args))
        with patch.dict(os.environ,{'GITHUB_REPOSITORY':'test/solar'}),patch('subprocess.check_output',side_effect=output),patch('subprocess.run',return_value=subprocess.CompletedProcess([],0,'{"status":"succeed"}','')),patch.object(Path,'read_text',return_value=json.dumps(expected)),patch('urllib.request.urlopen',side_effect=[io.StringIO(json.dumps(m)) for m in manifests]) as download,patch('time.sleep') as sleep:
            runpy.run_path(str(SCRIPT),run_name='__main__')
            return download.call_count,sleep.call_count
    def test_actual_deployment_and_manifest_both_required(self):
        self.assertEqual(self.run_build([{'eop_sha256':'old'},{'eop_sha256':'new','checked_at':'today'}]),(2,1))
    def test_matching_deployment_does_not_use_legacy_build_status(self):
        self.assertEqual(self.run_build([{'eop_sha256':'new','checked_at':'today'}]),(1,0))
    def test_unexpected_publishing_source_stops(self):
        with self.assertRaises(RuntimeError):self.run_build([],{'branch':'other','path':'/'})
if __name__=='__main__':unittest.main()
