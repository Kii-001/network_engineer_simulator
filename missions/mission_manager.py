"""Pengelola misi, pemuatan level, evaluasi keberhasilan, dan pemberian reward."""
from __future__ import annotations

import json
from pathlib import Path
import config
from networking.ip_address import ip_to_str


class MissionManager:
    def __init__(self, catalog_path: Path | str | None = None) -> None:
        p = Path(catalog_path) if catalog_path else config.BASE_DIR / "data" / "missions.json"
        with open(p, encoding="utf-8") as f:
            self.missions: list[dict] = json.load(f)
        self.by_id: dict[int, dict] = {m["id"]: m for m in self.missions}

    def get_mission(self, mission_id: int) -> dict:
        if mission_id not in self.by_id:
            raise KeyError(f"Misi ID {mission_id} tidak ditemukan.")
        return self.by_id[mission_id]

    def evaluate_mission(self, mission_id: int, topology, elapsed_seconds: float = 0.0) -> dict:
        """Evaluasi kepatuhan topologi terhadap kriteria kelulusan misi."""
        mission = self.get_mission(mission_id)
        criteria = mission.get("success_criteria", {})
        errors = []
        passed_objectives = []

        total_cost = topology.total_cost()
        budget = mission.get("budget", 1000)
        budget_ok = total_cost <= budget
        if not budget_ok:
            errors.append(f"Biaya (${total_cost}) melebihi anggaran yang diberikan (${budget}).")

        # 1. Cek jumlah perangkat minimal
        min_devs = criteria.get("min_devices", {})
        counts = topology.counts()
        for dtype, required_count in min_devs.items():
            actual = counts.get(dtype, 0)
            if actual < required_count:
                errors.append(f"Kurang perangkat {dtype}: butuh minimal {required_count}, saat ini {actual}.")
            else:
                passed_objectives.append(f"Perangkat {dtype} terpenuhi ({actual}/{required_count})")

        # 2. Cek link aktif
        if criteria.get("links_active", False):
            up_links = [l for l in topology.links.values() if l.state == "up"]
            if not up_links:
                errors.append("Tidak ada kabel jaringan yang berstatus aktif (UP).")
            else:
                passed_objectives.append(f"{len(up_links)} kabel berstatus aktif UP")

        # 3. Cek VLAN
        req_vlans = criteria.get("vlans_created", [])
        if req_vlans:
            found_vlans = set()
            for d in topology.devices.values():
                if hasattr(d, "vlans"):
                    found_vlans.update(d.vlans.keys())
            missing = [v for v in req_vlans if v not in found_vlans]
            if missing:
                errors.append(f"VLAN {missing} belum dibuat pada switch.")
            else:
                passed_objectives.append(f"VLAN {req_vlans} terkonfigurasi")

        # 4. Cek DHCP
        if criteria.get("dhcp_enabled", False):
            dhcp_ok = any(hasattr(d, "dhcp_service") and d.dhcp_service.enabled for d in topology.devices.values())
            if not dhcp_ok:
                errors.append("Layanan DHCP Server belum diaktifkan.")
            else:
                passed_objectives.append("DHCP Server aktif")

        # 5. Cek Port Security
        if criteria.get("port_security_active", False):
            sec_ok = any(
                any(sec.get("enabled") for sec in getattr(d, "port_security", {}).values())
                for d in topology.devices.values()
            )
            if not sec_ok:
                errors.append("Port security belum diaktifkan pada switch.")
            else:
                passed_objectives.append("Port security aktif")

        # 6. Cek ACL / Firewall
        if criteria.get("acls_configured", 0) > 0:
            acls_found = sum(len(getattr(d, "acls", {})) for d in topology.devices.values())
            if acls_found == 0:
                errors.append("Belum ada Access Control List (ACL) yang dikonfigurasi.")
            else:
                passed_objectives.append("ACL terkonfigurasi")

        # 7. Cek OSPF / RIP
        if criteria.get("ospf_routers", 0) > 0:
            ospf_count = sum(1 for d in topology.devices.values() if getattr(d, "ospf_enabled", False))
            if ospf_count < criteria["ospf_routers"]:
                errors.append(f"OSPF butuh {criteria['ospf_routers']} router, saat ini {ospf_count}.")
            else:
                passed_objectives.append(f"{ospf_count} router menjalankan OSPF")

        # Hitung skor dan bintang
        success = (len(errors) == 0)
        base_score = 70 if success else max(0, 50 - len(errors) * 15)
        
        # Bonus efisiensi anggaran & waktu
        time_limit = mission.get("time_limit", 300)
        time_bonus = 15 if (success and elapsed_seconds <= time_limit) else 0
        budget_bonus = 15 if (success and total_cost <= budget * 0.85) else (10 if success else 0)

        total_score = min(100, base_score + time_bonus + budget_bonus) if success else base_score
        stars = 3 if total_score >= 90 else (2 if total_score >= 75 else (1 if success else 0))

        xp = mission.get("xp_reward", 100) if success else 20
        coins = mission.get("coin_reward", 50) if success else 10

        return {
            "success": success,
            "mission_id": mission_id,
            "title": mission["title"],
            "score": total_score,
            "stars": stars,
            "xp": xp,
            "coins": coins,
            "passed_objectives": passed_objectives,
            "errors": errors,
            "elapsed_seconds": elapsed_seconds,
        }
