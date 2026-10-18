import unittest
from urllib.parse import parse_qs, urlparse

from healow_local import FHIR_BASE, build_authorize_url, build_laboratory_search_url, build_search_url


class AuthorizeUrlTests(unittest.TestCase):
    def test_builds_pkce_authorize_url_for_registered_callback(self):
        url = build_authorize_url("state-value", "challenge-value")
        parsed = urlparse(url)
        query = parse_qs(parsed.query)
        self.assertEqual(parsed.scheme, "https")
        self.assertEqual(parsed.netloc, "oauthserver.eclinicalworks.com")
        self.assertEqual(query["response_type"], ["code"])
        self.assertEqual(query["client_id"], ["ur4XSJpgwi1CcZ0FqUp-BAMSmuM7iSpctwQtfPt3fzU"])
        self.assertEqual(query["redirect_uri"], ["https://chattanoogadan.github.io/healow-health-data/callback.html"])
        self.assertEqual(query["state"], ["state-value"])
        self.assertEqual(query["code_challenge"], ["challenge-value"])
        self.assertEqual(query["code_challenge_method"], ["S256"])

    def test_static_callback_forwards_authorization_to_local_connector(self):
        with open("callback.html", encoding="utf-8") as callback:
            page = callback.read()
        self.assertIn("http://127.0.0.1:8765/callback", page)

    def test_builds_laboratory_observation_search_url(self):
        url = build_search_url("Observation", {"category": "laboratory", "_count": "100"})
        parsed = urlparse(url)
        self.assertEqual(f"{parsed.scheme}://{parsed.netloc}{parsed.path}", f"{FHIR_BASE}/Observation")
        self.assertEqual(parse_qs(parsed.query), {"category": ["laboratory"], "_count": ["100"]})

    def test_laboratory_search_scopes_request_to_authorized_patient(self):
        parsed = urlparse(build_laboratory_search_url("patient-123"))
        self.assertEqual(parse_qs(parsed.query), {
            "patient": ["patient-123"], "category": ["laboratory"],
        })


if __name__ == "__main__":
    unittest.main()
