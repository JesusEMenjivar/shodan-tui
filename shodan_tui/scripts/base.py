"""
Base class for all Shodan TUI scan scripts.

To create a custom script, subclass ShodanScript and place your file in
~/.config/shodan-tui/scripts/ or the user_scripts/ project directory.

Example
-------
from shodan_tui.scripts.base import ShodanScript

class MyScript(ShodanScript):
    name        = "My Custom Scan"
    description = "Finds something interesting"
    author      = "yourname"
    version     = "1.0.0"
    tags        = ["recon", "custom"]
    query       = "product:nginx port:8080"

    # Optional: override to add extra filters at runtime
    def build_query(self, **kwargs) -> str:
        country = kwargs.get("country")
        q = self.query
        if country:
            q += f" country:{country}"
        return q

    # Optional: post-process/enrich results
    async def process(self, api, results: dict) -> dict:
        return results
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from shodan_tui.api import ShodanAPI


class ShodanScript(ABC):
    # ── Required metadata ────────────────────────────────────────────────────
    name: str = "Unnamed Script"
    description: str = ""
    author: str = "unknown"
    version: str = "1.0.0"
    tags: list[str] = []

    # ── Optional defaults ─────────────────────────────────────────────────────
    # Set `query` directly for simple scripts.
    # Override `build_query()` for parameterized scripts.
    query: str = ""

    # Shodan facets to request alongside results (e.g. "country,org")
    facets: str | None = None

    # Runtime parameters the user can fill in before running.
    # Format: {"param_name": {"type": "str"|"int", "description": "...", "default": ...}}
    params: dict[str, dict[str, Any]] = {}

    # ── Interface ─────────────────────────────────────────────────────────────

    def build_query(self, **kwargs: Any) -> str:
        """
        Return the Shodan query string to execute.
        Override this to support runtime parameters.
        """
        return self.query

    async def process(self, api: "ShodanAPI", results: dict) -> dict:
        """
        Optionally enrich or filter the raw Shodan search results dict.
        Return the (possibly modified) results dict.
        """
        return results

    def format_summary(self, results: dict) -> str:
        """
        Return a short human-readable summary line shown after the script runs.
        Override to provide script-specific insight.
        """
        total = results.get("total", 0)
        return f"{total:,} results found for query: {self.build_query()}"

    # ── Helpers ───────────────────────────────────────────────────────────────

    @classmethod
    def meta(cls) -> dict[str, Any]:
        return {
            "name": cls.name,
            "description": cls.description,
            "author": cls.author,
            "version": cls.version,
            "tags": cls.tags,
            "query": cls.query,
            "params": cls.params,
        }
