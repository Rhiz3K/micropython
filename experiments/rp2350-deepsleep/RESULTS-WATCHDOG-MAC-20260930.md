# Watchdog: nové testy na Mac Picu 30. 9. 2026

**Oba požadované testy opravy watchdogu prošly na skutečném Pico 2 W ARM.**
Jde o dva nové, kompletně zachycené alarmové cykly po 2,5 s. Výsledky
z 29. 9., 100 cyklů a dlouhé spánky se zde nezapočítávají ani neopakují.

## Firmware a bezpečné převzetí

Host: macOS 27.2 arm64, picotool 2.3.1. Runtime UID, USB identita a ROM
chipid souhlasily se stejnou Mac deskou. Před zápisem vznikla nová lokální
záloha všech **29 souborů / 7 adresářů** a celé **4 MiB flash**, ověřená
samostatným čtením přes `picotool verify`. Offline LittleFS kontrola
souhlasila s runtime inventářem; nebyl použit formátovací fallback.
Zálohy, identifikátory a původní aplikační soubory zůstaly soukromé.

Sestava navazuje na uživatelem potvrzené zapojení: Pico 2 W s Waveshare
Pico-ePaper-2.9 **B/W V2, 296×128**, napájené přes hub → JT-UM120 IN → OUT
→ Pico, PC port měřáku ve stejném hubu, bez dalšího napájení či debuggeru.
Revize a fyzická topologie jsou převzaté z potvrzené sestavy; nově bylo
elektronicky ověřeno uspání a parkování připojeného panelu při každém bootu.
Panel se nepřekresloval, proto nebyla požadována nová vizuální kontrola.

Firmware je pracovní strom nad `6ce738ae0f13ab0732ed66f761a35aee04e64fab`
s opravou `machine_deepsleep_init()`, která odstraňuje pouze ENABLE při
vypršelém čítači watchdogu. TinyUSB patch zůstává zachovaný.

- Runtime: `v1.30.0-preview.105.g6ce738ae0f.dirty`, build `RPI_PICO2_W`.
- BIN: **889840 B**, SHA256
  `a0a2107db05f6ea2246cb8540e2d715b72bbcfa7a0cae1492b25cb6b7ae2ee08`.
- UF2 SHA256:
  `9d60d6bbe829ec745456ab0c6edf9b65cf4b4bb35c5fff8babf3b085acc49146`.
- Konec erase rozsahu firmwaru `0x100da000` je pod filesystemem `0x10180000`.
- Před prvním READY/PASS každého bootu se kontroloval skutečný BIN v XIP flash. Stejné
  bajty byly znovu ověřeny při kontrole dokončených testů i po obnově.

## Dokončené testy

### První aplikace po UF2 — PASS, 15:35:32 UTC

Testovací soubory byly připravené před startem. Spuštění provedl
`picotool load -u -v -x firmware.uf2`, tedy ROM **FLASH_UPDATE** restart.
Mezi tímto startem a prvním spánkem nebyl Ctrl-C, Ctrl-D ani `machine.reset()`.
Host ověřil už první aplikační boot, nikoli až dodatečně restartovanou desku.

| Boot / fáze | Výsledek | Reset cause | WATCHDOG.CTRL | REASON |
| --- | --- | ---: | --- | ---: |
| 1 / 0 | READY po UF2 | 1 | `0x00000000` | 1, TIMER |
| 2 / 1 | 1 dokončený alarmový spánek | 4, DEEPSLEEP_RESET | `0x07000000` | 0 |
| 3 / 5 | PASS po běžném resetu | 3 | `0x00000000` | 2, FORCE |

První boot tedy zachoval skutečný TIMER důvod ROM watchdogu a měl ENABLE
vypnutý. Spánek nevyhodil falešné EBUSY. Po probuzení souhlasily také
POWMAN alarm `0x40`, HAD_SWCORE_PD a scratch/filesystem sentinel.

### Živý watchdog → timeout → deepsleep — PASS, 15:38:09 UTC

`machine.WDT(timeout=2000)` byl spuštěn pouze na počátečním bootu.
Před `expect_busy()` měl ENABLE=1 a kladný raw TIME **1999950**. Volání
spánku vrátilo `OSError(EBUSY)`; bezprostředně poté zůstal ENABLE=1 a
raw TIME **1998555**. Následoval skutečný timeout, nikoli náhradní
`machine.reset()`. Stav fáze 4 se nastavuje až po potvrzeném EBUSY.

| Boot / fáze | Výsledek | Reset cause | WATCHDOG.CTRL | REASON |
| --- | --- | ---: | --- | ---: |
| 1 / 0 | READY, poté aktivní WDT / EBUSY | 3 | `0x00000000` před aktivací | 2 |
| 2 / 4 | READY po skutečném timeoutu | 3, WDT_RESET | `0x00000000` | 1, TIMER |
| 3 / 1 | 1 dokončený alarmový spánek | 4, DEEPSLEEP_RESET | `0x07000000` | 0 |
| 4 / 5 | PASS po běžném resetu | 3 | `0x00000000` | 2, FORCE |

Po skutečném WDT_RESET prošel požadovaný spánek 2,5 s se správným alarmovým
probuzením. Další běžný reset už `DEEPSLEEP_RESET` nehlásil. USB se v obou
dokončených sadách vrátilo na všech očekávaných bootech.

ACK spánku → následující READY trvalo **5,839 s / 5,801 s**, RTC hlásilo
v obou případech **5 s**. Interval zahrnuje boot, USB a přibližně 2,1 s
přípravy panelu po probuzení; není to měření samotné délky spánku či LPOSC.

## Neúplné pokusy a rozsah důkazů

Přípravný pokus překročil 60s čekací okno hostitele při nahrávání a
ověřování flash. Bezpečnostní kontrola zastavila postup **před `-x`**;
aplikace se vůbec nespustila. Firmware a filesystem již byly ověřené.

Další pokus zachytil první boot TIMER/ENABLE a úspěšné alarmové probuzení,
ale privátní hook počítal hash jen při READY. Závěrečný boot hlásil rovnou
PASS, takže přísná kontrola hostitele odmítla chybějící hash. Nebyl to
EBUSY, selhání alarmu ani ztráta USB. Hook se opravil na READY **i PASS**;
test se zopakoval skutečným UF2 FLASH_UPDATE startem a prošel celý.
Původní soubory byly při opravě zachované a retry checkpoint celé flash
znovu nezávisle ověřený. Tento další alarm se mezi dva dokončené cykly
nezapočítává. Souhrny neúplných pokusů jsou v důkazech.

Veřejné funkce `run()`, fáze, ACK a spánková cesta zůstaly v privátním
fixture stejné jako současné `device.py`. Doplněné hooky čtou hash a
registry watchdogu a přidávají metadata připraveného panelu.
Test **neověřuje živý watchdog zděděný už při startupu** (ROM
try-before-you-buy), RP2040 ani RISC-V. Nové měření spotřeby, Wi-Fi test,
100 cyklů ani dlouhé spánky se v této sadě neprováděly.

## Skutečný konečný stav — 15:39:49 UTC

- Opravený experimentální firmware zůstal na desce; jeho bajty odpovídají BIN.
- Všech **29 původních souborů a 7 adresářů** souhlasí s novou zálohou.
  Původní `main.py` byl obnoven jako poslední změna souborů.
- Všechny **tři oblasti `mem_backup`** byly obnovené a přečtené zpět.
- RTC byl obnoven z počátečního RTC plus skutečně uplynulý monotónní čas
  hostitele; čtecí bracket byl 0,039 s, RTC má sekundovou kvantizaci.
- Testovací soubory byly odstraněné, rádio/BLE neaktivní, panel uspaný a
  registry parkování ověřené. Obraz nebyl změněn.
- Deska skončila ve **friendly REPL**, bez resetu po obnově a bez spuštění
  původní aplikace. Další reset může původní aplikaci spustit.

Nové důkazy: [provenance](evidence/mac-20260930-watchdog/provenance.json),
[první UF2](evidence/mac-20260930-watchdog/first-uf2-events.jsonl),
[watchdog](evidence/mac-20260930-watchdog/after-wdt-events.jsonl),
[konečný stav](evidence/mac-20260930-watchdog/final-state.json),
[nezapočítané pokusy](evidence/mac-20260930-watchdog/excluded-attempts.json).
Zpráva zachycuje výše uvedený testovaný firmware a pracovní zdroje;
upstream PR nebyl založen.
