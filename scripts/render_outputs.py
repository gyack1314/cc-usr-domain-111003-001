"""由 analysis.json + 证据索引生成审查台账与负责人意见，保证编号、指纹、日期机器誊写。

用法: python3 -I scripts/render_outputs.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, "/workspace")
from workbench.evidence import atomic_json  # noqa: E402

WS = Path("/workspace")
OUT = WS / "output"
EV = OUT / "evidence"

CN_SCOPE = {"电气": "电气", "高空": "高空", "一般巡检": "一般巡检"}


def load(p):
    return json.loads(p.read_text(encoding="utf-8"))


def main():
    analysis = load(OUT / "analysis.json")
    index = load(EV / "index.json")
    manifest = load(WS / "state" / "materials-manifest.json")
    refs = analysis["refs"]
    recs = index["records"]
    portal = index["portal"]
    teams = analysis["teams"]

    def evrow(rid, note):
        r = recs[rid]
        f = r["fields"]
        if "effective" in f:
            span = f"自 {f['effective']} 起生效"
        else:
            span = f"{f.get('start','')} 至 {f.get('end','')}"
        who = f.get("entity") or (f["grantor"] + "→" + f["grantee"] if "grantor" in f else "—")
        return (f"| {rid} | {who} "
                f"| {note} | {span} | {r['reference']} | {r['record_url']} |")

    L = []
    L.append("# 维保入场资料预审台账（2026-11-16 至 2026-11-30）\n")
    L.append("## 0. 审查基线\n")
    L.append(f"- 门户地址：{portal}（本地合成业务门户；资料引用格式 编号@SHA256）")
    L.append("- 取证方式：Playwright 浏览器逐页存档（output/evidence/pages）、实际下载附件（output/evidence/attachments）"
             "与文书副本（output/evidence/documents）；每份附件 SHA-256 已与详情页所示内容摘要核对一致。")
    L.append("- 判定口径：materials/policy.md（区间首尾包含；撤销自指定日起生效；授权仅可缩小上游范围；"
             "转授权须上游许可；缺环/环路/同权冲突无效；集团关系不提供执业权；类别不互认；预审不签发准入）。")
    L.append("- 本地材料指纹（state/materials-manifest.json）：")
    for m in manifest:
        L.append(f"  - {m['path']} sha256={m['sha256']}")
    L.append("- 区间与链路计算留痕：output/verification/tool_inputs 与 tool_outputs（workbench 领域工具 CLI）。")
    L.append("- 进度账：state/journal.sqlite3（workbench.evidence.Journal，修订以新键登记并注明前序）。\n")

    L.append("## 1. 结论总览\n")
    L.append("| 队伍 | 主体（统一社会信用代码） | 作业类别 | 区域 | 排班窗口 | 可确定服务范围 | 缺口 |")
    L.append("|---|---|---|---|---|---|---|")
    label = {"T1": "主体资质全程；全体排班人员可确定至 11-25", "T2": "仅 11-16 至 11-18",
             "T3": "全程可确定", "T4": "无可确定范围"}
    for t in ["T1", "T2", "T3", "T4"]:
        v = teams[t]
        gap = "、".join(d[5:] for d in v["gap_days"]) or "无"
        L.append(f"| {t} | {v['entity_name']}（{v['entity']}） | {v['activity']} | {v['zone']}区 "
                 f"| {v['window'][0]} 至 {v['window'][1]} | {label[t]} | {gap} |")
    L.append("")

    # ---- T1 ----
    L.append("## 2. T1 · 青禾维护总部（91330001A）· 电气 · A区 · 2026-11-16 至 11-30 · 人员 P1、P2\n")
    L.append("**结论：主体电气资质全程有效（C1 至 11-22，续期证明 C2 自 11-23 无缝衔接）；人员 P1 全程有效；"
             "人员 P2 执业材料仅至 2026-11-25。全体排班人员可确定服务至 11-25；11-26 至 11-30 为人员缺口。**\n")
    L.append("- 主体资质：C1（至 2026-11-22）+ C2（2026-11-23 起，supersedes C1，出具方 园区认可机构）逐日覆盖，"
             "衔接点 11-22/11-23 无空窗（工具留痕 T1-cert-C1、T1-cert-C2）。")
    L.append("- 人员：P1（至 2027-01-01）全程；P2 至 2026-11-25（工具留痕 T1-person-P2）。")
    L.append("- 缺口：2026-11-26 至 11-30 共 5 天，P2 无有效执业材料。\n")
    L.append("| 编号 | 主体 | 内容摘要 | 适用日期 | 引用（编号@SHA256） | 门户地址 |")
    L.append("|---|---|---|---|---|---|")
    L.append(evrow("C1", "总部电气资质（电气）"))
    L.append(evrow("C2", "总部电气续期证明，衔接 C1"))
    L.append(evrow("P1", "人员 P1 电气执业材料"))
    L.append(evrow("P2", "人员 P2 电气执业材料，至 11-25"))
    L.append("")
    L.append("可调整方案：① 11-26 至 11-30 改由 P1 单独上岗——可解决 P2 证件到期缺口，"
             "但属排班变更，需负责人批准，并需确认现场单人电气作业是否符合现场规程；"
             "② 更换为总部其他持电气执业材料人员——门户当前无此类人员记录，需先补该人员材料；"
             "③ P2 补办续期——需新执业材料入场后再核。\n")

    # ---- T2 ----
    L.append("## 3. T2 · 青禾维护分公司（91330002B）· 高空 · B区 · 2026-11-16 至 11-20 · 人员 P3\n")
    L.append("**结论：仅 2026-11-16 至 11-18 可确定；11-19、11-20 高空授权已被撤销，不可确定。**\n")
    L.append("- 分公司为独立法人（entities.csv：independent=是），集团关系不提供执业权；"
             "其高空作业须依赖总部 C3 高空证 + 授权 A1（总部→分公司，高空，redelegate=false）。")
    L.append("- 撤销记录 N1：A1 自 2026-11-19 起撤销（高空合作终止）。按规程撤销自指定日起生效，"
             "A1 有效段为 11-01 至 11-18，与排班窗口交集为 11-16 至 11-18（工具留痕 T2-auth-A1-有效段）。")
    L.append("- 人员 P3（分公司，高空，至 2027-01-01）全程有效；瓶颈在授权而非人员。")
    L.append("- 「以总部证书替分公司担保」不成立：C3 持证主体是总部，分公司入场必须有有效授权链，"
             "11-19 起该链已断。\n")
    L.append("| 编号 | 主体 | 内容摘要 | 适用日期 | 引用（编号@SHA256） | 门户地址 |")
    L.append("|---|---|---|---|---|---|")
    L.append(evrow("C3", "总部高空资质（高空）"))
    L.append(evrow("A1", "总部→分公司高空授权，不可转授权"))
    L.append(evrow("N1", "撤销 A1，自 2026-11-19 起生效"))
    L.append(evrow("P3", "人员 P3 高空执业材料"))
    L.append("")
    L.append("可调整方案：① 就 11-19 至 11-20 重新取得总部→分公司高空授权（补证后重审）；"
             "② 改由总部直接承接该两日高空作业——总部持 C3，但门户中无总部高空作业人员执业材料"
             "（P3 属分公司），需补人员证据并由负责人批准排班变更；"
             "③ 将该两日工作量提前至 11-18 前完成——需负责人评估工作量与现场条件。\n")

    # ---- T3 ----
    L.append("## 4. T3 · 海桥巡检（91330003C）· 一般巡检 · C区 · 2026-11-18 至 11-30 · 人员 P4\n")
    L.append("**结论：全程可确定（2026-11-18 至 11-30）。**\n")
    L.append("- 主体资质 C4（一般巡检，至 2027-01-01）与人员 P4（一般巡检，至 2027-01-01）逐日覆盖排班窗口；"
             "C区一般巡检可按巡检范围服务（materials/site.md）。无需授权链。\n")
    L.append("| 编号 | 主体 | 内容摘要 | 适用日期 | 引用（编号@SHA256） | 门户地址 |")
    L.append("|---|---|---|---|---|---|")
    L.append(evrow("C4", "海桥一般巡检资质"))
    L.append(evrow("P4", "人员 P4 一般巡检执业材料"))
    L.append("")

    # ---- T4 ----
    L.append("## 5. T4 · 远岸工程（91330004D）· 电气 · A区 · 2026-11-16 至 11-30 · 人员 P5\n")
    L.append("**结论：无可确定服务范围。远岸无自有电气资质，现有授权均为无源头的中间段，全窗口不成立。**\n")
    L.append("- 路径一（A2：分公司→远岸，含电气）：分公司自身无电气资质，其唯一入链 A1 仅含高空"
             "（工具留痕 chain-A1-A2-范围交集=[高空]），电气超出上游范围，依规程不成立；"
             "且 A1 redelegate=false 且自 11-19 被撤销，A2 的高空部分同样不成立。")
    L.append("- 路径二（A4：海桥→远岸，电气）：海桥电气权力仅来自 A3（远岸→海桥），A3/A4 互为环路，"
             "两端主体均无电气资质，无持证源头，依规程环路不构成可用授权。")
    L.append("- 领域工具核对：电气授权图中总部→远岸不可达（工具留痕 电气授权图-总部至远岸=False）；"
             "不过滤范围时可达（全授权图=True），说明原始连通性不足以认定授权。")
    L.append("- 人员 P5（远岸，电气，至 2027-01-01）虽有效，但主体层面无可用授权，不能据此入场。\n")
    L.append("| 编号 | 主体 | 内容摘要 | 适用日期 | 引用（编号@SHA256） | 门户地址 |")
    L.append("|---|---|---|---|---|---|")
    L.append(evrow("A2", "分公司→远岸授权（高空、电气），电气超上游范围"))
    L.append(evrow("A3", "远岸→海桥电气授权，与 A4 构成环路"))
    L.append(evrow("A4", "海桥→远岸电气授权，与 A3 构成环路"))
    L.append(evrow("P5", "人员 P5 电气执业材料"))
    L.append("")
    L.append("可调整方案：① 远岸补齐电气授权链——须自总部（当前唯一电气持证主体，C1/C2）取得覆盖 "
             "2026-11-16 至 11-30 的直接授权，或经分公司的连续链（每环含电气、转授权许可齐全、"
             "区间覆盖服务日），补齐后重审；② 负责人将 A 区电气工作改派 T1（总部）——"
             "需确认 T1 产能与排班冲突，属负责人裁决。\n")

    L.append("## 6. 未决事项登记\n")
    L.append("| 事项 | 类型 | 关联队伍 | 说明 |")
    L.append("|---|---|---|---|")
    L.append("| P2 执业材料 11-26 起缺失 | 必须补证 / 可调整人员 | T1 | 补 P2 续期，或负责人批准改 P1 单人/换人 |")
    L.append("| 高空授权 11-19 起被撤销 | 必须补证 / 可调整主体 | T2 | 重新授权，或总部承接（缺总部高空人员材料） |")
    L.append("| 电气授权链无源头、含环路 | 必须补证 / 可调整主体 | T4 | 补总部源头全链，或改派 T1 |")
    L.append("| C1→C2 续期衔接 | 已核对，备负责人复核 | T1 | 衔接点 11-22/11-23 无空窗，出具方 园区认可机构 |")
    L.append("")
    L.append("本台账为预审结论，不构成准入批准，未签发任何通行证；最终裁定权在准入负责人。\n")
    (OUT / "ledger.md").write_text("\n".join(L), encoding="utf-8")

    # ---- 负责人意见（即草稿正文） ----
    O = []
    O.append("维保入场资料预审意见（2026-11-16 至 2026-11-30）")
    O.append("")
    O.append("一、审查范围与方法")
    O.append("本次预审覆盖排班表 T1 至 T4 四支队伍在 2026-11-16 至 11-30 的入场资料。"
             "证据经浏览器从资料门户逐页取得并下载附件核对指纹（引用格式 编号@SHA256），"
             "判定依据为 materials/policy.md：按统一社会信用代码识别主体、区间首尾包含、"
             "授权仅可缩小上游范围、转授权须上游许可、撤销自指定日起生效、"
             "缺环环路与同权冲突不构成可用授权、集团关系不提供执业权、作业类别不互认。")
    O.append("")
    O.append("二、可确定的服务范围")
    t1, t2, t3 = teams["T1"], teams["T2"], teams["T3"]
    O.append(f"1. T1 青禾维护总部（91330001A）电气/A区：主体资质全程有效（C1 至 11-22，C2 自 11-23 衔接）；"
             "全体排班人员（P1、P2）在岗可确定至 2026-11-25；P1 单人全程可确定。")
    O.append(f"2. T2 青禾维护分公司（91330002B）高空/B区：仅 2026-11-16 至 11-18 可确定"
             "（授权 A1 自 11-19 被 N1 撤销）。")
    O.append(f"3. T3 海桥巡检（91330003C）一般巡检/C区：2026-11-18 至 11-30 全程可确定。")
    O.append("")
    O.append("三、必须补证的事项")
    O.append("1. T1：人员 P2 执业材料至 2026-11-25，11-26 至 11-30 共 5 天需补续期或更换持证人员。")
    O.append("2. T2：高空授权 A1 自 2026-11-19 起被撤销，11-19 至 11-20 需重新取得总部→分公司高空授权；"
             "分公司为独立法人，总部证书不能替代授权。")
    O.append("3. T4：远岸工程（91330004D）电气无可用授权链——A2 电气超出上游（分公司无电气来源）、"
             "A3/A4 互为环路且无持证源头；须补自总部（唯一电气持证主体）出发、覆盖 11-16 至 11-30、"
             "每环含电气且转授权许可齐全的完整链条，补齐前全窗口不可确定。")
    O.append("")
    O.append("四、需负责人裁决的事项")
    O.append("1. T1 11-26 至 11-30：批准改 P1 单人上岗（需确认现场允许单人电气作业），"
             "或批准更换人员（门户暂无其他总部电气人员材料），或等待 P2 补证。")
    O.append("2. T2 11-19 至 11-20：批准改由总部直接承接（需先补总部高空作业人员执业材料，"
             "现有 P3 属分公司），或调整班次至 11-18 前完成，或等待新授权。")
    O.append("3. T4 全窗口：批准将 A 区电气工作改派 T1（需确认产能与排班），或要求远岸补链后重审。")
    O.append("4. 备查：C1→C2 续期衔接点 11-22/11-23 无空窗，C2 出具方为 园区认可机构，请负责人知悉。")
    O.append("")
    O.append("五、声明")
    O.append("本意见为预审草稿，不构成准入批准，未签发任何通行证；以上结论均可经所引编号回溯至门户材料。")
    O.append("")
    O.append("六、证据引用（编号@SHA256）")
    for rid in sorted(refs):
        O.append(f"- {refs[rid]}（{recs[rid]['record_url']}）")
    opinion = "\n".join(O)
    (OUT / "opinion.md").write_text(opinion + "\n", encoding="utf-8")
    atomic_json(OUT / "draft_payload.json", {
        "key": "precheck-2026-11-16-30",
        "title": "维保入场资料预审意见（2026-11-16 至 11-30）",
        "body": opinion,
        "refs": [refs[r] for r in sorted(refs)]})
    print("ledger.md / opinion.md / draft_payload.json 已生成")


if __name__ == "__main__":
    main()
