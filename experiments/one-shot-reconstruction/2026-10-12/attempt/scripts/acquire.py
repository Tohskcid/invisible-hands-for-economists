"""Acquire only public raw records, documentation, and survey instruments."""
from pathlib import Path
import hashlib, json, urllib.request, zipfile, datetime

ROOT = Path(__file__).resolve().parents[1]
URL = 'https://davidcard.berkeley.edu/data_sets/njmin.zip'
ALLOWED = ['public.dat', 'codebook', 'read.me', 'survey1.nj', 'survey2.nj']

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    raw = ROOT / 'data/raw'; raw.mkdir(parents=True, exist_ok=True)
    (raw / 'archive').mkdir(exist_ok=True)
    archive = raw / 'archive/njmin.zip'
    if not archive.exists():
        with urllib.request.urlopen(URL, timeout=30) as r:
            archive.write_bytes(r.read())
    with zipfile.ZipFile(archive) as z:
        assert all(n in z.namelist() for n in ALLOWED)
        for n in ALLOWED:
            target = raw / n
            if not target.exists(): target.write_bytes(z.read(n))
    # The archive's check.sas is deliberately never extracted or inspected.
    checksums = {n: digest(raw/n) for n in ['archive/njmin.zip'] + ALLOWED}
    manifest = ROOT / 'data/raw/checksums.sha256'
    if manifest.exists():
        expected = dict(line.rstrip().split('  ')[::-1] for line in manifest.read_text().splitlines())
        assert expected == checksums, 'Raw input checksum changed'
    else:
        manifest.write_text(''.join(f'{v}  {k}\n' for k,v in checksums.items()))
    return checksums

if __name__ == '__main__': main()
