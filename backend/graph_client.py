"""Small FalkorDB adapter, kept separate so it can be mocked in tests."""
import os
from typing import Any

try:
    from falkordb import FalkorDB
except ImportError:  # Allows existing unit tests to run without dependencies installed.
    FalkorDB = None

from graph_schema import GRAPH_NAME, RESET_QUERY, SEED_QUERY


class GraphUnavailable(Exception):
    pass


class GraphClient:
    def __init__(self, graph: Any):
        self.graph = graph

    @classmethod
    def from_environment(cls):
        if FalkorDB is None:
            raise GraphUnavailable("FalkorDB client is not installed")
        try:
            db = FalkorDB.from_url(os.environ["FALKORDB_URL"], socket_connect_timeout=float(os.getenv("FALKORDB_CONNECT_TIMEOUT_SECONDS", "2")), socket_timeout=float(os.getenv("FALKORDB_SOCKET_TIMEOUT_SECONDS", "4")))
            return cls(db.select_graph(os.getenv("FALKORDB_GRAPH_NAME", GRAPH_NAME)))
        except Exception as exc:
            raise GraphUnavailable("Could not connect to FalkorDB") from exc

    def query(self, cypher: str, params: dict[str, Any] | None = None):
        try:
            return self.graph.ro_query(cypher, params or {}).result_set
        except Exception as exc:
            raise GraphUnavailable("FalkorDB query failed") from exc

    def initialize_demo_graph(self):
        try:
            self.graph.query(RESET_QUERY)
            self.graph.query(SEED_QUERY)
        except Exception as exc:
            raise GraphUnavailable("Could not initialize FalkorDB graph") from exc
