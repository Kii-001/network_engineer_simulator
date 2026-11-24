"""Mesin topologi: menyimpan perangkat dan aturan penempatan. Tanpa UI."""
from __future__ import annotations

import json
import re
from pathlib import Path

import config
from devices import create_device
from devices.base_device import BaseDevice, short_port_name
from networking import cables
from networking.ip_address import IPv4Error, ip_to_str, parse_ip, parse_mask
from networking.subnetting import SubnetInfo, host_address_error, overlaps
from networking.cables import CableError, Link

GRID = 32
KEEP = object()   # penanda "jangan ubah" untuk apply_ip_config


class IPConfigError(ValueError):
    """Konfigurasi IP ditolak. `port` dan `field` ('ip'/'mask'/'gateway') menunjuk sumber kesalahan."""

    def __init__(self, message: str, port: str | None = None, field: str | None = None) -> None:
        super().__init__(message)
        self.port, self.field = port, field


NAME_RE = re.compile(r"^[A-Za-z0-9_-]{1,20}$")


def load_catalog(path: Path | str | None = None) -> dict:
    p = Path(path) if path else config.BASE_DIR / "data" / "devices.json"
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def snap(value: float, grid: int = GRID) -> int:
    return int(round(value / grid)) * grid


class Topology:
    def __init__(self, catalog: dict | None = None) -> None:
        self.catalog = catalog or load_catalog()
        self.devices: dict[int, BaseDevice] = {}
        self._next_id = 1
        self.links: dict[int, Link] = {}
        self._next_link_id = 1

    # --- penamaan ---
    def next_free_name(self, dtype: str) -> str:
        prefix = self.catalog[dtype]["name_prefix"]
        used = {d.name.lower() for d in self.devices.values()}
        n = 1
        while f"{prefix}{n}".lower() in used:
            n += 1
        return f"{prefix}{n}"

    def validate_name(self, name: str, exclude_id: int | None = None) -> str:
        name = name.strip()
        if not NAME_RE.match(name):
            raise ValueError("Nama harus 1-20 karakter: huruf, angka, '-' atau '_' (tanpa spasi).")
        for d in self.devices.values():
            if d.id != exclude_id and d.name.lower() == name.lower():
                raise ValueError(f"Nama '{name}' sudah dipakai perangkat lain.")
        return name

    # --- operasi perangkat ---
    def add_device(self, dtype: str, x: float, y: float, name: str | None = None,
                   rotation: int = 0, device_id: int | None = None) -> BaseDevice:
        if dtype not in self.catalog:
            raise ValueError(f"Jenis perangkat tidak dikenal: {dtype}")
        did = device_id if device_id is not None else self._next_id
        if did in self.devices:
            raise ValueError(f"ID perangkat {did} sudah ada.")
        nm = self.validate_name(name) if name else self.next_free_name(dtype)
        dev = create_device(did, dtype, self.catalog[dtype], nm, x, y, rotation)
        self.devices[did] = dev
        self._next_id = max(self._next_id, did + 1)
        return dev

    def get(self, did: int) -> BaseDevice:
        if did not in self.devices:
            raise KeyError(f"Perangkat {did} tidak ada.")
        return self.devices[did]

    def remove_device(self, did: int) -> BaseDevice:
        dev = self.get(did)
        for link in self.links_of(did):
            self.disconnect(link.id)
        del self.devices[did]
        return dev

    def move_device(self, did: int, x: float, y: float) -> None:
        dev = self.get(did)
        dev.x, dev.y = x, y

    def rotate_device(self, did: int, step: int = 90) -> int:
        dev = self.get(did)
        dev.rotation = (dev.rotation + step) % 360
        return dev.rotation

    def rename_device(self, did: int, new_name: str) -> str:
        dev = self.get(did)
        dev.name = self.validate_name(new_name, exclude_id=did)
        return dev.name

    def clear(self) -> None:
        self.devices.clear()
        self.links.clear()
        self._next_id = 1
        self._next_link_id = 1

    # --- kabel / link ---
    def links_of(self, did: int) -> list[Link]:
        return [l for l in self.links.values() if l.a[0] == did or l.b[0] == did]

    def port_options(self, did: int, cable: str, other_kind: str | None = None) -> list[dict]:
        """Daftar port perangkat beserta status bisa-dipakai untuk kabel tertentu."""
        out = []
        for p in self.get(did).ports:
            enabled, note = True, ""
            if p.link_id is not None:
                enabled, note = False, "terpakai"
            else:
                try:
                    if other_kind is None:
                        if not cables.port_supports(cable, p.kind):
                            raise CableError("tidak cocok")
                    else:
                        cables.validate_ports(cable, p.kind, other_kind)
                except CableError:
                    enabled, note = False, "tidak cocok"
            out.append({"name": p.name, "short": short_port_name(p.name), "kind": p.kind,
                        "enabled": enabled, "note": note, "state": self.port_state(p)})
        return out

    def port_state(self, port) -> str:
        """'off' (tanpa kabel), 'up', atau 'down'."""
        if port.link_id is None or port.link_id not in self.links:
            return "off"
        return self.links[port.link_id].state

    def connect(self, dev_a: int, port_a: str, dev_b: int, port_b: str, cable: str,
                link_id: int | None = None) -> Link:
        if cable not in cables.CABLE_TYPES:
            raise CableError(f"Jenis kabel tidak dikenal: {cable}")
        if dev_a == dev_b:
            raise CableError("Tidak bisa menghubungkan perangkat ke dirinya sendiri.")
        try:
            da, db = self.get(dev_a), self.get(dev_b)
            pa, pb = da.get_port(port_a), db.get_port(port_b)
        except KeyError as e:
            raise CableError(str(e.args[0])) from None
        for dev, port in ((da, pa), (db, pb)):
            if port.link_id is not None:
                raise CableError(f"Port {port.name} pada {dev.name} sudah terhubung.")
        cables.validate_ports(cable, pa.kind, pb.kind)
        lid = link_id if link_id is not None else self._next_link_id
        if lid in self.links:
            raise CableError(f"ID kabel {lid} sudah ada.")
        state, reason = cables.link_state(cable, da.mdi, db.mdi, pa.admin_up, pb.admin_up)
        link = Link(lid, cable, (dev_a, port_a), (dev_b, port_b), state, reason)
        self.links[lid] = link
        self._next_link_id = max(self._next_link_id, lid + 1)
        pa.link_id, pa.connected_to = lid, (dev_b, port_b)
        pb.link_id, pb.connected_to = lid, (dev_a, port_a)
        return link

    def disconnect(self, link_id: int) -> Link:
        if link_id not in self.links:
            raise KeyError(f"Kabel {link_id} tidak ada.")
        link = self.links.pop(link_id)
        for did, pname in (link.a, link.b):
            dev = self.devices.get(did)
            if dev:
                port = dev.get_port(pname)
                port.link_id = port.connected_to = None
        return link

    def refresh_links(self) -> None:
        """Hitung ulang status semua link (mis. setelah port di-shutdown di Phase 6)."""
        for l in self.links.values():
            da, db = self.devices[l.a[0]], self.devices[l.b[0]]
            l.state, l.reason = cables.link_state(l.cable, da.mdi, db.mdi,
                                                  da.get_port(l.a[1]).admin_up, db.get_port(l.b[1]).admin_up)

    # --- konfigurasi IP ---
    def apply_ip_config(self, did: int, ports: dict, gateway=KEEP) -> None:
        """Terapkan konfigurasi IP secara atomik (semua valid atau tidak ada yang berubah).

        `ports`: {nama_port: (ip_text, mask_text)} atau None / ('', '') untuk menghapus.
        `gateway`: teks IP, None/'' untuk menghapus, atau KEEP.
        """
        from devices.base_device import short_port_name
        dev = self.get(did)
        if dev.ip_role == "none":
            raise IPConfigError(f"{dev.label} '{dev.name}' tidak mendukung konfigurasi IP (perangkat layer 2).")
        capable = {p.name for p in dev.ip_ports()}
        new = {p.name: (p.ip, p.prefix) for p in dev.ip_ports()}
        for name, val in ports.items():
            if name not in capable:
                raise IPConfigError(f"Port '{name}' tidak bisa diberi IP.", port=name)
            tag = short_port_name(name)
            ip_t, mask_t = ("", "") if val is None else ((val[0] or "").strip(), (val[1] or "").strip())
            if not ip_t and not mask_t:
                new[name] = (None, None)
                continue
            if not ip_t:
                raise IPConfigError(f"{tag}: IP wajib diisi bila mask diisi.", name, "ip")
            try:
                ip = parse_ip(ip_t)
            except IPv4Error as e:
                raise IPConfigError(f"{tag}: {e}", name, "ip") from None
            if not mask_t:
                raise IPConfigError(f"{tag}: subnet mask wajib diisi (mis. 255.255.255.0 atau /24).", name, "mask")
            try:
                prefix = parse_mask(mask_t)
            except IPv4Error as e:
                raise IPConfigError(f"{tag}: {e}", name, "mask") from None
            err = host_address_error(ip, prefix)
            if err:
                raise IPConfigError(f"{tag}: {err}", name, "ip")
            new[name] = (ip, prefix)
        items = [(n, v) for n, v in new.items() if v[0] is not None]
        for i in range(len(items)):
            for j in range(i + 1, len(items)):
                (na, (ipa, pa)), (nb, (ipb, pb)) = items[i], items[j]
                if overlaps(SubnetInfo(ipa, pa), SubnetInfo(ipb, pb)):
                    bad = nb if (nb in ports or na not in ports) else na
                    other = na if bad == nb else nb
                    raise IPConfigError(f"{short_port_name(bad)}: subnet tumpang tindih dengan {short_port_name(other)} "
                                        "pada perangkat yang sama.", bad, "ip")
        new_gw = dev.gateway
        if gateway is not KEEP:
            g = (gateway or "").strip() if not isinstance(gateway, int) else ip_to_str(gateway)
            if not g:
                new_gw = None
            else:
                if dev.ip_role != "host":
                    raise IPConfigError("Router/firewall tidak memakai default gateway (gunakan routing).", field="gateway")
                try:
                    new_gw = parse_ip(g)
                except IPv4Error as e:
                    raise IPConfigError(f"Gateway: {e}", field="gateway") from None
                err = host_address_error(new_gw, 32)
                if err:
                    raise IPConfigError(f"Gateway: {err}", field="gateway")
                if any(v[0] == new_gw for v in new.values()):
                    raise IPConfigError("Gateway tidak boleh sama dengan IP perangkat itu sendiri.", field="gateway")
        for p in dev.ip_ports():
            p.ip, p.prefix = new[p.name]
        dev.gateway = new_gw
        if hasattr(dev, "sync_connected_routes"):
            dev.sync_connected_routes()

    def set_ip(self, did: int, port: str, ip: str, mask: str) -> None:
        self.apply_ip_config(did, {port: (ip, mask)})

    def clear_ip(self, did: int, port: str) -> None:
        self.apply_ip_config(did, {port: None})

    def set_gateway(self, did: int, gateway: str | None) -> None:
        self.apply_ip_config(did, {}, gateway)

    def ip_conflicts(self) -> list[tuple[str, list[tuple[str, str]]]]:
        """IP yang sama dipakai >1 perangkat: [(ip_str, [(nama_perangkat, nama_port), ...])]."""
        seen: dict[int, list] = {}
        for d in self.devices.values():
            for p in d.ports:
                if p.ip is not None:
                    seen.setdefault(p.ip, []).append((d.id, d.name, p.name))
        return [(ip_to_str(ip), [(n, pn) for _, n, pn in owners]) for ip, owners in seen.items()
                if len({o[0] for o in owners}) > 1]

    # --- query ---
    def device_at(self, x: float, y: float, radius: float = 34) -> BaseDevice | None:
        for dev in reversed(list(self.devices.values())):  # paling atas dulu
            if abs(dev.x - x) <= radius and abs(dev.y - y) <= radius:
                return dev
        return None

    def is_occupied(self, x: float, y: float, exclude: int | None = None, min_dist: float = 56) -> bool:
        return any(d.id != exclude and abs(d.x - x) < min_dist and abs(d.y - y) < min_dist
                   for d in self.devices.values())

    def find_free_spot(self, cx: float, cy: float, exclude: int | None = None) -> tuple[int, int]:
        cx, cy = snap(cx), snap(cy)
        for r in range(0, 12):
            for dx in range(-r, r + 1):
                for dy in range(-r, r + 1):
                    if max(abs(dx), abs(dy)) != r:
                        continue
                    x, y = cx + dx * GRID * 3, cy + dy * GRID * 3
                    if not self.is_occupied(x, y, exclude):
                        return x, y
        return cx, cy

    def counts(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for d in self.devices.values():
            out[d.type] = out.get(d.type, 0) + 1
        return out

    def total_cost(self) -> int:
        return sum(d.cost for d in self.devices.values())

    # --- serialisasi ---
    def to_dict(self) -> dict:
        return {"version": 3, "devices": [d.to_dict() for d in self.devices.values()],
                "links": [l.to_dict() for l in self.links.values()]}

    @classmethod
    def from_dict(cls, data: dict, catalog: dict | None = None) -> "Topology":
        topo = cls(catalog)
        for item in data.get("devices", []):
            try:
                topo.add_device(item["type"], item["x"], item["y"], item.get("name"),
                                item.get("rotation", 0), item["id"])
            except (KeyError, ValueError):
                continue  # data rusak/jenis tidak dikenal dilewati
            cfg = item.get("config") or {}
            for pname, val in (cfg.get("ports") or {}).items():
                try:
                    topo.apply_ip_config(item["id"], {pname: tuple(val)})
                except (ValueError, KeyError, TypeError):
                    continue
            try:
                topo.apply_ip_config(item["id"], {}, cfg.get("gateway"))
            except (ValueError, KeyError, TypeError):
                pass
        for item in data.get("links", []):
            try:
                topo.connect(item["a"][0], item["a"][1], item["b"][0], item["b"][1], item["cable"], item.get("id"))
            except (KeyError, ValueError, IndexError, TypeError):
                continue
        return topo
