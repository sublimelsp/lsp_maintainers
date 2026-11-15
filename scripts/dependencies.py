from __future__ import annotations

import io
import json
import platform
import re
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path
from typing import Any, NamedTuple

from package_version import PackageVersion
from utils import is_compatible_version

PACKAGE_CONTROL_CHANNEL_URL = 'https://packagecontrol.github.io/channel/channel_v4.json'
PYPI_URL = 'https://pypi.org/pypi'
ST_DOWNLOAD_PAGE_URL = 'https://www.sublimetext.com/download_thanks'
HTTP_TIMEOUT = 60  # seconds
SCRIPT_DIR = Path(__file__).resolve().parent
REPOSITORIES_DIR = SCRIPT_DIR.parent / 'repositories'
REQUIREMENTS_FILE = REPOSITORIES_DIR / 'requirements-packages.txt'
STUBS_DIR = REPOSITORIES_DIR / 'stubs'


def normalize_name(name: str) -> str:
    """Normalize a library name as described in PEP 503, so that `typing_extensions` equals `typing-extensions`."""
    return re.sub(r'[-_.]+', '-', name).lower()


class SublimeTextInfo(NamedTuple):
    build: int
    # The Python version of the newest plugin host, which runs the packages.
    python_version: str


class HttpRangeFile(io.RawIOBase):
    """A read-only file at a URL that fetches each read with an HTTP range request."""

    def __init__(self, url: str) -> None:
        super().__init__()
        self.url = url
        self.position = 0
        with urllib.request.urlopen(urllib.request.Request(url, method='HEAD'), timeout=HTTP_TIMEOUT) as response:
            self.size = int(response.headers['Content-Length'])

    def readable(self) -> bool:
        return True

    def seekable(self) -> bool:
        return True

    def tell(self) -> int:
        return self.position

    def seek(self, offset: int, whence: int = io.SEEK_SET) -> int:
        base = {io.SEEK_SET: 0, io.SEEK_CUR: self.position, io.SEEK_END: self.size}[whence]
        self.position = base + offset
        return self.position

    def readinto(self, buffer: Any) -> int:
        data = self.read_range(min(self.position + len(buffer), self.size))
        buffer[:len(data)] = data
        return len(data)

    def readall(self) -> bytes:
        return self.read_range(self.size)

    def read_range(self, end: int) -> bytes:
        if self.position >= end:
            return b''
        request = urllib.request.Request(self.url, headers={'Range': f'bytes={self.position}-{end - 1}'})
        with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT) as response:
            if response.status != 206:
                raise RuntimeError(f'{self.url} does not support range requests')
            data = response.read()
        self.position += len(data)
        return data


def get_latest_sublime_text_info() -> SublimeTextInfo:
    """
    Return the latest Sublime Text build and the Python version of its newest plugin host.

    The function reads only the list of files of the macOS zip, which is at the end of the zip, and not the whole zip.
    """
    request = urllib.request.Request(ST_DOWNLOAD_PAGE_URL, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT) as response:
        html = response.read().decode('utf-8', errors='replace')
    match = re.search(r'href="([^"]*_(\d+)_mac\.zip)"', html)
    if not match:
        raise RuntimeError('Failed to find the link to the latest version of Sublime Text')
    zip_url = urllib.parse.urljoin(ST_DOWNLOAD_PAGE_URL, match.group(1))
    build = int(match.group(2))
    with HttpRangeFile(zip_url) as file, zipfile.ZipFile(file) as zf:
        names = zf.namelist()
    versions = [m.group(1) for name in names if (m := re.search(r'/MacOS/plugin_host-([\d.]+)$', name))]
    if not versions:
        raise RuntimeError(f'Failed to find a plugin host in {zip_url}')
    return SublimeTextInfo(build, max(versions, key=parse_python_version))


def parse_python_version(version: str) -> tuple[int, ...]:
    return tuple(int(part) for part in version.split('.'))


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


def get_latest_release(
    library: dict[str, Any], python_version: str, st_version: int, platform_selectors: list[str]
) -> dict[str, Any] | None:
    """
    Return the latest release of a Package Control library for `python_version`.

    If no release supports `python_version`, return the latest release for the newest older Python version instead.
    """
    releases = [
        release
        for release in library['releases']
        if is_compatible_version(release['sublime_text'], st_version)
        and set(release['platforms']) & set(platform_selectors)
    ]
    supported_versions = [
        version
        for release in releases
        for version in release['python_versions']
        if parse_python_version(version) <= parse_python_version(python_version)
    ]
    if not supported_versions:
        return None
    best_version = max(supported_versions, key=parse_python_version)
    releases = [release for release in releases if best_version in release['python_versions']]
    return max(releases, key=lambda release: PackageVersion(release['version']))


def pypi_url_exists(url: str) -> bool:
    try:
        with urllib.request.urlopen(urllib.request.Request(url, method='HEAD')):
            return True
    except urllib.error.HTTPError as ex:
        if ex.code == 404:
            return False
        raise


def get_requirement(name: str, release: dict[str, Any]) -> str | None:
    """
    Return the requirement for a Package Control library release, or `None` if pip cannot install it.

    Prefer PyPI, because PyPI selects the correct wheel for the current platform. If PyPI does not have the release,
    use the wheel URL of the Package Control release.
    """
    version: str = release['version']
    url: str = release['url']
    if pypi_url_exists(f'{PYPI_URL}/{name}/{version}/json'):
        return f'{name}=={version}'
    if url.endswith('.whl'):
        return f'{name} @ {url}'
    if pypi_url_exists(f'{PYPI_URL}/{name}/json'):
        print(f'Not pinning {name}, because PyPI does not have the Package Control version {version}')
        return name
    return None


def collect_dependencies(st_info: SublimeTextInfo) -> None:
    """
    Write the PyPI requirements for the Package Control libraries that the packages in `repositories` depend on.

    The function reads the `dependencies.json` file of each package and writes the requirements to
    `repositories/requirements-packages.txt`. It pins each library to the latest version that Package Control provides
    for the Python version of the plugin host and for the build of `st_info`. If PyPI does not have that
    version, the requirement points to the wheel of the Package Control release. If that release has no wheel, the
    requirement is not pinned.
    """
    st_version, python_version = st_info
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
        release = get_latest_release(library, python_version, st_version, platform_selectors) if library else None
        if release is None:
            packages = ', '.join(sorted(required[name]))
            print(f'Skipping {name} (no Package Control release for Python {python_version}), used by: {packages}')
            continue
        requirement = get_requirement(name, release)
        if requirement is None:
            print(f'Skipping {name} (not on PyPI and no wheel in Package Control)')
            continue
        requirements.append(requirement)

    REQUIREMENTS_FILE.write_text(''.join(f'{requirement}\n' for requirement in requirements), encoding='utf-8')
    print(f'Wrote {len(requirements)} requirements to {REQUIREMENTS_FILE}')
