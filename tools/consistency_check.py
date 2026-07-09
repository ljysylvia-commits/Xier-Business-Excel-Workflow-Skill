#!/usr/bin/env python3
"""consistency_check —— 反漂移校验 + manifest 汇编 + 注册质检（确定性工具）

依赖: PyYAML（pip install pyyaml；只有检查已注册 yaml 套件时需要）

用法:
  python3 consistency_check.py --skill-root SKILL_DIR [--write-manifest] [--changed SUITE_ID]

检查项（对每个套件 data_acquisition/sources/*/acquisition.yaml、pipelines/*/pipeline.yaml 与 analysis/scenes/*/scene.yaml）:
  C1 必备文件齐全: yaml / plan.md / CALIBERS.md / LEARNINGS.md / scripts 目录
  C2 yaml 引用存在: transform|execution 各 step 脚本、validation 各层脚本、calibers、references、entrypoint
  C3 脚本可编译: scripts/*.py 逐个 py_compile
  C4 requires 可导入: yaml requires 中的 python 包逐个尝试 import（libreoffice 检查 soffice 命令）
  C5 外部绝对路径扫描: scripts/*.py|*.sh 中出现 skill 外绝对路径（/root/ /home/ /Users/ 等）即报
  C6 manifest 一致性: manifest 条目与套件 yaml 的 id/mode/hint/keywords/version 一致
  C7 版本影响分析(--changed): 列出 inputs 依赖该动线的全部场景，提醒复核
  C8 validation contract 声明: 套件 yaml 必须声明 validation_contract
  C9 校验隔离静态检查: validate/verify 脚本不得 import 主生成脚本模块
  D1 data_acquisition 必备文件齐全: acquisition.yaml / plan.md / ACCESS.md / LEARNINGS.md
  D2 data_acquisition execution refs 必须存在，且不能越过 source 目录
  D3 data_acquisition credential_policy 与 validation.checks 必须存在
  D4 data_acquisition prompt/subagent usage 与引用文件一致

行为约定: 只报告差异清单，不硬性拒绝——Agent 据此给对齐建议，决策由用户做。
退出码: 0=无发现 / 1=有发现（供脚本化使用；不代表禁止继续）。
"""
import argparse, json, os, py_compile, re, shutil, subprocess, sys

try:
    import yaml
except ImportError:
    yaml = None

FIND = []


def rpt(level, suite, code, msg):
    FIND.append((level, suite, code, msg))


def _steps(y):
    out = []
    for sec in ("transform", "execution"):
        for st in (y.get(sec) or {}).get("steps", []) or []:
            if st.get("script"):
                out.append(st["script"])
    for lv in (y.get("validation") or {}).get("layers", []) or []:
        if lv.get("script"):
            out.append(lv["script"])
    return out


def _script_module(path):
    return os.path.splitext(os.path.basename(path))[0]


def _validation_scripts(y):
    out = []
    for lv in (y.get("validation") or {}).get("layers", []) or []:
        if lv.get("script"):
            out.append(lv["script"])
    for st in (y.get("execution") or {}).get("steps", []) or []:
        script = st.get("script") or ""
        if re.search(r"(^|/)validate|(^|/)verify", script):
            out.append(script)
    return sorted(set(out))


def _main_scripts(y):
    vals = set(_validation_scripts(y))
    out = []
    for sec in ("transform", "execution"):
        for st in (y.get(sec) or {}).get("steps", []) or []:
            script = st.get("script")
            if script and script not in vals:
                out.append(script)
    return out


def _iter_ref_values(execution):
    refs = []
    for key in ("instruction_ref", "prompt_ref", "subagent_task_ref"):
        val = execution.get(key)
        if val:
            refs.append((key, val))
    for val in execution.get("required_refs") or []:
        refs.append(("required_refs", val))
    for val in execution.get("ref_read_order") or []:
        refs.append(("ref_read_order", val))
    return refs


def _ref_inside(base, ref):
    if os.path.isabs(ref):
        return False
    target = os.path.abspath(os.path.join(base, ref))
    base_abs = os.path.abspath(base)
    return target == base_abs or target.startswith(base_abs + os.sep)


def _compile_source_scripts(sid, sdir):
    spath = os.path.join(sdir, "scripts")
    if os.path.isdir(spath):
        for fn in sorted(os.listdir(spath)):
            if fn.endswith(".py"):
                try:
                    py_compile.compile(os.path.join(spath, fn), doraise=True)
                except py_compile.PyCompileError as e:
                    rpt("ERROR", sid, "C3", f"{fn} 编译失败: {str(e).splitlines()[-1]}")
    return spath


def _scan_external_paths(sid, spath):
    pat = re.compile(r"""['"](/(?:root|home|Users|usr/local|opt)/[^'"]+)['"]""")
    if os.path.isdir(spath):
        for fn in sorted(os.listdir(spath)):
            if fn.endswith((".py", ".sh")):
                for i, line in enumerate(open(os.path.join(spath, fn), encoding="utf-8", errors="replace"), 1):
                    m = pat.search(line)
                    if m:
                        rpt("ERROR", sid, "C5", f"{fn}:{i} 引用外部绝对路径 {m.group(1)}")


def _find_sensitive_key_values(obj, path=""):
    hits = []
    sensitive = {"password", "passwd", "cookie", "token", "api_key", "apikey", "secret", "client_secret"}
    if isinstance(obj, dict):
        for k, v in obj.items():
            key = str(k).lower()
            p = f"{path}.{k}" if path else str(k)
            if key in sensitive and v not in (None, "", False):
                hits.append(p)
            hits.extend(_find_sensitive_key_values(v, p))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            hits.extend(_find_sensitive_key_values(v, f"{path}[{i}]"))
    return hits


def check_data_source(root, sdir):
    sid = os.path.basename(sdir)
    ypath = os.path.join(sdir, "acquisition.yaml")
    if not os.path.exists(ypath):
        rpt("ERROR", sid, "D1", "缺少 acquisition.yaml")
        return None
    if yaml is None:
        rpt("ERROR", sid, "C4", "缺少依赖 PyYAML，无法解析 acquisition.yaml: pip install pyyaml")
        return None
    try:
        y = yaml.safe_load(open(ypath, encoding="utf-8")) or {}
    except yaml.YAMLError as e:
        rpt("ERROR", sid, "D1", f"acquisition.yaml 解析失败: {e}")
        return None
    for f in ("plan.md", "ACCESS.md", "LEARNINGS.md"):
        if not os.path.exists(os.path.join(sdir, f)):
            rpt("ERROR", sid, "D1", f"缺少 {f}")
    execution = y.get("execution") or {}
    mode = execution.get("mode")
    if not mode:
        rpt("ERROR", sid, "D2", "execution.mode 必须存在")
    for key, ref in _iter_ref_values(execution):
        if not isinstance(ref, str):
            rpt("ERROR", sid, "D2", f"{key} 必须是相对文件路径: {ref}")
            continue
        if not _ref_inside(sdir, ref):
            rpt("ERROR", sid, "D2", f"{key} 引用越过 source 目录或使用绝对路径: {ref}")
            continue
        if not os.path.exists(os.path.join(sdir, ref)):
            rpt("ERROR", sid, "D2", f"{key} 引用不存在: {ref}")
    prompt_ref = execution.get("prompt_ref")
    prompt_usage = execution.get("prompt_usage")
    if prompt_ref and prompt_usage not in ("execute_locally", "handoff_to_skill", "handoff_to_subagent"):
        rpt("ERROR", sid, "D4", "prompt_ref 非空时 prompt_usage 必须是 execute_locally / handoff_to_skill / handoff_to_subagent")
    if prompt_ref and prompt_ref not in (execution.get("required_refs") or []) + (execution.get("ref_read_order") or []):
        rpt("ERROR", sid, "D4", f"prompt_ref {prompt_ref} 必须出现在 required_refs 或 ref_read_order")
    sub_ref = execution.get("subagent_task_ref")
    sub_usage = execution.get("subagent_usage")
    if sub_ref and sub_usage not in ("spawn_subagent", "handoff_to_existing_agent"):
        rpt("ERROR", sid, "D4", "subagent_task_ref 非空时 subagent_usage 必须是 spawn_subagent / handoff_to_existing_agent")
    if sub_ref and sub_ref not in (execution.get("required_refs") or []) + (execution.get("ref_read_order") or []):
        rpt("ERROR", sid, "D4", f"subagent_task_ref {sub_ref} 必须出现在 required_refs 或 ref_read_order")
    policy = execution.get("instruction_policy") or {}
    if policy.get("must_read_refs_before_execution") is not True:
        rpt("ERROR", sid, "D4", "instruction_policy.must_read_refs_before_execution 必须为 true")
    if policy.get("stop_if_ref_missing") is not True:
        rpt("ERROR", sid, "D4", "instruction_policy.stop_if_ref_missing 必须为 true")
    if not ((y.get("permission") or {}).get("credential_policy")):
        rpt("ERROR", sid, "D3", "permission.credential_policy 必须存在")
    if not ((y.get("validation") or {}).get("checks")):
        rpt("ERROR", sid, "D3", "validation.checks 必须存在")
    for hit in _find_sensitive_key_values(y):
        rpt("ERROR", sid, "D3", f"acquisition.yaml 可能包含敏感明文字段: {hit}")
    spath = _compile_source_scripts(sid, sdir)
    _scan_external_paths(sid, spath)
    return y


def check_suite(root, kind, sdir):
    sid = os.path.basename(sdir)
    yname = "pipeline.yaml" if kind == "pipelines" else "scene.yaml"
    ypath = os.path.join(sdir, yname)
    if not os.path.exists(ypath):
        rpt("ERROR", sid, "C1", f"缺少 {yname}")
        return None
    if yaml is None:
        rpt("ERROR", sid, "C4", "缺少依赖 PyYAML，无法解析已注册套件 yaml: pip install pyyaml")
        return None
    try:
        y = yaml.safe_load(open(ypath, encoding="utf-8")) or {}
    except yaml.YAMLError as e:
        rpt("ERROR", sid, "C1", f"{yname} 解析失败: {e}")
        return None
    for f in ("plan.md", "CALIBERS.md", "LEARNINGS.md"):
        if not os.path.exists(os.path.join(sdir, f)):
            rpt("ERROR", sid, "C1", f"缺少 {f}")
    # C2 引用存在
    refs = _steps(y) + (y.get("references") or [])
    if y.get("calibers"):
        refs.append(y["calibers"])
    if y.get("entrypoint"):
        refs.append(y["entrypoint"])
    pd = ((y.get("understand") or {}).get("profile_detect") or {}).get("script")
    if pd:
        refs.append(pd)
    for r in refs:
        if not os.path.exists(os.path.join(sdir, r)):
            rpt("ERROR", sid, "C2", f"yaml 引用不存在: {r}")
    # C8 validation contract 声明
    vc = y.get("validation_contract")
    if not vc:
        rpt("ERROR", sid, "C8", "缺少 validation_contract 声明")
    elif not isinstance(vc, dict) or not vc.get("produces"):
        rpt("ERROR", sid, "C8", "validation_contract 必须声明 produces")
    # C3 py_compile
    spath = _compile_source_scripts(sid, sdir)
    # C4 requires
    for req in y.get("requires") or []:
        if req == "libreoffice":
            if not shutil.which("soffice"):
                rpt("WARN", sid, "C4", "未找到 soffice 命令（libreoffice）")
        else:
            r = subprocess.run([sys.executable, "-c", f"import {req}"], capture_output=True)
            if r.returncode != 0:
                rpt("WARN", sid, "C4", f"依赖不可导入: {req}")
    # C5 外部绝对路径
    _scan_external_paths(sid, spath)
    # C9 校验脚本不得 import 主生成脚本
    main_modules = {_script_module(s) for s in _main_scripts(y)}
    for script in _validation_scripts(y):
        path = os.path.join(sdir, script)
        if not os.path.exists(path) or not path.endswith(".py"):
            continue
        text = open(path, encoding="utf-8", errors="replace").read()
        for mod in main_modules:
            if re.search(rf"^\s*(import\s+{re.escape(mod)}|from\s+{re.escape(mod)}\s+import)\b", text, re.M):
                rpt("ERROR", sid, "C9", f"{script} import 主生成脚本模块 {mod}")
    return y


def assemble(root, kind, suites):
    entries = []
    for sid, y in suites.items():
        u = y.get("understand") or {}
        e = {"id": y.get("pipeline_id") or y.get("scene_id") or sid,
             "status": y.get("status", "draft"), "version": str(y.get("version", "0.1")),
             "yaml": f"{sid}/pipeline.yaml" if kind == "pipelines" else f"scenes/{sid}/scene.yaml"}
        if kind == "pipelines":
            e["mode"] = u.get("mode", "fixed")
            if u.get("filename_hint"):
                e["filename_hint"] = u["filename_hint"]
            if u.get("pattern_hint"):
                e["pattern_hint"] = u["pattern_hint"]
            rs = ((u.get("fingerprint") or {}).get("required_sheets") or [])[:2]
            if rs:
                e["fingerprint_hint"] = rs
        else:
            e["keywords"] = (y.get("trigger") or {}).get("keywords", [])
            e["inputs"] = [p.get("id") for p in (y.get("inputs") or {}).get("pipelines", []) or []]
        entries.append(e)
    return {"pipelines" if kind == "pipelines" else "scenes": entries}


def assemble_sources(root, suites):
    entries = []
    for sid, y in suites.items():
        execution = y.get("execution") or {}
        output = y.get("output") or {}
        entries.append({
            "id": y.get("source_id") or sid,
            "status": y.get("status", "draft"),
            "version": str(y.get("version", "0.1")),
            "yaml": f"sources/{sid}/acquisition.yaml",
            "source_type": y.get("source_type", "unknown"),
            "execution_mode": execution.get("mode", "unknown"),
            "raw_format": output.get("raw_format", "unknown"),
        })
    return {"sources": entries}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skill-root", required=True)
    ap.add_argument("--write-manifest", action="store_true")
    ap.add_argument("--changed", help="动线 id：列出依赖它的场景（版本影响分析）")
    a = ap.parse_args()
    root = a.skill_root
    all_suites = {}
    # data_acquisition sources
    src_base = os.path.join(root, "data_acquisition", "sources")
    src_suites = {}
    if os.path.isdir(src_base):
        for name in sorted(os.listdir(src_base)):
            sdir = os.path.join(src_base, name)
            if not os.path.isdir(sdir) or name.startswith("_"):
                continue
            y = check_data_source(root, sdir)
            if y:
                src_suites[name] = y
    all_suites["data_acquisition"] = src_suites
    src_manifest = os.path.join(root, "data_acquisition", "manifest.json")
    src_new = assemble_sources(root, src_suites)
    if os.path.isdir(os.path.dirname(src_manifest)):
        if a.write_manifest:
            json.dump(src_new, open(src_manifest, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
            print(f"manifest 已汇编: {src_manifest}")
        elif os.path.exists(src_manifest):
            cur = json.load(open(src_manifest, encoding="utf-8"))
            if cur != src_new:
                rpt("WARN", "data_acquisition", "C6", f"{src_manifest} 与 source yaml 汇编结果不一致（可用 --write-manifest 重生成）")
    for kind, base in (("pipelines", "pipelines"), ("analysis", os.path.join("analysis", "scenes"))):
        bdir = os.path.join(root, base)
        suites = {}
        if os.path.isdir(bdir):
            for name in sorted(os.listdir(bdir)):
                sdir = os.path.join(bdir, name)
                if not os.path.isdir(sdir) or name.startswith("_"):
                    continue
                y = check_suite(root, "pipelines" if kind == "pipelines" else "scenes", sdir)
                if y:
                    suites[name] = y
        all_suites[kind] = suites
        # C6/汇编
        mpath = os.path.join(root, "pipelines" if kind == "pipelines" else "analysis", "manifest.json")
        new = assemble(root, "pipelines" if kind == "pipelines" else "scenes", suites)
        if a.write_manifest:
            json.dump(new, open(mpath, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
            print(f"manifest 已汇编: {mpath}")
        elif os.path.exists(mpath):
            cur = json.load(open(mpath, encoding="utf-8"))
            if cur != new:
                rpt("WARN", kind, "C6", f"{mpath} 与套件 yaml 汇编结果不一致（可用 --write-manifest 重生成）")
    # C7 影响分析
    if a.changed:
        hit = [sid for sid, y in all_suites.get("analysis", {}).items()
               if a.changed in [p.get("id") for p in (y.get("inputs") or {}).get("pipelines", []) or []]]
        print(f"[影响分析] 动线 {a.changed} 变更 → 需复核的场景: {hit or '（无）'}")
    # 报告
    if not FIND:
        print("✅ consistency_check: 无发现")
        sys.exit(0)
    print(f"发现 {len(FIND)} 项差异（报告供用户拍板，不硬性拒绝）：")
    for lv, sid, code, msg in FIND:
        print(f"  [{lv}] [{sid}] {code}: {msg}")
    sys.exit(1)


if __name__ == "__main__":
    main()
