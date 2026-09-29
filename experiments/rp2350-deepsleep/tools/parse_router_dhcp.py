#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Parse saved RouterOS hex-encoded packet hexdumps; never contacts a device.

Input is the output of FRAME <id> str <length>, then :convert data to=hex.
The decoded data is RouterOS's 16-byte/line ASCII hexdump, including '*'
compression. Output contains private MAC/IP/options: do not publish unchanged.
Detailed packet print and frame export must come from the same frozen snapshot;
their ordering is cross-checked against all available Ethernet/IP/UDP fields.
"""

import argparse
import hashlib
import ipaddress
import json
import os
import re
import shlex
import struct
from decimal import Decimal
from pathlib import Path


class ParseError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise ParseError(message)


def checksum(data):
    """RFC 1071 one's complement checksum; 0 means a valid received packet."""
    if len(data) & 1:
        data += b"\0"
    total = sum(struct.unpack(f"!{len(data) // 2}H", data))
    while total >> 16:
        total = (total & 0xFFFF) + (total >> 16)
    return (~total) & 0xFFFF


def mac(data):
    return ":".join(f"{b:02x}" for b in data)


def normalize_mac(value):
    require(bool(re.fullmatch(r"(?:[0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}", value)), "invalid MAC")
    return value.lower()


def ip_layout(data):
    require(len(data) >= 14, "truncated Ethernet header")
    kind = int.from_bytes(data[12:14], "big")
    offset = 14
    while kind in (0x8100, 0x88A8):
        require(offset <= 18 and len(data) >= offset + 4, "invalid VLAN header")
        kind = int.from_bytes(data[offset + 2 : offset + 4], "big")
        offset += 4
    require(kind == 0x0800, "only Ethernet IPv4 captures are supported")
    require(len(data) >= offset + 4, "missing IPv4 length")
    require(data[offset] >> 4 == 4, "wrong IP version")
    ihl = (data[offset] & 15) * 4
    total = int.from_bytes(data[offset + 2 : offset + 4], "big")
    require(20 <= ihl <= 60 and total >= ihl + 8, "invalid IPv4 lengths")
    return offset, ihl, total


def reconstruct_dump(dump):
    data = bytearray()
    previous = None
    repeat_pending = False
    expansions = []

    def expand_to(end):
        count = end - len(data)
        require(
            count > 0 and end <= 65575 and previous is not None and len(previous) == 16,
            "invalid '*' expansion",
        )
        expansions.append({"offset": len(data), "bytes": count, "pattern_hex": previous.hex()})
        data.extend((previous * ((count + 15) // 16))[:count])

    for line in dump.splitlines():
        if line.strip() == "*":
            require(
                not repeat_pending and previous is not None and len(previous) == 16,
                "unexpected '*'",
            )
            repeat_pending = True
            continue
        match = re.match(r"^([0-9a-fA-F]{4,8}): ", line)
        require(match is not None, "invalid hexdump line")
        offset = int(match[1], 16)
        width = len(match[0])
        require(
            len(line) >= width + 50 and line[width + 48 : width + 50] == "  ",
            "invalid hexdump columns",
        )
        field = line[width : width + 48]
        require(
            bool(re.fullmatch(r"(?:[0-9a-fA-F]{2} +){0,15}[0-9a-fA-F]{2} *", field)),
            "invalid hex column",
        )
        block = bytes.fromhex(field)
        require(1 <= len(block) <= 16 and offset % 16 == 0, "invalid hexdump offset/block")
        if repeat_pending:
            require(
                offset % 16 == 0 and offset > len(data) and len(data) % 16 == 0,
                "invalid repeat gap",
            )
            expand_to(offset)
        else:
            require(offset == len(data), "unexplained gap or overlapping hexdump offset")
        repeat_pending = False
        data.extend(block)
        previous = block
        require(len(data) <= 65575, "oversized frame")

    ip_offset, _, total = ip_layout(data)
    expected = ip_offset + total
    if repeat_pending:
        expand_to(expected)
    require(len(data) == expected, "frame length differs from Ethernet + IPv4 total_length")
    return bytes(data), expansions


def read_frames(path):
    frames = []
    current = None
    encoded = []

    def finish():
        if current is None:
            return
        joined = "".join(encoded)
        require(
            bool(joined) and len(joined) % 2 == 0 and bool(re.fullmatch(r"[0-9a-fA-F]+", joined)),
            "invalid outer hex",
        )
        payload = bytes.fromhex(joined)
        require(
            len(payload) == current["dump_length"], "FRAME length does not match decoded string"
        )
        try:
            dump = payload.decode("ascii")
        except UnicodeDecodeError as exc:
            raise ParseError("non-ASCII hexdump") from exc
        frame, expansions = reconstruct_dump(dump)
        frames.append({**current, "data": frame, "repeat_expansions": expansions})

    for line in Path(path).read_text(encoding="ascii").splitlines():
        if not line.strip():
            continue
        match = re.fullmatch(r"FRAME (\S+) str ([0-9]+)", line)
        if match:
            finish()
            current = {"frame_id": match[1], "dump_length": int(match[2])}
            encoded = []
        else:
            require(current is not None, "data before FRAME header")
            encoded.append(line.strip())
    finish()
    require(bool(frames), "no frames")
    require(len({f["frame_id"] for f in frames}) == len(frames), "duplicate FRAME id")
    return frames


def read_packet_print(path):
    text = Path(path).read_text()
    starts = list(re.finditer(r"(?m)^\s*(\d+)\s+time=", text))
    require(bool(starts), "no packet-detail entries")
    require(not text[: starts[0].start()].strip(), "unexpected prefix before packet details")
    packets = []
    for i, start in enumerate(starts):
        end = starts[i + 1].start() if i + 1 < len(starts) else len(text)
        tokens = shlex.split(text[start.start() : end])
        require(tokens[0] == start[1], "invalid packet index")
        fields = {}
        previous_key = None
        for token in tokens[1:]:
            if token in ("(bootpc)", "(bootps)"):
                port = "68" if token == "(bootpc)" else "67"
                require(
                    previous_key in ("src-address", "dst-address")
                    and fields[previous_key].endswith(":" + port),
                    "unexpected port annotation",
                )
                previous_key = None
                continue
            field = re.fullmatch(r"([a-z][a-z0-9-]*)=(.+)", token)
            require(field is not None, "unparsed packet-detail text")
            require(field[1] not in fields, "duplicate packet-detail field")
            fields[field[1]] = field[2]
            previous_key = field[1]
        fields["print_index"] = int(start[1])
        require(fields.get("num", "").isdigit(), "missing or invalid packet number")
        if packets:
            require(fields["print_index"] > packets[-1]["print_index"], "packet index order")
            require(int(fields["num"]) > int(packets[-1]["num"]), "packet number order")
        packets.append(fields)
    return packets


def parse_options(data, field):
    options = []
    pos = 0
    while pos < len(data):
        code = data[pos]
        pos += 1
        if code == 0:
            continue
        if code == 255:
            require(not any(data[pos:]), "nonzero bytes after DHCP END in " + field)
            return options
        require(pos < len(data), "missing DHCP option length")
        length = data[pos]
        pos += 1
        require(pos + length <= len(data), "truncated DHCP option")
        options.append({"code": code, "field": field, "value_hex": data[pos : pos + length].hex()})
        pos += length
    raise ParseError("DHCP END option missing in " + field)


def parse_frame(data):
    offset, ihl, total = ip_layout(data)
    require(len(data) == offset + total, "frame length mismatch")
    ip = data[offset:]
    require(checksum(ip[:ihl]) == 0, "invalid IPv4 header checksum")
    require(ip[9] == 17 and not int.from_bytes(ip[6:8], "big") & 0xBFFF, "not unfragmented UDP")
    udp = ip[ihl:]
    src_port, dst_port, length, udp_check = struct.unpack("!HHHH", udp[:8])
    require(length == len(udp), "UDP length mismatch")
    require((src_port, dst_port) in ((67, 68), (68, 67)), "not DHCP ports")
    pseudo = ip[12:20] + bytes((0, 17)) + struct.pack("!H", length)
    require(udp_check != 0, "UDP checksum absent; cannot verify this capture")
    require(checksum(pseudo + udp) == 0, "invalid UDP checksum")
    bootp = udp[8:]
    require(
        len(bootp) >= 240 and bootp[236:240] == b"\x63\x82\x53\x63", "missing DHCP cookie/header"
    )
    require(
        bootp[0] in (1, 2) and bootp[1] == 1 and bootp[2] == 6,
        "unsupported BOOTP operation/hardware",
    )
    require((bootp[0], src_port) in ((1, 68), (2, 67)), "BOOTP operation disagrees with UDP ports")
    options = parse_options(bootp[240:], "options")
    overload = [bytes.fromhex(o["value_hex"]) for o in options if o["code"] == 52]
    require(len(overload) <= 1, "duplicate overload option")
    if overload:
        require(len(overload[0]) == 1 and 1 <= overload[0][0] <= 3, "invalid overload option")
        if overload[0][0] & 1:
            options.extend(parse_options(bootp[108:236], "file"))
        if overload[0][0] & 2:
            options.extend(parse_options(bootp[44:108], "sname"))
    types = [bytes.fromhex(o["value_hex"]) for o in options if o["code"] == 53]
    require(len(types) == 1 and len(types[0]) == 1, "missing/duplicate/invalid message type")
    msg_type = types[0][0]
    names = {
        1: "DISCOVER",
        2: "OFFER",
        3: "REQUEST",
        4: "DECLINE",
        5: "ACK",
        6: "NAK",
        7: "RELEASE",
        8: "INFORM",
    }
    require(msg_type in names, "unknown DHCP message type")
    require(
        msg_type in ({1, 3, 4, 7, 8} if bootp[0] == 1 else {2, 5, 6}),
        "DHCP message type disagrees with BOOTP operation",
    )
    result = {
        "frame_size": len(data),
        "frame_sha256": hashlib.sha256(data).hexdigest(),
        "src_mac": mac(data[6:12]),
        "dst_mac": mac(data[:6]),
        "src_ip": str(ipaddress.IPv4Address(ip[12:16])),
        "dst_ip": str(ipaddress.IPv4Address(ip[16:20])),
        "src_port": src_port,
        "dst_port": dst_port,
        "ip_total_length": total,
        "ip_header_length": ihl,
        "ip_identification": int.from_bytes(ip[4:6], "big"),
        "ipv4_checksum": "PASS",
        "udp_checksum": "PASS",
        "udp_length": length,
        "bootp_op": bootp[0],
        "xid": int.from_bytes(bootp[4:8], "big"),
        "bootp_flags": int.from_bytes(bootp[10:12], "big"),
        "chaddr": mac(bootp[28:34]),
        "ciaddr": str(ipaddress.IPv4Address(bootp[12:16])),
        "yiaddr": str(ipaddress.IPv4Address(bootp[16:20])),
        "siaddr": str(ipaddress.IPv4Address(bootp[20:24])),
        "giaddr": str(ipaddress.IPv4Address(bootp[24:28])),
        "message_type": msg_type,
        "message": names[msg_type],
        "options": options,
    }
    return result


def correlate(packet, metadata):
    expected = {
        "src-mac": packet["src_mac"],
        "dst-mac": packet["dst_mac"],
        "src-address": f"{packet['src_ip']}:{packet['src_port']}",
        "dst-address": f"{packet['dst_ip']}:{packet['dst_port']}",
        "size": str(packet["frame_size"]),
        "ip-packet-size": str(packet["ip_total_length"]),
        "ip-header-size": str(packet["ip_header_length"]),
        "identification": str(packet["ip_identification"]),
        "protocol": "ip",
        "ip-protocol": "udp",
        "fragment-offset": "0",
    }
    for key, value in expected.items():
        require(
            key in metadata and metadata[key].lower() == value.lower(),
            "packet detail mismatch for " + key,
        )
    require(
        "num" in metadata and "direction" in metadata and "time" in metadata,
        "missing packet metadata",
    )
    require(metadata["num"].isdigit(), "invalid packet number")
    require(metadata["direction"] in ("rx", "tx"), "invalid packet direction")
    require(bool(re.fullmatch(r"[0-9]+(?:\.[0-9]+)?", metadata["time"])), "invalid packet time")
    return {
        "packet_num": int(metadata["num"]),
        "relative_time_s": metadata["time"],
        "direction": metadata["direction"],
    }


def analyze(frames_path, metadata_path, target_mac, expected_xid=None):
    target_mac = normalize_mac(target_mac)
    frames = read_frames(frames_path)
    metadata = read_packet_print(metadata_path)
    require(len(frames) == len(metadata), "frame/packet-detail count mismatch")
    packets = []
    for frame, detail in zip(frames, metadata):
        packet = parse_frame(frame["data"])
        packet.update(correlate(packet, detail))
        packet.update({key: value for key, value in frame.items() if key != "data"})
        packet["target_match"] = packet["chaddr"] == target_mac
        packets.append(packet)
    times = [Decimal(p["relative_time_s"]) for p in packets]
    require(all(a <= b for a, b in zip(times, times[1:])), "packet time order decreases")
    for packet, time_value in zip(packets, times):
        packet["since_first_packet_ms"] = str((time_value - times[0]) * 1000)
    selected = [p for p in packets if p["target_match"]]
    require(bool(selected), "no target DHCP packets")
    transactions = []
    for xid in dict.fromkeys(p["xid"] for p in selected):
        sequence = [p for p in selected if p["xid"] == xid]
        transactions.append(
            {
                "xid": xid,
                "messages": [p["message"] for p in sequence],
                "packet_nums": [p["packet_num"] for p in sequence],
            }
        )
    if expected_xid is not None:
        require(any(t["xid"] == expected_xid for t in transactions), "expected RAM xid absent")
    return {
        "schema_version": 1,
        "privacy": "PRIVATE: contains device/network identifiers and raw DHCP options",
        "limitations": [
            "Router-side capture does not prove Wi-Fi delivery to the client",
            "RAM BOUND evidence is external; matching xid correlates but does not itself observe RAM",
            "ASCII dump reconstruction is checksum-validated; original raw packet bytes were not exported",
            "Frame-to-time mapping uses matching snapshot order plus Ethernet/IP/UDP header cross-checks",
        ],
        "inputs": {
            kind: {
                "name": Path(p).name,
                "sha256": hashlib.sha256(Path(p).read_bytes()).hexdigest(),
            }
            for kind, p in (("frames", frames_path), ("packet_print", metadata_path))
        },
        "target_mac": target_mac,
        "expected_ram_xid": expected_xid,
        "frame_count": len(packets),
        "target_frame_count": len(selected),
        "transactions": transactions,
        "packets": packets,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("frames", type=Path)
    parser.add_argument("packet_print", type=Path)
    parser.add_argument("--target-mac", required=True)
    parser.add_argument("--expected-xid", type=lambda value: int(value, 0))
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="private JSON; identifiers are not printed to stdout",
    )
    args = parser.parse_args()
    try:
        result = analyze(args.frames, args.packet_print, args.target_mac, args.expected_xid)
    except (OSError, ValueError, KeyError, struct.error) as exc:
        parser.exit(1, f"FAIL: {exc}\n")
    # Refuse overwrites and request owner-only access on POSIX systems.
    try:
        descriptor = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "w") as stream:
            json.dump(result, stream, indent=2)
            stream.write("\n")
    except OSError as exc:
        parser.exit(1, f"FAIL writing output: {exc}\n")
    print(
        f"PASS: {result['frame_count']} frames; {result['target_frame_count']} target frames; "
        "all IPv4/UDP checksums valid"
    )


if __name__ == "__main__":
    main()
