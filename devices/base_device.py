"""Model perangkat jaringan. Murni logika (tanpa pygame)."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Port:
    name: str
    kind: str                       # RJ45, FIBER, CONSOLE, WIRELESS, WAN
    admin_up: bool = True           # dipakai Phase 6 (shutdown / no shutdown)
    connected_to: tuple | None = None  # (device_id, port_name) ujung seberang
    link_id: int | None = None         # id kabel yang terpasang
    ip: int | None = None              # alamat IPv4 (integer)
    prefix: int | None = None          # panjang prefix CIDR


_ABBR = (("GigabitEthernet", "Gi"), ("FastEthernet", "Fa"), ("Ethernet", "Eth"))


def short_port_name(name: str) -> str:
    for long, short in _ABBR:
        if name.startswith(long):
            return short + name[len(long):]
    return name


def _fmt_ip(port) -> str | None:
    from networking.ip_address import ip_to_str
    return None if port.ip is None else f"{ip_to_str(port.ip)}/{port.prefix}"


def generate_mac(device_id: int) -> str:
    """MAC simulasi yang deterministik dan unik per id perangkat."""
    return "02:AB:CD:{:02X}:{:02X}:{:02X}".format((device_id >> 16) & 255, (device_id >> 8) & 255, device_id & 255)


def build_ports(spec: dict) -> list[Port]:
    ports: list[Port] = []
    for group in spec.get("ports", []):
        start = group.get("start", 0)
        for n in range(group["count"]):
            fmt = group["name"]
            name = fmt.format(i=start + n) if "{i}" in fmt else (fmt if group["count"] == 1 else f"{fmt}{start + n}")
            ports.append(Port(name=name, kind=group["kind"]))
    return ports


class BaseDevice:
    def __init__(self, device_id: int, dtype: str, spec: dict, name: str, x: float, y: float, rotation: int = 0) -> None:
        self.id = device_id
        self.type = dtype
        self.spec = spec
        self.name = name
        self.x = x
        self.y = y
        self.rotation = rotation % 360
        self.status = "online"
        self.mac = generate_mac(device_id)
        self.ports = build_ports(spec)
        self.gateway: int | None = None

    @property
    def label(self) -> str: return self.spec["label"]
    @property
    def model(self) -> str: return self.spec["model"]
    @property
    def cost(self) -> int: return self.spec["cost"]
    @property
    def mdi(self) -> str: return self.spec.get("mdi", "MDI")

    @property
    def ip_role(self) -> str: return self.spec.get("ip_role", "none")   # host | router | none

    def ip_ports(self) -> list[Port]:
        """Port yang boleh diberi IP (RJ45/FIBER pada perangkat L3/host)."""
        if self.ip_role == "none":
            return []
        return [p for p in self.ports if p.kind in ("RJ45", "FIBER")]

    def get_port(self, name: str) -> Port:
        for p in self.ports:
            if p.name == name:
                return p
        raise KeyError(f"Port '{name}' tidak ada pada {self.name}.")

    def to_dict(self) -> dict:
        from networking.ip_address import ip_to_str
        d = {"id": self.id, "type": self.type, "name": self.name,
             "x": self.x, "y": self.y, "rotation": self.rotation}
        ports = {p.name: [ip_to_str(p.ip), f"/{p.prefix}"] for p in self.ports if p.ip is not None}
        if ports or self.gateway is not None:
            d["config"] = {"ports": ports, "gateway": ip_to_str(self.gateway) if self.gateway is not None else None}
        return d
