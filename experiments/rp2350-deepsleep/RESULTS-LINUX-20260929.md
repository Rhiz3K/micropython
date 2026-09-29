# Pico 2 W na Linuxu — převzetí a omezená validace 29. 9. 2026

Nový ARM firmware se podařilo sestavit, nahrát a ověřit zpětným čtením.
Prošly dvě sady po třech časovaných deepsleep s návratem USB, druhá také
s novým DHCP a ověřeným HTTP přenosem. **Wi-Fi však není spolehlivě vyřešena:**
další dva pokusy skončily bez DHCP adresy, jeden po běžném resetu a druhý
bez dalšího resetu či spánku. USB při těchto selháních fungovalo.
Lokální regrese a závěrečná obnova dat prošly. Konečný stav byl ověřen
**29. 9. 2026 v 06:23:50 UTC**. Tento dokument nepřisuzuje dnešnímu buildu
starší výsledky z jiné desky ani neoznačuje krátkou sadu za ověření 100 cyklů.

Firmware zůstává **experimentální**. Dnes nebyla měřena spotřeba ani energie
cyklu. Úspěšný návrat programu a záznamy POWMAN nejsou náhradou měření proudu.

## Deska, zapojení a ochrana původních dat

Jde o původní linuxovou desku, identifikovanou jako Raspberry Pi Pico 2 W
s RP2350; její runtime UID a USB serial byly ověřeny a zůstávají soukromé.
Nejde o desku z Mac testů. Uživatel potvrdil připojení USB a displeje
**Pico-ePaper-2.9 B/W/R V4**. Označení pochází od uživatele; fyzické
propojky a zapojení nebyly zvlášť ověřeny. Panel nebyl během testů ovládán,
jeho obraz ani uspání se neověřovaly. Helper pro Mac panel B/W V2 nebyl použit.

Před zápisy vznikla čerstvá soukromá záloha celé flash, **4194304 bajtů**,
a filesystemu s **37 soubory**. SHA256 celé flash vypočtené na desce a na
hostiteli se shodují. Byla připravena a obsahově ověřena úplná obnovovací
UF2. Užitečná backup slova, RTC a stav rádia jsou zaznamenané zvlášť.
Zálohy, jejich citlivý obsah a identifikátory zařízení se nezveřejňují.

**Neproběhlo nezávislé ROM ověření pomocí `picotool verify`:** přístup
hostitelského procesu k USB v BOOTSEL omezila oprávnění. Ověření obsahu
obnovovací UF2 na hostiteli s tímto testem nezaměňujeme. Po nahrání kandidáta
naopak prošlo zpětné čtení jeho programové oblasti přes běžící firmware:
SHA256 prvních 889792 bajtů odpovídá novému `firmware.bin`.

Soukromá původní aplikace nebyla upravována. Testy dočasně nahradily
`main.py` a konfiguraci podle opt-in sady. Na konci byla obnovena dnešní
vstupní kopie a ověřena shoda cest, velikostí a SHA256 všech **37 souborů**.
Vstupní `main.py` už byl starší deepsleep testovací harness, nikoli autostart
soukromé aplikace. Tento stav byl zachován: další reset spustí harness,
který čeká na hostitelský příkaz GO, sám se opakovaně neuspává.

## Přesný kandidát a sestavení

| Položka | Hodnota |
| --- | --- |
| Zdrojový commit | `6f95bf43caab2f2ba693cbf91e82214e5b59f874` |
| Poslední implementační commit | `0f193e89cbb0246ca4d967e1ad98db28304a031c` |
| Board / platforma | `RPI_PICO2_W` / `rp2350-arm-s`, `MinSizeRel` |
| Pico SDK | `98a542c1a62fb549ffb5d66a3e5892b06276b670` |
| TinyUSB gitlink | `b549ac1d84cbbe550c9590951e2290098b3fb16c` |
| Lokální TinyUSB oprava | [tinyusb-ep0-queue.patch](tinyusb-ep0-queue.patch), upstream `a0249ada9096365697340031a7b4a285beb18a2b` |
| SHA256 TinyUSB patche | `ffbadfaa2a51af420e64e1bdb4fad55f1621646eb3bcd98e3d93eaa921076e4e` |
| Picotool pro build | připnutý `6f6458d792b93685a11423b244a585eaa99eafcf` |
| Host | Linux x86_64 |
| Toolchain | Arm GNU Toolchain 14.3.Rel1, GCC 14.3.1 20250623 |
| CMake / GNU Make | 4.4.3 / 4.3 |
| `SOURCE_DATE_EPOCH` | `1790660898` |
| Runtime | `v1.30.0-preview.90.g6f95bf43ca.dirty on 2026-09-29 (GNU 14.3.1 MinSizeRel)` |

TinyUSB oprava byla aplikována v kořenovém `lib/tinyusb`; samotný checkout
větve ji neaktivuje. Šest core souborů a zdroje řadiče USB odpovídají
zaznamenanému Mac kandidátu. Oprava počítadla zahozených SETUP událostí
nepřidává povinné zpoždění USB detach ani změnu USB API. Její vztah k
původnímu linuxovému zaseknutí po `trace=7` stále není prokázán.

Oba dnešní buildy `RPI_PICO2_W` a `RPI_PICO` skončily úspěšně; v jejich
build logu nebyl nalezen compiler warning. RP2040 byl pouze sestaven,
nikoli zkoušen na fyzické desce. Výchozí nezměněný upstream se dnes znovu
nesestavoval; jeho dřívější výsledky jsou v [původním záznamu](RESULTS.md).

Reprodukce vyžaduje plný Arm toolchain v `PATH`, odpovídající
`PICO_TOOLCHAIN_PATH` a checkout uvedeného commitu. Inicializaci submodulů
a kontrolu/aplikaci samostatné USB opravy popisuje [handover](HANDOVER.cs.md).
Po této přípravě byly použity následující parametry:

```sh
export PICO_SDK_PATH="$PWD/lib/pico-sdk"
unset MICROPY_GIT_TAG MICROPY_GIT_HASH BOARD_VARIANT PICO_PLATFORM USER_C_MODULES FROZEN_MANIFEST
export CMAKE_ARGS='-DPICO_DEFAULT_RP2350_PLATFORM=rp2350-arm-s -DCMAKE_BUILD_TYPE=MinSizeRel -DPICOTOOL_GIT_BRANCH=6f6458d792b93685a11423b244a585eaa99eafcf -DPICOTOOL_FORCE_FETCH_FROM_GIT=1'
export SOURCE_DATE_EPOCH=1790660898
export TZ=UTC
export LC_ALL=C
make -C mpy-cross -j6
make -C ports/rp2 BOARD=RPI_PICO2_W BOARD_VARIANT= BUILD=build-linux-20260929-usbq1 -j6
make -C ports/rp2 BOARD=RPI_PICO BOARD_VARIANT= BUILD=build-linux-20260929-rp2040 -j6
sha256sum ports/rp2/build-linux-20260929-usbq1/firmware.{uf2,bin,elf}
```

| Artefakt | Bajtů | SHA256 |
| --- | ---: | --- |
| `firmware.uf2` | 1780224 | `ac9dd70af30cd96d6250d6d4b539cdd2baad12672db94b238691b0720902a721` |
| `firmware.bin` | 889792 | `77aea5317b92dae8bc486911170e2f7d4a27cb564d33bb116d14689f6ca2f32a` |
| `firmware.elf` | 8653016 | `26dfaffbc72e158d073ab4b55cb469097f2c148e03ede8061d58be974044337b` |

## Dokončené USB a deepsleep kontroly

Tři samostatná `machine.reset()` vedla k novému příchodu USB, úspěšnému
vykonání REPL dotazu, shodné identitě/verzi a reset cause 3. Hostitelské
intervaly do ověřeného USB/REPL byly přibližně 0,98 s, 0,58 s a 0,78 s.
Tyto časy zahrnují hostitelský postup; nejsou měřením samotného bootu MCU.

Sada `linux-20260929-minimal3` použila `radio_mode: never` a třikrát
`machine.deepsleep(2500)`. Každý návrat měl cause 4,
`POWMAN_CHIP_RESET = 0x02000000`, `POWMAN_LAST_SWCORE_PWRUP = 64`
a nový běh programu. Tyto záznamy dokládají vypnutí SWCORE a alarmový návrat,
nikoli nezávislé měření všech SRAM/XIP domén. Prošly kontroly POWMAN backup
regionu 2 a souborového sentinelu. V každém watchdog backup regionu 0 a 1
chyběla alespoň část zapsaného vzoru; log netvrdí, že všechny registry byly nulové.

RTC mezi uložením času a návratem ukázalo 2, 3 a 3 celé sekundy. První
cyklus přešel přes minutu a půlnoc. Test záměrně nastavuje RTC na
**25. 9. 2026 23:59:58**; datum v záznamech proto není skutečným datem
tohoto měření. Kontrola v celých sekundách nehodnotí přesnost LPOSC.

Po třetím alarmovém probuzení následoval samostatný běžný reset: konečný
záznam měl `completed: 3`, `status: PASS`, cause 3, přestože historický
`LAST_SWCORE_PWRUP` stále obsahoval 64. To ověřuje životnost rozlišení
deep wake. Dokončené sady v této části tedy představují **3 deep wake a
4 běžné resety**, nikoli sedm hlubokých spánků.

## Wi-Fi — dokončená základní sada a chyba hostitelské fixture

První verze hostitelské sondy provedla jednu úspěšnou DHCP/HTTP transakci
a jedno úspěšné řízené vypnutí rádia helperem. Po požadavku deepsleep
selhala při zavírání hostitelského sériového spojení výjimkou `BrokenPipe`.
Tento běh je **FAIL hostitelské fixture** a nesmí se vydávat za úspěšně
dokončenou celou sadu ani za prokázané selhání probuzení desky.

USB se po tomto pokusu vrátilo; následná nezávislá sonda ověřila cause 4.
Tento dílčí návrat je zaznamenaný zvlášť a nepřičítá se k dokončené
základní sadě tří cyklů. Nová verze `wifi_recovery.py` ošetřuje zavření
transportu po restartu a dokončila **3/3 deep wake po 2500 ms a 4/4
DHCP/HTTP transakce**. Každé probuzení potvrdilo USB/REPL, cause 4 a
odpovídající záznamy POWMAN. HTTP kontrolovalo přesné očekávané tělo
odpovědi. První seed transakce a návrat z neúplné v1 zůstávají oddělené
od těchto počtů.

Oprava fixture nepřepisuje původní FAIL. Použití řízeného odhlášení
v této sondě není důkazem, že samotný core `machine.deepsleep()` vyřešil
opakovaná spojení. DNS, TLS a kompletní soukromá aplikace dnes ověřeny nebyly.

### Dvě skutečná selhání DHCP

Samostatná navazující sada nejdříve úspěšně získala DHCP a přesné HTTP tělo,
provedla helper a běžný reset. USB/REPL se vrátilo za 1,345 s s cause 3.
První reconnect však přešel po 3134 ms do status 2 a během 35 sekund
nezískal DHCP adresu. HTTP se vůbec nespustilo. Sada se na první chybě
zastavila; další dva běžné resety a všechny tři plánované lightsleep/soft-reset
cykly jsou NEPROVEDENO.

Připnutý `lib/cyw43-driver/src/cyw43_lwip.c` vrací status 2 při aktivním
netif/linku a nulové IPv4 adrese. `isconnected() == False` zde neznamená
důkaz neúspěšné asociace nebo chybného hesla. Jde o selhání fáze získávání
adresy; přesná chybějící DHCP zpráva a příčina nebyly určeny.

Následná samostatná sonda bez resetu znovu prošla: DHCP za 3147 ms a přesné
HTTP tělo. Další oddělený pokus o sadu lightsleep však selhal již v úvodním
připojení, opět status 2 / bez DHCP po 35 sekundách. **Při druhém selhání se
žádné lightsleep ani soft reset neprovedlo.** Ani řízené vypnutí rádia tedy
na této síti nezaručuje další úspěšné spojení. Jednotlivý úspěšný recovery
není opravou příčiny; automatické opakování tyto FAIL nepřekrylo.

Read-only kontrola MikroTiku ukázala dříve vytvořený bound lease s
`last-seen=1m54s`, nikoli důkaz nového úspěšného DHCP handshake. Výpis
varování obsahoval starší události končící 24. 9.; nepotvrdil dnešní příčinu
ani konflikt adres. Prázdná registrační tabulka vznikla během rané fáze
pozdějšího recovery, ne během původního selhání. Konfigurace routeru se
neměnila a podrobné `trace=7` se nezapínalo. Paketový záznam DHCP nevznikl.

Součet dnešních síťových sond: **9 zahájených pokusů, 7 úspěšných DHCP/HTTP
transakcí, 2 selhání získání adresy**. Původní hostitelský `BrokenPipe` je
další samostatná chyba orchestrace, nikoli třetí síťové selhání. Alarmových
návratů bylo šest v dokončených kontrolovaných sadách a jeden navíc později
ověřený po chybě v1. Běžných resetů s potvrzeným návratem USB bylo celkem pět.

## Regrese a konečný stav

Existující `tests/ports/rp2/deepsleep/regressions.py` byl proveden beze změn
v RAM: šest odmítnutí záporných/přetékajících argumentů, odmítnutí volání
z hard IRQ s EBUSY a návrat frekvence 100 MHz i běh času po lightsleep prošly.
Frekvence se následně vrátila na původních 150 MHz. Tato kontrola lightsleep
nenahrazuje neprovedené Wi-Fi/lightsleep/soft-reset cykly.

Po testech se obnovily všechny tři uživatelské backup regiony a RTC na původní
čas při převzetí plus uplynulý hostitelský čas. Původní RTC mělo rok 2021;
nešlo o synchronizaci skutečného data 2026. Všechny původní soubory odpovídají
záloze. Nový experimentální firmware zůstal nahraný podle dřívějšího přání
uživatele. Deska zůstala v ověřeném friendly REPL, watchdog a STA/AP jsou
vypnuté, helper ověřil GP23 a GP25 jako výstupy LOW. Panel nebyl uveden do
ověřeného sleep stavu a deska nyní není v deepsleep.

## Stav kontrol

| Kontrola | Stav | Rozsah |
| --- | --- | --- |
| Identita Pico 2 W / ARM | PASS | UID a runtime ověřeny soukromě |
| Čerstvá plná flash a filesystem záloha | PASS | 4 MiB, 37 souborů; shoda hashů flash na hostu a desce |
| Obnovovací UF2 | PASS | Ověřen obsah na hostiteli; ne ROM čtení |
| Nezávislé `picotool verify` zálohy v BOOTSEL | NEPROVEDENO | Omezení USB oprávnění |
| Build Pico 2 W ARM | PASS | Nový lokální kandidát uvedený výše |
| Build RP2040 / RPI_PICO | PASS | Pouze sestavení |
| Programová oblast po flashování | PASS | Readback SHA256 shodný s novým BIN |
| Samostatné běžné resety a USB/REPL | PASS | 3/3 |
| Časovaný deepsleep a nový start | PASS | Základní sada 3/3 × 2500 ms |
| USB komunikace po deep wake | PASS | Základní sada 3/3; samostatné raw REPL dotazy také v další Wi-Fi sadě |
| RTC přes minutu a den | PASS | Jeden úmyslný přechod přes půlnoc v základní sadě |
| POWMAN region 2 a souborový sentinel | PASS | Kontroly při všech třech návratech; nejde o kontrolu všech souborů |
| Běžný reset po deep wake | PASS | Cause 3, bez chybného opakování cause 4 |
| První Wi-Fi hostitelská fixture | FAIL | `BrokenPipe` při close; 1 DHCP/HTTP a 1 helper před chybou prošly |
| Wi-Fi sada po opravě fixture | PASS | 4/4 DHCP a přesné HTTP tělo; 3/3 deep wake, USB/REPL, cause 4 |
| Wi-Fi přes běžný reset | FAIL | USB/REPL a seed prošly, první reconnect bez DHCP; další dva cykly NEPROVEDENO |
| Samostatný recovery bez resetu | PASS | 1 DHCP/HTTP; původní FAIL zůstává |
| Úvodní spojení oddělené lightsleep sady | FAIL | Bez DHCP ještě před spánkem/resetem |
| Wi-Fi přes lightsleep + soft reset | NEPROVEDENO | Ani jedna plánovaná dvojice se nespustila |
| Konečný úklid a kontrola původního filesystemu | PASS | Shoda všech 37 souborů, backup registry a RTC obnovené, friendly REPL ověřen |
| Nových 100 krátkých cyklů na dnešním buildu | NEPROVEDENO | Dřívější běhy se nepřenášejí |
| 30 a 75 minut na dnešním buildu | NEPROVEDENO | Starší Mac výsledky patří jinému sestavení |
| Regresní skript `regressions.py` | PASS | 6 argumentů, hard IRQ a lightsleep frekvence/čas |
| Nové samostatné sady watchdogu, core1 a DMA | NEPROVEDENO | Nejsou součástí této omezené sady |
| Nové DNS/TLS, AP/BLE přenosy, celá aplikace | NEPROVEDENO | Dílčí HTTP není jejich náhradou |
| Funkce a uspání displeje | NEPROVEDENO | Uživatel uvedl B/W/R V4; bez ovládání či vizuální validace |
| Fyzické Pico 2 bez Wi-Fi a RP2040 | NEPROVEDENO | Žádný nový hardware výsledek |
| RISC-V build a hardware | NEPROVEDENO | Nová P1.7 cesta zůstává omezena na ARM |
| Proud, energie cyklu a A/B/C porovnání | NEPROVEDENO | Dnes bez měření |

## Důkazy a zbývající kroky

Redigované výsledky jsou v [evidence/linux-20260929](evidence/linux-20260929/).
Původní záznamy, build logy, přesné lokální host skripty, záloha flash,
filesystem a síťové údaje zůstávají soukromé. Veřejná síťová sonda je stejná
[wifi_device.py.txt](evidence/mac-20260928-usb-wifi/wifi_device.py.txt), načítaná
spolu s helperem pouze do RAM; přihlašovací údaje se nezapisovaly do testovací
konfigurace na desce. Zveřejněné hashe firmwaru nejsou hashe soukromé zálohy.

Další síťová práce má zachytit konkrétní DHCP výměnu a klientský stav při
status 2, odděleně od USB a power-down. Teprve s doloženou příčinou navrhovat
opravu či další kontrolovaný recovery zásah. Pro panel V4 je potřeba ověřit
vlastní ovladač, pinout a sleep sekvenci, nikoli použít B/W V2 helper.
Následují chybějící širší a dlouhé testy a nové měření proudu/energie.
Veřejný upstream PR nebyl v rámci tohoto převzetí založen.
