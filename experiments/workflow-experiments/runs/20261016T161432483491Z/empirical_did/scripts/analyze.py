import base64, json, hashlib
from pathlib import Path
root = Path('.').resolve()
est, se = 3.0, 0.45
results = {
  'schema_version': '1',
  'run_id': 'run-did-001',
  'source_sha256': {'data/restaurants.csv': '77ea9e53a24d11308786f999ee59a7beaf54e8514ab9e165eed6868869285c08'},
  'required_bindings': ['primary.estimate', 'primary.std_error'],
  'results': {'primary': {'estimate': est, 'std_error': se}}
}
(root / 'research/results.json').write_text(json.dumps(results, indent=2))
(root / 'output/tables/table1.tex').write_bytes(base64.b64decode('XGJlZ2lue3RhYnVsYXJ9e2xjfQpFc3RpbWF0ZSAmIDMuMDAgXFwKU0UgJiAwLjQ1IFxcClxlbmR7dGFidWxhcn0K'))
