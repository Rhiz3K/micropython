# Offline RouterOS DHCP parser

`parse_router_dhcp.py` uses Python 3.8+ and its standard library. It reads two
saved text files and writes JSON. It does not access a router, serial port or
network, start a capture, or change firmware. Its code and synthetic fixtures
are MIT licensed, like the surrounding repository.

From this directory, run the included **invented** example:

```sh
python3 parse_router_dhcp.py \
    fixtures/synthetic-frames.txt fixtures/synthetic-packets.txt \
    --target-mac 02:00:00:00:00:01 --expected-xid 0x12345678 \
    --output synthetic-result.json
python3 test_parse_router_dhcp.py
```

The fixtures describe a synthetic DISCOVER/OFFER/REQUEST/ACK exchange. They use
locally administered fictional MAC addresses and the documentation-only
`192.0.2.0/24` range. Their timestamps, identifiers and checksums were constructed
for parser tests; they are not hardware evidence. `synthetic-expected.json`
records independently generated frame hashes and checksum fields. Tests also
exercise an RFC 1071 checksum vector, corruption, missing/overlapping dump rows,
repeated rows, strict metadata parsing, VLAN headers, IPv4 options, DHCP option
overload and command-line output handling.

For a real saved capture, replace the two input paths and pass the client's
actual MAC as `--target-mac`. The optional `--expected-xid` requires a matching
target transaction; it accepts decimal or `0x` notation. It does not read RAM
or establish a DHCP BOUND state. No real identifier is embedded in the tool.

## Required input format

Both exports must describe the **same frozen capture in the same order**.
Acquiring and authorizing that capture is separate from this offline tool.

The first file contains one header and hexadecimal string per frame:

```text
FRAME *11 str 669
<hexadecimal encoding of the entire ASCII hexdump>
```

Here `str 669` is an example: the number is the decoded ASCII string's byte
length, **not** the Ethernet frame size. This is the format produced when
RouterOS packet `data` is a formatted hexdump string and that string is passed
through `:convert ... to=hex`. Direct raw-frame hex or PCAP is not this format.
Whitespace-only lines and line wrapping of the outer hex are accepted.

The decoded string has 16-byte rows such as `0000: ...`, two spaces between
the groups of eight bytes, a padded 48-character hex column and an ASCII
column. `*` means repetitions of the preceding complete 16-byte row. The next
explicit offset determines an interior repeat's extent; Ethernet header size
plus IPv4 `total_length` determines a trailing repeat's extent, including a
partial final row. An offset gap without `*` is rejected. Reconstructed bytes
are checked against IPv4 and UDP checksums and the separate packet lengths.

The second file is a RouterOS packet `print detail` text export, with entries
beginning with a decimal index followed by `time=...`. Required fields are:

```text
0 time=1.000 num=1 direction=rx src-mac=02:00:00:00:00:01
  dst-mac=ff:ff:ff:ff:ff:ff interface="synthetic fixture"
  src-address=0.0.0.0:68 (bootpc) dst-address=255.255.255.255:67 (bootps)
  protocol=ip ip-protocol=udp size=370 ip-packet-size=356
  ip-header-size=20 identification=1 fragment-offset=0
```

Additional `name=value` fields are accepted. Duplicate fields, unexplained
text, malformed quotes, duplicate/decreasing indices or packet numbers and
decreasing timestamps are rejected. Times must be nonnegative decimal seconds.
Frame IDs are not assumed to equal packet numbers: the ordered records must
agree on MACs, IPs, ports, sizes, header length and IP identification.

## Output and interpretation

The output preserves raw MAC/IP addresses and DHCP option values. It is
**private diagnostic data**, even if the input filenames or interface labels
were anonymized. Review/redact it separately before publishing. The file must
not already exist; on POSIX systems it is created with owner-only permissions.
The normal stdout summary contains counts and checksum results, not identifiers.

JSON includes input hashes, reconstructed frame hashes, repeat expansions,
BOOTP fields, raw DHCP options, message names, target matches and transaction
sequences grouped by xid. Router-relative timestamps remain separate from
`since_first_packet_ms`. A transaction sequence can be partial or contain
retries; successful parsing does not require or certify a complete DORA cycle.

The parser deliberately accepts a limited format: Ethernet IPv4, at most two
VLAN tags, unfragmented UDP on ports 67/68, Ethernet BOOTP clients and DHCP
message types 1–8. It requires END-terminated options with only zero padding
after END, including overloaded fields. Ethernet FCS/trailing bytes, zero UDP
checksums, empty captures and other packet types are rejected. A zero checksum
is legal in IPv4 UDP, but this tool cannot validate such a reconstructed packet
and therefore does not report it as checksum PASS. Export errors, unsupported
formats or an absent target yield a nonzero exit code; that is not a verdict
that DHCP or the hardware failed.

A router/VLAN capture observes packets at that capture point. It does not prove
Wi-Fi delivery to the client, over-the-air transmission/acknowledgment, client
acceptance of an OFFER/ACK, or the reason a packet is absent. Filters, capture
location, losses and offload can affect visibility. Matching a supplied xid
correlates external evidence; it cannot independently confirm RAM state.

Checksums validate reconstruction consistency, not authenticity. A hexdump is
not an independent raw capture, and header matches cannot distinguish reordered
identical retransmissions. Preserve the same-snapshot ordering assumption and
the original private exports when reporting results. Router timestamps do not
measure total boot, Wi-Fi association time, energy consumption or deepsleep
power state. These host tests verify the parser only.
