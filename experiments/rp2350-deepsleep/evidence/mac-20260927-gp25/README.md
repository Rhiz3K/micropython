# GP25 power comparison evidence, 2026-09-27

These measurements cover USB input to Pico 2 W with the attached Waveshare Pico-ePaper-2.9 B/W V2. Wireless was deinitialized and the display sleep command was sent before each sleep. Display signals were released by the tested panel helper in every run; GP25 was driven high or low as identified by the label. GP29 register snapshots describe its actual state without attributing a measured current to an individual component.

- Analysis files cover all five planned runs: high/low/high 45 s screening and high/low 300 s comparisons.
- Host results and events replace the Pico UID with `test-board-2`. Backup register contents are omitted; only the test boot counter remains.
- CSV traces include all recording samples grouped into one-second bins relative to host RUN receipt, including transitions and partial edge bins. Drain samples are excluded. No zero or outlier filter is used.
- PNG plots show seconds 5–295 of each 300 s run. They omit entry and wake transitions, which remain in the CSV traces. Bands on individual plots show each bin's minimum and maximum.
- Four ordered measurements in one HID frame share its actual host receipt timestamp; device sample times are unknown.
- No no-load offset is subtracted and cycle energy is not integrated. A late window is not a formal claim of steady state.
- Raw HID frames and full-resolution samples remain private. Their SHA-256 values in `private_source_sha256` identify private inputs, not the sanitized exported files. `public_file_sha256` identifies the files in this directory, excluding the manifest itself.
- Original applications, credentials, flash backups and inventories are not exported. The complete export requires verified restoration of the 29 original files and includes a safe restoration summary.
- Display A/B records preserve their automatic `NOT_VERIFIED` visual status. They establish refresh/communication and exact linkage to the low-GP25 public-helper 300 s wake. A separate normalized visual confirmation may record an explicit user reply or assistant review of a user-supplied photograph. Photo review records its method and SHA-256; the photograph itself and user prose are not exported. No visual PASS is inferred from automatic checks.
- The required radio reinitialization check activates the driver only: it requests no scan or association and proves no network connection. Actual GP23/WL_REG_ON and GP25 pad outputs pass LOW → HIGH → LOW; the final helper leaves STA/AP inactive. All backup words and the installed file inventory are unchanged.
