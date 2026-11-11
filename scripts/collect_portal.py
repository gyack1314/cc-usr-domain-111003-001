"""门户取证：用 Playwright 浏览目录与详情页，下载附件与文书副本，计算指纹。

只从浏览器可见页面与实际下载的字节取证，不读取服务端种子文件。
用法: python3 -I scripts/collect_portal.py <门户URL> <证据目录> <进度账路径>
"""
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, "/workspace")  # 显式引入项目工作台（-I 模式下不自动加路径）

from playwright.sync_api import sync_playwright

from workbench.evidence import Journal, atomic_json, digest


def sha256_file(path):
    return digest(Path(path).read_bytes())


def main():
    url, evidence_dir, journal_path = sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3])
    journal = Journal(journal_path)
    index = {"portal": url, "records": {}, "catalog_pages": [], "drafts_page": None}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        page = browser.new_page(viewport={"width": 1280, "height": 720}, accept_downloads=True)

        def archive_page(target, outdir):
            outdir.mkdir(parents=True, exist_ok=True)
            page.goto(target, wait_until="domcontentloaded")
            page.screenshot(path=str(outdir / "page.png"), full_page=True)
            text = page.locator("main").inner_text()
            atomic_json(outdir / "page.json", {"url": page.url, "title": page.title(), "text": text})
            return text

        # 1. 目录页（含分页），从页面表格中取得实际可见的资料编号
        page.goto(url + "/", wait_until="domcontentloaded")
        last = page.locator('nav[aria-label="资料分页"] a').last.inner_text()
        pages = int("".join(ch for ch in last if ch.isdigit()))
        record_ids = []
        for n in range(1, pages + 1):
            cat_dir = evidence_dir / "catalog" / f"page{n}"
            archive_page(f"{url}/?page={n}", cat_dir)
            index["catalog_pages"].append(str(cat_dir.relative_to(evidence_dir)))
            ids = page.locator("tr[data-record-id]").evaluate_all(
                "rows => rows.map(r => r.getAttribute('data-record-id'))"
            )
            record_ids.extend(ids)

        # 2. 每条记录：详情页存档 + 下载附件与文书
        for rid in record_ids:
            rec_dir = evidence_dir / "pages" / rid
            text = archive_page(f"{url}/record/{rid}", rec_dir)
            page.goto(f"{url}/record/{rid}", wait_until="domcontentloaded")
            shown_digest = page.locator('[data-testid="digest"]').inner_text().strip()
            reference = page.locator('[data-testid="reference"]').inner_text().strip()

            att_dir = evidence_dir / "attachments" / rid
            att_dir.mkdir(parents=True, exist_ok=True)
            with page.expect_download() as dl:
                page.click("text=下载原始材料")
            att_path = att_dir / f"{rid}.json"
            dl.value.save_as(str(att_path))

            doc_dir = evidence_dir / "documents" / rid
            doc_dir.mkdir(parents=True, exist_ok=True)
            with page.expect_download() as dl2:
                page.click("text=下载文书或扫描副本")
            doc_path = doc_dir / dl2.value.suggested_filename
            dl2.value.save_as(str(doc_path))

            att_sha = sha256_file(att_path)
            doc_sha = sha256_file(doc_path)
            fields = json.loads(att_path.read_text(encoding="utf-8"))["fields"]
            # 页面所示内容摘要必须与实际下载附件的 SHA-256 一致
            assert att_sha == shown_digest, f"{rid}: 附件指纹与页面摘要不符"
            assert reference == f"{rid}@{att_sha}", f"{rid}: 页面引用格式异常"
            index["records"][rid] = {
                "record_url": f"{url}/record/{rid}",
                "attachment_url": f"{url}/attachment/{rid}",
                "document_url": f"{url}/document/{rid}",
                "reference": reference,
                "attachment_sha256": att_sha,
                "document_file": doc_path.name,
                "document_sha256": doc_sha,
                "fields": fields,
                "page_archive": str(rec_dir.relative_to(evidence_dir)),
            }
            journal.append(
                f"collect-{rid}",
                {"source": f"{url}/record/{rid}", "reference": reference,
                 "attachment_sha256": att_sha, "document_sha256": doc_sha},
            )

        # 3. 草稿列表页存档（登记前基线）
        drafts_dir = evidence_dir / "drafts-before"
        archive_page(url + "/drafts", drafts_dir)
        index["drafts_page"] = str(drafts_dir.relative_to(evidence_dir))
        browser.close()

    atomic_json(evidence_dir / "index.json", index)
    journal.append("collect-complete", {"records": sorted(index["records"]), "count": len(index["records"])})
    print(json.dumps({"records": sorted(index["records"]), "count": len(index["records"])}, ensure_ascii=False))


if __name__ == "__main__":
    main()
