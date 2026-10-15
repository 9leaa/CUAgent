"""Compile/CLI checks only. Never exercise host desktop APIs."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


@unittest.skipUnless(sys.platform == 'darwin', 'macOS compiler required')
class NativePointProbeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory(prefix='cuagent-point-probe-')
        cls.binary = str(Path(cls.directory.name) / 'probe')
        cls.source = Path(__file__).resolve().parents[1] / 'native_point_probe.m'
        subprocess.run(['xcrun', 'clang', '-fobjc-arc', '-Wall', '-Wextra', '-Werror',
                        '-framework', 'Foundation', '-framework', 'ApplicationServices',
                        str(cls.source), '-o', cls.binary], check=True, timeout=60,
                       capture_output=True)

    @classmethod
    def tearDownClass(cls):
        cls.directory.cleanup()

    def call(self, *args):
        result = subprocess.run([self.binary, *args], capture_output=True, timeout=5)
        return result.returncode, json.loads(result.stdout)

    def test_valid_arguments_do_not_query_native_desktop(self):
        for args in [('360', '176.5', '468', '123'), ('-1', '0', '1', '4294967295')]:
            code, result = self.call('--validate', *args)
            self.assertEqual(code, 0)
            self.assertEqual(result, {'status': 'VALIDATED_ONLY', 'diagnosticOnly': True,
                                      'nativeQueries': 0})

    def test_malformed_arguments_are_rejected_before_native_queries(self):
        for args in [(), ('--observe',), ('--input', '1', '2', '3', '4'),
                     ('--validate', '', '2', '3', '4'),
                     ('--validate', 'nan', '2', '3', '4'),
                     ('--validate', '1e309', '2', '3', '4'),
                     ('--validate', '1e39', '2', '3', '4'),
                     ('--validate', '1junk', '2', '3', '4'),
                     ('--validate', '1', '2', '3.5', '4'),
                     ('--validate', '1', '2', '0', '4'),
                     ('--validate', '1', '2', '2147483648', '4'),
                     ('--validate', '1', '2', '3', '4294967296')]:
            with self.subTest(args=args):
                code, result = self.call(*args)
                self.assertEqual(code, 64)
                self.assertEqual(result['reason'], 'INVALID_ARGUMENTS')

    def test_host_refuses_observation(self):
        # Do not run this test as the VM account: that would be a live diagnostic.
        import getpass
        if getpass.getuser() == 'mvpagent':
            self.skipTest('host-only rejection check')
        code, result = self.call('--observe', '360', '176.5', '468', '123')
        self.assertEqual(code, 77)
        self.assertEqual(result['reason'], 'VM_IDENTITY_REQUIRED')

    def test_binary_has_no_input_or_permission_prompt_imports(self):
        symbols = subprocess.check_output(['nm', '-u', self.binary], text=True)
        for forbidden in ['CGEventPost', 'AXUIElementPerformAction',
                          'AXUIElementSetAttributeValue', 'AXIsProcessTrustedWithOptions',
                          'CGRequestScreenCaptureAccess']:
            self.assertNotIn(forbidden, symbols)

    def test_real_deadline_exits_without_desktop_queries(self):
        binary = str(Path(self.directory.name) / 'timeout-probe')
        subprocess.run(['xcrun', 'clang', '-fobjc-arc', '-Wall', '-Wextra', '-Werror',
                        '-framework', 'Foundation', '-framework', 'ApplicationServices',
                        str(Path(__file__).with_name('native_point_timeout.m')), '-o', binary],
                       check=True, timeout=60, capture_output=True)
        process = subprocess.Popen([binary], stdout=subprocess.PIPE)
        try:
            output, _ = process.communicate(timeout=6)
            self.assertEqual(process.returncode, 124)
            self.assertEqual(json.loads(output), {'status': 'UNKNOWN', 'reason': 'NATIVE_TIMEOUT',
                                                  'diagnosticOnly': True})
        finally:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=2)


if __name__ == '__main__':
    unittest.main()
