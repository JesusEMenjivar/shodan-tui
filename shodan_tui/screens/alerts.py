"""
Alerts screen — create, view, and delete Shodan network monitoring alerts.
Alerts notify you when new services appear on monitored IPs/netblocks.
"""

from __future__ import annotations

from textual import on, work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Button, DataTable, Input, Label, Static

from shodan_tui.api import ShodanAPIError


class AlertsPane(Container):
    """Manage Shodan network monitoring alerts."""

    BINDINGS = [
        Binding("r", "refresh", "Refresh"),
        Binding("n", "new_alert", "New Alert"),
    ]

    def compose(self) -> ComposeResult:
        yield Label("NETWORK MONITORING ALERTS", classes="section-label")
        yield Static(
            "Alerts notify you when new services are detected on your monitored IPs/netblocks.",
            classes="help-text",
        )

        yield Label("CREATE NEW ALERT", classes="section-label")
        with Container(id="create-alert-form"):
            with Horizontal(classes="input-row"):
                yield Label("Name:", classes="filter-label")
                yield Input(placeholder="e.g. My Server Monitor", id="alert-name")
            with Horizontal(classes="input-row"):
                yield Label("IPs / CIDRs:", classes="filter-label")
                yield Input(placeholder="e.g. 192.168.1.0/24, 203.0.113.5", id="alert-ips")
            with Horizontal(classes="input-row"):
                yield Label("Expires (days):", classes="filter-label")
                yield Input(placeholder="0 = never", id="alert-expires", value="0")
            with Horizontal(id="alert-create-buttons"):
                yield Button("Create Alert", id="btn-create-alert", variant="primary")

        yield Label("ACTIVE ALERTS", classes="section-label")
        yield Static("", id="alerts-status")
        yield DataTable(id="alerts-table", cursor_type="row", zebra_stripes=True)
        with Horizontal(id="alerts-actions"):
            yield Button("Refresh [R]", id="btn-refresh-alerts", variant="default")
            yield Button("Delete Selected", id="btn-delete-alert", variant="error")

    def on_mount(self) -> None:
        table = self.query_one("#alerts-table", DataTable)
        table.add_columns("ID", "Name", "Networks", "Created", "Expires")
        self._load_alerts()

    @property
    def api(self):
        return self.app.api  # type: ignore[attr-defined]

    # ── Load alerts ───────────────────────────────────────────────────────────

    def action_refresh(self) -> None:
        self._load_alerts()

    @on(Button.Pressed, "#btn-refresh-alerts")
    def on_refresh_pressed(self) -> None:
        self._load_alerts()

    @work
    async def _load_alerts(self) -> None:
        status = self.query_one("#alerts-status", Static)
        table = self.query_one("#alerts-table", DataTable)
        table.clear()
        status.update("⏳ Loading alerts...")
        try:
            alerts = await self.api.get_alerts()
            if not isinstance(alerts, list):
                alerts = []
            for alert in alerts:
                alert_id = alert.get("id", "")
                name = alert.get("name", "")
                networks = ", ".join(alert.get("filters", {}).get("ip", []) or [])
                created = (alert.get("created") or "")[:10]
                expires = str(alert.get("expires", "never"))
                table.add_row(alert_id, name, networks[:40], created, expires, key=alert_id)
            status.update(f"[green]✓[/green] {len(alerts)} active alert(s).")
        except ShodanAPIError as e:
            status.update(f"[red]Error: {e}[/red]")

    # ── Create alert ──────────────────────────────────────────────────────────

    @on(Button.Pressed, "#btn-create-alert")
    def create_alert(self) -> None:
        name = self.query_one("#alert-name", Input).value.strip()
        ips_raw = self.query_one("#alert-ips", Input).value.strip()
        expires_raw = self.query_one("#alert-expires", Input).value.strip()

        if not name or not ips_raw:
            self.notify("Name and IPs are required.", severity="warning")
            return

        ips = [ip.strip() for ip in ips_raw.split(",") if ip.strip()]
        try:
            expires = int(expires_raw) if expires_raw else 0
        except ValueError:
            expires = 0

        self._do_create_alert(name, ips, expires)

    @work
    async def _do_create_alert(self, name: str, ips: list[str], expires: int) -> None:
        try:
            result = await self.api.create_alert(name, ips, expires)
            self.notify(f"Alert '{name}' created (ID: {result.get('id', '')}).", title="Alert Created")
            # Clear form
            self.query_one("#alert-name", Input).value = ""
            self.query_one("#alert-ips", Input).value = ""
            self._load_alerts()
        except ShodanAPIError as e:
            self.notify(str(e), severity="error", title="API Error")

    # ── Delete alert ──────────────────────────────────────────────────────────

    @on(Button.Pressed, "#btn-delete-alert")
    def delete_alert(self) -> None:
        table = self.query_one("#alerts-table", DataTable)
        if table.row_count == 0 or table.cursor_row < 0:
            self.notify("Select an alert to delete.", severity="warning")
            return
        row_key = table.coordinate_to_cell_key(table.cursor_coordinate).row_key
        alert_id = str(row_key.value)
        self._do_delete_alert(alert_id)

    @work
    async def _do_delete_alert(self, alert_id: str) -> None:
        try:
            await self.api.delete_alert(alert_id)
            self.notify(f"Alert {alert_id} deleted.", title="Deleted")
            self._load_alerts()
        except ShodanAPIError as e:
            self.notify(str(e), severity="error", title="API Error")
