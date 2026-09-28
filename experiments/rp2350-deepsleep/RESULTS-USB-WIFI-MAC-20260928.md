# USB a Wi-Fi na Pico 2 W — výsledky 28. 9. 2026

Výsledky uzavřeny ověřeným nasazením 28. 9. 2026 v 09:06:56 UTC.

## Výsledek a rozsah opravy

Wi-Fi závadu jsme reprodukovali také bez resetu a bez ztráty USB: po samotném
`WLAN.deinit()` první spojení prošlo, druhé skončilo stavem `-1` bez DHCP.
Odhlášení STA před vypnutím rádia problém v kontrolované sadě odstranilo.
Opravená příprava před spánkem proto výslovně ukončí spojení, počká na lokální
link-down a teprve potom deaktivuje a vypne rádio. Stejná sekvence byla
ověřena v samostatném helperu i ve funkci nasazené do původní aplikace.

Pro USB byl připraven firmware s minimálním upstream fixem chyby ve frontě
řídicích událostí TinyUSB. Chyba a oprava jsou prokázány nativním C regresním
testem. Kandidát na této desce prošel 70 návraty USB po resetu nebo alarmovém
probuzení. **Přímá příčina výpadků enumerace z předchozího dne zůstává
neprokázaná:** dnešní kontrolní firmware bez opravy také prošel a uvnitř
starších selhání nebylo zaznamenáno zaplnění fronty TinyUSB.

Testováno s připojeným Waveshare Pico-ePaper-2.9 B/W V2, napájení Pica pouze
přes JT-UM120 a USB hub podle potvrzeného zapojení. Tato sada neprováděla
nové měření odběru ani vizuální A/B validaci displeje. Základní příprava měla
30 souborů, včetně odloženého originálního `main.py` a jednorázového guardu.
Přihlašovací údaje zůstaly soukromé, síťové sondy je dostávaly pouze do RAM.

## Wi-Fi: řízené odhlášení proti pouhému vypnutí

| Scénář na předchozím firmwaru `9a8542bb24` | Výsledek |
| --- | --- |
| Řízené odhlášení, stejný boot | 3/3 PASS; další série 10/10 PASS |
| Jen `deinit()`, stejný boot | První spojení PASS; druhé FAIL za 3308 ms; třetí NOT RUN |
| Spojení ponechané aktivní přes běžný reset | Před resetem PASS; první reconnect FAIL za 3310 ms |
| Spojení ponechané aktivní přes deepsleep 2500 ms | Před spánkem PASS; první reconnect FAIL za 3308 ms |
| Samostatné zotavení po obou neúspěšných reconnectech | 2/2 PASS s řízeným cleanup |
| Řízené odhlášení před běžným resetem | 5/5 prvních reconnectů PASS |
| Řízené odhlášení před deepsleep 2500 ms | 5/5 prvních reconnectů PASS |

Důkazy: [samotné vypnutí](evidence/mac-20260928-usb-wifi/wifi-poweroff-three/events.jsonl),
[deset úspěšných spojení](evidence/mac-20260928-usb-wifi/wifi-graceful-ten/events.jsonl),
[neúspěch po běžném resetu](evidence/mac-20260928-usb-wifi/wifi-abrupt-after/events.jsonl),
[neúspěch po alarmovém probuzení](evidence/mac-20260928-usb-wifi/wifi-deep-abrupt-after/events.jsonl).
V obou resetových negativních kontrolách se USB úspěšně vrátilo ještě před
selháním Wi-Fi. V testu bez resetu se nezměnily backup registry ani reset cause.

Záporný stav `-1` znamená selhání připojení v ovladači; žádný z těchto tří
pokusů nedostal DHCP adresu. Nejde tedy jen o opožděný DNS či HTTP požadavek.
Odpovídá to hypotéze, že AP dále eviduje neukončenou asociaci, a podobnou
zkušenost popisuje [pico-sdk #1373](https://github.com/raspberrypi/pico-sdk/issues/1373#issuecomment-1687037861).
V této sestavě však nebyly pořízeny rádiové pakety ani log ASUS; konkrétní stav
AP, přijetí odhlašovacího rámce a účinek každého dílčího kroku sekvence nejsou
samostatně prokázány.

Každá úspěšná sonda vyžadovala `ipconfig('has_dhcp4')`, stav připojení,
HTTP 200 a přesné tělo obsahující jedinečnou cestu daného testu. Server byl
lokální a použitá adresa číselná: **žádné tvrzení o otestovaném DNS, TLS nebo
internetovém serveru**. Sonda neopakuje neúspěšný první pokus automaticky.

Konečný součet z dokončených síťových sond:
**58 požadovaných cyklů, 57 zahájených,
54 úspěšných transakcí, 3 neúspěšné a
1 nespustěný cyklus**. Součet obsahuje i navazující sondy
helperu a aplikace; nejde o stejný počet nezávislých testů spánku. Jedna seed
transakce po chybě aplikačního testovacího prostředí využila stále připojené
STA a trvala 11 ms; všechny úspěchy proto nelze označit za čerstvé asociace.
Konečné počty určuje [manifest](evidence/mac-20260928-usb-wifi/manifest.json).

## Helper a funkce původní aplikace

Veřejný helper `radio_off_and_disable_vsys_monitor()` zachovává API a ochranu
pro Pico 2 W. Aktivní STA odhlásí, nejvýše 500 ms čeká na lokální link-down,
teprve potom deaktivuje rozhraní a provede deinit. Samotný příkaz disconnect
má ještě vlastní timeout ovladače. Neaktivnímu rozhraní nevolá zbytečně
`active(False)`, které by mohlo rádio inicializovat pouze kvůli vypnutí.

Po vypnutí zůstaly fyzické kontroly GP23/WL_REG_ON i GP25/CS, včetně muxu,
padů, směru a výstupní úrovně. Pokud se původně připojená STA v limitu
nepotvrdí jako odpojená, rádio a monitor cesta se vypnou a helper vyvolá
`OSError`. Před jeho použitím musí být zastaveny síťové úlohy a výslovně
vypnuté Bluetooth. Nemění USB, displej ani soubory.

Hardwarově testovaná verze má SHA256
`47cee7235cab22ffbcc756a2094741630ef0571d57f9bf9a0f1d4df96d29d1b8`.
Šest offline testů ověřilo pořadí vypnutí, timeout, nikdy nezapnuté rádio,
přetečení časovače, board gate a fyzickou kontrolu GP23.
Na hardwaru bylo ověřeno **16 úspěšných samostatných
volání helperu**; výsledky zaznamenávají SHA zdroje i verzi firmwaru.
Přesná kopie zdroje je [helper-source.py.txt](evidence/mac-20260928-usb-wifi/helper-source.py.txt).
Před commitem byl aktuální helper pouze přeformátován pomocí Ruff. Jeho
AST zůstává totožné a všech šest offline kontrol znovu prošlo; původní
hardwarové důkazy se nepřepisovaly. Oba hashe a shodu C zdrojů dokládá
[kontrola formátování](evidence/mac-20260928-usb-wifi/commit-format-checks.json).

Nasazená funkce původní aplikace byla zkoušena odděleně v RAM. Její
součet je **9 úspěšných funkčních případů**, včetně kontrol
před dvěma běžnými resety, třemi alarmovými spánky a třemi případy
lightsleep se soft resetem. Soukromý zdroj původní
aplikace ani jeho diff se nezveřejňují; výsledky obsahují pouze hashe a
ověřené stavy. Test funkce a síťová sonda nenahrazují spuštění celé aplikace
s jejími servery, dlouhými intervaly a překreslením panelu.

[Validace aplikační změny](evidence/mac-20260928-usb-wifi/app-validation-public.json)
potvrzuje šest izolovaných případů, kontrolu syntaxe a shodu zbývajícího AST.
Kromě `_shutdown_wifi` se změnilo jediné místo běžné cesty stahování/obrazu,
které nyní použije společnou odhlašovací funkci místo přímého vypnutí STA.
Ostatní funkce a kód modulu zůstávají po této přesně vymezené normalizaci
shodné. Potřebné globální závislosti byly ověřeny v rozsahu skutečného modulu.

Aplikační funkce zachovává svůj dosavadní tolerantní cleanup: při timeoutu
odhlášení nebo výjimce zaloguje varování a pokračuje ve vypnutí rádia.
To je odlišné od veřejného VSYS helperu, který při nepotvrzeném odhlášení
původně připojené STA po vypnutí vyvolává chybu. Aplikační změna nemění
lightsleep/deepsleep, reset, GP25, captive portal ani autostart.

První aplikační fixture skončila FAIL: její RAM namespace neobsahoval původní
globální `network`, funkce zachytila `NameError` a STA zůstala připojená.
Současně logger původně počítal očekávanou informační zprávu jako varování.
Testovací prostředí bylo opraveno doplněním závislosti a přesným rozlišením
úspěšného info od varování; kandidátní aplikace se kvůli tomu neměnila.
**V neúspěšném pokusu se nevyžádal reset ani spánek.** Původní FAIL i
[záznam opravy fixture](evidence/mac-20260928-usb-wifi/app-fixture-fix.json)
zůstávají zachované, oddělené od hardwarových výsledků.

### Původní cesta lightsleep + soft reset

Prošly všechny **3/3** případy původní aplikační cesty:
`machine.lightsleep(2500)` následované `machine.soft_reset()`.
Naměřená doba spánku byla ve všech třech případech 2501 ms; každý případ
potvrdil právě jeden start guardu a nezměněný hardwarový reset cause.
Před každým během prošla Wi-Fi/HTTP sonda a přesná odhlašovací funkce aplikace.
Viz [první](evidence/mac-20260928-usb-wifi/app-soft-app-soft-1/result.json)
a [třetí](evidence/mac-20260928-usb-wifi/app-soft-app-soft-3/result.json) výsledek.

Jde o soft reset, **nikoli `machine.reset()` ani timed deepsleep**. USB se zde
nemusí znovu enumerovat; tyto tři případy nejsou zahrnuty ve 114 hardwarových
návratech níže. Ověření izolované cesty neznamená kompletní běh celé aplikace.

## USB: porovnání tří variant

| Firmware | Běžné resety s návratem USB | Alarmová probuzení | Boot sondy rádia | Celkem |
| --- | ---: | ---: | ---: | ---: |
| Předchozí `9a8542bb24` | 19 | 6 | 6 | 31 |
| Společná změna bez USB opravy, UF2 `c5c308…` | 0 | 3 | 10 | 13 |
| Společná změna + TinyUSB a024, runtime `.usbq1` | 37 | 8 | 25 | 70 |
| **Celkem úspěšných kontrolovaných návratů** | **56** | **17** | **41** | **114** |

Boot sondy rádia nejsou další položkou zahrnutou v prvním sloupci. U kandidáta
jde o 20 časných a 5 hostem spuštěných aktivací STA+BLE; kontrolní společný
firmware prošel 10 časnými aktivacemi STA+BLE. Tyto sondy dokazují start,
aktivaci, cleanup a stav guardu, **nikoli BLE komunikaci s protějškem ani
asociaci STA/AP klienta**.

Kandidát obsahuje 30 běžných resetů základní sady, 5 běžných a 5 alarmových
cyklů s veřejným helperem a 2 běžné + 3 alarmové cykly s aplikační funkcí.
Použitý alarmový spánek je 2500 ms. Základní kontroly starého firmwaru prošly
jak se samostatným 250ms odpojením pull-up (3 cykly), tak bez něj (10 cyklů).
USB kandidát **nepřidává povinný detach delay do firmwaru**. Host při testech
používá 150ms odklad před resetem pro dokončení REPL komunikace; ověření se
proto nevztahuje na libovolný hostitelský protokol bez tohoto odkladu.

Původní `usb-graceful-deep-1` FAIL byl chybnou hostitelskou precondition:
CTRL `0x07000000` obsahoval pause-on-debug příznaky, ale ne ENABLE
`0x40000000`. Kontrola byla opravena z porovnání celého registru na test
ENABLE bitu. Žádný watchdog registr se neměnil a **reset nebyl vyžádán**;
tento případ se nepřičítá k USB výpadkům ani ke 114 návratům.
Viz [záznam opravy](evidence/mac-20260928-usb-wifi/wdt-precondition-fix.json).

## Logy Macu a hranice příčinného vysvětlení

[Zpětný rozbor tří selhání z 27. 9.](evidence/mac-20260928-usb-wifi/host-usb-log-evidence.json)
ukazuje u prvního AP startu, běžného resetu bez rádia a STA+BLE startu stejnou
posloupnost: STALL řídicího endpointu, neplatný fragment device descriptoru,
7 neúspěchů při přiřazování adresy a trvalé selhání enumerace. Proto šlo o
chybu USB enumerace, nikoli pouze o zavřený či obsazený sériový port.

[Kontrolní okno kandidáta](evidence/mac-20260928-usb-wifi/host-usb-candidate-log-evidence.json)
od 08:49:25 do 08:59:16 UTC zaznamenalo 66 úspěšných enumerací a 66 odpojení,
žádný STALL, neplatný descriptor ani chybu enumerace cílového portu.
Tento počet obsahuje také přechody při změně firmwaru a není totožný s počtem
kontrolovaných resetů; okno končí před posledními aplikačními testy.

Samotné hlášení `hardware connection lost` se objevuje i při úspěšném resetu.
Není důkazem ručního vytažení kabelu. Ztráty obou větví hubu v pozdějších
intervalech ruční obnovy jsou zaznamenány zvlášť, bez přisouzení příčiny.
Žádný z těchto hostitelských logů sám neprokazuje pád MCU, stav Wi-Fi ani
zaplnění fronty TinyUSB. Úspěch kontrolní neopravené varianty znamená,
že současná hardwarová sada nevytváří deterministické USB FAIL/PASS srovnání.

## Minimální USB oprava a reprodukovatelnost

Připnuté TinyUSB `b549ac1d84cbbe550c9590951e2290098b3fb16c` obsahuje chybu:
při zahození SETUP události kvůli plné frontě zůstane zvýšené počítadlo
čekajících událostí a další řídicí požadavek může být přeskočen.
Upstream [a0249ada](https://github.com/hathach/tinyusb/commit/a0249ada9096365697340031a7b4a285beb18a2b)
vrací počítadlo při neúspěšném vložení. Použitý produkční rozdíl má +4/−2
řádky v `src/device/usbd.c`; další upstream commit `a52562b` není aplikován.

[Nativní C validace](evidence/mac-20260928-usb-wifi/usb-unit-tests/summary.json)
reprodukovala izolovaný oficiální test jako FAIL 1/1 na původním zdroji a PASS
1/1 po opravě. Celá opravená sada prošla 7/7; s lokálním testem pořadí resetu
a již zařazeného SETUP prošla 8/8. Dvě chyby původní celé sady nevydáváme
za dvě nezávislé regrese: první ponechala stav a kontaminovala navazující test.
C fixture používá mock DCD, nikoli fyzický USB řadič.

[Sestavení kandidáta](evidence/mac-20260928-usb-wifi/usb-fix-build/build-result.json)
pro Pico 2 W ARM prošlo bez varování kompilátoru. Runtime:
`v1.30.0-preview.88.g764de396cf.dirty.usbq1`.
UF2 SHA256:
`b404a1771bf0097a07709848cd296ff6a2eb755f1d7cf25a10395a8f346f0a43`.
Kontrolní společný UF2 má SHA256
`c5c308066fc70ecf91d94709d6e5515ff15756d892834417aadd85d685b62f2b`.
Přechody firmwaru zachovaly obsah filesystemu a byly ověřeny zpětným čtením.

Samostatná [přesná upstream záplata](tinyusb-ep0-queue.patch) zachovává
původní autorství a hash; SHA256 je
`ffbadfaa2a51af420e64e1bdb4fad55f1621646eb3bcd98e3d93eaa921076e4e`.
Na **čistém připnutém TinyUSB** se z kořene hlavního repozitáře aplikuje takto:

```sh
git -C lib/tinyusb apply --check ../../experiments/rp2350-deepsleep/tinyusb-ep0-queue.patch
git -C lib/tinyusb apply ../../experiments/rp2350-deepsleep/tinyusb-ep0-queue.patch
```

V aktuálním pracovním stromu již aplikovaná je. Gitlink TinyUSB zůstává na
`b549ac1d…`; commit hlavního repozitáře sám neuloží necommitované změny uvnitř
submodulu. `combined-upstream.patch` obsahuje core/docs/opt-in testy a tuto
USB záplatu **neobsahuje**. Následný firmware build potřebuje obě části.
Přesné hashe šesti core souborů, čtyř TinyUSB souborů, verzí závislostí,
argumenty CMake a prostředí pro runtime suffix jsou v build-result.json.
Build používá ARM GCC 14.3.1, SDK 2.3.0, board `RPI_PICO2_W`, platformu
`rp2350-arm-s`, vlastní build adresář a čtyři paralelní úlohy. Záznam slouží
k reprodukci zdrojů a nastavení; jiný čas a prostředí buildu nemusí dát
byteově stejný UF2. Hotové UF2/ELF/BIN a ověřené zálohy jsou uloženy soukromě.

Přidaný osmý test je uložen jako
[testovací patch](evidence/mac-20260928-usb-wifi/usb-unit-tests/reset-queued-setup-test.patch),
odděleně od firmware opravy. Nemění produkční kód a testuje mockovaný DCD.

Jde o místní downstream backport do závislosti a aplikační změnu odhlašování,
ne o nový upstream USB algoritmus. Toto šetření automaticky nerozšiřuje
rozsah připraveného PR na timed deepsleep a GP25. Publikace výsledků a patchů ve forku
neznamená připravenost k odeslání upstream; upstream PR nebyl založen.

## Konečný stav zařízení

[Ověřené nasazení](evidence/mac-20260928-usb-wifi/deployment-result-public.json)
prošlo v 09:06:56 UTC. V desce zůstává runtime `.usbq1` a UF2 s SHA256
`b404a1771bf0097a07709848cd296ff6a2eb755f1d7cf25a10395a8f346f0a43`.

Všech **29 souborů** bylo ověřeno zpětným čtením: **28 souborů zůstalo
byteově totožných**, jediná záměrná změna je minimální oprava `main.py`
(SHA256 `dd5d46130dd872b5849c4328e17ce06363067d72356778542fb7deaf50b3d6b9`).
Původní `main.py` má ověřenou soukromou zálohu. Všechny dočasné testovací
soubory a guardy jsou odstraněné, backup registry obnovené a RTC ověřené.
Rádio je vypnuté, displej zaparkovaný, **aplikace zastavená v REPL**.
Plný autostart aplikace nebyl po nasazení spuštěn. Dočasný hostitelský HTTP
server byl po nasazení ukončen.

## Limity

Celá původní aplikace s reálným vzdáleným serverem a displejem nebyla touto
sadou validována od startu až po další plánovaný dlouhý cyklus. Nově nejsou
ověřeny DNS/TLS, přenosy BLE/AP s protějškem, dlouhé spánky na kandidátu,
RISC-V či jiné fyzické desky, aktuální odběr nebo nová fotografie displeje.
Starší dlouhé spánky a měření z 27. 9. zůstávají důkazy pro tehdejší firmware,
nikoli náhradou těchto chybějících testů. Četnost vzácných budoucích USB
výpadků nelze z omezené série odvodit jako nulovou.
