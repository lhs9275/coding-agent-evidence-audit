"""Render the public Markdown report using installed system fonts."""
from pathlib import Path
import sys
import markdown
from weasyprint import HTML

root = Path(sys.argv[1]).resolve()
report = root / 'TECHNICAL_REPORT.ko.md'
body = markdown.markdown(report.read_text(), extensions=['tables', 'fenced_code'])
style = '''
@page { size: A4; margin: 19mm 19mm 20mm;
  @bottom-center { content: "Paper A · Technical Report · " counter(page); font-size: 8pt; color: #666; }
}
body { font-family: "Noto Sans CJK KR", sans-serif; font-size: 10pt; line-height: 1.65; color: #202020; }
h1 { font-size: 22pt; line-height: 1.4; margin-bottom: 8mm; }
h2 { font-size: 14pt; margin-top: 7mm; border-bottom: 1px solid #ccc; padding-bottom: 2mm; }
h3 { font-size: 11pt; margin-top: 5mm; }
h1,h2,h3 { break-after: avoid; }
p { orphans: 3; widows: 3; }
a { color: #174c75; text-decoration: none; overflow-wrap: anywhere; }
code { font-family: "DejaVu Sans Mono", "Noto Sans CJK KR", monospace; font-size: 8pt; overflow-wrap: anywhere; }
pre { white-space: pre-wrap; background: #f4f5f6; padding: 3mm; font-size: 8pt; }
table { border-collapse: collapse; width: 100%; font-size: 8.5pt; margin: 4mm 0; }
th,td { border-bottom: 1px solid #ddd; padding: 2mm; text-align: left; vertical-align: top; overflow-wrap: anywhere; }
th { background: #eef1f4; }
tr { break-inside: avoid; }
blockquote { border-left: 3px solid #bbb; padding-left: 4mm; color: #444; margin-left: 0; }
'''
html = '<!doctype html><html lang="ko"><meta charset="utf-8"><title>Paper A Technical Report</title><style>' + style + '</style><body>' + body + '</body></html>'
(root / 'TECHNICAL_REPORT.ko.html').write_text(html)
HTML(string=html, base_url='https://github.com/lhs9275/coding-agent-evidence-audit/blob/main/').write_pdf(root / 'TECHNICAL_REPORT.ko.pdf')
print('Rendered technical report')
