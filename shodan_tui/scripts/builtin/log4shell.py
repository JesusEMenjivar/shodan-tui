"""
Log4Shell (CVE-2021-44228) — find hosts still vulnerable to the Log4j RCE.
One of the most critical vulnerabilities ever disclosed (CVSS 10.0).
"""

from shodan_tui.scripts.base import ShodanScript


class Log4ShellScript(ShodanScript):
    name = "Log4Shell Scanner"
    description = (
        "Find hosts flagged by Shodan as vulnerable to CVE-2021-44228 (Log4Shell), "
        "the critical Log4j remote code execution vulnerability (CVSS 10.0)."
    )
    author = "shodan-tui"
    version = "1.0.0"
    tags = ["cve", "log4j", "rce", "critical", "java"]
    query = "vuln:CVE-2021-44228"
    facets = "country,org,product"

    params = {
        "country": {
            "type": "str",
            "description": "Filter by 2-letter country code",
            "default": "",
        },
        "org": {
            "type": "str",
            "description": "Filter by organization name",
            "default": "",
        },
    }

    def build_query(self, **kwargs) -> str:
        q = self.query
        country = kwargs.get("country", "").strip().upper()
        org = kwargs.get("org", "").strip()
        if country:
            q += f" country:{country}"
        if org:
            q += f' org:"{org}"'
        return q

    def format_summary(self, results: dict) -> str:
        total = results.get("total", 0)
        return f"Found {total:,} hosts still vulnerable to Log4Shell (CVE-2021-44228)."
