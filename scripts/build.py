"""Package the preserved static frontend for Vercel's public CDN directory."""
import ast
import json
import shutil
from pathlib import Path

root = Path(__file__).resolve().parents[1]
for path in (root/'backend').rglob('*.py'):
    ast.parse(path.read_text(encoding='utf-8'))
for name in ['index.html', 'app.js', 'api.js', 'model.js', 'styles.css', 'favicon.svg']:
    source = root/'dist'/name
    if not source.is_file():
        raise SystemExit(f'Missing frontend asset: {name}')
    destination = root/'public'/name
    destination.parent.mkdir(exist_ok=True)
    shutil.copyfile(source, destination)
json.loads((root/'vercel.json').read_text())
print('Production assets built to public/; backend syntax validated. No database migration at build time.')
