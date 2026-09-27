# Předání: RP2350 deepsleep, Mac a Pico 2 W s displejem

Stav k 27. 9. 2026. Fork: [Rhiz3K/micropython](https://github.com/Rhiz3K/micropython),
větev `rp2/rp2350-timed-deepsleep`.

**Experimentální firmware. Funkční testy proběhly na jedné jiné Pico 2 W;
spotřeba a energie cyklu nejsou změřené. Wi-Fi není spolehlivě ověřená.**
Nová sestava na Macu dosud nebyla sestavena, zálohována ani testována.

## Co přebíráš

- Firmware a testy jsou v commitu `3fc3f9431d9ccc571b4fb0c27bd860d5709ab683`.
  Tento už existující commit nebyl při předání přepisován.
- Základ je `09f5bb447504a058376c62fe991b3613531837e6`, SDK
  `98a542c1a62fb549ffb5d66a3e5892b06276b670` (2.3.0).
- [Výsledky a otevřené chyby](RESULTS.md), [návrh upstream PR v angličtině](upstream-pr.md),
  [testovací nástroje](../../tests/ports/rp2/deepsleep/README.md),
  [přesné revize submodulů](submodule-revisions.txt).
- `firmware.patch` a `tests.patch` lze samostatně posoudit vůči přesnému základu.
  Jsou už aplikované ve větvi; na ni je znovu neaplikuj.
- Veřejný upstream PR nebyl vytvořen. Tato složka je předávací materiál forku,
  nikoli navrhovaná součást upstream firmwaru.

Nové `machine.deepsleep(ms)` na Pico 2/Pico 2 W ARM žádá POWMAN P1.7:
SWCORE, obě SRAM domény a XIP cache se mají vypnout, AON časovač běží z LPOSC
a alarm spustí normální ROM boot. Python heap se nezachovává. RTC a
`machine.mem_backup(2)` přežijí; regiony 0/1 nikoli. Firmware nepoužívá scratch
slova jako vlastní wake značku. Aktivní watchdog, Python worker na core1 a IRQ
kontext se odmítají EBUSY. Aplikace musí předem ukončit workery a flush/close
otevřené soubory. USB a síť se po probuzení navazují znovu.

RP2040 a bezargumentová cesta zůstávají původní. Nová cesta není ověřená pro
RISC-V a je pro něj vypnutá. Opravy RTC/frekvence `cc120575`, `eb1611d2`,
`1ea77a5d` již obsahuje základ; znovu je neimplementuj.

## Známý stav původní desky

Původní Pico 2 W na linuxovém PC prošlo 100 krátkými cykly a dalšími kontrolami.
Při následném Wi-Fi trasování `wlan.config(trace=7)` 26. září přestalo odpovídat
USB REPL. To je pozdější událost než úspěšné testy z 25. září. Firmware se při
trasování nepřepisoval. Běžný USB reset a 5/30sekundové požadavky na vypnutí
portu hubu obnovu nezajistily; skutečné odpojení VBUS nebylo změřeno. Majitel
potvrdil napájení pouze USB, bez dalších vodičů.

Poslední ověřený stav je **neodpovídající deska**, čekající na fyzické odpojení
a připojení, nejprve bez BOOTSEL a ideálně přímo k PC. Na přání majitele má
zůstat experimentální firmware. Ověřená úplná původní záloha a obnovovací UF2
existují soukromě na původním PC, nejsou ve forku. Nejsou zálohou nového Pica.

Wi-Fi test selhal i na původním masteru před prvním uspáním. Read-only diagnostika
routeru našla dřívější neúspěšné DHCP nabídky pro kandidátní MAC; její přiřazení
k desce ještě potřebuje potvrdit skutečným WLAN MAC. Není prokázaná příčina ani
regrese deepsleep. Příště preferuj packet capture na kontrolovaném AP. USB trace
bez funkční obnovy neopakuj. Router nebyl překonfigurován; privátní síťové
podklady, hesla ani původní aplikace se nepřenášejí do GitHubu.

## Nová sestava

Majitel uvedl **Pico 2 WH** (Pico 2 W s připájenými headery) a
[Waveshare Pico-ePaper-2.9](https://rpishop.cz/pico-karty/3652-waveshare-29-e-paper-displej-pro-raspberry-pi-pico.html).
Pro ověřenou originální Pico 2 W použij `BOARD=RPI_PICO2_W`, výchozí ARM variantu.
Model i unique ID ověř na nové desce; staré sériové číslo/manifest nepřebírej.
Nezaměňuj ji s Pico WH/Pico W (RP2040, stará cesta) nebo Pico 2 bez Wi-Fi
(`BOARD=RPI_PICO2`).

Displej je samostatná navazující integrace; patch žádný driver nepřidává.
Nejdřív otestuj samotnou desku bez displeje. Displej připojuj/odpojuj při
odpojeném napájení. Před přidáním driveru ověř potisk/revizi a její schéma.
Zachovaný obraz e-paperu sám o sobě nedokazuje spánek procesoru ani nízký odběr.
Při měření porovnávej zvlášť holou desku a celou sestavu včetně displeje,
jeho řadiče a napájení.

Odkazovaný modul je černobílý 296×128, nikoli varianta B/D/CapTouch.
[Schéma Waveshare](https://files.waveshare.com/upload/6/62/Pico-ePaper-2.9.pdf)
a [připnuté Python demo](https://github.com/waveshareteam/Pico_ePaper_Code/blob/c9bcd84db5adf5f085353649a8a5c31492bc5fb8/python/Pico_ePaper-2.9.py)
uvádějí toto zapojení; před použitím porovnej fyzickou revizi:

| Signál | Připojení |
| --- | --- |
| Napájení | VSYS, GND |
| DC / CS | GP8 / GP9 |
| SPI1 CLK / DIN (MOSI) | GP10 / GP11 |
| RST / BUSY | GP12 / GP13 |

Schéma obsahuje řízení napájecího obvodu navázané na RST; nevymýšlej samostatný
volný GPIO EN ani bez měření netvrď úplné odpojení napájení. Demo `sleep()`
pošle příkaz `0x10`, data `0x01`, počká dvě sekundy a stáhne RST. Pro pozdější
integraci dokonči refresh/BUSY, zavolej ověřené `epd.sleep()` a pak teprve
`machine.deepsleep(5000)`. Po novém bootu displej resetuj a inicializuj. Vendor
`ReadBusy()` nemá timeout: integrační test musí čekání omezit, aby zamrzlý
displej neskrýval chybu uspávání. Vendor UF2 není náhradou tohoto firmwaru.

## Klon a prostředí na Macu

Následující příkazy jsou postup pro nový host; **na macOS zde nebyly spuštěné**.
Nejprve ověř `uname -m` a dostupnost Command Line Tools (`xcode-select -p`).
Pokud chybí, nainstaluj je `xcode-select --install`. S dostupným Homebrew:

```sh
git clone --branch rp2/rp2350-timed-deepsleep https://github.com/Rhiz3K/micropython.git
cd micropython
git rev-parse HEAD

brew install cmake python picotool
brew install --cask gcc-arm-embedded
python3 -m venv "$HOME/.venvs/rp2350"
source "$HOME/.venvs/rp2350/bin/activate"
python -m pip install mpremote pyserial

uname -m
arm-none-eabi-gcc --version
arm-none-eabi-gcc -print-file-name=libc.a
cmake --version
picotool version
```

`libc.a` musí ukázat skutečný existující soubor. Samostatná Homebrew formula
`arm-none-eabi-gcc` bez target C knihovny nestačí. Cask se časem mění a může mít
jinou verzi než historicky ověřený Linux GCC 14.3.1; zaznamenej skutečné verze.
Pro přesný historický build je níže Linux recept, pro bližší nativní sestavení
je k dispozici oficiální Arm 14.3.rel1 balíček pro příslušnou macOS architekturu.
Nový GCC/Mac build vyžaduje vlastní validaci, není automaticky původní UF2.

Zdroje: [Homebrew cask](https://formulae.brew.sh/cask/gcc-arm-embedded),
[Arm toolchains](https://developer.arm.com/downloads/-/arm-gnu-toolchain-downloads),
[mpremote](https://docs.micropython.org/en/latest/reference/mpremote.html).

## Identifikace a záloha nové desky

Před zápisem firmwaru/testů potvrď oprávnění k použití právě této desky,
ověř její model/UID, zazálohuj firmware i celý filesystem a zajisti BOOTSEL
obnovu. Užitečná data z backup registrů zaznamenej zvlášť; flash je neobsahuje.
Další sériové klienty zavři. Metadata portů lze nejprve jen vypsat:

```sh
python tests/ports/rp2/deepsleep/host.py list
mpremote connect list
mpremote connect id:NEW_USB_SERIAL resume exec \
  'import machine, sys, os; print(sys.implementation); print(os.uname()); print(machine.unique_id().hex()); print(os.listdir())'
```

`NEW_USB_SERIAL` nahraď skutečným identifikátorem. Na Macu se názvy portů liší
od linuxového ttyACM0; nepoužívej slepě první port. REPL příkaz může přerušit
běžící aplikaci. Pro zálohu přepni vlastní desku fyzicky do BOOTSEL, připoj
jen tuto testovanou desku a pomocí `picotool info -a` ověř identitu a kapacitu.
BOOTSEL serial se může lišit od MicroPython USB serial:

```sh
umask 077
pico_backup="$HOME/pico-backup-NEW_DEVICE"
mkdir -p "$pico_backup"
picotool info -a
picotool info -a --ser NEW_BOOTSEL_SERIAL
picotool save -a -v "$pico_backup/full-flash.bin" --ser NEW_BOOTSEL_SERIAL
picotool verify "$pico_backup/full-flash.bin" --ser NEW_BOOTSEL_SERIAL
wc -c "$pico_backup/full-flash.bin"
shasum -a 256 "$pico_backup/full-flash.bin"
```

Použij nový adresář a nepřepisuj starší zálohu. U originální Pico 2 W očekávej
celou 4 MiB flash (4194304 bajtů), ne pouze programovou část. Ověřený kompletní
obraz zahrnuje interní filesystem; externí úložiště by vyžadovalo zvláštní
zálohu. Pokud se kapacita/identita liší nebo verify selže, nepokračuj zápisem.
Postup nástroje: [oficiální picotool](https://github.com/raspberrypi/picotool).

## Sestavení a instalace

Pro novou potvrzenou Pico 2 W, z kořene klonu (bez `BOARD_VARIANT=RISCV`):

```sh
make -C ports/rp2 BOARD=RPI_PICO2_W submodules
git -C lib/pico-sdk rev-parse HEAD
git submodule status --recursive
make -C mpy-cross -j"$(sysctl -n hw.ncpu)"
export CMAKE_ARGS='-DPICOTOOL_GIT_BRANCH=6f6458d792b93685a11423b244a585eaa99eafcf -DPICOTOOL_FORCE_FETCH_FROM_GIT=1 -DCMAKE_BUILD_TYPE=MinSizeRel'
make -C ports/rp2 BOARD=RPI_PICO2_W BUILD=build-mac-PICO2_W -j"$(sysctl -n hw.ncpu)"
shasum -a 256 ports/rp2/build-mac-PICO2_W/firmware.uf2
```

Zkontroluj vypsané SDK SHA proti začátku dokumentu. `CMAKE_ARGS` je úmyslně
proměnná prostředí; zadání na příkazovém řádku make by mohlo přepsat argumenty
boardu. Uchovej build log a hash svého artefaktu.

Teprve po identifikaci, oprávnění a ověřené záloze nahraj firmware na stejnou
desku v BOOTSEL a znovu ověř její REPL identitu:

```sh
picotool load -v ports/rp2/build-mac-PICO2_W/firmware.uf2 --ser NEW_BOOTSEL_SERIAL
picotool reboot --ser NEW_BOOTSEL_SERIAL
```

Původní `boot.py`/`main.py` zůstávají ve flash; před jejich dalším použitím
posuď jejich chování. Nahrání UF2 není záloha ani automatické vyčištění aplikace.
BOOTSEL boot může zanechat aktivní watchdog; testovací instalátor provede
`machine.reset()` před sadou. EBUSY neobcházej zápisem do watchdog registrů.

Přesné opakování historických buildů **na Linux x86_64**:

```sh
experiments/rp2350-deepsleep/reproduce.sh /absolute/path/to/NEW-build-directory
```

Skript nejprve sestaví nezměněné W/RP2040, pak patch pro W/Pico2/RP2040,
ověří stažený toolchain a uloží logy i hashe. Na macOS jej nespouštěj jako
nativní recept. Binárky stejného funkčního zdroje po commitu mohou mít jiný
hash kvůli verzovacím metadatům.

## Pořadí nových testů

1. Bez displeje a Wi-Fi: nový privátní manifest podle [README testů](../../tests/ports/rp2/deepsleep/README.md),
   `cycles=3`, `sleep_ms=2500`, `expect_deep_cause=true`. Manifest patří nové
   desce a vlastní záloze. Pokud jeden ověřený full-flash obraz zahrnuje firmware
   i interní FS, obě zálohové položky mohou odkazovat na něj; tento fakt zapiš.
2. Po úspěchu samostatná sada 100 cyklů. Kontroluj cause, RTC, POWMAN, soubor
   a USB. Host vyžaduje nový název logu, nic nepřepisuje.
3. Regrese lightsleep, vlákna, DMA, watchdog odmítnutí a běh watchdogu po odmítnutí.
4. Wi-Fi na známém AP s kontrolovaným HTTP endpointem: nejprve obyčejné restarty,
   pak deep wake. Zaznamenej asociaci, DHCP, DNS, HTTP a WLAN status odděleně.
   Nepřenášej stará síťová hesla ani předpoklad stejné příčiny mezi sítěmi.
5. 30 min a 75 min; poté integrace a uspání konkrétní revize e-paperu.
6. Proud a energie cyklu A sleep / B původní implementace / C nová. Zaznamenej
   napětí, místo měření, měřidlo/rozlišení, USB, debugger, Wi-Fi i displej.

Příklad po přípravě privátního manifestu a konfigurace mimo Git:

```sh
python tests/ports/rp2/deepsleep/host.py install \
  --manifest "$pico_backup/manifest.json" --config "$pico_backup/config.json" --allow-write
python tests/ports/rp2/deepsleep/host.py run \
  --manifest "$pico_backup/manifest.json" --allow-run --log "$pico_backup/three-cycles.jsonl"
```

Existující `main.py` vyžaduje vědomé `--replace-main`; nástroj si jeho kopii
uloží do privátního adresáře. `boot.py` nemění. Sada nastavuje RTC, zabírá
všech osm POWMAN slov a kontroluje ztrátu watchdog backup oblastí. Po ztrátě
napájení se progress vynuluje, program však čeká na host GO a sám necykluje.

Známé omezení host nástroje: serial write/flush nemají úplnou časovou mez;
`--timeout` není zárukou ukončení při zamrzlém USB ovladači. Při zaseknutí
ukonči testovacího klienta a zajisti fyzické odpojení desky. Zápis firmware ani
testovací smyčku nespouštěj bez dostupné obnovy.

Pro dlouhé sady použij vždy `cycles=1`, nový run/log a větší host timeout:
30 minut znamená `sleep_ms=1800000` s `--timeout 2100`, 75 minut
`sleep_ms=4500000` s `--timeout 4800`. Výchozích 90 sekund nestačí.
Nastav také explicitní `rtc_tolerance_s` podle plánované tolerance a zaznamenej
skutečný rozdíl RTC vůči host času; LPOSC nemá garantovanou přesnost krystalu.
Oba dlouhé testy jsou při tomto předání stále NEPROVEDENO.

## Návrat a další předání

Obnova celé zálohy je zápis přes celý obsah flash právě této desky. Zkontroluj
její uložený hash, vrať desku do BOOTSEL, znovu ověř identitu a pak:

```sh
picotool load -v "$pico_backup/full-flash.bin" --ser NEW_BOOTSEL_SERIAL
picotool reboot --ser NEW_BOOTSEL_SERIAL
```

Původní firmware/filesystem nové desky lze obnovit jen její vlastní zálohou.
Veřejný fork neobsahuje zálohy ani credentials. Pro budoucí upstream bude
potřeba lidská revize, přezkoumání změny retence mem_backup, měření spotřeby,
vyřešení síťové stability a commit message/DCO podle upstream pravidel.
Existující autorství při předání nebylo přepisováno.

Text pro dalšího asistenta:

> Pokračuj ve forku Rhiz3K/micropython, větev rp2/rp2350-timed-deepsleep.
> Nejdřív přečti experiments/rp2350-deepsleep/HANDOVER.cs.md a RESULTS.md.
> Mám Mac, jinou Pico 2 W s headery a Waveshare Pico-ePaper-2.9; revizi displeje,
> firmware/UID desky a zálohu musíš ověřit před zápisem. Původní deska na Linuxu
> po USB trace neodpovídá, její stav nesměšuj s touto deskou. Nejdřív testuj
> samostatnou desku, potom Wi-Fi a teprve potom displej. Výsledek je experiment,
> bez měření spotřeby; neoznačuj nové testy za PASS, dokud skutečně neproběhnou.
> Upstream PR zatím nevytvářej; aplikační firmware a webový instalátor jsou mimo rozsah.
