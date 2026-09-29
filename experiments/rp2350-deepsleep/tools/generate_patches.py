#!/usr/bin/env python3
# The MIT License (MIT). Copyright (c) 2026 MicroPython contributors.
"""Check (default) or explicitly regenerate the two current upstream patch snapshots."""

import argparse
import os
import subprocess
import tempfile
from contextlib import contextmanager
from pathlib import Path

BASE = "09f5bb447504a058376c62fe991b3613531837e6"
BUNDLE = Path("experiments/rp2350-deepsleep")
CORE = (
    "docs/library/machine.rst",
    "docs/rp2",
    "ports/rp2",
)
COMBINED = CORE + ("tests/ports/rp2/deepsleep",)
SCOPES = {"core-upstream.patch": CORE, "combined-upstream.patch": COMBINED}


def git_environment():
    # No inherited Git redirection, diff command, config injection or replace refs.
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    env.update(
        {
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_ATTR_NOSYSTEM": "1",
            "LC_ALL": "C",
        }
    )
    return env


def git(repo, *args, worktree=None):
    command = [
        "git",
        "--no-optional-locks",
        "--no-replace-objects",
        # Git also reads default XDG attributes/ignore files without config.
        "-c",
        "core.attributesFile=" + os.devnull,
        "-c",
        "core.excludesFile=" + os.devnull,
        "-C",
        str(repo),
    ]
    if worktree is not None:
        command += ["--work-tree=" + str(worktree)]
    result = subprocess.run(
        command + list(args), env=git_environment(), capture_output=True, check=False
    )
    if result.returncode:
        raise RuntimeError(
            "git {} failed: {}".format(args[0], result.stderr.decode(errors="replace").strip())
        )
    return result.stdout


@contextmanager
def committed_view(repo):
    """Borrow objects, not the source index/config/attributes/hooks/working files."""
    actual = Path(git(repo, "rev-parse", "--show-toplevel").decode().strip()).resolve()
    if actual != repo.resolve():
        raise RuntimeError("run the generator stored in the root checkout's tools directory")
    head = git(repo, "rev-parse", "--verify", "HEAD^{commit}").decode().strip()
    objects = (
        git(repo, "rev-parse", "--path-format=absolute", "--git-path", "objects").decode().strip()
    )
    if "\n" in objects or "\r" in objects:
        raise RuntimeError("object directory contains an unsupported newline")
    with tempfile.TemporaryDirectory(prefix="rp2350-patches-") as directory:
        view = Path(directory)
        git(view, "init", "--bare", "--template=", "-q")
        (view / "objects/info/alternates").write_text(objects + "\n")
        git(view, "update-ref", "HEAD", head)
        # This temporary index supplies committed attributes to tree-to-tree diff
        # and fresh stat checks; source skip-worktree/assume-unchanged bits cannot
        # conceal modifications. The source index itself is never refreshed.
        git(view, "read-tree", head)
        yield view, head


def snapshots(repo, base=BASE):
    """Internal base argument exists for isolated fixtures; the CLI pins BASE."""
    with committed_view(repo) as (view, head):
        try:
            git(view, "merge-base", "--is-ancestor", base, head)
        except RuntimeError as exc:
            raise RuntimeError("pinned base is missing or is not an ancestor of HEAD") from exc
        source_index = git(repo, "ls-files", "--stage", "-z", "--", *COMBINED)
        committed_index = git(view, "ls-files", "--stage", "-z", "--", *COMBINED)
        if source_index != committed_index:
            raise RuntimeError("scoped sources have staged changes; commit or preserve them first")
        dirty = git(
            view,
            "diff",
            "--no-ext-diff",
            "--no-textconv",
            "--name-only",
            "-z",
            "HEAD",
            "--",
            *COMBINED,
            worktree=repo,
        )
        if dirty:
            raise RuntimeError("scoped tracked sources are modified; use committed clean sources")
        untracked = git(
            view,
            "ls-files",
            "--others",
            "--exclude-standard",
            "-z",
            "--",
            *COMBINED,
            worktree=repo,
        )
        if untracked:
            raise RuntimeError(
                "nonignored untracked scoped sources exist; add and commit them first"
            )
        result = {}
        for name, scope in SCOPES.items():
            result[name] = git(
                view,
                "diff",
                "--no-ext-diff",
                "--no-textconv",
                "--no-color",
                "--no-renames",
                "--full-index",
                "--binary",
                "--unified=3",
                "--diff-algorithm=myers",
                "--no-indent-heuristic",
                "--src-prefix=a/",
                "--dst-prefix=b/",
                base,
                head,
                "--",
                *scope,
            )
        if git(repo, "rev-parse", "HEAD").decode().strip() != head:
            raise RuntimeError("HEAD changed during generation; retry with a stable checkout")
        return result


def update(repo, write=False, base=BASE):
    generated = snapshots(repo, base)
    stale = []
    for name, content in generated.items():
        target = repo / BUNDLE / name
        if target.is_symlink():
            raise RuntimeError("snapshot must not be a symlink: " + name)
        if not target.is_file() or target.read_bytes() != content:
            stale.append(name)
    if stale and not write:
        raise RuntimeError(
            "stale/missing snapshots: {}; run with --write after committing sources".format(
                ", ".join(stale)
            )
        )
    for name in stale:
        target = repo / BUNDLE / name
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as output:
                temporary = Path(output.name)
                output.write(generated[name])
            os.replace(temporary, target)
        finally:
            if temporary is not None and temporary.exists():
                temporary.unlink()
    return stale


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="check exact snapshot bytes (default)")
    mode.add_argument(
        "--write", action="store_true", help="replace stale snapshots from committed HEAD"
    )
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[3]
    try:
        changed = update(repo, write=args.write)
    except (RuntimeError, OSError) as exc:
        parser.exit(1, f"ERROR: {exc}\n")
    print(
        "PASS: "
        + ("updated " + ", ".join(changed) if changed else "both snapshots match committed HEAD")
    )


if __name__ == "__main__":
    main()
