"""
Async Shodan API wrapper.
Covers: Search, Host Lookup, DNS, Scanning, Alerts, Exploits, Account.
"""

from __future__ import annotations

import httpx
from typing import Any


class ShodanAPIError(Exception):
    """Raised when the Shodan API returns a non-200 or network error."""
    pass


class ShodanAPI:
    BASE_URL = "https://api.shodan.io"
    EXPLOITS_URL = "https://exploits.shodan.io/api"

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key
        self._client: httpx.AsyncClient | None = None

    # ── Connection management ─────────────────────────────────────────────────

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=30.0, follow_redirects=True)
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    # ── Internal helpers ──────────────────────────────────────────────────────

    async def _get(self, path: str, params: dict[str, Any] | None = None, base_url: str | None = None) -> Any:
        url = (base_url or self.BASE_URL) + path
        params = {**(params or {}), "key": self.api_key}
        # Remove None values
        params = {k: v for k, v in params.items() if v is not None}
        try:
            response = await self.client.get(url, params=params)
            if response.status_code != 200:
                # Body may not be JSON on proxy/gateway errors (503, 502, etc.)
                try:
                    err_msg = response.json().get("error", f"HTTP {response.status_code}")
                except Exception:
                    err_msg = f"HTTP {response.status_code}"
                raise ShodanAPIError(err_msg)
            return response.json()
        except ShodanAPIError:
            raise
        except httpx.TimeoutException:
            raise ShodanAPIError("Request timed out — check your connection.")
        except httpx.RequestError as e:
            raise ShodanAPIError(f"Network error: {e}")

    async def _post(
        self,
        path: str,
        json_body: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        form_data: dict[str, Any] | None = None,
    ) -> Any:
        url = self.BASE_URL + path
        params = {**(params or {}), "key": self.api_key}
        try:
            if form_data is not None:
                # Some Shodan endpoints (e.g. /shodan/scan) require form-encoded bodies
                response = await self.client.post(url, data=form_data, params=params)
            else:
                response = await self.client.post(url, json=json_body or {}, params=params)
            if response.status_code != 200:
                try:
                    err_msg = response.json().get("error", f"HTTP {response.status_code}")
                except Exception:
                    err_msg = f"HTTP {response.status_code}"
                raise ShodanAPIError(err_msg)
            return response.json()
        except ShodanAPIError:
            raise
        except httpx.TimeoutException:
            raise ShodanAPIError("Request timed out.")
        except httpx.RequestError as e:
            raise ShodanAPIError(f"Network error: {e}")

    async def _delete(self, path: str) -> Any:
        url = self.BASE_URL + path
        params = {"key": self.api_key}
        try:
            response = await self.client.delete(url, params=params)
            if response.status_code == 200:
                try:
                    return response.json()
                except Exception:
                    return {"success": True}
            data = response.json()
            raise ShodanAPIError(data.get("error", f"HTTP {response.status_code}"))
        except httpx.TimeoutException:
            raise ShodanAPIError("Request timed out.")
        except httpx.RequestError as e:
            raise ShodanAPIError(f"Network error: {e}")

    # ── Search ────────────────────────────────────────────────────────────────

    async def search(
        self,
        query: str,
        page: int = 1,
        facets: str | None = None,
        minify: bool = True,
    ) -> dict:
        """Search Shodan. Returns matches + total. Consumes query credits."""
        params: dict[str, Any] = {"query": query, "page": page, "minify": str(minify).lower()}
        if facets:
            params["facets"] = facets
        return await self._get("/shodan/host/search", params)

    async def count(self, query: str, facets: str | None = None) -> dict:
        """Count results without consuming query credits."""
        params: dict[str, Any] = {"query": query}
        if facets:
            params["facets"] = facets
        return await self._get("/shodan/host/count", params)

    # TODO: use in a dynamic facets picker for the Results sidebar
    async def get_facets(self) -> dict:
        """List all available facets for search breakdowns."""
        return await self._get("/shodan/host/search/facets")

    # ── Host ──────────────────────────────────────────────────────────────────

    async def host(self, ip: str, history: bool = False, minify: bool = False) -> dict:
        """Return all services found on a given IP address."""
        params = {
            "history": str(history).lower(),
            "minify": str(minify).lower(),
        }
        return await self._get(f"/shodan/host/{ip}", params)

    # ── DNS ───────────────────────────────────────────────────────────────────

    async def dns_resolve(self, hostnames: list[str]) -> dict:
        """Forward DNS: hostname → IP."""
        return await self._get("/dns/resolve", {"hostnames": ",".join(hostnames)})

    async def dns_reverse(self, ips: list[str]) -> dict:
        """Reverse DNS: IP → hostname(s)."""
        return await self._get("/dns/reverse", {"ips": ",".join(ips)})

    async def dns_domain(
        self,
        domain: str,
        history: bool = False,
        dns_type: str | None = None,
        page: int = 1,
    ) -> dict:
        """Return DNS entries + subdomains for a domain. Uses 1 query credit."""
        params: dict[str, Any] = {"history": str(history).lower(), "page": page}
        if dns_type:
            params["type"] = dns_type
        return await self._get(f"/dns/domain/{domain}", params)

    # ── Scanning ──────────────────────────────────────────────────────────────

    # TODO: use in Scans tab when creating on-demand scans (protocol picker)
    async def get_protocols(self) -> dict:
        """List all protocols available for on-demand scanning."""
        return await self._get("/shodan/protocols")

    async def create_scan(self, ips: list[str]) -> dict:
        """Request an on-demand scan of IPs/netblocks. Uses scan credits.
        The /shodan/scan endpoint requires form-encoded data, not JSON.
        """
        return await self._post("/shodan/scan", form_data={"ips": ",".join(ips)})

    async def get_scans(self) -> dict:
        """List all on-demand scans."""
        return await self._get("/shodan/scans")

    async def get_scan(self, scan_id: str) -> dict:
        """Get status of a specific scan."""
        return await self._get(f"/shodan/scan/{scan_id}")

    # ── Network Alerts ────────────────────────────────────────────────────────

    async def get_alerts(self) -> list[dict]:
        """List all active network monitoring alerts."""
        return await self._get("/shodan/alert/info")

    async def create_alert(self, name: str, ips: list[str], expires: int = 0) -> dict:
        """Create a network monitoring alert for the given IPs/netblocks.
        The API requires filters.ip to be a JSON array, not a comma-joined string.
        """
        body: dict[str, Any] = {
            "name": name,
            "filters": {"ip": ips},
        }
        if expires:
            body["expires"] = expires
        return await self._post("/shodan/alert", json_body=body)

    async def delete_alert(self, alert_id: str) -> dict:
        """Delete a network monitoring alert."""
        return await self._delete(f"/shodan/alert/{alert_id}")

    # ── Exploits ──────────────────────────────────────────────────────────────

    async def search_exploits(self, query: str, page: int = 1) -> dict:
        """Search the Shodan Exploits database."""
        return await self._get(
            "/search",
            {"query": query, "page": page},
            base_url=self.EXPLOITS_URL,
        )

    # ── Account ───────────────────────────────────────────────────────────────

    async def get_profile(self) -> dict:
        """Return the current user's account information."""
        return await self._get("/account/profile")

    async def get_api_info(self) -> dict:
        """Return API plan information and remaining credits."""
        return await self._get("/api-info")

    async def my_ip(self) -> str:
        """Return the current client's public IP address."""
        result = await self._get("/tools/myip")
        return result if isinstance(result, str) else result.get("ip", "Unknown")
