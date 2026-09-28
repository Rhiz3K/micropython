# Extended RP2350 evidence, 2026-09-27

This is an allowlisted, sanitized export. Board UID is replaced by test-board-2;
network addresses are redacted. Original user scratch contents are omitted;
only verified private test-guard counters and retention/check booleans remain.
Configurations, credentials, manifests, original apps/inventories, flash images,
raw meter records, and private asynchronous traces are not exported.

One-second CSV rows use all recording-phase samples, including zeroes/outliers
and partial edge seconds; drain samples are excluded. Time is relative to the
host-received RUN event. Four samples can share a frame receipt timestamp.
No no-load offset is subtracted and full application-cycle energy is not measured.
The power analyses retain hashes of their private raw sources; these are not
links to exported raw files. Build result references identify private records.

Suite failures retain their FAIL/ERROR status. Missing planned files appear in
manifest.json and are not PASS results. Regression PASS requires all six script
results, runner exit zero, and the final ordinary-reset result. Restoration is
reported separately; absent evidence is never a claim of successful restoration.
Per-case source hashes describe the files actually used during each run and
are authoritative if host.py changed between cases. They may precede later
formatting-only changes. No whole-matrix PASS is synthesized by this exporter.

Additional reviewed evidence includes three radio-only watchdog preflights,
the final firmware rollback and expired-watchdog cleanup, source equivalence
checks and the exact hardware-tested device.py as a non-executable text file.
The final source uses formatting-equivalent device.py; its AST was compared.
Restoration refers to the previous firmware, not the combined candidate.
