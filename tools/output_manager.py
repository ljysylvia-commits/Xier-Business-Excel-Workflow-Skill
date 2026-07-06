#!/usr/bin/env python3
"""output_manager —— 输出目录/运行元数据/统计 管理（确定性工具，无第三方依赖）

子命令:
  create   --root OUT_ROOT --kind pipelines|analysis --id SUITE_ID
           创建占位运行目录 {id}_PENDING_{时间戳}/，初始化 info；打印目录绝对路径
  step     --dir RUN_DIR --step NAME --status done|failed|running
           写回步骤状态（断点续跑依据）
  finalize --dir RUN_DIR --csv CSV [--csv CSV ...] [--data-date YYYYMMDD]
           [--validation-contract CONTRACT_JSON] [--usage USAGE_JSON] [--extra k=v ...]
           从 CSV 的 date 列取 max 得数据截止日期（或用 --data-date 指定），
           计算同日期序号，目录重命名为 {id}_{YYYYMMDD}_{seq}，
           写 info.json（机读）+ pipeline_info.yaml/analysis_info.yaml（人读）；默认状态为 generated，不代表验证通过
  validate --dir RUN_DIR --contract CONTRACT_JSON [--usage USAGE_JSON]
           读取 validation contract，写入 validation 摘要，并将状态置为
           verified / partial_verified / validation_failed
  status   --dir RUN_DIR    打印 steps 进度（供中断重入时报告）

info 数据以 info.json 为机读事实源，pipeline_info.yaml/analysis_info.yaml 为同内容的人读视图（finalize/step 时同步生成）。
"""
import argparse, csv, json, os, re, shutil, sys
from datetime import datetime

INFO_JSON = "info.json"


def _load(d):
    p = os.path.join(d, INFO_JSON)
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else {}


def _save(d, info):
    json.dump(info, open(os.path.join(d, INFO_JSON), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    _emit_yaml(d, info)


def _emit_yaml(d, info):
    """按固定 schema 输出人读 yaml 视图（仅本工具生成，不回读解析）。"""
    L = []
    for k in ("suite_id", "kind", "run_id", "run_time", "input_file", "profile_used", "status"):
        if k in info:
            L.append(f"{k}: {info[k]}")
    if "data_date_range" in info:
        r = info["data_date_range"]
        L.append(f"data_date_range: {{ min: {r.get('min')}, max: {r.get('max')} }}")
    if "params" in info:
        L.append("params:")
        for k, v in info["params"].items():
            L.append(f"  {k}: {v}")
    if "steps" in info:
        L.append("steps:")
        for s in info["steps"]:
            L.append(f"  - {{ step: {s['step']}, status: {s['status']} }}")
    if "outputs" in info:
        L.append("outputs:")
        for o in info["outputs"]:
            L.append(f"  - {{ file: {o['file']}, rows: {o.get('rows', '')} }}")
    if "validation" in info:
        v = info["validation"]
        L.append("validation:")
        run_status = v.get("run_status") or info.get("status")
        if run_status is not None:
            L.append(f"  run_status: {run_status}")
        if "contract_status" in v:
            L.append(f"  contract_status: {v['contract_status']}")
        for k in ("validator_exit_code", "coverage_scope", "total_checks", "failed_checks", "contract_file",
                  "delivery_gate", "final_conclusion_allowed", "boundary_delivery_allowed"):
            if k in v:
                L.append(f"  {k}: {v[k]}")
        reasons = v.get("reasons") or ([v.get("reason")] if v.get("reason") else [])
        if reasons:
            L.append("  reasons:")
            for item in reasons:
                L.append(f"    - {item}")
        if v.get("oracle_provenance_summary"):
            L.append("  oracle_provenance_summary:")
            for k, val in v["oracle_provenance_summary"].items():
                L.append(f"    {k}: {val}")
        if v.get("unverified_scope"):
            L.append("  unverified_scope:")
            for item in v["unverified_scope"]:
                L.append(f"    - {item}")
        if v.get("assumptions"):
            L.append("  assumptions:")
            for item in v["assumptions"]:
                L.append(f"    - {item}")
    name = "pipeline_info.yaml" if info.get("kind") == "pipelines" else "analysis_info.yaml"
    open(os.path.join(d, name), "w", encoding="utf-8").write("\n".join(L) + "\n")


def cmd_create(a):
    ts = datetime.now().strftime("%H%M%S")
    d = os.path.join(a.root, a.kind, f"{a.id}_PENDING_{ts}")
    os.makedirs(d, exist_ok=True)
    _save(d, {"suite_id": a.id, "kind": a.kind, "status": "created",
              "run_time": datetime.now().isoformat(timespec="seconds"), "steps": []})
    print(os.path.abspath(d))


def cmd_step(a):
    info = _load(a.dir)
    steps = info.setdefault("steps", [])
    for s in steps:
        if s["step"] == a.step:
            s["status"] = a.status
            break
    else:
        steps.append({"step": a.step, "status": a.status})
    _save(a.dir, info)
    print(f"step {a.step} -> {a.status}")


def cmd_status(a):
    info = _load(a.dir)
    for s in info.get("steps", []):
        print(f"{s['status']:8s} {s['step']}")
    done = sum(1 for s in info.get("steps", []) if s["status"] == "done")
    print(f"-- {done}/{len(info.get('steps', []))} done; status={info.get('status')}")


def _usage_update(path, sid, run_id, status):
    if not path:
        return False, "usage path not provided"
    if not run_id:
        return False, "run_id missing; usage not updated"
    u = json.load(open(path, encoding="utf-8")) if os.path.exists(path) else {}
    e = u.setdefault(sid, {"run_count": 0})
    validated = e.get("validated_runs")
    if validated is None:
        validated = []
        if e.get("last_run"):
            validated.append(e["last_run"])
    if run_id in validated:
        e["validated_runs"] = validated
        e["last_run"] = run_id
        e["last_status"] = status
        json.dump(u, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        return False, f"run already counted: {run_id}"
    validated.append(run_id)
    e["validated_runs"] = validated
    e["run_count"] = e.get("run_count", 0) + 1
    e["last_run"] = run_id
    e["last_status"] = status
    json.dump(u, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    return True, f"usage updated: {sid}/{run_id}"


def _as_int(v, default=0):
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


def _contract_status(c):
    """Return (run_status, reasons) from a validation contract."""
    validator_exit = _as_int(c.get("validator_exit_code"), default=1)
    failed = _as_int(c.get("failed_checks"), default=1)
    contract_status = str(c.get("status", "")).lower()
    if validator_exit != 0 or failed != 0 or contract_status not in {"pass", "passed", "ok", "success"}:
        return "validation_failed", ["validator_exit_code/status/failed_checks did not prove success"]

    coverage = str(c.get("coverage_scope", "")).strip()
    unverified = c.get("unverified_scope") or []
    assumptions = c.get("assumptions") or []
    prov = c.get("oracle_provenance_summary") or {}
    agent_inferred = _as_int(prov.get("agent_inferred"), default=0)
    source_recomputed = _as_int(prov.get("source_recomputed"), default=0)
    external_authoritative = _as_int(prov.get("external_authoritative"), default=0)
    user_provided_target = _as_int(prov.get("user_provided_target"), default=0)

    reasons = []
    if assumptions:
        reasons.append("validation depends on assumptions")
    if unverified:
        reasons.append("contract declares unverified scope")
    if agent_inferred:
        reasons.append("agent-inferred oracle cannot prove correctness")
    if not coverage:
        reasons.append("coverage_scope missing")
    if coverage in {"structural_only", "sample_only", "partial"}:
        reasons.append(f"coverage_scope={coverage}")
    if source_recomputed + external_authoritative <= 0:
        if user_provided_target > 0:
            reasons.append("only user-provided target oracle; source truth not independently proven")
        else:
            reasons.append("strong oracle provenance missing")
    if reasons:
        return "partial_verified", reasons
    return "verified", ["validation contract proves required scope"]


def _delivery_gate(status):
    if status == "verified":
        return "final_allowed"
    if status == "partial_verified":
        return "boundary_only"
    return "blocked"


def _apply_validation_contract(run_dir, contract_path):
    info = _load(run_dir)
    c = json.load(open(contract_path, encoding="utf-8"))
    status, reasons = _contract_status(c)
    contract_name = os.path.basename(contract_path)
    dest = os.path.join(run_dir, contract_name)
    if os.path.abspath(contract_path) != os.path.abspath(dest):
        shutil.copy2(contract_path, dest)
    info["status"] = status
    info["validation"] = {
        "run_status": status,
        "contract_status": c.get("status"),
        "status": c.get("status"),  # legacy machine field; YAML emits contract_status to avoid ambiguity.
        "validator_exit_code": c.get("validator_exit_code"),
        "coverage_scope": c.get("coverage_scope"),
        "total_checks": c.get("total_checks"),
        "failed_checks": c.get("failed_checks"),
        "contract_file": contract_name,
        "delivery_gate": _delivery_gate(status),
        "final_conclusion_allowed": status == "verified",
        "boundary_delivery_allowed": status in {"verified", "partial_verified"},
        "reason": "; ".join(reasons),
        "reasons": reasons,
        "unverified_scope": c.get("unverified_scope") or [],
        "assumptions": c.get("assumptions") or [],
        "oracle_provenance_summary": c.get("oracle_provenance_summary") or {},
    }
    steps = info.setdefault("steps", [])
    for s in steps:
        if s["step"] == "validation":
            s["status"] = "done" if status in {"verified", "partial_verified"} else "failed"
            break
    else:
        steps.append({"step": "validation", "status": "done" if status in {"verified", "partial_verified"} else "failed"})
    _save(run_dir, info)
    return info


def _max_date(paths):
    mx, mn = "", "9999-99-99"
    for p in paths:
        with open(p, encoding="utf-8") as f:
            r = csv.DictReader(f)
            if "date" not in (r.fieldnames or []):
                continue
            for row in r:
                dt = (row.get("date") or "").strip()
                if re.match(r"^\d{4}-\d{2}-\d{2}$", dt):
                    mx, mn = max(mx, dt), min(mn, dt)
    return (mn if mn != "9999-99-99" else None), (mx or None)


def cmd_finalize(a):
    d = os.path.abspath(a.dir)
    info = _load(d)
    if a.data_date:
        dd, mn = a.data_date, None
    else:
        mn, mx = _max_date(a.csv or [])
        if not mx:
            sys.exit("finalize 失败：无法从 CSV 取得数据截止日期（date 列缺失或为空），可用 --data-date 指定")
        dd = mx.replace("-", "")
    parent, sid = os.path.dirname(d), info.get("suite_id", "suite")
    seq = 1
    for name in os.listdir(parent):
        m = re.match(rf"^{re.escape(sid)}_{dd}_(\d{{3}})$", name)
        if m:
            seq = max(seq, int(m.group(1)) + 1)
    final = os.path.join(parent, f"{sid}_{dd}_{seq:03d}")
    outs = []
    for p in a.csv or []:
        rows = sum(1 for _ in open(p, encoding="utf-8")) - 1
        outs.append({"file": os.path.basename(p), "rows": rows})
    validation_contract = a.validation_contract
    if validation_contract and os.path.abspath(validation_contract).startswith(d + os.sep):
        rel = os.path.relpath(os.path.abspath(validation_contract), d)
        validation_contract = os.path.join(final, rel)
    os.rename(d, final)
    info["run_id"] = f"{dd}_{seq:03d}"
    info["status"] = "generated"
    info["data_date_range"] = {"min": mn, "max": f"{dd[:4]}-{dd[4:6]}-{dd[6:]}"}
    if outs:
        info["outputs"] = outs
    for kv in a.extra or []:
        k, _, v = kv.partition("=")
        info[k] = v
    _save(final, info)
    if validation_contract:
        info = _apply_validation_contract(final, validation_contract)
    if a.usage and info.get("status") in {"verified", "partial_verified"}:
        updated, msg = _usage_update(a.usage, sid, info.get("run_id"), info["status"])
        print(f"usage -> {'updated' if updated else 'skipped'}: {msg}")
    print(final)


def cmd_validate(a):
    info = _apply_validation_contract(os.path.abspath(a.dir), a.contract)
    if a.usage and info.get("status") in {"verified", "partial_verified"}:
        updated, msg = _usage_update(a.usage, info.get("suite_id", "suite"), info.get("run_id"), info["status"])
        print(f"usage -> {'updated' if updated else 'skipped'}: {msg}")
    print(f"validation -> {info['status']}: {info['validation']['reason']}")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("create"); c.add_argument("--root", required=True)
    c.add_argument("--kind", choices=["pipelines", "analysis"], required=True)
    c.add_argument("--id", required=True); c.set_defaults(f=cmd_create)
    s = sub.add_parser("step"); s.add_argument("--dir", required=True)
    s.add_argument("--step", required=True)
    s.add_argument("--status", choices=["done", "failed", "running"], required=True)
    s.set_defaults(f=cmd_step)
    t = sub.add_parser("status"); t.add_argument("--dir", required=True); t.set_defaults(f=cmd_status)
    z = sub.add_parser("finalize"); z.add_argument("--dir", required=True)
    z.add_argument("--csv", action="append"); z.add_argument("--data-date")
    z.add_argument("--validation-contract"); z.add_argument("--usage"); z.add_argument("--extra", action="append")
    z.set_defaults(f=cmd_finalize)
    v = sub.add_parser("validate"); v.add_argument("--dir", required=True)
    v.add_argument("--contract", required=True); v.add_argument("--usage")
    v.set_defaults(f=cmd_validate)
    a = p.parse_args(); a.f(a)


if __name__ == "__main__":
    main()
