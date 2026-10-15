"""Native preflight rejection tests; never launch an application or request TCC."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


@unittest.skipUnless(sys.platform == "darwin", "macOS native launcher")
class PermissionHelperLauncherTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.build = tempfile.TemporaryDirectory(prefix="cuagent-launcher-tests-")
        cls.binary = Path(cls.build.name) / "launcher"
        source = Path(__file__).resolve().parents[1] / "permission_helper_launcher.swift"
        subprocess.run(["xcrun", "swiftc", str(source), "-o", str(cls.binary)],
                       check=True, capture_output=True, timeout=120)

    @classmethod
    def tearDownClass(cls):
        cls.build.cleanup()

    def reject(self, args, reason):
        response = subprocess.run([str(self.binary), *args], capture_output=True,
                                  text=True, timeout=10)
        self.assertEqual(response.returncode, 2, response.stderr)
        self.assertEqual(json.loads(response.stdout), {"result": "REJECTED", "reason": reason})

    def test_missing_argument(self):
        self.reject([], "EXPECTED_RESULT_FILE_ARGUMENT")

    def test_extra_argument(self):
        self.reject(["--result-file", "/tmp/no.json", "--retry"], "EXPECTED_RESULT_FILE_ARGUMENT")

    def test_missing_file(self):
        with tempfile.TemporaryDirectory() as directory:
            self.reject(["--result-file", str(Path(directory) / "cua-driver-permissions-no.json")],
                        "UNSAFE_RESULT_FILE")

    def test_nonempty_file_preserved(self):
        with tempfile.NamedTemporaryFile(prefix="cua-driver-permissions-", suffix=".json") as f:
            f.write(b"original"); f.flush()
            self.reject(["--result-file", f.name], "UNSAFE_RESULT_FILE")
            self.assertEqual(Path(f.name).read_bytes(), b"original")

    def test_public_file_preserved(self):
        with tempfile.NamedTemporaryFile(prefix="cua-driver-permissions-", suffix=".json") as f:
            os.chmod(f.name, 0o644)
            self.reject(["--result-file", f.name], "UNSAFE_RESULT_FILE")
            self.assertEqual(Path(f.name).read_bytes(), b"")

    def test_symlink_rejected(self):
        with tempfile.NamedTemporaryFile(prefix="cua-driver-permissions-", suffix=".json") as f:
            link = f.name + ".link.json"
            try:
                os.symlink(f.name, link)
                self.reject(["--result-file", link], "UNSAFE_RESULT_FILE")
            finally:
                os.unlink(link)


if __name__ == "__main__":
    unittest.main()
