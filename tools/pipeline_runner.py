#!/usr/bin/env python3
"""pipeline_runner - standard runner for registered cleaning pipelines.

This is intentionally conservative. It only runs enabled cleaning pipelines and
delegates business logic to the suite scripts declared in pipeline.yaml.
"""
import argparse
import fnmatch
import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover - exercised in clean environments
    yaml = None


def load_json(path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def load_yaml(path):
    if yaml is None:
        raise SystemExit("PyYAML is required for pipeline_runner: pip install pyyaml")
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def run_cmd(cmd, cwd=None, check=True):
    proc = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True)
    if proc.stdout:
        print(proc.stdout, end="")
    if proc.stderr:
        print(proc.stderr, end="", file=sys.stderr)
    if check and proc.returncode != 0:
        raise SystemExit(proc.returncode)
    return proc


def script_path(skill_root, suite_dir, rel):
    path = (suite_dir / rel).resolve()
    if not str(path).startswith(str(suite_dir.resolve()) + os.sep):
        raise SystemExit(f"script path escapes suite directory: {rel}")
    if not path.exists():
        raise SystemExit(f"script not found: {path}")
    return path


def load_manifest(skill_root):
    path = skill_root / "pipelines" / "manifest.json"
    data = load_json(path, {"pipelines": []})
    return path, data.get("pipelines", [])


def suite_from_entry(skill_root, entry):
    yaml_rel = entry.get("yaml")
    if yaml_rel:
        yaml_path = skill_root / "pipelines" / yaml_rel
        return yaml_path.parent, yaml_path
    suite_dir = skill_root / "pipelines" / entry["id"]
    return suite_dir, suite_dir / "pipeline.yaml"


def filename_matches(path, hint):
    if not hint:
        return True
    return fnmatch.fnmatch(path.name, hint) or fnmatch.fnmatch(str(path), hint)


def select_pipeline(skill_root, input_path, pipeline_id=None):
    _, entries = load_manifest(skill_root)
    enabled = [entry for entry in entries if entry.get("status") == "enabled"]
    if pipeline_id:
        hits = [entry for entry in enabled if entry.get("id") == pipeline_id]
    else:
        hits = [entry for entry in enabled if filename_matches(input_path, entry.get("filename_hint") or entry.get("pattern_hint"))]
    if not hits:
        raise SystemExit("no enabled pipeline matched; use cocreation or pass --pipeline-id")
    if len(hits) > 1 and not pipeline_id:
        ids = ", ".join(entry.get("id", "?") for entry in hits)
        raise SystemExit(f"multiple pipelines matched ({ids}); pass --pipeline-id")
    entry = hits[0]
    suite_dir, yaml_path = suite_from_entry(skill_root, entry)
    return entry, suite_dir, yaml_path, load_yaml(yaml_path)


def check_requires(requires):
    problems = []
    for req in requires or []:
        if req == "libreoffice":
            if not (shutil.which("soffice") or shutil.which("libreoffice")):
                problems.append("libreoffice/soffice not found")
        elif importlib.util.find_spec(req) is None:
            problems.append(f"python package not importable: {req}")
    if problems:
        raise SystemExit("preflight failed: " + "; ".join(problems))


def substitute_args(items, input_path, run_dir, suite_dir, skill_root):
    values = {
        "input": str(input_path),
        "output": str(run_dir),
        "run_dir": str(run_dir),
        "suite_dir": str(suite_dir),
        "skill_root": str(skill_root),
    }
    out = []
    for item in items or []:
        text = str(item)
        for key, value in values.items():
            text = text.replace("{" + key + "}", value)
        out.append(text)
    return out


def output_manager(skill_root):
    path = skill_root / "tools" / "output_manager.py"
    if not path.exists():
        raise SystemExit(f"missing output_manager.py: {path}")
    return path


def sibling_tool(skill_root, name):
    candidate = skill_root / "tools" / name
    if candidate.exists():
        return candidate
    fallback = Path(__file__).resolve().parent / name
    if fallback.exists():
        return fallback
    raise SystemExit(f"missing tool: {name}")


def step(skill_root, run_dir, name, status):
    run_cmd([sys.executable, str(output_manager(skill_root)), "step", "--dir", str(run_dir), "--step", name, "--status", status])


def run_drift_check(skill_root, suite_dir, input_path, allow_partial):
    tool = sibling_tool(skill_root, "drift_check.py")
    proc = run_cmd([
        sys.executable,
        str(tool),
        "--suite-dir",
        str(suite_dir),
        "--input",
        str(input_path),
        "--json",
    ], check=False)
    if proc.returncode == 0:
        return
    if proc.returncode == 2 and allow_partial:
        return
    raise SystemExit(proc.returncode)


def create_run(skill_root, output_root, pipeline_id):
    proc = run_cmd([
        sys.executable,
        str(output_manager(skill_root)),
        "create",
        "--root",
        str(output_root),
        "--kind",
        "pipelines",
        "--id",
        pipeline_id,
    ])
    return Path(proc.stdout.strip().splitlines()[-1])


def finalize_run(skill_root, run_dir, csvs, usage, data_date=None):
    cmd = [sys.executable, str(output_manager(skill_root)), "finalize", "--dir", str(run_dir)]
    for csv_path in csvs:
        cmd += ["--csv", str(csv_path)]
    if data_date:
        cmd += ["--data-date", data_date]
    # Usage is updated after validation, not at generated/finalize stage.
    proc = run_cmd(cmd)
    return Path(proc.stdout.strip().splitlines()[-1])


def run_steps(kind, steps, skill_root, suite_dir, input_path, run_dir):
    for index, item in enumerate(steps or [], 1):
        rel = item.get("script")
        if not rel:
            continue
        args = substitute_args(item.get("args") or [], input_path, run_dir, suite_dir, skill_root)
        cmd = [sys.executable, str(script_path(skill_root, suite_dir, rel))] + args
        print(f"[{kind} {index}] {' '.join(cmd)}")
        run_cmd(cmd, cwd=str(suite_dir))


def declared_csv_outputs(run_dir, data):
    csvs = []
    for item in data.get("outputs") or []:
        name = item.get("file")
        if name and name.endswith(".csv"):
            csvs.append(run_dir / name)
    if not csvs:
        csvs = sorted(run_dir.glob("*.csv"))
    existing = [path for path in csvs if path.exists()]
    if not existing:
        raise SystemExit("no CSV outputs found for finalize; declare outputs or pass a data_date strategy")
    return existing


def validate_contract(skill_root, run_dir, data, usage):
    produced = ((data.get("validation_contract") or {}).get("produces")) or "validation_contract.json"
    contract = run_dir / produced
    if not contract.exists():
        raise SystemExit(f"validation contract was not produced: {contract}")
    cmd = [
        sys.executable,
        str(output_manager(skill_root)),
        "validate",
        "--dir",
        str(run_dir),
        "--contract",
        str(contract),
    ]
    if usage:
        cmd += ["--usage", str(usage)]
    run_cmd(cmd)
    info_path = run_dir / "info.json"
    return load_json(info_path, {}) if info_path.exists() else {}


def run_cleanup(skill_root, output_root, pipeline_id, run_dir, data):
    lifecycle = data.get("run_lifecycle")
    policy = lifecycle or {"cleanup_policy": "ask"}
    cleanup_policy = policy.get("cleanup_policy", "ask")
    if cleanup_policy == "disabled":
        return
    tool = sibling_tool(skill_root, "cleanup_manager.py")
    policy_path = run_dir / "cleanup_policy.json"
    policy_path.write_text(json.dumps(policy, ensure_ascii=False, indent=2), encoding="utf-8")
    plan_path = run_dir / "cleanup_plan.json"
    cmd = [
        sys.executable,
        str(tool),
        "plan",
        "--output-root",
        str(output_root),
        "--kind",
        "pipelines",
        "--suite-id",
        pipeline_id,
        "--latest-run",
        str(run_dir),
        "--policy-json",
        str(policy_path),
        "--out",
        str(plan_path),
    ]
    run_cmd(cmd)
    if cleanup_policy == "ask":
        print(f"cleanup -> pending user confirmation: {plan_path}")
        return
    if cleanup_policy == "auto_delete_csv":
        run_cmd([sys.executable, str(tool), "apply", "--plan", str(plan_path), "--confirm"])
        print(f"cleanup -> applied: {plan_path}")
        return
    raise SystemExit(f"unsupported cleanup_policy: {cleanup_policy}")


def command_list(args):
    skill_root = Path(args.skill_root).resolve()
    _, entries = load_manifest(skill_root)
    enabled = [entry for entry in entries if entry.get("status") == "enabled"]
    print(json.dumps(enabled, ensure_ascii=False, indent=2))


def command_match(args):
    skill_root = Path(args.skill_root).resolve()
    input_path = Path(args.input).resolve()
    entry, suite_dir, yaml_path, _ = select_pipeline(skill_root, input_path, args.pipeline_id)
    print(json.dumps({
        "id": entry.get("id"),
        "suite_dir": str(suite_dir),
        "yaml": str(yaml_path),
        "filename_hint": entry.get("filename_hint"),
    }, ensure_ascii=False, indent=2))


def command_run(args):
    skill_root = Path(args.skill_root).resolve()
    input_path = Path(args.input).resolve()
    output_root = Path(args.output_root).resolve()
    usage = Path(args.usage).resolve() if args.usage else skill_root / "pipelines" / "usage.json"

    entry, suite_dir, _, data = select_pipeline(skill_root, input_path, args.pipeline_id)
    pipeline_id = data.get("pipeline_id") or entry.get("id") or suite_dir.name
    usage_data = load_json(usage, {})
    if not args.yes_first_run and not usage_data.get(pipeline_id):
        raise SystemExit(f"first run for {pipeline_id}; rerun with --yes-first-run after user confirmation")

    check_requires(data.get("requires") or [])
    run_drift_check(skill_root, suite_dir, input_path, args.allow_partial_drift)

    run_dir = create_run(skill_root, output_root, pipeline_id)
    try:
        step(skill_root, run_dir, "preflight", "done")
        run_steps("transform", (data.get("transform") or {}).get("steps") or [], skill_root, suite_dir, input_path, run_dir)
        step(skill_root, run_dir, "transform", "done")
        csvs = declared_csv_outputs(run_dir, data)
        final_dir = finalize_run(skill_root, run_dir, csvs, usage, data_date=args.data_date)
        run_dir = final_dir
        run_steps("validation", (data.get("validation") or {}).get("layers") or [], skill_root, suite_dir, input_path, run_dir)
        info = validate_contract(skill_root, run_dir, data, usage)
        if info.get("status") in {"verified", "partial_verified"}:
            run_cleanup(skill_root, output_root, pipeline_id, run_dir, data)
        print(str(run_dir))
    except BaseException:
        if run_dir.exists():
            try:
                step(skill_root, run_dir, "runner", "failed")
            except BaseException:
                pass
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_list = sub.add_parser("list")
    p_list.add_argument("--skill-root", required=True)
    p_list.set_defaults(func=command_list)

    p_match = sub.add_parser("match")
    p_match.add_argument("--skill-root", required=True)
    p_match.add_argument("--input", required=True)
    p_match.add_argument("--pipeline-id")
    p_match.set_defaults(func=command_match)

    p_run = sub.add_parser("run")
    p_run.add_argument("--skill-root", required=True)
    p_run.add_argument("--input", required=True)
    p_run.add_argument("--output-root", required=True)
    p_run.add_argument("--pipeline-id")
    p_run.add_argument("--usage")
    p_run.add_argument("--data-date")
    p_run.add_argument("--yes-first-run", action="store_true")
    p_run.add_argument("--allow-partial-drift", action="store_true")
    p_run.set_defaults(func=command_run)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
