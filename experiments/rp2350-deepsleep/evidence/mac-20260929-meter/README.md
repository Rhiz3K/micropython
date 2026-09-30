# Mac RP2350 evidence export

This archive preserves reported PASS, FAIL, DEGRADED and unfinished results. Export completion is not scientific PASS.

UID is aliased to test-board-2; unexpected identities retain distinct anonymous aliases. USB/HID serials and private paths are removed. Unrecognized console lines are omitted explicitly. Original app/config, backup words and flash images are not included.

Raw meter frames/samples/events remain private because of volume; their hashes and sizes are recorded. Raw hashes are skipped for captures lacking consistent final summary and finished health evidence from the pinned reader. Metadata, final summary and health are separately projected through explicit schema2 allowlists; active captures have control snapshots only. Published analysis is not independently reproducible from plots alone. Private raw evidence remains necessary for a full replay.

DEGRADED and coverage-failing energy integrals are diagnostics. Only globally PASS captures with all required windows PASS can be called complete cycle energy.

export-manifest.json hashes every payload file and records private source digests. SHA256SUMS additionally covers the manifest; it excludes itself. Source excerpts are review artifacts, not standalone replacements for the complete tools.
