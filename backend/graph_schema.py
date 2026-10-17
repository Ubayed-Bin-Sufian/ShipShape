"""Schema and deterministic demo data for ShipShape Graph."""

GRAPH_NAME = "shipshape_ops"

SEED_QUERY = """
CREATE
  (web:Service {id:'web-api', name:'Web API', description:'Public order API', environment:'production'}),
  (orders:Service {id:'orders', name:'Orders Service', description:'Creates and reads orders', environment:'production'}),
  (payments:Service {id:'payments', name:'Payments Service', description:'Processes payments', environment:'production'}),
  (auth:Service {id:'auth', name:'Auth Service', description:'Validates user tokens', environment:'production'}),
  (postgres:Dependency {id:'postgres', name:'PostgreSQL', kind:'database', owner_service:'orders'}),
  (redis:Dependency {id:'redis', name:'Redis', kind:'cache', owner_service:'auth'}),
  (web)-[:DEPENDS_ON {criticality:'high'}]->(orders),
  (web)-[:DEPENDS_ON {criticality:'high'}]->(auth),
  (orders)-[:DEPENDS_ON {criticality:'high'}]->(payments),
  (orders)-[:USES_DEPENDENCY]->(postgres),
  (auth)-[:USES_DEPENDENCY]->(redis),
  (pay_deploy:Deployment {id:'deploy-payments-2026-09-14', service_id:'payments', version:'payments-2.4.0', deployed_at:'2026-09-14T10:00:00Z', status:'succeeded', change_summary:'Changed payment timeout handling'}),
  (auth_deploy:Deployment {id:'deploy-auth-2026-09-10', service_id:'auth', version:'auth-1.8.2', deployed_at:'2026-09-10T08:30:00Z', status:'succeeded', change_summary:'Rotated token validation library'}),
  (db_deploy:Deployment {id:'deploy-orders-2026-08-28', service_id:'orders', version:'orders-3.1.0', deployed_at:'2026-08-28T12:00:00Z', status:'succeeded', change_summary:'Added order history query'}),
  (pay_deploy)-[:DEPLOYED]->(payments),
  (auth_deploy)-[:DEPLOYED]->(auth),
  (db_deploy)-[:DEPLOYED]->(orders),
  (i1:Incident {id:'inc-payment-timeouts', title:'Payment requests time out', error_pattern:'payment timeout gateway', occurred_at:'2026-09-14T10:20:00Z', severity:'high', status:'resolved', root_cause:'Payments deployment reduced upstream timeout budget', resolution_summary:'Rolled back payments-2.4.0'}),
  (i2:Incident {id:'inc-token-invalid', title:'Tokens rejected after auth release', error_pattern:'invalid token unauthorized jwt', occurred_at:'2026-09-10T09:00:00Z', severity:'medium', status:'resolved', root_cause:'Auth validation library changed accepted issuer format', resolution_summary:'Restored compatible issuer configuration'}),
  (i3:Incident {id:'inc-payment-timeouts-old', title:'Payment gateway timeout', error_pattern:'payment timeout gateway', occurred_at:'2026-06-20T13:00:00Z', severity:'medium', status:'resolved', root_cause:'Payment gateway latency exceeded client timeout', resolution_summary:'Adjusted gateway timeout and retries'}),
  (i1)-[:AFFECTS]->(payments),
  (i1)-[:CAUSED_BY]->(pay_deploy),
  (i2)-[:AFFECTS]->(auth),
  (i2)-[:CAUSED_BY]->(auth_deploy),
  (i3)-[:AFFECTS]->(payments),
  (i1)-[:SIMILAR_TO]->(i3)
"""

RESET_QUERY = "MATCH (n) DETACH DELETE n"
