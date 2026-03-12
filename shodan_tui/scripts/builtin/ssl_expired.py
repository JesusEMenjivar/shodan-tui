"""
Expired SSL Certificates — find hosts serving expired TLS certificates.
Expired certs can indicate abandoned/unmaintained infrastructure.
"""

from shodan_tui.scripts.base import ShodanScript


class ExpiredSSLScript(ShodanScript):
    name = "Expired SSL Certs"
    description = (
        "Find hosts serving expired TLS/SSL certificates. "
        "Expired certs often indicate neglected or abandoned infrastructure, "
        "a useful signal during org-wide OSINT recon."
    )
    author = "shodan-tui"
    version = "1.0.0"
    tags = ["ssl", "tls", "certificate", "recon", "infrastructure"]
    query = 'ssl.cert.expired:true'
    facets = "org,country"

    params = {
        "org": {
            "type": "str",
            "description": "Target organization name",
            "default": "",
        },
        "country": {
            "type": "str",
            "description": "Filter by 2-letter country code",
            "default": "",
        },
    }

    def build_query(self, **kwargs) -> str:
        q = self.query
        org = kwargs.get("org", "").strip()
        country = kwargs.get("country", "").strip().upper()
        if org:
            q += f' org:"{org}"'
        if country:
            q += f" country:{country}"
        return q

    def format_summary(self, results: dict) -> str:
        total = results.get("total", 0)
        return f"Found {total:,} hosts with expired SSL/TLS certificates."
