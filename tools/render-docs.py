"""Render the maintained README into the local HTML reference."""
import argparse
from pathlib import Path
import markdown

parser = argparse.ArgumentParser()
parser.add_argument('--output', required=True)
args = parser.parse_args()
source = Path(__file__).resolve().parents[1] / 'README.md'
body = markdown.markdown(source.read_text(), extensions=['tables', 'fenced_code', 'toc'])
html = '''<!doctype html><html lang="pt-BR"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>FliperOS — documentação técnica</title>
<style>
body{max-width:1000px;margin:40px auto;padding:0 24px;background:#111820;color:#e2e9ef;font:17px/1.65 system-ui,sans-serif}
h1,h2{line-height:1.25;color:#8fd5bb}h2{margin-top:2.5em}a{color:#8ccfff}
pre{overflow:auto;background:#202b36;padding:20px;border-radius:6px}code{font-size:.9em}
table{border-collapse:collapse;width:100%;font-size:.92em}th,td{border-bottom:1px solid #405060;text-align:left;padding:12px}
strong{color:#fff}li{margin:.5em 0}footer{margin:60px 0 20px;color:#9cabb8}
</style><main>''' + body + '</main><footer>Gerado de README.md. Consulte AUDITORIA.md para os resultados dos testes.</footer></html>'
Path(args.output).write_text(html)
