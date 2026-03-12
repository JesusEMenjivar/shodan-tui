"""
Search screen — query input, filter builder, and search history.
Results are displayed in the dedicated Results tab after a search completes.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual import on, work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.message import Message
from textual.widgets import (
    Button,
    Collapsible,
    Input,
    Label,
    ListItem,
    ListView,
    Static,
)

from shodan_tui.api import ShodanAPIError

if TYPE_CHECKING:
    from shodan_tui.app import ShodanTUI


class SearchPane(Container):
    """Search tab — query input, filter builder, and history."""

    # ── Message posted when a search returns results ───────────────────────────
    class SearchCompleted(Message):
        """Posted after a successful search so the Results tab can display it."""
        def __init__(self, query: str, data: dict, page: int) -> None:
            super().__init__()
            self.query = query
            self.data = data
            self.page = page

    BINDINGS = [
        Binding("f5", "run_search", "Search"),
        Binding("escape", "blur_input", "Blur"),
    ]

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._current_query: str = ""
        self._page: int = 1

    @property
    def api(self):
        return self.app.api  # type: ignore[attr-defined]

    @property
    def storage(self):
        return self.app.storage  # type: ignore[attr-defined]

    def compose(self) -> ComposeResult:
        with Horizontal(id="search-top"):
            # ── Left: query + filters ─────────────────────────────────────────
            with Vertical(id="search-left"):
                yield Label("QUERY", classes="section-label")
                yield Input(
                    placeholder="e.g.  apache port:443 country:US",
                    id="query-input",
                )

                with Horizontal(id="search-buttons"):
                    yield Button("Search [F5]", id="btn-search", variant="primary")
                    yield Button("Count →",     id="btn-count",  variant="default")
                    yield Button("Clear",        id="btn-clear-query", variant="default")
                    yield Button("Build →",      id="btn-build",  variant="default")

                yield Static("", id="count-result", classes="hidden")

                with Collapsible(title="Advanced Filters", collapsed=True, id="filter-collapsible"):
                    with Container(id="filter-grid"):
                        yield Label("Port:", classes="filter-label")
                        yield Input(placeholder="443", id="f-port", classes="filter-input")
                        yield Label("Country:", classes="filter-label")
                        yield Input(placeholder="US", id="f-country", classes="filter-input")
                        yield Label("Org:", classes="filter-label")
                        yield Input(placeholder='e.g. "Amazon"', id="f-org", classes="filter-input")
                        yield Label("Product:", classes="filter-label")
                        yield Input(placeholder="nginx", id="f-product", classes="filter-input")
                        yield Label("Version:", classes="filter-label")
                        yield Input(placeholder="1.14", id="f-version", classes="filter-input")
                        yield Label("OS:", classes="filter-label")
                        yield Input(placeholder="Windows", id="f-os", classes="filter-input")
                        yield Label("Net (CIDR):", classes="filter-label")
                        yield Input(placeholder="192.168.1.0/24", id="f-net", classes="filter-input")
                        yield Label("CVE:", classes="filter-label")
                        yield Input(placeholder="CVE-2021-44228", id="f-vuln", classes="filter-input")
                        yield Label("ASN:", classes="filter-label")
                        yield Input(placeholder="AS701", id="f-asn", classes="filter-input")

            # ── Right: history + saved ────────────────────────────────────────
            with Vertical(id="search-right"):
                with Horizontal(id="history-header"):
                    yield Label("HISTORY", classes="section-label")
                    yield Button("✕ Clear", id="btn-clear-history", variant="error")
                yield ListView(id="history-list")

        yield Static("", id="search-status")

    def on_mount(self) -> None:
        self._refresh_history()

    # ── History ───────────────────────────────────────────────────────────────

    def _refresh_history(self) -> None:
        lv = self.query_one("#history-list", ListView)
        lv.clear()
        for entry in self.storage.history[:20]:
            lv.append(ListItem(Label(entry.query), name=entry.query))

    @on(ListView.Selected, "#history-list")
    def on_history_selected(self, event: ListView.Selected) -> None:
        query = event.item.name or ""
        if query:
            self.query_one("#query-input", Input).value = query
            self._current_query = query
            self._page = 1
            self.call_after_refresh(self._run_search)

    # ── Filter builder ────────────────────────────────────────────────────────

    def _get_field(self, field_id: str) -> str:
        return self.query_one(f"#{field_id}", Input).value.strip()

    @on(Button.Pressed, "#btn-build")
    def build_query_from_filters(self) -> None:
        parts = [self._get_field("query-input")]
        filters = {
            "port":    self._get_field("f-port"),
            "country": self._get_field("f-country"),
            "org":     self._get_field("f-org"),
            "product": self._get_field("f-product"),
            "version": self._get_field("f-version"),
            "os":      self._get_field("f-os"),
            "net":     self._get_field("f-net"),
            "vuln":    self._get_field("f-vuln"),
            "asn":     self._get_field("f-asn"),
        }
        for key, val in filters.items():
            if val:
                parts.append(f'{key}:"{val}"' if key in ("org", "product") and " " in val else f"{key}:{val}")
        self.query_one("#query-input", Input).value = " ".join(p for p in parts if p)

    # ── Search ────────────────────────────────────────────────────────────────

    @on(Button.Pressed, "#btn-search")
    def on_search_button_pressed(self) -> None:
        query = self.query_one("#query-input", Input).value.strip()
        if not query:
            self.notify("Enter a search query first.", severity="warning")
            return
        self._current_query = query
        self._page = 1
        self._run_search()

    @on(Input.Submitted, "#query-input")
    def on_query_submitted(self) -> None:
        self.action_run_search()

    @on(Button.Pressed, "#btn-clear-query")
    def clear_query(self) -> None:
        self.query_one("#query-input", Input).value = ""

    @on(Button.Pressed, "#btn-clear-history")
    def clear_history(self) -> None:
        self.storage.clear_history()
        self._refresh_history()
        self.notify("Search history cleared.", title="Cleared")

    @work(exclusive=True)
    async def _run_search(self) -> None:
        from textual.widgets import TabbedContent
        from shodan_tui.screens.results import ResultsPane

        status = self.query_one("#search-status", Static)
        status.update("⏳ Searching…")
        try:
            data = await self.api.search(
                self._current_query, page=self._page, facets="country:5,org:5,port:5"
            )
        except ShodanAPIError as e:
            self.notify(str(e), severity="error", title="API Error")
            status.update(f"[red]Error: {e}[/red]")
            return

        total = data.get("total", 0)
        status.update(
            f"[green]✓[/green] [bold]{total:,}[/bold] results — switching to Results tab…"
        )
        self.storage.add_history(self._current_query, total)
        self._refresh_history()

        # Load results, switch tab, then explicitly focus the results table.
        # Without the focus() call, Textual reverts the tab switch because the
        # Search button still holds focus after being clicked — Textual's
        # post-activation focus management reasserts the button's tab.
        self.app.query_one("#results-pane", ResultsPane).load_results(  # type: ignore
            self._current_query, data, self._page
        )
        self.app.query_one("#main-tabs", TabbedContent).active = "tab-results"  # type: ignore
        self.app.query_one("#results-table").focus()  # type: ignore

        self.post_message(self.SearchCompleted(self._current_query, data, self._page))

    def action_run_search(self) -> None:
        """Called by the F5 key binding."""
        query = self.query_one("#query-input", Input).value.strip()
        if not query:
            self.notify("Enter a search query first.", severity="warning")
            return
        self._current_query = query
        self._page = 1
        self._run_search()

    def action_blur_input(self) -> None:
        self.query_one("#query-input", Input).blur()

    # ── Count (free, no credits) ──────────────────────────────────────────────

    @on(Button.Pressed, "#btn-count")
    def on_count_pressed(self) -> None:
        query = self.query_one("#query-input", Input).value.strip()
        if not query:
            self.notify("Enter a search query first.", severity="warning")
            return
        self._run_count(query)

    @work(exclusive=True)
    async def _run_count(self, query: str) -> None:
        status = self.query_one("#search-status", Static)
        result_widget = self.query_one("#count-result", Static)
        result_widget.add_class("hidden")
        status.update("⏳ Counting…")
        try:
            data = await self.api.count(query, facets="country:5,org:5,port:5")
            total = data.get("total", 0)
            facets = data.get("facets", {})

            lines = [
                f"[bold green]{total:,}[/bold green] results  "
                f"[dim]·  no credits consumed[/dim]\n"
            ]

            for key, label in (("country", "Country"), ("org", "Org"), ("port", "Port")):
                items = facets.get(key, [])
                if not items:
                    continue
                row = "  ".join(
                    f"[cyan]{i['value']}[/cyan] [dim]{i['count']:,}[/dim]"
                    for i in items[:5]
                )
                lines.append(f"[bold]{label}:[/bold]  {row}")

            result_widget.update("\n".join(lines))
            result_widget.remove_class("hidden")
            status.update("")
        except ShodanAPIError as e:
            status.update(f"[red]Error: {e}[/red]")
