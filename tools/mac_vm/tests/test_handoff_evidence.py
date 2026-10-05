"""Simulated producer evidence only; no model, VM, or semantic acceptance."""
import hashlib
import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import test_handoff_trace
from handoff_evidence import inspect_handoff_evidence


class HandoffEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.fixture = test_handoff_trace.HandoffTraceTests()
        self.addCleanup(self.fixture.doCleanups)
        self.fixture.setUp()
        self.root = self.fixture.task.directory
        self.binding = dict(version=1, runId=self.fixture.run, owner='worker', epoch=1)
        for name, status in [('handoff-input-intent.json', 'INTENT'), ('handoff-input-receipt.json', 'STORED')]:
            path = self.root / name
            path.write_text(json.dumps(dict(status=status, binding=self.binding,
                inputSha256=hashlib.sha256(self.fixture.materials).hexdigest(), bytes=len(self.fixture.materials))))
            path.chmod(0o600)

    def inspect(self):
        return inspect_handoff_evidence(self.root, binding=self.binding,
            materials=self.fixture.materials, expected=self.fixture.expected)

    def test_complete_simulated_evidence_is_readonly_and_not_business_success(self):
        original = {str(p): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        result = self.inspect()
        self.assertEqual(result['status'], 'VM_EVIDENCE_VERIFIED')
        self.assertTrue(result['filesVerified'])
        self.assertFalse(result['sessionVerified']); self.assertFalse(result['semanticVerified'])
        self.assertEqual(result['rawCalls'], 15)
        self.assertEqual(len(result['files']), 16)
        self.assertEqual(original, {str(p): p.read_bytes() for p in self.root.rglob('*') if p.is_file()})

    def test_tampered_material_trace_state_png_final_document_or_result_denied(self):
        names = ['handoff-input.json', 'trace.jsonl', 'state-04.json', 'state-04.png',
                 'final_state.json', 'artifacts/handoff-' + self.fixture.run + '.txt', 'result.txt']
        for name in names:
            path = self.root / name; original = path.read_bytes()
            path.write_bytes(original + b'x')
            with self.subTest(name=name), self.assertRaises((ValueError, KeyError)): self.inspect()
            path.write_bytes(original)

    def test_original_binding_and_receipt_fields_checked(self):
        path = self.root / 'handoff-input-receipt.json'; original = path.read_bytes()
        for field in ('owner', 'epoch', 'version', 'bytes', 'sha', 'status', 'extra'):
            value = json.loads(original)
            if field == 'owner': value['binding']['owner'] = 'other'
            elif field == 'epoch': value['binding']['epoch'] = 2
            elif field == 'version': value['binding']['version'] = True
            elif field == 'bytes': value['bytes'] += 1
            elif field == 'sha': value['inputSha256'] = '0' * 64
            elif field == 'status': value['status'] = 'INTENT'
            else: value['extra'] = True
            path.write_text(json.dumps(value))
            with self.subTest(field=field), self.assertRaises(ValueError): self.inspect()
        path.write_bytes(original)

    def test_reopen_intent_is_not_a_replaceable_claim(self):
        path = self.root / 'handoff-reopen-intent.json'; original = path.read_bytes()
        for field, value in [('pid', 99), ('window_id', 99), ('sha256', '0' * 64), ('snapshot_id', '1')]:
            record = json.loads(original); record[field] = value
            path.write_text(json.dumps(record))
            with self.subTest(field=field), self.assertRaises(ValueError): self.inspect()
        path.write_bytes(original)

    def test_duplicate_keys_nonfinite_and_numeric_type_substitution_denied(self):
        path = self.root / 'final_state.json'; original = path.read_bytes()
        for payload in (b'{"pid":10,"pid":10}', b'{"pid":NaN}',
                        original.replace(b'"element_index": 1', b'"element_index": true')):
            path.write_bytes(payload)
            with self.subTest(payload=payload[:40]), self.assertRaises(ValueError): self.inspect()
        path.write_bytes(original)

    def test_missing_private_and_oversized_files_denied(self):
        path = self.root / 'handoff-input.json'
        path.chmod(0o644)
        with self.assertRaises(ValueError): self.inspect()
        path.chmod(0o600)
        result = self.root / 'result.txt'; original = result.read_bytes()
        result.write_bytes(b'x' * 4098)
        with self.assertRaises(ValueError): self.inspect()
        result.unlink()
        with self.assertRaises(FileNotFoundError): self.inspect()
        result.write_bytes(original)

    def test_symlink_hardlink_fifo_and_symlink_directory_denied(self):
        path = self.root / 'result.txt'; original = path.read_bytes()
        target = self.root.parent / 'external'; target.write_bytes(original)
        for kind in ('symlink', 'hardlink', 'fifo'):
            path.unlink()
            if kind == 'symlink': path.symlink_to(target)
            elif kind == 'hardlink': os.link(target, path)
            else: os.mkfifo(path)
            with self.subTest(kind=kind), self.assertRaises((ValueError, OSError)): self.inspect()
        path.unlink(); path.write_bytes(original)
        directory = self.root / 'artifacts'; moved = self.root / 'original-artifacts'
        directory.rename(moved); directory.symlink_to(moved, target_is_directory=True)
        with self.assertRaises((ValueError, OSError)): self.inspect()

    def test_change_after_first_read_is_caught_before_return(self):
        real_open = os.open
        changed = False
        def changing_open(name, *args, **kwargs):
            nonlocal changed
            if name == 'result.txt' and not changed:
                changed = True
                path = self.root / 'handoff-input.json'
                path.write_bytes(path.read_bytes() + b' ')
            return real_open(name, *args, **kwargs)
        with patch('handoff_evidence.os.open', side_effect=changing_open):
            with self.assertRaises(ValueError): self.inspect()
        self.assertTrue(changed)

    def test_root_permissions_and_wrong_trusted_identity_denied(self):
        self.root.chmod(0o755)
        with self.assertRaises(ValueError): self.inspect()
        self.root.chmod(0o700)
        self.binding['owner'] = 'other'
        with self.assertRaises(ValueError): self.inspect()

    def test_same_bytes_replacement_is_not_the_original_file(self):
        real_open = os.open
        replaced = False
        def replacing_open(name, *args, **kwargs):
            nonlocal replaced
            if name == 'result.txt' and not replaced:
                replaced = True
                path = self.root / 'handoff-input.json'
                original = path.read_bytes()
                path.rename(self.root / 'retained-original-input.json')
                path.write_bytes(original); path.chmod(0o600)
            return real_open(name, *args, **kwargs)
        with patch('handoff_evidence.os.open', side_effect=replacing_open):
            with self.assertRaises(ValueError): self.inspect()
        self.assertTrue(replaced)


if __name__ == '__main__': unittest.main()
