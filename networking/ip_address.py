"""Parsing & konversi IPv4 / subnet mask. Murni logika (tanpa pygame)."""
from __future__ import annotations


class IPv4Error(ValueError):
    """Alamat atau mask tidak valid (pesan dalam Bahasa Indonesia)."""


def parse_ip(text: str) -> int:
    t = (text or "").strip()
    if not t:
        raise IPv4Error("Alamat IP kosong.")
    parts = t.split(".")
    if len(parts) != 4:
        raise IPv4Error("IPv4 harus 4 angka dipisah titik (contoh 192.168.1.10).")
    value = 0
    for p in parts:
        if not p:
            raise IPv4Error("Ada oktet yang kosong.")
        if not (p.isascii() and p.isdigit()):
            raise IPv4Error(f"Oktet '{p}' bukan angka.")
        if len(p) > 1 and p[0] == "0":
            raise IPv4Error(f"Oktet '{p}' tidak boleh diawali angka nol.")
        n = int(p)
        if n > 255:
            raise IPv4Error(f"Oktet {n} di luar rentang 0-255.")
        value = (value << 8) | n
    return value


def ip_to_str(n: int) -> str:
    return ".".join(str((n >> s) & 255) for s in (24, 16, 8, 0))


def prefix_to_mask(prefix: int) -> int:
    if not 0 <= prefix <= 32:
        raise IPv4Error("Prefix harus 0-32.")
    return (0xFFFFFFFF << (32 - prefix)) & 0xFFFFFFFF if prefix else 0


def mask_to_str(prefix: int) -> str:
    return ip_to_str(prefix_to_mask(prefix))


def wildcard_to_str(prefix: int) -> str:
    return ip_to_str(~prefix_to_mask(prefix) & 0xFFFFFFFF)


def parse_mask(text: str) -> int:
    """Terima '255.255.255.0', '/24', atau '24'. Kembalikan prefix (0-32)."""
    t = (text or "").strip()
    if not t:
        raise IPv4Error("Subnet mask kosong.")
    bare = t[1:] if t.startswith("/") else t
    if "." not in t:
        if not (bare.isascii() and bare.isdigit()):
            raise IPv4Error("Mask harus berbentuk 255.255.255.0 atau /24.")
        prefix = int(bare)
        if prefix > 32:
            raise IPv4Error("Prefix CIDR harus 0-32.")
        return prefix
    try:
        m = parse_ip(t)
    except IPv4Error as e:
        raise IPv4Error(f"Mask tidak valid: {e}") from None
    inv = ~m & 0xFFFFFFFF
    if inv & (inv + 1):
        raise IPv4Error("Mask tidak valid: bit 1 harus berurutan dari kiri (contoh 255.255.255.0).")
    return bin(m).count("1")
