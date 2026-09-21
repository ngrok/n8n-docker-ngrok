#!/usr/bin/env python3
"""Update the example environment from n8n's latest stable GitHub release."""

import json
import os
from pathlib import Path
import re
from urllib.request import Request, urlopen


def update_version(content, release):
    tag = release["tag_name"]
    match = re.fullmatch(r"n8n@(\d+\.\d+\.\d+)", tag)
    if release.get("draft") or release.get("prerelease") or not match:
        raise ValueError(f"Expected a stable n8n release, got {tag!r}")
    version = match[1]
    assignments = re.findall(r"^N8N_VERSION=.*$", content, re.MULTILINE)
    if len(assignments) != 1:
        raise ValueError("Expected exactly one N8N_VERSION assignment")
    current = re.fullmatch(r'N8N_VERSION="(\d+\.\d+\.\d+)"', assignments[0])
    if not current:
        raise ValueError("Expected a quoted numeric N8N_VERSION")
    if tuple(map(int, version.split("."))) <= tuple(map(int, current[1].split("."))):
        return content, current[1], version
    updated = content.replace(assignments[0], f'N8N_VERSION="{version}"', 1)
    return updated, current[1], version


def main():
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "n8n-release-update"}
    if os.environ.get("GH_TOKEN"):
        headers["Authorization"] = f"Bearer {os.environ['GH_TOKEN']}"
    request = Request("https://api.github.com/repos/n8n-io/n8n/releases/latest", headers=headers)
    with urlopen(request, timeout=30) as response:
        release = json.load(response)
    path = Path(".env.example")
    original = path.read_text()
    updated, current, version = update_version(original, release)
    if updated != original:
        path.write_text(updated)
        print(f"Updated N8N_VERSION from {current} to {version}")
    else:
        print(f"No update needed: current {current}, latest stable {version}")
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a") as output:
            output.write(f"current={current}\nversion={version}\n")
            output.write(f"release_url=https://github.com/n8n-io/n8n/releases/tag/n8n%40{version}\n")


if __name__ == "__main__":
    main()
