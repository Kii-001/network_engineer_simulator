"""Sistem VLAN (Virtual LAN) dan 802.1Q tagging."""
from __future__ import annotations

from dataclasses import dataclass, field

PORT_MODE_ACCESS = "access"
PORT_MODE_TRUNK = "trunk"
DEFAULT_VLAN = 1


@dataclass
class VLAN:
    id: int
    name: str = ""

    def __post_init__(self):
        if not (1 <= self.id <= 4094):
            raise ValueError("VLAN ID harus di antara 1 dan 4094.")
        if not self.name:
            self.name = f"VLAN_{self.id:04d}"

    def to_dict(self) -> dict:
        return {"id": self.id, "name": self.name}

    @classmethod
    def from_dict(cls, data: dict) -> VLAN:
        return cls(id=data["id"], name=data.get("name", ""))


@dataclass
class PortVLANConfig:
    mode: str = PORT_MODE_ACCESS        # 'access' | 'trunk'
    access_vlan: int = DEFAULT_VLAN
    native_vlan: int = DEFAULT_VLAN
    allowed_vlans: set[int] = field(default_factory=lambda: set(range(1, 4095)))

    def is_vlan_allowed(self, vlan_id: int) -> bool:
        if self.mode == PORT_MODE_ACCESS:
            return vlan_id == self.access_vlan
        return vlan_id in self.allowed_vlans

    def to_dict(self) -> dict:
        return {
            "mode": self.mode,
            "access_vlan": self.access_vlan,
            "native_vlan": self.native_vlan,
            "allowed_vlans": sorted(list(self.allowed_vlans)) if len(self.allowed_vlans) < 500 else "all",
        }

    @classmethod
    def from_dict(cls, data: dict) -> PortVLANConfig:
        cfg = cls(
            mode=data.get("mode", PORT_MODE_ACCESS),
            access_vlan=data.get("access_vlan", DEFAULT_VLAN),
            native_vlan=data.get("native_vlan", DEFAULT_VLAN),
        )
        allowed = data.get("allowed_vlans", "all")
        if allowed == "all":
            cfg.allowed_vlans = set(range(1, 4095))
        elif isinstance(allowed, list):
            cfg.allowed_vlans = set(allowed)
        return cfg
