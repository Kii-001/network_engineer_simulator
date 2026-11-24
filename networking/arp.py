"""Tabel ARP (Address Resolution Protocol) dan pemetaan IP ke MAC."""
from __future__ import annotations

import time
from dataclasses import dataclass
from networking.ip_address import ip_to_str, parse_ip

@dataclass
class ARPEntry:
    ip: int
    mac: str
    interface: str = ""
    timestamp: float = 0.0
    static: bool = False

    def to_dict(self) -> dict:
        return {
            "ip": ip_to_str(self.ip),
            "mac": self.mac,
            "interface": self.interface,
            "static": self.static,
        }

    @classmethod
    def from_dict(cls, data: dict) -> ARPEntry:
        return cls(
            ip=parse_ip(data["ip"]),
            mac=data["mac"],
            interface=data.get("interface", ""),
            static=data.get("static", False),
        )


class ARPTable:
    def __init__(self, max_entries: int = 128, timeout_seconds: float = 300.0) -> None:
        self.entries: dict[int, ARPEntry] = {}
        self.max_entries = max_entries
        self.timeout = timeout_seconds

    def lookup(self, ip: int) -> str | None:
        entry = self.entries.get(ip)
        if entry:
            return entry.mac
        return None

    def add(self, ip: int, mac: str, interface: str = "", static: bool = False) -> None:
        if len(self.entries) >= self.max_entries and ip not in self.entries:
            # Hapus entry tertua
            oldest_ip = min(self.entries.keys(), key=lambda k: self.entries[k].timestamp)
            del self.entries[oldest_ip]
        self.entries[ip] = ARPEntry(
            ip=ip, mac=mac.upper(), interface=interface,
            timestamp=time.time(), static=static
        )

    def remove(self, ip: int) -> bool:
        if ip in self.entries:
            del self.entries[ip]
            return True
        return False

    def clear(self) -> None:
        self.entries.clear()

    def get_all(self) -> list[ARPEntry]:
        return list(self.entries.values())

    def to_dict(self) -> list[dict]:
        return [entry.to_dict() for entry in self.entries.values()]

    def from_dict(self, data: list[dict]) -> None:
        self.clear()
        for item in data:
            entry = ARPEntry.from_dict(item)
            self.entries[entry.ip] = entry
