import base64
import json
import logging
import os
from typing import Any
from graph_client import GraphClient, GraphUnavailable
from investigation import evidence_context, retrieve_evidence

try:
    from openai import OpenAI
    from openai import APIConnectionError, APIError, RateLimitError
except ImportError:
    OpenAI = None
    class APIConnectionError(Exception): pass
    class APIError(Exception): pass
    class RateLimitError(Exception): pass

LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)
MAX_INPUT_LENGTH = 12000
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4.1-mini")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
FRONTEND_ORIGIN = os.environ.get("FRONTEND_ORIGIN", "").rstrip("/")
openai_client = OpenAI(api_key=OPENAI_API_KEY) if OpenAI and OPENAI_API_KEY else None
SYSTEM = """You are ShipShape, a calm DevOps troubleshooter. Give concise, safe, structured advice. Return ONLY valid JSON with exactly these fields: explanation (string), likely_cause (string), diagnostic_steps (array of strings), verification_commands (array of strings). Never suggest destructive commands, credential disclosure, or automatic changes. Say when uncertain. Do not execute commands."""
RESPONSE_SCHEMA = {
    "type": "json_schema",
    "name": "shipshape_troubleshooting",
    "strict": True,
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "explanation": {"type": "string"},
            "likely_cause": {"type": "string"},
            "diagnostic_steps": {"type": "array", "items": {"type": "string"}},
            "verification_commands": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["explanation", "likely_cause", "diagnostic_steps", "verification_commands"],
    },
}
INVESTIGATION_SCHEMA = {**RESPONSE_SCHEMA, "name": "shipshape_investigation", "schema": {**RESPONSE_SCHEMA["schema"], "properties": {**RESPONSE_SCHEMA["schema"]["properties"], "evidence": {"type": "array", "items": {"type": "string"}}, "relationships": {"type": "array", "items": {"type": "string"}}, "confidence": {"type": "string"}}, "required": ["explanation", "likely_cause", "diagnostic_steps", "verification_commands", "evidence", "relationships", "confidence"]}}
INVESTIGATION_SYSTEM = """You are ShipShape Graph, a read-only DevOps incident investigator. Return ONLY valid JSON matching the schema. Use the supplied graph facts as the only source of historical incidents, deployments, services, dependencies, and relationships. Separate explicit facts from inferences in evidence strings. Never invent graph data. If evidence is missing or contradictory, say so clearly in likely_cause and set confidence to low. Never suggest destructive commands, credential disclosure, automatic changes, or command execution."""

def response(status: int, body: dict[str, Any]) -> dict[str, Any]:
    return {"statusCode": status, "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": FRONTEND_ORIGIN, "Access-Control-Allow-Headers": "content-type", "Access-Control-Allow-Methods": "POST,OPTIONS", "Vary": "Origin"}, "body": json.dumps(body)}

def parse_event(event: dict[str, Any]) -> str:
    raw = event.get("body")
    if event.get("isBase64Encoded") and raw: raw = base64.b64decode(raw).decode("utf-8")
    if not isinstance(raw, str): raise ValueError("Request body must be JSON.")
    try: payload = json.loads(raw)
    except json.JSONDecodeError as exc: raise ValueError("Request body must be valid JSON.") from exc
    text = payload.get("error_text") if isinstance(payload, dict) else None
    if not isinstance(text, str) or not text.strip(): raise ValueError("error_text must be a non-empty string.")
    if len(text) > MAX_INPUT_LENGTH: raise ValueError(f"error_text must be {MAX_INPUT_LENGTH} characters or fewer.")
    return text.strip()

def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    if event.get("requestContext", {}).get("http", {}).get("method") == "OPTIONS": return response(204, {})
    try: error_text = parse_event(event)
    except (ValueError, UnicodeDecodeError) as exc: return response(400, {"message": str(exc)})
    route = event.get("requestContext", {}).get("http", {}).get("path", "")
    if route.endswith("/investigate"):
        if not openai_client or not OPENAI_API_KEY:
            LOGGER.error("OpenAI configuration is missing")
            return response(500, {"message": "The investigation service is not configured."})
        return investigate(error_text)
    if not openai_client or not OPENAI_API_KEY:
        LOGGER.error("OpenAI configuration is missing")
        return response(500, {"message": "The troubleshooting service is not configured."})
    try:
        result = openai_client.responses.create(model=OPENAI_MODEL, instructions=SYSTEM, input=error_text, text={"format": RESPONSE_SCHEMA}, temperature=0.2, max_output_tokens=900)
        parsed = json.loads(result.output_text)
        required = ("explanation", "likely_cause", "diagnostic_steps", "verification_commands")
        if not all(key in parsed for key in required): raise ValueError("model response shape")
        return response(200, parsed)
    except RateLimitError: return response(429, {"message": "ShipShape is busy right now. Please retry in a moment."})
    except (APIConnectionError, APIError):
        LOGGER.exception("OpenAI request failed")
        return response(502, {"message": "The AI troubleshooting service is unavailable right now."})
    except (json.JSONDecodeError, KeyError, ValueError): return response(502, {"message": "The AI returned an unexpected answer. Please retry."})
    except Exception:
        LOGGER.exception("Unexpected troubleshooting failure")
        return response(500, {"message": "Something went wrong on our side. Please retry."})


def investigate(error_text: str) -> dict[str, Any]:
    try:
        graph = GraphClient.from_environment()
        evidence = retrieve_evidence(graph, error_text)
    except GraphUnavailable:
        LOGGER.exception("FalkorDB investigation unavailable")
        return response(503, {"message": "The graph investigation service is unavailable right now."})
    try:
        result = openai_client.responses.create(model=OPENAI_MODEL, instructions=INVESTIGATION_SYSTEM, input=f"Incident:\n{error_text}\n\n{evidence_context(evidence)}", text={"format": INVESTIGATION_SCHEMA}, temperature=0.1, max_output_tokens=1200)
        parsed = json.loads(result.output_text)
        required = ("explanation", "likely_cause", "diagnostic_steps", "verification_commands", "evidence", "relationships", "confidence")
        if not all(key in parsed for key in required): raise ValueError("model response shape")
        parsed["graph_evidence"] = evidence
        return response(200, parsed)
    except RateLimitError:
        return response(429, {"message": "ShipShape is busy right now. Please retry in a moment."})
    except (APIConnectionError, APIError):
        LOGGER.exception("OpenAI investigation failed")
        return response(502, {"message": "The AI investigation service is unavailable right now."})
    except (json.JSONDecodeError, KeyError, ValueError):
        return response(502, {"message": "The AI returned an unexpected investigation answer. Please retry."})
    except Exception:
        LOGGER.exception("Unexpected investigation failure")
        return response(500, {"message": "Something went wrong during investigation. Please retry."})
