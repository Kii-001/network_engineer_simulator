"""Perhitungan subnet, pemecahan subnet, dan VLSM. Murni logika."""
from __future__ import annotations

from dataclasses import dataclass

from networking.ip_address import (IPv4Error, ip_to_str, mask_to_str, parse_ip, parse_mask,
                                   prefix_to_mask, wildcard_to_str)


class SubnetError(ValueError):
    pass


def ip_class(n: int) -> str:
    first = n >> 24
    return "A" if first < 128 else "B" if first < 192 else "C" if first < 224 else "D (multicast)" if first < 240 else "E (reserved)"


def ip_kind(n: int) -> str:
    first = n >> 24
    if first == 127: return "Loopback"
    if first == 0: return "This network"
    if n >> 16 == 0xA9FE: return "Link-local (APIPA)"
    if first == 10 or n >> 20 == 0xAC1 or n >> 16 == 0xC0A8: return "Private (RFC 1918)"
    if first >= 224: return "Multicast/Reserved"
    return "Public"


@dataclass(frozen=True)
class SubnetInfo:
    address: int
    prefix: int

    @property
    def mask(self) -> int: return prefix_to_mask(self.prefix)
    @property
    def network(self) -> int: return self.address & self.mask
    @property
    def broadcast(self) -> int: return self.network | (~self.mask & 0xFFFFFFFF)
    @property
    def total_addresses(self) -> int: return 1 << (32 - self.prefix)

    @property
    def usable_hosts(self) -> int:
        if self.prefix == 32: return 1
        if self.prefix == 31: return 2
        return self.total_addresses - 2

    @property
    def first_host(self) -> int:
        return self.network if self.prefix >= 31 else self.network + 1

    @property
    def last_host(self) -> int:
        return self.broadcast if self.prefix >= 31 else self.broadcast - 1

    def contains(self, ip: int) -> bool:
        return self.network <= ip <= self.broadcast

    def cidr(self) -> str:
        return f"{ip_to_str(self.network)}/{self.prefix}"

    def describe(self) -> list[tuple[str, str]]:
        return [("Network", self.cidr()), ("Broadcast", ip_to_str(self.broadcast)),
                ("Subnet mask", mask_to_str(self.prefix)), ("Wildcard", wildcard_to_str(self.prefix)),
                ("Host pertama", ip_to_str(self.first_host)), ("Host terakhir", ip_to_str(self.last_host)),
                ("Total alamat", f"{self.total_addresses:,}"), ("Host usable", f"{self.usable_hosts:,}"),
                ("Kelas", ip_class(self.address)), ("Jenis", ip_kind(self.address))]


def calculate(ip_text: str, mask_text: str) -> SubnetInfo:
    return SubnetInfo(parse_ip(ip_text), parse_mask(mask_text))


def overlaps(a: SubnetInfo, b: SubnetInfo) -> bool:
    return a.network <= b.broadcast and b.network <= a.broadcast


def same_network(ip_a: int, ip_b: int, prefix: int) -> bool:
    m = prefix_to_mask(prefix)
    return ip_a & m == ip_b & m


def host_address_error(ip: int, prefix: int) -> str | None:
    """Alasan alamat tidak boleh dipasang pada interface host (None bila boleh)."""
    first = ip >> 24
    if first == 0:
        return "Alamat 0.x.x.x (this network) tidak valid untuk host."
    if first == 127:
        return "127.x.x.x adalah loopback, tidak bisa dipasang pada interface."
    if first >= 224:
        return "Alamat kelas D/E (multicast/reserved) tidak bisa dipakai host."
    if prefix <= 30:
        info = SubnetInfo(ip, prefix)
        if ip == info.network:
            return f"{ip_to_str(ip)} adalah alamat NETWORK untuk /{prefix}; pakai alamat host."
        if ip == info.broadcast:
            return f"{ip_to_str(ip)} adalah alamat BROADCAST untuk /{prefix}; pakai alamat host."
    return None


def prefix_for_hosts(hosts: int) -> int:
    if hosts < 1:
        raise SubnetError("Jumlah host minimal 1.")
    bits = (hosts + 2 - 1).bit_length()      # 2^bits >= hosts + 2
    if bits > 32:
        raise SubnetError("Jumlah host terlalu besar.")
    return min(30, 32 - bits)


def split_subnet(base: SubnetInfo, new_prefix: int, limit: int = 512) -> tuple[int, list[SubnetInfo]]:
    """Pecah subnet menjadi subnet berprefix lebih panjang. Return (jumlah total, daftar max `limit`)."""
    if not base.prefix <= new_prefix <= 32:
        raise SubnetError(f"Prefix baru harus antara /{base.prefix} dan /32.")
    count = 1 << (new_prefix - base.prefix)
    step = 1 << (32 - new_prefix)
    return count, [SubnetInfo(base.network + i * step, new_prefix) for i in range(min(count, limit))]


@dataclass(frozen=True)
class VLSMAllocation:
    label: str
    hosts_needed: int
    info: SubnetInfo


def vlsm(base: SubnetInfo, demands: list[int]) -> list[VLSMAllocation]:
    """Alokasi VLSM: kebutuhan terbesar dulu, berurutan dari awal blok induk."""
    if not demands:
        raise SubnetError("Isi minimal satu kebutuhan host.")
    order = sorted(range(len(demands)), key=lambda i: (-demands[i], i))
    cursor, end = base.network, base.broadcast
    out = []
    for i in order:
        p = prefix_for_hosts(demands[i])
        size = 1 << (32 - p)
        cursor = (cursor + size - 1) // size * size
        if cursor + size - 1 > end:
            raise SubnetError(f"Ruang {base.cidr()} tidak cukup untuk {demands[i]} host (Net{i + 1}).")
        out.append(VLSMAllocation(f"Net{i + 1}", demands[i], SubnetInfo(cursor, p)))
        cursor += size
    return out
