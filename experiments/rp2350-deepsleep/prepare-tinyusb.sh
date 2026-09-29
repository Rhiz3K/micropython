#!/usr/bin/env bash
# Apply the reviewed TinyUSB fix without changing its pinned gitlink.
set -euo pipefail

if [[ $# -ne 0 ]]; then
    printf 'Usage: %s\n' "$0" >&2
    printf 'Initialize rp2 submodules first, as described in HANDOVER.cs.md.\n' >&2
    printf 'Requires git and Python 3. Does not build, flash or update dependencies.\n' >&2
    if [[ $# -eq 1 && ( "$1" == '--help' || "$1" == '-h' ) ]]; then
        exit 0
    fi
    exit 2
fi

exec python3 - "${BASH_SOURCE[0]}" <<'PY'
import hashlib
import os
from pathlib import Path
import stat
import subprocess
import sys

PINNED_HEAD = "b549ac1d84cbbe550c9590951e2290098b3fb16c"
PATCH_SHA256 = "ffbadfaa2a51af420e64e1bdb4fad55f1621646eb3bcd98e3d93eaa921076e4e"
# Complete file hashes after applying that patch to PINNED_HEAD, including
# unchanged context. Unlike patch-id, this rejects additional whitespace edits.
EXPECTED_FILES = {
    "src/device/usbd.c": "79abb088c6dbecb1a4c8a3872baf518ce84cc24a3e4d22c63ce024b463746a19",
    "test/unit-test/test/device/usbd/test_usbd.c":
        "2fdf3d24b88e3611e4c1b99debdfb005bf800105081ffb72980ac28b117c9653",
}


def fail(message):
    raise SystemExit("ERROR: " + message)


def git(directory, *args):
    result = subprocess.run(
        ["git", "--no-optional-locks", "-C", str(directory), *args],
        capture_output=True,
        check=False,
    )
    if result.returncode:
        fail("git " + args[0] + " failed; no reset or cleanup was attempted.")
    return result.stdout


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


for name in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR"):
    if name in os.environ:
        fail("Unset " + name + " before preparing this checkout.")

script_dir = Path(sys.argv[1]).resolve().parent
repo = Path(git(script_dir, "rev-parse", "--show-toplevel").decode().strip()).resolve()
if script_dir != repo / "experiments/rp2350-deepsleep":
    fail("Run the script stored in this checkout's experiments/rp2350-deepsleep directory.")
patch = script_dir / "tinyusb-ep0-queue.patch"
if not patch.is_file() or digest(patch) != PATCH_SHA256:
    fail("Stored TinyUSB patch is missing or has an unexpected SHA-256.")

tinyusb = repo / "lib/tinyusb"
if not tinyusb.is_dir() or not (tinyusb / ".git").exists():
    fail("Initialize rp2 submodules first; see HANDOVER.cs.md. No submodules were updated.")
actual_root = Path(git(tinyusb, "rev-parse", "--show-toplevel").decode().strip()).resolve()
if actual_root != tinyusb.resolve() or tinyusb.is_symlink():
    fail("lib/tinyusb must be its own Git checkout, not a symlink or parent repository.")
if git(tinyusb, "rev-parse", "HEAD").decode().strip() != PINNED_HEAD:
    fail("TinyUSB HEAD does not match the pinned revision. No checkout was changed.")
if git(tinyusb, "diff", "--cached", "--name-only", "-z"):
    fail("TinyUSB has staged changes; preserve and review them before proceeding.")
# Include ignored files: never assume an untracked dependency file is disposable.
if git(tinyusb, "ls-files", "--others", "-z"):
    fail("TinyUSB contains untracked files (including ignored files); nothing was removed.")


def changed_files():
    output = git(tinyusb, "diff", "--no-ext-diff", "--name-only", "-z", "HEAD", "--")
    return set(output.decode().rstrip("\0").split("\0")) if output else set()


def exact_patch_present():
    if changed_files() != set(EXPECTED_FILES):
        return False
    for name, expected in EXPECTED_FILES.items():
        path = tinyusb / name
        executable = stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
        if not path.is_file() or path.is_symlink() or path.stat().st_mode & executable:
            return False
        if digest(path) != expected:
            return False
    return True


if changed_files():
    if not exact_patch_present():
        fail("TinyUSB changes differ from the exact reviewed patch; nothing was overwritten.")
    git(tinyusb, "apply", "--reverse", "--check", str(patch))
    print("PASS: exact TinyUSB patch already applied; no files changed.")
else:
    git(tinyusb, "apply", "--check", str(patch))
    git(tinyusb, "apply", str(patch))
    if not exact_patch_present():
        fail("Post-apply verification failed; changes were preserved for inspection.")
    git(tinyusb, "apply", "--reverse", "--check", str(patch))
    print("PASS: applied and verified the exact TinyUSB patch.")
print("TinyUSB HEAD remains " + PINNED_HEAD + "; no gitlink, build or device was changed.")
PY
