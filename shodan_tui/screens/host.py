"""
Host Detail Screen — full information panel for a single IP address.
Pushed as a modal overlay from the Search, DNS, or Workspace screens.
"""

from __future__ import annotations

from textual import on, work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, ScrollableContainer, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, DataTable, Label, Pretty, Rule, Static

from shodan_tui.api import ShodanAPIError


class HostDetailScreen(ModalScreen):
    """Modal screen showing full host details."""

    BINDINGS = [
        Binding("escape,q", "dismiss", "Close"),
        Binding("s", "save_target", "Save Target"),
        Binding("n", "add_note", "Note"),
    ]

    def __init__(self, ip: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self._ip = ip
        self._host_data: dict | None = None

    @property
    def api(self):
        return self.app.api  # type: ignore[attr-defined]

    @property
    def storage(self):
        return self.app.storage  # type: ignore[attr-defined]

    def compose(self) -> ComposeResult:
        with Container(id="host-modal"):
            with Horizontal(id="host-header"):
                yield Label(f"HOST  {self._ip}", id="host-title")
                yield Button("✕ Close [Esc]", id="btn-close", variant="default")
                yield Button("★ Save", id="btn-save", variant="primary")

            yield Static("⏳ Loading...", id="host-status")

            with ScrollableContainer(id="host-body"):
                # Identity section
                yield Label("IDENTITY", classes="section-label")
                with Horizontal(classes="detail-row-group"):
                    with Vertical(classes="detail-col"):
                        yield Static("", id="identity-panel")
                    with Vertical(classes="detail-col"):
                        yield Static("", id="location-panel")

                yield Rule()
                yield Label("OPEN PORTS & SERVICES", classes="section-label")
                yield DataTable(id="ports-table", cursor_type="row", zebra_stripes=True)

                yield Rule()
                yield Label("HOSTNAMES & DOMAINS", classes="section-label")
                yield Static("", id="hostnames-panel")

                yield Rule()
                yield Label("VULNERABILITIES", classes="section-label")
                yield DataTable(id="vulns-table", cursor_type="row", zebra_stripes=True)

                yield Rule()
                yield Label("TAGS", classes="section-label")
                yield Static("", id="tags-panel")

                yield Rule()
                yield Label("RAW BANNERS", classes="section-label")
                yield Static("", id="banners-panel")

    def on_mount(self) -> None:
        self._setup_tables()
        self._load_host()

    def _setup_tables(self) -> None:
        ports = self.query_one("#ports-table", DataTable)
        ports.add_columns("Port", "Proto", "Product", "Version", "SSL", "CPE")

        vulns = self.query_one("#vulns-table", DataTable)
        vulns.add_columns("CVE", "CVSS", "Summary")

    @work
    async def _load_host(self) -> None:
        status = self.query_one("#host-status", Static)
        try:
            data = await self.api.host(self._ip)
            self._host_data = data
            status.update("")
            self._render_host(data)
        except ShodanAPIError as e:
            status.update(f"[red]Error: {e}[/red]")

    def _render_host(self, d: dict) -> None:
        # ── Identity ──────────────────────────────────────────────────────────
        identity_lines = []
        if d.get("asn"):
            identity_lines.append(f"ASN:   [cyan]{d['asn']}[/cyan]")
        if d.get("org"):
            identity_lines.append(f"Org:   [bold]{d['org']}[/bold]")
        if d.get("isp"):
            identity_lines.append(f"ISP:   {d['isp']}")
        self.query_one("#identity-panel", Static).update("\n".join(identity_lines))

        loc = d.get("location", {})
        location_lines = []
        if loc.get("country_name"):
            location_lines.append(f"Country: [bold]{loc['country_name']}[/bold] ({loc.get('country_code', '')})")
        if loc.get("city"):
            location_lines.append(f"City:    {loc['city']}")
        if loc.get("region_code"):
            location_lines.append(f"Region:  {loc['region_code']}")
        if loc.get("latitude"):
            location_lines.append(f"Coords:  {loc['latitude']:.4f}, {loc['longitude']:.4f}")
        self.query_one("#location-panel", Static).update("\n".join(location_lines))

        # ── Ports & Services ─────────────────────────────────────────────────
        ports_table = self.query_one("#ports-table", DataTable)
        services = d.get("data", [])
        if services:
            for svc in services:
                port = str(svc.get("port", ""))
                proto = svc.get("transport", "tcp")
                product = (svc.get("product") or "")[:28]
                version = (svc.get("version") or "")[:16]
                has_ssl = "✓" if "ssl" in svc else ""
                cpe = (svc.get("cpe") or [""])[0][:30] if svc.get("cpe") else ""
                ports_table.add_row(port, proto, product, version, has_ssl, cpe)
        else:
            ports_table.display = False
            self.query_one("#host-body").mount(
                Static("[dim]No service data currently indexed for this host.[/dim]")
            )

        # ── Hostnames & Domains ───────────────────────────────────────────────
        hostnames = d.get("hostnames", [])
        domains = d.get("domains", [])
        hn_lines = []
        if hostnames:
            hn_lines.append("[bold]Hostnames:[/bold]")
            hn_lines.extend(f"  {h}" for h in hostnames)
        if domains:
            hn_lines.append("[bold]Domains:[/bold]")
            hn_lines.extend(f"  {dom}" for dom in domains)
        self.query_one("#hostnames-panel", Static).update(
            "\n".join(hn_lines) if hn_lines else "[dim]None recorded[/dim]"
        )

        # ── Vulnerabilities ───────────────────────────────────────────────────
        vulns_table = self.query_one("#vulns-table", DataTable)
        all_vulns: dict = {}
        for svc in d.get("data", []):
            all_vulns.update(svc.get("vulns", {}))
        if not all_vulns and d.get("vulns"):
            all_vulns = d["vulns"]

        if all_vulns:
            for cve, info in sorted(all_vulns.items()):
                cvss = str(info.get("cvss", ""))
                summary = (info.get("summary") or "")[:60]
                severity_color = "red" if float(cvss or 0) >= 7.0 else "yellow"
                vulns_table.add_row(
                    f"[{severity_color}]{cve}[/{severity_color}]",
                    f"[{severity_color}]{cvss}[/{severity_color}]",
                    summary,
                )
        else:
            vulns_table.display = False

        # ── Tags ──────────────────────────────────────────────────────────────
        tags = d.get("tags", [])
        self.query_one("#tags-panel", Static).update(
            "  ".join(f"[cyan][{t}][/cyan]" for t in tags) if tags else "[dim]No tags[/dim]"
        )

        # ── Banners ───────────────────────────────────────────────────────────
        banner_parts = []
        for svc in d.get("data", []):
            port = svc.get("port", "")
            raw = (svc.get("data") or "").strip()[:500]
            if raw:
                banner_parts.append(f"[bold cyan]── Port {port} ──[/bold cyan]\n{raw}")
        self.query_one("#banners-panel", Static).update(
            "\n\n".join(banner_parts) if banner_parts else "[dim]No banners[/dim]"
        )

    # ── Actions ───────────────────────────────────────────────────────────────

    @on(Button.Pressed, "#btn-close")
    def action_dismiss(self) -> None:
        self.dismiss()

    @on(Button.Pressed, "#btn-save")
    def action_save_target(self) -> None:
        label = (self._host_data.get("org", "") if self._host_data else "") or None
        self.storage.save_target(self._ip, label=label)
        self.notify(f"Saved {self._ip} to workspace.", title="Saved ★")
        self.query_one("#btn-save", Button).label = "★ Saved"

    def action_add_note(self) -> None:
        self.notify("Use the Workspace tab to add notes to saved targets.", severity="information")
