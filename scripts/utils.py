from __future__ import annotations

import json
import re
import urllib.request
from pathlib import Path
from typing import Any, Literal, NotRequired, TypedDict

SCRIPT_DIR = Path(__file__).resolve().parent
LSP_REPOSITORY_URL = "https://raw.githubusercontent.com/sublimelsp/repository/refs/heads/main/repository.json"


class Package(TypedDict):
    name: str
    details: str
    tag_prefix: str | None


class PackageRelease(TypedDict):
    sublime_text: str
    tags: NotRequired[Literal[True] | str]


def fetch_lsp_repository() -> dict[str, Any]:
    with urllib.request.urlopen(LSP_REPOSITORY_URL) as response:
        return json.loads(response.read().decode())


def get_all_packages(st_version: int) -> list[Package]:
    packages = json.loads((SCRIPT_DIR.parent / "lsp_maintainers.sublime-settings").read_text(encoding='utf-8')).get('packages')
    official_packages = fetch_lsp_repository()['packages']
    all_packages: list[Package] = []

    for package in sorted(packages + official_packages, key=lambda item: item["name"].lower()):
        releases: list[PackageRelease] = package.get('releases', [])
        if not releases:
            all_packages.append({
                'name': package['name'],
                'details': package['details'],
                'tag_prefix': None
            })
        else:
            if compatible_release := next((r for r in releases if is_compatible_version(r['sublime_text'], st_version)), None):
                tags = compatible_release.get('tags', True)
                all_packages.append({
                    'name': package['name'],
                    'details': package['details'],
                    'tag_prefix': None if tags is True else tags
                })
            else:
                print(f'Skipping {package["name"]} as it is not compatible with current version of ST')

    return all_packages


# Utility extracted from Package Control

def is_compatible_version(version_range: str, st_version: int) -> bool:
    """
    Determines if current ST version is covered by given version range.

    :param version_range:
        The version range expression to match ST version against.

        Examples: ">4000", ">=4000", "<4000", "<=4000", "4000 - 4100"

    :param st_version:
        The ST version to evaluate.

    :returns:
        True if compatible version, False otherwise.
    """

    if version_range == "*":
        return True

    match = re.match(r"([<>]=?)(\d{4})$", version_range)
    if match:
        op, ver = match.groups()
        if op == ">":
            return st_version > int(ver)
        if op == ">=":
            return st_version >= int(ver)
        if op == "<":
            return st_version < int(ver)
        if op == "<=":
            return st_version <= int(ver)

    match = re.match(r"(\d{4}) - (\d{4})$", version_range)
    if match:
        return st_version >= int(match.group(1)) and st_version <= int(match.group(2))

    return False
