import base64
import io
import json
from pathlib import Path
import sys
import tarfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from desktop_control import LeaseController
from desktop_export import write_bundle
import handoff_export
import test_handoff_evidence


class HandoffExportTests(unittest.TestCase):
    def setUp(self):
        self.fixture = test_handoff_evidence.HandoffEvidenceTests()
        self.fixture.setUp(); self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.root
        self.materials, self.expected = self.fixture.fixture.materials, self.fixture.fixture.expected
        self.controller = LeaseController(self.root / 'lease.json', run_id=self.root.name,
            owner='worker', epoch=1, clock=lambda: 100)
        self.controller.revoke()

    def export(self):
        return handoff_export.build_bundle(self.root, self.controller, self.materials, self.expected)

    def test_original_evidence_tar_excludes_credentials_and_is_not_success(self):
        (self.root / 'control-token').write_text('SYNTHETIC_SECRET')
        original = {str(p): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        contents = self.export(); output = io.BytesIO(); write_bundle(contents, output)
        self.assertNotIn(b'SYNTHETIC_SECRET', output.getvalue())
        self.assertNotIn('lease.json', contents)
        manifest = json.loads(contents['guest-manifest.json'])
        self.assertEqual(manifest['binding'], self.fixture.binding)
        self.assertFalse(manifest['guest']['sessionVerified'])
        self.assertFalse(manifest['guest']['semanticVerified'])
        with tarfile.open(fileobj=io.BytesIO(output.getvalue())) as archive:
            self.assertEqual(set(archive.getnames()), set(contents))
            for member in archive:
                self.assertEqual(member.mode, 0o600)
                self.assertEqual(archive.extractfile(member).read(), contents[member.name])
        self.assertEqual(original, {str(p): p.read_bytes() for p in self.root.rglob('*') if p.is_file()})

    def test_missing_or_live_lease_denied(self):
        self.controller.path.unlink()
        with self.assertRaises(ValueError): self.export()
        self.controller.renew(1)
        with self.assertRaises(ValueError): self.export()

    def test_modified_evidence_or_unapproved_manifest_denied(self):
        original = handoff_export.inspect_handoff_evidence
        for mode in ('changed', 'secret'):
            def changed(*args, **kwargs):
                report = original(*args, **kwargs)
                if mode == 'changed': (self.root / 'result.txt').write_bytes(b'changed')
                else: report['files']['control-token'] = {}
                return report
            saved = (self.root / 'result.txt').read_bytes()
            with patch.object(handoff_export, 'inspect_handoff_evidence', side_effect=changed):
                with self.assertRaises(ValueError): self.export()
            (self.root / 'result.txt').write_bytes(saved)

    def test_lease_changed_after_read_denied(self):
        lease = self.controller.existing()
        with patch.object(self.controller, 'existing', side_effect=[lease, dict(lease, epoch=2)]):
            with self.assertRaises(ValueError): self.export()

    def test_bounded_strict_input(self):
        value = dict(materialsBase64=base64.b64encode(self.materials).decode(),
                     expectedBase64=base64.b64encode(self.expected).decode())
        parse = lambda raw: handoff_export.input_from_stream(io.BytesIO(raw))
        self.assertEqual(parse(json.dumps(value).encode()), (self.materials, self.expected))
        for bad in (dict(value, path='/tmp'), dict(value, expectedBase64='!'),
                    dict(value, materialsBase64=''), dict(value, expectedBase64=base64.b64encode(b'x'*4097).decode())):
            with self.assertRaises(ValueError): parse(json.dumps(bad).encode())
        for raw in (b'x' * (512*1024+1), b'{"expectedBase64":"a","expectedBase64":"b"}'):
            with self.assertRaises(ValueError): parse(raw)

    def test_cli_refuses_host_before_reading_input(self):
        with patch.object(handoff_export, 'require_vm', side_effect=ValueError), patch.object(handoff_export, 'input_from_stream') as read:
            self.assertEqual(handoff_export.main(['--run', self.root.name, '--owner', 'bad', '--epoch', '1']), 1)
            read.assert_not_called()
