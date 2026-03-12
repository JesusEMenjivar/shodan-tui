"""
Account screen — API plan info, credit usage, and current public IP.
"""

from __future__ import annotations

from textual import on, work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Button, Label, Rule, Static

from shodan_tui.api import ShodanAPIError


class AccountPane(Container):
    """Shodan account info and API plan details."""

    BINDINGS = [
        Binding("r", "refresh", "Refresh"),
    ]

    def compose(self) -> ComposeResult:
        yield Label("ACCOUNT & API INFO", classes="section-label")

        with Horizontal(id="account-layout"):
            with Vertical(id="account-left"):
                yield Label("API PLAN", classes="section-label")
                yield Static("⏳ Loading...", id="plan-panel")

                yield Rule()
                yield Label("QUERY CREDITS", classes="section-label")
                yield Static("", id="credits-panel")

                yield Rule()
                yield Label("SCAN CREDITS", classes="section-label")
                yield Static("", id="scan-credits-panel")

            with Vertical(id="account-right"):
                yield Label("PROFILE", classes="section-label")
                yield Static("", id="profile-panel")

                yield Rule()
                yield Label("YOUR PUBLIC IP", classes="section-label")
                yield Static("", id="ip-panel")

        yield Rule()
        with Horizontal(id="account-actions"):
            yield Button("Refresh [R]", id="btn-refresh-account", variant="default")

    def on_mount(self) -> None:
        self._load_account()

    @property
    def api(self):
        return self.app.api  # type: ignore[attr-defined]

    def action_refresh(self) -> None:
        self._load_account()

    @on(Button.Pressed, "#btn-refresh-account")
    def on_refresh_pressed(self) -> None:
        self._load_account()

    @work
    async def _load_account(self) -> None:
        plan_panel = self.query_one("#plan-panel", Static)
        credits_panel = self.query_one("#credits-panel", Static)
        scan_panel = self.query_one("#scan-credits-panel", Static)
        profile_panel = self.query_one("#profile-panel", Static)
        ip_panel = self.query_one("#ip-panel", Static)

        # Load API info and profile concurrently
        import asyncio

        async def load_api_info():
            try:
                return await self.api.get_api_info()
            except ShodanAPIError as e:
                return {"error": str(e)}

        async def load_profile():
            try:
                return await self.api.get_profile()
            except ShodanAPIError as e:
                return {"error": str(e)}

        async def load_my_ip():
            try:
                return await self.api.my_ip()
            except ShodanAPIError:
                return "Unavailable"

        api_info, profile, my_ip = await asyncio.gather(
            load_api_info(), load_profile(), load_my_ip()
        )

        # ── API Plan ──────────────────────────────────────────────────────────
        if "error" in api_info:
            plan_panel.update(f"[red]{api_info['error']}[/red]")
        else:
            plan = api_info.get("plan", "Unknown")
            https = "✓" if api_info.get("https") else "✗"
            unlocked = "✓" if api_info.get("unlocked") else "✗"
            plan_panel.update(
                f"Plan:    [bold cyan]{plan}[/bold cyan]\n"
                f"HTTPS:   {https}\n"
                f"Unlocked: {unlocked}\n"
                f"Monitored IPs: {api_info.get('monitored_ips', 0)}"
            )

            # Query credits
            qc = api_info.get("query_credits", 0)
            color = "green" if qc > 50 else "yellow" if qc > 10 else "red"
            credits_panel.update(
                f"Remaining: [{color}]{qc}[/{color}]\n"
                f"[dim]1 credit consumed per search page (after the first).[/dim]"
            )

            # Scan credits
            sc = api_info.get("scan_credits", 0)
            sc_color = "green" if sc > 100 else "yellow" if sc > 10 else "red"
            scan_panel.update(
                f"Remaining: [{sc_color}]{sc}[/{sc_color}]\n"
                f"[dim]1 credit consumed per IP scanned on-demand.[/dim]"
            )

        # ── Profile ───────────────────────────────────────────────────────────
        if "error" in profile:
            profile_panel.update(f"[red]{profile['error']}[/red]")
        else:
            display = profile.get("display_name") or profile.get("username", "N/A")
            member = profile.get("member")
            email = (
                profile.get("email")
                or (member.get("email") if isinstance(member, dict) else None)
                or "N/A"
            )
            created = profile.get("created", "")[:10]
            profile_panel.update(
                f"Name:    [bold]{display}[/bold]\n"
                f"Email:   {email}\n"
                f"Created: {created}"
            )

        # ── My IP ─────────────────────────────────────────────────────────────
        ip_panel.update(f"[bold cyan]{my_ip}[/bold cyan]")
