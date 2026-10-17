"""Evidence retrieval and investigation orchestration."""
from typing import Any

QUERIES = {
    "services": """
      MATCH (s:Service)-[r:DEPENDS_ON|USES_DEPENDENCY]->(target)
      WHERE toLower(s.name) CONTAINS toLower($term) OR toLower(target.name) CONTAINS toLower($term)
      RETURN s.id, s.name, type(r), target.id, target.name LIMIT 25
    """,
    "deployments": """
      MATCH (d:Deployment)-[:DEPLOYED]->(s:Service)
      WHERE s.id IN $service_ids RETURN d.id, d.version, d.deployed_at, d.status, d.change_summary, s.id
      ORDER BY d.deployed_at DESC LIMIT 10
    """,
    "incidents": """
      MATCH (i:Incident)-[:AFFECTS]->(s:Service)
      WHERE s.id IN $service_ids RETURN i.id, i.title, i.error_pattern, i.occurred_at, i.root_cause, s.id
      ORDER BY i.occurred_at DESC LIMIT 10
    """,
    "paths": """
      MATCH p=(i:Incident)-[:AFFECTS]->(s:Service)<-[:DEPLOYED]-(d:Deployment)
      WHERE i.id IN $incident_ids RETURN i.id, s.id, d.id, d.version LIMIT 20
    """,
}


def _terms(text: str) -> list[str]:
    words = [w.strip(".,:;!?()[]{}\"'").lower() for w in text.split()]
    return list(dict.fromkeys([w for w in words if len(w) >= 4]))[:8]


def retrieve_evidence(client: Any, incident_text: str) -> dict[str, Any]:
    service_rows: list[Any] = []
    for term in _terms(incident_text):
        service_rows.extend(client.query(QUERIES["services"], {"term": term}))
    service_ids = list(dict.fromkeys([row[0] for row in service_rows if row and row[0]]))
    deployments = client.query(QUERIES["deployments"], {"service_ids": service_ids}) if service_ids else []
    incidents = client.query(QUERIES["incidents"], {"service_ids": service_ids}) if service_ids else []
    incident_ids = list(dict.fromkeys([row[0] for row in incidents if row and row[0]]))
    paths = client.query(QUERIES["paths"], {"incident_ids": incident_ids}) if incident_ids else []
    return {"services": service_rows, "deployments": deployments, "incidents": incidents, "paths": paths}


def evidence_context(evidence: dict[str, Any]) -> str:
    return "Graph facts (empty sections mean no matching graph evidence):\n" + "\n".join(f"{name}: {rows}" for name, rows in evidence.items())
