# Handover pro PC s Picem a měřákem

**Aktualizace 1. 10. 2026:** nejnovější Mac ověření je v
[LPOSC, startup WDT a aplikačním měření](RESULTS-LPOSC-APP-MAC-20260930.md),
navazuje na [opravu expirovaného watchdogu](RESULTS-WATCHDOG-MAC-20260930.md).
Nová relace dokončila čtyři časovací a tři aplikační alarmové návraty,
šest full refreshů a měření tří celých period s připojeným USB.
Současný konečný Mac stav: přesný experimentální BIN `a0a2107d…ee08`,
29 původních souborů a 7 adresářů ověřeno, všechny tři backup regiony
a RTC obnoveny, rádio/BLE vypnuté, panel zaparkovaný, friendly REPL.
Původní aplikace byla vrácena beze změn a nespustila se; Z2 dekodér byl
pouze součástí odstraněného testu. Fyzický obraz dosud není potvrzený.
Níže je zachováno původní předání z 29. 9., jeho počty nejsou současný stav.

Připraveno 29. 9. 2026. Úkol na cílovém PC: převzít aktuální kandidát,
ověřit jej na **tamní** desce a změřit odběr i energii cyklu. Toto předání
nespouští testy, neflashuje a nepopisuje nově ověřený stav vzdálené sestavy.

## Stav, ze kterého pokračovat

- Fork `https://github.com/Rhiz3K/micropython`, větev
  `rp2/rp2350-timed-deepsleep`. Zdrojový checkpoint před tímto předáním je
  `2d260c80b6699f7d01d4a98325302dc910b4a80f`; samotný core firmware se od
  `2445a04bfa2f426e8390b2efaa6450910734e430` nezměnil.
- Timed deepsleep na ARM Pico 2/Pico 2 W požaduje P1.7, nový ROM boot,
  zachování RTC a `mem_backup(2)`. Aktivní WDT, Python worker na druhém jádře
  a nevhodný IRQ kontext vracejí EBUSY. Bezargumentová cesta je původní.
- Finální Linux kandidát má **5 alarmových probuzení**, reset-cause a další
  kontroly PASS. **100 cyklů, 30/75 minut a měření této revize zatím chybějí.**
  RISC-V má 4 buildy PASS, ale používá starou cestu lightsleep → reset;
  žádná RISC-V P1.7/runtime podpora se tím nedokládá.
- Exporty patchů kontroluje `tools/generate_patches.py`; zdroj pravdy je Git.
  TinyUSB vyžaduje samostatný `prepare-tinyusb.sh`. Samotný clone nestačí.

| Sestava | Poslední známý stav, který je nutné znovu ověřit |
| --- | --- |
| Mac / měřicí sestava `test-board-2` | Pico 2 W ARM, Waveshare **Pico-ePaper-2.9 B/W V2, 296×128**, Joy-IT **JT-UM120**. Dne 28. 9. firmware `v1.30.0-preview.88.g764de396cf.dirty.usbq1`, 29 souborů, friendly REPL, rádio vypnuté, panel zaparkovaný. Další reset mohl spustit původní aplikaci. |
| Původní Linux deska | Pico 2 W ARM, **B/W/R V4**, 37 souborů, firmware `2445a04bf` plus TinyUSB fix. Poslední read-only kontrola 29. 9. v 09:45 UTC. Její záloha, UID ani displejový postup nepatří Mac desce. |

Historických **0,37 mA** patří starším revizím a konkrétnímu USB zapojení.
Existují starší helperové i přímé C/GP25 testy; žádný neznamená měření
současné revize nebo odběru samotného RP2350. Wi-Fi selhání na
Linux/MikroTik zůstávají otevřená.

Podklady: [hlavní handover](HANDOVER.cs.md),
[finální ARM kontroly](RESULTS-REVIEW-20260929.md),
[navazující review a RISC-V](FOLLOWUP-REVIEW-20260929.md),
[dřívější GP25 měření](POWER-GP25-MAC-20260927.md).

## 1. Převzetí zdrojů a zařízení

Použij čistý klon; cizí rozpracované změny ani lokální TinyUSB patch nemaž.
Následující příkazy pouze připraví zdroje a ověří veřejné podklady:

```sh
git clone --branch rp2/rp2350-timed-deepsleep \
  https://github.com/Rhiz3K/micropython.git micropython-meter
cd micropython-meter
git merge-base --is-ancestor 2d260c80b6699f7d01d4a98325302dc910b4a80f HEAD
git status --short
python3 experiments/rp2350-deepsleep/tools/generate_patches.py --check
(cd experiments/rp2350-deepsleep && shasum -a 256 -c SHA256SUMS)
```

Na Linuxu lze místo `shasum -a 256` použít `sha256sum`. Zaznamenej nový HEAD,
OS/architekturu, verze nástrojů a později všechny revize submodulů.

1. Nejdřív pasivně vylistuj USB, potom ověř model, runtime USB serial,
   `machine.unique_id()`, `os.uname()` a `sys.implementation._build`:
   požaduj ARM `RPI_PICO2_W`, nikoli `RPI_PICO2_W-RISCV`. Nevybírej první sériový
   port a nepřebírej UID z jiného PC. Otevření REPL může přerušit aplikaci.
2. Ověř skutečný displej, měřák a zapojení. Historické zapojení bylo
   **hub → JT-UM120 IN → OUT → Pico**, PC port měřáku ve stejném hubu,
   bez jiného napájení Pica a debuggeru. Dnešní stav z fotografie/logu
   z minulého dne nevyplývá. B/W V2 helper nepoužívej na B/W/R V4.
3. Přečti aktuální `boot.py`/`main.py` a zazálohuj dnešní soubory,
   celou flash i všechna užitečná backup slova a RTC s host časem.
   Pro originální Pico 2 W má full flash 4 MiB. Ověř velikost, SHA-256,
   čitelnost zálohy a nezávislé `picotool verify`. BOOTSEL serial ověř
   zvlášť; nemusí se shodovat s runtime serialem.
4. Zajisti použitelnou BOOTSEL obnovu této desky. Dříve udělené oprávnění
   pro identifikovanou sestavu platí; při nejasné identitě ji nejdřív vyřeš.
   Flash dump jiné desky nepoužívej. Nové zálohy a manifest drž mimo Git.

Při chybě USB zaznamenej host log a čas. Nepouštěj znovu rizikové `trace=7`
ani reset celého hubu. Power-cycle konkrétního portu potřebuje aktuálně
ověřenou topologii a vyloučené druhé napájení; jinak použij fyzický reconnect.
BOOTSEL obnova: odpojit napájení, držet BOOTSEL, připojit, ověřit správný
RP2350 disk a nahrát vlastní známý obnovovací obraz. Běžný firmware UF2
sám o sobě neobnovuje filesystem.

## 2. Kandidát a build

Použij [ARM build postup v hlavním handoveru](HANDOVER.cs.md#4-převzetí-zdrojů-a-build-na-druhém-pc),
`BOARD=RPI_PICO2_W`, prázdné `BOARD_VARIANT`, plný ARM GCC 14.3.1 a
MinSizeRel. Neinstaluj RISC-V variantu. Nejdřív submoduly, potom
`bash experiments/rp2350-deepsleep/prepare-tinyusb.sh`, poté mpy-cross a port.
SDK je `98a542c1a62fb549ffb5d66a3e5892b06276b670`, TinyUSB gitlink
`b549ac1d84cbbe550c9590951e2290098b3fb16c` plus přesně kontrolovaný patch.

Referenční Linux UF2 má SHA-256
`b6eb010e46925f196002de0b9fd865da5107e9a9d8b49c3853577d7108ce53f2`;
není ve veřejném Git repozitáři. Nový build z HEAD dostane vlastní runtime
verzi a hashe; zaznamenej je, nepředstírej shodu starým version override.
Nahrání proveď až po vlastní záloze a posouzení autostartu zachovaného
`main.py`. Ověř naprogramované bajty vůči BIN, runtime identitu a návrat USB.
Na nové desce nový build potřebuje vlastní hardware výsledky.

## 3. Funkční série bez měřicích závěrů

[Protokol 2 a manifest](../../tests/ports/rp2/deepsleep/README.md) jsou závazný
popis harnessu. Instalátor dočasně nahrazuje `main.py`; existující `boot.py`
nadále běží a nesmí aktivovat rádio nebo aplikaci proti testovacímu profilu.
Suite mění RTC a všechna backup slova. Obnovu z vlastního výchozího stavu
připrav před instalací. Stav cyklů se ukládá do POWMAN, ne každým cyklem do flash.

V kořeni klonu založ privátní pracovní prostor a venv:

```sh
umask 077
meter_work="$HOME/pico-work/meter-review-$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$meter_work"
python3 -m venv "$meter_work/venv"
meter_python="$meter_work/venv/bin/python"
"$meter_python" -m pip install pyserial
"$meter_python" tests/ports/rp2/deepsleep/host.py list
```

Do `$meter_work/manifest.json` připrav skutečný manifest podle README,
s vlastními ověřenými zálohami. Nevkládej tam příklady UID ani smyšlené
potvrzení zálohy. Každá řádka následující tabulky je **samostatný run**,
nový název/config/log a nová instalace; další spusť až po vyhodnocení předchozího.

| Pořadí | `cycles` | `sleep_ms` | `--timeout` | Výsledek při předání |
| --- | ---: | ---: | ---: | --- |
| Smoke test | 3 | 2500 | 120 | NEPROVEDENO na převzaté sestavě |
| Opakované probouzení | 100 | 2500 | 120 | NEPROVEDENO |
| 30 minut | 1 | 1800000 | 1920 | NEPROVEDENO |
| 75 minut, požadavek přes 72 minut | 1 | 4500000 | 4620 | NEPROVEDENO |

Příklad `$meter_work/config.json` pro smoke test:

```json
{
  "run": "meter-review-smoke-UNIQUE",
  "cycles": 3,
  "sleep_ms": 2500,
  "radio": "never",
  "expect_deep_cause": true,
  "rtc_tolerance_s": 3,
  "host_tolerance_s": 0.25
}
```

Pro oba dlouhé běhy nastav předem například `rtc_tolerance_s: 60` a
`host_tolerance_s: 60`; je to explicitní hranice této zkoušky, nikoli
specifikace LPOSC. Ulož skutečné odchylky. Selhání tolerance zachovej a
vyšetři; po běhu neposouvej hranici jen kvůli získání PASS.

Po záloze a úpravě názvu/configu pro zvolený run:

```sh
"$meter_python" tests/ports/rp2/deepsleep/host.py install \
  --manifest "$meter_work/manifest.json" --config "$meter_work/config.json" \
  --replace-main --allow-write
"$meter_python" tests/ports/rp2/deepsleep/host.py run \
  --manifest "$meter_work/manifest.json" --config "$meter_work/config.json" \
  --allow-run --timeout 120 --log "$meter_work/smoke.jsonl"
```

Pro další run změň config, jméno logu a timeout podle tabulky. Původní úplná
záloha zůstává zdrojem obnovy: `*-main-before-install.py` z druhé instalace
může obsahovat předchozí harness, nikoli aplikaci. Host musí být připojený
od začátku; bez potvrzení READY a SLEEP deska neusne. Na Macu při běhu
zajisti bdělý host, např. `caffeinate -i` před uvedeným příkazem `run`.
Současně smí Pico serial otevřít jen tento runner, ne také měřicí skript.
Per-boot `--timeout` není tvrdý limit zaseknutého serial write/flush.
Hostitelský dohled má mít také celkový deadline, například 1800 s pro
100 cyklů, 2100 s pro 30min a 4800 s pro 75min run; po jeho překročení
ukončit jen testovací proces, zachovat log a označit nedokončený běh.

PASS vyžaduje úplnou sekvenci a závěrečný obyčejný reset. Host interval
ACK SLEEP → READY zahrnuje boot/USB; není přesným časem v P1.7.
RTC a alarm sdílejí AON časovač, proto ani jejich vzájemná shoda není
nezávislá kalibrace. Při timeoutu nejprve uchovej log; neoznačuj běh PASS
podle návratu USB nebo stále viditelného obrazu na e-paperu.

## 4. Měření na stejné sestavě

Nejdřív identifikuj a ověř čtecí logger měřáku. Veřejný `host.py` **neměří
proud ani energii**. Dřívější raw logger a orchestrace nejsou ve forku;
na původním Macu je hledej soukromě pod
`~/pico-work/rp2350-mac-20260927-112409/`. Provenience a názvy, např.
`meter_reader.py`, `measure_one.py`, `analyze_power.py`, jsou v
[measurement-plan.json](evidence/mac-20260927-power/measurement-plan.json).
Nejdřív přečti skripty: mohou obsahovat staré UID, cesty a serial orchestrace.
Pokud na tomto PC nejsou, připrav/ověř nový logger; souhrnné CSV nenahrazuje
raw záznam a samotné připojení HID není důkaz správného dekódování.

U JT-UM120 dřívější čtení používalo pouze handshake/keepalive 0x81/0x82/0x83,
CRC a čtyři vzorky na rámec. Neměnit výstupní napětí, trigger rychlonabíjení
ani kalibraci. Historicky udávané rozlišení je 10 µA, nejde o nezávisle
ověřenou absolutní přesnost; malé rozdíly pod možnostmi přístroje nepřisuzovat pinům.

Pro každý běh zaznamenej napětí, měřicí místo, přístroj/rozlišení/vzorkování,
oba kabely měřáku, hub, debugger, periferie, stav rádia a přesný stav panelu.
Měření na USB vstupu zahrnuje celou připojenou sestavu. Reference bez zátěže
je samostatný záznam; automaticky ji neodečítej. Zachovej nuly, špičky, mezery
i chybné rámce s příznakem. Ověř časové pokrytí každého vyhodnocovaného okna.

Srovnej stejný napájecí řetězec a přípravu, alespoň tři opakování na režim:

| Varianta | Co spustit |
| --- | --- |
| A | `time.sleep_ms()`; pro celý srovnatelný cyklus potom reset |
| B | `lightsleep()` → reset a odděleně původní upstream `deepsleep()` |
| C | Nový timed `deepsleep()` bez Python radio/GP23/GP25 helperu |
| C + aplikační příprava | Samostatný označený běh s ověřeným helperem |

Harness podporuje `mode: sleep_reset / lightsleep_reset / deepsleep`,
viz README; na kontrolním upstreamu je `expect_deep_cause: false`.
U C použij zvlášť profil `never` a profil `sta`, který rádio inicializuje
a nechá jej ukončit C kódem; `sta` bez síťového configu nedokazuje připojení.
Panel připrav stejně ve všech variantách jeho správným driverem. Nemíchej
test core přípravy s Python helperem, který už předem stáhne GP23/GP25.
Zkoušky GP24/29 zatím do této sady nepřidávej.
Veřejný harness panel sám neinicializuje ani neuspává a nemá konfigurační
panelový hook. Přípravu zajisti a zdokumentuj při každém bootu stejně v A/B/C;
samotný výchozí `host.py run` tuto část měřicího postupu neprovádí.

Kontrolní upstream základ je `09f5bb447504a058376c62fe991b3613531837e6`.
Neupravený upstream a tentýž základ s pouhou TinyUSB opravou označ odděleně:
první ukazuje původní stav, druhý pomůže izolovat efekt POWMAN změny.
Neslučuj změnu USB závislosti s tvrzením o samotném deepsleep core.

Pro ustálený proud lze navázat na 300s běhy s předem určeným pozdním oknem;
celý průběh přesto uchovej a stabilitu ověř. Energii počítej z integrálu
`U(t) * I(t)` přes stejně definovaný celý cyklus včetně bootu, síťového
připojení a čekání na host. Variabilní USB ACK čekání musí být viditelné.
Historický logger přiřazoval čtyřem vzorkům společný host čas přijetí rámce,
bez individuálních device timestamps. U integrace energie uveď použitý
časový model a nejistotu; krátké špičky mohou měřáku uniknout.
Se síťovým profilem zvlášť ověř DHCP, DNS a očekávané HTTP tělo na vlastním
endpointu. Síťové timeouty uchovej; test na jiné síti neřeší Linux/MikroTik FAIL.

POWMAN/reset záznamy a odběr jsou dva různé důkazy. Samotný pokles proudu
neprokazuje vypnutí domén; post-boot snapshot GPIO neprokazuje jejich úroveň
ve spánku. Bez debuggeru nejdřív ověř běžnou sestavu. Variantu bez USB dat
připrav samostatně tak, aby měl harness potřebný SLEEP ACK a zůstalo napájení;
prosté odpojení jediného napájecího kabelu není test spánku.

## 5. Obnova a odevzdání

Ponech aktuální experimentální firmware podle přání uživatele. Vrať **dnešní
vlastní** soubory/aplikaci, konfiguraci, backup slova a RTC s uplynulým časem;
odstraň jen evidované testovací soubory a guardy. Host runner nemá automatický
restore příkaz. Porovnej celý inventář velikostí/SHA s výchozí zálohou.
Uveď, zda aplikace běží, nebo je zastavená ve friendly REPL, a stav rádia/panelu.

Výstupem je nový report pro tuto desku a firmware: SHA, příkazy, kompletní
PASS/FAIL/NEPROVEDENO, 100cyklový/30min/75min log, aktuální proud s rozsahem
a energií cyklu, podmínky a omezení přístroje, obnovení souborů a konečný stav.
Původní výsledky nepřepisuj. Veřejně pouze anonymizované podklady; UID,
hesla, raw osobní konfigurace a flash zálohy zůstávají soukromé.
Upstream PR zatím nezakládej, DCO/identitu nevymýšlej a soukromý aplikační
firmware ani webový instalátor nezahrnuj do core změny.
