"""Aturan kabel & kompatibilitas port. Murni logika (tanpa pygame)."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CableType:
    key: str
    label: str
    color: tuple
    style: str            # solid | dashed | dotted
    width: int
    summary: str
    port_kinds: frozenset
    detail: str = ""      # penjelasan panjang untuk log


CABLE_TYPES: dict[str, CableType] = {
    "straight": CableType("straight", "Straight-Through", (0, 229, 255), "solid", 3,
                          "Beda jenis", frozenset({"RJ45"}), "Untuk perangkat BERBEDA jenis, mis. PC-Switch atau Router-Switch."),
    "crossover": CableType("crossover", "Crossover", (255, 140, 50), "dashed", 3,
                           "Sejenis", frozenset({"RJ45"}), "Untuk perangkat SEJENIS, mis. PC-PC, Switch-Switch, atau Router-PC."),
    "fiber": CableType("fiber", "Fiber Optic", (255, 196, 61), "solid", 2,
                       "Fiber-Fiber", frozenset({"FIBER"}), "Hanya port FIBER ke FIBER (jarak jauh, antar gedung)."),
    "console": CableType("console", "Console Cable", (120, 190, 255), "dotted", 3,
                         "Console-RS232", frozenset({"CONSOLE", "RS232"}), "Port CONSOLE perangkat ke port RS232 komputer."),
}

CLASS_LABEL = {"MDI": "perangkat ujung/router (MDI)", "MDIX": "switch/hub (MDI-X)"}


class CableError(ValueError):
    """Koneksi ditolak (tidak mungkin secara fisik / aturan)."""


def port_supports(cable: str, kind: str) -> bool:
    return kind in CABLE_TYPES[cable].port_kinds


def validate_ports(cable: str, kind_a: str, kind_b: str) -> None:
    """Cek apakah kabel secara fisik bisa dipasang pada dua jenis port. Raise CableError bila tidak."""
    if cable not in CABLE_TYPES:
        raise CableError(f"Jenis kabel tidak dikenal: {cable}")
    ct = CABLE_TYPES[cable]
    if "WIRELESS" in (kind_a, kind_b):
        raise CableError("Port wireless tidak memakai kabel.")
    if cable == "console":
        if {kind_a, kind_b} != {"CONSOLE", "RS232"}:
            raise CableError("Kabel console hanya untuk port CONSOLE <-> RS232 (komputer).")
        return
    for kind in (kind_a, kind_b):
        if kind not in ct.port_kinds:
            raise CableError(f"{ct.label} tidak cocok untuk port {kind}.")


def link_state(cable: str, class_a: str, class_b: str, admin_a: bool = True, admin_b: bool = True) -> tuple[str, str]:
    """Status link ('up'/'down') + alasan (dipakai juga untuk Cable Diagnostics)."""
    if not (admin_a and admin_b):
        return "down", "Salah satu port dimatikan (shutdown)."
    if cable == "console":
        return "up", "Sesi console tersedia."
    if cable == "fiber":
        return "up", "Fiber optic terhubung."
    same = class_a == class_b
    if cable == "straight" and same:
        return "down", (f"Salah kabel: kedua ujung sama-sama {CLASS_LABEL[class_a]}. "
                        "Straight-Through untuk perangkat berbeda jenis; gunakan Crossover.")
    if cable == "crossover" and not same:
        return "down", (f"Salah kabel: ujungnya {CLASS_LABEL[class_a]} dan {CLASS_LABEL[class_b]} (beda jenis). "
                        "Crossover untuk perangkat sejenis; gunakan Straight-Through.")
    return "up", "Link normal."


@dataclass
class Link:
    id: int
    cable: str
    a: tuple          # (device_id, port_name)
    b: tuple
    state: str = "up"
    reason: str = ""

    def to_dict(self) -> dict:
        return {"id": self.id, "cable": self.cable, "a": list(self.a), "b": list(self.b)}
