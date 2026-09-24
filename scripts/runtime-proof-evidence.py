"""Bind checkout proof to immutable inputs; missing evidence never becomes PASS."""

import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

SHA = re.compile(r"[0-9a-f]{40}\Z")
UI_SCENARIOS = {
    "keyboard-one-selection-focus", "two-selection-opens", "three-selection-limit",
    "removal-preserves-node-focus", "canonical-invalid-duplicate-url",
    "empty-ids-does-not-reuse-storage", "delayed-compare-render-waits-for-terminal-state",
    "delayed-route-preserves-local-firewall", "cross-tab-storage-sync", "mobile-390x844",
    "profile-three-questions-anchors-keyboard", "profile-occupation-is-not-current-activity",
    "profile-current-mandate-is-current-activity", "profile-web-share",
    "profile-clipboard-fallback", "profile-mobile-390x844",
}
INVARIANTS = {"teardown-rejects-preclosed-page", "pending-route-drain-waits",
              "pending-route-rejection-propagates"}
REQUIRED_FILES = {
    "screenshots/profile-desktop-1366x900.png", "screenshots/profile-mobile-390x844.png",
    "http.log", "runtime.log",
}


def git(root, *args):
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def reconcile(manifest, env, target, harness, out):
    problems = []
    if env.get("QV_WORKFLOW_SHA") != env.get("QV_HARNESS_REF"):
        problems.append("workflow:harness_sha_mismatch")
    for key in ("QV_HARNESS_REF", "QV_TARGET_REF", "QV_WORKFLOW_SHA"):
        if not SHA.fullmatch(env.get(key, "")):
            problems.append("invalid:" + key)
    for key in ("QV_RUN_ID", "QV_RUN_ATTEMPT", "QV_ACTOR", "QV_TRIGGERING_ACTOR", "QV_REPOSITORY"):
        if not env.get(key):
            problems.append("missing:" + key)
    if env.get("QV_MATRIX_OUTCOME") != "success":
        problems.append("matrix:not_success")
    for root, key, name in ((target, "QV_TARGET_REF", "target"),
                            (harness, "QV_HARNESS_REF", "harness")):
        if git(root, "rev-parse", "HEAD") != env.get(key):
            problems.append(name + ":sha_mismatch")
        # Dependency installation may create untracked files in the harness only.
        mode = "all" if name == "target" else "no"
        if git(root, "status", "--porcelain", "--untracked-files=" + mode):
            problems.append(name + ":dirty_checkout")
    expected = {
        "harness_sha": env.get("QV_HARNESS_REF"),
        "id": env.get("QV_RUN_ID"), "attempt": env.get("QV_RUN_ATTEMPT"),
    }
    if any(manifest.get("run", {}).get(k) != v for k, v in expected.items()):
        problems.append("manifest:run_mismatch")
    target_metadata = manifest.get("target", {})
    if (target_metadata.get("ref") != env.get("QV_TARGET_REF") or
            target_metadata.get("sha") != env.get("QV_TARGET_REF") or
            target_metadata.get("mode") != "checkout" or
            target_metadata.get("base_url") != "http://127.0.0.1:8000/"):
        problems.append("manifest:target_mismatch")
    suites = manifest.get("suites", {})
    material_failure = False
    for suite_name, required in (("ui", UI_SCENARIOS), ("harness_invariants", INVARIANTS)):
        suite = suites.get(suite_name, {})
        scenarios = suite.get("scenarios", [])
        names = [s.get("name") for s in scenarios]
        if set(names) != required or len(names) != len(required):
            problems.append(suite_name + ":scenario_inventory_mismatch")
        for scenario in scenarios:
            status = scenario.get("status")
            if status == "FAIL":
                material_failure = True
            elif status != "PASS":
                problems.append(suite_name + ":scenario_not_conclusive")
            if suite_name == "ui":
                errors = scenario.get("runtime_errors", {}).get("material")
                if not isinstance(errors, list):
                    problems.append("runtime:missing_error_capture")
                elif errors:
                    material_failure = True
        if suite.get("status") != "PASS":
            problems.append(suite_name + ":not_pass")
    for name in sorted(REQUIRED_FILES):
        file = out / name
        if not file.is_file() or not file.stat().st_size:
            problems.append("evidence:missing:" + name)
    if manifest.get("overall") != "PASS" or manifest.get("merge_gate") != "PASS":
        problems.append("manifest:not_pass")
    # Preserve a functional FAIL even when screenshots/attribution are also incomplete.
    result = "FAIL" if material_failure or manifest.get("overall") == "FAIL" else "BLOCKED" if problems else "PASS"
    manifest["bridge"] = {
        "status": result, "problems": problems,
        "repository": env.get("QV_REPOSITORY"),
        "workflow_sha": env.get("QV_WORKFLOW_SHA"),
        "harness_ref": env.get("QV_HARNESS_REF"), "target_ref": env.get("QV_TARGET_REF"),
        "run_id": env.get("QV_RUN_ID"), "run_attempt": env.get("QV_RUN_ATTEMPT"),
        "actor": env.get("QV_ACTOR"), "triggering_actor": env.get("QV_TRIGGERING_ACTOR"),
        "artifact_name": "runtime-proof-{}-{}".format(env.get("QV_RUN_ID"), env.get("QV_RUN_ATTEMPT")),
        "limitations": ["Controlled Web Share/clipboard stubs do not prove native device sharing.",
                        "Independent audit and Release Arbiter reconciliation remain required."],
    }
    manifest["overall"] = result
    manifest["merge_gate"] = "PASS" if result == "PASS" else "FAIL"
    return manifest


def main():
    target, out = map(Path, sys.argv[1:])
    out.mkdir(parents=True, exist_ok=True)
    manifest_path = out / "proof-manifest.json"
    manifest = {}
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if not isinstance(manifest, dict):
            raise ValueError("manifest must be an object")
        manifest = reconcile(manifest, os.environ, target, Path.cwd(), out)
    except Exception as exc:
        # Includes absent/malformed manifests, interrupted browser startup and git errors.
        manifest = {"overall": "BLOCKED", "merge_gate": "FAIL", "bridge": {
            "status": "BLOCKED", "problems": [str(exc)],
            "harness_ref": os.environ.get("QV_HARNESS_REF"),
            "target_ref": os.environ.get("QV_TARGET_REF"),
            "workflow_sha": os.environ.get("QV_WORKFLOW_SHA"),
            "run_id": os.environ.get("QV_RUN_ID"),
            "run_attempt": os.environ.get("QV_RUN_ATTEMPT"),
        }}
    manifest["artifacts"] = [
        {"path": str(file.relative_to(out)), "bytes": file.stat().st_size,
         "sha256": hashlib.sha256(file.read_bytes()).hexdigest()}
        for file in sorted(out.rglob("*")) if file.is_file() and file != manifest_path
    ]
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest["bridge"], indent=2))
    return 0 if manifest["bridge"]["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
