# SPDX-License-Identifier: MIT
"""Offline parser tests using invented packets, never a router or device."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import parse_router_dhcp as parser

HERE = Path(__file__).resolve().parent
FIXTURES = HERE / "fixtures"
FRAMES = FIXTURES / "synthetic-frames.txt"
DETAILS = FIXTURES / "synthetic-packets.txt"
EXPECTED = json.loads((FIXTURES / "synthetic-expected.json").read_text())


def uncompressed_dump(data):
    lines = []
    for offset in range(0, len(data), 16):
        block = data[offset : offset + 16]
        left = " ".join(f"{b:02x}" for b in block[:8])
        right = " ".join(f"{b:02x}" for b in block[8:])
        field = left + ("  " + right if right else "")
        lines.append(f"{offset:04x}: {field:<48}  {'.' * len(block)}")
    return "\n".join(lines)


def repair_checksums(data):
    """Keep mutated protocol fixtures valid so tests reach the intended check."""
    data = bytearray(data)
    offset, ihl, _ = parser.ip_layout(data)
    data[offset + 10 : offset + 12] = b"\0\0"
    data[offset + 10 : offset + 12] = parser.checksum(data[offset : offset + ihl]).to_bytes(
        2, "big"
    )
    start = offset + ihl
    data[start + 6 : start + 8] = b"\0\0"
    pseudo = data[offset + 12 : offset + 20] + b"\0\x11" + data[start + 4 : start + 6]
    data[start + 6 : start + 8] = (parser.checksum(pseudo + data[start:]) or 0xFFFF).to_bytes(
        2, "big"
    )
    return bytes(data)


def read_text_input(reader, text):
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "input.txt"
        path.write_text(text)
        return reader(path)


class ParserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.frames = parser.read_frames(FRAMES)
        cls.details = parser.read_packet_print(DETAILS)
        cls.parsed = [parser.parse_frame(f["data"]) for f in cls.frames]

    def test_checksum_known_vectors(self):
        self.assertEqual(parser.checksum(bytes.fromhex("0001f203f4f5f6f7")), 0x220D)
        self.assertEqual(parser.checksum(b"\x01"), 0xFEFF)

    def test_fixture_hashes_checksums_and_dora(self):
        self.assertEqual([p["message"] for p in self.parsed], EXPECTED["messages"])
        self.assertEqual({p["xid"] for p in self.parsed}, {EXPECTED["xid"]})
        self.assertEqual({p["chaddr"] for p in self.parsed}, {EXPECTED["target_mac"]})
        for frame, packet, expected in zip(self.frames, self.parsed, EXPECTED["frames"]):
            with self.subTest(frame=frame["frame_id"]):
                self.assertEqual(packet["frame_sha256"], expected["sha256"])
                self.assertEqual(packet["frame_size"], expected["frame_size"])
                self.assertEqual(frame["data"][24:26].hex(), expected["ipv4_checksum_hex"])
                self.assertEqual(frame["data"][40:42].hex(), expected["udp_checksum_hex"])
                self.assertEqual(packet["ipv4_checksum"], "PASS")
                self.assertEqual(packet["udp_checksum"], "PASS")

    def test_correlate_metadata_and_times(self):
        result = parser.analyze(FRAMES, DETAILS, EXPECTED["target_mac"], EXPECTED["xid"])
        self.assertEqual([p["relative_time_s"] for p in result["packets"]], EXPECTED["times_s"])
        self.assertEqual(
            [p["since_first_packet_ms"] for p in result["packets"]],
            ["0.000", "10.000", "20.000", "30.000"],
        )
        self.assertEqual(set(result["inputs"]), {"frames", "packet_print"})
        wrong = dict(self.details[0], size="1")
        with self.assertRaisesRegex(parser.ParseError, "packet detail mismatch"):
            parser.correlate(self.parsed[0], wrong)

    def test_byte_exact_uncompressed_roundtrip(self):
        for frame in self.frames:
            restored, expansions = parser.reconstruct_dump(uncompressed_dump(frame["data"]))
            self.assertEqual(restored, frame["data"])
            self.assertEqual(expansions, [])

    def test_compressed_interior_and_trailing_zeros(self):
        self.assertEqual([len(f["repeat_expansions"]) for f in self.frames], [2, 1, 2, 1])
        for frame in self.frames:
            for expansion in frame["repeat_expansions"]:
                self.assertEqual(expansion["pattern_hex"], "00" * 16)

    def test_compressed_nonzero_repeat(self):
        data = bytearray(self.frames[0]["data"])
        data[96:144] = bytes(range(16)) * 3
        lines = uncompressed_dump(data).splitlines()
        lines[7:9] = ["*"]
        restored, expansions = parser.reconstruct_dump("\n".join(lines))
        self.assertEqual(restored, data)
        self.assertEqual(expansions[0]["pattern_hex"], bytes(range(16)).hex())

    def test_gap_overlap_truncation_rejected(self):
        lines = uncompressed_dump(self.frames[0]["data"]).splitlines()
        for mutated in (lines[:6] + lines[7:], lines[:6] + lines[5:]):
            with self.assertRaisesRegex(parser.ParseError, "unexplained gap"):
                parser.reconstruct_dump("\n".join(mutated))
        with self.assertRaisesRegex(parser.ParseError, "frame length"):
            parser.reconstruct_dump(uncompressed_dump(self.frames[0]["data"][:-1]))

    def test_invalid_repeat_rejected(self):
        dump = uncompressed_dump(self.frames[0]["data"])
        for mutated in ("*\n" + dump, dump.replace("0010:", "*\n*\n0010:", 1)):
            with self.assertRaises(parser.ParseError):
                parser.reconstruct_dump(mutated)
        lines = dump.splitlines()
        with self.assertRaisesRegex(parser.ParseError, "invalid '\\*' expansion"):
            parser.reconstruct_dump(
                "\n".join(lines[:2] + ["*", lines[2].replace("0020:", "fffffff0:")])
            )

    def test_corrupt_checksums_rejected(self):
        for frame in self.frames:
            for index, message in ((22, "IPv4 header checksum"), (46, "UDP checksum")):
                data = bytearray(frame["data"])
                data[index] ^= 1
                with self.assertRaisesRegex(parser.ParseError, message):
                    parser.parse_frame(bytes(data))

    def test_absent_udp_checksum_rejected(self):
        data = bytearray(self.frames[0]["data"])
        data[40:42] = b"\0\0"
        with self.assertRaisesRegex(parser.ParseError, "checksum absent"):
            parser.parse_frame(bytes(data))

    def test_vlan_and_ipv4_options(self):
        original = self.frames[0]["data"]
        for tags in (b"\x81\0\0\x64", b"\x88\xa8\0\x64\x81\0\0\x65"):
            packet = parser.parse_frame(original[:12] + tags + original[12:])
            self.assertEqual(packet["xid"], EXPECTED["xid"])
        data = bytearray(original[:34] + b"\x01" * 4 + original[34:])
        data[14] = 0x46
        data[16:18] = (len(data) - 14).to_bytes(2, "big")
        self.assertEqual(parser.parse_frame(repair_checksums(data))["ip_header_length"], 24)

    def test_ipv4_fragment_and_reserved_flag_rejected(self):
        for flag in (0x2000, 1, 0x8000):
            data = bytearray(self.frames[0]["data"])
            data[20:22] = flag.to_bytes(2, "big")
            with self.assertRaisesRegex(parser.ParseError, "unfragmented UDP"):
                parser.parse_frame(repair_checksums(data))

    def test_dhcp_overload(self):
        data = bytearray(self.frames[0]["data"])
        bootp = 42
        data[bootp + 44 : bootp + 108] = (b"\x0f\x0fexample.invalid\xff").ljust(64, b"\0")
        data[bootp + 108 : bootp + 236] = (b"\x0c\x07fixture\xff").ljust(128, b"\0")
        size = len(data) - bootp - 240
        data[bootp + 240 :] = b"\x35\x01\x01\x34\x01\x03\xff" + bytes(size - 7)
        packet = parser.parse_frame(repair_checksums(data))
        self.assertEqual({o["field"] for o in packet["options"]}, {"options", "file", "sname"})

    def test_invalid_dhcp_options_and_message_direction(self):
        for options in (b"\x35\x01\x01", b"\x35\x04\x01\xff", b"\x35\x01\x01\xff\x01"):
            with self.assertRaises(parser.ParseError):
                parser.parse_options(options, "test")
        data = bytearray(self.frames[1]["data"])
        data[42 + 242] = 1  # DISCOVER with BOOTREPLY / server ports.
        with self.assertRaisesRegex(parser.ParseError, "message type disagrees"):
            parser.parse_frame(repair_checksums(data))

    def test_invalid_packet_metadata_rejected(self):
        original = DETAILS.read_text()
        cases = (
            original + "garbage\n",
            original.replace("size=370", "size=370 size=370", 1),
            original.replace('interface="synthetic fixture"', 'interface="unclosed', 1),
            original.replace(" 1 time=", " 0 time=", 1),
            original.replace("num=2", "num=1", 1),
        )
        for text in cases:
            with self.assertRaises(ValueError):
                read_text_input(parser.read_packet_print, text)

    def test_invalid_frame_export_rejected(self):
        original = FRAMES.read_text()
        lines = original.splitlines()
        altered_header = lines[0].rsplit(" ", 1)[0] + " 1"
        cases = (
            "\n".join([altered_header] + lines[1:]),
            original + original,
            "\n".join([lines[0], "z" + lines[1][1:]] + lines[2:]),
        )
        for text in cases:
            with self.assertRaises(parser.ParseError):
                read_text_input(parser.read_frames, text)

    def test_expected_xid_and_target_must_be_present(self):
        with self.assertRaisesRegex(parser.ParseError, "expected RAM xid absent"):
            parser.analyze(FRAMES, DETAILS, EXPECTED["target_mac"], EXPECTED["xid"] ^ 1)
        with self.assertRaisesRegex(parser.ParseError, "no target DHCP"):
            parser.analyze(FRAMES, DETAILS, "02:00:00:00:00:ff")

    def test_cli_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "parsed.json"
            command = [
                sys.executable,
                str(HERE / "parse_router_dhcp.py"),
                str(FRAMES),
                str(DETAILS),
                "--target-mac",
                EXPECTED["target_mac"],
                "--expected-xid",
                hex(EXPECTED["xid"]),
                "--output",
                str(output),
            ]
            result = subprocess.run(command, capture_output=True, text=True, check=False)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertNotIn(EXPECTED["target_mac"], result.stdout)
            self.assertEqual(json.loads(output.read_text())["target_frame_count"], 4)
            if os.name == "posix":
                self.assertEqual(output.stat().st_mode & 0o077, 0)
            saved = output.read_bytes()
            result = subprocess.run(command, capture_output=True, text=True, check=False)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(output.read_bytes(), saved)


if __name__ == "__main__":
    unittest.main(verbosity=2)
