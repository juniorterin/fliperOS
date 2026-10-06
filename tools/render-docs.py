"""Render the documentation (README + docs/wiki) into the local HTML reference.

The README is the short overview and the wiki pages carry the detail; the HTML
is everything in one file, for reading without network. The page order is the
one of the wiki sidebar.
"""
import argparse
from pathlib import Path
import re

import markdown

parser = argparse.ArgumentParser()
parser.add_argument('--output', required=True)
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
wiki = root / 'docs' / 'wiki'
WIKI_URL = 'https://github.com/juniorterin/fliperOS/wiki'


def render(text):
    # Links to wiki pages become links inside this document.
    text = re.sub(r'\]\(%s/([A-Za-z0-9_-]+)\)' % re.escape(WIKI_URL), r'](#\1)', text)
    text = text.replace('](%s)' % WIKI_URL, '](#Install)')
    text = re.sub(r'\]\(([A-Za-z0-9_-]+)\.md(?:#[^)]*)?\)',
                  lambda m: '](#%s)' % m.group(1) if (wiki / (m.group(1) + '.md')).exists() else m.group(0), text)
    return markdown.markdown(text, extensions=['tables', 'fenced_code', 'toc'])


pages = []
for title, name in re.findall(r'\[([^\]]+)\]\(([A-Za-z0-9_-]+)\.md\)', (wiki / '_Sidebar.md').read_text(encoding='utf-8')):
    if name != 'Home' and name not in [n for _, n in pages]:
        pages.append((title, name))
body = render((root / 'README.md').read_text(encoding='utf-8'))
for title, name in pages:
    body += '\n<h1 id="%s">%s</h1>\n' % (name, title) + render((wiki / (name + '.md')).read_text(encoding='utf-8'))
html = '''<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>FliperOS — technical documentation</title>
<style>
body{max-width:1000px;margin:40px auto;padding:0 24px;background:#111820;color:#e2e9ef;font:17px/1.65 system-ui,sans-serif}
h1,h2,h3{line-height:1.25;color:#8fd5bb}h1{margin-top:3em;border-top:1px solid #405060;padding-top:1em}h2{margin-top:2.5em}a{color:#8ccfff}
pre{overflow:auto;background:#202b36;padding:20px;border-radius:6px}code{font-size:.9em}
table{border-collapse:collapse;width:100%;font-size:.92em}th,td{border-bottom:1px solid #405060;text-align:left;padding:12px}
strong{color:#fff}li{margin:.5em 0}footer{margin:60px 0 20px;color:#9cabb8}
</style><main>''' + body + '</main><footer>Generated from README.md and docs/wiki by tools/render-docs.py.</footer></html>'
Path(args.output).write_text(html, encoding='utf-8')
