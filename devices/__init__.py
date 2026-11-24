"""Pabrik perangkat (Device Factory) untuk instansiasi tipe perangkat yang tepat."""
from __future__ import annotations

from devices.base_device import BaseDevice
from devices.router import Router
from devices.switch import Switch
from devices.managed_switch import ManagedSwitch
from devices.server import Server
from devices.computer import Computer
from devices.firewall import Firewall
from devices.access_point import AccessPoint

DEVICE_CLASSES = {
    "router": Router,
    "switch": Switch,
    "managed_switch": ManagedSwitch,
    "hub": Switch,  # Hub mewarisi BaseDevice / Switch dengan logika L1 di engine
    "server": Server,
    "pc": Computer,
    "laptop": Computer,
    "printer": Computer,
    "firewall": Firewall,
    "access_point": AccessPoint,
    "modem": BaseDevice,
    "internet_cloud": BaseDevice,
}


def create_device(device_id: int, dtype: str, spec: dict, name: str,
                  x: float, y: float, rotation: int = 0) -> BaseDevice:
    cls = DEVICE_CLASSES.get(dtype, BaseDevice)
    return cls(device_id, dtype, spec, name, x, y, rotation)
