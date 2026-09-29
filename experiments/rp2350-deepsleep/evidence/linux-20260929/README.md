# Veřejné důkazy omezené linuxové sady, 29. 9. 2026

Tyto soubory jsou odvozené z dokončených soukromých záznamů původní
linuxové Pico 2 W. Veřejný pseudonym `original-linux-pico2w` označuje jednu
desku; není odvozený z jejího UID, USB serialu ani MAC adresy. Neoznačuje
desku z Mac sady.

Záznamy patří firmwaru uvedenému v [build-result.json](build-result.json).
Vysvětlení experimentu a zbývajících omezení je v
[denním výsledku](../../RESULTS-LINUX-20260929.md). Tato složka neposkytuje
celkový PASS celého úkolu. Neobsahuje nové měření proudu ani energie,
100 cyklů, dlouhé spánky či kompletní test původní aplikace.

## Původ a přesné úpravy

`build-result.json` je byteově totožná kopie veřejně bezpečných build
metadat. Obsahuje pouze revize, konfiguraci a hashe firmwaru a patche.
`flash_sha256` v prvním záznamu `candidate-usb.json` je hash programové
oblasti nového firmwaru, nikoli hash soukromé úplné flash zálohy.

Ostatní JSON/JSONL byly vyexportovány pomocí výslovného seznamu povolených
klíčů; neznámý klíč export zastavuje. Na všech úrovních byly odstraněny
`uid`, `usb_serial` a `mac_hex`; ze závěrečného stavu také soukromý seznam
souborů `restored_paths`. Nahradily je veřejné `device_tag` v daném
objektu; tento tag byl přidán také ke každému vrchnímu záznamu. Přesné
odstraněné a přidané cesty pro každý soubor uvádí
[manifest.json](manifest.json). Cesta `$[n]` označuje položku JSON pole
nebo JSONL záznam s indexem od nuly.

Původní pořadí záznamů a všechny ostatní hodnoty jsou zachované, včetně
`host_time`, `host_start`, `host_finished`, reset cause, stavů DHCP, chyb a časů RTC.
Změnilo se pouze JSON formátování. `uname` zůstává celé; jeho nodename byl
ověřen jako obecné `rp2`. Zbývající texty byly zkontrolovány na soukromé
cesty a síťové adresy. Soukromé zdrojové záznamy nebyly upravené.

U položek `wifi_event` je `host_time` časem zpracování výstupu po návratu
celé sondy, nikoli přesný čas jednotlivé události. Pro jejich časový průběh
slouží původní `ticks_ms` a `connect_elapsed_ms`. Případnou korelaci s
routerovými logy nelze odvozovat pouze ze shodných hostitelských časů těchto řádků.

Nejsou publikovány přihlašovací údaje, soukromé skripty, obsah nebo inventář
filesystemu, úplná záloha flash, její hash ani surové výstupy routeru.
Tato redakce neodstraňuje FAIL záznamy a nemění je na PASS.

## Jak číst jednotlivé běhy

| Soubor | Doložený rozsah a konečný stav |
| --- | --- |
| [candidate-usb.json](candidate-usb.json) | Úvodní readback firmware a 3 běžné resety s návratem USB/REPL a cause 3. Úvodní záznam není další resetový test. |
| [minimal3.jsonl](minimal3.jsonl) | PASS: 3 × 2500 ms deep wake, kontrola RTC, backup regionu 2 a sentinelu; potom 1 běžný reset s konečným PASS. |
| [wifi-recovery.jsonl](wifi-recovery.jsonl) | FAIL hostitelské fixture `BrokenPipeError`: 1 HTTP transakce a vypnutí helperem prošly, následoval požadavek spánku; konečný úspěšný wake záznam v tomto souboru chybí. |
| [wifi-recovery-v2.jsonl](wifi-recovery-v2.jsonl) | PASS: 4 HTTP transakce a 3 kontrolované deep wake. Úvodní `initial_state` navíc zachycuje cause 4 po předchozí v1; není čtvrtým deep wake této sady. |
| [wifi-reset-lightsleep.jsonl](wifi-reset-lightsleep.jsonl) | FAIL: seed HTTP prošlo, 1 běžný reset vrátil USB/REPL; první reconnect zůstal bez DHCP a skončil timeoutem. Další plánované resety a lightsleep/soft reset se nespustily. |
| [wifi-dhcp-recovery.jsonl](wifi-dhcp-recovery.jsonl) | PASS samostatného zotavení: 1 HTTP transakce bez resetu. Nemění předchozí neúspěšný reconnect na PASS. |
| [wifi-lightsleep-only.jsonl](wifi-lightsleep-only.jsonl) | FAIL už při seed připojení bez DHCP; 0 HTTP transakcí a 0 spuštěných lightsleep/soft resetů. |
| [regressions.txt](regressions.txt) | PASS 8 kontrol: 6 hraničních argumentů, odmítnutí hard IRQ s EBUSY a samostatná kontrola obnovy frekvence/času po lightsleep. Byteově totožný výstup. |
| [final-state.json](final-state.json) | PASS obnovy původních 37 souborů a backup regionů 0/1/2; RTC obnoveno z původního stavu s přičteným časem hostu. Rádio a watchdog vypnuté, friendly REPL ověřený. Tento PASS nemaže předchozí síťové FAIL. |

Celkem síťové logy dokládají **7 úspěšných HTTP transakcí z 9 zahájených
sond**, dvě skončily bez DHCP. USB logy dokládají **5 běžných resetů**,
**6 přímo kontrolovaných deep wake** a jedno další alarmové probuzení
z v1 potvrzené následně v úvodním stavu v2. Nejde o sedm standardně
dokončených časovaných případů ani o sedm dalších probuzení vedle v2.
Síťové varianty lightsleep/soft reset se kvůli seed/reconnect selhání
nespustily; samostatná lightsleep kontrola v regresním skriptu ano.

HTTP úspěch zde znamená zaznamenaný návrat 200 a kontrolu přesného těla
odpovědi. Není důkazem DNS, TLS ani přenosu celé soukromé aplikace.
Požadavek spánku není úspěšné probuzení; plánovaný počet cyklů není
počet skutečně provedených cyklů. Čítače v manifestu počítají příslušné
doložené události jednotlivých souborů; souhrn rozlišuje druhy kontrol
a nezavádí celkový počet PASS celého úkolu.

V `minimal3.jsonl` je zářijové datum RTC úmyslně nastavené testem tak,
aby přešel přes půlnoc; `host_start` a `host_time` zůstávají skutečnými
hodnotami hostitelského záznamu. Závěrečná obnova RTC zachovává původní
datum 2021 s přičteným uplynulým časem, nikoli skutečné kalendářní datum
testu. Závěrečná kontrola byla dokončena 29. 9. 2026 v 06:23:50 UTC.
