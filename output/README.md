# 预审产出说明（2026-11-16 至 2026-11-30 维保入场资料）

## 结论文件
- `ledger.md` — 审查台账：按队伍 × 作业类别展开，每条结论含门户地址、材料编号、内容摘要（SHA-256）、适用日期与缺口原因。
- `opinion.md` — 给准入负责人的意见：可确定范围 / 必须补证 / 需裁决事项，已登记为门户预审草稿
  `precheck-2026-11-16-30`（状态：待人工审批，见 http://127.0.0.1:8765/drafts ）。
- `analysis.json` — 机器可读的逐日判定（主体覆盖日、人员覆盖日、缺口日、授权链路径）。
- `draft_payload.json` — 登记草稿时提交的正文与引用。

## 证据（均以浏览器可见页面与实际下载件为准）
- `evidence/pages/<编号>/` — 各记录详情页截图与正文存档；`evidence/catalog/` 目录分页存档。
- `evidence/attachments/<编号>/<编号>.json` — 实际下载的原始材料附件（判定依据）。
- `evidence/documents/<编号>/` — 下载的文书副本（与附件摘要是不同对象，未混用）。
- `evidence/index.json` — 每份资料的门户地址、引用（编号@SHA256）、附件/文书指纹。
- `evidence/draft/` — 草稿回读页存档；`evidence/drafts-before/` 登记前草稿列表基线。

## 计算留痕
- `verification/tool_inputs|tool_outputs/` — 区间交集、范围交集、图可达性的领域工具输入与结果。
- `verification/draft_readback.json` — 草稿回读核对结果。
- `../state/journal.sqlite3` — 进度账（取证、分析、草稿登记；修订以新键登记并注明前序，可续用不重复）。
- `../state/materials-manifest.json` — 本地材料（排班、规程、主体、现场）指纹。

## 复查方法
```bash
python -m workbench.portal --port 8765 --state state/portal   # 启动门户（另一终端）
python3 -I scripts/verify_all.py                              # 全量重核：指纹/引用/工具重放/草稿状态
```
单项重放示例：`python -m workbench.tools call intersection output/verification/tool_inputs/T2-auth-A1-有效段.json`
脚本位于 `scripts/`（collect_portal 取证、analyze 判定、render_outputs 生成台账与意见、save_draft 登记并回读、verify_all 复查），
重跑均为幂等：证据覆盖写同名文件、进度账同键同内容不重复、草稿同内容不增版本。
