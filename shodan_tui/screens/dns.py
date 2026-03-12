"""
DNS & Recon screen — forward/reverse DNS, domain enumeration, org footprint.
"""

from __future__ import annotations

import json
from datetime import datetime

from textual import on, work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Button, DataTable, Input, Label, Static, TabbedContent, TabPane

from shodan_tui.api import ShodanAPIError


class DNSPane(Container):
    """DNS recon tools: resolve, reverse, domain enum, org footprint."""

    BINDINGS = [
        Binding("f5", "run_lookup", "Run"),
        Binding("escape", "blur", "Blur"),
    ]

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        # Per-tab result state for export
        self._resolve_data: dict[str, str] = {}            # hostname → ip
        self._reverse_data: dict[str, list[str]] = {}      # ip → [hostnames]
        self._domain_data: dict = {}                        # {domain, subdomains, records}
        self._org_data: dict = {}                           # {org, total, matches}

    @property
    def api(self):
        return self.app.api  # type: ignore[attr-defined]

    @property
    def _exports_dir(self):
        return self.app.config.exports_dir  # type: ignore[attr-defined]

    def compose(self) -> ComposeResult:
        with TabbedContent(id="dns-tabs"):
            with TabPane("Resolve DNS", id="tab-resolve"):
                yield Label("Forward DNS Lookup — hostname → IP", classes="section-label")
                with Horizontal(classes="input-row"):
                    yield Input(placeholder="e.g. example.com, api.example.com", id="resolve-input")
                    yield Button("Resolve", id="btn-resolve", variant="primary")
                yield Static("", id="resolve-status")
                yield DataTable(id="resolve-table", zebra_stripes=True)
                with Horizontal(id="resolve-export-btns", classes="hidden dns-export-row"):
                    yield Button("Export JSON", id="btn-resolve-json", variant="default")
                    yield Button("Export CSV",  id="btn-resolve-csv",  variant="default")

            with TabPane("Reverse DNS", id="tab-reverse"):
                yield Label("Reverse DNS Lookup — IP → hostname", classes="section-label")
                with Horizontal(classes="input-row"):
                    yield Input(placeholder="e.g. 8.8.8.8, 1.1.1.1", id="reverse-input")
                    yield Button("Lookup", id="btn-reverse", variant="primary")
                yield Static("", id="reverse-status")
                yield DataTable(id="reverse-table", zebra_stripes=True)
                with Horizontal(id="reverse-export-btns", classes="hidden dns-export-row"):
                    yield Button("Export JSON", id="btn-reverse-json", variant="default")
                    yield Button("Export CSV",  id="btn-reverse-csv",  variant="default")

            with TabPane("Domain Enum", id="tab-domain"):
                yield Label("Domain Enumeration — subdomains & DNS records (uses 1 query credit)", classes="section-label")
                with Horizontal(classes="input-row"):
                    yield Input(placeholder="e.g. target.com", id="domain-input")
                    yield Button("Enumerate", id="btn-domain", variant="primary")
                yield Static("", id="domain-status")
                yield DataTable(id="domain-table", zebra_stripes=True)
                with Horizontal(id="domain-export-btns", classes="hidden dns-export-row"):
                    yield Button("Export JSON", id="btn-domain-json", variant="default")
                    yield Button("Export CSV",  id="btn-domain-csv",  variant="default")

            with TabPane("Org Footprint", id="tab-org"):
                yield Label("Organization Footprint — all IPs & netblocks associated with an org", classes="section-label")
                with Horizontal(classes="input-row"):
                    yield Input(placeholder='e.g. "Amazon" or "Tesla Inc"', id="org-input")
                    yield Button("Search", id="btn-org", variant="primary")
                yield Static("", id="org-status")
                yield DataTable(id="org-table", zebra_stripes=True)
                with Horizontal(id="org-export-btns", classes="hidden dns-export-row"):
                    yield Button("Export JSON", id="btn-org-json", variant="default")
                    yield Button("Export CSV",  id="btn-org-csv",  variant="default")

    def on_mount(self) -> None:
        self.query_one("#resolve-table", DataTable).add_columns("Hostname", "IP")
        self.query_one("#reverse-table", DataTable).add_columns("IP", "Hostname(s)")
        self.query_one("#domain-table",  DataTable).add_columns("Type", "Name / Value", "Last Seen")
        self.query_one("#org-table",     DataTable).add_columns("IP", "Port", "Product", "Country")

    # ── Resolve ───────────────────────────────────────────────────────────────

    @on(Button.Pressed, "#btn-resolve")
    def run_resolve(self) -> None:
        val = self.query_one("#resolve-input", Input).value.strip()
        if not val:
            return
        self._do_resolve([h.strip() for h in val.split(",") if h.strip()])

    @on(Input.Submitted, "#resolve-input")
    def on_resolve_submitted(self) -> None:
        self.run_resolve()

    @work
    async def _do_resolve(self, hostnames: list[str]) -> None:
        status = self.query_one("#resolve-status", Static)
        table  = self.query_one("#resolve-table", DataTable)
        table.clear()
        self.query_one("#resolve-export-btns").add_class("hidden")
        status.update("⏳ Resolving...")
        try:
            data = await self.api.dns_resolve(hostnames)
            self._resolve_data = {h: (ip or "") for h, ip in data.items()}
            for hostname, ip in data.items():
                table.add_row(hostname, ip or "[dim]NXDOMAIN[/dim]")
            status.update(f"[green]✓[/green] Resolved {len(data)} hostname(s).")
            if data:
                self.query_one("#resolve-export-btns").remove_class("hidden")
        except ShodanAPIError as e:
            status.update(f"[red]Error: {e}[/red]")

    # ── Reverse ───────────────────────────────────────────────────────────────

    @on(Button.Pressed, "#btn-reverse")
    def run_reverse(self) -> None:
        val = self.query_one("#reverse-input", Input).value.strip()
        if not val:
            return
        self._do_reverse([ip.strip() for ip in val.split(",") if ip.strip()])

    @on(Input.Submitted, "#reverse-input")
    def on_reverse_submitted(self) -> None:
        self.run_reverse()

    @work
    async def _do_reverse(self, ips: list[str]) -> None:
        status = self.query_one("#reverse-status", Static)
        table  = self.query_one("#reverse-table", DataTable)
        table.clear()
        self.query_one("#reverse-export-btns").add_class("hidden")
        status.update("⏳ Looking up...")
        try:
            data = await self.api.dns_reverse(ips)
            self._reverse_data = data
            for ip, hostnames in data.items():
                hn_str = ", ".join(hostnames) if hostnames else "[dim]No PTR record[/dim]"
                table.add_row(ip, hn_str)
            status.update(f"[green]✓[/green] Resolved {len(data)} IP(s).")
            if data:
                self.query_one("#reverse-export-btns").remove_class("hidden")
        except ShodanAPIError as e:
            status.update(f"[red]Error: {e}[/red]")

    # ── Domain Enum ───────────────────────────────────────────────────────────

    @on(Button.Pressed, "#btn-domain")
    def run_domain(self) -> None:
        domain = self.query_one("#domain-input", Input).value.strip()
        if not domain:
            return
        self._do_domain(domain)

    @on(Input.Submitted, "#domain-input")
    def on_domain_submitted(self) -> None:
        self.run_domain()

    @work
    async def _do_domain(self, domain: str) -> None:
        status = self.query_one("#domain-status", Static)
        table  = self.query_one("#domain-table", DataTable)
        table.clear()
        self.query_one("#domain-export-btns").add_class("hidden")
        status.update("⏳ Enumerating...")
        try:
            data = await self.api.dns_domain(domain)
            subdomains   = data.get("subdomains", [])
            dns_records  = data.get("data", [])
            self._domain_data = {
                "domain":     domain,
                "subdomains": subdomains,
                "records":    dns_records,
            }
            for sub in subdomains:
                table.add_row("SUBDOMAIN", f"{sub}.{domain}", "")
            for rec in dns_records:
                table.add_row(
                    rec.get("type", ""),
                    rec.get("value", ""),
                    rec.get("last_seen", "")[:10],
                )
            status.update(
                f"[green]✓[/green] Found {len(subdomains)} subdomains, "
                f"{len(dns_records)} DNS records."
            )
            if subdomains or dns_records:
                self.query_one("#domain-export-btns").remove_class("hidden")
        except ShodanAPIError as e:
            status.update(f"[red]Error: {e}[/red]")

    # ── Org Footprint ─────────────────────────────────────────────────────────

    @on(Button.Pressed, "#btn-org")
    def run_org(self) -> None:
        org = self.query_one("#org-input", Input).value.strip()
        if not org:
            return
        self._do_org(org)

    @on(Input.Submitted, "#org-input")
    def on_org_submitted(self) -> None:
        self.run_org()

    @work
    async def _do_org(self, org: str) -> None:
        status = self.query_one("#org-status", Static)
        table  = self.query_one("#org-table", DataTable)
        table.clear()
        self.query_one("#org-export-btns").add_class("hidden")
        status.update("⏳ Searching...")
        try:
            query   = f'org:"{org}"' if " " in org else f"org:{org}"
            data    = await self.api.search(query)
            matches = data.get("matches", [])
            total   = data.get("total", 0)
            self._org_data = {"org": org, "total": total, "matches": matches}
            for m in matches:
                ip      = m.get("ip_str", "")
                port    = str(m.get("port", ""))
                product = (m.get("product") or "")[:28]
                cc      = m.get("location", {}).get("country_code") or m.get("country_code", "")
                table.add_row(ip, port, product, cc, key=f"{ip}:{port}")
            status.update(
                f"[green]✓[/green] [bold]{total:,}[/bold] total hosts for org "
                f"[bold]{org}[/bold] (showing first page)."
            )
            if matches:
                self.query_one("#org-export-btns").remove_class("hidden")
        except ShodanAPIError as e:
            status.update(f"[red]Error: {e}[/red]")

    # ── Row click → host detail ───────────────────────────────────────────────

    @on(DataTable.RowSelected, "#org-table")
    def on_org_row_selected(self, event: DataTable.RowSelected) -> None:
        key = str(event.row_key.value)
        ip  = key.split(":")[0]
        if ip:
            self.app.push_screen("host", {"ip": ip})  # type: ignore[attr-defined]

    # ── Export helpers ────────────────────────────────────────────────────────

    def _ts(self) -> str:
        return datetime.now().strftime("%Y%m%d_%H%M%S")

    def _save(self, filename: str, content: str) -> None:
        path = self._exports_dir / filename
        path.write_text(content, encoding="utf-8")
        self.notify(f"Saved → {path}", title="Exported")

    # ── Resolve exports ───────────────────────────────────────────────────────

    @on(Button.Pressed, "#btn-resolve-json")
    def export_resolve_json(self) -> None:
        if not self._resolve_data:
            return
        self._save(
            f"dns_resolve_{self._ts()}.json",
            json.dumps(self._resolve_data, indent=2),
        )

    @on(Button.Pressed, "#btn-resolve-csv")
    def export_resolve_csv(self) -> None:
        if not self._resolve_data:
            return
        lines = ["hostname,ip"]
        for hostname, ip in self._resolve_data.items():
            lines.append(f"{hostname},{ip}")
        self._save(f"dns_resolve_{self._ts()}.csv", "\n".join(lines))

    # ── Reverse exports ───────────────────────────────────────────────────────

    @on(Button.Pressed, "#btn-reverse-json")
    def export_reverse_json(self) -> None:
        if not self._reverse_data:
            return
        self._save(
            f"dns_reverse_{self._ts()}.json",
            json.dumps(self._reverse_data, indent=2),
        )

    @on(Button.Pressed, "#btn-reverse-csv")
    def export_reverse_csv(self) -> None:
        if not self._reverse_data:
            return
        lines = ["ip,hostnames"]
        for ip, hostnames in self._reverse_data.items():
            hn = "; ".join(hostnames) if hostnames else ""
            lines.append(f"{ip},{hn}")
        self._save(f"dns_reverse_{self._ts()}.csv", "\n".join(lines))

    # ── Domain exports ────────────────────────────────────────────────────────

    @on(Button.Pressed, "#btn-domain-json")
    def export_domain_json(self) -> None:
        if not self._domain_data:
            return
        domain = self._domain_data.get("domain", "unknown")
        self._save(
            f"domain_enum_{domain}_{self._ts()}.json",
            json.dumps(self._domain_data, indent=2),
        )

    @on(Button.Pressed, "#btn-domain-csv")
    def export_domain_csv(self) -> None:
        if not self._domain_data:
            return
        domain = self._domain_data.get("domain", "unknown")
        lines  = ["type,name_value,last_seen"]
        for sub in self._domain_data.get("subdomains", []):
            lines.append(f"SUBDOMAIN,{sub}.{domain},")
        for rec in self._domain_data.get("records", []):
            lines.append(
                f"{rec.get('type', '')},"
                f"{rec.get('value', '')},"
                f"{rec.get('last_seen', '')[:10]}"
            )
        self._save(f"domain_enum_{domain}_{self._ts()}.csv", "\n".join(lines))

    # ── Org exports ───────────────────────────────────────────────────────────

    @on(Button.Pressed, "#btn-org-json")
    def export_org_json(self) -> None:
        if not self._org_data:
            return
        safe_org = self._org_data.get("org", "org").replace(" ", "_")
        self._save(
            f"org_footprint_{safe_org}_{self._ts()}.json",
            json.dumps(self._org_data, indent=2),
        )

    @on(Button.Pressed, "#btn-org-csv")
    def export_org_csv(self) -> None:
        if not self._org_data:
            return
        safe_org = self._org_data.get("org", "org").replace(" ", "_")
        lines    = ["ip,port,product,country"]
        for m in self._org_data.get("matches", []):
            ip      = m.get("ip_str", "")
            port    = m.get("port", "")
            product = (m.get("product") or "").replace(",", " ")
            cc      = m.get("location", {}).get("country_code") or m.get("country_code", "")
            lines.append(f"{ip},{port},{product},{cc}")
        self._save(f"org_footprint_{safe_org}_{self._ts()}.csv", "\n".join(lines))
