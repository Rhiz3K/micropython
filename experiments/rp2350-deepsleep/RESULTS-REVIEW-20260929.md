# Ověření code review a opravy, 29. 9. 2026

Potvrzené chyby byly opravené a nový ARM kandidát byl nahrán do původního
linuxového Pico 2 W. **Jde stále o experimentální firmware: v této sadě
neproběhlo měření proudu ani energie, nové Wi-Fi testy ani dlouhý spánek.**
Předchozí výsledky a neúspěchy se nepřepisují.

## Co z review platí

| Nález | Ověření a výsledek |
| --- | --- |
| Pull-up GP23 během každého deepsleep | Tvrzení je příliš silné. SDK při inicializaci pull-up zapíná a `gpio_init()` jej nemaže, ale úplný `cyw43_deinit()` volá `cyw43_init()` a MicroPython HAL oba pulls odstraní. Větev s `cyw43_poll == NULL` končí dříve. Explicitní `gpio_disable_pulls()` je přidané jako zajištění konečného stavu i pro tuto cestu; není doložený nový pokles proudu. |
| Nadpis quickref 41 znaků / 40 pomlček | Potvrzeno: Sphinx před opravou FAIL, po opravě PASS se stejným `-W`. Nadpis opravený, detailní výčet krajních argumentů zkrácený. |
| Poškozené JSON z USB ukončí hostitele | Opraveno. Neplatný záznam se zaznamená bez ACK a bez prodloužení timeoutu; odpojený fragment se zahodí. |
| Watchdog může skončit falešným PASS | Opraveno. Úspěšná fáze se nastaví až po EBUSY; reset předtím v nové fázi 8 znamená FAIL. |
| Záporný argument na starém RP2 firmwaru může čekat přibližně 49 dní | Opraveno. Ručně spouštěná regrese vyžaduje RP2, RP2350 a podmíněný export `DEEPSLEEP_RESET`, jinak skončí výjimkou před prvním uspáním. Není ještě převedená na upstream runner s `SKIP`/`.exp`. |
| Historické patche sestavují starý kandidát | `firmware.patch` a `tests.patch` skutečně odpovídají `3fc3f9431`; zůstávají historické. `reproduce.sh` teď bez `--historical-20260925` odmítne pokračovat. `combined-upstream.patch` už před review odpovídal tehdejšímu HEAD; nyní je aktualizovaný znovu. |
| TinyUSB není aplikovaný pouhým klonováním | Potvrzeno. Nový `prepare-tinyusb.sh` aplikuje přesnou uloženou opravu nebo ověří její úplnou shodu. Odmítá cizí změny; gitlink se nemění. Součástí výsledku je výslovný krok přípravy, nikoli tvrzení, že samotný clone stačí. |
| Opakované započtení probuzení po Ctrl-D | Opraveno spotřebováním fáze před zvýšením čítače. Další soft reset skončí FAIL, nikoli novým cyklem. |
| Ztracené SLEEP / kruhová kontrola RTC | Protokol 2 opakuje SLEEP do samostatného ACK pro konkrétní run/boot/status. Hostitel ověřuje celý sled a monotónní čas. Ten zahrnuje boot, USB a případně síť; pomalý boot může zakrýt časné probuzení. Není to měření délky P1.7 ani kalibrace oscilátoru. |
| Trvale ignorované debug power request | Potvrzeno a opraveno: při startu se `DBG_PWRCFG.IGNORE` vrací na false. Na hardware po alarmovém probuzení načteno `DBG_PWRCFG=0`. |
| Magické `1 << 6` | Pojmenováno `RP2_POWMAN_ALARM_PWRUP_MASK` s komentářem k bitové hodnotě `0x40` pozorované na hardware. |
| LPOSC údajně nemá kalibraci | Připnuté SDK již v `powman_timer_set_1khz_tick_source_lposc()` používá dostupnou platnou OTP kalibraci. Není tím prokázaná přesnost aktuální desky. Nové měření proti XOSC nebylo přidáno. |

Zdrojová kontrola GP23 zahrnula `cyw43_bus_pio_spi.c`, `hardware_gpio/gpio.c`,
`cyw43_ctrl.c` a `ports/rp2/mphalport.h`, nikoli jen samostatné `gpio_init()`.
[SDK POWMAN implementace](https://github.com/raspberrypi/pico-sdk/blob/98a542c1a62fb549ffb5d66a3e5892b06276b670/src/rp2_common/hardware_powman/powman.c)
určuje skutečné chování LPOSC API. Registry a napájecí domény popisuje
[RP2350 datasheet](https://datasheets.raspberrypi.com/rp2350/rp2350-datasheet.pdf).

## Doplněná oprava životnosti wake příznaku

POWMAN záznamy o vypnutí SWCORE a zdroji jeho zapnutí jsou read-only a
přežívají další reset samotného jádra. Přitom SYSRESETREQ maže watchdog reason.
Původní trojice podmínek tedy mohla znovu klasifikovat starý alarm jako nové
probuzení. Finální commit vyžaduje navíc `POWMAN_TIMER_ALARM_BITS` a hned
potom jej stávající init vymaže. Nezabírá žádné slovo `mem_backup`.

Oficiální ROM při bootu maže pouze `PWRUP_ON_ALARM`, alarmový latch zachovává:
[A2](https://github.com/raspberrypi/pico-bootrom-rp2350/blob/fd6104450fa8f55c11c0c9b54dbc69a27537130f/src/main/arm/varm_boot_path.c#L596),
[A3](https://github.com/raspberrypi/pico-bootrom-rp2350/blob/abd9f7bdcda7cdd1c3e10ce4c8e68fa8d9225ef8/src/main/arm/varm_boot_path.c#L618),
[A4](https://github.com/raspberrypi/pico-bootrom-rp2350/blob/c6cdb1711f32c3e34faaebd58618a6d096dbd52e/src/main/arm/varm_boot_path.c#L626).
SDK runtime jej také nemaže; `machine_deepsleep_init()` je první volání
v `main()`. Následující skutečné hardware ověření podporuje tuto zdrojovou
analýzu. Starý firmware nebyl kvůli tomuto testu znovu nahráván, proto zde
nejde o změřené srovnání před/po stejného SYSRESETREQ pokusu.

## Rozsah patche a zdrojové revize

První C commit je `f7f0d0704f7fd6f4442eab00406ea12d04a32a9d`:
šest přidaných a jeden nahrazený řádek v `ports/rp2/modmachine.c`.
Navazující `2445a04bfa2f426e8390b2efaa6450910734e430` přidává spotřebovaný
příznak alarmu do rozpoznání probuzení (čtyři přidané / dva nahrazené řádky).
Testy jsou odděleně v `9b0760c44`, dokumentace v `5f4f0fde9`, příprava buildu
v `de4b5c531`. Celý mechanismus nadále používá POWMAN P1.7: vypne SWCORE,
oba SRAM bloky a XIP cache; AON časovač na LPOSC vyvolá nový ROM boot.
Python heap zaniká, RTC a osm uživatelských POWMAN scratch slov zůstávají.
Napájení celé desky, externí flash a panelu se tím nevypíná.

- Upstream základ a při této kontrole ověřený master:
  `09f5bb447504a058376c62fe991b3613531837e6`.
- Před-review větev: `aef9b009951b9dbf463d809b0015281eebcb608d`.
- První testovaný kandidát: `5f4f0fde963fa53332e41b857327098e7bb09185`.
- Finální nahraný kandidát: `2445a04bfa2f426e8390b2efaa6450910734e430`
  plus přesný TinyUSB patch. Runtime obsahuje `.dirty` kvůli lokálně
  upravenému submodulu; pracovní změny experimentálních receptů nebyly
  vstupem C buildu.
- Pico SDK `98a542c1a62fb549ffb5d66a3e5892b06276b670` (2.3.0), CYW43
  `055d64274b014dd7b1c2fc94d26e8a18face7124`, TinyUSB gitlink
  `b549ac1d84cbbe550c9590951e2290098b3fb16c`.
- Oddělený TinyUSB patch SHA256:
  `ffbadfaa2a51af420e64e1bdb4fad55f1621646eb3bcd98e3d93eaa921076e4e`.

[Core patch](core-upstream.patch) obsahuje jen osm souborů jádra/desek/docs
proti upstream základu (338 přidaných / jeden odstraněný řádek). [Úplný podklad](combined-upstream.patch)
přidává opt-in testy. Ani jeden neobsahuje TinyUSB změnu či `experiments/`;
na tuto větev se znovu neaplikují. Nejde zatím o připravenou historii upstream PR.

## Sestavení a opakování

Linux x86_64: Arm GNU 14.3.Rel1 / GCC 14.3.1 20250623, CMake 4.4.3,
MinSizeRel, ARM Secure. Nejprve prošel **nezměněný před-review kandidát**
Pico 2 W; není to nový kontrolní build neopraveného upstream masteru.
Potom prošly opravené Pico 2 W, Pico 2 a Pico RP2040, bez compiler warnings.
První Pico 2 / RP2040 přelinkování má zdrojový commit `de4b5c531`.
Po následné opravě alarmového příznaku proběhly zcela nové buildy všech tří
konfigurací ze stejného commitu `2445a04bf`, opět bez compiler warnings.

Z nového klonu postupuj podle [handoveru](HANDOVER.cs.md#4-převzetí-zdrojů-a-build-na-druhém-pc).
Pro přesný zdroj dnešního Pico 2 W lze checkoutnout výše uvedený `2445a04bf`,
inicializovat submoduly a spustit `bash experiments/rp2350-deepsleep/prepare-tinyusb.sh`. Toolchain musí být v `PATH`, `PICO_TOOLCHAIN_PATH`
musí ukazovat na jeho kořen a `PICO_SDK_PATH` na SDK tohoto checkoutu.

```sh
export SOURCE_DATE_EPOCH=1790668407 TZ=UTC LC_ALL=C
export CMAKE_ARGS='-DPICO_DEFAULT_RP2350_PLATFORM=rp2350-arm-s -DCMAKE_BUILD_TYPE=MinSizeRel -DPICOTOOL_GIT_BRANCH=6f6458d792b93685a11423b244a585eaa99eafcf -DPICOTOOL_FORCE_FETCH_FROM_GIT=1'
make -C ports/rp2 BOARD=RPI_PICO2_W BOARD_VARIANT= BUILD=build-review-opus-alarm -j6
make -C ports/rp2 BOARD=RPI_PICO2 BOARD_VARIANT= BUILD=build-review-opus-alarm-pico2 -j4
make -C ports/rp2 BOARD=RPI_PICO BOARD_VARIANT= BUILD=build-review-opus-alarm-rp2040 -j4
python3 tests/ports/rp2/deepsleep/test_host.py
python3 experiments/rp2350-deepsleep/tools/test_prepare_tinyusb.py
python3 tools/codeformat.py -c ports/rp2/modmachine.c
make -C docs MICROPY_PORT=rp2 SPHINXOPTS='-W --keep-going -j 4' BUILDDIR=/tmp/rp2350-docs-review-after html
```

Formatter vyžaduje CI balíček `micropython-uncrustify==1.0.0.post1`
(`Uncrustify-373ed72`); docs závislosti jsou z `docs/requirements.txt`.
Při jiném checkoutu/hostu se může lišit vložená verze nebo ELF cesty;
nově vzniklé binárce automaticky nepřiřazuj zdejší hardware PASS.

Finální nahraný `v1.30.0-preview.99.g2445a04bfa.dirty` má:

| Artefakt | SHA256 |
| --- | --- |
| UF2 | `b6eb010e46925f196002de0b9fd865da5107e9a9d8b49c3853577d7108ce53f2` |
| BIN | `1ccc6c9f02a2e48396f7ee8332d9fcb857dbeeab13fc06904968158f476d29d1` |
| ELF | `b4ade24d239c35a89abdddcfa17dc5573720502239dc7eff14c05aad4471ac8f` |

Lokálně jsou v `ports/rp2/build-review-opus-alarm/`. Anonymizované úplné
build/docs logy jsou komprimované v [evidence](evidence/linux-20260929-review/);
[alarm-builds.json](evidence/linux-20260929-review/alarm-builds.json) zaznamenává velikosti,
hashe ostatních buildů, verze a hashe všech zdrojových souborů patche.

Předchozí kandidát a jeho artefakty jsou samostatně v
[builds.json](evidence/linux-20260929-review/builds.json); jeho testy
se nepřenášejí automaticky na finální image.

## Provedené kontroly

Sestava: původní Pico 2 W ARM, USB + uživatelem potvrzený
**Pico-ePaper-2.9 B/W/R V4**, bez připojeného měřidla či debuggeru.
Panel se neovládal. Před zápisem byla znovu ověřená identita, stažená úplná
4MiB flash a všech 37 souborů. Host a nezávisle vypočtený hash na zařízení
se shodují. Obnovovací UF2 byl ověřen po blocích proti záloze.
Nezávislé ROM `picotool verify` neproběhlo; netvrdíme opak.
Přechod do BOOTSEL byl softwarový, následně se ověřil serial/model boot disku.
Po nahrání se hash celé programové oblasti shodoval s novým BIN.

Níže jsou první kontroly `5f4f0fde9`; finální opakování je oddělené pod tabulkou.

| Kontrola první revize | Výsledek | Přesný rozsah |
| --- | --- | --- |
| Build před review, poté tři opravené board konfigurace | PASS | Pico 2 W ARM, Pico 2 ARM, RP2040; Pico 2/RP2040 pouze compile |
| Sphinx quickref s `-W` | FAIL → PASS | Před opravou dvě hlášení krátkého podtržení; po opravě exit 0 |
| C formatter, Python formatter/lint, `mpy-cross`, diff whitespace | PASS | Změněné zdroje; stávající experimentální soubory celé větve nebyly plošně přeformátované |
| Offline testovací protokol | PASS | 21 testů; nejsou důkaz uspání hardware |
| Izolovaná příprava TinyUSB | PASS | 10 Git fixture testů a idempotentní kontrola skutečného checkoutu |
| Historický recept bez explicitního přepínače | PASS | Očekávané odmítnutí exit 2, bez sestavení starého firmwaru |
| Readback nového BIN, samostatný běžný reset, USB/REPL | PASS | Jeden reset, REPL zpět za přibližně 0,691 s |
| 3 × 2500 ms, nový boot, cause, RTC, soubor, POWMAN, USB | PASS | Čtyři READY, tři SLEEP, následný běžný reset/PASS; po alarmu cause 4, po běžném resetu 3 |
| CPU1, aktivní RAM DMA, lightsleep před deepsleep | PASS | Součást každého ze tří cyklů; CPU1 musí dostat EBUSY, pak skončí; DMA se zastaví při teardownu |
| Watchdog EBUSY a skutečný následný watchdog reset | PASS | Jeden WDT reset; žádný deepsleep této sady; PASS fáze až po odmítnutí |
| Soft reset po spotřebovaném probuzení | PASS negativní kontroly | Druhý pokus: jedno alarmové probuzení, Ctrl-D, očekávaný FAIL fáze 7, čítač zůstal 1 |
| První hostitelský pokus soft-reset kontroly | FAIL testovacího postupu | Jedno alarmové probuzení ověřené, pak timeout: `machine.soft_reset()` v raw REPL nespustil `main.py`. USB stále odpovídalo. Nezapočítává se jako dokončená sada |
| Debug požadavky po alarmovém probuzení | PASS | Dvakrát načteno `DBG_PWRCFG=0`; není to zkouška reálného SWD debuggeru |
| Argumenty, hard IRQ, lightsleep frekvence a čas | PASS | Osm kontrol původním regresním zdrojem v RAM; zopakováno po opravě testovacího postupu |
| Obnova uživatelských dat / REPL | PASS | 37/37 souborů byteově, všechny backup regiony, RTC s uplynulým host časem |
| 100 cyklů, 30/75 minut na této revizi | NEPROVEDENO | Historické úspěchy jiné revize jsou v dřívějších reportech |
| Nové Wi-Fi/DHCP/DNS/HTTP, upstream kontrola ve stejné síti | NEPROVEDENO | Starší Linux timeouty zůstávají nevyřešené |
| SWD SYSRESETREQ, RISC-V build/hardware | NEPROVEDENO | RISC-V podpora se netvrdí; chybí vhodný lokální toolchain/debugger |
| Proud a energie celého cyklu | NEPROVEDENO | Žádné nové mA, µA ani mJ; historických 0,37 mA nepřenášet na tento firmware/panel |

Host časy tří cyklů byly 3,857 / 3,852 / 3,831 s od ACK SLEEP do READY,
včetně bootu a USB. RTC celé sekundy: 2 / 3 / 2 s; první cyklus přešel přes
minutu a den. `HAD_SWCORE_PD=1`, alarmový zdroj `0x40`, cause 4 a ztráta
watchdog scratch doplňují důkazy o zvoleném mechanismu. Samotné sticky
registry nestačí: stejné hodnoty zůstaly i po běžném resetu s cause 3.
POWMAN scratch a sentinel prošly. Skript během krátkých cyklů nezapisoval
flash; soubory se měnily jen při instalaci jednotlivých sad a konečné obnově.

## Finální alarmový kandidát `2445a04bf`

| Kontrola finálního firmwaru | Výsledek | Rozsah |
| --- | --- | --- |
| Tři čerstvé buildy a zpětné čtení nahraného BIN | PASS | ARM Pico 2 W, ARM Pico 2, RP2040; na hardware pouze Pico 2 W |
| Tři 2500ms cykly s CPU1/DMA/lightsleep | PASS | Tři SLEEP / čtyři READY / finální PASS; alarm cause 4, ordinary reset cause 3, RTC přes půlnoc, file/POWMAN/USB |
| Alarm → software SYSRESETREQ → ochranný WDT reset | PASS | Příčiny 4 → 1 → 3; čítač zůstal 1, očekávané FAIL fáze 7 po přerušení výsledku. Skutečné SWD nepřipojeno |
| Další alarm po této sekvenci | PASS | Samostatně znovu spuštěná jednocyklová sada: cause 4, poté finální normal-reset PASS/cause 3 |
| Watchdog odmítnutí a následný WDT reset | PASS | Nová sada s protokolem 2, EBUSY potvrzen před PASS fází |
| Regrese argumentů/hard IRQ/lightsleep | PASS | Osm kontrol v RAM, finální frekvence 150 MHz |
| Konečný ordinary reset, firmware readback a obnova dat | PASS | USB/REPL, 37/37 souborů, backup regiony a RTC ověřené |
| První kontrola bezprostředně po flash | FAIL hostitelské precondition | Port ještě nebyl enumerovaný; před otevřením skončilo `assert len(ports)==1`. Následná kontrola prošla, nejde o timeout probuzení |
| První příprava dalšího cyklu po SYSRESETREQ | FAIL hostitelského předpokladu | Ochranný watchdog zůstal aktivní; guard proto nepovolil pokračovat. Čekající observer byl ukončen. Následný explicitní `machine.reset()` jej odstranil a nová sada prošla |
| Nových 100 cyklů, 30/75 minut, Wi-Fi, proud/energie, RISC-V, fyzické SWD | NEPROVEDENO | Starší výsledky tyto mezery nenahrazují |

**Pět finálních alarmových návratů:** tři v hlavní sadě, jeden v sondě resetu
jádra, jeden v opakované sadě po této sondě. Nejde o nových 100 cyklů.
Host časy hlavní finální sady: 3,811 / 3,876 / 3,844 s včetně bootu a USB.
Původních pět pozorovaných alarmových návratů na prvním kandidátu (včetně
nedokončeného hostitelského pokusu) se do této pětice nepřičítá.

Resetovací sonda po prvním READY/probuzení zastavila harness bez jeho ACK,
ověřila `phase=7`, `completed=1`, cause 4, `DBG_PWRCFG=0` a vymazaný ALARM.
Potom provedla `machine.WDT(timeout=8000)` a zápis
`machine.mem32[0xe000ed0c] = 0x05fa0004` (AIRCR klíč + SYSRESETREQ).
Nový start programu zachytil cause 1 a později watchdog cause 3; oba správně
odmítly znovu započítat starou fázi. Pro další jednorázovou sadu se vymazal
jen testovací magic `machine.mem_backup(2)[0] = 0` a vyvolal `machine.reset()`.
Žádný z těchto kroků nezapisoval flash. Tyto příkazy jsou destruktivní
resetovací test pro identifikovanou zálohovanou testovací desku, nikoli návod
k resetování libovolné běžící aplikace.

Konečný stav **09:22:02 UTC**: nový firmware ponechaný dle přání uživatele,
obnovený vstupní starší testovací `main.py`, nikoli nově nasazená aplikace.
Friendly REPL odpovídá, frekvence 150 MHz, příčina posledního běžného resetu 3,
`DBG_PWRCFG=0`, STA/AP/BLE a watchdog neaktivní. Všech 37 souborů je shodných
se vstupní zálohou; backup regiony a původní RTC s uplynulým časem jsou obnovené.
Panel nebyl překreslován ani prokazatelně uspán.

## Co se záměrně nemění a další ověření

- **Watchdog:** EBUSY zůstává veřejným omezením experimentu. P1.7 odstraní
  ochranu ve SWCORE; povolení aktivního WDT by změnilo kontrakt a vyžaduje
  samostatnou implementaci/testy teardownu a selhání přechodu.
- **Wi-Fi:** odhlášení s limitem 500 ms v C není součástí této opravy.
  Je nutné vyřešit souběh, blokování a význam celkového časovaného deadline.
  Nevyřešená autentizace na MikroTiku není prohlášená za opravenou.
- **Desky/architektury:** ARM opt-in jen Pico 2/Pico 2 W zůstává. GP24/29
  se bez doložené potřeby nově nepřepínají; žádná slepá podpora PSRAM desek.
  RP2040, RISC-V, `lightsleep()` a bezargumentová cesta zůstávají nezměněné.
- **Reset přes debugger:** softwarový AIRCR SYSRESETREQ po spotřebovaném
  alarmu prošel; fyzické SWD a reset před spotřebováním alarmu nebyly testované.
  Vlastní kód s přímým zápisem do POWMAN, který znovu nastaví alarm, může narušit
  klasifikaci; běžné RP2 RTC API takový budík neposkytuje. Test softwarového
  požadavku nelze vydávat za test připojeného debuggeru.
- **Upstream:** nynější větev zachovává experimenty a důkazy, není určena
  k přímému merge. Čistá historie má oddělit workaround po WDT, timed sleep
  a board přípravu GP25; migrace na `multitest.expect_reboot()` není hotová.
  BSD atribuce převzaté SDK sekvence se nesmí bez náhrady smazat.
  [Contributor guidelines](https://github.com/micropython/micropython/wiki/ContributorGuidelines)
  vyžadují DCO; dle dosavadního přání uživatele nepřidáváme `Signed-off-by`
  ani nevymýšlíme identitu. `tools/verifygitlog.py` pro pět nových implementačních
  commitů skutečně skončil FAIL kvůli noreply adrese a chybějícímu sign-off;
  jiné chyby formátu u nich nehlásil. Veřejný PR nebyl založen.

Související [MicroPython #15623](https://github.com/micropython/micropython/issues/15623)
zůstává relevantní; USB odpojení samo neprokazuje správný deep stav ani
opravu hlášeného pádu. [Badger2350 #30](https://github.com/pimoroni/badger2350/pull/30)
je board-specifické řešení, ne stejný Pico 2 W core patch.
[mamba2410/rp2350-powman-sleep](https://github.com/mamba2410/rp2350-powman-sleep)
řeší jinou cestu se zachováním SRAM; kód se odtud nekopíroval.

Pro instalaci/obnovu platí [handover](HANDOVER.cs.md#5-cílová-deska-první-kroky-před-zápisem):
ověřit vlastní desku, soubory a backup, teprve pak její ARM UF2. Při ztrátě
USB držet BOOTSEL při připojení a obnovit odpovídající známý firmware;
úplný obraz se soubory patří jen původní desce. Další měření má porovnat
stejnou sestavu bez Python GP23/GP25 helperu, přesně určit napájení, měřidlo,
panel a USB/debugger a oddělit spánkový proud od energie bootu a Wi-Fi.
