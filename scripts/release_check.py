#!/usr/bin/env python3
from __future__ import annotations

import argparse
import difflib
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

REQUIRED_PATHS = [
    Path("README.md"),
    Path(".gitignore"),
    Path(".ignore"),
    Path("docs/project-orchestrator-update-workflow-sop-v0.1.md"),
    Path("docs/project-orchestrator-public-ready-gap-review-v0.1.md"),
    Path("docs/project-orchestrator-reviewer-quickstart-v0.1.md"),
    Path("project-orchestrator/projects/pa-sample/project.json"),
    Path("project-orchestrator/registry/projects.sample.json"),
]

FORBIDDEN_PATTERNS = [
    "pa-lovemoney",
    "codex_lovemoney",
    "/root/projects/lovemoney",
    "oc_7fae57f0989ee61b50639b20074eff9d",
    "ou_49a0925ff505a0043d4449f53885e077",
    "resumeId=019cf09b",
    "LOVEMONEY-",
]

SKIP_SCAN_RELATIVE_PATHS = {
    "scripts/release_check.py",
}

SKIP_SCAN_DIRS = {
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
}

TESTS = [
    "tests.test_project_orchestrator_agent_shell",
    "tests.test_project_orchestrator_instance_runner",
    "tests.test_project_orchestrator_review",
    "tests.test_project_orchestrator_watcher",
]


class CheckFailure(Exception):
    pass


def run(cmd: list[str], *, cwd: Path = REPO_ROOT, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    return subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, env=merged_env)


def section(title: str) -> None:
    print(f"\n== {title} ==")


def ok(msg: str) -> None:
    print(f"OK   {msg}")


def fail(msg: str) -> None:
    print(f"FAIL {msg}")


def info(msg: str) -> None:
    print(f"INFO {msg}")


def check_required_paths() -> None:
    section("required paths")
    missing: list[str] = []
    for rel in REQUIRED_PATHS:
        path = REPO_ROOT / rel
        if path.exists():
            ok(str(rel))
        else:
            fail(f"missing {rel}")
            missing.append(str(rel))
    if missing:
        raise CheckFailure("required paths missing")


def normalized_ignore_lines(path: Path) -> list[str]:
    lines = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        lines.append(line)
    return lines


def check_ignore_parity() -> None:
    section("ignore parity")
    gitignore = normalized_ignore_lines(REPO_ROOT / ".gitignore")
    ignore = normalized_ignore_lines(REPO_ROOT / ".ignore")
    if gitignore == ignore:
        ok(".gitignore and .ignore are aligned")
        return
    diff = "\n".join(
        difflib.unified_diff(gitignore, ignore, fromfile=".gitignore", tofile=".ignore", lineterm="")
    )
    fail(".gitignore and .ignore differ")
    print(diff)
    raise CheckFailure("ignore files differ")


def check_sample_boundary() -> None:
    section("sample boundary")
    sample_dir = REPO_ROOT / "project-orchestrator/projects/pa-sample"
    local_private_dir = REPO_ROOT / "project-orchestrator/projects/local-private"
    if sample_dir.exists():
        ok("pa-sample exists")
    else:
        fail("pa-sample missing")
        raise CheckFailure("sample directory missing")

    if local_private_dir.exists():
        fail("local-private directory should not be packaged")
        raise CheckFailure("local-private directory present")
    ok("local-private directory not packaged")

    local_registry = REPO_ROOT / "project-orchestrator/registry/projects.json"
    if local_registry.exists():
        fail("local registry should not be packaged")
        raise CheckFailure("local registry present")
    ok("local registry not packaged")


def iter_text_files() -> list[Path]:
    files: list[Path] = []
    for path in REPO_ROOT.rglob("*"):
        rel = path.relative_to(REPO_ROOT)
        if any(part in SKIP_SCAN_DIRS for part in rel.parts):
            continue
        if not path.is_file():
            continue
        if str(rel) in SKIP_SCAN_RELATIVE_PATHS:
            continue
        files.append(path)
    return files


def scan_pattern_hits(pattern: str) -> list[str]:
    matches: list[str] = []
    for path in iter_text_files():
        rel = path.relative_to(REPO_ROOT)
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue
        for idx, line in enumerate(lines, start=1):
            if pattern in line:
                matches.append(f"./{rel}:{idx}:{line.strip()}")
    return matches


def check_forbidden_patterns() -> None:
    section("forbidden patterns")
    hits: list[str] = []
    for pattern in FORBIDDEN_PATTERNS:
        matches = scan_pattern_hits(pattern)
        if matches:
            fail(f"found forbidden pattern: {pattern}")
            print("\n".join(matches[:20]))
            if len(matches) > 20:
                print(f"... and {len(matches) - 20} more")
            hits.append(pattern)
        else:
            ok(f"not found: {pattern}")
    if hits:
        raise CheckFailure("forbidden patterns found")


def check_component_manifest() -> None:
    section("component manifest")
    manifest_path = REPO_ROOT / "project-orchestrator/component-manifest.json"
    try:
        import json
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception as exc:
        fail(f"component manifest unreadable: {exc}")
        raise CheckFailure("component manifest unreadable")

    missing: list[str] = []
    for rel in [manifest.get("baseline"), manifest.get("statusDoc")]:
        if not rel:
            continue
        path = REPO_ROOT / rel
        if path.exists():
            ok(f"manifest path exists: {rel}")
        else:
            fail(f"manifest path missing: {rel}")
            missing.append(rel)

    for comp in manifest.get("components", []):
        rel = comp.get("path")
        name = comp.get("name", rel)
        if not rel:
            fail(f"component missing path: {name}")
            missing.append(f"<missing-path:{name}>")
            continue
        path = REPO_ROOT / rel
        if path.exists():
            ok(f"component exists: {name} -> {rel}")
        else:
            fail(f"component missing: {name} -> {rel}")
            missing.append(rel)

    if missing:
        raise CheckFailure("component manifest drift detected")


def check_phase1() -> None:
    section("phase1 check")
    result = run([sys.executable, "scripts/project_orchestrator_phase1_check.py"])
    if result.returncode != 0:
        fail("phase1 check failed")
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr)
        raise CheckFailure("phase1 check failed")
    ok(result.stdout.strip() or "phase1 check passed")


def check_tests() -> None:
    section("tests")
    cmd = [sys.executable, "-m", "unittest", *TESTS]
    result = run(cmd, cwd=REPO_ROOT, env={"PYTHONPATH": str(REPO_ROOT / "scripts")})
    if result.returncode != 0:
        fail("unit tests failed")
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr)
        raise CheckFailure("tests failed")
    summary = (result.stderr or result.stdout).strip()
    ok(summary.splitlines()[-1] if summary else "tests passed")


def check_git_status() -> None:
    section("git status")
    result = run(["git", "status", "--short"])
    if result.returncode != 0:
        fail("git status failed")
        if result.stderr:
            print(result.stderr)
        raise CheckFailure("git status failed")
    if result.stdout.strip():
        info("working tree has local changes:")
        print(result.stdout.strip())
    else:
        ok("working tree clean")


def main() -> int:
    parser = argparse.ArgumentParser(description="Pre-push release check for the staged project-orchestrator repo")
    parser.add_argument("--skip-tests", action="store_true", help="Skip unit tests")
    parser.add_argument("--skip-phase1", action="store_true", help="Skip phase1 structural check")
    args = parser.parse_args()

    try:
        check_required_paths()
        check_ignore_parity()
        check_sample_boundary()
        check_component_manifest()
        check_forbidden_patterns()
        if not args.skip_phase1:
            check_phase1()
        if not args.skip_tests:
            check_tests()
        check_git_status()
    except CheckFailure:
        print("\nRELEASE_CHECK_FAILED")
        return 1

    print("\nRELEASE_CHECK_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
