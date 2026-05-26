"""
本日の N225LLMAdvisor/analyses/YYYY-MM-DD.md を HTML 化して既定ブラウザで開く。

呼出元:
- start_claude_analyze.bat (/analyze 完了後の最終ステップ)
- 手動: `python preview_analysis.py [YYYY-MM-DD]`
  - 引数なしなら本日、なければ最新ファイル
"""

from __future__ import annotations

import datetime as dt
import sys
import tempfile
import webbrowser
from pathlib import Path

import markdown

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent  # N225LLMAdvisor
ANALYSES_DIR = ROOT / "analyses"
SCREENSHOTS_DIR = (ROOT.parent / "N225McpServer" / "screenshots").resolve()

CSS = """
<style>
  body {
    font-family: -apple-system, "Segoe UI", "Hiragino Kaku Gothic ProN", Meiryo, sans-serif;
    max-width: 1020px;
    margin: 30px auto;
    padding: 0 24px 80px;
    color: #1f2328;
    line-height: 1.65;
    background: #ffffff;
  }
  h1 { font-size: 28px; border-bottom: 2px solid #1f6feb; padding-bottom: 8px; }
  h2 { font-size: 22px; color: #0969da; margin-top: 36px; border-bottom: 1px solid #d0d7de; padding-bottom: 6px; }
  h3 { font-size: 18px; margin-top: 28px; }
  h4 { font-size: 15px; color: #57606a; }
  table { border-collapse: collapse; width: 100%; margin: 12px 0; font-size: 14px; }
  th, td { border: 1px solid #d0d7de; padding: 7px 10px; vertical-align: top; }
  th { background: #f6f8fa; text-align: left; }
  tr:nth-child(even) td { background: #fafbfc; }
  code, pre { background: #f6f8fa; border-radius: 6px; font-family: SFMono-Regular, Consolas, monospace; }
  pre { padding: 14px; overflow-x: auto; font-size: 13px; line-height: 1.5; }
  code { padding: 2px 6px; font-size: 90%; }
  blockquote { border-left: 4px solid #d0d7de; color: #57606a; padding: 4px 16px; margin: 12px 0; }
  hr { border: none; border-top: 1px solid #d0d7de; margin: 28px 0; }
  img { max-width: 100%; border: 1px solid #d0d7de; border-radius: 6px; }
  a { color: #0969da; }
  ul, ol { margin: 8px 0; padding-left: 28px; }
  li { margin: 3px 0; }
  .meta-bar {
    background: #ddf4ff;
    border: 1px solid #54aeff;
    border-radius: 8px;
    padding: 10px 16px;
    margin: 18px 0 28px;
    font-size: 13px;
    color: #0550ae;
  }
</style>
"""


def find_target(arg: str | None) -> Path:
    if arg:
        candidate = ANALYSES_DIR / f"{arg}.md"
        if candidate.exists():
            return candidate
        raise FileNotFoundError(f"指定された分析ファイルが見つかりません: {candidate}")

    today = dt.date.today().isoformat()
    target = ANALYSES_DIR / f"{today}.md"
    if target.exists():
        return target

    files = sorted(ANALYSES_DIR.glob("????-??-??.md"))
    if not files:
        raise FileNotFoundError(f"分析ファイルが見つかりません: {ANALYSES_DIR}")
    return files[-1]


def rewrite_screenshot_paths(md_text: str, md_path: Path) -> str:
    """相対パスの screenshots を file:/// 絶対 URI に書き換えてブラウザで表示可能にする。"""
    rel_prefix = "../../N225McpServer/screenshots/"
    abs_prefix = SCREENSHOTS_DIR.as_uri() + "/"
    return md_text.replace(rel_prefix, abs_prefix)


def main() -> int:
    arg = sys.argv[1] if len(sys.argv) > 1 else None
    md_path = find_target(arg)
    print(f"Preview source: {md_path}")

    md_text = md_path.read_text(encoding="utf-8")
    md_text = rewrite_screenshot_paths(md_text, md_path)

    html_body = markdown.markdown(
        md_text,
        extensions=["tables", "fenced_code", "toc", "sane_lists"],
    )

    meta_bar = (
        f'<div class="meta-bar">📄 <strong>{md_path.name}</strong> '
        f'&nbsp;|&nbsp; 生成: {dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")} '
        f'&nbsp;|&nbsp; ソース: <code>{md_path}</code></div>'
    )

    html = (
        '<!DOCTYPE html>\n'
        '<html lang="ja"><head><meta charset="utf-8">'
        f'<title>{md_path.stem} - N225 分析</title>'
        f'{CSS}'
        '</head><body>'
        f'{meta_bar}'
        f'{html_body}'
        '</body></html>'
    )

    tmp = Path(tempfile.gettempdir()) / f"n225_analysis_{md_path.stem}.html"
    tmp.write_text(html, encoding="utf-8")
    print(f"HTML: {tmp}")

    webbrowser.open(tmp.as_uri())
    return 0


if __name__ == "__main__":
    sys.exit(main())
