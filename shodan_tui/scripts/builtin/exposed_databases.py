"""
Exposed Databases — find databases with no authentication exposed to the internet.
Covers MongoDB, Elasticsearch, Redis, CouchDB, Cassandra, and more.
"""

from shodan_tui.scripts.base import ShodanScript

# Individual queries per DB type — OR between filter:value pairs is not supported
# on Shodan Developer plan, so there is no combined "all" query.
_QUERIES = {
    "mongodb":       "product:MongoDB port:27017",
    "elasticsearch": "product:Elasticsearch port:9200",
    "redis":         "product:Redis port:6379",
    "couchdb":       "product:CouchDB port:5984",
    "cassandra":     "product:Cassandra port:9042",
    "memcached":     "product:Memcached port:11211",
}

_DEFAULT_DB = "mongodb"


class ExposedDatabasesScript(ShodanScript):
    name = "Exposed Databases"
    description = (
        "Find internet-exposed databases (MongoDB, Elasticsearch, Redis, CouchDB, etc.) "
        "that may be accessible without authentication."
    )
    author = "shodan-tui"
    version = "1.1.0"
    tags = ["database", "exposure", "mongodb", "elasticsearch", "redis"]
    query = _QUERIES[_DEFAULT_DB]
    facets = "product,country"

    params = {
        "db_type": {
            "type": "str",
            "description": "mongodb, elasticsearch, redis, couchdb, cassandra, memcached",
            "default": _DEFAULT_DB,
        },
        "country": {
            "type": "str",
            "description": "Filter by 2-letter country code",
            "default": "",
        },
    }

    def build_query(self, **kwargs) -> str:
        db_type = kwargs.get("db_type", _DEFAULT_DB).lower().strip()
        country = kwargs.get("country", "").strip().upper()
        q = _QUERIES.get(db_type, _QUERIES[_DEFAULT_DB])
        if country:
            q += f" country:{country}"
        return q

    def format_summary(self, results: dict) -> str:
        total = results.get("total", 0)
        return f"Found {total:,} exposed database instances."
