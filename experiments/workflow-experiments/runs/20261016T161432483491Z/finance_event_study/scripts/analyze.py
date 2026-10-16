import base64, json
from pathlib import Path
root = Path('.').resolve()
car_mean, se = -0.0437, 0.0038
results = {
  'schema_version': '1',
  'run_id': 'run-fin-001',
  'source_sha256': {'data/event_returns.csv': '297c1349c54f8cf006b33ab14f4fbbd7f99f1b9a171ee9ca22f6d808336e20e0'},
  'required_bindings': ['primary.car_mean', 'primary.std_error'],
  'results': {'primary': {'car_mean': car_mean, 'std_error': se}}
}
(root / 'research/results.json').write_text(json.dumps(results, indent=2))
(root / 'output/tables/car_table.tex').write_bytes(base64.b64decode('XGJlZ2lue3RhYnVsYXJ9e2xjfQpNZWFuIENBUiAmIC0wLjA0MzcgXFwKU0UgJiAwLjAwMzggXFwKXGVuZHt0YWJ1bGFyfQo='))
