# BDSRC paper collection deployment

On 2026-11-22 (Asia/Taipei) the saved process exit code was 0, with 180/180 journal-year queries complete and 15,168 distinct DOI records (AER 5,532, Econometrica 3,118, JPE 2,650, QJE 1,747, REStud 2,121). The AER queries for 1990–1998 returned no records. These are coverage gaps. The 1994 AER calibration paper was sourced separately.

Deployed 2026-11-18 (Asia/Taipei). Credentials are not part of the deployment or repository.

- Release: `~/econ-paper-collector/releases/20261118-v1/`
- Collection: `~/econ-paper-collector/corpus/`
- Run receipts/logs: `~/econ-paper-collector/runs/20261118-1990-2025/`
- Initial job PID: `1919488` (historical receipt, not a permanent job identifier).
- Scope: AER, Econometrica, JPE, QJE, REStud; publication years 1990–2025, all subject areas.
- Limits: one process, 1-second delay after each page, bounded HTTP retries, at most five 1,000-record pages per journal/year, two-hour process deadline with 30-second kill grace.
- Uses the host's Python 3.10.12 and standard library; no packages installed and no GPU allocated.

The remote release hashes match the local files:

```
f523f6d5a19510db99fa011cecd1a43d302fc5a23fc2cf825eac5d5b3feb7306  collect_papers.py
db6dad5d80bc1ca0328b0cab5f31c0acfa035e18e516d03f3c3482ab136025d4  search_literature.py
```

All four collection tests passed on the host. A separately selected author-hosted article was downloaded to `~/econ-paper-collector/demo/`; its PDF SHA-256 matched the local source. This verifies actual PDF transfer, not full-text reading or identity validation.

## Inspect on the remote host

```bash
cat ~/econ-paper-collector/runs/20261118-1990-2025/pid
cat ~/econ-paper-collector/runs/20261118-1990-2025/stdout.log
cat ~/econ-paper-collector/runs/20261118-1990-2025/stderr.log
cat ~/econ-paper-collector/runs/20261118-1990-2025/exit-code
```

`exit-code` is written only after the batch ends; `0` means the invocation succeeded, `124` means its time budget expired. Check each catalog query's `complete` flag before declaring the date range finished. A completed query with zero records means this API returned no metadata, not that the journal published no papers. Historical coverage needs source reconciliation.

Resume after checking that no prior process is active:

```bash
python3 ~/econ-paper-collector/releases/20261118-v1/scripts/collect_papers.py \
  --out ~/econ-paper-collector/corpus discover \
  --from-year 1990 --to-year 2025 --pages 5 --rows 1000
```

The collector lock prevents simultaneous writers. Do not delete its checkpoint to restart. Remote cursor expiry still requires a separate query collection as described in the curation reference.

This batch collects metadata and candidate full-text links. It does not indiscriminately download every publisher link, establish journal access rights, or mark papers as read. Full texts remain a separate acquisition stage. The process runs under `nohup` and survives the initiating SSH session; no recurring service or scheduled automation was installed.
