# Další review: reprodukovatelnost, LPOSC a návrhová rozhodnutí

Navazuje na [opravy a hardware testy](RESULTS-REVIEW-20260929.md).
Tato sada nemění C implementaci ani firmware připojeného Pico. Doplňuje
udržování exportovaných patchů, výslovné chování hostitelského testu,
kontrolu tovární kalibrace a ověření RISC-V sestavení.

## Rozhodnutí pro nynější kandidát

**Aktivní watchdog zatím zůstává EBUSY.** Je to omezení tohoto kandidáta,
nikoli hardwarová nutnost nebo požadavek obecného MicroPython API.
Pro následnou implementaci dává smysl watchdog přijmout a nechat jej běžet
bez vypínání, krmení nebo prodlužování během přípravy. SWCORE power-down
jej resetuje, takže po probuzení jej musí nový program znovu vytvořit.
Dosavadní hardware test ale ověřuje pouze odmítnutí, nikoli souběh jeho
timeoutu s napájecím přechodem.

Watchdog je resetovaný při vypnutí SWCORE podle
[RP2350 datasheetu, §12.9.1](https://datasheets.raspberrypi.com/rp2350/rp2350-datasheet.pdf#page=1194).
SDK `watchdog_enable()` standardně resetuje PSM; s výchozím `POWMAN_WDSEL=0`
nezničí POWMAN ani RTC. Běžná flash-boot cesta ROM čeká na dokončení
`CHANGING`, vyžádá P0.0 a znovu počká:
[A2 boot ROM](https://github.com/raspberrypi/pico-bootrom-rp2350/blob/fd6104450fa8f55c11c0c9b54dbc69a27537130f/src/main/arm/varm_boot_path.c#L587).
Proto netvrdíme, že timeout watchdogu nutně způsobí zamrznutí. Zdroje však
nenahrazují zkoušku timeoutu před požadavkem, během `WAITING`, kolem
`CHANGING` a při rušení přechodu. Právě tyto případy musí následný patch
ověřit, včetně správné reset cause, návratu USB a zachování RTC.
Změna `POWMAN_WDSEL` by nebyla bezplatnou pojistkou: reset POWMAN by ztratil RTC.

**Automatické síťové odhlášení nyní nevkládáme do timed-deepsleep jádra.**
Patří do samostatně ověřené síťové přípravy, která vyřeší i jiné způsoby
resetu a vypnutí rozhraní. Současný core nadále driver ukončí a rádio vypne.
Není tím přislíbené potvrzené odhlášení na AP ani bezchybné znovupřipojení.

Konkrétní důvody v připnutých zdrojích:

- `WLAN.active(False)` již pro STA volá `cyw43_wifi_leave()`; `WLAN.deinit()`
  volá přímo `cyw43_deinit()`. Nejde o totožné cesty
  (`extmod/network_cyw43.c:135–150`). Návrat `leave()` je dnes zahazovaný také
  v `WLAN.disconnect()`; jeho propagace je samostatný vhodný fix.
- `leave()` jde přes `cyw43_ioctl()` a `cyw43_ensure_up()`; bez kontroly
  aktivní STA a inicializovaného driveru může znovu zapnout neaktivní rádio
  (`lib/cyw43-driver/src/cyw43_ctrl.c:444–455,666–668`).
- Čekání na odpověď IOCTL má v MicroPythonu timeout 1 s; před ním může být čekání na
  flow-control kredity nebo probuzení sběrnice. SPI/DMA obsahuje i čekání
  bez časového limitu. Vnější 500ms smyčka tedy nezaručí dokončení celé
  přípravy do 500 ms (`extmod/cyw43_config_common.h:43`, `cyw43_ll.c`,
  SDK `cyw43_bus_pio_spi.c`).
- Příprava potřebuje zpracování událostí, zamykání a opakovanou kontrolu
  souběhu před globálním IRQ-off. Musí zachovat původní alarmový deadline,
  nikoli po odhlášení založit nový celý interval. Lokální link-down není
  důkaz přijetí odhlášení AP.

Neřešíme to zde změnou společného síťového kódu bez kontrolních síťových
testů. [Dřívější Linux/MikroTik selhání](RESULTS-DHCP-LINUX-20260929.md)
zůstávají nevyřešená.

## Rozsah desek a GPIO

Board opt-in pro ARM Pico 2 / Pico 2 W se nemění. Další RP2350 desky nejsou
prokázaně nekompatibilní, ale samotná podmínka `PICO_RP2350 && PICO_ARM`
neověří restart jejich externích součástek. Například PSRAM používá druhý
QMI/XIP prostor a vlastní inicializaci/timing. Při novém programu nepotřebujeme
zachovat Python heap, potřebujeme však korektní nový boot s externí pamětí,
která během spánku zůstala napájená. Širší zapnutí má následovat až po
kontrole reprezentativních konfigurací, nikoli jako vedlejší změna review.

GP24 a GP29 se zatím nově neparkují. Bez měření není prokázaný přínos;
nejprve je nutné ověřit směry, externí úrovně a pořadí po vypnutí CYW43.
Připojený B/W/R V4 panel nebyl ovládán. Historických 0,37 mA z jiné sestavy
není měření současného firmwaru nebo těchto dvou pinů.

## LPOSC na skutečně připojené desce

Dne **29. 9. v 09:45:21 UTC** byla znovu ověřená USB/runtime identita
původního linuxového Pico 2 W ARM a verze `2445a04bf`. Následovalo pouze
čtení, bez resetu, uspání, flashování či zápisu do OTP:

| Položka | Výsledek |
| --- | --- |
| ECC OTP řádek `0x11`, 16 bitů na `0x40130022` | **33045 Hz** |
| Platnost podle připnutého SDK, rozsah 26000–40000 Hz | PASS |
| `POWMAN_LPOSC_FREQ_KHZ_INT` na `0x40100050` | 33 |
| `POWMAN_LPOSC_FREQ_KHZ_FRAC` na `0x40100054` | 2949 |
| Shoda se SDK výpočtem `45 * 65536 // 1000` | PASS |
| Návrat friendly REPL, původní `main.py`, 150 MHz, WDT vypnutý | PASS |

[Anonymizovaný záznam](evidence/linux-20260929-followup/lposc-otp.json).
SDK čte právě tento ECC řádek a při platné hodnotě nastaví dělič. Jeho
aktuální registry této hodnotě odpovídají. To není nové měření frekvence,
driftu ani délky spánku. Tovární údaj platí pro výrobní měření při 1,1 V,
pokojové teplotě a výchozím trimu; neznamená přesnost krystalu za všech podmínek.
Na vzdáleném Mac Picu se OTP v této sadě nečetla.

## Testovací protokol

README nyní výslovně říká, že časované cykly tohoto harnessu bez odpovídajícího
host ACK nevstoupí do deepsleep. Omezení patří do testovacího programu,
nikoli do implementace `machine.deepsleep()`.

Host měří interval **ACK SLEEP → READY**, tedy i boot, USB a případně síť.
Formulace druhého review „skutečný čas spánku“ je příliš silná: pomalý boot
může zakrýt předčasné probuzení. Existující README tento limit popisuje.

## Generování patchů

`core-upstream.patch` a `combined-upstream.patch` už mají společný
[generátor a kontrolu](tools/README.md). Zdroj pravdy je commitnutý HEAD
proti připnutému `09f5bb447504a058376c62fe991b3613531837e6`.

```sh
python3 experiments/rp2350-deepsleep/tools/generate_patches.py --check
# Po commitu zamýšlených core/test změn:
python3 experiments/rp2350-deepsleep/tools/generate_patches.py --write
python3 experiments/rp2350-deepsleep/tools/generate_patches.py --check
python3 experiments/rp2350-deepsleep/tools/test_generate_patches.py
```

Výchozí kontrola nic nepřepisuje, zastaralý export vrací chybu. Generování
odmítá necommitované či nové nezařazené zdroje ve svém rozsahu a izoluje Git
konfiguraci, atributy, textconv a skutečný index. Historické patche ani
TinyUSB nemění. **10/10 izolovaných testů PASS**, včetně globálních XDG
atributů/ignore pravidel, aplikace exportu na základ a zachování indexu.
Repozitářová pravidla Ruff, formát a kontrola whitespace PASS. Dodatečný
pokus s nesouvisejícím `ruff --select ALL` hlásil 117 stylistických pravidel
(například anotace typů, docstringy a preference pytest); shodu s touto
nadstandardní sadou netvrdíme. [Výsledky](evidence/linux-20260929-followup/offline-checks.json).

Aktuální core export má stále stejných osm zdrojových souborů; změnil se
formát indexových hashů na plné SHA. Combined navíc obsahuje nové vysvětlení
host ACK v README. Commit, checksum inventář a případné CI spuštění nejsou
automatické vedlejší účinky generátoru.

## RISC-V compile regression

Ve čtyřech oddělených buildech na Linuxu x86_64 prošel čistý původní základ
a kandidát `b0222450ee72e29f4d61d0fe9918ebff408c2879`. Kandidát má stejný C
kód jako nahraný ARM `2445a04bf`; pozdější commit `709a7f966` mění jen README
harnessu. Žádná RISC-V binárka nebyla nahraná do desky.

| Kontrola | Výsledek |
| --- | --- |
| Upstream `09f5bb4475`, `RPI_PICO2_W` + `RISCV` | PASS |
| Upstream `09f5bb4475`, `RPI_PICO2` + `RISCV` | PASS |
| Kandidát `b0222450ee`, `RPI_PICO2_W` + `RISCV` | PASS |
| Kandidát `b0222450ee`, `RPI_PICO2` + `RISCV` | PASS |
| Preprocesor, symboly a disassembly: `lightsleep()` → reset | PASS ve všech čtyřech |
| RISC-V runtime, USB, alarm, spotřeba a P1.7 | **NEPROVEDENO** |
| Nové ARM cykly, dlouhé spánky, Wi-Fi a měření spotřeby | **NEPROVEDENO v této navazující sadě** |

Všechny úspěšné buildy mají nula compiler warnings; CMake hláška o vlastním
sestavení připnutého picotool je zachovaná. První pokus základního Pico 2 W
selhal na chybějícím host `mpy-cross`: vlastní `BUILD` se přenesl do vnořeného
make. Oprava postupu je explicitní prebuild `mpy-cross BUILD=build`; nebyla
potřeba změna zdrojů. Původní neúspěšný log zůstává mezi důkazy.

Použit byl oficiální [pico-sdk-tools v2.3.0-1](https://github.com/raspberrypi/pico-sdk-tools/releases/tag/v2.3.0-1),
GCC **16.1.0**, CMake **4.4.3**, Python **3.12.3**. Archiv
`riscv-toolchain-16-x86_64-lin.tar.gz` byl ověřen proti SHA-256 vydání:
`4fca2b0159348fcc444f959d706fa389aa7fcd98f518d67e15d1beb8ffccf99a`.
SDK zůstalo `98a542c1a62fb549ffb5d66a3e5892b06276b670`.
Jeho vlastní Zcmp probe nepřijal clobber `s0` při `-O0`, a proto SDK samo
zvolilo podporované `-march=rv32imac_zicsr_zifencei_zba_zbb_zbs_zbkb -mabi=ilp32`.
Nešlo o ruční změnu ISA ani SDK. Baseline měl původní TinyUSB, kandidát
stejný gitlink plus přesně ověřenou opravu SETUP fronty.

`PICO_RISCV=1`, `PICO_ARM` není definované (v `#if` je tedy nula).
Ve všech ELF chybí ARM funkce `machine_deepsleep_timed` a
`machine_deepsleep_init`; výsledné `machine_deepsleep` volá lightsleep a reset.
Výsledek dokládá sestavitelnost zachované cesty, **nikoli RISC-V podporu
nového úsporného stavu**. Také neopravuje argumenty staré RISC-V cesty;
nepouštět na ní nehlídané záporné/bezargumentové sleep testy.

Úplné příkazy, revize sedmi závislostí, hashe ELF/BIN/UF2, verze a odkazy na
komprimované build logy jsou v [riscv-summary.json](evidence/linux-20260929-followup/riscv-summary.json).
Lokální cesty jsou anonymizované; hashe binárek zůstávají původní. UF2 hash
kandidáta Pico 2 W je
`acf16ece40202aaa978ac082225266e5c6d5870385e367c634f9ab4b53a04932`,
Pico 2 je `d7b145e627bc18c8cfde1f11d7ce9781e351d5cbf25935208cff1d2c9ab15530`.
Tyto UF2 nejsou náhradou otestovaného ARM firmware ani hardware doporučením.

### Reprodukce konfigurace RISC-V

Následující blok je pro **Linux x86_64**, nové adresáře a přesně uvedené
revize, nikoli automatický build budoucího HEAD. Vyžaduje Git, curl, GNU Make,
host C/C++ compiler, Python a venv. Ověřený host měl GCC 13.3.0 a Make 4.3.
Pořadí odpovídá provedeným buildům; zapsaný souhrnný blok prošel `bash -n`,
celý se podruhé nespouštěl. Jiné absolutní cesty/verze host nástrojů mohou
změnit checksum ELF; jde o reprodukci konfigurace, nikoli tvrzení o bitové
shodě na libovolném hostu. Neobsahuje flashování ani práci s deskou.

```bash
(
set -euo pipefail
[[ $(uname -s) == Linux && $(uname -m) == x86_64 ]]
for v in ${!PICO_@} ${!PICOTOOL_@} ${!CMAKE_@} ${!MICROPY_@} ${!GIT_@}; do unset "$v"; done
unset CC CXX CFLAGS CXXFLAGS LDFLAGS MAKEFLAGS MFLAGS
unset BOARD BOARD_VARIANT BUILD CROSS_COMPILE MPY_CROSS USER_C_MODULES FROZEN_MANIFEST

riscv_repro_root="$PWD/rp2350-riscv-repro"
mkdir "$riscv_repro_root"
cd "$riscv_repro_root"
python3 -m venv venv
venv/bin/python -m pip install 'cmake==4.4.3'

curl --fail --location --output toolchain.tar.gz \
  https://github.com/raspberrypi/pico-sdk-tools/releases/download/v2.3.0-1/riscv-toolchain-16-x86_64-lin.tar.gz
printf '%s  %s\n' \
  4fca2b0159348fcc444f959d706fa389aa7fcd98f518d67e15d1beb8ffccf99a \
  toolchain.tar.gz | sha256sum --check -
mkdir toolchain
tar -xzf toolchain.tar.gz -C toolchain

export PICO_TOOLCHAIN_PATH="$riscv_repro_root/toolchain"
export PATH="$riscv_repro_root/venv/bin:$PICO_TOOLCHAIN_PATH/bin:$PATH"
riscv32-pico-elf-gcc --version
export SOURCE_DATE_EPOCH=1790668407 TZ=UTC LC_ALL=C
export CMAKE_ARGS='-DCMAKE_BUILD_TYPE=MinSizeRel -DCMAKE_EXPORT_COMPILE_COMMANDS=ON -DPICOTOOL_GIT_BRANCH=6f6458d792b93685a11423b244a585eaa99eafcf -DPICOTOOL_FORCE_FETCH_FROM_GIT=1'

build_revision() (
  label=$1; url=$2; sha=$3
  git clone --no-checkout "$url" "$riscv_repro_root/$label"
  cd "$riscv_repro_root/$label"
  git checkout --detach "$sha"
  git submodule update --init -- lib/btstack lib/cyw43-driver lib/lwip \
    lib/mbedtls lib/micropython-lib lib/pico-sdk lib/tinyusb
  test "$(git -C lib/pico-sdk rev-parse HEAD)" = 98a542c1a62fb549ffb5d66a3e5892b06276b670

  if [[ $label == candidate ]]; then
    bash experiments/rp2350-deepsleep/prepare-tinyusb.sh
  fi
  export PICO_SDK_PATH="$PWD/lib/pico-sdk"
  make -C mpy-cross BUILD=build -j6
  for board in RPI_PICO2_W RPI_PICO2; do
    suffix=pico2; [[ $board != RPI_PICO2_W ]] || suffix=pico2w
    make -C ports/rp2 BOARD="$board" BOARD_VARIANT=RISCV \
      BUILD="build-review-riscv-$label-$suffix" -j6
  done
)

build_revision baseline https://github.com/micropython/micropython.git \
  09f5bb447504a058376c62fe991b3613531837e6
build_revision candidate https://github.com/Rhiz3K/micropython.git \
  b0222450ee72e29f4d61d0fe9918ebff408c2879
)
```

## Příprava upstreamu

Zůstává stejná experimentální větev; nová veřejná větev ani upstream PR
nevznikají. Čistý upstream návrh má oddělit WFI workaround, timed sleep
a Pico 2 W přípravu a převést relevantní testy do upstream runneru.
Tato reorganizace není zaměnitelná za export core patche.
DCO certifikaci a skutečnou autorskou identitu nepřidáváme za uživatele;
dosavadní požadavek ponechat noreply identitu bez sign-off se nemění.
