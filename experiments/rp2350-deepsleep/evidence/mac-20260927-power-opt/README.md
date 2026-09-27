# Power optimization evidence, 2026-09-27

These measurements cover USB input to Pico 2 W with the attached Waveshare Pico-ePaper-2.9 B/W V2. Wireless was deinitialized and the display sleep command was sent before each sleep. The display bus configuration differs between labeled runs.

- Analysis files cover every completed analyzed run at export time.
- Host results and events replace the Pico UID with `test-board-2`. Backup register contents are omitted; only the test boot counter remains.
- CSV traces include all recording samples grouped into one-second bins relative to host RUN receipt, including transitions and partial edge bins. Drain samples are excluded. No zero or outlier filter is used.
- PNG plots show seconds 5–295 of each 300 s run. They omit entry and wake transitions, which remain in the CSV traces. Bands on individual plots show each bin's minimum and maximum.
- Four ordered measurements in one HID frame share its actual host receipt timestamp; device sample times are unknown.
- No no-load offset is subtracted and cycle energy is not integrated. A late window is not a formal claim of steady state.
- Raw HID frames and full-resolution samples remain private. Their SHA-256 values in `private_source_sha256` identify private inputs, not the sanitized exported files. `public_file_sha256` identifies the files in this directory, excluding the manifest itself.
- Original applications, credentials, flash backups and inventories are not exported. Restoration is included only when a verified `restored.json` already exists; consult the manifest status.
- Display A/B records preserve their automatic `NOT_VERIFIED` visual status. They establish refresh/communication and exact linkage to the public-helper 300 s wake. A separate normalized user visual confirmation is included only if it already exists; no user prose is copied and no visual PASS is inferred from automatic checks.
