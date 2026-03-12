"""
Scans screen — request and monitor on-demand Shodan scans.
Requires a paid API plan with scan credits.
"""

from __future__ import annotations

from textual import on, work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal
from textual.widgets import Button, DataTable, Input, Label, Static

from shodan_tui.api import ShodanAPIError


class ScansPane(Container):
    """On-demand scan management."""

    BINDINGS = [
        Binding("r", "refresh", "Refresh"),
    ]

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        # Track IPs submitted per scan in this session — the API history
        # endpoint does not return the original IP list.
        self._scan_ips: dict[str, list[str]] = {}
        self._selected_scan_id: str = ""

    def compose(self) -> ComposeResult:
        yield Label("ON-DEMAND SCANS", classes="section-label")
        yield Static(
            "Request Shodan to actively scan specific IPs or netblocks.\n"
            "[yellow]⚠ Requires a paid API plan — uses 1 scan credit per IP scanned.[/yellow]",
            classes="help-text",
        )

        yield Label("NEW SCAN", classes="section-label")
        with Container(id="scan-form"):
            with Horizontal(classes="input-row"):
                yield Label("IPs / CIDRs:", classes="filter-label")
                yield Input(
                    placeholder="e.g. 203.0.113.5, 198.51.100.0/24",
                    id="scan-ips",
                )
            with Horizontal(id="scan-buttons"):
                yield Button("Request Scan", id="btn-request-scan", variant="primary")
                yield Static("", id="scan-credit-note", classes="help-text")

        yield Label("SCAN HISTORY", classes="section-label")
        yield Static("", id="scans-status")
        yield DataTable(id="scans-table", cursor_type="row", zebra_stripes=True)
        with Horizontal(id="scans-actions"):
            yield Button("Refresh [R]", id="btn-refresh-scans", variant="default")
            yield Button("Check Status", id="btn-check-scan", variant="default")

        # ── Scan detail panel (revealed on row selection) ──────────────────
        with Container(id="scan-detail", classes="hidden"):
            yield Label("SCAN DETAIL", classes="section-label")
            yield Static("", id="scan-detail-info")
            with Horizontal(id="scan-detail-actions"):
                yield Button(
                    "▶ Open Host Detail",
                    id="btn-scan-open-host",
                    variant="primary",
                    classes="hidden",
                )

    def on_mount(self) -> None:
        table = self.query_one("#scans-table", DataTable)
        table.add_columns("Scan ID", "Status", "IPs Submitted", "Credits Used", "Created")
        self._load_scans()

    @property
    def api(self):
        return self.app.api  # type: ignore[attr-defined]

    # ── Load scans ────────────────────────────────────────────────────────────

    def action_refresh(self) -> None:
        self._load_scans()

    @on(Button.Pressed, "#btn-refresh-scans")
    def on_refresh_pressed(self) -> None:
        self._load_scans()

    @work
    async def _load_scans(self) -> None:
        status = self.query_one("#scans-status", Static)
        table = self.query_one("#scans-table", DataTable)
        table.clear()
        status.update("⏳ Loading scans...")
        try:
            data = await self.api.get_scans()
            matches = data.get("matches", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
            for scan in matches:
                scan_id      = scan.get("id", "")
                scan_status  = scan.get("status", "")
                count        = str(scan.get("count", ""))
                credits_left = str(scan.get("credits_left", ""))
                created      = (scan.get("created") or "")[:19]
                if scan_status == "DONE":
                    status_str = f"[green]{scan_status}[/green]"
                elif scan_status in ("PROCESSING", "SUBMITTING"):
                    status_str = f"[yellow]{scan_status}[/yellow]"
                else:
                    status_str = scan_status
                table.add_row(scan_id, status_str, count, credits_left, created, key=scan_id)
            status.update(f"[green]✓[/green] {len(matches)} scan(s) on record.")
        except ShodanAPIError as e:
            status.update(f"[red]Error: {e}[/red]")

    # ── Request scan ──────────────────────────────────────────────────────────

    @on(Button.Pressed, "#btn-request-scan")
    def request_scan(self) -> None:
        raw = self.query_one("#scan-ips", Input).value.strip()
        if not raw:
            self.notify("Enter at least one IP or CIDR.", severity="warning")
            return
        ips = [ip.strip() for ip in raw.split(",") if ip.strip()]
        self._do_scan(ips)

    @work
    async def _do_scan(self, ips: list[str]) -> None:
        try:
            result  = await self.api.create_scan(ips)
            scan_id = result.get("id", "")
            credits = result.get("credits_left", "")
            # Remember which IPs belong to this scan
            if scan_id:
                self._scan_ips[scan_id] = ips
            self.notify(
                f"Scan submitted (ID: {scan_id}) — {credits} scan credits remaining.",
                title="Scan Requested",
            )
            self.query_one("#scan-ips", Input).value = ""
            self._load_scans()
        except ShodanAPIError as e:
            self.notify(str(e), severity="error", title="API Error")

    # ── Row selection → detail panel ──────────────────────────────────────────

    @on(DataTable.RowSelected, "#scans-table")
    def on_scan_selected(self, event: DataTable.RowSelected) -> None:
        scan_id = str(event.row_key.value)
        self._selected_scan_id = scan_id
        ips = self._scan_ips.get(scan_id, [])

        lines = [f"[bold]Scan ID:[/bold]  {scan_id}"]

        open_btn = self.query_one("#btn-scan-open-host", Button)

        if ips:
            lines.append(f"[bold]IPs / CIDRs:[/bold]  {', '.join(ips)}")
            if len(ips) == 1 and "/" not in ips[0]:
                # Single concrete IP — enable direct host lookup
                lines.append(
                    "\n[green]✓ Scan complete.[/green] Click [bold]Open Host Detail[/bold] "
                    "to view discovered services for this IP."
                )
                open_btn.remove_class("hidden")
            else:
                # Multiple IPs or a CIDR block
                lines.append(
                    "\n[green]✓ Scan complete.[/green] Results are now indexed in Shodan.\n"
                    "Search for each IP in the [bold]Search[/bold] tab to view discovered services."
                )
                open_btn.add_class("hidden")
        else:
            lines.append(
                "[dim]IPs not available — this scan was submitted in a previous session.[/dim]\n\n"
                "Results are indexed in Shodan. To find them, search for the original IP(s)\n"
                "in the [bold]Search[/bold] tab (e.g. enter the IP directly as your query)."
            )
            open_btn.add_class("hidden")

        self.query_one("#scan-detail-info", Static).update("\n".join(lines))
        self.query_one("#scan-detail").remove_class("hidden")

    @on(Button.Pressed, "#btn-scan-open-host")
    def open_scan_host(self) -> None:
        ips = self._scan_ips.get(self._selected_scan_id, [])
        if ips and len(ips) == 1:
            self.app.push_screen("host", {"ip": ips[0]})  # type: ignore[attr-defined]

    # ── Check scan status ─────────────────────────────────────────────────────

    @on(Button.Pressed, "#btn-check-scan")
    def check_scan_status(self) -> None:
        table = self.query_one("#scans-table", DataTable)
        if table.row_count == 0 or table.cursor_row < 0:
            self.notify("Select a scan from the table first.", severity="warning")
            return
        row_key = table.coordinate_to_cell_key(table.cursor_coordinate).row_key
        scan_id = str(row_key.value)
        self._do_check_scan(scan_id)

    @work
    async def _do_check_scan(self, scan_id: str) -> None:
        try:
            result      = await self.api.get_scan(scan_id)
            scan_status = result.get("status", "UNKNOWN")
            count       = result.get("count", 0)
            self.notify(
                f"Scan {scan_id}: {scan_status} ({count} IPs)",
                title="Scan Status",
            )
            self._load_scans()
        except ShodanAPIError as e:
            self.notify(str(e), severity="error", title="API Error")
