import copy
import json
import tempfile
import unittest
from pathlib import Path
from applynix.core import Store, analyze, prepare, verify, export

PROFILE = {'personal': {'name': 'Example'}, 'skills': ['Linux', 'Windows', 'DNS'], 'experience': [{'title': 'Trainee', 'company': 'Example', 'bullets': ['Worked with Linux.', 'Troubleshot Windows.']}], 'certifications': []}
JD = 'Company: Test\nTitle: Support\nRequirements:\nWindows and DNS required.\nPreferred:\nServiceNow preferred.'

class Tests(unittest.TestCase):
    def test_requirement_weights_and_missing(self):
        result = analyze(JD, PROFILE)
        self.assertEqual(result['keyword_match'], 86)
        self.assertEqual([r['skill'] for r in result['requirements'] if not r['matched']], ['ServiceNow'])
    def test_unrecognized_is_unknown_not_perfect(self):
        self.assertIsNone(analyze('Great communication required', PROFILE)['keyword_match'])
    def test_substring_not_skill(self):
        self.assertIsNone(analyze('draws diagrams', PROFILE)['keyword_match'])
    def test_extract_preserves_words_and_reorders(self):
        draft = prepare(PROFILE, JD)
        self.assertLess(draft['resume'].index('Windows'), draft['resume'].index('Linux'))
        self.assertNotIn('ServiceNow', draft['resume'])
        verify(draft)
    def test_reject_modified_claim_or_render(self):
        for key in ('resume', 'claims', 'analysis'):
            draft = prepare(PROFILE, JD)
            if key == 'resume': draft[key] += '\nCertified expert'
            elif key == 'claims': draft[key][0]['text'] = 'Invented'
            else: draft[key]['keyword_match'] = 100
            with self.assertRaises(ValueError): verify(draft)
    def test_snapshot_tamper_rejected(self):
        draft = prepare(PROFILE, JD)
        draft['profile_snapshot']['skills'].append('ServiceNow')
        with self.assertRaises(ValueError): verify(draft)
    def test_approval_and_manual_receipt(self):
        with tempfile.TemporaryDirectory() as d:
            store = Store(Path(d) / 'db')
            identity = store.save(prepare(PROFILE, JD))
            self.assertEqual(identity, store.save(prepare(PROFILE, JD)))
            self.assertEqual(len(store.list()), 1)
            with self.assertRaises(ValueError): store.status(identity, 'APPLIED', 'receipt')
            store.status(identity, 'READY')
            with self.assertRaises(ValueError): store.status(identity, 'APPLIED')
            store.status(identity, 'APPLIED', 'Manually submitted; receipt #123')
            store.status(identity, 'INTERVIEW')
            self.assertEqual(len(store.events(identity)), 4)
    def test_storage_tamper_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            store = Store(Path(d) / 'db')
            identity = store.save(prepare(PROFILE, JD))
            store.db.execute('UPDATE applications SET bundle=? WHERE id=?', ('{}', identity))
            with self.assertRaises(ValueError): store.get(identity)
    def test_export_escapes_html(self):
        profile = copy.deepcopy(PROFILE); profile['personal']['name'] = '<script>alert(1)</script>'
        with tempfile.TemporaryDirectory() as d:
            export(prepare(profile, JD), d)
            html = (Path(d) / 'resume.html').read_text()
            self.assertNotIn('<script>', html)
            self.assertIn('&lt;script&gt;', html)
    def test_required_beats_preferred(self):
        result = analyze('Required:\nWindows\nPreferred:\nWindows and Linux', PROFILE)
        self.assertEqual(len(result['requirements']), 2)
        self.assertEqual(next(r for r in result['requirements'] if r['skill'] == 'Windows')['classification'], 'required')

if __name__ == '__main__': unittest.main()
