import importlib.util, unittest
from pathlib import Path
p=Path(__file__).resolve().parents[1]/'scripts/update-eop.py'
spec=importlib.util.spec_from_file_location('updater',p);u=importlib.util.module_from_spec(spec);spec.loader.exec_module(u)
class UpdateGates(unittest.TestCase):
    def test_missing_or_different_reference_release_is_rejected(self):
        for text in ['', 'EOP file : eop.261117.p270213', 'EOP file : eop.261118.p270215']:
            with self.assertRaises(ValueError):u.check_reference_version(text,'eop.261118.p270214')
        u.check_reference_version('EOP file : eop.261118.p270214','eop.261118.p270214')
    def test_wrong_frame_or_truncated_data_is_rejected(self):
        raw=(p.parents[1]/'data/eop-2026-11-17.long').read_bytes()
        observed,rows=u.parse_ascii(raw);self.assertGreater(len(rows),10000)
        self.assertEqual(observed.date().isoformat(),'2026-11-17')
        for bad in [raw.replace(b'ITRF93',b'ITRF08'),raw[:500]]:
            with self.assertRaises(ValueError):u.parse_ascii(bad)
    def test_kernel_selection_uses_observation_date_not_forecast_end(self):
        index='<a href="earth_000101_270214_261118.bpc">x</a><a href="earth_000101_280214_261117.bpc">x</a>'
        self.assertEqual(u.latest_kernel(index)[0],'earth_000101_270214_261118.bpc')
        with self.assertRaises(ValueError):u.latest_kernel('<html>unavailable</html>')
if __name__=='__main__':unittest.main()
