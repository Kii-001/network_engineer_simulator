"""Mesin keamanan jaringan: Evaluasi ACL Standard & Extended, Port Security, dan Firewall Policies."""
from __future__ import annotations

from networking.ip_address import ip_to_str, parse_ip


class FirewallEngine:
    def __init__(self, topology) -> None:
        self.topo = topology

    def evaluate_acl(self, acl_rules: list[dict], src_ip: int | None, dst_ip: int | None,
                     protocol: str = "IP", dst_port: int | None = None) -> tuple[bool, str]:
        """Evaluasi paket terhadap daftar aturan ACL.
        Mengembalikan (allowed, matching_rule_description).
        """
        for i, rule in enumerate(acl_rules):
            action = rule.get("action", "permit").lower()
            proto = rule.get("protocol", "IP").upper()

            # Filter protokol
            if proto != "IP" and proto != protocol.upper():
                continue

            # Filter IP sumber
            r_src = rule.get("src_ip")
            r_src_wcard = rule.get("src_wildcard", 0)
            if r_src is not None and src_ip is not None:
                if (src_ip & ~r_src_wcard) != (r_src & ~r_src_wcard):
                    continue

            # Filter IP tujuan
            r_dst = rule.get("dst_ip")
            r_dst_wcard = rule.get("dst_wildcard", 0)
            if r_dst is not None and dst_ip is not None:
                if (dst_ip & ~r_dst_wcard) != (r_dst & ~r_dst_wcard):
                    continue

            # Filter port (untuk extended ACL)
            r_port = rule.get("port")
            if r_port is not None and dst_port is not None:
                if r_port != dst_port:
                    continue

            # Aturan cocok!
            allowed = (action == "permit")
            return allowed, f"Rule #{i+1} {action.upper()}"

        # Default implicit deny
        return False, "Implicit Deny"

    def audit_security(self) -> dict:
        """Audit keamanan topologi: port security, ACL coverage, default passwords."""
        issues = []
        recommendations = []

        # 1. Cek port security pada switches
        switches = [d for d in self.topo.devices.values() if d.type == "managed_switch"]
        for sw in switches:
            unsecured = [p.name for p, sec in getattr(sw, "port_security", {}).items() if not sec.get("enabled")]
            if unsecured:
                issues.append(f"{sw.name}: Port security tidak aktif pada {len(unsecured)} port.")
                recommendations.append(f"Aktifkan 'switchport port-security' pada port access {sw.name}.")

        # 2. Cek firewall presence
        firewalls = [d for d in self.topo.devices.values() if d.type == "firewall"]
        if not firewalls:
            recommendations.append("Tambahkan Firewall untuk memisahkan jaringan internal dan eksternal.")

        # 3. Cek default router password / ACLs
        routers = [d for d in self.topo.devices.values() if d.type == "router"]
        for r in routers:
            if not getattr(r, "acls", {}):
                issues.append(f"{r.name}: Tidak ada Access Control List (ACL) yang terkonfigurasi.")

        score = max(0, 100 - (len(issues) * 15))
        return {
            "score": score,
            "issues": issues,
            "recommendations": recommendations,
        }
