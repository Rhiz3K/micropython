#!/usr/bin/env python3
"""Exercise dependency preparation in disposable clones; never touch a device."""

import hashlib
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

BUNDLE = Path(__file__).resolve().parents[1]
REPO = BUNDLE.parents[1]
PINNED_HEAD = "b549ac1d84cbbe550c9590951e2290098b3fb16c"
ENV = {
    key: value
    for key, value in os.environ.items()
    if key not in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR")
}


def git(directory, *args):
    return subprocess.run(
        ["git", "-C", str(directory), *args],
        env=ENV,
        capture_output=True,
        check=True,
    ).stdout


class PrepareTinyUSBTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="tinyusb-prepare-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        git(self.root, "init", "-q")
        bundle = self.root / "experiments/rp2350-deepsleep"
        bundle.mkdir(parents=True)
        self.script = bundle / "prepare-tinyusb.sh"
        self.patch = bundle / "tinyusb-ep0-queue.patch"
        shutil.copyfile(BUNDLE / self.script.name, self.script)
        shutil.copyfile(BUNDLE / self.patch.name, self.patch)
        self.tinyusb = self.root / "lib/tinyusb"
        self.tinyusb.parent.mkdir()
        # --shared borrows immutable objects, not files/index from the working tree.
        git(
            self.root,
            "clone",
            "-q",
            "--shared",
            "--no-checkout",
            str(REPO / "lib/tinyusb"),
            str(self.tinyusb),
        )
        git(self.tinyusb, "checkout", "-q", "--detach", PINNED_HEAD)

    def run_script(self, path=None, env=None):
        return subprocess.run(
            ["bash", str(path or self.script)],
            cwd=self.temp.name,
            env=env or ENV,
            capture_output=True,
            text=True,
            check=False,
        )

    def assert_refused(self, message):
        before = git(self.tinyusb, "diff", "--binary", "HEAD")
        result = self.run_script()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(message, result.stderr)
        self.assertEqual(git(self.tinyusb, "diff", "--binary", "HEAD"), before)

    def test_clean_apply_and_exact_idempotence(self):
        index = self.tinyusb / ".git/index"
        before_index = hashlib.sha256(index.read_bytes()).hexdigest()
        result = self.run_script()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("applied and verified", result.stdout)
        git(self.tinyusb, "apply", "--reverse", "--check", str(self.patch))
        first_diff = git(self.tinyusb, "diff", "--binary", "HEAD")
        result = self.run_script()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("already applied", result.stdout)
        self.assertEqual(git(self.tinyusb, "diff", "--binary", "HEAD"), first_diff)
        self.assertEqual(git(self.tinyusb, "rev-parse", "HEAD").decode().strip(), PINNED_HEAD)
        self.assertEqual(hashlib.sha256(index.read_bytes()).hexdigest(), before_index)

    def test_unrelated_tracked_change_is_preserved(self):
        path = self.tinyusb / "README.rst"
        path.write_bytes(path.read_bytes() + b"\nUnrelated change.\n")
        self.assert_refused("differ from the exact reviewed patch")

    def test_applied_patch_with_additional_whitespace_is_refused(self):
        self.assertEqual(self.run_script().returncode, 0)
        path = self.tinyusb / "src/device/usbd.c"
        path.write_bytes(path.read_bytes() + b"\n")
        self.assert_refused("differ from the exact reviewed patch")

    def test_untracked_and_ignored_files_are_preserved(self):
        path = self.tinyusb / "private-notes.tmp"
        path.write_text("Do not remove.\n")
        self.assert_refused("untracked files")
        (self.tinyusb / ".git/info/exclude").write_text("private-notes.tmp\n")
        self.assert_refused("untracked files")
        self.assertEqual(path.read_text(), "Do not remove.\n")

    def test_staged_changes_are_preserved(self):
        path = self.tinyusb / "README.rst"
        path.write_bytes(path.read_bytes() + b"\nStaged change.\n")
        git(self.tinyusb, "add", "README.rst")
        before = git(self.tinyusb, "diff", "--cached", "--binary")
        self.assert_refused("staged changes")
        self.assertEqual(git(self.tinyusb, "diff", "--cached", "--binary"), before)

    def test_wrong_head_is_not_changed(self):
        git(self.tinyusb, "checkout", "-q", "--detach", "HEAD^")
        before = git(self.tinyusb, "rev-parse", "HEAD")
        self.assert_refused("HEAD does not match")
        self.assertEqual(git(self.tinyusb, "rev-parse", "HEAD"), before)

    def test_modified_patch_is_refused(self):
        self.patch.write_bytes(self.patch.read_bytes() + b"\n")
        self.assert_refused("unexpected SHA-256")

    def test_wrong_script_location_is_refused(self):
        misplaced = self.root / self.script.name
        shutil.copyfile(self.script, misplaced)
        result = self.run_script(misplaced)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Run the script stored in this checkout", result.stderr)
        self.assertEqual(git(self.tinyusb, "diff", "HEAD"), b"")

    def test_uninitialized_dependency_is_not_initialized(self):
        shutil.rmtree(self.tinyusb)
        self.tinyusb.mkdir()
        result = self.run_script()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Initialize rp2 submodules first", result.stderr)
        self.assertEqual(list(self.tinyusb.iterdir()), [])

    def test_git_environment_override_is_refused(self):
        result = self.run_script(env={**ENV, "GIT_INDEX_FILE": str(self.root / "other-index")})
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Unset GIT_INDEX_FILE", result.stderr)
        self.assertFalse((self.root / "other-index").exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
