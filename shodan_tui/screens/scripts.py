"""
Scripts screen — browse, add, remove, and run OSINT scan scripts.
Scripts are Python files that extend ShodanScript and define a reusable query+workflow.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from textual import on, work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, ScrollableContainer, Vertical
from textual.widgets import Button, DataTable, Input, Label, ListItem, ListView, Static

from shodan_tui.api import ShodanAPIError
from shodan_tui.scripts.loader import ScriptLoader

if TYPE_CHECKING:
    from shodan_tui.scripts.base import ShodanScript


class ScriptsPane(Container):
    """Script manager — list, install, remove, and run scan scripts."""

    BINDINGS = [
        Binding("r", "refresh_scripts", "Refresh"),
    ]

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._scripts: list[type[ShodanScript]] = []
        self._selected_script: type[ShodanScript] | None = None
        self._param_inputs: dict[str, Input] = {}
        # Pagination / export state
        self._script_query: str = ""
        self._script_page: int = 1
        self._script_total: int = 0
        self._script_results: list[dict] = []

    @property
    def api(self):
        return self.app.api  # type: ignore[attr-defined]

    def compose(self) -> ComposeResult:
        with Horizontal(id="scripts-layout"):
            # Left: script list
            with Vertical(id="scripts-list-panel"):
                yield Label("AVAILABLE SCRIPTS", classes="section-label")
                yield ListView(id="scripts-list")
                # Stacked vertically so buttons never overflow the panel width
                with Vertical(id="scripts-list-actions"):
                    yield Button("Refresh [R]", id="btn-refresh-scripts", variant="default")
                    yield Button("+ Add Script", id="btn-add-script", variant="primary")

            # Right: script detail + run
            with ScrollableContainer(id="scripts-detail-panel"):
                yield Label("SCRIPT DETAILS", classes="section-label")
                yield Static("← Select a script to view details", id="script-detail")

                yield Label("PARAMETERS", classes="section-label", id="params-label")
                yield Container(id="params-container")

                with Horizontal(id="script-run-actions", classes="hidden"):
                    yield Button("▶ Run Script", id="btn-run-script", variant="primary")
                    yield Button("🗑 Remove", id="btn-remove-script", variant="error")

                yield Label("OUTPUT", classes="section-label", id="output-label")
                yield Static("", id="script-output")
                yield DataTable(id="script-results-table", cursor_type="row", zebra_stripes=True)

                # Pagination (hidden until first run)
                with Horizontal(id="script-nav", classes="hidden"):
                    yield Button("◀ Prev", id="btn-script-prev", variant="default")
                    yield Static("", id="script-page-label")
                    yield Button("Next ▶", id="btn-script-next", variant="default")

                # Export (hidden until first run)
                with Horizontal(id="script-export-btns", classes="hidden"):
                    yield Button("Export JSON", id="btn-script-json", variant="default")
                    yield Button("Export CSV",  id="btn-script-csv",  variant="default")

        # Add script form (hidden by default)
        with Container(id="add-script-form", classes="hidden"):
            yield Label("ADD SCRIPT", classes="section-label")
            yield Static(
                "Enter the full path to a .py file containing a ShodanScript subclass.",
                classes="help-text",
            )
            with Horizontal(classes="input-row"):
                yield Label("File Path:", classes="filter-label")
                yield Input(placeholder="C:\\path\\to\\my_script.py", id="script-path-input")
            with Horizontal(id="add-script-buttons"):
                yield Button("Install", id="btn-install-script", variant="primary")
                yield Button("Cancel", id="btn-cancel-add", variant="default")

    def on_mount(self) -> None:
        results_table = self.query_one("#script-results-table", DataTable)
        results_table.add_columns("IP", "Port", "Org", "Country", "Product", "Hostname")
        self.action_refresh_scripts()

    def action_refresh_scripts(self) -> None:
        loader = ScriptLoader(self.app.config.user_scripts_dir)  # type: ignore[attr-defined]
        self._scripts = loader.load_all()
        lv = self.query_one("#scripts-list", ListView)
        lv.clear()
        for script_cls in self._scripts:
            tag_str = " ".join(f"[{t}]" for t in script_cls.tags[:3])
            label = f"{script_cls.name}  [dim]{tag_str}[/dim]"
            lv.append(ListItem(Label(label), name=script_cls.name))

    @on(Button.Pressed, "#btn-refresh-scripts")
    def on_refresh_pressed(self) -> None:
        self.action_refresh_scripts()

    # ── Script selection ──────────────────────────────────────────────────────

    @on(ListView.Selected, "#scripts-list")
    def on_script_selected(self, event: ListView.Selected) -> None:
        name = event.item.name
        cls = next((s for s in self._scripts if s.name == name), None)
        if cls is None:
            return
        self._selected_script = cls
        self._load_script_detail(cls)

    @work
    async def _load_script_detail(self, cls: type[ShodanScript]) -> None:
        """Async worker — awaits container mutations to prevent DuplicateIds."""
        detail = self.query_one("#script-detail", Static)
        lines = [
            f"[bold]{cls.name}[/bold]  v{cls.version}  by [cyan]{cls.author}[/cyan]",
            "",
            cls.description,
            "",
            f"[dim]Query:[/dim]  {cls.query}",
            f"[dim]Tags:[/dim]   " + "  ".join(f"[cyan][{t}][/cyan]" for t in cls.tags),
        ]
        if cls.facets:
            lines.append(f"[dim]Facets:[/dim] {cls.facets}")
        detail.update("\n".join(lines))

        # Clear old parameter inputs BEFORE mounting new ones (must be awaited)
        params_container = self.query_one("#params-container", Container)
        await params_container.remove_children()
        self._param_inputs = {}

        if cls.params:
            for param_name, meta in cls.params.items():
                default = str(meta.get("default", ""))
                desc = meta.get("description", "")
                inp = Input(placeholder=desc or default, id=f"param-{param_name}", value=default)
                self._param_inputs[param_name] = inp
                row = Horizontal(classes="input-row")
                await params_container.mount(row)
                await row.mount(Label(f"{param_name}:", classes="filter-label"))
                await row.mount(inp)
        else:
            await params_container.mount(
                Static("[dim]No parameters — runs with default query.[/dim]")
            )

        self.query_one("#script-run-actions").remove_class("hidden")

    # ── Run script ────────────────────────────────────────────────────────────

    @on(Button.Pressed, "#btn-run-script")
    def run_script(self) -> None:
        if self._selected_script is None:
            return
        kwargs = {}
        for param_name, inp in self._param_inputs.items():
            val = inp.value.strip()
            if val:
                kwargs[param_name] = val
        self._do_run_script(self._selected_script, kwargs)

    @work
    async def _do_run_script(self, script_cls: type[ShodanScript], kwargs: dict) -> None:
        output = self.query_one("#script-output", Static)
        table = self.query_one("#script-results-table", DataTable)
        table.clear()
        # Reset pagination/export while loading
        self.query_one("#script-nav").add_class("hidden")
        self.query_one("#script-export-btns").add_class("hidden")

        instance = script_cls()
        query = instance.build_query(**kwargs)
        output.update(f"⏳ Running: [bold]{script_cls.name}[/bold]\nQuery: {query}")

        try:
            raw = await self.api.search(query, facets=script_cls.facets)
            results = await instance.process(self.api, raw)

            self._script_query = query
            self._script_page = 1
            self._script_total = results.get("total", 0)
            self._script_results = results.get("matches", [])
            max_page = max(1, (self._script_total + 99) // 100)

            summary = instance.format_summary(results)
            output.update(f"[green]✓[/green] {summary}\nQuery: {query}")

            for m in self._script_results:
                ip       = m.get("ip_str", "")
                port     = str(m.get("port", ""))
                org      = (m.get("org") or "")[:28]
                cc       = m.get("location", {}).get("country_code") or m.get("country_code", "")
                product  = (m.get("product") or "")[:22]
                hostname = (m.get("hostnames") or [""])[0][:30]
                # Use "ip:port" as key — prevents DuplicateKey when the same IP
                # has multiple open ports (common with webcams, databases, etc.)
                table.add_row(ip, port, org, cc, product, hostname, key=f"{ip}:{port}")

            # Show pagination controls
            self.query_one("#script-page-label", Static).update(
                f"  Page {self._script_page}/{max_page}  "
            )
            self.query_one("#btn-script-prev", Button).disabled = True
            self.query_one("#btn-script-next", Button).disabled = self._script_page >= max_page
            self.query_one("#script-nav").remove_class("hidden")
            self.query_one("#script-export-btns").remove_class("hidden")

        except ShodanAPIError as e:
            output.update(f"[red]Error: {e}[/red]")

    # ── Pagination ────────────────────────────────────────────────────────────

    @on(Button.Pressed, "#btn-script-prev")
    def script_prev_page(self) -> None:
        if self._script_page > 1:
            self._script_page -= 1
            self._fetch_script_page()

    @on(Button.Pressed, "#btn-script-next")
    def script_next_page(self) -> None:
        max_page = max(1, (self._script_total + 99) // 100)
        if self._script_page < max_page:
            self._script_page += 1
            self._fetch_script_page()

    @work(exclusive=True)
    async def _fetch_script_page(self) -> None:
        output = self.query_one("#script-output", Static)
        table = self.query_one("#script-results-table", DataTable)
        table.clear()
        output.update(f"⏳ Loading page {self._script_page}…")
        try:
            data = await self.api.search(self._script_query, page=self._script_page)
            self._script_total = data.get("total", 0)
            self._script_results = data.get("matches", [])
            max_page = max(1, (self._script_total + 99) // 100)

            for m in self._script_results:
                ip       = m.get("ip_str", "")
                port     = str(m.get("port", ""))
                org      = (m.get("org") or "")[:28]
                cc       = m.get("location", {}).get("country_code") or m.get("country_code", "")
                product  = (m.get("product") or "")[:22]
                hostname = (m.get("hostnames") or [""])[0][:30]
                table.add_row(ip, port, org, cc, product, hostname, key=f"{ip}:{port}")

            output.update(
                f"[green]✓[/green] Page {self._script_page}/{max_page}  ·  "
                f"[bold green]{self._script_total:,}[/bold green] total\n"
                f"Query: {self._script_query}"
            )
            self.query_one("#script-page-label", Static).update(
                f"  Page {self._script_page}/{max_page}  "
            )
            self.query_one("#btn-script-prev", Button).disabled = self._script_page <= 1
            self.query_one("#btn-script-next", Button).disabled = self._script_page >= max_page
        except ShodanAPIError as e:
            output.update(f"[red]Error: {e}[/red]")

    # ── Row selection → host detail ───────────────────────────────────────────

    @on(DataTable.RowSelected, "#script-results-table")
    def on_result_selected(self, event: DataTable.RowSelected) -> None:
        # Key is "ip:port" — split to get just the IP
        key = str(event.row_key.value)
        ip = key.split(":")[0]
        if ip:
            self.app.push_screen("host", {"ip": ip})  # type: ignore[attr-defined]

    # ── Export ────────────────────────────────────────────────────────────────

    @property
    def _exports_dir(self):
        return self.app.config.exports_dir  # type: ignore[attr-defined]

    @on(Button.Pressed, "#btn-script-json")
    def export_script_json(self) -> None:
        if not self._script_results:
            self.notify("No results to export.", severity="warning")
            return
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = self._exports_dir / f"script_results_p{self._script_page}_{ts}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "query": self._script_query,
                    "total": self._script_total,
                    "page": self._script_page,
                    "matches": self._script_results,
                },
                f, indent=2,
            )
        self.notify(f"Saved → {path}", title="Exported")

    @on(Button.Pressed, "#btn-script-csv")
    def export_script_csv(self) -> None:
        if not self._script_results:
            self.notify("No results to export.", severity="warning")
            return
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = self._exports_dir / f"script_results_p{self._script_page}_{ts}.csv"
        with open(path, "w", encoding="utf-8") as f:
            f.write("ip,port,org,country,product,hostname\n")
            for m in self._script_results:
                ip       = m.get("ip_str", "")
                port     = m.get("port", "")
                org      = (m.get("org") or "").replace(",", " ")
                cc       = m.get("location", {}).get("country_code") or m.get("country_code", "")
                product  = (m.get("product") or "").replace(",", " ")
                hostname = (m.get("hostnames") or [""])[0]
                f.write(f"{ip},{port},{org},{cc},{product},{hostname}\n")
        self.notify(f"Saved → {path}", title="Exported")

    # ── Add / Remove scripts ──────────────────────────────────────────────────

    @on(Button.Pressed, "#btn-add-script")
    def show_add_form(self) -> None:
        self.query_one("#add-script-form").remove_class("hidden")

    @on(Button.Pressed, "#btn-cancel-add")
    def hide_add_form(self) -> None:
        self.query_one("#add-script-form").add_class("hidden")

    @on(Button.Pressed, "#btn-install-script")
    def install_script(self) -> None:
        path_str = self.query_one("#script-path-input", Input).value.strip()
        if not path_str:
            return
        path = Path(path_str)
        loader = ScriptLoader(self.app.config.user_scripts_dir)  # type: ignore[attr-defined]
        if loader.install_script(path):
            self.notify(f"Script '{path.name}' installed.", title="Installed")
            self.query_one("#add-script-form").add_class("hidden")
            self.query_one("#script-path-input", Input).value = ""
            self.action_refresh_scripts()
        else:
            self.notify(f"Failed to install '{path.name}'. Check the path.", severity="error")

    @on(Button.Pressed, "#btn-remove-script")
    def remove_script(self) -> None:
        if self._selected_script is None:
            return
        loader = ScriptLoader(self.app.config.user_scripts_dir)  # type: ignore[attr-defined]
        cls = self._selected_script
        module = cls.__module__
        if "builtin" in module:
            self.notify("Built-in scripts cannot be removed.", severity="warning")
            return
        # Module names are "shodan_tui_scripts_user_<stem>" or "shodan_tui_scripts_local_<stem>".
        # Strip the known prefix to recover the full filename stem (which may contain underscores).
        stem: str | None = None
        for prefix in ("shodan_tui_scripts_user_", "shodan_tui_scripts_local_"):
            if module.startswith(prefix):
                stem = module[len(prefix):]
                break
        if not stem:
            self.notify("Could not determine script file to remove.", severity="error")
            return
        if loader.remove_script(stem):
            self.notify(f"Script '{cls.name}' removed.", title="Removed")
            self._selected_script = None
            self.query_one("#script-detail", Static).update("← Select a script to view details")
            self.query_one("#script-run-actions").add_class("hidden")
            self.action_refresh_scripts()
        else:
            self.notify("Could not find script file to remove.", severity="error")
