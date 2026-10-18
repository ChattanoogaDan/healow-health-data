# New Mac setup and project handoff

## Purpose

This project is Dan Wofford's personal, read-only Healow/eClinicalWorks FHIR viewer. It connects only after Dan approves access through Healow. It is not a clinical tool, does not write to Healow, and does not send health records to GitHub Pages.

## Current working architecture

- **Source repository:** https://github.com/ChattanoogaDan/healow-health-data
- **Repository visibility:** public. It contains code and non-PHI setup documentation only.
- **GitHub Pages callback:** https://chattanoogadan.github.io/healow-health-data/callback.html
- **Local application:** `healow_local.py`, bound only to `127.0.0.1:8765`
- **OAuth mode:** public OAuth client, Authorization Code flow with PKCE (S256)
- **FHIR endpoint:** Healow R4 endpoint for the authorized Restore Health and Wellness practice
- **Data currently proved to work:** Patient record and patient-scoped laboratory `Observation` results
- **Local view:** raw FHIR laboratory data and a normalized laboratory summary (test name, date, value/unit, reference range, server-provided abnormal flag)

The static GitHub Pages callback forwards the temporary authorization response to the loopback-only local helper. That is necessary because Healow's token endpoint does not permit a token exchange directly from the GitHub Pages browser origin.

## What does not move to the new Mac

Do **not** copy or commit:

- portal passwords, MFA codes, recovery answers, access tokens, authorization codes, refresh tokens, or session cookies
- FHIR JSON responses, laboratory data, browser downloads, screenshots, or local logs containing health data
- the current running process

The current implementation stores the access token only in process memory. It is lost at restart by design. The new Mac must use a fresh Healow authorization.

## New Mac steps

1. Install or confirm Apple Command Line Tools and Python 3:

   ```sh
   xcode-select --install
   python3 --version
   git --version
   ```

2. Clone the project. The repository is public, so GitHub sign-in is not required for cloning:

   ```sh
   git clone https://github.com/ChattanoogaDan/healow-health-data.git
   cd healow-health-data
   ```

3. Run the local-only connector:

   ```sh
   python3 healow_local.py
   ```

4. On that new Mac, open http://127.0.0.1:8765/.

5. Choose **Connect Healow**, sign in, and approve the read-only request. Do not paste any token into chat.

6. Select **Show laboratory summary** or **Load raw laboratory data**.

No Healow app re-registration is expected: the registered GitHub Pages callback remains unchanged and the same public-client configuration is in the source project.

## Routine operation on the new Mac

Start the local connector when needed:

```sh
cd ~/healow-health-data
python3 healow_local.py
```

Then use the local browser URL. With the current session-only model, authorize after a restart or when Healow access expires.

## Safe future direction

The intended next phase is a local encrypted, on-demand/post-visit sync cache with explicit assistant access limited to the records relevant to a question. Do not implement persistent token or health-record storage without Dan's explicit approval and a reviewed encryption/key-management design.

## For a future Hermes session

Read, in order:

1. `README.md`
2. this file
3. `healow_local.py`
4. `test_healow_local.py`

Run the test suite before editing:

```sh
python3 -m unittest test_healow_local.py -v
```

Use strict test-first changes. Keep API scopes read-only and use the official Healow OAuth/FHIR flow. A working local viewer does not itself give Hermes chat access to the medical data; a separate explicit, least-privilege bridge is required.
