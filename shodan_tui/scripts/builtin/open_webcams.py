"""
Open Webcams — find internet-accessible IP cameras with no authentication.
Useful for demonstrating IoT exposure risks in OSINT investigations.
"""

from shodan_tui.scripts.base import ShodanScript


class OpenWebcamsScript(ShodanScript):
    name = "Open Webcams"
    description = (
        "Find publicly accessible IP cameras and webcams indexed by Shodan. "
        "Demonstrates IoT/camera exposure commonly found during OSINT recon."
    )
    author = "shodan-tui"
    version = "1.0.0"
    tags = ["iot", "camera", "webcam", "exposure"]
    query = 'title:"webcam" has_screenshot:true'
    facets = "country,org"

    params = {
        "country": {
            "type": "str",
            "description": "Filter by 2-letter country code",
            "default": "",
        },
        "brand": {
            "type": "str",
            "description": "Camera brand keyword (e.g. Hikvision, Dahua, Axis)",
            "default": "",
        },
    }

    def build_query(self, **kwargs) -> str:
        country = kwargs.get("country", "").strip().upper()
        brand = kwargs.get("brand", "").strip()

        if brand:
            q = f'product:"{brand}" has_screenshot:true'
        else:
            q = self.query

        if country:
            q += f" country:{country}"
        return q

    def format_summary(self, results: dict) -> str:
        total = results.get("total", 0)
        return f"Found {total:,} accessible webcam/camera interfaces."
