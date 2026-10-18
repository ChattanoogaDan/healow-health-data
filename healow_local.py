#!/usr/bin/env python3
"""Local-only Healow OAuth companion for the Personal Health Data Viewer."""
import base64
import hashlib
import json
import os
import secrets
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from cryptography.fernet import Fernet
from sync_store import detect_new_resources, read_cache, write_cache

HOST, PORT = "127.0.0.1", 8765
CLIENT_ID = "ur4XSJpgwi1CcZ0FqUp-BAMSmuM7iSpctwQtfPt3fzU"
REDIRECT_URI = "https://chattanoogadan.github.io/healow-health-data/callback.html"
AUTHORIZE_URL = "https://oauthserver.eclinicalworks.com/oauth/oauth2/authorize"
TOKEN_URL = "https://oauthserver.eclinicalworks.com/oauth/oauth2/token"
FHIR_BASE = "https://fhir4.healow.com/fhir/r4/HADFDD"
SCOPES = " ".join([
    "openid", "fhirUser", "patient/Patient.read", "patient/AllergyIntolerance.read",
    "patient/CarePlan.read", "patient/Condition.read", "patient/DiagnosticReport.read",
    "patient/DocumentReference.read", "patient/Encounter.read", "patient/Immunization.read",
    "patient/MedicationRequest.read", "patient/Observation.read", "patient/Procedure.read",
])
SESSION = {"state": None, "verifier": None, "access_token": None, "patient": None, "error": None, "sync_report": None}
CACHE_PATH = Path.home() / ".healow-health-data" / "sync-cache.enc"
KEYCHAIN_SERVICE = "healow-health-data-cache"


def local_cache_key():
    existing = subprocess.run(
        ["security", "find-generic-password", "-a", "local-cache", "-s", KEYCHAIN_SERVICE, "-w"],
        capture_output=True, text=True,
    )
    if existing.returncode == 0:
        return existing.stdout.strip().encode()
    key = Fernet.generate_key()
    subprocess.run(
        ["security", "add-generic-password", "-U", "-a", "local-cache", "-s", KEYCHAIN_SERVICE, "-w", key.decode()],
        check=True, capture_output=True,
    )
    return key


def fetch_fhir(target):
    request = urllib.request.Request(target, headers={"Authorization": f"Bearer {SESSION['access_token']}", "Accept": "application/fhir+json"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read())


def sync_resources():
    patient_id = SESSION["patient"]
    targets = {"Patient": f"{FHIR_BASE}/Patient/{urllib.parse.quote(patient_id)}", "Observation": build_laboratory_search_url(patient_id)}
    for resource_type in ("AllergyIntolerance", "CarePlan", "Condition", "DiagnosticReport", "DocumentReference", "Encounter", "Immunization", "MedicationRequest", "Procedure"):
        targets[resource_type] = build_search_url(resource_type, {"patient": patient_id})
    resources, errors = {}, {}
    for resource_type, target in targets.items():
        try:
            payload = fetch_fhir(target)
            resources[resource_type] = [payload] if payload.get("resourceType") != "Bundle" else [item["resource"] for item in payload.get("entry", [])]
        except Exception as exc:
            errors[resource_type] = str(exc)
    key = local_cache_key()
    previous = read_cache(CACHE_PATH, key)
    current = {"synced_at": datetime.now(timezone.utc).isoformat(), "resources": resources}
    changes = detect_new_resources(previous, current)
    write_cache(CACHE_PATH, key, current)
    return {"first_sync": changes["first_sync"], "new": changes["new"], "errors": errors, "counts": {kind: len(items) for kind, items in resources.items()}}


def b64url(raw):
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def build_authorize_url(state, challenge):
    query = urllib.parse.urlencode({
        "response_type": "code", "client_id": CLIENT_ID, "redirect_uri": REDIRECT_URI,
        "scope": SCOPES, "state": state, "aud": FHIR_BASE,
        "code_challenge": challenge, "code_challenge_method": "S256",
    })
    return f"{AUTHORIZE_URL}?{query}"


def build_search_url(resource_type, parameters):
    return f"{FHIR_BASE}/{resource_type}?{urllib.parse.urlencode(parameters)}"


def build_laboratory_search_url(patient_id):
    return build_search_url("Observation", {
        "patient": patient_id, "category": "laboratory",
    })


def summarize_laboratory_bundle(bundle):
    summary = []
    for entry in bundle.get("entry", []):
        observation = entry.get("resource", {})
        if observation.get("resourceType") != "Observation":
            continue
        coding = observation.get("code", {})
        test_name = coding.get("text") or next(
            (item.get("display") or item.get("code") for item in coding.get("coding", []) if item.get("display") or item.get("code")),
            "Unnamed test",
        )
        quantity = observation.get("valueQuantity")
        if quantity:
            value = " ".join(str(part) for part in (quantity.get("value"), quantity.get("unit")) if part is not None)
        else:
            value = observation.get("valueString", "")
        ranges = observation.get("referenceRange", [])
        reference_range = ranges[0].get("text", "") if ranges else ""
        flags = observation.get("interpretation", [])
        flag = flags[0].get("text") if flags else ""
        summary.append({
            "test": test_name, "date": observation.get("effectiveDateTime", ""), "value": value,
            "reference_range": reference_range, "flag": flag or "",
        })
    return summary


def html_page():
    status = "Connected" if SESSION["access_token"] else "Not connected"
    error = f"<p class='error'>{SESSION['error']}</p>" if SESSION["error"] else ""
    report = SESSION.get("sync_report")
    sync_note = ""
    if report:
        sync_phrase = "Baseline created" if report["first_sync"] else f"{len(report['new'])} new record(s) found"
        sync_note = f"<p><strong>Sync:</strong> {sync_phrase}. Retrieved {sum(report['counts'].values())} records; {len(report['errors'])} resource type(s) unavailable.</p>"
    patient_button = "<button onclick='loadData(\"/api/patient\")'>Load my patient summary</button>" if SESSION["access_token"] else ""
    labs_button = "<button onclick='loadData(\"/api/labs\")'>Load raw laboratory data</button>" if SESSION["access_token"] else ""
    summary_button = "<button onclick='loadData(\"/api/lab-summary\")'>Show laboratory summary</button>" if SESSION["access_token"] else ""
    sync_button = "<a href='/sync'><button>Sync now</button></a>" if SESSION["access_token"] else ""
    return f"""<!doctype html><html><head><meta charset='utf-8'><title>Personal Health Data Viewer</title>
<style>body{{max-width:760px;margin:3rem auto;padding:0 1rem;font:17px/1.5 system-ui;color:#172033}}.card{{border:1px solid #c5d9e7;border-radius:12px;padding:1.25rem;margin:1rem 0}}button{{background:#145d83;color:#fff;border:0;border-radius:8px;padding:.75rem 1rem;font:inherit;cursor:pointer;margin:.25rem}}pre{{white-space:pre-wrap;word-break:break-word;background:#f5f7f8;padding:1rem;border-radius:8px}}.error{{color:#a21d2e}}</style></head>
<body><h1>Personal Health Data Viewer</h1><div class='card'><strong>Status:</strong> {status}{error}{sync_note}<p>This local-only helper exchanges the authorization code server-side so no token request is made from GitHub Pages.</p><a href='/connect'><button>Connect Healow</button></a> {sync_button} {patient_button} {labs_button} {summary_button}</div><pre id='output'></pre>
<script>async function loadData(path){{let r=await fetch(path);let t=await r.text();document.getElementById('output').textContent=t;}}</script></body></html>"""


def exchange_code(code):
    body = urllib.parse.urlencode({
        "grant_type": "authorization_code", "code": code, "redirect_uri": REDIRECT_URI,
        "client_id": CLIENT_ID, "code_verifier": SESSION["verifier"],
    }).encode()
    request = urllib.request.Request(TOKEN_URL, data=body, method="POST", headers={"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read())


class Handler(BaseHTTPRequestHandler):
    def send_html(self, body, status=200):
        self.send_response(status); self.send_header("Content-Type", "text/html; charset=utf-8"); self.end_headers(); self.wfile.write(body.encode())

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/":
            return self.send_html(html_page())
        if parsed.path == "/connect":
            SESSION.update({"state": b64url(secrets.token_bytes(24)), "verifier": b64url(secrets.token_bytes(64)), "error": None})
            challenge = b64url(hashlib.sha256(SESSION["verifier"].encode()).digest())
            self.send_response(302); self.send_header("Location", build_authorize_url(SESSION["state"], challenge)); self.end_headers(); return
        if parsed.path == "/sync":
            if not SESSION["access_token"]:
                return self.send_html("Not connected", 401)
            try:
                SESSION["sync_report"] = sync_resources()
                SESSION["error"] = None
            except Exception as exc:
                SESSION["error"] = f"Sync failed: {exc}"
            self.send_response(302); self.send_header("Location", "/"); self.end_headers(); return
        if parsed.path == "/callback":
            values = urllib.parse.parse_qs(parsed.query)
            if values.get("state", [None])[0] != SESSION["state"]:
                SESSION["error"] = "OAuth state verification failed. Start the connection again."
            elif values.get("error"):
                SESSION["error"] = values.get("error_description", values["error"])[0]
            else:
                try:
                    payload = exchange_code(values.get("code", [""])[0])
                    SESSION["access_token"] = payload["access_token"]
                    SESSION["patient"] = payload.get("patient")
                    SESSION["sync_report"] = sync_resources()
                    SESSION["error"] = None
                except Exception as exc:
                    SESSION["error"] = f"Token exchange failed: {exc}"
            self.send_response(302); self.send_header("Location", "/"); self.end_headers(); return
        if parsed.path in ("/api/patient", "/api/labs", "/api/lab-summary"):
            if not SESSION["access_token"]:
                return self.send_html("Not connected", 401)
            if parsed.path == "/api/patient":
                target = f"{FHIR_BASE}/Patient/{urllib.parse.quote(SESSION['patient'])}" if SESSION["patient"] else f"{FHIR_BASE}/Patient"
            else:
                target = build_laboratory_search_url(SESSION["patient"])
            try:
                request = urllib.request.Request(target, headers={"Authorization": f"Bearer {SESSION['access_token']}", "Accept": "application/fhir+json"})
                with urllib.request.urlopen(request, timeout=30) as response:
                    body = response.read()
                    if parsed.path == "/api/lab-summary":
                        body = json.dumps(summarize_laboratory_bundle(json.loads(body)), indent=2).encode()
                    self.send_response(response.status); self.send_header("Content-Type", "application/json"); self.end_headers(); self.wfile.write(body)
            except urllib.error.HTTPError as exc:
                detail = exc.read().decode("utf-8", errors="replace")
                self.send_html(f"FHIR request failed: HTTP {exc.code}: {detail}", 502)
            except Exception as exc:
                self.send_html(f"FHIR request failed: {exc}", 502)
            return
        self.send_html("Not found", 404)

    def log_message(self, *_):
        pass


if __name__ == "__main__":
    print(f"Open http://{HOST}:{PORT}")
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
