"""
Example user script — copy this file, rename it, and customize it.

Place finished scripts in:
  - ./user_scripts/                       (project-local)
  - ~/.config/shodan-tui/scripts/         (user-global, persists across projects)

Then manage them from the Scripts tab in shodan-tui.
"""

from shodan_tui.scripts.base import ShodanScript


class ExampleScript(ShodanScript):
    name = "Example Script"
    description = "A template — replace this with your own description."
    author = "you"
    version = "1.0.0"
    tags = ["example", "template"]

    # The Shodan query to run. Can be any valid Shodan search syntax.
    query = "apache port:80 country:US"

    # Optional: request facet breakdowns alongside results
    facets = "country,org"

    # Optional: declare runtime parameters the user can fill in
    params = {
        "country": {
            "type": "str",
            "description": "Filter by 2-letter country code (e.g. US, DE, GB)",
            "default": "US",
        },
    }

    def build_query(self, **kwargs) -> str:
        """Build the final query string. Override to support params."""
        country = kwargs.get("country", "US").strip().upper()
        return f"apache port:80 country:{country}"

    async def process(self, api, results: dict) -> dict:
        """
        Optional: enrich or filter the raw results dict.
        `api` is a live ShodanAPI instance — you can make additional API calls here.
        """
        return results

    def format_summary(self, results: dict) -> str:
        total = results.get("total", 0)
        return f"Example script found {total:,} results."
