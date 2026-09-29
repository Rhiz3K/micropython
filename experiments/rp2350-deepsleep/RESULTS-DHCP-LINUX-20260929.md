# Linux Pico 2 W: DHCP diagnostika a dvě opravy helperu, 29. 9. 2026

Opraveny jsou dvě konkrétní chyby experimentálního
[`pico2w_vsys_lowpower.py`](pico2w_vsys_lowpower.py): příprava GP23 po startu
bez inicializace rádia a falešné odmítnutí již lokálně odpojeného spojení
se zbytkovým stavem chyby autentizace. Obě mají skutečný hardware FAIL před
opravou a PASS po ní. **Příčina nestabilního Wi-Fi spojení není vyřešená.**
Vypnutí úspory rádia pomocí `PM_NONE` timeouty neodstranilo.

Samotný helper a jeho přenosná regrese jsou v malém samostatném
[commitu `0da78808c`](https://github.com/Rhiz3K/micropython/commit/0da78808c).
Offline diagnostické nástroje jsou oddělené v `bfd8ba9b8`.

Jde o navazující sadu na [ranní Linux testy](RESULTS-LINUX-20260929.md),
nikoli o přepsání jejich výsledků. Nově proběhlo **15 připojení: 12× DHCP
a přesné HTTP tělo PASS, 3× timeout bez DHCP BOUND**. Poslední připojení
patří samostatné regresi opraveného helperu. Neproběhl žádný nový deepsleep,
flashování ani zápis souboru na desku. Pět běžných resetů vrátilo USB/REPL.
Měření proudu a energie této sestavy zůstává **NEPROVEDENO**.

## Sestava a nezměněný firmware

Runtime UID i USB serial byly ověřeny proti soukromému manifestu. Stále jde
o původní linuxové **Pico 2 W / RP2350 ARM**, USB a uživatelem označený panel
**Pico-ePaper-2.9 B/W/R V4**. Panel nebyl ovládán. Router je MikroTik RB5009,
RouterOS 7.16.1; registrace Wi-Fi jsou spravované přes jeho Wi-Fi controller.
Adresy, SSID, identifikátory, přihlašovací údaje a plné pakety zůstávají soukromé.

Výchozí checkout je `c19140ec78dcfa2b733dac425a94f9e677583c08`.
Program v desce zůstává sestavený z `6f95bf43caab2f2ba693cbf91e82214e5b59f874`
s již doloženou TinyUSB opravou. Zpětné čtení prvních 889792 bajtů opět dalo
BIN SHA256 `77aea5317b92dae8bc486911170e2f7d4a27cb564d33bb116d14689f6ca2f32a`.
ELF SHA256 je `26dfaffbc72e158d073ab4b55cb469097f2c148e03ede8061d58be974044337b`.
Build příkazy, UF2 a toolchain jsou v předchozím záznamu; **nový firmware ani
nový build touto změnou nevznikl**. SDK zůstává na `98a542c1…`, CYW43 driver
na `055d64274b014dd7b1c2fc94d26e8a18face7124`. Core, SDK a společný network
kód nejsou touto opravou změněné.

## Malý patch a jeho hardware regrese

### GP23 po startu bez rádia

Po běžném resetu zůstával GP23/WL_REG_ON v muxu NULL (`FUNCSEL=31`). Volání
`WLAN.deinit()` u nikdy neinicializovaného rádia nic nepřepíná a starý helper
proto skončil `Expected SIO output low on GPIO 23`. Nastavený nízký SIO latch
a output-enable samy nedokládaly, že pin skutečně používá SIO.

Helper nyní po deinitializaci a ověření neaktivních WLAN explicitně provede
`machine.Pin(23, machine.Pin.OUT, pull=None, value=0)`. Až po kontrole muxu,
padů a výstupních registrů GP23 vypne monitorovací cestu přes GP25. `Pin` zapisuje nízký latch před
výběrem výstupu/SIO; pořadí nezavádí požadavek na zapnutí rádia. Zdrojové
souvislosti: `ports/rp2/mphalport.h`, `ports/rp2/machine_pin.c` a
`cyw43_deinit()` v připnutém driveru. `machine_pin_init()` samotný mux neresetuje.

První GP23 oprava prošla třemi samostatnými starty s `cyw43_poll == 0`
před i po helperu a přechodem muxu `31 → 5`. Následně přenosný
[`pico2w_vsys_lowpower_regression.py`](pico2w_vsys_lowpower_regression.py)
na čerstvém startu zachytil **původní helper FAIL → opravený PASS**. Konečná
verze s oběma opravami prošla ještě na dalším čerstvém startu. Tento skript
nepoužívá adresy závislé na ELF, nezapisuje flash a neresetuje desku. Jeho
docstring obsahuje přesné spuštění přes `mpremote ... resume run ...` a
nutné podmínky bezpečného autostartu, vypnutého BLE a zastavených pracovníků.

### Chyba autentizace může přežít shození linku

V `capture19` starý helper začínal při `status=3`, `isconnected=True`,
`netif.flags=127`, ale `wifi_join_state=4` (BADAUTH). Po `disconnect()`
za 20 ms přešel na `status=-3`, `isconnected=False`, `netif.flags=123`:
bit `LINK_UP=0x04` byl vymazán. BADAUTH zůstal, takže čekání na přesné
`status == 0` neprošlo ani po 500 ms. Rádio se přesto vypnulo a helper vyhodil
výjimku; nové připojení se v tomto pokusu vůbec nespustilo.

Obě kontroly nyní požadují `status <= 0 and not isconnected()`.
V připnutém `cyw43_tcpip_link_status()` současné `UP + LINK_UP` vždy vrací
NOIP=2 nebo UP=3. JOIN=1, NOIP=2 i UP=3 zůstávají odmítnuty. Záporný status
tedy může potvrdit lokální neprovozní stav; událost LINK-down na rozdíl od
DISASSOC nemusí vymazat starší `wifi_join_state`. Není to atomické čtení
registrů ani důkaz přijetí odpojení AP. Požadavek na zastavení dalších
síťových/BLE úloh, timeout, deinit a ověření výstupních registrů zůstávají.

Samostatný `shutdown-fix1` získal DHCP/HTTP za 3221 ms, pak zachytil stejný
skutečný průběh `status 3 → -3`, `netif 127 → 123`, `join_state=4`.
Opravený helper po 20 ms odpojení přijal a ověřil vypnutá WLAN a nízké GP23/25:
**PASS**. Původní `capture19` zůstává FAIL. Jde o opravu falešné chyby
pomocné funkce, nikoli autentizace nebo DHCP.

## Co ukázalo DHCP a Wi-Fi

Sonda v RAM vzorkovala status, DHCP state/tries/request_timeout, síťový
soft timer, netif flags a `wifi_join_state`. Adresy RAM byly odvozené
offline z přesného ELF, před použitím ověřeného SHA256 programové oblasti.
Jednotlivá čtení nejsou atomická. XID načtený přes `mem32` může být záporný;
při porovnání se síťovým rámcem se normalizuje `xid & 0xffffffff`.
Pozorování bylo průběžně posíláno přes USB asi jednou za sekundu. `trace=7`
nebylo zapnuto. Samotné počítadlo retries nedokládá úspěšné odeslání rámce.

Na routeru se dočasně spustil omezený sniffer pro MAC cíle, UDP 67/68 a jeho
DHCP VLAN, bez souboru a streamování. Po každém pokusu se zastavení i shoda
uloženého nastavení ověřily. Neměnila se konfigurace AP, DHCP, lease ani
routování. Metoda vychází z [RouterOS sniffer start](https://manual.mikrotik.com/docs/cli-reference/tool/sniffer/start/)
a [omezení packet snifferu](https://help.mikrotik.com/docs/spaces/ROS/pages/8323088/Packet%2BSniffer).
MAC filtr může vynechat broadcast odpovědi. Routerový capture bod neprokazuje
rádiové doručení, příjem klientem ani místo ztráty před tímto bodem.

- **Capture3:** kompletní DISCOVER/OFFER/REQUEST/ACK, shodný XID s klientem,
  kontrolní součty IPv4/UDP správné, celá zachycená výměna 15 ms; DHCP/HTTP PASS.
- **Capture10:** DHCP až za 32715 ms. Retry časovač fungoval, `tries` rostlo
  1→4. Ve 14 vzorcích byl BADAUTH a současně cached LINK_UP, takže Python
  hlásil jen status 2. První zachycený DISCOVER přišel až na konci čekání;
  DORA pak trvala 18 ms. Toto zdržení nebylo pomalou odpovědí DHCP serveru.
- **Capture12:** timeout 35002 ms, v omezeném capture žádný rámec. Jedenáct
  průběžných dotazů na router ukázalo sedm přítomností a čtyři absence klienta;
  přítomné registrace měly krátké uptime a příznak authorized. To spolu se
  střídáním stavů driveru podporuje nestabilní spojení, nikoli zastavený DHCP timer.
- **Capture15:** timeout i s PM_NONE. Router zachytil DISCOVER/OFFER/REQUEST/ACK
  a další REQUEST/ACK, klient však na konci stále nebyl BOUND. Samotné odeslání
  ACK routerem tedy není důkaz jeho přijetí a zpracování klientem.

Souvislost AUTH/PSK_SUP událostí s BADAUTH plyne z `cyw43_ctrl.c`; bez jejich
`type/status/reason` nelze určit konkrétní důvod. Neznamená to prokázané
špatné heslo. Podobné chování popisuje [pico-sdk #2153](https://github.com/raspberrypi/pico-sdk/issues/2153).
Obnova po ICV_ERROR z [cyw43-driver #130](https://github.com/georgerobotics/cyw43-driver/pull/130)
už v připnutém zdroji je; její opětovné přidání by tuto práci neřešilo.

### Omezené střídání Wi-Fi PM presetů

Preset byl výslovně nastaven po `active(True)` před `connect()` a jednou
přečten zpět. Ostatní postup byl stejný. Bez resetu/spánku mezi těmito pokusy:

| Preset | Pokusy | DHCP/HTTP PASS | Timeout | Časy úspěchů |
| --- | --- | ---: | ---: | --- |
| PM_PERFORMANCE, readback `0xa11142` | 12, 14, 16, 18 | 2/4 | 2 | 4833, 3121 ms |
| PM_NONE, readback `0x10` | 13, 15, 17 | 2/3 | 1 | 3261, 32899 ms |

Pokus 19 skončil ještě v přípravě a PM_NONE se nenastavilo; nepatří do jeho
jmenovatele. PM_NONE mění i listen/beacon parametry, takže srovnání neizoluje
jediný power-save bit. Sada je malá a pořadí může hrát roli. **Nepodporuje
nasazení PM_NONE jako opravy**; výchozí PM preset proto změněn nebyl.

## Výsledky a reprodukce

[Anonymizované důkazy](evidence/linux-20260929-dhcp/README.md) obsahují
samostatné výsledky, časové řady, routerové zprávy bez adres, přesné zdrojové
fragmenty sondy a otisky soukromých originálů. Nevydávají rekonstruovaný
hexdump za nezávislý rádiový záznam. Přidaný [offline parser](tools/README.md)
ověřuje formát, pořadí, hlavičky a IPv4/UDP checksums; jeho syntetické fixture
a unit testy jsou výslovně oddělené od hardware výsledků.

| Kontrola této navazující sady | Výsledek |
| --- | --- |
| Identita, přesný programový hash a USB/REPL | PASS |
| Captures 1–19: skutečně zahájená připojení | 11 PASS / 3 FAIL z 14 |
| Další připojení pro `shutdown-fix1` | 1 PASS |
| Helper před připojením, původní chyby | FAIL: 2/8/19 odpojení, 9 GP23 |
| První GP23 fix: tři čerstvé starty | 3 PASS |
| Přenosný test: starý → GP23 fix → konečný helper | FAIL → PASS → PASS |
| Odpojení se skutečným zbytkovým BADAUTH, nový helper | PASS |
| Pět běžných resetů, návrat USB/REPL a cause 3 | 5 PASS |
| Offline parser, syntetické testy | 18 PASS; nedokládají hardware sleep |
| Finální firmware + 37 souborů + backup data + běh RTC | PASS |
| Nové deep cykly, 100 cyklů, 30/75 min, DNS/TLS, lightsleep | NEPROVEDENO v této sadě |
| Proud, energie cyklu a uspání B/W/R V4 panelu | NEPROVEDENO |

Původní hostitelské chyby jsou zachovány zvlášť: capture1 neměl použitelný
packet capture kvůli interaktivnímu SSH, capture4 selhal před sondou při
parsování prázdného pole. První cleanup narazil na převzatou nesprávnou
podmínku backup slova před změnami; následná obnova vycházela ze skutečného
vstupního checkpointu. Tyto chyby nejsou DHCP timeouty ani selhání deep wake.

Kompilace Python helperu a přenosné regrese přes `mpy-cross`, host unit testy
a Ruff se provádějí bez přístupu k zařízení:

```sh
python3 experiments/rp2350-deepsleep/tools/test_parse_router_dhcp.py
mpy-cross/build/mpy-cross -o /tmp/pico2w-vsys-helper.mpy experiments/rp2350-deepsleep/pico2w_vsys_lowpower.py
mpy-cross/build/mpy-cross -o /tmp/pico2w-vsys-regression.mpy experiments/rp2350-deepsleep/pico2w_vsys_lowpower_regression.py
```

Obě kompilace i 18 testů prošly. Nové Python soubory prošly Ruff bez výjimek;
u existujícího helperu zůstaly původní stylové nálezy I001 a UP031. Kontrola
ostatních pravidel a formátu prošla; tyto dvě nesouvisející úpravy se do
hardware ověřeného patche nepřidávaly.

Helper byl při testech načten do RAM. **Není nově nainstalován do filesystemu
ani soukromé aplikace**; reset tuto kopii odstraní. Pro zopakování použít
uvedený RAM test. Neaktualizovat naslepo soubor v aplikaci. Klasifikace
RP2040/RISC-V, bezargumentového deepsleep a samotný core patch zůstávají
podle předchozího handoveru beze změn, bez nové hardware validace.

## Konečný stav a další krok

**29. 9. 2026 v 07:55:24 UTC:** friendly REPL odpovídá, frekvence 150 MHz,
STA/AP/BLE a watchdog neaktivní, GP23/25 registrově ověřené jako výstupy LOW.
Napětí na pinech nebylo nezávisle měřeno. Programový
hash i cesty/velikosti/SHA256 všech 37 souborů odpovídají vstupu. Všechny tři
backup regiony jsou obnovené, RTC nebylo přenastaveno a odpovídá vstupu plus
uplynulému času. Zachovaný `main.py` je dřívější harness čekající na GO.
Panel zůstal bez zásahu; jeho uspání se netvrdí. Sniffer je zastavený,
uložené nastavení nezměněné. Není potřeba flashovat nový UF2 kvůli těmto
dvěma Python opravám; obnovovací UF2 a BOOTSEL postup z předchozího předání platí.

Další užitečné ladění Wi-Fi má zachytit omezený RAM záznam AUTH/PSK_SUP/ICV/LINK
událostí a výsledky TX, případně současné logy příslušného AP. Vyžaduje
samostatný diagnostický build nebo další přístup k AP; v tomto kroku se
neprovedlo. Nepoužívat neomezený USB trace. Neměnit DHCP timeout ani síťovou
konfiguraci jen proto, aby timeout zmizel z výsledku. Upstream PR nebyl založen;
dosavadní [návrh PR](upstream-pr.md) zůstává k posouzení s těmito omezeními.
