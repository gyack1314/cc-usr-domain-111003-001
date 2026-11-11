"""预审分析：基于已下载的门户附件副本与本地材料，按规程逐日核对四支队伍。

规则编码（materials/policy.md）：
- 区间首尾包含；撤销自指定日起生效（当日即不可用）；
- 授权仅可缩小上游范围；转授权须上游明确许可；
- 缺环、环路、同权冲突不构成可用授权；集团关系不提供执业权；
- 电气/高空/一般巡检分别核对，不跨类别互认。
核心区间与图计算调用 workbench 领域工具（CLI），输入输出留档于 output/verification。
用法: python3 -I scripts/analyze.py
"""
import csv
import json
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, "/workspace")
from workbench.evidence import Journal, atomic_json  # noqa: E402

WS = Path("/workspace")
EV = WS / "output" / "evidence"
VER = WS / "output" / "verification"
OUT = WS / "output"
JOURNAL = Journal(WS / "state" / "journal.sqlite3")


def load_attachment(rid):
    return json.loads((EV / "attachments" / rid / f"{rid}.json").read_text(encoding="utf-8"))


def tool_call(name, payload, tag):
    """调用项目领域工具并留档输入输出。"""
    inp = VER / "tool_inputs" / f"{tag}.json"
    outp = VER / "tool_outputs" / f"{tag}.json"
    atomic_json(inp, payload)
    proc = subprocess.run(
        [sys.executable, "-m", "workbench.tools", "call", name, str(inp)],
        cwd=WS, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"工具调用失败 {name} {tag}: {proc.stderr}")
    result = json.loads(proc.stdout)
    atomic_json(outp, {"tool": name, "input_file": str(inp.relative_to(WS)), "result": result})
    return result


def days(d0, d1):
    a, b = date.fromisoformat(d0), date.fromisoformat(d1)
    return [(a + timedelta(days=i)).isoformat() for i in range((b - a).days + 1)]


def journal_note(prefix, note):
    """幂等登记：内容未变则复用已有键；内容有修订则启用新键并注明前序。"""
    existing = {e["key"]: e["note"] for e in JOURNAL.read()}
    n = 0
    while True:
        n += 1
        key = f"{prefix}-v{n}"
        if key not in existing:
            if n > 1:
                note = {**note, "supersedes": f"{prefix}-v{n-1}"}
            return JOURNAL.append(key, note)
        if existing[key] == note or existing[key] == {**note, "supersedes": f"{prefix}-v{n-1}"}:
            return JOURNAL.append(key, existing[key])


def main():
    index = json.loads((EV / "index.json").read_text(encoding="utf-8"))
    recs = {rid: load_attachment(rid) for rid in index["records"]}
    refs = {rid: index["records"][rid]["reference"] for rid in recs}

    shifts = list(csv.DictReader((WS / "materials" / "shifts.csv").read_text(encoding="utf-8").splitlines()))
    entities = {r["code"]: r for r in csv.DictReader((WS / "materials" / "entities.csv").read_text(encoding="utf-8").splitlines())}

    certs = {i: r["fields"] for i, r in recs.items() if r["category"] == "证照"}
    auths = {i: dict(r["fields"]) for i, r in recs.items() if r["category"] == "授权"}
    revos = [r["fields"] for r in recs.values() if r["category"] == "撤销"]
    persons = {i: r["fields"] for i, r in recs.items() if r["category"] == "人员"}

    # 撤销：自 effective 日起目标授权不可用（区间首尾包含 → 有效至前一日）
    for rv in revos:
        tgt = auths[rv["target"]]
        cut = (date.fromisoformat(rv["effective"]) - timedelta(days=1)).isoformat()
        tgt["end"] = min(tgt["end"], cut)
        tgt["revoked_by"] = rv

    def cert_covers(entity, activity, day):
        return [cid for cid, c in certs.items()
                if c["entity"] == entity and activity in c["scope"] and c["start"] <= day <= c["end"]]

    def chain_ok(entity, activity, day):
        """当日是否存在从持证主体到 entity 的可用授权链（简单路径，排除环路）。"""
        if cert_covers(entity, activity, day):
            return True, []
        edges = [(aid, a["grantor"], a["grantee"]) for aid, a in auths.items()
                 if activity in a["scope"] and a["start"] <= day <= a["end"]]
        holders = {c["entity"] for c in certs.values()
                   if activity in c["scope"] and c["start"] <= day <= c["end"]}
        # 深搜简单路径：起点为当日持证主体；继续下一段须上一环 redelegate=True
        stack = [(h, [], {h}) for h in holders]
        while stack:
            node, path, seen = stack.pop()
            for aid, g0, g1 in edges:
                if g0 != node or g1 in seen:
                    continue
                if path and not auths[path[-1]]["redelegate"]:
                    continue  # 上一环未许可转授权
                newpath = path + [aid]
                if g1 == entity:
                    return True, newpath
                stack.append((g1, newpath, seen | {g1}))
        return False, []

    analysis = {"window": ["2026-11-16", "2026-11-30"], "teams": {}, "tool_checks": []}
    for s in shifts:
        team, ent, act = s["team"], s["entity"], s["activity"]
        crew = s["crew"].split("|")
        win_days = days(s["start"], s["end"])
        ent_days, ent_chains = [], {}
        for d in win_days:
            ok, chain = chain_ok(ent, act, d)
            if ok:
                ent_days.append(d)
                ent_chains[d] = chain
        per_person = {}
        for p in crew:
            prec = {i: f for i, f in persons.items() if f["person"] == p and f["entity"] == ent and act in f["scope"]}
            covered = [d for d in win_days if any(f["start"] <= d <= f["end"] for f in prec.values())]
            per_person[p] = {"covered": covered, "records": sorted(prec)}
        all_crew_days = [d for d in ent_days if all(d in per_person[p]["covered"] for p in crew)]
        analysis["teams"][team] = {
            "entity": ent, "entity_name": entities[ent]["name"], "activity": act,
            "zone": s["zone"], "window": [s["start"], s["end"]], "crew": crew,
            "entity_days": ent_days, "entity_chain_refs": {d: c for d, c in ent_chains.items() if c},
            "person_days": per_person, "team_days_all_crew": all_crew_days,
            "gap_days": [d for d in win_days if d not in all_crew_days],
        }

    # ---- 领域工具留痕核对 ----
    t = analysis["teams"]
    checks = [
        ("intersection", {"windows": [t["T1"]["window"], [certs["C1"]["start"], certs["C1"]["end"]]]}, "T1-cert-C1"),
        ("intersection", {"windows": [t["T1"]["window"], [certs["C2"]["start"], certs["C2"]["end"]]]}, "T1-cert-C2"),
        ("intersection", {"windows": [t["T1"]["window"], [persons["P2"]["start"], persons["P2"]["end"]]]}, "T1-person-P2"),
        ("intersection", {"windows": [t["T2"]["window"], [auths["A1"]["start"], auths["A1"]["end"]]]}, "T2-auth-A1-有效段"),
        ("intersection", {"windows": [t["T4"]["window"], [auths["A2"]["start"], auths["A2"]["end"]]]}, "T4-auth-A2-区间"),
        ("scope_intersection", {"scopes": [auths["A1"]["scope"], auths["A2"]["scope"]]}, "chain-A1-A2-范围交集"),
        ("reachable", {"edges": [[a["grantor"], a["grantee"]] for a in auths.values() if "电气" in a["scope"]],
                       "start": "91330001A", "target": "91330004D"}, "电气授权图-总部至远岸"),
        ("reachable", {"edges": [[a["grantor"], a["grantee"]] for a in auths.values()],
                       "start": "91330001A", "target": "91330004D"}, "全授权图-总部至远岸"),
    ]
    for name, payload, tag in checks:
        analysis["tool_checks"].append({"tag": tag, "tool": name, "result": tool_call(name, payload, tag)})

    atomic_json(OUT / "analysis.json", {"refs": refs, **analysis})
    journal_note("analysis", {
        "basis": "output/evidence 下载附件 + materials 本地材料",
        "team_days": {k: v["team_days_all_crew"] for k, v in analysis["teams"].items()},
        "gaps": {k: v["gap_days"] for k, v in analysis["teams"].items()}})
    print(json.dumps({k: {"可确定": v["team_days_all_crew"], "缺口": v["gap_days"]}
                      for k, v in analysis["teams"].items()}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
