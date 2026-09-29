#!/usr/bin/env python3
# The MIT License (MIT). Copyright (c) 2026 MicroPython contributors.
"""Offline tests in disposable repositories; no real index, snapshots or devices changed."""

import hashlib
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import generate_patches as generator


class GeneratePatchesTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="patch-generator-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.git("init", "-q")
        self.git("config", "user.name", "Synthetic Fixture")
        self.git("config", "user.email", "fixture@example.invalid")
        self.put(".gitignore", "build*/\n__pycache__/\n*.pyc\n")
        self.put(".gitattributes", "*.c diff=hostile\n")
        self.put("ports/rp2/modmachine.c", "int counter(void) {\n    return 0;\n}\n")
        self.put("docs/rp2/quickref.rst", "Before\n======\n")
        self.put("docs/library/machine.rst", "Old documentation.\n")
        self.put("experiments/private-note.txt", "Outside patch scope.\n")
        self.git("add", ".")
        self.git("commit", "-qm", "base")
        self.base = self.git("rev-parse", "HEAD").decode().strip()
        self.put("ports/rp2/modmachine.c", "int counter(void) {\n    return 1;\n}\n")
        self.put("ports/rp2/new_helper.c", "int helper(void) { return 2; }\n")
        self.put("docs/rp2/quickref.rst", "After\n=====\n")
        self.put("tests/ports/rp2/deepsleep/device.py", "print('synthetic fixture')\n")
        self.put("experiments/private-note.txt", "Still outside scope.\n")
        self.git("add", ".")
        self.git("commit", "-qm", "scoped changes and unrelated experiment")
        self.output = self.root / generator.BUNDLE
        self.output.mkdir(parents=True)
        self.index_before = (self.root / ".git/index").read_bytes()

    def git(self, *args, input=None, index=None):
        env = generator.git_environment()
        if index is not None:
            env["GIT_INDEX_FILE"] = str(index)
        return subprocess.run(
            ["git", "-C", str(self.root), *args],
            input=input,
            env=env,
            capture_output=True,
            check=True,
        ).stdout

    def put(self, name, text):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        return path

    def snapshots(self):
        return generator.snapshots(self.root, self.base)

    def update(self, write=False):
        return generator.update(self.root, write=write, base=self.base)

    def test_exact_scopes_apply_to_base_and_preserve_real_index(self):
        result = self.snapshots()
        self.assertNotIn(b"tests/", result["core-upstream.patch"])
        self.assertIn(b"ports/rp2/new_helper.c", result["core-upstream.patch"])
        self.assertIn(b"tests/ports/rp2/deepsleep/device.py", result["combined-upstream.patch"])
        for name, content in result.items():
            self.assertNotIn(b"experiments/", content)
            index = self.root / (name + ".index")
            self.git("read-tree", self.base, index=index)
            self.git("apply", "--cached", "--check", "-", input=content, index=index)
            self.git("apply", "--cached", "-", input=content, index=index)
            self.assertEqual(
                self.git("ls-files", "--stage", "-z", "--", *generator.SCOPES[name], index=index),
                self.git("ls-files", "--stage", "-z", "--", *generator.SCOPES[name]),
            )
        self.assertEqual((self.root / ".git/index").read_bytes(), self.index_before)

    def test_check_is_read_only_and_write_changes_only_current_snapshots(self):
        historical = self.put(str(generator.BUNDLE / "firmware.patch"), "Historical; preserve.\n")
        with self.assertRaisesRegex(RuntimeError, "stale/missing"):
            self.update()
        self.assertFalse((self.output / "core-upstream.patch").exists())
        self.assertEqual(len(self.update(write=True)), 2)
        self.assertEqual(self.update(), [])
        self.assertEqual(self.update(write=True), [])
        target = self.output / "combined-upstream.patch"
        target.write_bytes(target.read_bytes() + b"stale\n")
        digest = hashlib.sha256(target.read_bytes()).digest()
        with self.assertRaisesRegex(RuntimeError, "combined-upstream.patch"):
            self.update()
        self.assertEqual(hashlib.sha256(target.read_bytes()).digest(), digest)
        self.assertEqual(self.update(write=True), [target.name])
        self.assertEqual(historical.read_text(), "Historical; preserve.\n")

    def test_unstaged_scoped_source_refused_without_writing(self):
        self.put("docs/library/machine.rst", "Uncommitted change.\n")
        with self.assertRaisesRegex(RuntimeError, "tracked sources are modified"):
            self.update(write=True)
        self.assertEqual(list(self.output.iterdir()), [])

    def test_staged_new_helper_refused(self):
        self.put("ports/rp2/newer_helper.c", "int newer;\n")
        self.git("add", "ports/rp2/newer_helper.c")
        with self.assertRaisesRegex(RuntimeError, "staged changes"):
            self.snapshots()

    def test_untracked_source_in_either_scope_refused(self):
        self.put("xdg/git/ignore", "*\n")
        for name in ("ports/rp2/untracked.c", "tests/ports/rp2/deepsleep/new_test.py"):
            with self.subTest(name=name), patch.dict(
                os.environ, {"XDG_CONFIG_HOME": str(self.root / "xdg")}
            ):
                path = self.put(name, "Untracked source.\n")
                with self.assertRaisesRegex(RuntimeError, "untracked scoped sources"):
                    self.snapshots()
                path.unlink()

    def test_ignored_builds_bytecode_and_unrelated_changes_allowed(self):
        expected = self.snapshots()
        self.put("ports/rp2/build-example/generated.c", "Build output.\n")
        self.put("tests/ports/rp2/deepsleep/__pycache__/device.cpython-312.pyc", "Bytecode.\n")
        self.put("experiments/private-note.txt", "Uncommitted unrelated changes.\n")
        self.put("lib/tinyusb/src/device/usbd.c", "Unrelated dependency changes.\n")
        self.assertEqual(self.snapshots(), expected)

    def test_missing_or_nonancestor_base_refused(self):
        tree = self.git("rev-parse", "HEAD^{tree}").decode().strip()
        unrelated = self.git("commit-tree", tree, "-m", "unrelated root").decode().strip()
        for base in ("0" * 40, unrelated):
            with self.subTest(base=base), self.assertRaisesRegex(RuntimeError, "not an ancestor"):
                generator.snapshots(self.root, base)

    def test_user_config_attributes_and_git_environment_do_not_change_output(self):
        expected = self.snapshots()
        for key, value in {
            "diff.external": "false",
            "diff.hostile.command": "false",
            "diff.hostile.textconv": "false",
            "diff.hostile.xfuncname": "hostile",
            "diff.algorithm": "histogram",
            "diff.context": "1000",
            "diff.noprefix": "true",
            "color.ui": "always",
        }.items():
            self.git("config", key, value)
        self.put(".git/info/attributes", "* -diff\n")
        self.put("xdg/git/attributes", "* -diff\n")
        config = self.put("global-config", "[diff]\n\texternal = false\n\tcontext = 999\n")
        with patch.dict(
            os.environ,
            {
                "GIT_CONFIG_GLOBAL": str(config),
                "GIT_EXTERNAL_DIFF": "false",
                "GIT_DIR": str(self.root / "does-not-exist"),
                "GIT_DIFF_OPTS": "--unified=999",
                "XDG_CONFIG_HOME": str(self.root / "xdg"),
            },
        ):
            self.assertEqual(self.snapshots(), expected)
        self.assertEqual((self.root / ".git/index").read_bytes(), self.index_before)

    def test_assume_unchanged_cannot_hide_modified_source(self):
        self.git("update-index", "--assume-unchanged", "ports/rp2/modmachine.c")
        self.put("ports/rp2/modmachine.c", "Hidden change.\n")
        with self.assertRaisesRegex(RuntimeError, "tracked sources are modified"):
            self.snapshots()

    def test_symlink_snapshot_refused(self):
        outside = self.put("outside.txt", "Preserve.\n")
        (self.output / "core-upstream.patch").symlink_to(outside)
        with self.assertRaisesRegex(RuntimeError, "symlink"):
            self.update(write=True)
        self.assertEqual(outside.read_text(), "Preserve.\n")


if __name__ == "__main__":
    unittest.main(verbosity=2)
