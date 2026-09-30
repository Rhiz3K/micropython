# Soukromý přehled měřicích profilů

Stav: **FAIL**. Žádné nové měření ani ovládání zařízení.

Tabulka uvádí pouze platné modelové hodnoty; hranaté závorky jsou min/max mezi třemi cykly. Chybové/částečné integrály jsou pouze v diagnostických sloupcích JSON/CSV.

| Profil | Stav | Délky oken [s] | Proud spánku [mA] | Napětí spánku [V] | Energie celého cyklu [J] |
|---|---|---|---|---|---|
| A | PASS | 220/220/220 | 15.9677 [15.957; 15.9752] | 5.0689 [5.06885; 5.069] | 24.5375 [24.5184; 24.5502] |
| B-LS | FAIL | — | — | — | — |
| C-never | PASS | 220/220/220 | 0.372855 [0.372727; 0.373012] | 5.08068 [5.0806; 5.08075] | 0.828783 [0.826662; 0.831176] |
| C-STA | PASS | 220/220/220 | 0.371704 [0.371214; 0.372276] | 5.08078 [5.08074; 5.08083] | 1.06937 [1.06245; 1.07608] |
| C+helper-STA | PASS | 220/220/220 | 0.372295 [0.371573; 0.372914] | 5.08098 [5.08089; 5.08106] | 1.08054 [1.07823; 1.08478] |
| B-upstream-vanilla | FAIL | — | — | — | — |
| B-upstream-usbfix | FAIL | — | — | — | — |

Metodika a omezení:

- Selection is fixed: A from cmp300v2; two B suite failures from cmp300v2/cont2; startup-only cont1 separately; C profiles03..05 from cmp300deep; reference06 from cmp300refvanilla and reference07 from cmp300refusbq.
- Unclosed results expose RUNNING/NOT_RUN/INCOMPLETE only. No active meter, analysis or raw data is read.
- The unchanged pinned base aggregator supplies all cycle values, equal-cycle means and min/max ranges. No pooling across attempts or normalization of actual durations.
- Valid energy still requires profile/suite/capture/analysis PASS, linked JSON hashes, complete cycle/window coverage and exact declared conditions. Failed/degraded/startup-only B has null valid current/energy.
- Only comparison copies use the digest of the exact original 18 source hashes. Every complete metadata source map must equal its exact pinned 18/35/45/58/70 manifest; extra keys and values must be explicitly present there. Added reviewed wrappers/proofs select profiles and validate prerequisites. The sibling70 reference wrappers also remove automatic firmware switches and require a fresh verified fixture; original V2 run_profile, timing gates, collector and analyzer remain unchanged. Original maps and full digests are retained and never rewritten.
- Projection changes only the provenance digest passed to comparison copies. Radio group, fixture hash, same-artifact BIN hash, duration/tolerances, direct timing and exact ACK+60..280s boundaries retain all original comparison gates.
- All 18 common hashes must agree; additional hashes must exactly match the chosen pinned manifest. Both reference70 manifests are independent children of the same immutable58 parent. No unknown source, changed parent/common hash or generalized provenance exception is accepted.
- Whole-cycle energy remains a host-receipt frame-mean U*I trapezoid estimate, READY-to-READY; nominal100Hz sensitivity stays diagnostic. Min/max are between-cycle ranges, not uncertainty bounds.
- USB input measures the complete fixture. Zeros/spikes are retained; no no-load subtraction or core-only interpretation. Raw integrity is inherited from the closed pinned analyzer, not reverified here.
- Overall status remains FAIL when B failed, even if later profiles pass. Reference failures also retain null valid values and unavailable percentage comparisons.
- remaining_sequence_result and candidate_restored_reported refer only to the original cmp300deep sequence, which can remain FAIL/false. Separate reference sequence results do not replace it. Final application/RTC restoration requires a separate root-owned proof and is not asserted here.

B-LS: počet funkčních selhání doložených načtenými výsledky: 2/2; úplná provenience obou: True. Pokusy jsou zvlášť v JSON a excluded-B-attempts.csv. Cont1: functional NOT_RUN. B nemá platný proud ani energii a není součástí procentních úspor.

Veřejný export zachovává celkový FAIL, dva funkční FAIL B-LS i oba referenční FAIL. Procenta se vztahují pouze k jednotlivým doloženým párům. Návrat firmwaru kandidáta není obnovením původních uživatelských souborů.
