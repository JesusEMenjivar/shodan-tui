"""
ShodanTUI — main Textual application.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer, Header, Static, TabbedContent, TabPane

from shodan_tui.api import ShodanAPI
from shodan_tui.screens.account import AccountPane
from shodan_tui.screens.alerts import AlertsPane
from shodan_tui.screens.dns import DNSPane
from shodan_tui.screens.exploits import ExploitsPane
from shodan_tui.screens.results import ResultsPane
from shodan_tui.screens.scans import ScansPane
from shodan_tui.screens.scripts import ScriptsPane
from shodan_tui.screens.search import SearchPane
from shodan_tui.screens.workspace import WorkspacePane
from shodan_tui.storage import WorkspaceStorage

if TYPE_CHECKING:
    from shodan_tui.config import Config


HELP_TEXT = """\
[bold cyan]SHODAN TUI — Keyboard Reference[/bold cyan]

[bold]Global[/bold]
  1-9        Switch tabs (9 = Exploits)
  ?          This help
  Ctrl+Q     Quit

[bold]Search Tab[/bold]
  F5 / Enter Run search
  Build →    Assemble query from filter fields

[bold]Results Tab[/bold]
  Enter      Open host detail for selected row
  s          Save selected host to workspace
  ◀ / ▶     Previous / next page

[bold]Host Detail[/bold]
  Esc / q    Close
  s          Save host to workspace

[bold]DNS & Recon[/bold]
  F5         Run current lookup
  Enter      Open host detail (Org Footprint results)

[bold]Alerts[/bold]
  R          Refresh alert list

[bold]Scans[/bold]
  R          Refresh scan list

[bold]Scripts[/bold]
  R          Refresh script list
  ▶ Run      Execute selected script
  + Add      Install a new script from file path
  🗑 Remove  Remove a user-installed script

[bold]Workspace[/bold]
  Del        Delete selected target
  R          Refresh list

[bold]Exploits[/bold]
  F5 / Enter Search exploits database
  Export     Save results as JSON or CSV

"""


class ShodanTUI(App):
    """Shodan TUI — OSINT terminal interface for Shodan."""

    CSS_PATH = "app.tcss"
    TITLE = "Shodan TUI"
    SUB_TITLE = "OSINT Terminal Interface"

    BINDINGS = [
        Binding("1", "switch_tab('tab-search')",    "Search",    show=True),
        Binding("2", "switch_tab('tab-results')",   "Results",   show=True),
        Binding("3", "switch_tab('tab-dns')",        "DNS/Recon", show=True),
        Binding("4", "switch_tab('tab-alerts')",     "Alerts",    show=True),
        Binding("5", "switch_tab('tab-scans')",      "Scans",     show=True),
        Binding("6", "switch_tab('tab-scripts')",    "Scripts",   show=True),
        Binding("7", "switch_tab('tab-workspace')",  "Workspace", show=True),
        Binding("8", "switch_tab('tab-account')",    "Account",   show=True),
        Binding("9", "switch_tab('tab-exploits')",   "Exploits",  show=True),
        Binding("question_mark", "show_help", "Help",  show=True),
        Binding("ctrl+q",        "quit",      "Quit",  show=True),
    ]

    def __init__(self, config: "Config", **kwargs) -> None:
        super().__init__(**kwargs)
        self.config = config
        self.api = ShodanAPI(config.api_key)
        self.storage = WorkspaceStorage(config)
        self._credits_text: str = ""  # updated by startup worker and Account pane

    # ── Composition ───────────────────────────────────────────────────────────

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)

        with TabbedContent(id="main-tabs", initial="tab-search"):
            with TabPane("🔍 Search",     id="tab-search"):
                yield SearchPane(id="search-pane")
            with TabPane("📋 Results",    id="tab-results"):
                yield ResultsPane(id="results-pane")
            with TabPane("🌐 DNS & Recon", id="tab-dns"):
                yield DNSPane(id="dns-pane")
            with TabPane("🔔 Alerts",     id="tab-alerts"):
                yield AlertsPane(id="alerts-pane")
            with TabPane("📡 Scans",      id="tab-scans"):
                yield ScansPane(id="scans-pane")
            with TabPane("⚙ Scripts",    id="tab-scripts"):
                yield ScriptsPane(id="scripts-pane")
            with TabPane("📁 Workspace",  id="tab-workspace"):
                yield WorkspacePane(id="workspace-pane")
            with TabPane("👤 Account",    id="tab-account"):
                yield AccountPane(id="account-pane")
            with TabPane("💥 Exploits",   id="tab-exploits"):
                yield ExploitsPane(id="exploits-pane")

        yield Static("⏳ loading credits…", id="status-credits", classes="status-bar-extra")
        yield Footer()

    # ── Search → Results handoff ──────────────────────────────────────────────

    def on_search_pane_search_completed(self, event: SearchPane.SearchCompleted) -> None:
        """Show credits + last-query summary in the status bar after a search."""
        try:
            query_part = (
                f"[dim]{event.query[:35]}[/dim]  ·  "
                f"[green]{event.data.get('total', 0):,}[/green] results"
            )
            text = f"{self._credits_text}   {query_part}" if self._credits_text else query_part
            self.query_one("#status-credits", Static).update(text)
        except Exception:
            pass

    # ── Screen routing ────────────────────────────────────────────────────────

    def push_screen(self, screen, params=None):  # type: ignore[override]
        """Route push_screen calls with string identifiers."""
        if screen == "host":
            from shodan_tui.screens.host import HostDetailScreen
            ip = (params or {}).get("ip", "")
            super().push_screen(HostDetailScreen(ip=ip))
        else:
            super().push_screen(screen)

    # ── Tab switching ─────────────────────────────────────────────────────────

    def action_switch_tab(self, tab_id: str) -> None:
        try:
            self.query_one("#main-tabs", TabbedContent).active = tab_id
        except Exception:
            pass

    # ── Help overlay ──────────────────────────────────────────────────────────

    def action_show_help(self) -> None:
        from textual.screen import ModalScreen
        from textual.app import ComposeResult as CR
        from textual.widgets import Button
        from textual.containers import Container

        class _HelpModal(ModalScreen):
            BINDINGS = [Binding("escape,q,question_mark", "dismiss", "Close")]

            def compose(self) -> CR:
                with Container(id="help-modal"):
                    yield Static(HELP_TEXT, id="help-content")
                    yield Button("Close [Esc]", id="btn-help-close", variant="default")

            def on_button_pressed(self) -> None:
                self.dismiss()

        self.push_screen(_HelpModal())

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def on_mount(self) -> None:
        """Fetch API plan info on startup to populate the credits status bar."""
        self._fetch_startup_credits()

    @work
    async def _fetch_startup_credits(self) -> None:
        """Pull query/scan credit counts and display them in the status bar."""
        try:
            info = await self.api.get_api_info()
            qc = info.get("query_credits", 0)
            sc = info.get("scan_credits", 0)
            self._credits_text = f"Credits: [cyan]{qc}[/cyan] query / [cyan]{sc}[/cyan] scan"
            self.query_one("#status-credits", Static).update(self._credits_text)
        except Exception:
            self._credits_text = ""
            self.query_one("#status-credits", Static).update("")

    async def on_unmount(self) -> None:
        await self.api.close()
