"""可复查验证：重核材料指纹、证据完整性、台账/意见引用、领域工具留痕与门户草稿状态。

用法: python3 -I scripts/verify_all.py   （门户需在 127.0.0.1:8765 运行）
"""
import json
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, "/workspace")
from workbench.evidence import Journal, digest  # noqa: E402

WS = Path("/workspace")
OUT = WS / "output"
PORTAL = "http://127.0.0.1:8765"
failures = []


def check(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + (f" | {detail}" if detail else ""))
    if not ok:
        failures.append(name)


def sha_file(p):
    return digest(Path(p).read_bytes())


def get(url):
    with urllib.request.urlopen(url) as r:
        return r.read()


# 1. 本地材料指纹
proc = subprocess.run([sys.executable, "-m", "workbench.tools", "verify", "materials",
                       "state/materials-manifest.json"], cwd=WS, capture_output=True, text=True)
check("本地材料指纹未变", proc.returncode == 0 and json.loads(proc.stdout) == [], proc.stdout.strip())

# 2. 证据完整性：下载件指纹 == 索引登记值
index = json.loads((OUT / "evidence" / "index.json").read_text(encoding="utf-8"))
for rid, r in sorted(index["records"].items()):
    att = OUT / "evidence" / "attachments" / rid / f"{rid}.json"
    doc = OUT / "evidence" / "documents" / rid / r["document_file"]
    check(f"{rid} 附件指纹", att.is_file() and sha_file(att) == r["attachment_sha256"])
    check(f"{rid} 文书指纹", doc.is_file() and sha_file(doc) == r["document_sha256"])
    # 3. 门户在线摘要与留存附件一致（重新经 HTTP 取得）
    live = digest(get(f"{PORTAL}/attachment/{rid}"))
    check(f"{rid} 门户在线摘要一致", live == r["attachment_sha256"])

# 4. 台账与意见中的引用必须存在于证据索引
refs = {r["reference"] for r in index["records"].values()}
for doc in ["ledger.md", "opinion.md"]:
    text = (OUT / doc).read_text(encoding="utf-8")
    cited = set(re.findall(r"[A-Z]\d+@[0-9a-f]{64}", text))
    check(f"{doc} 引用均可回溯({len(cited)}条)", cited <= refs,
          "" if cited <= refs else str(cited - refs))

# 5. 领域工具留痕可重放
for out in sorted((OUT / "verification" / "tool_outputs").glob("*.json")):
    rec = json.loads(out.read_text(encoding="utf-8"))
    proc = subprocess.run([sys.executable, "-m", "workbench.tools", "call", rec["tool"],
                           str(WS / rec["input_file"])], cwd=WS, capture_output=True, text=True)
    check(f"工具重放 {out.name}", proc.returncode == 0 and json.loads(proc.stdout) == rec["result"])

# 6. 分析结论与台账总览一致
analysis = json.loads((OUT / "analysis.json").read_text(encoding="utf-8"))
ledger = (OUT / "ledger.md").read_text(encoding="utf-8")
expect = {"T1": "全体排班人员可确定至 11-25", "T2": "仅 11-16 至 11-18",
          "T3": "全程可确定", "T4": "无可确定范围"}
for t, phrase in expect.items():
    days = analysis["teams"][t]["team_days_all_crew"]
    check(f"{t} 台账结论与分析一致", phrase in ledger and (
        (t == "T1" and days[-1] == "2026-11-25" and len(days) == 10) or
        (t == "T2" and days == ["2026-11-16", "2026-11-17", "2026-11-18"]) or
        (t == "T3" and len(days) == 13) or
        (t == "T4" and days == [])))

# 7. 门户草稿：存在、待人工审批、引用与分析一致
payload = json.loads((OUT / "draft_payload.json").read_text(encoding="utf-8"))
html = get(f"{PORTAL}/draft/{payload['key']}").decode("utf-8")
m = re.search(r'data-testid="draft-status">([^<]*)<', html)
check("草稿存在且状态为待人工审批", bool(m) and m.group(1) == "待人工审批", m.group(1) if m else "无状态")
check("草稿引用与分析一致", all(r in html for r in payload["refs"]))
check("无已批准/已签发状态痕迹", "已批准" not in html and "已签发" not in html)

# 8. 进度账可读
notes = Journal(WS / "state" / "journal.sqlite3").read()
check("进度账可读", len(notes) >= 15, f"{len(notes)} 条")

print("\n" + ("全部通过" if not failures else f"失败 {len(failures)} 项: {failures}"))
sys.exit(1 if failures else 0)
