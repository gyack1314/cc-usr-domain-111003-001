"""把预审意见登记为门户预审草稿：浏览器表单提交，随后回读核对。

幂等：相同内容重送返回已有版本；内容有修订时先读取当前版本号再提交。
用法: python3 -I scripts/save_draft.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, "/workspace")
from playwright.sync_api import sync_playwright  # noqa: E402
from workbench.evidence import Journal, atomic_json  # noqa: E402

WS = Path("/workspace")
OUT = WS / "output"
PORTAL = "http://127.0.0.1:8765"


def main():
    payload = json.loads((OUT / "draft_payload.json").read_text(encoding="utf-8"))
    journal = Journal(WS / "state" / "journal.sqlite3")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        page = browser.new_page(viewport={"width": 1280, "height": 720})

        # 已存在则读取当前版本，否则走新建页
        resp = page.goto(f"{PORTAL}/draft/{payload['key']}", wait_until="domcontentloaded")
        if resp.status == 404:
            page.goto(f"{PORTAL}/draft/new", wait_until="domcontentloaded")
        version = page.locator('input[name="version"]').input_value()
        key_input = page.locator('input[name="key"]')
        if key_input.is_editable():
            key_input.fill(payload["key"])
        page.fill('input[name="title"]', payload["title"])
        page.fill('textarea[name="body"]', payload["body"])
        page.fill('textarea[name="refs"]', "\n".join(payload["refs"]))
        page.click("button")
        page.wait_for_load_state("domcontentloaded")
        assert f"/draft/{payload['key']}" in page.url, f"保存后未回到草稿页: {page.url}"

        # 回读核对：状态、正文、引用逐项比对
        status = page.locator('[data-testid="draft-status"]').inner_text().strip()
        body_back = page.locator('textarea[name="body"]').input_value()
        refs_back = page.locator('textarea[name="refs"]').input_value().splitlines()
        title_back = page.locator('input[name="title"]').input_value()
        version_back = page.locator('input[name="version"]').input_value()
        checks = {
            "status": status,
            "title_match": title_back == payload["title"],
            "body_match": body_back == payload["body"],
            "refs_match": sorted(r.strip() for r in refs_back if r.strip()) == sorted(payload["refs"]),
            "version": version_back,
            "url": page.url,
        }
        assert status == "待人工审批", f"草稿状态异常: {status}"
        assert checks["title_match"] and checks["body_match"] and checks["refs_match"], f"回读不一致: {checks}"

        archive = OUT / "evidence" / "draft"
        archive.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(archive / "page.png"), full_page=True)
        atomic_json(archive / "page.json", {"url": page.url, "title": page.title(),
                                            "text": page.locator("main").inner_text()})
        browser.close()

    atomic_json(OUT / "verification" / "draft_readback.json", checks)
    journal.append(f"draft-{payload['key']}", {
        "source": f"{PORTAL}/draft/{payload['key']}", "version": version_back,
        "status": status, "refs": payload["refs"],
        "note": "预审草稿已登记并回读核对；不构成审批"})
    print(json.dumps(checks, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
