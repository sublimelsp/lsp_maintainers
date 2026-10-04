from __future__ import annotations

import json
import platform
import plistlib
import re
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

import tomllib
from package_version import PackageVersion
from utils import is_compatible_version

PACKAGE_CONTROL_CHANNEL_URL = 'https://packagecontrol.github.io/channel/channel_v4.json'
PYPI_URL = 'https://pypi.org/pypi'
SCRIPT_DIR = Path(__file__).resolve().parent
REPOSITORIES_DIR = SCRIPT_DIR.parent / 'repositories'
REQUIREMENTS_FILE = REPOSITORIES_DIR / 'requirements-packages.txt'
# The checkout-repos.py script downloads the macOS build of Sublime Text.
ST_INFO_PLIST = REPOSITORIES_DIR / 'Sublime Text.app' / 'Contents' / 'Info.plist'
STUBS_DIR = REPOSITORIES_DIR / 'stubs'


def normalize_name(name: str) -> str:
    """Normalize a library name as described in PEP 503, so that `typing_extensions` equals `typing-extensions`."""
    return re.sub(r'[-_.]+', '-', name).lower()


def get_st_version() -> int:
    with ST_INFO_PLIST.open('rb') as f:
        return int(plistlib.load(f)['CFBundleVersion'])


def get_python_version() -> str:
    pyproject = tomllib.loads((REPOSITORIES_DIR / 'pyproject.toml').read_text(encoding='utf-8'))
    return pyproject['tool']['pyright']['pythonVersion']


def get_platform_selectors() -> list[str]:
    """Return the platform selectors of `dependencies.json` in the order that Package Control uses."""
    arch = 'arm64' if platform.machine() in ('arm64', 'aarch64') else 'x64'
    return [f'osx-{arch}', 'osx', '*']


def get_package_libraries(dependencies_file: Path, st_version: int, platform_selectors: list[str]) -> list[str]:
    dependencies: dict[str, dict[str, list[str]]] = json.loads(dependencies_file.read_text(encoding='utf-8'))
    for platform_selector in platform_selectors:
        if platform_selector not in dependencies:
            continue
        for version_selector, libraries in dependencies[platform_selector].items():
            if is_compatible_version(version_selector, st_version):
                return libraries
        return []
    return []


def get_local_names() -> set[str]:
    """Return the names of the libraries that the type check gets from the source checkouts or from the stubs."""
    names = {normalize_name(path.name) for path in REPOSITORIES_DIR.iterdir() if path.is_dir()}
    if STUBS_DIR.is_dir():
        names.update(normalize_name(path.stem) for path in STUBS_DIR.iterdir())
    return names


def fetch_channel_libraries() -> dict[str, dict[str, Any]]:
    with urllib.request.urlopen(PACKAGE_CONTROL_CHANNEL_URL) as response:
        channel = json.loads(response.read().decode('utf-8'))
    return {
        normalize_name(library['name']): library
        for libraries in channel['libraries_cache'].values()
        for library in libraries
    }


def get_latest_version(
    library: dict[str, Any], python_version: str, st_version: int, platform_selectors: list[str]
) -> str | None:
    versions = [
        PackageVersion(release['version'])
        for release in library['releases']
        if python_version in release['python_versions']
        and is_compatible_version(release['sublime_text'], st_version)
        and set(release['platforms']) & set(platform_selectors)
    ]
    return str(max(versions)) if versions else None


def pypi_url_exists(url: str) -> bool:
    try:
        with urllib.request.urlopen(urllib.request.Request(url, method='HEAD')):
            return True
    except urllib.error.HTTPError as ex:
        if ex.code == 404:
            return False
        raise


def get_requirement(name: str, version: str) -> str | None:
    """Return the PyPI requirement for a Package Control library, or `None` if PyPI does not have the library."""
    if pypi_url_exists(f'{PYPI_URL}/{name}/{version}/json'):
        return f'{name}=={version}'
    if pypi_url_exists(f'{PYPI_URL}/{name}/json'):
        print(f'Not pinning {name}, because PyPI does not have the Package Control version {version}')
        return name
    return None


def collect_dependencies(st_version: int) -> None:
    """
    Write the PyPI requirements for the Package Control libraries that the packages in `repositories` depend on.

    The function reads the `dependencies.json` file of each package and writes the requirements to
    `repositories/requirements-packages.txt`. It pins each library to the latest version that Package Control provides
    for the Python version of the type check and for the Sublime Text build `st_version`. If PyPI does not have that
    version, the requirement is not pinned.
    """
    python_version = get_python_version()
    platform_selectors = get_platform_selectors()
    print(f'Sublime Text build {st_version}, Python {python_version}, platform {platform_selectors[0]}')

    required: dict[str, set[str]] = {}
    for dependencies_file in sorted(REPOSITORIES_DIR.glob('*/dependencies.json')):
        package_name = dependencies_file.parent.name
        for library_name in get_package_libraries(dependencies_file, st_version, platform_selectors):
            required.setdefault(normalize_name(library_name), set()).add(package_name)

    local_names = get_local_names()
    channel_libraries = fetch_channel_libraries()
    requirements: list[str] = []
    for name in sorted(required):
        if name in local_names:
            print(f'Skipping {name} (source checkout or stubs)')
            continue
        library = channel_libraries.get(name)
        version = get_latest_version(library, python_version, st_version, platform_selectors) if library else None
        if version is None:
            packages = ', '.join(sorted(required[name]))
            print(f'Skipping {name} (no Package Control release for Python {python_version}), used by: {packages}')
            continue
        requirement = get_requirement(name, version)
        if requirement is None:
            print(f'Skipping {name} (not on PyPI)')
            continue
        requirements.append(requirement)

    REQUIREMENTS_FILE.write_text(''.join(f'{requirement}\n' for requirement in requirements), encoding='utf-8')
    print(f'Wrote {len(requirements)} requirements to {REQUIREMENTS_FILE}')
