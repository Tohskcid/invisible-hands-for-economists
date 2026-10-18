"""Freeze BLS public API responses; refuse to replace a prior snapshot."""

import hashlib
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
API = "https://api.bls.gov/publicAPI/v2/timeseries/data/"
SERIES = ["LNS14000000", "JTS000000000000000JOR"]
WINDOWS = [(2001, 2010), (2011, 2020), (2021, 2024)]


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    if any(RAW.iterdir()):
        raise SystemExit("raw snapshot already exists; refusing to overwrite it")
    log = []
    for start, end in WINDOWS:
        payload = json.dumps({"seriesid": SERIES, "startyear": str(start), "endyear": str(end)}).encode()
        request = urllib.request.Request(API, data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(request, timeout=30) as response:
            body = response.read()
            if response.status != 200:
                raise RuntimeError(f"BLS HTTP {response.status}")
        parsed = json.loads(body)
        if parsed.get("status") != "REQUEST_SUCCEEDED":
            raise RuntimeError(f"BLS request failed: {parsed.get('message')}")
        found = {item["seriesID"] for item in parsed["Results"]["series"]}
        if found != set(SERIES):
            raise RuntimeError(f"wrong BLS series: {found}")
        path = RAW / f"bls-{start}-{end}.json"
        path.write_bytes(body)
        log.append({"path": path.relative_to(ROOT).as_posix(), "request": json.loads(payload),
                    "retrieved_at": datetime.now(timezone.utc).isoformat(),
                    "sha256": hashlib.sha256(body).hexdigest(), "bytes": len(body)})
    (ROOT / "data" / "acquisition-log.json").write_text(json.dumps({"endpoint": API, "downloads": log}, indent=2) + "\n")
    for path in RAW.iterdir():
        path.chmod(0o444)


if __name__ == "__main__":
    main()
