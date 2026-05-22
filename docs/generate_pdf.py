"""HTML 매뉴얼을 PDF로 변환 — Edge 헤드리스 브라우저 사용"""
import subprocess, os, sys, time, shutil, tempfile

EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
BROWSER = EDGE if os.path.exists(EDGE) else CHROME

DOCS_DIR = os.path.dirname(os.path.abspath(__file__))

FILES = [
    ("user_manual.html",  "user_manual_v1.3.pdf"),
    ("admin_manual.html", "admin_manual_v1.3.pdf"),
]

def html_to_pdf(html_path, pdf_path):
    abs_html = os.path.abspath(html_path)
    abs_pdf  = os.path.abspath(pdf_path)

    # 브라우저는 --print-to-pdf 경로를 절대 경로로 지정해야 함
    with tempfile.TemporaryDirectory() as tmp:
        cmd = [
            BROWSER,
            "--headless=new",
            "--disable-gpu",
            "--no-sandbox",
            "--disable-extensions",
            "--disable-software-rasterizer",
            f"--print-to-pdf={abs_pdf}",
            "--print-to-pdf-no-header",
            f"--user-data-dir={tmp}",
            f"file:///{abs_html.replace(os.sep, '/')}",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

    if os.path.exists(abs_pdf) and os.path.getsize(abs_pdf) > 0:
        size_kb = os.path.getsize(abs_pdf) // 1024
        print(f"  OK  {os.path.basename(pdf_path)}  ({size_kb} KB)")
        return True
    else:
        print(f"  FAIL {os.path.basename(pdf_path)}")
        if result.stderr:
            print("  stderr:", result.stderr[:300])
        return False

def main():
    print(f"브라우저: {os.path.basename(BROWSER)}")
    print(f"출력 폴더: {DOCS_DIR}\n")

    ok = 0
    for html_name, pdf_name in FILES:
        html_path = os.path.join(DOCS_DIR, html_name)
        pdf_path  = os.path.join(DOCS_DIR, pdf_name)
        print(f"변환 중: {html_name} → {pdf_name}")
        if html_to_pdf(html_path, pdf_path):
            ok += 1

    print(f"\n완료: {ok}/{len(FILES)} 파일 생성")

if __name__ == "__main__":
    main()
