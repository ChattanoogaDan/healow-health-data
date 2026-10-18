"""Encrypted, local-only storage and change detection for Healow syncs."""
import json
from pathlib import Path

from cryptography.fernet import Fernet


def read_cache(path, key):
    path = Path(path)
    if not path.exists():
        return {"resources": {}}
    return json.loads(Fernet(key).decrypt(path.read_bytes()))


def write_cache(path, key, payload):
    path = Path(path)
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    path.write_bytes(Fernet(key).encrypt(json.dumps(payload, separators=(",", ":")).encode()))
    path.chmod(0o600)


def detect_new_resources(previous, current):
    if not previous.get("synced_at"):
        return {"first_sync": True, "new": []}
    known = {
        (resource_type, resource.get("id"))
        for resource_type, resources in previous.get("resources", {}).items()
        for resource in resources
    }
    return {
        "first_sync": False,
        "new": [
            {"resource_type": resource_type, "id": resource.get("id")}
            for resource_type, resources in current.get("resources", {}).items()
            for resource in resources
            if (resource_type, resource.get("id")) not in known
        ],
    }
