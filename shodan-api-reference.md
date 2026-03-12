# Shodan REST API Reference

---

## Overview

The Shodan REST API allows programmatic access to the Shodan search engine, scanning infrastructure, network alerts, DNS lookups, and account management. Results are returned as JSON.

---

## Base URL

```
https://api.shodan.io
```

---

## Authentication

All requests require an API key passed as a query parameter:

```
?key=YOUR_API_KEY
```

The API key is appended to every request URL. There is no header-based authentication method described in the provided documentation.

---

## Credit System

Two types of credits apply:

| Credit Type | Description |
|---|---|
| **Query credits** | Consumed by filtered searches and pagination past page 1 of `/shodan/host/search`. |
| **Scan credits** | Consumed by on-demand scans via `POST /shodan/scan`. 1 IP = 1 scan credit. |

A paid API plan is required to use on-demand scanning (`POST /shodan/scan`).

---

## Error Handling

A non-200 HTTP status code indicates an error. The response body contains a JSON object with an `error` field:

```json
{
    "error": "Invalid IP"
}
```

No specific error codes or exhaustive list of error conditions are specified in the provided documentation.

---

## Rate Limits

Not specified in the provided documentation.

---

## Endpoints

---

### Search Methods

---

#### `GET /shodan/host/{ip}`

**Host Information**

Returns all services that have been found on the given host IP.

**Parameters**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `ip` | String | Yes | Host IP address (path parameter) |
| `history` | Boolean | No | If `true`, return all historical banners (default: `false`) |
| `minify` | Boolean | No | If `true`, return only the list of ports and general host information, no banners (default: `false`) |

**Example Request**

```bash
curl -X GET "https://api.shodan.io/shodan/host/8.8.8.8?key=YOUR_API_KEY"
```

**Example Response**

```json
{
    "region_code": null,
    "ip": 134744072,
    "postal_code": null,
    "country_code": "US",
    "city": null,
    "dma_code": null,
    "last_update": "2021-01-22T08:49:35.190817",
    "latitude": 37.751,
    "tags": [],
    "area_code": null,
    "country_name": "United States",
    "hostnames": ["dns.google"],
    "org": "Google",
    "data": [
        {
            "_shodan": {
                "id": "cea5795b-55fd-4595-b9e5-ad5ca847cb4b",
                "options": {},
                "ptr": true,
                "module": "dns-udp",
                "crawler": "ac284849be0745621b3c518f74c14cf43cafbf08"
            },
            "hash": -553166942,
            "os": null,
            "ip": 134744072,
            "isp": "Google",
            "port": 53,
            "hostnames": ["dns.google"],
            "location": {
                "city": null,
                "region_code": null,
                "area_code": null,
                "longitude": -97.822,
                "country_code3": null,
                "country_name": "United States",
                "postal_code": null,
                "dma_code": null,
                "country_code": "US",
                "latitude": 37.751
            },
            "timestamp": "2021-01-22T08:49:35.190817",
            "domains": ["dns.google"],
            "org": "Google",
            "data": "\nRecursion: enabled",
            "asn": "AS15169",
            "transport": "udp",
            "ip_str": "8.8.8.8"
        }
    ],
    "asn": "AS15169",
    "isp": "Google",
    "longitude": -97.822,
    "country_code3": null,
    "domains": ["dns.google"],
    "ip_str": "8.8.8.8",
    "os": null,
    "ports": [53]
}
```

---

#### `GET /shodan/host/count`

**Search Shodan Without Results**

Identical to `/shodan/host/search` but returns only the total result count and facet information — no host matches. **Does not consume query credits.**

**Parameters**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `query` | String | Yes | Shodan search query (e.g., `apache country:DE`) |
| `facets` | String | No | Comma-separated list of properties for summary info. Format: `property` or `property:count` (e.g., `country:100`) |

**Example Request**

```bash
curl -X GET "https://api.shodan.io/shodan/host/count?key=YOUR_API_KEY&query=port:22&facets=org,os"
```

**Example Response**

```json
{
    "matches": [],
    "facets": {
        "org": [
            {"count": 3012386, "value": "Amazon.com"},
            {"count": 1322102, "value": "Google Cloud"}
        ],
        "os": [
            {"count": 601923, "value": "Ubuntu"},
            {"count": 227851, "value": "Debian"}
        ]
    },
    "total": 19590274
}
```

---

#### `GET /shodan/host/search`

**Search Shodan**

Search Shodan using the same query syntax as the website. Supports facets for summary breakdowns.

**Credit Usage**

1 query credit is deducted if:
- The search query contains a filter.
- Results past page 1 are accessed (1 credit per 100 additional results).

**Parameters**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `query` | String | Yes | Shodan search query (e.g., `apache country:DE`) |
| `facets` | String | No | Comma-separated list of properties for summary info. Format: `property` or `property:count` |
| `page` | Integer | No | Page number, 100 results per page (default: `1`) |
| `minify` | Boolean | No | Whether to truncate larger fields (default: `true`) |
| `fields` | String | No | Comma-separated list of fields to return (e.g., `tags,http.title,http.favicon.hash`) |

**Example Request**

```bash
curl -X GET "https://api.shodan.io/shodan/host/search?key=YOUR_API_KEY&query=product:nginx&facets=country"
```

**Example Response**

```json
{
    "matches": [
        {
            "product": "nginx",
            "hash": -1609083510,
            "ip": 1616761883,
            "org": "Comcast Business",
            "isp": "Comcast Business",
            "transport": "tcp",
            "cpe": ["cpe:/a:igor_sysoev:nginx"],
            "data": "HTTP/1.1 400 Bad Request\r\nServer: nginx\r\n...",
            "asn": "AS7922",
            "port": 443,
            "hostnames": ["three.webapplify.net"],
            "location": {
                "city": "Denver",
                "region_code": "CO",
                "longitude": -104.9078,
                "latitude": 39.7301,
                "country_code": "US",
                "country_name": "United States"
            },
            "timestamp": "2021-01-25T21:33:49.154513",
            "ip_str": "96.93.212.27"
        }
    ],
    "facets": {
        "country": [
            {"count": 7883733, "value": "US"},
            {"count": 2964965, "value": "CN"}
        ]
    },
    "total": 23047224
}
```

> **Note:** The response may also include a `_scroll_id` field for cursor-based pagination in certain plan tiers.

---

#### `GET /shodan/host/search/facets`

**List All Search Facets**

Returns a list of facet names that can be used to get a breakdown of top values for a property.

**Parameters**

None beyond authentication.

**Example Request**

```bash
curl -X GET "https://api.shodan.io/shodan/host/search/facets?key=YOUR_API_KEY"
```

**Example Response**

```json
["asn", "bitcoin.ip", "bitcoin.ip_count", "..."]
```

---

#### `GET /shodan/host/search/filters`

**List All Search Filters**

Returns a list of search filter names that can be used in a search query.

**Parameters**

None beyond authentication.

**Example Request**

```bash
curl -X GET "https://api.shodan.io/shodan/host/search/filters?key=YOUR_API_KEY"
```

**Example Response**

```json
["all", "asn", "bitcoin.ip", "bitcoin.ip_count", "..."]
```

---

#### `GET /shodan/host/search/tokens`

**Break Search Query Into Tokens**

Parses a search query string and returns which filters are being used and what parameters were provided to each filter.

**Parameters**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `query` | String | Yes | Shodan search query to parse |

**Example Request**

```bash
curl -X GET "https://api.shodan.io/shodan/host/search/tokens?key=YOUR_API_KEY&query=Raspbian port:22"
```

**Example Response**

```json
{
    "attributes": {
        "ports": [22]
    },
    "errors": [],
    "string": "Raspbian",
    "filters": ["port"]
}
```

---

### On-Demand Scanning

---

#### `GET /shodan/ports`

**List Ports Crawled by Shodan**

Returns a list of port numbers that Shodan's crawlers are currently scanning on the Internet.

**Parameters**

None beyond authentication.

**Example Request**

```bash
curl -X GET "https://api.shodan.io/shodan/ports?key=YOUR_API_KEY"
```

**Example Response**

```json
[7, 11, 13, 15, "..."]
```

---

#### `GET /shodan/protocols`

**List Supported Protocols**

Returns an object containing all protocols that can be used when launching an on-demand Internet scan.

**Parameters**

None beyond authentication.

**Example Request**

```bash
curl -X GET "https://api.shodan.io/shodan/protocols?key=YOUR_API_KEY"
```

**Example Response**

```json
{
    "afp": "AFP server information grabbing module",
    "ajp": "Check whether the Tomcat server running AJP protocol",
    "amqp": "Grab information from an AMQP service"
}
```

---

#### `POST /shodan/scan`

**Request Shodan to Crawl an IP / Netblock**

Submits a scan request for specific IPs or netblocks.

**Requirements:** Paid API plan required. 1 IP = 1 scan credit.

**Request Body (form-encoded)**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `ips` | String | Yes | Comma-separated list of IPs or CIDR netblocks, OR a JSON-encoded object mapping IPs to service lists |
| `service` | Array | No | List of `[port, protocol]` pairs to restrict the scan to specific services |

**JSON body format (for specifying services):**

```json
{
    "ips": {
        "1.1.1.1": [
            [53, "dns-udp"],
            [443, "https"]
        ]
    }
}
```

**Example Request (all services)**

```bash
curl -X POST "https://api.shodan.io/shodan/scan?key=YOUR_API_KEY" -d 'ips=8.8.8.8,1.1.1.1'
```

**Example Request (specific services)**

```bash
curl -X POST "https://api.shodan.io/shodan/scan?key=YOUR_API_KEY" -d 'ips={"1.1.1.1": [[53, "dns-udp"], [443, "https"]]}'
```

**Example Response**

```json
{
    "count": 2,
    "id": "vwWO7P5N1rWF5jbh",
    "credits_left": 100000
}
```

---

#### `POST /shodan/scan/internet`

**Crawl the Entire Internet for a Specific Port and Protocol**

Submits a scan request for a given port across the entire Internet.

**Requirements:** Restricted to security researchers and companies with a Shodan Enterprise Data license. Contact `jmath@shodan.io` to request access.

**Request Body (form-encoded)**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `port` | Integer | Yes | The port number to crawl |
| `protocol` | String | Yes | Protocol name (see `GET /shodan/protocols` for valid values) |

**Example Request**

```bash
curl -X POST "https://api.shodan.io/shodan/scan/internet?key=YOUR_API_KEY" -d 'port=80' -d 'protocol=http'
```

**Example Response**

```json
{
    "id": "TcjcsMfPcw4o7O84"
}
```

---

#### `GET /shodan/scans`

**Get List of All Created Scans**

Returns a listing of all on-demand scans that are currently active on the account.

**Parameters**

None beyond authentication.

**Example Request**

```bash
curl -X GET "https://api.shodan.io/shodan/scans?key=YOUR_API_KEY"
```

**Example Response**

```json
{
    "matches": [
        {
            "status": "PROCESSING",
            "created": "2021-01-26T08:17:43.794000",
            "status_check": "2021-01-26T08:17:43.900000",
            "credits_left": 100000,
            "api_key": "REDACTED",
            "id": "Mo8W7itcWumiy9Ay",
            "size": 1
        },
        {
            "status": "DONE",
            "created": "2021-01-26T08:08:26.296000",
            "status_check": "2021-01-26T08:09:39.636000",
            "credits_left": 100000,
            "api_key": "REDACTED",
            "id": "04GjMnUkQx9HsFhA",
            "size": 1
        }
    ],
    "total": 19
}
```

---

#### `GET /shodan/scan/{id}`

**Get the Status of a Scan Request**

Checks the progress of a previously submitted scan.

**Possible status values:** `SUBMITTING`, `QUEUE`, `PROCESSING`, `DONE`

**Parameters**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `id` | String | Yes | Scan ID returned by `POST /shodan/scan` (path parameter) |

**Example Request**

```bash
curl -X GET "https://api.shodan.io/shodan/scan/Mo8W7itcWumiy9Ay?key=YOUR_API_KEY"
```

**Example Response**

```json
{
    "count": 1,
    "status": "DONE",
    "id": "Mo8W7itcWumiy9Ay",
    "created": "2021-01-26T08:17:43.794000"
}
```

---

### Network Alerts

---

#### `POST /shodan/alert`

**Create an Alert to Monitor a Network Range**

Creates a network alert for a defined IP or netblock to subscribe to changes and events discovered within that range.

**Request Body (JSON)**

```json
{
    "name": "Alert Name",
    "filters": {
        "ip": ["8.8.8.8", "1.1.1.1"]
    },
    "expires": 0
}
```

| Parameter | Type | Required | Description |
|---|---|---|---|
| `name` | String | Yes | Descriptive name for the alert |
| `filters` | Object | Yes | Object defining trigger criteria. Only `ip` is currently supported |
| `filters.ip` | String | Yes | List of IPs or CIDR network ranges |
| `expires` | Integer | No | Number of seconds the alert should remain active (`0` = no expiry) |

**Example Request**

```bash
curl -X POST "https://api.shodan.io/shodan/alert?key=YOUR_API_KEY" \
  -H 'Content-Type: application/json' \
  -d '{"name": "DNS Alert", "filters": {"ip": ["8.8.8.8", "1.1.1.1"]}, "expires": 0}'
```

**Example Response**

```json
{
    "name": "DNS Alert",
    "created": "2021-01-27T03:44:22.989575",
    "triggers": {},
    "has_triggers": false,
    "expires": 0,
    "expiration": null,
    "filters": {
        "ip": ["8.8.8.8", "1.1.1.1"]
    },
    "id": "OYPRB8IR9Z35AZPR",
    "size": 2
}
```

---

#### `GET /shodan/alert/{id}/info`

**Get the Details for a Network Alert**

Returns information about a specific network alert.

**Parameters**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `id` | String | Yes | Alert ID (path parameter) |

**Example Request**

```bash
curl -X GET "https://api.shodan.io/shodan/alert/67UQ4JM3NGJKROR9/info?key=YOUR_API_KEY"
```

**Example Response**

```json
{
    "name": "DNS Alert",
    "created": "2021-01-27T03:50:24.277000",
    "triggers": {},
    "has_triggers": false,
    "expires": 0,
    "notify": {},
    "expiration": null,
    "filters": {
        "ip": ["8.8.8.8", "1.1.1.1"]
    },
    "notifiers": [],
    "id": "67UQ4JM3NGJKROR9",
    "size": 2
}
```

---

#### `DELETE /shodan/alert/{id}`

**Delete an Alert**

Removes the specified network alert.

**Parameters**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `id` | String | Yes | Alert ID (path parameter) |

**Example Request**

```bash
curl -X DELETE "https://api.shodan.io/shodan/alert/67UQ4JM3NGJKROR9?key=YOUR_API_KEY"
```

**Example Response**

```json
{"success": true}
```

---

#### `POST /shodan/alert/{id}`

**Edit the Networks Monitored in an Alert**

Updates a network alert with a new list of IPs or networks.

**Parameters**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `id` | String | Yes | Alert ID (path parameter) |
| `filters` | Object | Yes | Object with `ip` field containing updated list of IPs/CIDR ranges |

**Request Body (JSON)**

```json
{
    "filters": {
        "ip": ["8.8.8.8", "1.1.1.1"]
    }
}
```

**Example Response**

```json
{
    "name": "DNS Alert",
    "created": "2021-01-27T03:44:22.989575",
    "triggers": {},
    "has_triggers": false,
    "expires": 0,
    "expiration": null,
    "filters": {"ip": ["8.8.8.8", "1.1.1.1"]},
    "id": "67UQ4JM3NGJKROR9",
    "size": 2
}
```

---

#### `GET /shodan/alert/info`

**Get a List of All Created Alerts**

Returns all active network alerts on the account.

**Parameters**

None beyond authentication.

**Example Request**

```bash
curl -X GET "https://api.shodan.io/shodan/alert/info?key=YOUR_API_KEY"
```

**Example Response**

```json
[
    {
        "name": "DNS Alert",
        "created": "2021-01-27T03:44:22.989000",
        "triggers": {},
        "has_triggers": false,
        "expires": 0,
        "notify": {},
        "expiration": null,
        "filters": {"ip": ["8.8.8.8", "1.1.1.1"]},
        "notifiers": [],
        "id": "OYPRB8IR9Z35AZPR",
        "size": 2
    }
]
```

---

#### `GET /shodan/alert/triggers`

**Get a List of Available Triggers**

Returns all triggers that can be enabled on network alerts.

**Parameters**

None beyond authentication.

**Example Request**

```bash
curl -X GET "https://api.shodan.io/shodan/alert/triggers?key=YOUR_API_KEY"
```

**Example Response**

```json
[
    {"name": "any", "rule": "*", "description": "Match any service that is discovered"},
    {"name": "industrial_control_system", "rule": "tag:ics", "description": "Services associated with industrial control systems"},
    {"name": "malware", "rule": "tag:compromised,malware", "description": "Compromised or malware-related services"},
    {"name": "uncommon", "rule": "-port:22,80,443,7547", "description": "Services that generally shouldn't be publicly available"}
]
```

---

#### `PUT /shodan/alert/{id}/trigger/{trigger}`

**Enable a Trigger**

Enables notifications for the specified trigger on the given alert.

**Parameters**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `id` | String | Yes | Alert ID (path parameter) |
| `trigger` | String | Yes | Comma-separated list of trigger names (path parameter) |

**Example Request**

```bash
curl -X PUT "https://api.shodan.io/shodan/alert/OYPRB8IR9Z35AZPR/trigger/new_service,vulnerable?key=YOUR_API_KEY"
```

**Example Response**

```json
{"success": true}
```

---

#### `DELETE /shodan/alert/{id}/trigger/{trigger}`

**Disable a Trigger**

Stops notifications for the specified trigger on the given alert.

**Parameters**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `id` | String | Yes | Alert ID (path parameter) |
| `trigger` | String | Yes | Comma-separated list of trigger names (path parameter) |

**Example Request**

```bash
curl -X DELETE "https://api.shodan.io/shodan/alert/OYPRB8IR9Z35AZPR/trigger/new_service,vulnerable?key=YOUR_API_KEY"
```

**Example Response**

```json
{"success": true}
```

---

#### `PUT /shodan/alert/{id}/trigger/{trigger}/ignore/{service}`

**Add to Whitelist**

Ignores a specific service when it matches the given trigger (i.e., suppresses notifications for that service).

**Parameters**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `id` | String | Yes | Alert ID (path parameter) |
| `trigger` | String | Yes | Trigger name (path parameter) |
| `service` | String | Yes | Service in `ip:port` format, e.g., `1.1.1.1:80` (path parameter) |

**Example Request**

```bash
curl -X PUT "https://api.shodan.io/shodan/alert/OYPRB8IR9Z35AZPR/trigger/new_service/ignore/1.1.1.1:53?key=YOUR_API_KEY"
```

**Example Response**

```json
{"success": true}
```

---

#### `DELETE /shodan/alert/{id}/trigger/{trigger}/ignore/{service}`

**Remove from Whitelist**

Resumes notifications for a previously whitelisted service/trigger combination.

**Parameters**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `id` | String | Yes | Alert ID (path parameter) |
| `trigger` | String | Yes | Trigger name (path parameter) |
| `service` | String | Yes | Service in `ip:port` format (path parameter) |

**Example Response**

```json
{"success": true}
```

---

#### `PUT /shodan/alert/{id}/notifier/{notifier_id}`

**Add a Notifier to an Alert**

Attaches a notification service to the alert. Notifications are only sent if triggers are also enabled. Each account has a default notifier that sends via email.

**Parameters**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `id` | String | Yes | Alert ID (path parameter) |
| `notifier_id` | String | Yes | Notifier ID (path parameter); use `default` for the account's default email notifier |

**Example Request**

```bash
curl -X PUT "https://api.shodan.io/shodan/alert/OYPRB8IR9Z35AZPR/notifier/default?key=YOUR_API_KEY"
```

**Example Response**

```json
{"success": true}
```

---

#### `DELETE /shodan/alert/{id}/notifier/{notifier_id}`

**Remove a Notifier from an Alert**

Detaches a notification service from the alert.

**Parameters**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `id` | String | Yes | Alert ID (path parameter) |
| `notifier_id` | String | Yes | Notifier ID (path parameter) |

**Example Response**

```json
{"success": true}
```

---

### Notifiers

---

#### `GET /notifier`

**List All User-Created Notifiers**

Returns a list of all notifiers the user has created.

**Example Request**

```bash
curl -X GET "https://api.shodan.io/notifier?key=YOUR_API_KEY"
```

**Example Response**

```json
{
    "matches": [
        {
            "description": null,
            "args": {"to": "user@example.com"},
            "provider": "email",
            "id": "default"
        }
    ],
    "total": 2
}
```

---

#### `GET /notifier/provider`

**List Available Notification Providers**

Returns all supported notification providers and their required parameters.

**Example Request**

```bash
curl -X GET "https://api.shodan.io/notifier/provider?key=YOUR_API_KEY"
```

**Example Response**

```json
{
    "pagerduty": {"required": ["routing_key"]},
    "slack":     {"required": ["webhook_url"]},
    "telegram":  {"required": ["chat_id", "token"]},
    "webhook":   {"required": ["url"]},
    "phone":     {"required": ["to"]},
    "email":     {"required": ["to"]},
    "gitter":    {"required": ["room_id", "token"]}
}
```

---

#### `POST /notifier`

**Create a New Notifier**

Creates a new notification service endpoint.

**Parameters**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `provider` | String | Yes | Provider name (from `/notifier/provider`) |
| `description` | String | Yes | Description for the notifier |
| `**args` | String | Yes | Provider-specific required arguments (e.g., `to` for email) |

**Example Request**

```bash
curl -X POST "https://api.shodan.io/notifier?key=YOUR_API_KEY" \
  -d 'provider=email' -d 'description=Email notifier' -d 'to=user@example.com'
```

**Example Response**

```json
{"id": "1VxiaJb93Gn8TUnM", "success": true}
```

---

#### `DELETE /notifier/{id}`

**Delete a Notifier**

Removes the specified notification service.

**Parameters**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `id` | String | Yes | Notifier ID (path parameter) |

**Example Response**

```json
{"success": true}
```

---

#### `GET /notifier/{id}`

**Get Information About a Notifier**

Returns details for a specific notifier.

**Parameters**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `id` | String | Yes | Notifier ID (path parameter) |

**Example Response**

```json
{
    "description": "Email notifier",
    "args": {"to": "user@example.com"},
    "provider": "email",
    "id": "1VxiaJb93Gn8TUnM"
}
```

---

#### `PUT /notifier/{id}`

**Edit a Notifier**

Updates the parameters of an existing notifier.

**Parameters**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `id` | String | Yes | Notifier ID (path parameter) |
| `**args` | String | Yes | Updated provider-specific arguments |

**Example Request**

```bash
curl -X PUT "https://api.shodan.io/notifier/1VxiaJb93Gn8TUnM?key=YOUR_API_KEY" -d 'to=newaddress@example.com'
```

**Example Response**

```json
{"id": "1VxiaJb93Gn8TUnM", "success": true}
```

---

### Directory Methods

---

#### `GET /shodan/query`

**List Saved Search Queries**

Returns community-saved search queries from Shodan's directory.

**Parameters**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `page` | Integer | No | Page number; 10 items per page |
| `sort` | String | No | Sort property: `votes` or `timestamp` |
| `order` | String | No | Sort direction: `asc` or `desc` |

**Example Request**

```bash
curl -X GET "https://api.shodan.io/shodan/query?key=YOUR_API_KEY"
```

**Example Response**

```json
{
    "matches": [
        {
            "votes": 3,
            "description": "This is Moxa Nport Devices ICS system with Authentication disabled",
            "tags": ["ics", "iot", "moxa"],
            "timestamp": "2021-01-24T07:44:08.889000",
            "title": "Moxa Nport Devices with Authentication disabled",
            "query": "\"Moxa Nport Device\" Status: Authentication disabled port:\"4800\""
        }
    ],
    "total": 6746
}
```

---

#### `GET /shodan/query/search`

**Search the Directory of Saved Queries**

Searches the directory of community-saved search queries.

**Parameters**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `query` | String | Yes | Search term to find within saved query titles and descriptions |
| `page` | Integer | No | Page number; 10 items per page |

**Example Request**

```bash
curl -X GET "https://api.shodan.io/shodan/query/search?query=webcam&key=YOUR_API_KEY"
```

**Example Response**

```json
{
    "matches": [
        {
            "votes": 2,
            "description": "",
            "title": "Webcam",
            "timestamp": "2019-07-07T02:54:45.194000",
            "tags": [""],
            "query": "IP Webcam has_screenshot: -port:3269 country:\"KR\""
        }
    ],
    "total": 309
}
```

---

#### `GET /shodan/query/tags`

**List the Most Popular Tags**

Returns a list of popular tags used in saved search queries.

**Parameters**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `size` | Integer | No | Number of tags to return (default: `10`) |

**Example Request**

```bash
curl -X GET "https://api.shodan.io/shodan/query/tags?key=YOUR_API_KEY"
```

**Example Response**

```json
{
    "matches": [
        {"count": 209, "value": "webcam"},
        {"count": 172, "value": "cam"},
        {"count": 159, "value": "camera"}
    ],
    "total": 7580
}
```

---

### Bulk Data *(Enterprise)*

---

#### `GET /shodan/data`

**Get a List of Available Datasets**

Returns all datasets available for download.

**Example Request**

```bash
curl -X GET "https://api.shodan.io/shodan/data?key=YOUR_API_KEY"
```

**Example Response**

```json
[
    {"scope": "monthly", "name": "country",   "description": "Data broken down by country of the device"},
    {"scope": "daily",   "name": "ships",     "description": "AIS data from public receivers"},
    {"scope": "daily",   "name": "ping",      "description": "Ping sweeps of the entire IPv4 as well as statistical breakdown of devices by country"},
    {"scope": "monthly", "name": "dnsdb",     "description": "DNS data for active domains on the Internet"},
    {"scope": "daily",   "name": "raw-daily", "description": "Data files containing all the information collected during a day"}
]
```

---

#### `GET /shodan/data/{dataset}`

**List the Files for a Dataset**

Returns downloadable files available within the specified dataset.

**Parameters**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `dataset` | String | Yes | Dataset name from `/shodan/data` (path parameter) |

**Example Request**

```bash
curl -X GET "https://api.shodan.io/shodan/data/raw-daily?key=YOUR_API_KEY"
```

**Example Response**

```json
[
    {
        "url": "https://...",
        "timestamp": 1611711401000,
        "sha1": "5a91f49c90da5ab8856c83c84846941115c55441",
        "name": "2021-01-26.json.gz",
        "size": 104650655998
    }
]
```

---

### Manage Organization *(Enterprise)*

---

#### `GET /org`

**General Organization Information**

Returns information about the organization including members, upgrades, and authorized domains.

**Example Request**

```bash
curl -X GET "https://api.shodan.io/org?key=YOUR_API_KEY"
```

**Example Response**

```json
{
    "name": "Shodan Organization",
    "created": "2020-09-30T15:41:48.073000",
    "admins": [{"username": "admin", "email": "admin@shodan.io"}],
    "members": [{"username": "member", "email": "member@shodan.io"}],
    "upgrade_type": "stream-100",
    "domains": ["shodan.io"],
    "logo": false,
    "id": "p3cEAmoDapAPeP7w"
}
```

---

#### `PUT /org/member/{user}`

**Add a New Member**

Adds a Shodan user to the organization and upgrades them.

**Parameters**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `user` | String | Yes | Username or email of the Shodan user (path parameter) |
| `notify` | Boolean | No | Whether to send an email notification to the new member |

**Example Request**

```bash
curl -X PUT "https://api.shodan.io/org/member/new-member@shodan.io?key=YOUR_API_KEY"
```

**Example Response**

```json
{"success": true}
```

---

#### `DELETE /org/member/{user}`

**Remove a Member**

Removes and downgrades the specified member from the organization.

**Parameters**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `user` | String | Yes | Username or email of the Shodan user (path parameter) |

**Example Request**

```bash
curl -X DELETE "https://api.shodan.io/org/member/new-member@shodan.io?key=YOUR_API_KEY"
```

**Example Response**

```json
{"success": true}
```

---

### Account Methods

---

#### `GET /account/profile`

**Account Profile**

Returns information about the Shodan account linked to the given API key.

**Parameters**

None beyond authentication.

**Example Request**

```bash
curl -X GET "https://api.shodan.io/account/profile?key=YOUR_API_KEY"
```

**Example Response**

```json
{
    "member": true,
    "credits": 0,
    "display_name": null,
    "created": "2020-06-15T10:44:43.148000"
}
```

---

### DNS Methods

---

#### `GET /dns/domain/{domain}`

**Domain Information**

Returns all subdomains and other DNS entries for the given domain. **Uses 1 query credit per lookup.**

**Parameters**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `domain` | String | Yes | Domain name (path parameter), e.g., `google.com` |
| `history` | Boolean | No | If `true`, include historical DNS data (default: `false`) |
| `type` | String | No | DNS record type filter. Possible values: `A`, `AAAA`, `CNAME`, `NS`, `SOA`, `MX`, `TXT` |
| `page` | Integer | No | Page number, 100 results per page (default: `1`) |

**Example Request**

```bash
curl -X GET "https://api.shodan.io/dns/domain/google.com?key=YOUR_API_KEY"
```

**Example Response**

```json
{
    "domain": "google.com",
    "tags": ["ipv6"],
    "data": [
        {
            "subdomain": "",
            "type": "MX",
            "value": "aspmx.l.google.com",
            "last_seen": "2021-01-19T22:23:15.978799+00:00"
        },
        {
            "subdomain": "*.auth.corp",
            "type": "CNAME",
            "value": "uberproxy.l.google.com",
            "last_seen": "2021-01-26T13:04:34.018114+00:00"
        }
    ],
    "subdomains": ["*.auth.corp", "*.cloud.sandbox"],
    "more": true
}
```

---

#### `GET /dns/resolve`

**DNS Lookup**

Resolves a list of hostnames to their IP addresses.

**Parameters**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `hostnames` | String | Yes | Comma-separated list of hostnames, e.g., `google.com,bing.com` |

**Example Request**

```bash
curl -X GET "https://api.shodan.io/dns/resolve?hostnames=google.com,facebook.com&key=YOUR_API_KEY"
```

**Example Response**

```json
{
    "google.com": "172.217.6.46",
    "facebook.com": "157.240.22.35"
}
```

---

#### `GET /dns/reverse`

**Reverse DNS Lookup**

Returns the hostnames defined for the given list of IP addresses.

**Parameters**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `ips` | String | Yes | Comma-separated list of IP addresses, e.g., `74.125.227.230,204.79.197.200` |

**Example Request**

```bash
curl -X GET "https://api.shodan.io/dns/reverse?ips=8.8.8.8,1.1.1.1&key=YOUR_API_KEY"
```

**Example Response**

```json
{
    "8.8.8.8": ["dns.google"],
    "1.1.1.1": ["one.one.one.one"]
}
```

---

### Utility Methods

---

#### `GET /tools/httpheaders`

**HTTP Headers**

Returns the HTTP headers that the calling client sends when connecting to a webserver.

**Parameters**

None beyond authentication.

**Example Request**

```bash
curl -X GET "https://api.shodan.io/tools/httpheaders?key=YOUR_API_KEY"
```

**Example Response**

```json
{
    "User-Agent": "curl/7.64.1",
    "Host": "api.shodan.io",
    "Accept": "*/*",
    "X-Forwarded-For": "113.161.57.41",
    "Connection": "Keep-Alive"
}
```

---

#### `GET /tools/myip`

**My IP Address**

Returns the caller's current public IP address as seen from the Internet.

**Parameters**

None beyond authentication.

**Example Request**

```bash
curl -X GET "https://api.shodan.io/tools/myip?key=YOUR_API_KEY"
```

**Example Response**

```
"113.161.57.41"
```

---

### API Status Methods

---

#### `GET /api-info`

**API Plan Information**

Returns information about the API plan associated with the given API key.

**Parameters**

None beyond authentication.

**Example Request**

```bash
curl -X GET "https://api.shodan.io/api-info?key=YOUR_API_KEY"
```

**Example Response**

```json
{
    "scan_credits": 100000,
    "usage_limits": {
        "scan_credits": -1,
        "query_credits": -1,
        "monitored_ips": -1
    },
    "plan": "stream-100",
    "https": false,
    "unlocked": true,
    "query_credits": 100000,
    "monitored_ips": 19,
    "unlocked_left": 100000,
    "telnet": false
}
```

> `-1` in `usage_limits` indicates no cap on that resource.

---

## Endpoint Summary

| Method | Endpoint | Description | Credits |
|---|---|---|---|
| GET | `/shodan/host/{ip}` | Host information | None |
| GET | `/shodan/host/count` | Search result count only | None |
| GET | `/shodan/host/search` | Search Shodan | Query credits (filtered/paginated) |
| GET | `/shodan/host/search/facets` | List available facets | None |
| GET | `/shodan/host/search/filters` | List available filters | None |
| GET | `/shodan/host/search/tokens` | Parse search query | None |
| GET | `/shodan/ports` | List crawled ports | None |
| GET | `/shodan/protocols` | List scan protocols | None |
| POST | `/shodan/scan` | Submit IP scan | Scan credits (1 per IP) |
| POST | `/shodan/scan/internet` | Scan entire Internet for a port | Enterprise only |
| GET | `/shodan/scans` | List all scans | None |
| GET | `/shodan/scan/{id}` | Get scan status | None |
| POST | `/shodan/alert` | Create network alert | None |
| GET | `/shodan/alert/{id}/info` | Get alert details | None |
| DELETE | `/shodan/alert/{id}` | Delete alert | None |
| POST | `/shodan/alert/{id}` | Edit alert | None |
| GET | `/shodan/alert/info` | List all alerts | None |
| GET | `/shodan/alert/triggers` | List trigger types | None |
| PUT | `/shodan/alert/{id}/trigger/{trigger}` | Enable trigger | None |
| DELETE | `/shodan/alert/{id}/trigger/{trigger}` | Disable trigger | None |
| PUT | `/shodan/alert/{id}/trigger/{trigger}/ignore/{service}` | Whitelist service | None |
| DELETE | `/shodan/alert/{id}/trigger/{trigger}/ignore/{service}` | Remove from whitelist | None |
| PUT | `/shodan/alert/{id}/notifier/{notifier_id}` | Add notifier to alert | None |
| DELETE | `/shodan/alert/{id}/notifier/{notifier_id}` | Remove notifier from alert | None |
| GET | `/notifier` | List notifiers | None |
| GET | `/notifier/provider` | List notification providers | None |
| POST | `/notifier` | Create notifier | None |
| DELETE | `/notifier/{id}` | Delete notifier | None |
| GET | `/notifier/{id}` | Get notifier details | None |
| PUT | `/notifier/{id}` | Edit notifier | None |
| GET | `/shodan/query` | List saved queries | None |
| GET | `/shodan/query/search` | Search saved queries | None |
| GET | `/shodan/query/tags` | List popular tags | None |
| GET | `/shodan/data` | List bulk datasets | Enterprise |
| GET | `/shodan/data/{dataset}` | List files in dataset | Enterprise |
| GET | `/org` | Organization info | Enterprise |
| PUT | `/org/member/{user}` | Add org member | Enterprise |
| DELETE | `/org/member/{user}` | Remove org member | Enterprise |
| GET | `/account/profile` | Account profile | None |
| GET | `/dns/domain/{domain}` | Domain DNS info | 1 query credit |
| GET | `/dns/resolve` | DNS lookup | None |
| GET | `/dns/reverse` | Reverse DNS lookup | None |
| GET | `/tools/httpheaders` | View client HTTP headers | None |
| GET | `/tools/myip` | View caller's public IP | None |
| GET | `/api-info` | API plan information | None |
