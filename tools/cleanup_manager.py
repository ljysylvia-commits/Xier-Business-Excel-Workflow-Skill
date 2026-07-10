#!/usr/bin/env python3
"""cleanup_manager - plan and apply conservative cleanup for superseded runs.

Default behavior is non-destructive: `plan` writes a cleanup_plan.json that
lists candidate files. `apply` requires --confirm and only removes files already
listed in the plan.
"""
import argparse
import json
import os
from datetime import datetime, timedelta
from pathlib import Path

INFO_JSON = "info.json"
DEFAULT_POLICY = {
    "cleanup_policy": "ask",
    "keep_latest": 1,
    "keep_days": 0,
    "delete_scope": "csv_only",
    "protect": {
        "pinned": True,
        "referenced_by_data_analysis": True,
        "validation_reports": True,
        "info_files": True,
    },
    "tombstone": "cleanup_tombstone.json",
}


def load_json(path, default=None):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def merge_policy(raw):
    policy = json.loads(json.dumps(DEFAULT_POLICY))
    raw = raw or {}
    for key, value in raw.items():
        if key == "protect" and isinstance(value, dict):
            policy["protect"].update(value)
        else:
            policy[key] = value
    return policy


def kind_base(output_root, kind):
    root = Path(output_root).resolve()
    if root.name == kind:
        return root
    return root / kind


def workspace_root_from_base(base, kind):
    if base.name == kind:
        return base.parent
    return base


def run_sort_key(run):
    info = run["info"]
    date_max = ((info.get("data_date_range") or {}).get("max") or "").replace("-", "")
    run_id = info.get("run_id") or ""
    run_time = info.get("run_time") or ""
    return (date_max, run_id, run_time, run["path"].name)


def discover_runs(output_root, kind, suite_id):
    base = kind_base(output_root, kind)
    if not base.exists():
        return []
    runs = []
    for child in sorted(base.iterdir()):
        if not child.is_dir():
            continue
        info = load_json(child / INFO_JSON)
        if not info:
            continue
        if info.get("suite_id") != suite_id:
            continue
        runs.append({"path": child.resolve(), "info": info})
    return runs


def discover_data_analysis_references(output_root, run):
    workspace_root = workspace_root_from_base(kind_base(output_root, "data_cleansing"), "data_cleansing")
    data_analysis_base = workspace_root / "data_analysis"
    if not data_analysis_base.exists():
        return []
    run_path = str(run["path"])
    run_name = run["path"].name
    run_id = run["info"].get("run_id")
    refs = []
    for info_path in data_analysis_base.glob("*/info.json"):
        text = info_path.read_text(encoding="utf-8", errors="replace")
        if run_path in text or run_name in text or (run_id and run_id in text):
            refs.append(str(info_path.parent))
    return refs


def is_recent(run, keep_days):
    if not keep_days:
        return False
    raw = run["info"].get("run_time")
    if not raw:
        return False
    try:
        run_time = datetime.fromisoformat(str(raw))
    except ValueError:
        return False
    return run_time >= datetime.now() - timedelta(days=int(keep_days))


def candidate_files(run, delete_scope):
    run_dir = run["path"]
    info = run["info"]
    files = []
    if delete_scope == "csv_only":
        names = set()
        for item in info.get("outputs") or []:
            name = item.get("file")
            if name and name.endswith(".csv"):
                names.add(name)
        for path in run_dir.glob("*.csv"):
            names.add(path.name)
        files = [run_dir / name for name in sorted(names)]
    elif delete_scope == "generated_outputs":
        names = [item.get("file") for item in info.get("outputs") or [] if item.get("file")]
        files = [run_dir / name for name in sorted(set(names))]
    elif delete_scope == "full_run":
        protected = {INFO_JSON, "data_cleansing_info.yaml", "data_analysis_info.yaml", "validation_contract.json"}
        files = [path for path in run_dir.iterdir() if path.is_file() and path.name not in protected]
    else:
        raise SystemExit(f"unsupported delete_scope: {delete_scope}")
    return [path for path in files if path.exists() and path.is_file()]


def build_plan(args):
    latest = Path(args.latest_run).resolve()
    policy = merge_policy(load_json(Path(args.policy_json), {}) if args.policy_json else {})
    if args.cleanup_policy:
        policy["cleanup_policy"] = args.cleanup_policy
    if args.delete_scope:
        policy["delete_scope"] = args.delete_scope
    if args.keep_latest is not None:
        policy["keep_latest"] = args.keep_latest
    if args.keep_days is not None:
        policy["keep_days"] = args.keep_days

    runs = discover_runs(args.output_root, args.kind, args.suite_id)
    old_runs = [run for run in runs if run["path"] != latest]
    old_runs.sort(key=run_sort_key, reverse=True)
    protected_keep = {str(run["path"]) for run in old_runs[:max(0, int(policy["keep_latest"]) - 1)]}

    candidates = []
    protected = []
    for run in old_runs:
        info = run["info"]
        reasons = []
        refs = discover_data_analysis_references(args.output_root, run)
        if info.get("pinned") and policy["protect"].get("pinned", True):
            reasons.append("pinned")
        if refs and policy["protect"].get("referenced_by_data_analysis", True):
            reasons.append("referenced_by_data_analysis")
        if str(run["path"]) in protected_keep:
            reasons.append("keep_latest")
        if is_recent(run, policy.get("keep_days")):
            reasons.append("keep_days")
        if info.get("status") not in {"verified", "partial_verified"}:
            reasons.append(f"status={info.get('status')}")
        if reasons:
            protected.append({
                "run_dir": str(run["path"]),
                "run_id": info.get("run_id"),
                "status": info.get("status"),
                "reasons": reasons,
                "data_analysis_references": refs,
            })
            continue
        files = candidate_files(run, policy["delete_scope"])
        candidates.append({
            "run_dir": str(run["path"]),
            "run_id": info.get("run_id"),
            "status": info.get("status"),
            "delete_files": [str(path) for path in files],
            "reason": f"newer run exists: {latest.name}",
        })

    plan = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "kind": args.kind,
        "suite_id": args.suite_id,
        "latest_run": str(latest),
        "policy": policy,
        "mode": "apply_allowed" if policy["cleanup_policy"] in {"auto_delete_csv", "ask"} else "disabled",
        "candidates": candidates,
        "protected_runs": protected,
    }
    out = Path(args.out) if args.out else latest / "cleanup_plan.json"
    write_json(out, plan)
    print(str(out.resolve()))


def apply_plan(args):
    if not args.confirm:
        raise SystemExit("apply requires --confirm")
    plan_path = Path(args.plan).resolve()
    plan = load_json(plan_path, {})
    deleted = []
    missing = []
    for item in plan.get("candidates") or []:
        run_dir = Path(item["run_dir"])
        removed = []
        already_missing = []
        for raw in item.get("delete_files") or []:
            path = Path(raw)
            if not path.exists():
                already_missing.append(str(path))
                continue
            if path.is_dir():
                raise SystemExit(f"refuse to delete directory from cleanup plan: {path}")
            path.unlink()
            removed.append(str(path))
        tombstone_name = (plan.get("policy") or {}).get("tombstone") or "cleanup_tombstone.json"
        tombstone = {
            "cleanup_time": datetime.now().isoformat(timespec="seconds"),
            "suite_id": plan.get("suite_id"),
            "superseded_by": Path(plan.get("latest_run", "")).name,
            "deleted_files": [Path(path).name for path in removed],
            "already_missing": [Path(path).name for path in already_missing],
            "kept_files": sorted(path.name for path in run_dir.iterdir() if path.is_file()),
            "reason": item.get("reason"),
            "reversible": False,
            "plan_file": str(plan_path),
        }
        write_json(run_dir / tombstone_name, tombstone)
        deleted.extend(removed)
        missing.extend(already_missing)
    result = {"deleted_files": deleted, "already_missing": missing, "candidate_count": len(plan.get("candidates") or [])}
    print(json.dumps(result, ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("plan")
    p.add_argument("--output-root", required=True)
    p.add_argument("--kind", choices=["data_cleansing"], default="data_cleansing")
    p.add_argument("--suite-id", required=True)
    p.add_argument("--latest-run", required=True)
    p.add_argument("--policy-json")
    p.add_argument("--cleanup-policy", choices=["disabled", "ask", "auto_delete_csv"])
    p.add_argument("--delete-scope", choices=["csv_only", "generated_outputs", "full_run"])
    p.add_argument("--keep-latest", type=int)
    p.add_argument("--keep-days", type=int)
    p.add_argument("--out")
    p.set_defaults(func=build_plan)

    a = sub.add_parser("apply")
    a.add_argument("--plan", required=True)
    a.add_argument("--confirm", action="store_true")
    a.set_defaults(func=apply_plan)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
