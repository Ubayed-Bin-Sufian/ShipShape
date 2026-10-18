import json
import os
import sys
import unittest
from unittest.mock import Mock, patch
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import handler

class HandlerTests(unittest.TestCase):
    def event(self, body): return {"requestContext":{"http":{"method":"POST"}},"body":json.dumps(body)}
    def test_empty_input_is_rejected(self): self.assertEqual(handler.handler(self.event({"error_text":" "}), None)["statusCode"], 400)
    def test_large_input_is_rejected(self): self.assertEqual(handler.handler(self.event({"error_text":"x"*12001}), None)["statusCode"], 400)
    @patch.object(handler, "OPENAI_API_KEY", "test-key")
    @patch.object(handler, "openai_client")
    def test_response_formatting(self, client):
        client.responses.create.return_value.output_text=json.dumps({"explanation":"x","likely_cause":"y","diagnostic_steps":["z"],"verification_commands":["echo ok"]})
        result=handler.handler(self.event({"error_text":"error"}), None)
        self.assertEqual(result["statusCode"], 200); self.assertEqual(json.loads(result["body"])["explanation"], "x")
    @patch.object(handler, "OPENAI_API_KEY", "test-key")
    @patch.object(handler, "openai_client")
    def test_throttling_is_safe(self, client):
        client.responses.create.side_effect=handler.RateLimitError("rate limited", response=Mock(), body=None)
        self.assertEqual(handler.handler(self.event({"error_text":"error"}), None)["statusCode"], 429)

    @patch.object(handler, "OPENAI_API_KEY", "test-key")
    @patch.object(handler, "openai_client", Mock())
    @patch.object(handler, "GraphClient")
    def test_investigation_requires_graph(self, graph):
        graph.from_environment.side_effect = handler.GraphUnavailable()
        result = handler.handler({**self.event({"error_text":"payment timeout"}), "requestContext":{"http":{"method":"POST","path":"/investigate"}}}, None)
        self.assertEqual(result["statusCode"], 503)

    @patch.object(handler, "OPENAI_API_KEY", "test-key")
    @patch.object(handler, "openai_client")
    @patch.object(handler, "GraphClient")
    def test_empty_graph_returns_uncertainty_without_llm_claims(self, graph, client):
        graph.from_environment.return_value.query.return_value = []
        result = handler.handler({**self.event({"error_text":"quantum toaster meltdown"}), "requestContext":{"http":{"method":"POST","path":"/investigate"}}}, None)
        body = json.loads(result["body"])
        self.assertEqual(result["statusCode"], 200)
        self.assertEqual(body["confidence"], "low")
        self.assertIn("insufficient", body["likely_cause"])
        self.assertEqual(body["graph_evidence"], {"services": [], "deployments": [], "incidents": [], "paths": []})
        client.responses.create.assert_not_called()

if __name__ == "__main__": unittest.main()
