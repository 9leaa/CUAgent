import io
import json
from pathlib import Path
import sys
import tarfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from desktop_control import LeaseController
from desktop_export import build_bundle, expected_from_stream, write_bundle
import desktop_export
import test_desktop_evidence


class ExportTests(unittest.TestCase):
    def setUp(self):
        self.fixture = test_desktop_evidence.DesktopEvidenceTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.root
        self.controller = LeaseController(self.root / 'lease.json', run_id='task', owner='owner', epoch=1,
                                          clock=lambda: 100)
        self.controller.revoke()

    def test_real_tar_has_only_verified_files_and_no_credentials(self):
        (self.root / 'bridge-token').write_text('SYNTHETIC_SECRET')
        (self.root / 'control-token').write_text('OTHER_SYNTHETIC_SECRET')
        contents = build_bundle(self.root, self.controller, self.fixture.expected)
        output = io.BytesIO()
        write_bundle(contents, output)
        self.assertNotIn(b'SYNTHETIC_SECRET', output.getvalue())
        with tarfile.open(fileobj=io.BytesIO(output.getvalue())) as archive:
            self.assertEqual(set(archive.getnames()), set(contents))
            for member in archive:
                self.assertTrue(member.isfile())
                self.assertEqual(member.mode, 0o600)
                self.assertEqual(archive.extractfile(member).read(), contents[member.name])
        manifest = json.loads(contents['guest-manifest.json'])
        self.assertFalse(manifest['guest']['sessionVerified'])
        self.assertEqual(manifest['binding']['owner'], 'owner')

    def test_live_or_missing_lease_cannot_export(self):
        self.controller.path.unlink()
        with self.assertRaises(ValueError):
            build_bundle(self.root, self.controller, self.fixture.expected)
        self.controller.renew(1)
        with self.assertRaises(ValueError):
            build_bundle(self.root, self.controller, self.fixture.expected)

    def test_changed_source_after_verification_refused_before_output(self):
        original = desktop_export.inspect_guest_evidence
        def verify_then_change(*args, **kwargs):
            report = original(*args, **kwargs)
            (self.root / 'result.txt').write_bytes(b'changed')
            return report
        with patch.object(desktop_export, 'inspect_guest_evidence', side_effect=verify_then_change):
            with self.assertRaises(ValueError):
                build_bundle(self.root, self.controller, self.fixture.expected)

    def test_unapproved_manifest_paths_cannot_export_secrets(self):
        original = desktop_export.inspect_guest_evidence
        def bad_manifest(*args, **kwargs):
            report = original(*args, **kwargs)
            report['files']['control-token'] = {'sha256': 'unused', 'bytes': 0}
            return report
        with patch.object(desktop_export, 'inspect_guest_evidence', side_effect=bad_manifest):
            with self.assertRaises(ValueError):
                build_bundle(self.root, self.controller, self.fixture.expected)

    def test_expected_contract_and_limits(self):
        self.assertEqual(expected_from_stream(io.BytesIO(json.dumps({'lines': ['你好', 'ok']}).encode())), '你好\nok\n'.encode())
        for value in [{'lines': []}, {'lines': ['bad\nline']}, {'lines': ['x'], 'path': '/other'},
                      {'lines': ['x' * 4096]}, {'lines': [1]}, {'lines': ['\u200b']}]:
            with self.assertRaises(ValueError):
                expected_from_stream(io.BytesIO(json.dumps(value).encode()))
        with self.assertRaises(ValueError):
            expected_from_stream(io.BytesIO(b'x' * 32769))


if __name__ == '__main__':
    unittest.main()
