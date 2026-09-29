# Handover: pokračování na druhém PC a druhé desce

Aktualizováno **29. 9. 2026**. Cílem je pokračovat v ověřování časovaného
RP2350 deepsleep, USB a Wi-Fi na cílovém PC a jeho skutečné desce.
Při tomto předání se **neotevíral USB port, neresetovala ani nepřepisovala deska**.
Níže uvedené stavy hardware jsou poslední zaznamenaná pozorování, nikoli
nové ověření dnešního zapojení.

## 1. Co převzít

- Fork: [Rhiz3K/micropython](https://github.com/Rhiz3K/micropython), větev
  **`rp2/rp2350-timed-deepsleep`**.
- Poslední implementační commit:
  [`0f193e89cbb0246ca4d967e1ad98db28304a031c`](https://github.com/Rhiz3K/micropython/commit/0f193e89cbb0246ca4d967e1ad98db28304a031c).
  Obsahuje GP25 přípravu v core, rozšířené testy, Wi-Fi helper, TinyUSB patch
  a anonymizované důkazy. Je pushnutý; při přípravě předání se ověřila shoda
  lokálního a vzdáleného commitu. Následující commit tohoto předání mění jen dokumentaci.
- **Upstream PR nebyl založen a celek stále není ready pro upstream.**
  Používá se stávající Git identita. Podle přání uživatele nepřidávat
  `Signed-off-by` ani vymýšlet skutečné jméno/e-mail. Případné budoucí
  upstream podání a jeho požadavky se řeší samostatně.
- Hlavní pracovní strom na Macu je před tímto předáním čistý; **`lib/tinyusb`
  je úmyslně lokálně upravený**. Gitlink zůstává na `b549ac1d…`.
  Přesný [TinyUSB patch](tinyusb-ep0-queue.patch) je uložený v hlavním repozitáři,
  ale nový klon jej musí zvlášť aplikovat. Samotné `git clone` nestačí.
- `firmware.patch`, `tests.patch` a `combined-upstream.patch` jsou podklady
  proti upstream základu `09f5bb447504a058376c62fe991b3613531837e6`.
  **Core/test změny už jsou v této větvi; tyto tři patche na ni znovu neaplikovat.**
  `combined-upstream.patch` neobsahuje TinyUSB opravu ani soukromou aplikaci.

Čti v tomto pořadí:

1. Tento handover.
2. [USB/Wi-Fi: opravy, testy a nasazení 28. 9.](RESULTS-USB-WIFI-MAC-20260928.md).
3. [Společný P1.7/GP25 kandidát a rozšířené testy 27. 9.](RESULTS-EXTENDED-MAC-20260927.md).
4. [Opt-in hardware testy a formát privátního manifestu](../../tests/ports/rp2/deepsleep/README.md).
5. Podle úkolu [Mac funkční testy](RESULTS-MAC-20260927.md),
   [displejová optimalizace](POWER-OPT-MAC-20260927.md),
   [GP25 měření](POWER-GP25-MAC-20260927.md) a [návrh upstream PR](upstream-pr.md).

[Starý chronologický handover](https://github.com/Rhiz3K/micropython/blob/0f193e89cbb0246ca4d967e1ad98db28304a031c/experiments/rp2350-deepsleep/HANDOVER.cs.md)
a [původní linuxové výsledky](RESULTS.md) zůstávají historickými podklady.
Jejich tehdejší „aktuální stav“ nepřebírat jako dnešní stav cílové desky.

## 2. Dvě různé desky — nesměšovat jejich stav ani zálohy

| Deska | Poslední zaznamenaný stav | Co z něj nelze odvodit |
| --- | --- | --- |
| Původní Pico 2 W na linuxovém PC | Dříve prošlo 100 krátkými spánky. Po Wi-Fi trasování `wlan.config(trace=7)` 26. 9. přestalo odpovídat USB. Obnova fyzickým odpojením tehdy nebyla potvrzená; soukromé zálohy jsou na původním PC. | Že je dnes stále zaseklé, že má nový USB fix nebo že se na něj vztahuje Mac nasazení. |
| Nové Pico 2 W na Macu | Nasazení ověřeno **28. 9. v 09:06:56 UTC**: nový firmware, 29 souborů, z toho 28 původních byteově totožných a cíleně upravený `main.py`. Zůstalo ve friendly REPL, rádio vypnuté, panel zaparkovaný; nebylo v deepsleep. Guard odstraněný, backup slova obnovená, RTC ověřené. | Že po pozdějším přepojení stále stojí v REPL. Reset spustí upravenou původní aplikaci. |
| Deska připojená při novém pokračování | **Zatím neověřeno.** Nejdřív zjistit skutečný model, UID, aktuální firmware a zapojení. | Že jde automaticky o jednu z předchozích desek nebo že na ni patří jejich manifest/flash backup. |

Mac sestava měla stále připojený Waveshare **Pico-ePaper-2.9 B/W V2, 296×128**.
Napájení při pozdějších testech: hub → vstup JT-UM120 → výstup JT-UM120 → Pico;
PC port měřáku byl také v hubu. Pico nemělo další napájení. Nové zapojení
ověřit znovu; stará fotografie neurčuje dnešní stav ani polohu propojek.

Mac firmware zůstává historicky označen
`v1.30.0-preview.88.g764de396cf.dirty.usbq1` (build 28. 9.). Jeho UF2 SHA256:
`b404a1771bf0097a07709848cd296ff6a2eb755f1d7cf25a10395a8f346f0a43`.
Vznikl před commitem `0f193e89c`; starší hash v runtime není důkazem,
že opravy chybějí. Nový build na druhém PC bude mít vlastní verzi/hash.

## 3. Co funguje a co ještě není prokázané

| Oblast | Přesný rozsah důkazů |
| --- | --- |
| Timed deepsleep | P1.7 vypíná SWCORE, SRAM a XIP cache; alarm vede k novému ROM bootu. RTC a `machine.mem_backup(2)` se zachovávají, Python heap a regiony 0/1 ne. Aktivní watchdog/core1/IRQ mají definovaná odmítnutí. RP2040, RISC-V a bezargumentová cesta nejsou touto cestou změněné. |
| Společný P1.7/GP25 firmware `c5c308…` | 120 alarmových návratů: 100 bez rádia, 10 STA, 5 AP v opakované sadě, 5 BLE. Dřívější AP/STA+BLE bootstrap FAIL jsou zachované. |
| Nový USB firmware `b404a177…` | **70 kontrolovaných návratů USB**: 37 běžných resetů, 8 alarmových návratů a 25 samostatně počítaných startů STA+BLE. Není to 70 deepsleep cyklů. |
| TinyUSB chyba | Upstream `a0249ada…` opravuje únik počítadla SETUP při plné frontě. Nativní mockovaný C test: před opravou FAIL 1/1, po opravě PASS 1/1, celá sada 7/7 a s přidaným testem pořadí 8/8. |
| Původní výpadky USB | Logy Macu dokládají skutečné chyby enumerace. Jejich příčinná souvislost s opravenou chybou TinyUSB **není prokázaná**; kontrolní firmware v nové sadě také procházel. |
| Wi-Fi | Samotné vypnutí bez odhlášení reprodukovalo tři neúspěchy, i bez resetu. Odhlášení a vyčkání na lokální link-down před vypnutím prošlo kontrolovanými testy. Celkem 54 úspěšných DHCP/HTTP transakcí; jedna seed transakce použila již připojenou STA. |
| Běžná cesta původní aplikace | Přesná funkce vypnutí Wi-Fi prošla v RAM; navíc 3× `lightsleep(2500) → soft_reset` a opětovné DHCP/HTTP. Celá soukromá aplikace s reálným serverem a displejem nebyla po nasazení znovu spuštěna. |
| Spotřeba s displejem | Historicky přibližně 3,82 → 0,60 → 0,37 mA na USB vstupu sestavy; poslední krok byl GP25. Nejde o odběr samotného RP2350, garantovanou hodnotu jiné desky ani dnešní REPL. S USB kandidátem se proud znovu neměřil. |
| Dlouhé spánky a displej | 30/75 minut a dřívější nové obrazy B prošly na dřívějším Mac firmwaru; nikoli automaticky na novém USB buildu nebo druhé desce. |

Neověřené zůstávají celý produkční cyklus a jeho energie, nové DNS/TLS testy,
BLE/AP přenosy s protějškem, zbývající kombinované/regresní sady, nový dlouhý
běh a měření USB kandidáta, fyzické jiné desky a RISC-V.
Všechny FAIL/NOT RUN zachovat; příchod USB, aktivace rádia a úspěšný HTTP přenos
jsou různé kontroly.

## 4. Převzetí zdrojů a build na druhém PC

Následující shellový postup je určen pro **Linux/macOS s dostupnými build
nástroji**, nikoli jako ověřený nativní Windows návod. Neinstaluje firmware.
Nejprve zjisti OS/architekturu a použij plný Arm GNU Toolchain pro daný host;
ověřená verze byla **14.3.Rel1 / GCC 14.3.1**, CMake 4.4.3. Potřebuješ Git,
GNU Make, host C/C++ compiler, Python 3 a target C knihovnu, nejen samotné GCC.
Pro USB zálohy je navíc potřeba host `picotool` s USB podporou; picotool,
který si CMake sestaví pro generování UF2, tuto podporu mít nemusí.

Použij nový adresář nebo nejdřív prověř vlastní rozpracované změny. Nepřepisuj
existující checkout pomocí `reset --hard` ani `submodule update --force`.

```sh
git clone --branch rp2/rp2350-timed-deepsleep \
  https://github.com/Rhiz3K/micropython.git micropython-rp2350-handover
cd micropython-rp2350-handover
git status --short
git merge-base --is-ancestor 0f193e89cbb0246ca4d967e1ad98db28304a031c HEAD

arm-none-eabi-gcc --version
arm-none-eabi-gcc -print-file-name=libc.a
cmake --version
python3 --version
```

`libc.a` musí být skutečný existující soubor. Do `PATH` dej binářky plného
Arm toolchainu. Ověř a odstraň případné zděděné nastavení jiného SDK,
RISC-V compileru, user C modulů či frozen manifestu; nový build adresář sám
neodstraní konfiguraci přenesenou prostředím. Nenastavuj staré `MICROPY_GIT_TAG`
a `MICROPY_GIT_HASH` jen pro napodobení runtime `.usbq1`.

```sh
unset MICROPY_GIT_TAG MICROPY_GIT_HASH BOARD_VARIANT
export CMAKE_ARGS='-DPICO_DEFAULT_RP2350_PLATFORM=rp2350-arm-s -DCMAKE_BUILD_TYPE=MinSizeRel -DPICOTOOL_GIT_BRANCH=6f6458d792b93685a11423b244a585eaa99eafcf -DPICOTOOL_FORCE_FETCH_FROM_GIT=1'
make -C ports/rp2 BOARD=RPI_PICO2_W BOARD_VARIANT= BUILD=build-handover-pico2w submodules

test "$(git -C lib/pico-sdk rev-parse HEAD)" = 98a542c1a62fb549ffb5d66a3e5892b06276b670
test "$(git -C lib/tinyusb rev-parse HEAD)" = b549ac1d84cbbe550c9590951e2290098b3fb16c
```

Každý neúspěšný příkaz nejdřív vyřeš; nepokračuj dalším krokem s chybnou
identitou závislosti. `CMAKE_ARGS` předávej **prostředím**, jak je uvedeno,
ne jako argument za `make`, který by přebil doplnění board parametrů.
Board varianta nastavuje obecné `rp2350`; ARM proto výslovně určuje
`PICO_DEFAULT_RP2350_PLATFORM=rp2350-arm-s`. Nepoužívej variantu `RISCV`.

Teprve **po inicializaci submodulů** aplikuj USB opravu v kořenovém
`lib/tinyusb`, nikoli v `lib/pico-sdk/lib/tinyusb`. Následující blok je pro
čistý TinyUSB v novém klonu:

```sh
test -z "$(git -C lib/tinyusb status --porcelain)"
git -C lib/tinyusb apply --check ../../experiments/rp2350-deepsleep/tinyusb-ep0-queue.patch
git -C lib/tinyusb apply ../../experiments/rp2350-deepsleep/tinyusb-ep0-queue.patch
git -C lib/tinyusb apply --reverse --check ../../experiments/rp2350-deepsleep/tinyusb-ep0-queue.patch
git -C lib/tinyusb diff --check
```

Na Macu už aplikovaná je. Pokud opačná kontrola projde v převzatém checkoutu,
porovnej celý diff se záplatou a nepřidávej ji podruhé. Očekávané změny jsou
`src/device/usbd.c` a `test/unit-test/test/device/usbd/test_usbd.c`.
Patch má SHA256 `ffbadfaa2a51af420e64e1bdb4fad55f1621646eb3bcd98e3d93eaa921076e4e`.
Samostatný `a52562b…` nebyl zahrnut; nepřidávej jej automaticky.

```sh
make -C mpy-cross -j4
make -C ports/rp2 BOARD=RPI_PICO2_W BOARD_VARIANT= BUILD=build-handover-pico2w -j4
python3 - <<'PY'
from pathlib import Path
import hashlib
p = Path('ports/rp2/build-handover-pico2w/firmware.uf2')
print(hashlib.sha256(p.read_bytes()).hexdigest(), p)
PY
```

Zkontroluj v configure/build logu skutečné `RPI_PICO2_W`, ARM platformu,
compiler a připnutý picotool; ulož logy, ELF/UF2/BIN, source commit a hashe
závislostí soukromě. Referenční hashe šesti core a čtyř TinyUSB souborů jsou
v [build-result.json](evidence/mac-20260928-usb-wifi/usb-fix-build/build-result.json).
Nový hash binárky je normální, ale novému buildu nelze přiřadit starý PASS.

**`reproduce.sh` je historický Linux x86_64 recept** pro upstream základ
plus `firmware.patch`; nevytváří dnešní společný GP25/USB kandidát.
Pro nový build používej tuto větev a postup výše.

## 5. Cílová deska: první kroky před zápisem

1. Vylistuj USB bez otevření portu: `python3 tests/ports/rp2/deepsleep/host.py list`
   (vyžaduje `pyserial`). Ověř, která fyzická deska je připojená, zda má displej,
   napájení a případný debugger. Port/VID/PID samotné nestačí; při nejasnosti
   se doptat na přiřazení, nevybírat první nalezený port.
2. Je-li REPL dostupný, načti model, `machine.unique_id()` a `os.uname()` do
   **soukromého** záznamu. Zjisti aktuální `boot.py`/`main.py` před restartem;
   otevření REPL může přerušit aplikaci. Nepoužívej natvrdo Mac port ani UID.
3. U původní neodpovídající linuxové desky znovu ověř aktuální stav. Pokud USB
   opravdu chybí, zajisti fyzické odpojení jediného napájení a normální připojení;
   případně BOOTSEL s vlastní ověřenou obnovou. Neopakuj slepě `trace=7` ani
   nekonečné pokusy o otevření zaseklého CDC.
4. Před flash/testy vytvoř nový privátní manifest pro tuto desku. Zálohuj
   firmware, celý filesystem a zvlášť užitečná backup slova. U originální
   Pico 2 W má úplná flash **4 MiB / 4194304 bajtů**. Ověř velikost, SHA256 a
   nezávislé `picotool verify`. Použij její skutečný BOOTSEL serial, který se
   může lišit od runtime serialu; žádné erase ani cizí full-flash obrazy.
5. Zajisti obnovu před první mutací. Autorizaci už poskytnutou pro stejnou desku
   neopakuj; nepřenášej však souhlas ani manifest na neidentifikované zařízení.
   Současně smí port ovládat jen jeden hostitelský proces.

Celá flash záloha desky A **není** instalační obraz desky B: obsahuje cizí
aplikaci, konfiguraci i případná tajemství. Firmware UF2 neobsahuje automaticky
zálohu filesystemu. Jeho nahrání ponechá `boot.py`/`main.py`, které se mohou
po rebootu ihned spustit; předem připrav bezpečný start s možností obnovy.

Při použití opt-in testů postupuj podle jejich README. Vytvářej nové názvy
runů/logů, první sada jen **3× 2500 ms**; další rozsah podle jejího výsledku.
Předávej stejný `--config` do `install` i `run`. `--replace-main` použij až po
ověřené záloze a posouzení autostartu. Nástroj mění RTC a všechna backup slova;
jejich původní hodnoty musí zůstat v privátním záznamu pro konečnou obnovu.
Jeho timeout plně neomezuje zaseklý hostitelský serial write/flush: použij i
vnější mez procesu a dostupnou fyzickou obnovu. Neočekávané selhání zastaví sadu.
Pokud brání spánku watchdog, EBUSY neobcházej libovolným zápisem do jeho
registrů. Aktivitu určuje bit ENABLE `0x40000000`, nikoli nenulový celý CTRL;
dřívější test právě toto chybně zaměnil. Obnova po BOOTSEL se musí řídit
aktuálně přečteným stavem a původem watchdogu, ne slepým spuštěním starého skriptu.

## 6. Wi-Fi a displej: co přenést do aplikace

**Oprava Wi-Fi není automaticky součástí samotného `machine.deepsleep()`.**
Před vypnutím ukončit síťové úlohy/callbacky a BLE, odhlásit aktivní STA,
vyčkat na lokální `status()==0` a `not isconnected()`, potom deaktivovat
rozhraní a provést deinit. Lokální link-down nedokazuje přijetí rámce AP.
Polling má limit 500 ms; synchronní příkaz disconnect má vlastní timeout.

Veřejný [Pico 2 W helper](pico2w_vsys_lowpower.py) navíc ověřuje GP23 LOW
(rádio vypnuté) a nastaví GP25/CS LOW (VSYS monitor vypnutý). Pokud se dříve
připojená STA nepotvrdí jako odpojená, po vypnutí vyvolá chybu. Před dalším
použitím musí ovladač znovu inicializovat rádio a jeho piny.
Formátování při commitu změnilo SHA helperu, ale nikoli AST; přesný testovaný
zdroj i [ověření shody](evidence/mac-20260928-usb-wifi/commit-format-checks.json)
zůstávají v důkazech.

Soukromé Mac `main.py` dostalo stejné řízené odhlášení do `_shutdown_wifi()`
a jednoho místa volání. Zachovává best-effort vypnutí s varováním při chybě.
**Stále používá lightsleep + soft reset, ne P1.7 deepsleep**, a nebylo do něj
plošně přidáno parkování displeje/GP25. Na druhé desce aplikaci nejdřív přečti;
přenes odpovídající malou změnu, nepředpokládej totožný soubor ani rozhraní.

Výchozí Wi-Fi režim veřejné opt-in sady ponechá rádio aktivní pro teardown
v core; **automaticky nevolá nový helper**. Taková sada testuje jinou situaci
než ověřenou aplikační přípravu. Pro ověření opravy použij výslovnou přípravu
a kontrolovaný endpoint; negativní kontrolu bez ní eviduj odděleně.
Síť, heslo, DHCP, DNS a HTTP cíl zjisti na novém místě. Heslo zadat lokálně
mimo Git, netisknout do chatu/logů. Veřejné `*.py.txt` jsou přesné záznamy
tehdejších sond, ne hotový přenosný host runner s novou identitou.

U stejného panelu platí DC/CS GP8/9, SPI1 CLK/MOSI GP10/11, RST/BUSY GP12/13;
fyzickou revizi a napájecí propojky ověř. Po dokončeném refresh/BUSY a
**skutečném panel sleep** zavolej [park_after_sleep()](pico_epaper29_lowpower.py).
Helper sám sleep příkaz neposílá. Potom už panel nečíst a vstoupit do spánku;
po bootu obnovit všechna GPIO/SPI a panel resetovat/inicializovat. Původní
vendor `init()` samo směry pinů nemusí obnovit a `ReadBusy()` nemá timeout.
Na jiném panelu nepřebírat GPIO registry ani uspávací sekvenci bez ověření.

## 7. Doporučené navazující ověření

1. Identita, dnešní stav a vlastní záloha cílové desky; malá USB/reset sada
   a 3 krátké alarmové návraty. Při novém USB FAIL uložit čas a log hostu;
   podle potřeby srovnat přímé připojení s hubem, nikoli zaměnit výsledek jiné desky.
2. Wi-Fi: cold boot, běžný reset, krátký deepsleep a lightsleep/soft-reset
   s řízeným odhlášením. Po každém návratu ověřit nové spojení, DHCP a přesné
   HTTP tělo; DNS/TLS přidat samostatně, pokud jsou součástí reálné aplikace.
3. Přečíst a cíleně integrovat aplikaci cílové desky; ověřit celý skutečný cyklus
   stažení → nový obraz → uspání → probuzení → další přenos. Funkční text na
   e-paperu vyžaduje vizuální kontrolu nového obrazu, ne pouze úspěšné SPI.
4. Teprve potom širší profily STA/AP/BLE, regrese a dlouhé spánky. Pro 30/75 minut
   samostatný run s jedním cyklem, host timeout delší než spánek a explicitní
   RTC tolerance. Dlouhé testy na druhé desce nebyly tímto předáním objednány.
5. Změřit aktuální odběr a energii celého cyklu s přesně zaznamenaným zapojením.
   Rozlišit holou desku/sestavu, USB vstup/3V3 a napájený vs. zaparkovaný panel.
   Předchozí 0,37 mA nelze automaticky přisoudit nové sestavě.

Po testech odstranit guard a testovací konfiguraci, ověřit soubory proti vlastní
záloze, obnovit backup hodnoty/RTC a uvést skutečný konečný stav aplikace.
Nové výsledky ukládat s jiným datem/deskou; původní důkazy se nepřepisují.

## 8. Co se přes Git nepřenese

Ve forku jsou firmware zdroje, oba veřejné helpery, opt-in testy, patche a
anonymizované výsledky. **Nejsou v něm** hotové UF2/ELF/BIN, původní/soukromé
`main.py`, hesla, celé flash zálohy, skutečné UID/serialy, privátní manifesty
ani host skripty s identitou konkrétní Mac desky.

Na Macu jsou privátní artefakty pod pracovním adresářem
`~/pico-work/rp2350-mac-20260927-112409/`, poslední USB/Wi-Fi práce v
`usb-wifi-20260928T082726Z/`. Relevantní položky jsou `usb-fix-build/firmware.uf2`,
`original-files/`, `app-candidate/main.py`, `checkpoint.json`,
`deployment-result-public.json` a vlastní ověřené flash obrazy u obou změn
firmwaru. Kopírovat je případně soukromě; hesla a dumpy nepublikovat.
Tyto zálohy patří Mac desce. Zálohy původní linuxové desky hledej na původním PC.
Pro práci pouze na firmwaru stačí nový klon a vlastní build; pro přenos
konkrétní aplikace je potřeba také její skutečný privátní zdroj.

Kontrolní součty veřejných artefaktů jsou v `SHA256SUMS`; na Linuxu ověřit
`sha256sum -c SHA256SUMS`, na Macu `shasum -a 256 -c SHA256SUMS` z této složky.

## Text pro dalšího asistenta

> Převezmi https://github.com/Rhiz3K/micropython/blob/rp2/rp2350-timed-deepsleep/experiments/rp2350-deepsleep/HANDOVER.cs.md
> a pokračuj na tomto PC a zde připojené desce. Poslední implementační commit
> je 0f193e89cbb0246ca4d967e1ad98db28304a031c, navazující commit je handover.
> Nejdřív ověř OS, zdroje, fyzickou identitu a současný stav desky; nesměšuj
> původní linuxové Pico s Mac Picem a nepoužívej cizí flash zálohu/UID.
> TinyUSB a024 je uložený patch, který nový klon nemá automaticky aplikovaný.
> Core patche už ve větvi jsou. Wi-Fi oprava vyžaduje přípravu aplikace;
> samotné deepsleep ji neprovádí. Zachovej soukromé soubory a zajisti vlastní
> ověřenou obnovu před zápisem. Navazuj na hotové výsledky, ověř novou sestavu
> postupně a neoznačuj staré PASS za nové. Upstream PR zatím nevytvářej.
