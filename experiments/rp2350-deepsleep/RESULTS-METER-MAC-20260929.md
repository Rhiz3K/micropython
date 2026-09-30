# RP2350 / Pico 2 W — nové ověření na Macu 29. 9. 2026

**Závěrečná zpráva po opakovaném měření a obnově 29. 9. 2026 v 19:24:45 UTC (21:24 CEST).
Obnova souborů, RTC a retenčních regionů PASS; experimentální firmware ponechán.
Nový obraz uživatel potvrdil. Úplný no-load pokus neprošel; zachycený
úsek bez Pica je vyhodnocen samostatně jako diagnostika.**

Souhrn sedmi měřicích profilů je **4 PASS a 3 FAIL**. Kandidátní deepsleep
má v předem stanoveném okně přibližně **0,373 mA při 5,08 V** na USB vstupu
celé sestavy s displejem. Jde o modelové výsledky JT-UM120 bez nezávislé
kalibrace absolutní přesnosti. A a tři C varianty mají platné cykly; B-LS
selhal ve dvou pokusech a obě upstream reference skončily funkčním FAIL.
**Platné srovnání spotřeby proti upstream deepsleep proto není k dispozici.**

Kandidát prošel 3 + 100 krátkými probuzeními, 30minutovým i 75minutovým
spánkem. Po ručním návratu kandidáta prošel další 2500ms smoke a čerstvé
ověření skutečných BIN bajtů. Původní RTC continuity FAIL při přepínání
firmware zůstávají nevyřešené. Čtyřbuněčná RAM sonda lightsleep zaznamenala
40/40/2500/2500 ms; nejde o opravu ani opakování cílových 300s testů.
Finální render má elektronický PASS a nové fyzické potvrzení uživatele.
První no-load pokus skončil timeoutem; druhý zachytil odpojení, ale skončil
chybou čtení HID ještě před doložením návratu USB.
Původní soubory, RTC a retenční regiony byly následně obnoveny; aplikace
zůstala zastavená ve friendly REPL.

Žádný starší výsledek spotřeby, dlouhého spánku, Wi-Fi ani jiné desky není
započítán jako nový výsledek této revize.

## Sestava a výchozí záloha

Uživatel dnes potvrdil Pico 2 W ARM s Waveshare **Pico-ePaper-2.9 B/W V2,
296×128** a měřákem **Joy-IT JT-UM120**. Napájecí řetězec je USB-C hub →
JT-UM120 IN → JT-UM120 OUT → USB Pica; PC port měřáku je v témže hubu.
Není připojen debugger ani další zdroj napájení. Host je macOS 27.2,
build 26B5091g, arm64. Tato identifikace displeje není převzatá z Linux
sestavy s B/W/R V4.

Před zápisem byla ověřena identita runtime/ARM buildu a odděleně BOOTSEL
zařízení. Výchozí firmware byl
`v1.30.0-preview.88.g764de396cf.dirty.usbq1` z 28. 9.; první dnešní čtení
ukázalo vypnutý watchdog a zařízení bylo poté ponecháno ve friendly REPL.
Následovalo:

- dnešní zálohování a ověření velikosti/SHA-256 všech **29 souborů**;
- čerstvá úplná flash **4 194 304 B**, SHA-256 a nezávislý `picotool verify`;
- soukromé uložení RTC a všech tří dostupných backup regionů;
- offline ověření LittleFS proti stejným 29 souborům a inventář **7 adresářů
  včetně root**, včetně prázdných adresářů;
- přesun původního main do dočasného evidovaného názvu a instalace guardu
  výhradně v kopii filesystemu, kontrola po remount, potom ověřený zápis této
  kopie a programu. Guard neimportuje aplikaci ani síť a nemění RTC/backup slova.

Filesystem leží na offsetu `0x180000`, má `0x280000` bajtů. Guardovaná kopie
měla 30 souborů, ostatní původní obsah byl zachován. Programové bajty kandidáta
byly ověřeny vůči BIN; filesystem byl znovu ověřen i po jeho nahrání. UID,
USB serial, soukromé soubory a plné obrazy flash zůstávají mimo veřejné podklady.

## Přesný firmware

Zdroj kandidáta: `91e91d58de8513fbf3f3e2829e49bf22843fac86`.
Build je nativní ARM **RPI_PICO2_W**, bez BOARD_VARIANT, GCC **14.3.1**,
**MinSizeRel**, bez ručního přepsání version stringu. Runtime:
`v1.30.0-preview.104.g91e91d58de.dirty on 2026-09-29 (GNU 14.3.1 MinSizeRel)`.

| Kandidát | Bajtů | SHA-256 |
| --- | ---: | --- |
| BIN | 889824 | `0c8c1b0439fa050e1bf30c7f586f5deeb5e53b202b91877e30840411148ad12b` |
| UF2 | 1780224 | `d7e6172b40c65eb84bc58d08646b80dc184a03b08785a1f5fb7fe1e9db3838e1` |
| ELF | 8821116 | `b9c2058e193a0c8648fc2f6ab8e09bb2e956aae88617cd76862455a47dc80fc5` |

SDK: `98a542c1a62fb549ffb5d66a3e5892b06276b670`. TinyUSB gitlink:
`b549ac1d84cbbe550c9590951e2290098b3fb16c`, navíc přesná oprava queued SETUP
ze zdejšího `prepare-tinyusb.sh`; SHA patche
`ffbadfaa2a51af420e64e1bdb4fad55f1621646eb3bcd98e3d93eaa921076e4e`.
Dirty označení kandidáta zahrnuje tuto vědomou úpravu závislosti; nesmí se
zaměnit za neupravený upstream.

Dva kontrolní buildy byly staticky ověřené, nahrané a každý samostatně
otestovaný. Oba nové referenční spánkové běhy skončily **funkčním FAIL**;
výsledky přepnutí firmware a jejich samostatné guard ověření jsou oddělené
od výsledku vlastního spánkového testu, jak je rozlišeno níže.
Oba buildy vycházejí z
`09f5bb447504a058376c62fe991b3613531837e6`:

| Kontrola | Runtime | BIN SHA-256 | UF2 SHA-256 |
| --- | --- | --- | --- |
| Upstream bez změny | `v1.30.0-preview.85.g09f5bb4475` | `340360f9d49d8d5ec70c308af210c5b9dca84d23f3f55b07732ae01258349ae9` | `71d10571198cef144c2139028903d1ea9d411a1697cdb045fc433f61511e7c6f` |
| Upstream + pouze TinyUSB oprava | `v1.30.0-preview.85.g09f5bb4475.dirty` | `c893e0c19802b6098365ad3d917b4ffd306914d69acb0f3316a05130bd8d1e49` | `10873c94cbcf7fd08c52fcbd320e67a209d7ed42a761b3360be44ed581a9cdaa` |

## Watchdog po BOOTSEL

První guardovaný boot nového kandidáta se vrátil přes USB, ale čtení ukázalo
`WATCHDOG.CTRL = 0x40000000`: ENABLE=1, zbývající čas=0, REASON=1.
Tento stav nebyl vydáván za připravený začátek deepsleep testu.

Obyčejný `machine.reset()` do ověřeného guardu vedl k ENABLE=0,
`CTRL=0`, `REASON=2`, `reset_cause=3`. Výsledek byl přečten a uložen
29. 9. v 14:13:40 UTC. Řešení nepoužilo přímé přepsání registru watchdogu.
Teprve potom začaly funkční série. Z této přípravy samotné neplyne nový test
odmítnutí deepsleep při aktivním WDT.

## Harness a příprava displeje

Veřejný `tests/ports/rp2/deepsleep/device.py`, protokol 2, má SHA-256
`2dfabddd920d7b97b79e8c28084dcfbd945da20420a0171d3be276753feac96e`.
Nasazený privátní `device-panelmeta.py` má SHA-256
`cdadbbd07bc7ecd7b6c26a97641bc736bd15b19f9016f92ae1bfc8fe865d903d`.
Obsahuje přípravný prefix a jednu popsanou změnu `emit()`: zkopíruje record
a přidá `panel_prep`. Veřejné kontroly resetu, čítačů, RTC, sentinelů, rádia
a samotná sleep cesta zůstávají stejné. Toto je tedy veřejný harness
s výslovně přiznanou přípravou konkrétní měřicí sestavy, ne tvrzení o
byte-for-byte nezměněném nasazeném `main.py`.

Při **každém bootu**, včetně závěrečného obyčejného resetu, wrapper znovu
nastaví displejové piny/SPI a použije ověřený vendor B/W V2 driver:

1. reset a inicializace řadiče/LUT **bez refresh obrazu**;
2. vendor příkaz deep sleep `0x10/0x01`, čekání 2 s a RST low;
3. zastavení SPI před zaparkováním sběrnice veřejným
   `pico_epaper29_lowpower.park_after_sleep()`;
4. ověření latch/OE a pad registrů, připojené do protokolových záznamů.

BUSY čekání má limit 30 s a celá BUSY fáze 45 s. Vendor zdroj je připnut na
commit `c9bcd84db5adf5f085353649a8a5c31492bc5fb8`; jeho SHA-256 je
`93ed904c879b9fe44503c8c198f97036b0c1266b82285c964089543f1572d254`.
Ve dokončených krátkých bězích trvala příprava 2118–2119 ms na boot.
Neimportuje `network`/`bluetooth` a nemění GP23/GP25. Profil `radio=never`
neprovádí síťový test ani nedokazuje Wi-Fi reconnect.

Úspěšný BUSY/pinový test nepotvrzuje skutečný text na panelu. Nový závěrečný
obraz „B: METER REVIEW OK“ s pravým černým obdélníkem byl v samostatném
bounded renderu elektronicky dokončen jako **PASS v 18:35:33.864638 UTC**.
Proběhl jeden úplný refresh, vendor sleep a ověřené parkování; render trval
5157 ms a neprovedl reset ani nespustil původní aplikaci. Čerstvé čtení
potvrdilo skutečné kandidátní BIN bajty, guard, zachování 29 původních
souborů a všech tří backup regionů; spojení skončilo uzavřené ve friendly
REPL. Původní renderový záznam zachovává `visual_result=NOT_VERIFIED`;
následné dnešní potvrzení uživatele, že nový text i obdélník jsou správně,
je odděleně zaznamenané jako `USER_CONFIRMED` v
[evidenci obrazu](evidence/mac-20260929-meter/final-display/visual-confirmation.json).

## Dnešní funkční výsledky

Všechny níže uvedené funkční sady používají nový kandidát, `mode=deepsleep`,
`radio=never`, `expect_deep_cause=true`, bez Python radio/GP23/GP25 helperu.
Host v těchto sadách od začátku používal READY a SLEEP ACK, bez hostem vynuceného resetu cyklu.

| Sada | Ověřený stav | Doklad |
| --- | --- | --- |
| 3 × 2500 ms | **PASS** | 4 READY, 3 SLEEP, konečný PASS: completed=3, boot=5, phase=5, cause=3; dokončeno 14:15:04 UTC |
| 100 × 2500 ms | **PASS** | 101 READY, 100 SLEEP, konečný PASS: completed=100, boot=102, phase=5, cause=3; dokončeno 14:24:35 UTC |
| 1 × 1800000 ms | **PASS** | 2 READY, 1 SLEEP, konečný PASS: completed=1, boot=3, phase=5, cause=3; dokončeno 14:55:03 UTC |
| 1 × 4500000 ms | **PASS** | 2 READY, 1 SLEEP, konečný PASS: completed=1, boot=3, phase=5, cause=3; dokončeno 16:10:50.224956 UTC |

Všech **103 nových krátkých alarmových probuzení** má cause=4,
`LAST_SWCORE_PWRUP=64` a `CHIP_RESET.HAD_SWCORE_PD` nastavený. Stavový čítač,
POWMAN sentinel a vyhrazená nula v unused slovech prošly kontrolami harnessu.
Záznamy watchdog scratch retention jsou `[false,false]`; nejde o tvrzení,
že by ve deep stavu byly zachovány všechny tři backup regiony. Konečné obyčejné
resety mají cause=3, takže se neopakuje starý příznak DEEPSLEEP_RESET.
Také obě nová dlouhá probuzení mají cause=4, `LAST_SWCORE_PWRUP=64`,
`CHIP_RESET=33554432` a watchdog scratch retention `[false,false]`.
U 75minutového testu je READY po alarmu boot=2/completed=1, následný
obyčejný reset končí PASS boot=3/completed=1/cause=3.

| Pozorovaný interval | Smoke 3 | 100 cyklů | 30 minut | 75 minut |
| --- | ---: | ---: | ---: | ---: |
| RTC delta od přípravy vstupu po další boot/panel přípravu | 5–6 s | 5–6 s | 1802 s | 4502 s |
| Host SLEEP ACK → následující READY | 5,372350–5,376974 s | 5,373379–5,394244 s | 1815,646946 s | 4534,351404 s |
| Dokončené alarmové cykly | 3 | 100 | 1 | 1 |

Host/RTC intervaly zahrnují boot, přípravu displeje a USB/host komunikaci.
**Nejsou měřením přesného času v P1.7.** RTC a alarm navíc vycházejí ze
stejného AON časovače; jejich shoda není nezávislá kalibrace LPOSC. U 30minutového
testu je host interval o 15,646946 s delší než požadovaných 1800 s;
u 75minutového o 34,351404 s delší než 4500 s. Přesná uložená hodnota
dlouhého host intervalu je `4534.351403874985` s. Složenému rozdílu nelze
z těchto čísel připsat jedinou příčinu. Skutečné hodnoty
zůstávají zachované, limity nebyly po výsledku posunuty.

Předem nastavené tolerance a dohled:

| Série | rtc_tolerance_s | Skutečné RTC přijímací meze harnessu | host_tolerance_s / dolní host mez | No-progress timeout / celkový observer deadline |
| --- | ---: | --- | --- | --- |
| Smoke a 100 cyklů | 3 | 1 až 15,5 s | 0,25 / 2,25 s | 120 s / 300 s pro smoke, 1800 s pro 100 |
| 30 minut | 60 | 1740 až 1870 s | 60 / 1740 s | 1920 / 2100 s |
| 75 minut | 60 | 4440 až 4570 s | 60 / 4440 s | 4620 / 4800 s |

RTC horní mez je target + tolerance + 10 s, dolní mez nejméně 1 s pro tyto
targety. Host validator kontroluje dolní mez, nikoli symetrické ±tolerance;
horní časový dohled zajišťují samostatné timeouty. Tolerance není specifikací
přesnosti oscilátoru a nesmí se dodatečně měnit jen kvůli získání PASS.

Nové Wi-Fi/DHCP/DNS/HTTP transakce, BLE/AP klienti, CPU1/IRQ/DMA/WDT
negativní testy a RISC-V runtime nejsou obsahem těchto dokončených sad.

Po obou referenčních FAIL byl znovu nasazen kandidát a proveden samostatný
`candidate-final-smoke`: **1 × 2500 ms PASS**, `deepsleep`, `radio=never`,
`expect_deep_cause=true`, tolerance RTC 3 s a host 0,25 s. Výsledek byl
uzavřen v **18:20:31.601019 UTC**, completed=1, boot=3 po závěrečném
obyčejném resetu. Příprava panelu opět neprovedla refresh a ověřila parkování.
Tento smoke je samostatný funkční test po návratu kandidáta, není čtvrtým
opakováním některého energetického profilu ani důkazem obnovy aplikace/RTC.

## Proud a energie — uzavřený souhrn 4 PASS a 3 FAIL

Srovnávací měřicí pokusy jsou uzavřené; čerstvý pokus o referenci bez
zátěže skončil FAIL bez platného intervalu. Níže zůstávají i všechny předchozí chyby. Sada `cmp300`
byla spuštěna v 16:11:36.609490 UTC a skončila
**FAIL v přípravné fázi `meter_startup` v 16:11:41.418007 UTC**:
`Meter startup cadence outside 95..105 Hz`. První profil A má
`functional_result=NOT_RUN`, `energy_result=NOT_RUN`, `capture_result=PASS`
a `complete_cycle_energy_model_valid=false`. Jde o neúspěšný start měřicí
sady; spánkový cyklus ani srovnávací analýza v tomto prvním pokusu nebyly
provedeny. Tento FAIL a původní 17souborový freeze zůstávají zachované.

Samostatný wrapper v2 počká před nezměněným testem 95–105 Hz nejméně na
500 recording vzorků a pět sekund od startu collectoru; po celou dobu
zachovává kontrolu čerstvosti a běhu collectoru. Nemění firmware, suite,
analyzátor ani profily. Má samostatný `measurement-source-freeze-v2.json`
s původními 17 nezměněnými hashi a hashem wrapperu
`c2850e74b5e0fd99ae1a61f3e8779e6c3b0a292e925a1abf087329c9040b47e5`.
Následná explicitně spuštěná sada `cmp300v2` začala v 16:17:09.496413 UTC.

| Profil | Zdroj | Skutečný uzavřený výsledek |
| --- | --- | --- |
| A, `time.sleep_ms(300000)` → reset, never | `cmp300v2` | **PASS**: 3 cykly; functional, capture i energy PASS; complete-cycle energy model valid; dokončeno 16:32:44.282527 UTC |
| B-LS, `lightsleep(300000)` → reset, never | `cmp300v2`, `cmp300cont2` | **2 × FAIL** v prvním cyklu: functional FAIL, capture PASS, energy NOT_RUN, completed=0; žádný platný proud/energie B-LS |
| C deepsleep never | `cmp300deep` | **PASS**: 3 cykly; functional, capture i energy PASS; complete-cycle energy model valid; dokončeno 17:17:33.763403 UTC |
| C deepsleep STA | `cmp300deep` | **PASS**: 3 cykly; functional, capture i energy PASS; complete-cycle energy model valid; dokončeno 17:33:18.053117 UTC |
| C + helper STA | `cmp300deep` | **PASS**: 3 cykly; functional, capture i energy PASS; complete-cycle energy model valid; dokončeno 17:49:05.670020 UTC |
| B upstream vanilla | `cmp300refvanilla`, index 06 | **FAIL**: první skutečný 300s pokus skončil boot=2, completed=0, RTC delta 2 s; capture PASS, energy NOT_RUN; uzavřeno 18:03:03.752183 UTC |
| B upstream s TinyUSB opravou | `cmp300refusbq`, index 07 | **FAIL**: první skutečný 300s pokus skončil boot=2, completed=0, RTC delta 2 s; capture PASS, energy NOT_RUN; uzavřeno 18:17:01.953467 UTC |

B-LS prošel startup gate v2 a odeslal `SLEEP` s `sleep_ms=300000`.
Následný záznam je `FAIL`, boot=2, completed=0, cause=3, phase=1,
`rtc_elapsed_s=2`, `AssertionError('RTC duration',)`. Hostový funkční
výsledek byl uzavřen v **16:33:01.721412 UTC**, celá sada potom v
**16:33:05.441023 UTC** ve fázi `suite`. Nejde o opakování chyby měřicí
startup gate. Cílová doba nebyla dodržena; příčina je předmětem samostatné
diagnostiky, tento protokol ji sám neurčuje. V rámci `cmp300v2` se po FAIL
nespustil žádný další profil ani přechod na baseline firmware.

Následné explicitní pokračování `cmp300cont1` skončilo v **16:46:59.281358 UTC**
ještě ve fázi `meter_startup`: uzavřený capture měl **524 recording vzorků**,
žádnou nevalidní/CRC-chybnou zprávu a jednu mezeru **0,646572167 s**.
Jeho globální kvalita byla DEGRADED. B-LS zde nebyl spuštěn
(`functional_result=NOT_RUN`, `energy_result=NOT_RUN`); tento start tedy
není druhým funkčním pokusem B-LS.

Samostatný `cmp300cont2` pak provedl právě jeden nezměněný B-LS pokus.
Funkční výsledek skončil **FAIL v 16:55:34.106037 UTC** se stejnou podstatnou
sekvencí: cílových 300000 ms → boot=2, completed=0, cause=3, RTC delta 2 s,
`AssertionError('RTC duration',)`. Sada byla uzavřena v **16:55:38.137335 UTC**.
Její měřicí capture má 1804 recording vzorků, nula nevalidních rámců,
nula nadlimitních gapů a PASS. Tento PASS měřáku nepovyšuje funkční FAIL
na použitelný proud nebo energii B-LS. Dva skutečné B-LS pokusy tak zůstávají
FAIL; příčina předčasného návratu není určena a firmware/harness nebyl opraven.

`cmp300deep` je další samostatně přezkoumaný běh pouze původních profilů
03–07, se zachováním A PASS a obou B-LS FAIL. B-LS znovu nespouští.
Původní V2 runtime, příkazy, konfigurace i limity zůstávají stejné; přidané
zdroje/proofs jsou odděleně zmrazené v řetězci **18 → 35 → 45 → 58**.
Profil C-never má uzavřený funkční PASS v **17:17:25.471330 UTC**, meter
capture skončil v **17:17:30.695754 UTC** a celý profil v
**17:17:33.763403 UTC**. Profile result i analýza jsou PASS a
`complete_cycle_energy_model_valid=true`; SHA-256 skutečné analýzy odpovídá
hodnotě v result: `54afeca7dbbca29424d0b9bf19a9ac2fec5ead040f2a7db9723b21271bc8a93d`.
Všechna tři READY→READY okna, tři 220s sleep okna a 12 drift podoken mají
PASS a úplné pokrytí hostitelského integračního modelu. Uzavřený capture má
**93452 recording vzorků**, nula nevalidních rámců, nula mezer nad 0,2 s,
maximum receipt gap **0,08153075 s** a nula skoků UTC/monotonic offsetu.

| C-never, tři cykly | Průměr s rovnou vahou každého cyklu | Minimum–maximum tří cyklických průměrů/hodnot |
| --- | ---: | ---: |
| Proud v předem určeném sleep okně ACK +60 až +280 s | **0,3728554037 mA** | 0,3727272727–0,3730121796 mA |
| Energie celého READY→READY cyklu, model host receipt trapezoid | **0,82878309457 J** | 0,82666242040–0,83117621825 J |

Tři skutečné READY→READY intervaly trvaly 304,960534250;
305,013626083 a 304,942063792 s. Sleep okna měla přesně 220 s a
22000/22004/22004 přijatých vzorků. Číselné hodnoty jsou reprodukovanými
odhady pro USB vstup celé sestavy, bez odečtu no-load reference; uvedené
minimum–maximum je rozptyl mezi třemi opakováními, nikoli interval nejistoty.
Kalibrace ani absolutní přesnost měřáku tím nejsou ověřeny.

C-STA byl samostatně uzavřen jako **PASS v 17:33:18.053117 UTC**, se třemi
celými cykly, třemi sleep okny a 12 drift podokny PASS a úplným pokrytím.
Průměr proudu sleep oken s rovnou vahou cyklů je **0,3717042424 mA**
(cyklická minima–maxima 0,3712136364–0,3722763636 mA), napětí
**5,0807809217 V**. Odhad energie celého cyklu stejným modelem je
**1,06936529911 J** (1,06244705278–1,07607704853 J). Uzavřený capture má
**93864 recording vzorků**, nula nevalidních rámců, nula mezer nad 0,2 s
a maximum receipt gap **0,082605792 s**. SHA analýzy shodný s profile result:
`bfb80ce1d69913bb6bea33baba717aa24c0dab2aea3aadff157164c44c3bb9e3`.
Tento STA profil neprokazuje připojení k Wi-Fi; podmínky a meze měření jsou
stejné jako popsané výše. Never a STA nejsou vzájemně zahrnuty do procentních
úspor; helper porovnání používá pouze dvojici STA variant.

C + helper STA má uzavřený **PASS v 17:49:05.670020 UTC**. Průměr proudu
sleep oken s rovnou vahou cyklů je **0,3722946970 mA**
(0,3715731818–0,3729136364 mA mezi cyklickými průměry), modelová energie
celého cyklu **1,08053908959 J** (1,07822748966–1,08477616469 J).
Všechna 3 celá, 3 sleep a 12 drift oken mají PASS a plné pokrytí.
Capture skončil v 17:49:02.663548 UTC: **94148 recording vzorků**, nula
nevalidních rámců, nula mezer nad 0,2 s a maximum receipt gap
**0,090697542 s**. SHA analýzy odpovídá profile result:
`4712469b8cad88a608e70c649e0a34dfd67039ede3481a16f33a60616f9e48f8`.
Tato samostatná helper varianta není dodatečně sloučená s C-STA ani použita
k úpravě původních kontrolních limitů.

Následný `cmp300deep-switch-vanilla` byl uzavřen jako **FAIL
v 17:49:58.724038 UTC**, fáze `ordinary-reset`, důvod
`RTC continuity differs from host elapsed time by more than 5 seconds`.
Celá sada `cmp300deep` skončila **FAIL v 17:49:59.123038 UTC**, fáze
`firmware_switch`, `candidate_restored=false`, `root_recovery_required=true`.
Profily 06/07 tedy v této sadě zůstaly NOT_RUN; selhání switche není výsledkem
jejich spánkového testu. SHA uzavřeného výsledku sady:
`48b03f77ad17e17a91e21102c011b95520e9f263cdd24a38c6854fff300edf79`.

Root následně provedl samostatnou čerstvou read-only kontrolu vanilla
runtime, přesného guardu/souborů, vypnutého watchdogu a friendly REPL.
Krátké nové pozorování ukázalo přibližně 10,45 s hostitele proti 11 s RTC;
neobjasňuje původní epochový posun a původní switch zůstává FAIL.
Před samostatnými referencemi byly znovu ověřeny skutečné bajty aktuálního
BIN ve flash, celý guardovaný inventář se zachováním 29 původních souborů,
backup, WDT0, cause=3 a uzavřené sériové spojení ve friendly REPL.
Supplemental guard důkaz pro vanilla byl dokončen v **18:01:49.218288 UTC**
(RTC 11 s / host 10,920773354 s), pro USBq v **18:15:52.800526 UTC**
(RTC 11 s / host 10,9055366 s). Také původní switch na USBq skončil RTC
continuity FAIL. Tyto chyby nebyly přepsané na PASS: root je výslovně přijal
pouze pro novou přípravu testovací sestavy po čerstvém guard ověření.
RTC nebylo touto guard kontrolou přepisováno. Původní harness před každým
cyklem nastavuje svůj RTC seed a následně používá nezměněné časové meze.

Každý referenční běh použil právě jeden původní profil a shodný V2
`run_profile`, collector, analyzer a limity; samostatný host wrapper nemá
automatický firmware switch ani retry. Jeho dva neměnné 70položkové manifesty
jsou sourozenci nad stejným rodičem58. Oba skutečné testy odeslaly SLEEP
pro 300000 ms, ale při dalším bootu skončily na `AssertionError('RTC duration',)`:

| Samostatná reference | Hostový interval oznámený FAIL záznamem | RTC delta | Dokončené cykly | Platný proud/energie |
| --- | ---: | ---: | ---: | --- |
| Vanilla | 5,932987500 s | 2 s | 0 | žádné |
| USBq | 5,890064625 s | 2 s | 0 | žádné |

Nejde o dva nové B-LS retry: jsou to odlišné upstream deepsleep reference.
Samotný jejich protokol neurčuje příčinu předčasného návratu. Výsledek
capture PASS pouze potvrzuje čisté zaznamenání neúspěšného testu.

Všechny dosavadní startup, funkční a switch FAIL zůstávají zachované;
nejde o tichý retry ani přepsání dřívějšího výsledku. `combined-final`
vybírá A z `cmp300v2`, tři C profily z `cmp300deep`, reference ze dvou
samostatných běhů a historické B-LS pokusy uchovává zvlášť. Výsledkem je
**4 PASS / 3 FAIL / 0 DEGRADED / 0 INCOMPLETE / 0 RUNNING / 0 NOT_RUN**.
Původní `cmp300deep` přesto zůstává FAIL s `candidate_restored=false`;
pozdější ruční návrat kandidáta tento historický záznam nemění.

| Platný profil, vždy tři cykly | Proud sleep okna [mA], průměr [min; max] | Napětí sleep okna [V], průměr | Energie READY→READY [J], průměr [min; max] |
| --- | ---: | ---: | ---: |
| A: `time.sleep_ms(300000)` → reset, never | 15,967739 [15,957041; 15,975155] | 5,068903 | 24,537503 [24,518425; 24,550248] |
| C deepsleep never | 0,372855 [0,372727; 0,373012] | 5,080676 | 0,828783 [0,826662; 0,831176] |
| C deepsleep STA | 0,371704 [0,371214; 0,372276] | 5,080781 | 1,069365 [1,062447; 1,076077] |
| C + helper STA | 0,372295 [0,371573; 0,372914] | 5,080976 | 1,080539 [1,078227; 1,084776] |

Cyklus má v průměru 302,886916 s u A, 304,972075 s u C-never,
305,833153 s u C-STA a 306,141426 s u helperu. Obsahuje skutečné hostem
pozorované ACK čekání, spánek a další boot/přípravu; energie se nepřepočítává
na předstíranou shodnou délku. Průměry mají rovnou váhu každého ze tří
cyklů. Číslice tabulky popisují reprodukované modelové odhady, nikoli takto
prokázanou absolutní přesnost přístroje. Hranaté závorky jsou min/max tří
cyklických hodnot, ne intervaly spolehlivosti.

Pouze dvě z devíti předem určených dvojic mají úplné srovnatelné podklady:

| Dvojice | Relativní úspora proudu sleep okna | Relativní úspora modelové energie celého cyklu |
| --- | ---: | ---: |
| A → C-never | 97,664945 % | 96,622382 % |
| C-STA → C + helper STA | −0,158851 % | −1,044899 % |

První řádek je **výhradně srovnání s A (`time.sleep_ms()` a reset)**.
Není to úspora proti upstream deepsleep; obě upstream reference selhaly
a žádné takové procento se nevydává. Druhý řádek má záporné znaménko,
protože naměřený průměr helper varianty byl mírně vyšší. Jde o popisnou
změnu při třech cyklech bez intervalu spolehlivosti, nezávislé kalibrace
nebo prokázání příčiny; sama neprokazuje přínos ani skutečné zhoršení
helperem. Sedm ostatních párů je `NOT_COMPARABLE` a má procenta `null`.

Offline kontrola souhrnu ověřila 47 existujících control-JSON hashů a sedm
záměrně chybějících vstupů, dvanáct platných cyklů a 72 full/sleep/drift
oken, přesné source mapy a všech 727 CSV buněk. Neprováděla nový raw replay
ani měření. Soukromý SHA-256 `combined-final/aggregate.json`:
`2d4ea2d5c6ea2cce00850715af55250d7107cbf513322b20fae147013b9750e1`.

Společný orientační záznam `meter-functional` již nemá čistou globální
kvalitu: dne 29. 9. 2026 v **15:48:55.241429 UTC** zaznamenal `receipt_gap`
**0,381433084 s** mezi rámci **141576 → 141577**, tedy nad předem stanoveným
limitem 0,2 s. Finální summary uzavírá záznam v **16:11:16.452026 UTC**:
**700160 recording vzorků**, 175040 recording rámců, jeden gap a nula
nevalidních/CRC-chybných rámců. `capture_result=PASS`, `stop_reason=stop_file`
potvrzují řízené ukončení; `data_quality=DEGRADED` a celkový `result=DEGRADED`
znamenají, že nejde o čistý globální podklad úplné energie. Finální health
má fázi `finished`. Srovnávací profily používají vlastní oddělené capture.
Tento výpadek doručení měřicích rámců sám neprokazuje funkční chybu Pica;
75minutový funkční test následně dokončil PASS. Limity ani zmrazené zdroje
se kvůli události nemění.

Předem připravený plán požadoval po třech 300s cyklech; A a C je dokončily,
B-LS a obě reference skončily při prvním intervalu:

- A: kandidát `time.sleep_ms()` → reset, profil never;
- B: kandidát `lightsleep()` → reset, profil never;
- dvě oddělené B kontroly původního upstream deepsleep, bez a s TinyUSB opravou;
- C: kandidát deepsleep zvlášť never a STA bez připojení;
- C + veřejný radio/VSYS helper: samostatně označený STA běh po SLEEP ACK.

Displejová příprava byla shodná ve všech variantách. Primární celý cyklus je
první READY receipt(k) → první READY receipt(k+1), tedy tři uzavřená okna
ze tří sleep cyklů včetně ACK čekání, bootu a panelové/radio přípravy.
Samostatné sleep okno je předem stanoveno na SLEEP ACK-flush +60 až +280 s,
s drift podokny 60–120, 120–180, 180–240 a 240–280 s.

JT-UM120 měří USB vstup **celé připojené sestavy**, nikoli samotný RP2350.
Čtyři vzorky rámce sdílejí host timestamp přijetí; přístroj v použitých
podkladech neposkytuje individuální device timestamps. Primární aproximace
energie integruje frame mean(U×I) trapezoidálně podle host receipt, s lineárním
ořezem na hranách a bez překlenutí nevalidního rámce nebo mezery nad 0,2 s.
Druhý model používá předpoklad 100 Hz, 10 ms na přijatý vzorek, pouze jako
citlivost výsledku na model. Rozdíl není interval nejistoty ani kalibrace.

Nuly a špičky se nefiltrují, no-load offset se automaticky neodečítá. Podklady
obsahují mean, min/max, trend, napětí a skutečné pokrytí. Mediány/percentily
streaming analyzátor nepočítá. Kompletní energii lze publikovat jen při
coverage/CRC/density PASS příslušného okna a globálním PASS capture analýzy;
DEGRADED logy a integrály zůstávají diagnostikou. Nominální rozlišení 10 µA
neprokazuje absolutní přesnost a krátké proudové špičky mohou uniknout.

## Samostatná RAM sonda lightsleep — čtyři pozorování

Po závěrečném smoke kandidáta byla provedena jedna předem daná čtyřbuněčná
sonda `ls-matrix-1`, uzavřená v **18:22:32.847970 UTC**. Po každém skutečném
host ACK následovalo buď žádné dodatečné čekání, nebo 200 ms klidu, případně
stejný RTC seed jako ve veřejném harnessu, stejné čtení RTC v obou větvích
a právě jedno `machine.lightsleep(2500)`. Pořadí nebylo náhodné ani opakované:

| Pořadí | Nový RTC seed | Klid po ACK před přípravou měření | Naměřená délka lightsleep podle `ticks_ms()` |
| --- | --- | ---: | ---: |
| 1 | ne | 0 ms | **40 ms** |
| 2 | ano | 0 ms | **40 ms** |
| 3 | ne | 200 ms | **2500 ms** |
| 4 | ano | 200 ms | **2500 ms** |

V těchto čtyřech konkrétních pozorováních se oba krátké návraty objevily
bez přidaného klidu; oba pokusy po 200 ms trvaly požadovaných 2500 ms,
a to s RTC seedem i bez něj. **Každá buňka měla jediný pokus.** Výsledek je
`execution_result=COMPLETE`, ale `hardware_result=OBSERVATION_ONLY`:
neidentifikuje konkrétní přerušení ani neprokazuje jeho příčinu. Pořadí,
předchozí stav a transport nebyly replikací či náhodným pořadím odděleny.
Není to opakování cílového 300s testu, oprava firmware ani důvod přepsat
kterýkoli z dřívějších funkčních FAIL na PASS. Do měřicího harnessu se
kvůli této sondě nepřidalo čekání ani jiný workaround.

Sonda nepožadovala reset, nezapisovala soubory desky ani nevolala rádio.
Zaznamenala jedinou RAM payload exekuci, čtyři jedinečné ACK a zachovaný
nonce, inventář a všechny tři backup regiony; cleanup skončil bez chyb
a friendly REPL byl ověřen. RTC bylo obnoveno ze vstupní hodnoty plus
uplynulého host času, se sekundovou kvantizací; nejde o dokončenou obnovu
původní aplikace ani počátečního stavu celé měřicí akce. Identita sondy
ověřuje runtime a CDC zařízení, nikoli úplnou USB topologii, a její BIN hash
je provenience očekávaného artefaktu, nikoli nové čtení flash.

Nezávislá offline kontrola ověřila host/payload SHA, šest zdrojových hashů,
pořadí záznamů/ACK, shodu veřejných čtyř výsledků se soukromými událostmi
a zaznamenané vstupní/výstupní invarianty. SHA-256 veřejného výsledku sondy:
`6a880e1942e5369a008c6aea7aeebfabbbf8f27cda3e87fd4ebbb58b96eac707`.

## Obnova a konečný stav

**Poslední obnova PASS v 19:24:45.235838 UTC.** Po druhém pokusu a potvrzení, že Pico je znovu
připojené a už nebude odpojované, proběhla kontrola identity, přesného guardu,
vypnutého watchdogu, původních souborů a skutečných kandidátních BIN bajtů.
Všech **29 původních souborů** souhlasí velikostí a SHA-256; obnoveno a
ověřeno **7 adresářů včetně root** a všechny tři retenční regiony.
Odstraněny byly pouze evidované testovací soubory; původní `main.py` se vrátil
jako poslední filesystemová změna. RTC a všechny tři retenční regiony byly
obnoveny z čerstvého stavu zachyceného před druhým pokusem; k RTC byl přičten
uplynulý monotonic čas hostitele. RTC má sekundovou kvantizaci, interval
čtení uloženého výchozího RTC byl 0,037743 s. První obnova z 19:08:29 UTC
zůstává samostatným historickým důkazem.

Na desce zůstává **candidate-91e91**, runtime
`v1.30.0-preview.104.g91e91d58de.dirty`, BIN SHA-256
`0c8c1b0439fa050e1bf30c7f586f5deeb5e53b202b91877e30840411148ad12b`.
Rádio a Bluetooth jsou neaktivní, panel byl znovu připraven bez překreslení
a ověřeně uspán/parkován. Watchdog je vypnutý. Původní aplikace nebyla
spuštěna; Pico zůstalo ve **friendly REPL**, sériový klient byl uzavřen.
Po obnově nebyl proveden reset ani import aplikace. **Příští běžný reset
již spustí původní aplikaci.**

[Veřejný výsledek poslední obnovy](evidence/mac-20260929-meter/no-load-final2/restoration.json)
je samostatným novým důkazem. Nepřepisuje dřívější `candidate_restored=false`
v uzavřené sekvenci `cmp300deep` ani žádný ze tří RTC continuity FAIL.

Nový obraz „B: METER REVIEW OK“ a černý obdélník vpravo uživatel výslovně
potvrdil. V prvním pokusu `final1` také potvrdil odpojení pouze Pica
a zachování měřáku i hubu.
Tato odpověď ale přišla až po uzavření záznamu: watcher skončil
**FAIL v 18:39:02.953501 UTC**, fáze `READY_TO_UNPLUG`, timeout bez
zaznamenané USB absence. Collector byl řízeně ukončen přes stop-file
v **18:39:26.106012 UTC**: 21880 vzorků, capture/data quality PASS,
žádné nevalidní/CRC rámce ani mezery nad 0,2 s. Bez odpovídajícího
časového okna nelze pozdní potvrzení spojit s platným no-load měřením.
**No-load analýza zůstává NOT_RUN; žádný offset nebyl odečten.**

## Druhé měření bez Pica — ověřený diagnostický úsek

Na nový pokyn uživatel odpojil pouze Pico, ponechal měřák i jeho PC kabel
a hub zapojené, poté Pico normálně připojil a potvrdil tuto manipulaci.
Pokus `final2` měl vlastní čerstvou kontrolu identity/BIN, zálohu aktuálního
mainu/RTC/retenčních regionů a ověřený guard. Příprava skončila PASS
v 19:21:23.682296 UTC. Původní soubory a adresáře souhlasily se zálohou.

Watcher zaznamenal 274 pollů, z toho 132 souvislých úplných absencí Pica;
největší odstup pozorování byl 0,357275 s. Čtení měřáku však skončilo
`OSError: read error`. Výsledkem celého capture je **ERROR**, s 10848
zachycenými vzorky, nulou CRC chyb a nulou mezer nad 0,2 s v zaznamenaných
datech. Watcher skončil **FAIL v 19:23:28.419089 UTC**, ve fázi
`ABSENCE_OBSERVED`, protože meter health již nebyl `recording`.
Úspěšný návrat USB před ukončením watcher nedoložil. Příčina chyby HID
není určena; nejde o důkaz závady Pica nebo o přepsání spánkových výsledků.

Ze souvisle pozorované absence byl následně vytvořen samostatný
**POST_HOC_DIAGNOSTIC**: začátek je konec prvního úplně absentního pollu
+5 s, konec je začátek posledního potvrzeného absentního pollu −5 s.
Meze byly odvozeny z topologie, nikoli z hodnot proudu. Jde o jiné,
konzervativní vnitřní okno než původní pravidlo s doloženým návratem USB.

| Údaj v diagnostickém okně bez Pica | Nový výsledek |
| --- | ---: |
| Interval UTC | 19:22:50.281498–19:23:23.081187 |
| Délka | 32,799783292 s |
| Vzorky / měřicí rámce | 3280 / 820 |
| Průměr indikovaného proudu | **0,0514116 mA = 51,4116 µA** |
| Minimum / maximum | **0,030 / 0,070 mA** |
| Přesně nulové vzorky | 0 |
| Průměrné napětí | 5,082409 V |
| Kontrola vnitřního okna | coverage/CRC/density **PASS** |

Původní připnutý parser znovu zpracoval všechny raw rámce, CRC i všechny
odvozené vzorky a ověřil shodu se souhrnem bez změny jeho ERROR stavu.
Koherence hodin watcheru a měřáku prošla. Nezávislý přepočet rootem dává
stejný počet vzorků, délku, průměr i extrema. Fyzické potvrzení uživatele
patří k tomuto novému pokusu; neodvozuje se ze samotné USB absence.
[Diagnostický důkaz](evidence/mac-20260929-meter/no-load-final2/posthoc-diagnostic.json)
a samostatná fyzická odpověď jsou oddělené od výsledku celého capture.

**Hodnota 51,4 µA je indikace v odpojené sestavě, nikoli ověřená kalibrace
nuly nebo absolutní přesnosti.** Nic nebylo odečteno od dříve naměřených
přibližně 0,373 mA ve spánku, nuly ani špičky nebyly filtrovány. Původní
standardní no-load analýza zůstává **NOT_RUN**, celý pokus nemá PASS.
Po měření proběhla výše doložená poslední obnova PASS v 19:24:45 UTC.

## Veřejný evidence export — konečný stav

Byl vytvořen skutečný anonymizovaný snapshot `public-evidence-final2`:
**252 souborů, přibližně 2,92 MB**, 251 ověřených checksumů (soubor
`SHA256SUMS` nezahrnuje sám sebe). Exportér a kontrakt prošly offline
testy a nezávislým review; allowlist a kontrola soukromých údajů prošly.
Předchozí průběžné snapshoty zůstávají soukromě zachované.
Aktualizovaný adresář v repu je
`experiments/rp2350-deepsleep/evidence/mac-20260929-meter/`.
Export zachovává skutečné FAIL a pending stavy; jeho úspěch není potvrzením
obnovy desky ani úplného úspěchu experimentu a nezakládá upstream PR.

| Veřejný podklad | Obsah a anonymizace |
| --- | --- |
| setup/build manifest | Dnešní potvrzená sestava, platforma, revize, nástroje a firmware hashe; vynechat místní absolutní cesty a identifikátory zařízení |
| backup/guard verification | PASS, počty, velikost flash, způsob nezávislého ověření a preserve kontroly; žádná flash data, originální aplikace/config ani backup slova |
| scénáře a výsledky runů | Skutečné configy bez secrets, timeouty, úplné anonymizované protokolové sekvence, souhrny PASS/FAIL/NEPROVEDENO; UID nahradit stabilním označením `test-board-2` |
| watchdog preparation | Selektivní before/after CTRL/REASON/cause, obyčejný reset a jeho výsledek; odstranit UID, RTC baseline a hodnoty backup slov |
| wrapper provenance | Přesné zdroje/hashe veřejného harnessa, panel prefixu, emit hooku, pinned vendor driveru a případného odděleného helper hooku; bez private app zdrojů |
| meter evidence | Uzavřené metadata/summary/health a SHA-256 soukromých raw HID frames, decoded samples a events; objemné raw zůstávají lokálně, žádné HID device paths/serial ani konfigurace uživatele |
| analýza a grafy | Anonymizované protokolové hranice, stejné předem určené modely/okna, coverage a všechny nedokončené/DEGRADED výsledky; samotné grafy nenahradí raw důkaz |
| no-load | Zachované final1 FAIL/timeout a final2 FAIL/capture ERROR; samostatná post-hoc diagnostika vnitřního odpojeného úseku, standardní analýza NOT_RUN, bez odečtu |
| display / restore | Elektronický render PASS, nové fyzické USER_CONFIRMED a samostatná obnova PASS; 29 souborů, 7 adresářů, RTC a všechny retenční regiony ověřeny |

Export používá výslovný allowlist polí, nikoli jen plošnou náhradu jedné UID.
Kontroluje vnořené JSON, chybové výpisy, non-test serial řádky, build cesty
a USB/HID identifikátory. Neobsahuje `original-files`, plné flash/FS obrazy,
instalátorem zachycený původní main, `initial-state-private.json`, syrové
soukromé konfigurace ani credentials. Veřejné serial logy zachovávají
povolené protokolové markery/časy s přiznanou anonymizací; nepřezkoumaný
konzolový obsah se nepřenáší. Objemné soukromé raw záznamy zastupují hashe;
jejich úplné přehrání nebylo úlohou exportéru.

SHA-256 veřejných souborů byly vytvořeny **po anonymizaci**; manifest uvádí
vazby na soukromé zdrojové hashe. Původní místní logy zůstaly beze změny.
Zpráva popisuje skutečné uzavřené pokusy, nové potvrzení obrazu a dokončenou
obnovu. Neúspěšné reference a chybějící dokončený no-load pokus zůstávají omezením
výsledků. Vnitřní diagnostické okno ani dokončení obnovy je nepovyšují na PASS.

### Soukromé zdroje této zprávy

`setup-public.json`, `initial-read-public.json`, `initial-full-backup/result.json`,
`offline-guard/result.json`, `original-directories.json`,
`candidate-first-flash/result.json`, `guard-reset-private.json`,
`artifacts/*/build-manifest.json`, `staging/provenance.json`,
`runs/candidate-smoke3/*`, `runs/candidate-cycles100/*`,
`runs/candidate-long30/*`, `runs/candidate-long75/*`,
`functional-sequence-public.json`, `measurement-plan.md`,
`meter-functional/events.jsonl` (událost receipt_gap), `meter-functional/summary.json`,
finální `meter-functional/health.json`, `measurements/cmp300/result.json`,
`startup-cadence-review.json`, oba `measurement-source-freeze*.json`,
`measurements/cmp300v2/result.json`, výsledky profilů A/B-LS,
`runs/cmp300v2-b-lightsleep-reset/events-private.jsonl`,
`measurements/cmp300cont1/result.json`, `measurements/cmp300cont2/result.json`,
jejich uzavřené B capture summary a `runs/cmp300cont2-b-lightsleep-reset/result-public.json`,
`comparison-startup-cont2-review.json`, `comparison-deep-continuation-review.json`,
uzavřené `measurements/cmp300deep/03-c-deepsleep-never/{result.json,analysis/analysis.json,meter/summary.json,meter/health.json}`,
uzavřené `measurements/cmp300deep/04-c-deepsleep-sta/{result.json,analysis/analysis.json,meter/summary.json,meter/health.json}`,
uzavřené `measurements/cmp300deep/05-c-helper-sta/{result.json,analysis/analysis.json,meter/summary.json,meter/health.json}`,
`measurements/cmp300deep/result.json`,
`firmware-switches/cmp300deep-switch-vanilla/result-private.json`,
`runs/cmp300deep-c-deepsleep-never/result-public.json`,
uzavřený `measurements/cmp300deep/progress.json`,
`reference-guard-vanilla/result-public.json`, `reference-guard-usbq/result-public.json`,
`reference-review-vanilla.json`, `reference-review-usbq.json`,
`measurement-source-freeze-refvanilla.json`, `measurement-source-freeze-refusbq.json`,
uzavřené `measurements/cmp300refvanilla/06-b-upstream-vanilla/`
a `measurements/cmp300refusbq/07-b-upstream-usbfix/` (jen vybrané control JSON),
jejich samostatné výsledky sekvencí a veřejné suite výsledky,
`combined-final/{aggregate.json,profiles.csv,cycles.csv,comparisons.csv,excluded-B-attempts.csv,README.cs.md}`,
`runs/candidate-final-smoke/{config.json,result-public.json}`,
`final-display/result-public.json`,
`lightsleep-matrix/preparation-result.json` a `lightsleep-matrix/runs/ls-matrix-1/`
(veřejný výsledek, soukromá provenience a události pro interní QA).
Tyto relativní odkazy/názvy slouží internímu review; nejsou pokynem k publikaci
celého soukromého pracovního adresáře.

Nové závěrečné podklady: `restoration/result-public.json`,
`final-display/visual-confirmation-public.json` a
`no-load-runs/final1/late-physical-confirmation-public.json`.

Nový pokus final2: `no_load_guard.py`, `no-load-runs/final2/guard/result-public.json`,
`no-load-runs/final2/restoration/result-public.json`, `no-load-runs/final2/physical-reply-public.json`,
uzavřené watcher/meter záznamy a `final2_diagnostic.py` s
`no-load-runs/final2/post-hoc-diagnostic/{analysis.json,window-plan.json,trace-bins.csv}`.
