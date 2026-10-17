import os
import sys
import unittest
from unittest.mock import Mock
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from investigation import retrieve_evidence


class InvestigationTests(unittest.TestCase):
    def test_traverses_services_deployments_incidents_and_paths(self):
        graph = Mock()
        graph.query.side_effect = [
            [("payments", "Payments Service", "DEPENDS_ON", "gateway", "Gateway")],
            [("deploy-1", "payments-2.4.0", "2026-09-14", "succeeded", "timeout change", "payments")],
            [("incident-1", "Payment timeout", "payment timeout", "2026-09-14", "deployment issue", "payments")],
            [("incident-1", "payments", "deploy-1", "payments-2.4.0")],
        ]
        evidence = retrieve_evidence(graph, "payment")
        self.assertEqual(len(evidence["paths"]), 1)
        self.assertEqual(graph.query.call_count, 4)

    def test_missing_terms_does_not_fabricate_queries(self):
        graph = Mock()
        self.assertEqual(retrieve_evidence(graph, "x y"), {"services": [], "deployments": [], "incidents": [], "paths": []})
        graph.query.assert_not_called()


if __name__ == "__main__":
    unittest.main()
