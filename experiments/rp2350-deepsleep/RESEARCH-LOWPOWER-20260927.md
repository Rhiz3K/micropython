# Další snížení spotřeby Pico 2 W s e-paperem

Webová rešerše k 27. 9. 2026. Nové návrhy níže jsou **NOT TESTED**;
během rešerše se s hardwarem ani firmwarem nepracovalo.

Nejvyšší prioritu má porovnání **USB napájení a napájení přes VSYS bez
VBUS**, se stále připojeným displejem. Pro ještě nižší odběr při dlouhých
intervalech dává smysl externí časovač a vypínání celé napájecí větve.
Další čistě softwarové zásahy mají podle nalezených podkladů menší potenciál.

## Výchozí doložený stav

[Poslední měření](POWER-GP25-MAC-20260927.md) této sestavy:
Pico 2 W / RP2350 A2, Waveshare Pico-ePaper-2.9 B/W V2, rádio vypnuté,
panel sleep + Hi-Z a GP25 LOW. V pozdním okně 300s spánku bylo naměřeno
**0,37077 mA při 5,08369 V, tedy 1,88489 mW** na USB vstupu. Alarmový boot
a nové vykreslení byly ověřeny automaticky i fotografií.

Jde o celé zařízení v testovacím spánku. Původní aplikace helpery dosud
nepoužívá, Wi-Fi připojení není vyřešené a energie celého cyklu nebyla
změřena. Poslední zdokumentovaný stav zařízení po obnově je REPL, nikoli
deepsleep; rešerše jeho aktuální stav znovu neověřovala.

| Možnost | Potenciál podle podkladů | Priorita |
| --- | --- | --- |
| VSYS bez VBUS | Odstranění významného stálého odběru USB napájecí cesty | První vratný A/B/A test |
| Externí časovač + vypínání celé větve | Největší prostor pro snížení standby, při zachování obrazu | Pro dlouhé intervaly |
| Audit napájení carrieru displeje | Neznámý; závisí na skutečné revizi a stavu napájecího spínače | Změřit před úpravou |
| Flash deep power-down | Malý čistý přínos, složitější boot | Až s přesnějším měřidlem |
| SSD1680 deep mode 2 | Typický rozdíl jen 0,3 µA na řadiči | Nízká priorita |
| Kratší aktivní fáze a méně refreshů | Může podstatně snížit energii cyklu | Samostatně od sleep proudu |

## 1. VBUS a napájení přes VSYS

[Samostatné schéma Pico 2 W, rev. 2, list 1](https://datasheets.raspberrypi.com/picow/pico-2-w-schematic.pdf#page=1)
ukazuje VBUS dělič R10 = 5,6 kΩ a R1 = 10 kΩ. Vlastní výpočet pro
nezatížený dělič při našem napětí:

`5,08369 V / (5 600 + 10 000 Ω) = 325,9 µA`.

To je významná stopa, **nikoli změřená úspora**. Tento dělič je jiná cesta
než VSYS monitor již vypnutý přes GP25. Bez změny napájecí cesty jej
samotné uspání RP2350 neodstraní.

Dokumentace navíc není jednotná:
[obecný datasheet Pico 2 W, obr. 8](https://datasheets.raspberrypi.com/picow/pico-2-w-datasheet.pdf#page=14)
uvádí R10 = 10 kΩ, což by dalo 254,2 µA. Stejný dokument v §3.5 doporučuje
VSYS při nepoužitém USB napájení. Osazení konkrétní desky a zatížení uzlu
zatím nebylo proměřeno. Nelze odečíst 326 µA od 371 µA a slíbit výsledek
45 µA.

Navržený experiment: 300s **A/B/A**, stejné helpery, připojený displej,
stejný řízený zdroj a měření. A = dosavadní USB; B = VSYS bez přítomného
VBUS a bez jiné napájecí cesty. Logování nesmí dodávat proud přes USB,
UART nebo SWD. Porovnat napětí, proud i příkon a po probuzení boot,
alarm, soubory a nový obraz. Výsledkem bude změna celé napájecí cesty,
včetně diody a USB stavu, nikoli izolované změření jednoho odporu.

Před zapojením je potřeba ověřit napájecí jumper carrieru; vstupní rozsah
samotného Pica není automaticky rozsahem displeje. Při různých napětích
porovnávat hlavně mW a energii cyklu.

## 2. Vypínání celé sestavy s ponechaným obrazem

E-paper může zůstat fyzicky připojený. Výrobce přímo u
[Pico-ePaper-2.9](https://www.waveshare.com/Pico-ePaper-2.9.htm)
uvádí zachování posledního obrazu po vypnutí napájení. Po dalším zapnutí
je však potřeba řádná inicializace řadiče a obnovení jeho dat.

**TPL5110 + napájecí spínač:** samotný časovač má typicky 35 nA při 2,5 V,
interval 100 ms–7200 s a napájení 1,8–5,5 V. Vyhovuje tedy i 30/75min
intervalům. Po dokončení práce MCU vyšle DONE. Logický vstup vyžaduje
HIGH alespoň 0,7×VDD; přímých 3,3 V z Pica proto není zaručené HIGH
při napájení časovače 5 V.
[TI TPL5110, str. 1, 5 a 10](https://www.ti.com/lit/ds/symlink/tpl5110.pdf)

**RV-3028-C7 + napájecí spínač:** RTC má typicky 45 nA při 3 V/25 °C,
s vypnutým CLKOUT, neaktivním I²C a bez aktivovaného backup switchingu.
Hodí se pro kalendářní čas nebo programovatelné intervaly. Manuál v §7.4
přímo ukazuje RTC, spínač a GPIO Hold, které udrží MCU zapnutý do dokončení
práce. Krátký countdown pulz vyžaduje správné zachycení; pozor také na
napájení vypnutého MCU přes I²C pull-upy.
[Micro Crystal, aplikační manuál, str. 106](https://www.microcrystal.com/fileadmin/Media/Products/RTC/App.Manual/RV-3028-C7_App-Manual.pdf#page=106)

Hodnoty 35/45 nA patří jednotlivým součástkám. Standby hotového zapojení
zahrne spínač, regulaci, odpory a úniky. Každé probuzení bude studený
start; Pico ztratí RAM, vlastní RTC a backup registry. Změní se tedy
aplikační kontrakt a je nutné dokončit refresh i zápisy před vypnutím.

Vypínat větev před rozdělením napájení Pica a panelu. Pouhé `3V3_EN=0`
ponechává proud jeho 100kΩ pull-upem z VSYS: přibližně 50 µA při 5 V.
Přítomný VBUS a samostatně napájený panel by vytvářely další cesty.
[Schéma Pico 2 W](https://datasheets.raspberrypi.com/picow/pico-2-w-schematic.pdf#page=1)

## 3. Regulátory a deska displeje

Pico 2 W používá **RT6154AGQW**. PS/SYNC ovládá WL_GPIO1 s pulldownem;
nízká úroveň umožňuje úsporný PFM. To je doložená výchozí konfigurace,
nikoli nově změřený stav TP4 během našeho spánku.
[Schéma Pico 2 W](https://datasheets.raspberrypi.com/picow/pico-2-w-schematic.pdf#page=1)

Richtek udává neswitchující Iq 20 µA typ./40 µA max. při EN=VINA a SYNC=0;
shutdown 0,1 µA typ./1 µA max. za EN=PS/SYNC=PGOOD=0. Jde o parametry IC,
nikoli odběr celé desky. Vynucené PWM by při malé zátěži účinnost zhoršilo.
[RT6154A/B, str. 7 a 13](https://www.richtek.com/assets/product_file/RT6154A=RT6154B/DS6154AB-05.pdf)

Zveřejněné [schéma carrieru Waveshare](https://files.waveshare.com/upload/6/62/Pico-ePaper-2.9.pdf)
obsahuje RT9193, tranzistory napájecí části ovládané RST a TXS0108E.
**Neobsahuje však fotografovaný jumper 3V3/VSYS**, takže přesnou revizi
uživatelova carrieru nepokrývá. Nelze slíbit, že změna jumperu obejde LDO.
[RT9193](https://www.richtek.com/assets/product_file/RT9193/DS9193-18.pdf)
má typicky 90 µA v zapnutém stavu; skutečný stav napájecích uzlů během
našeho spánku potřebuje měření. Pokud je carrier již vypnutý přes RST,
další spínač nemusí nic přinést.

Shutdown rádia rovněž není odpojené napájení. Starší výrobcův
[CYW43439 datasheet Rev. *B, kopie Avnet, tab. 38](https://www.avnet.com/wcm/connect/006d2e5f-b0e5-4c7a-a17b-6bb2e6af4503/CYW43439-Datasheet.pdf?CVID=o8u5DCc&MOD=AJPERES&attachment=false&id=1658360871631)
uvádí OFF typicky 3,5 µA z VBAT a 0,08 µA z VIO při 3,6/1,8 V, 25 °C,
obou REG_ON LOW a nezatížených pinech. Podmínky se liší od Pica;
nelze je použít jako přesný proudový rozpočet. Aktuální PDF Infineon bylo
při rešerši dostupné jen po přihlášení.

## 4. Další firmware: malé přínosy a důsledky pro probuzení

**Flash deep power-down:** Winbond W25Q32RV industrial Rev. B uvádí
standby 10 µA typ. a power-down 0,1 µA typ. při 3 V. Příkaz B9 tedy nabízí
úsporu zhruba 10 µA samotné flash; probuzení vyžaduje AB.
[Winbond datasheet, str. 49–50 a 70, kopie distributora](https://resources.ampheo.com/static/datasheets/winbond-electronics-corporation/w25q32rvsnjq.pdf#page=71)

[A2 boot ROM](https://github.com/raspberrypi/pico-bootrom-rp2350/blob/A2/src/main/arm/varm_generic_flash.c#L271)
v běžném flash bootu AB neposílá. Prosté přidání B9 před náš stávající
P1.7 proto není hotová optimalizace. Datasheet RP2350 §5.2.3 popisuje
probuzení flash pomocí POWMAN boot vectoru a kódu v zachované paměti.
P1.3 by mohl zachovat pinned XIP kód a stack; poté se vrátit do ROM.
BOOT0–3 nezasahují do našich `mem_backup` slov.
[RP2350 §4.4.1.3 a §5.2.3](https://datasheets.raspberrypi.com/rp2350/rp2350-datasheet.pdf#page=372),
[pořadí A2 bootu](https://github.com/raspberrypi/pico-bootrom-rp2350/blob/A2/src/main/arm/varm_boot_path.c#L525)

Zachování XIP ovšem spotřebovává proud: tabulka 1445 uvádí proti P1.7
o 7 µA více ve větvi VREG_VIN. Podmínky nejsou shodné s Winbond tabulkou
a vytištěné celkové příkony RP2350 nejsou aritmeticky konzistentní
s proudovými sloupci. Čistou USB úsporu nelze spolehlivě vypočítat.
[RP2350, tab. 1445](https://datasheets.raspberrypi.com/rp2350/rp2350-datasheet.pdf#page=1348)

**SSD1680 mode 2:** `0x10/0x03` místo `0x10/0x01` znamená podle Solomon
1 → 0,7 µA typ. při 3 V/25 °C; maximum obou režimů je 3 µA. Mode 2
nezachovává RAM, návrat vyžaduje hardwarový reset. Rozdíl 0,3 µA je
na úrovni řadiče a po vypnutí jeho napájení nemusí mít význam.
[Solomon SSD1680, str. 23 a 41, kopie Adafruit](https://cdn-learn.adafruit.com/assets/assets/000/097/631/original/SSD1680_Datasheet.pdf#page=41)

**Nový SDK a GPIO:** kontrolovaný `pico_low_power` nepřidává hlubší stav
než naše P1.7. Wrapper navíc používá SCRATCH6/7, které patří do kontraktu
`mem_backup`. Výchozí LP nastavení již přepíná regulátor a vypíná BOD;
náš kód potřebné přepínání odemyká. Zastavení LPOSC by zastavilo také
náš časovač. [SDK low_power](https://github.com/raspberrypi/pico-sdk/blob/master/src/rp2_common/pico_low_power/low_power.c),
[registry připnutého SDK](https://github.com/raspberrypi/pico-sdk/blob/98a542c1a62fb549ffb5d66a3e5892b06276b670/src/rp2350/hardware_regs/include/hardware/regs/powman.h)

Novější A3/A4 opravují E9, ale výměna desky nezaručí další úsporu:
vypnutí vstupních bufferů už bylo součástí naší optimalizace a rozšířený
test další pokles neprokázal.
[Raspberry Pi o A4/E9](https://www.raspberrypi.com/news/rp2350-a4-rp2354-and-a-new-hacking-challenge/),
[naše předchozí testy](POWER-OPT-MAC-20260927.md)

## 5. Jak poznat skutečné zlepšení

[JT-UM120](https://joy-it.net/en/products/JT-UM120) má rozlišení 10 µA
a přesnost ±0,05 % + 2 číslice. Hodí se pro dosavadní rozdíl asi 228 µA;
rozdíly jednotek µA jím spolehlivě nepotvrdíme. Průměrování neodstraňuje
systematickou chybu. Naše nezatížená reference kolem 55 µA nebyla
kalibrací a od výsledků se neodečítala.
[Záznam reference](POWER-MAC-20260927.md)

Pro další malé rozdíly použít mikroampérové měření s vhodným rozsahem
i pro boot a Wi-Fi špičky. Příkladem je
[Nordic PPK2](https://www.nordicsemi.com/Products/Development-hardware/Power-Profiler-Kit-2)
s profilováním 200 nA–1 A a 100 ksps. Má ale limit 5,0 V; náš USB zdroj
kolem 5,084 V nelze bez kontroly připojit do jeho měřicího vstupu.
Rozlišení přístroje samo o sobě není absolutní přesnost.

Nakonec změřit energii kompletního cyklu včetně připojení k síti,
refreshů a případných opakovaných pokusů. Ilustrační výpočet: dodatečný
odběr 100 mA po 1 s každých 300 s přidává průměrně 333 µA, tedy podobný
řád jako celý dnešní sleep. To není měření naší aplikace.

Nepřekreslovat nezměněný obsah. Partial refresh zvažovat až s ověřeným
obnovením obrazových RAM a periodickým full refresh; zatím jsme ověřili
full refresh po alarmovém bootu. Výrobce tyto podmínky popisuje v
[pokynech pro e-paper](https://www.waveshare.com/wiki/2.9inch_e-Paper_Module_Manual)
a [referenčním Pico driveru](https://github.com/waveshareteam/Pico_ePaper_Code/blob/c9bcd84db5adf5f085353649a8a5c31492bc5fb8/python/Pico_ePaper-2.9.py).

Praktické pořadí: **VSYS A/B/A → proměření napájení carrieru a celého
cyklu → externí časovač, pokud výsledek nestačí → drobné zásahy do flash
a panelového sleep režimu až podle přesnějšího měření.**
