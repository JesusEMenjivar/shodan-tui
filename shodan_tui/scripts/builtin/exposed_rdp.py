"""
Exposed RDP — find Remote Desktop Protocol servers indexed by Shodan.
RDP on port 3389 exposed to the internet is a common attack vector.
"""

from shodan_tui.scripts.base import ShodanScript


class ExposedRDPScript(ShodanScript):
    name = "Exposed RDP"
    description = (
        "Find internet-exposed Remote Desktop Protocol (RDP) servers. "
        "Useful for identifying attack surface on Windows infrastructure."
    )
    author = "shodan-tui"
    version = "1.0.0"
    tags = ["windows", "rdp", "exposure", "attack-surface"]
    query = "port:3389 product:\"Remote Desktop Protocol\""
    facets = "country,org"

    params = {
        "country": {
            "type": "str",
            "description": "Filter by 2-letter country code (e.g. US, DE)",
            "default": "",
        },
        "has_screenshot": {
            "type": "bool",
            "description": "Only include hosts with screenshots captured by Shodan",
            "default": False,
        },
    }

    def build_query(self, **kwargs) -> str:
        q = self.query
        country = kwargs.get("country", "").strip().upper()
        has_screenshot = kwargs.get("has_screenshot", False)
        if country:
            q += f" country:{country}"
        if has_screenshot:
            q += " has_screenshot:true"
        return q

    def format_summary(self, results: dict) -> str:
        total = results.get("total", 0)
        return f"Found {total:,} exposed RDP servers."
