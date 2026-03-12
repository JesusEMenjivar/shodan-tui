"""
Results screen — displays paginated Shodan search results.
Populated automatically when a search completes in the Search tab.
"""

from __future__ import annotations

import json
from datetime import datetime

from textual import on, work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Button, DataTable, Label, Static

from shodan_tui.api import ShodanAPIError


FLAG_MAP = {
    "US": "🇺🇸", "GB": "🇬🇧", "DE": "🇩🇪", "CN": "🇨🇳", "RU": "🇷🇺",
    "FR": "🇫🇷", "JP": "🇯🇵", "NL": "🇳🇱", "BR": "🇧🇷", "IN": "🇮🇳",
    "CA": "🇨🇦", "AU": "🇦🇺", "SG": "🇸🇬", "KR": "🇰🇷", "IT": "🇮🇹",
}


def _flag(cc: str) -> str:
    return FLAG_MAP.get((cc or "").upper(), "🏳")


class ResultsPane(Container):
    """Full-screen results table with pagination and export."""

    BINDINGS = [
        Binding("s", "save_selected", "Save Host"),
    ]

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._results: list[dict] = []
        self._current_query: str = ""
        self._total: int = 0
        self._page: int = 1
        self._facets: dict = {}

    @property
    def api(self):
        return self.app.api  # type: ignore[attr-defined]

    @property
    def storage(self):
        return self.app.storage  # type: ignore[attr-defined]

    def compose(self) -> ComposeResult:
        with Horizontal(id="results-outer"):
            # ── Main column: header + table + pagination ───────────────────────
            with Vertical(id="results-main"):
                with Horizontal(id="results-header"):
                    yield Static("No results yet — run a search first.", id="results-meta")
                    with Horizontal(id="results-export-btns"):
                        yield Button("Export JSON", id="btn-export-json", variant="default")
                        yield Button("Export CSV",  id="btn-export-csv",  variant="default")

                yield DataTable(id="results-table", cursor_type="row", zebra_stripes=True)

                with Horizontal(id="results-nav", classes="hidden"):
                    yield Button("◀ Prev", id="btn-prev", variant="default")
                    yield Static("", id="page-indicator")
                    yield Button("Next ▶", id="btn-next", variant="default")

            # ── Facets sidebar ─────────────────────────────────────────────────
            with Vertical(id="results-facets", classes="hidden"):
                yield Label("BREAKDOWN", classes="section-label")
                yield Static("", id="facets-content")

    def on_mount(self) -> None:
        table = self.query_one("#results-table", DataTable)
        table.add_columns("IP", "Port", "Org", "CC", "Product", "Hostname", "Vulns")

    # ── Public API (called by app.py after SearchCompleted) ───────────────────

    def load_results(self, query: str, data: dict, page: int) -> None:
        """Populate the table from a fresh search result dict."""
        self._current_query = query
        self._page = page
        self._total = data.get("total", 0)
        self._results = data.get("matches", [])
        self._facets = data.get("facets", {})
        self._refresh_table()
        self._refresh_facets()

    # ── Table rendering ───────────────────────────────────────────────────────

    def _refresh_table(self) -> None:
        """Clear and repopulate the DataTable from self._results."""
        table = self.query_one("#results-table", DataTable)
        table.clear()

        max_page = max(1, (self._total + 99) // 100)
        self.query_one("#results-meta", Static).update(
            f"[bold cyan]{self._current_query}[/bold cyan]  ·  "
            f"[bold green]{self._total:,}[/bold green] results  ·  "
            f"page [bold]{self._page}[/bold] / [bold]{max_page}[/bold]"
        )

        for match in self._results:
            ip       = match.get("ip_str", "")
            port     = str(match.get("port", ""))
            org      = (match.get("org") or match.get("isp") or "")[:28]
            cc       = match.get("location", {}).get("country_code") or match.get("country_code", "")
            product  = (match.get("product") or "")[:22]
            hostname = (match.get("hostnames") or [""])[0][:34]
            vuln_n   = len(match.get("vulns", {}))
            vuln_str = f"[red]⚠ {vuln_n}[/red]" if vuln_n else ""
            table.add_row(ip, port, org, f"{_flag(cc)} {cc}", product, hostname, vuln_str, key=f"{ip}:{port}")

        nav = self.query_one("#results-nav")
        nav.remove_class("hidden")
        self.query_one("#page-indicator", Static).update(f"  Page {self._page}/{max_page}  ")
        self.query_one("#btn-prev", Button).disabled = self._page <= 1
        self.query_one("#btn-next", Button).disabled = self._page >= max_page

    # ── Facets sidebar ────────────────────────────────────────────────────────

    def _refresh_facets(self) -> None:
        """Update the breakdown sidebar from self._facets."""
        panel = self.query_one("#results-facets")
        content = self.query_one("#facets-content", Static)

        if not self._facets:
            panel.add_class("hidden")
            return

        lines: list[str] = []
        for key, label in (("country", "Country"), ("org", "Org"), ("port", "Port")):
            items = self._facets.get(key, [])
            if not items:
                continue
            if lines:
                lines.append("")
            lines.append(f"[bold cyan]{label}[/bold cyan]")
            for item in items[:5]:
                val = str(item.get("value", ""))[:20]
                count = item.get("count", 0)
                # right-align the count with a dim style
                lines.append(f"  {val:<20} [dim]{count:,}[/dim]")

        if lines:
            content.update("\n".join(lines))
            panel.remove_class("hidden")
        else:
            panel.add_class("hidden")

    # ── Pagination ────────────────────────────────────────────────────────────

    @on(Button.Pressed, "#btn-prev")
    def prev_page(self) -> None:
        if self._page > 1:
            self._page -= 1
            self._fetch_page()

    @on(Button.Pressed, "#btn-next")
    def next_page(self) -> None:
        max_page = max(1, (self._total + 99) // 100)
        if self._page < max_page:
            self._page += 1
            self._fetch_page()

    @work(exclusive=True)
    async def _fetch_page(self) -> None:
        meta = self.query_one("#results-meta", Static)
        meta.update("⏳ Loading page…")
        try:
            data = await self.api.search(self._current_query, page=self._page)
            self._total   = data.get("total", 0)
            self._results = data.get("matches", [])
            self._refresh_table()
        except ShodanAPIError as e:
            self.notify(str(e), severity="error", title="API Error")
            meta.update(f"[red]Error: {e}[/red]")

    # ── Row selection → host detail ───────────────────────────────────────────

    @on(DataTable.RowSelected, "#results-table")
    def on_row_selected(self, event: DataTable.RowSelected) -> None:
        # key is "ip:port" — extract just the IP portion
        key = str(event.row_key.value)
        ip = key.split(":")[0]
        self.app.push_screen("host", {"ip": ip})  # type: ignore[attr-defined]

    # ── Save selected host ────────────────────────────────────────────────────

    def action_save_selected(self) -> None:
        table = self.query_one("#results-table", DataTable)
        if table.cursor_row < 0 or not self._results:
            return
        row_key = table.coordinate_to_cell_key(table.cursor_coordinate).row_key
        # key is "ip:port" — extract just the IP portion
        ip = str(row_key.value).split(":")[0]
        match = next((m for m in self._results if m.get("ip_str") == ip), {})
        label = match.get("org") or None   # don't overwrite existing label if org is absent
        self.storage.save_target(ip, label=label)
        self.notify(f"Saved {ip} to workspace.", title="Saved ★")

    # ── Export ────────────────────────────────────────────────────────────────

    @property
    def _exports_dir(self):
        return self.app.config.exports_dir  # type: ignore[attr-defined]

    @on(Button.Pressed, "#btn-export-json")
    def export_json(self) -> None:
        if not self._results:
            self.notify("No results to export.", severity="warning")
            return
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = self._exports_dir / f"search_results_p{self._page}_{ts}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(
                {"query": self._current_query, "total": self._total, "matches": self._results},
                f, indent=2,
            )
        self.notify(f"Saved → {path}", title="Exported")

    @on(Button.Pressed, "#btn-export-csv")
    def export_csv(self) -> None:
        if not self._results:
            self.notify("No results to export.", severity="warning")
            return
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = self._exports_dir / f"search_results_p{self._page}_{ts}.csv"
        with open(path, "w", encoding="utf-8") as f:
            f.write("ip,port,org,country,product,hostname,vulns\n")
            for m in self._results:
                ip       = m.get("ip_str", "")
                port     = m.get("port", "")
                org      = (m.get("org") or "").replace(",", " ")
                cc       = m.get("location", {}).get("country_code") or m.get("country_code", "")
                product  = (m.get("product") or "").replace(",", " ")
                hostname = (m.get("hostnames") or [""])[0]
                vulns    = len(m.get("vulns", {}))
                f.write(f"{ip},{port},{org},{cc},{product},{hostname},{vulns}\n")
        self.notify(f"Saved → {path}", title="Exported")
