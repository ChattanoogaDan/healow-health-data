# Personal Health Data Viewer

A personal, read-only Healow FHIR connector. It runs only on the Mac where it is started and listens only on `127.0.0.1`.

## Run locally

```sh
cd healow-health-data
python3 healow_local.py
```

Open http://127.0.0.1:8765/, select **Connect Healow**, complete the Healow approval, then select **Load my laboratory results**.

## Moving to a new Mac

Follow the complete [new-Mac setup and handoff guide](docs/NEW-MAC-SETUP.md). The source code is in the public owner repository. On the new Mac:

```sh
git clone https://github.com/ChattanoogaDan/healow-health-data.git
cd healow-health-data
python3 healow_local.py
```

Then open http://127.0.0.1:8765/ and connect to Healow again. OAuth access tokens are held only in the running local process and are not saved in the repository, so no health record data or active session transfers to the new Mac.

## Privacy

The GitHub Pages site is only the registered OAuth callback page. It does not retrieve, store, or display health records. The local helper performs the token exchange and FHIR queries on the Mac where it runs.
