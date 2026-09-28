# Společný RP2350 deepsleep a příprava Pico 2 W — rozšířené testy

Rozšířená hardwarová validace z 27. 9. 2026. **Společný kandidát zůstává
experimentální a není připravený k odeslání upstream: opakovaně se ztrácelo USB
při běžném resetu/startu a příčina není určená.**

Časovaný P1.7 deepsleep a vypnutí měřicí cesty VSYS přes GP25 jsou nyní
spojené v jednom kandidátním firmwaru. Přímé nové A/B měření s připojeným
e-paperem dalo **0,60048 → 0,37178 mA**, tedy přibližně **38,1 %** méně.
V obou bězích Python před uspáním nastavil GP25 HIGH; nový firmware přebírá
jeho přípravu automaticky. Python helper pro GP25 nebyl na desce nainstalován.
Panel sleep a příprava jeho pinů zůstávají odpovědností aplikace.

## Přesný kandidát a sestava

- Základ upstream: `09f5bb447504a058376c62fe991b3613531837e6`.
- Testovaná větev: `764de396cf5893fd12cd6e70fd4edecb1b68c509` + změna GP25;
  runtime `v1.30.0-preview.88.g764de396cf.dirty` z 27. 9. 2026.
- Pico SDK 2.3.0: `98a542c1a62fb549ffb5d66a3e5892b06276b670`.
- Build picotool: `6f6458d792b93685a11423b244a585eaa99eafcf`.
- GCC 14.3.1, nativní ARM64 macOS build, MinSizeRel.
- Pico 2 W UF2 SHA256:
  `c5c308066fc70ecf91d94709d6e5515ff15756d892834417aadd85d685b62f2b`.
- Fyzicky testována druhá Pico 2 W, RP2350 A2 ARM, stále s Waveshare
  Pico-ePaper-2.9 B/W V2 296×128. Napájení jen přes JT-UM120 z USB hubu;
  samostatný PC port měřáku vede do stejného hubu.

Nová úplná 4MiB záloha flash byla nezávisle ověřena pomocí picotool.
Po nahrání kandidáta se znovu ověřil nezměněný souborový oddíl
`0x10180000..0x10400000` a přesný inventář původních i dočasných souborů.
Při následném běžném resetu se ztratilo potvrzení raw-paste přes USB.
Samostatná kontrola nového bootu, verze, čítače, reset cause a všech souborů
potvrdila úspěšný přechod; transportní událost nebyla započtena jako spánkový test.

Buildy `RPI_PICO2_W`, `RPI_PICO2` a `RPI_PICO` mají PASS, každý bez compiler
warnings. Hashe core souborů před/po sestavení jsou shodné. Pro RISC-V nebyl
k dispozici vhodný kompilátor: SKIPPED, nikoli PASS. Fyzický non-W Pico 2
se netestoval.

## Resetové a rádiové scénáře

Dokončené sady dohromady ověřily **120 alarmových probuzení**. Každá
úspěšná sada ověřila i následný obyčejný reset a zánik DEEPSLEEP_RESET.

| Scénář společného kandidáta | Ověřené deep wakes | Výsledek |
| --- | ---: | --- |
| Rádio neinicializované testovací sadou | 100/100 | PASS |
| STA aktivní, bez asociace k AP | 10/10 | PASS |
| Zabezpečené AP, první pokus | 0 | FAIL — bez prvního READY, USB zmizelo |
| Zabezpečené AP, samostatné opakování po obnově | 5/5 | PASS |
| BLE aktivní, bez protějšku | 5/5 | PASS |
| STA + BLE, resetová sada | 0 | FAIL — bez prvního READY, USB zmizelo |
| STA + AP | — | NOT RUN |
| CPU1, WDT, DMA, lightsleep-before, 0/1/20 ms | — | NOT RUN v tomto kandidátu |
| Šest regresních skriptů | — | NOT RUN; úvodní reset selhal ještě před prvním testem |
| Wi-Fi aktivní přes sleep, HTTP po každém bootu | — | NOT RUN |

Zbylé scénáře byly zastaveny po opakovaném výpadku USB. Starší výsledky
jiného firmwaru zůstávají v původních reportech; nenahrazují tyto nové běhy.
Observer dostává
stejnou privátní konfiguraci jako instalátor a před GO kontroluje identitu
běhu a profil, na konci také přesný počet dokončených cyklů. SLEEP řádky nejsou
potvrzované a při odpojení USB mohou chybět; počítají se ověřené nové booty.

Profily `never`, STA, zabezpečené AP, BLE, STA+BLE a STA+AP nechávají zvolená
rozhraní aktivní pro teardown firmwaru. AP musí po aktivaci do 10 s dosáhnout
firmware link status 3; WPA2 se nastavuje před aktivací. BLE kontrola ověřuje
aktivaci, bez advertisingu či protějšku. STA bez Wi-Fi transakce prokazuje
stav API, nikoli připojení k síti. Běhy nevolají Python přípravu GP25.

## Výpadky USB při běžném resetu

Prvních 100 alarmových návratů prošlo. Instalátor další STA sady ztratil
raw-paste EOF potvrzení při `machine.reset()`. Bez nové instalace se pozorováním
ověřil správný nový start a všech deset STA cyklů; původní transportní chyba
zůstala zvlášť zaznamenaná.

První AP sada nedodala žádný READY ani první spánkový výsledek a Pico se
nehlásilo ani v USB inventáři. Bylo napájené: následné samostatné 10s čtení
měřáku mělo 1 008 vzorků, průměr 22,90085 mA při 5,07032 V. Toto není
měření spánku ani lokalizace místa zastavení. Majitel připojil BOOTSEL;
flash po selhání byla zálohována a nezávisle ověřena, potom se obnovil dříve
ověřený guard a tentýž kandidátní firmware. Ověření celé obnovené flash,
souborového oddílu a přesných 34 souborů prošlo.

Následující obyčejný reset guardu bez aktivace rádia také neobnovil USB
během 25 s. První regresní pokus skončil ještě před spuštěním regresních
skriptů. Majitel provedl normální odpojení/připojení Pica. **Příčina výpadku
není prokázaná a nelze jej připsat AP nebo časovanému deepsleep.**

Tři kontrolní resety s 150ms prodlevou pro raw-REPL ACK a uzavření CDC portu
prošly, s přesnou kontrolou boot čítače i všech souborů. Instalátor nyní před
resetem vypíná raw-paste a používá tuto prodlevu. Jde o úpravu testovacího
transportu; nemění `machine.reset()` ve firmwaru a neprokazuje opravu USB
či závadu hubu. Původní chyby nejsou odstraněny z důkazů ani přepsány na PASS.

Samostatné AP, BLE a STA+BLE preflight kontroly s 8s watchdogem následně
prošly. Uložený dokončený krok, přijatá completion zpráva, FORCE reset reason,
právě jeden nový guard boot, obnova backup hodnot a inventář byly ověřeny.
Tyto tři běhy nepoužívaly deepsleep. Nová AP spánková sada má vlastní název
`ap-retry-5`, zatímco původní `ap-5` zůstává FAIL.

AP opakování i BLE sada pak prošly všemi pěti spánky. Následující STA+BLE
sada však opět nedodala první READY a USB se nevrátilo do 90 s, tentokrát
už s upraveným instalátorem. **Prodleva tedy neodstranila všechny výpadky.**
Není doloženo, zda tato sada vůbec dokončila inicializaci rádia; žádný její
spánek se nezapočítává. Další automatické sady byly zastaveny a vyžádána
obnova firmwaru před touto rozšířenou sadou. Přenosová chyba, neúspěšné
booty i následné úspěšné pokusy zůstávají oddělené.

## Nové přímé měření spotřeby

Všechny běhy mají 300 s, stejné napájení, rádio vypnuté, panel sleep + Hi-Z,
a ověřený GP25 HIGH těsně před `machine.deepsleep(300000)`.
Pozdní okno je vždy 235–295 s od přijetí RUN hostitelem, 6 000 vzorků.

| Firmware | Proud v pozdním okně | Výsledek |
| --- | ---: | --- |
| Dřívější `9a8542bb24`, bez automatické GP25 přípravy | 0,60048 mA | PASS |
| Společný kandidát, první běh | 0,37178 mA | PASS |
| Společný kandidát, druhý běh a displej | — | NOT RUN |

Oba dokončené návraty měly alarm cause 4, `HAD_SWCORE_PD`, wake source 64,
právě jeden nový guard boot a odpovídající posun RTC. Offline audit ověřil
CRC každého rámce, přesné mapování vzorků i pokrytí obou měřicích oken.
Žádné vzorky ani nezatížená reference nebyly odečteny či filtrovány.

Jde o proud USB vstupu celé sestavy, nikoli samotného RP2350. Měřák má
rozlišení 10 µA, nebyl nezávisle kalibrován a průměrování jeho systematickou
chybu neodstraňuje. Okno na konci 300 s neprokazuje úplné tepelné ustálení.
Energie celého cyklu včetně bootu, sítě a refresh není změřena.

## Wi-Fi a displej

Tři samostatné diagnostiky kandidáta po alarmovém/běžném/alarmovém bootu
prošly připojením, DHCP a HTTP 200 na dočasném lokálním serveru. Každá z nich
prováděla symetrický úplný deinit před i po připojení. Neprováděly DNS ani
kontrolu těla HTTP odpovědi. Nejde o důkaz opravy dříve reprodukovaného
Wi-Fi reconnect problému; protokol se liší od původního testu.

Resetová sada s aktivním Wi-Fi spojením přes deepsleep, kontrolní síťové
resety a nové A/B překreslení displeje jsou **NOT RUN**. Starší fotograficky
potvrzený obraz `B: GP25 SLEEP OK` není vizuální validací tohoto nového
společného firmwaru.

## Zdrojové soubory a reprodukovatelnost

Hashe po jednotlivých bězích jsou autoritativní. Core soubory po sestavení
kandidáta zůstaly beze změny. Během validace se opravil pouze hostitelský
instalátor; firmware tím nebyl přestavován ani měněn. Po ukončení hardwarových
sad se `device.py` pouze zformátoval Ruffem 0.11.6; úplné Python AST před/po
je shodné. Přesný testovaný zdroj a hashe jsou zachované v důkazech.

[Společný patch vůči upstream základu](combined-upstream.patch) obsahuje
core, dokumentaci a opt-in hardwarové testy pro jeden návrh PR. Historické
`firmware.patch` a `tests.patch` zůstaly beze změny. Experimentální reporty,
měřicí podklady a panelové helpery jsou materiálem forku a netvoří tento patch.
[Návrh PR](upstream-pr.md) zůstává neodeslaný.

## Obnova a omezení

**PASS, 2026-09-27T21:21:08.784101+00:00.** Přes BOOTSEL se nezávisle ověřila nová záloha flash po
STA+BLE selhání, obnovila celá dřívější flash a ověřila byte po byte. Na desce
je opět firmware před touto sadou `9a8542bb24`, nikoli společný kandidát.
Po BOOTSEL bootu zůstal watchdog s ENABLE=1 a nulovým zbývajícím časem;
jeho ENABLE byl bez resetu vymazán a výsledek přečten zpět.

Všech **29 původních souborů**, včetně `main.py`, souhlasí velikostí i SHA256
s novou zálohou bezprostředně před rozšířenými testy. Dočasné programy i
rádiové konfigurace byly odstraněny. UTC RTC a všechna původní backup slova
jsou obnovená a ověřená. STA/AP jsou neaktivní, WL_REG_ON=0, GP25 LOW,
panel má sleep/RST=0 a datové piny Hi-Z. Aplikace je **zastavená ve friendly
REPL**, nyní neběží ani není v deepsleep. Další reset spustí původní aplikaci;
původní aplikace stále nevolá naše nové optimalizační helpery.

Po obnově nebyla spuštěna další restartovací sada. Dočasný HTTP server
je ukončený a žádný záznam měřáku neběží.

[Sanitizované důkazy](evidence/mac-20260927-extended/README.md) obsahují
výsledky jednotlivých sad, původní selhání, power analýzy a 1s CSV, build
matrix a ověření obnovy. Hesla, originální aplikace, soukromé konfigurace,
inventáře souborů ani původní hodnoty backup registrů se neexportují.

Starší 30- a 75minutové testy patří dřívějšímu firmwaru a nejsou zde vydávány
za nové testy společného kandidáta. Samostatné AP klientské přenosy, BLE peer
komunikace, jiné desky/steppingy, RISC-V, fault injection a bezargumentový
spánek zůstávají mimo nové ověření. Původní aplikace se těmito testy neupravuje.
