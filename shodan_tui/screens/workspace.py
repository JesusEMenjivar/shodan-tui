"""
Workspace screen — manage saved OSINT targets, notes, and investigations.
All data is stored locally — nothing is sent to Shodan.
"""

from __future__ import annotations

from textual import on, work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Button, DataTable, Input, Label, Static, TextArea

from shodan_tui.api import ShodanAPIError


class WorkspacePane(Container):
    """Local workspace for managing saved OSINT targets and notes."""

    BINDINGS = [
        Binding("r", "refresh", "Refresh"),
        Binding("delete", "delete_target", "Delete"),
    ]

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._selected_ip: str | None = None

    @property
    def storage(self):
        return self.app.storage  # type: ignore[attr-defined]

    @property
    def api(self):
        return self.app.api  # type: ignore[attr-defined]

    def compose(self) -> ComposeResult:
        with Horizontal(id="workspace-layout"):
            # Left: target list + filters
            with Vertical(id="workspace-list-panel"):
                yield Label("SAVED TARGETS", classes="section-label")
                with Horizontal(classes="input-row"):
                    yield Input(placeholder="Filter by IP, label, or tag...", id="workspace-filter")
                yield DataTable(id="workspace-table", cursor_type="row", zebra_stripes=True)
                with Horizontal(id="workspace-list-actions"):
                    yield Button("Refresh [R]", id="btn-refresh-workspace", variant="default")
                    yield Button("Delete [Del]", id="btn-delete-target", variant="error")
                    yield Button("View Host", id="btn-view-host", variant="default")

            # Right: target detail / notes editor
            with Vertical(id="workspace-detail-panel"):
                yield Label("TARGET DETAIL", classes="section-label")
                yield Static("← Select a target", id="workspace-detail")

                yield Label("NOTES", classes="section-label")
                yield TextArea("", id="notes-editor", language=None)

                with Horizontal(classes="input-row"):
                    yield Label("Label:", classes="filter-label")
                    yield Input(placeholder="Short label", id="target-label-input")
                with Horizontal(classes="input-row"):
                    yield Label("Investigation:", classes="filter-label")
                    yield Input(placeholder="Default", id="target-investigation-input")
                yield Button("💾 Save Notes", id="btn-save-notes", variant="primary")

                yield Label("RE-SCAN", classes="section-label")
                yield Static("", id="rescan-panel")
                yield Button("Refresh Host Data", id="btn-rescan", variant="default")

    def on_mount(self) -> None:
        table = self.query_one("#workspace-table", DataTable)
        table.add_columns("IP", "Label", "Investigation", "Tags", "Saved")
        self._load_targets()

    def action_refresh(self) -> None:
        self._load_targets()

    def _load_targets(self, filter_text: str = "") -> None:
        table = self.query_one("#workspace-table", DataTable)
        table.clear()
        targets = self.storage.targets
        if filter_text:
            ft = filter_text.lower()
            targets = [
                t for t in targets
                if ft in t.ip or ft in t.label.lower() or any(ft in tag for tag in t.tags)
            ]
        for t in targets:
            tags_str = ", ".join(t.tags) if t.tags else ""
            saved = t.saved_at[:10] if t.saved_at else ""
            table.add_row(t.ip, t.label, t.investigation, tags_str, saved, key=t.ip)

    @on(Input.Changed, "#workspace-filter")
    def on_filter_changed(self, event: Input.Changed) -> None:
        self._load_targets(event.value)

    @on(Button.Pressed, "#btn-refresh-workspace")
    def on_refresh_pressed(self) -> None:
        self._load_targets()

    # ── Target selection ──────────────────────────────────────────────────────

    @on(DataTable.RowSelected, "#workspace-table")
    def on_target_selected(self, event: DataTable.RowSelected) -> None:
        ip = str(event.row_key.value)
        self._selected_ip = ip
        self._populate_detail(ip)

    def _populate_detail(self, ip: str) -> None:
        """Fill the right-hand panel with data for the given IP."""
        target = self.storage.get_target(ip)
        if target is None:
            return
        lines = [
            f"[bold]{target.ip}[/bold]",
            f"Label:         {target.label or '[dim]none[/dim]'}",
            f"Investigation: {target.investigation}",
            f"Tags:          {', '.join(target.tags) if target.tags else '[dim]none[/dim]'}",
            f"Saved:         {target.saved_at[:19]}",
        ]
        self.query_one("#workspace-detail", Static).update("\n".join(lines))
        self.query_one("#notes-editor", TextArea).load_text(target.notes or "")
        self.query_one("#target-label-input", Input).value = target.label
        self.query_one("#target-investigation-input", Input).value = target.investigation

    def _restore_cursor(self) -> None:
        """Re-highlight the previously selected row after a table rebuild."""
        if not self._selected_ip:
            return
        table = self.query_one("#workspace-table", DataTable)
        for row_idx, row_key in enumerate(table.rows):
            if str(row_key.value) == self._selected_ip:
                table.move_cursor(row=row_idx)
                break

    # ── Save notes ────────────────────────────────────────────────────────────

    @on(Button.Pressed, "#btn-save-notes")
    def save_notes(self) -> None:
        if not self._selected_ip:
            self.notify("Select a target first.", severity="warning")
            return
        notes = self.query_one("#notes-editor", TextArea).text
        label = self.query_one("#target-label-input", Input).value.strip()
        investigation = self.query_one("#target-investigation-input", Input).value.strip() or "Default"
        self.storage.save_target(self._selected_ip, label=label, notes=notes, investigation=investigation)
        self._load_targets()
        self._restore_cursor()
        self._populate_detail(self._selected_ip)
        self.notify("Notes saved.", title="Saved ✓")

    # ── Delete target ─────────────────────────────────────────────────────────

    @on(Button.Pressed, "#btn-delete-target")
    def action_delete_target(self) -> None:
        if not self._selected_ip:
            self.notify("Select a target to delete.", severity="warning")
            return
        ip = self._selected_ip
        if self.storage.remove_target(ip):
            self.notify(f"Removed {ip} from workspace.", title="Deleted")
            self._selected_ip = None
            self.query_one("#workspace-detail", Static).update("← Select a target")
            self.query_one("#notes-editor", TextArea).load_text("")
            self._load_targets()

    # ── View host detail ──────────────────────────────────────────────────────

    @on(Button.Pressed, "#btn-view-host")
    def view_host(self) -> None:
        if not self._selected_ip:
            self.notify("Select a target first.", severity="warning")
            return
        self.app.push_screen("host", {"ip": self._selected_ip})  # type: ignore[attr-defined]

    # ── Re-scan / refresh host ────────────────────────────────────────────────

    @on(Button.Pressed, "#btn-rescan")
    def rescan_host(self) -> None:
        if not self._selected_ip:
            return
        self._do_rescan(self._selected_ip)

    @work
    async def _do_rescan(self, ip: str) -> None:
        panel = self.query_one("#rescan-panel", Static)
        panel.update(f"⏳ Refreshing data for {ip}...")
        try:
            data = await self.api.host(ip)
            ports = data.get("ports", [])
            org = data.get("org", "")
            vuln_count = sum(len(svc.get("vulns", {})) for svc in data.get("data", []))
            panel.update(
                f"[green]✓ {ip}[/green]\n"
                f"Org:   {org}\n"
                f"Ports: {', '.join(str(p) for p in ports[:20])}\n"
                f"CVEs:  {'[red]' + str(vuln_count) + '[/red]' if vuln_count else '0'}"
            )
        except ShodanAPIError as e:
            panel.update(f"[red]Error: {e}[/red]")
