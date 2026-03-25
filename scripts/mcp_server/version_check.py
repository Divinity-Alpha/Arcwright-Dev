"""
Arcwright version check utility.
Checks whether a newer version is available and returns
a human-readable notification string if so.
"""

import urllib.request
import json
import os
import time
from pathlib import Path
from typing import Optional

DEFAULT_VERSION_URL = (
    "https://raw.githubusercontent.com/Divinity-Alpha/"
    "BlueprintLLM/main/version.json"
)

CACHE_PATH = Path(__file__).parent.parent.parent / ".version_cache.json"
CACHE_MAX_AGE_HOURS = 24


def _parse_semver(version_str: str) -> tuple:
    try:
        parts = version_str.strip().split('.')
        return tuple(int(p) for p in parts[:3])
    except (ValueError, AttributeError):
        return (0, 0, 0)


def _is_newer(latest: str, current: str) -> bool:
    return _parse_semver(latest) > _parse_semver(current)


def _load_cache() -> Optional[dict]:
    try:
        if not CACHE_PATH.exists():
            return None
        with open(CACHE_PATH) as f:
            cache = json.load(f)
        age_hours = (time.time() - cache.get('cached_at', 0)) / 3600
        if age_hours > CACHE_MAX_AGE_HOURS:
            return None
        return cache
    except Exception:
        return None


def _save_cache(data: dict) -> None:
    try:
        data['cached_at'] = time.time()
        with open(CACHE_PATH, 'w') as f:
            json.dump(data, f)
    except Exception:
        pass


def _fetch_version_manifest(url: str) -> Optional[dict]:
    try:
        req = urllib.request.Request(
            url,
            headers={'User-Agent': 'Arcwright-VersionCheck/1.0'},
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read().decode())
    except Exception:
        return None


def get_current_version() -> str:
    local_version_path = Path(__file__).parent.parent.parent / "version.json"
    if local_version_path.exists():
        try:
            with open(local_version_path) as f:
                data = json.load(f)
            if data.get('changelog'):
                return data['changelog'][0]['version']
        except Exception:
            pass
    return "1.0.0"


def check_for_updates(
    current_version: str = None,
    version_url: str = None,
    force_refresh: bool = False,
) -> Optional[str]:
    if current_version is None:
        current_version = get_current_version()

    if version_url is None:
        version_url = os.environ.get('ARCWRIGHT_VERSION_URL', DEFAULT_VERSION_URL)

    manifest = None
    if not force_refresh:
        manifest = _load_cache()

    if manifest is None:
        manifest = _fetch_version_manifest(version_url)
        if manifest:
            _save_cache(manifest)

    if manifest is None:
        return None

    latest_version = manifest.get('latest', '0.0.0')

    if not _is_newer(latest_version, current_version):
        return None

    latest_info = None
    for entry in manifest.get('changelog', []):
        if entry['version'] == latest_version:
            latest_info = entry
            break

    lines = [
        f"Arcwright {latest_version} is available "
        f"(you have {current_version}).",
    ]

    if latest_info:
        lines.append(f"Released: {latest_info.get('date', 'recently')}")
        highlights = latest_info.get('highlights', [])
        if highlights:
            lines.append("What's new:")
            for h in highlights[:4]:
                lines.append(f"  - {h}")

    download_url = manifest.get('download_url', 'https://www.fab.com')
    lines.append(f"Download: {download_url}")

    return "\n".join(lines)
