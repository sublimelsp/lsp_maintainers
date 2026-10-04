#!/usr/bin/env python3

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import tarfile
import tempfile
import urllib.parse
import urllib.request
import zipfile
from collections.abc import Generator
from pathlib import Path

from dependencies import collect_dependencies
from package_version import PackageVersion, version_match_prefix
from utils import get_lsp_packages_and_dependencies

ST4_WEB_URL = 'https://www.sublimetext.com/download_thanks'
SCRIPT_DIR = Path(__file__).resolve().parent



def download_latest_sublime_text(target_dir: Path) -> int:
    with urllib.request.urlopen(urllib.request.Request(ST4_WEB_URL, headers={'User-Agent': 'Mozilla/5.0'})) as resp:
        html = resp.read().decode('utf-8', errors='replace')
    match = re.search(r'href="([^"]*_(\d+)_mac\.zip)"', html)
    if match:
        st_version = int(match.group(2))
        zip_url = urllib.parse.urljoin(ST4_WEB_URL, match.group(1))
        print(f"Downloading {zip_url} ...")
        filepath, _ = urllib.request.urlretrieve(zip_url)
        print(f"Extracting {filepath} ...")
        with zipfile.ZipFile(filepath, 'r') as zf:
            zf.extractall(target_dir)
            print(f"Build {st_version} downloaded")
        Path(filepath).unlink()
        return st_version
    else:
        raise RuntimeError('Failed to found link to the latest version of Sublime Text')


def run_subprocess(args: list[str], *, cwd: Path, check: bool = True) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(args, check=check, cwd=cwd)


def export_git_archive(source_dir: Path, package_dir: Path) -> None:
    """Replace the contents of package_dir with a git archive export of HEAD of source_dir.

    This filters out anything marked as export-ignore in .gitattributes and
    removes the .git directory, leaving a clean export in place. The source_dir
    can be package_dir itself.
    """
    # LSP export-ignores its stubs, so copy them to the shared stubs directory before the export.
    stubs_dir = source_dir / 'stubs'
    if package_dir.name == 'LSP' and stubs_dir.is_dir():
        target_stubs_dir = package_dir.parent / 'stubs'
        if target_stubs_dir.is_dir():
            shutil.rmtree(target_stubs_dir)
        shutil.copytree(stubs_dir, target_stubs_dir)
    with tempfile.NamedTemporaryFile(suffix='.tar', delete=False) as tmp:
        tmp_path = Path(tmp.name)
    try:
        run_subprocess(['git', 'archive', '--output', str(tmp_path), 'HEAD'], cwd=source_dir)
        if package_dir.is_dir():
            shutil.rmtree(package_dir)
        package_dir.mkdir()
        with tarfile.open(tmp_path) as tar:
            tar.extractall(package_dir)
    finally:
        tmp_path.unlink(missing_ok=True)


def git_clone(repo_url: str, name: str, *, target_dir: Path, branch: str | None = None) -> None:
    """Shallow-clone the repository."""
    # Cloning a tag checks out a detached HEAD, so turn off the related advice.
    args = ['git', '-c', 'advice.detachedHead=false', 'clone', '--quiet', '--depth=1']
    if branch is not None:
        args += ['--branch', branch]
    run_subprocess([*args, repo_url, name], cwd=target_dir)


def clone_repository(repo_url: str, name: str, tag_prefix: str | None, *, target_dir: Path, branch_override: str | None = None) -> None:
    branches, tags = fetch_remote_refs(repo_url)
    latest_release = next(get_sorted_releases(tags, tag_prefix), None)
    print(f'Cloning {name}...')
    package_dir = target_dir / name
    if package_dir.is_dir():
        shutil.rmtree(package_dir)
    if branch_override is not None and branch_override in branches:
        git_clone(repo_url, name, target_dir=target_dir, branch=branch_override)
        print(f'-> Cloned branch {branch_override!r}')
    else:
        if branch_override is not None:
            print(f'-> Branch {branch_override!r} not found, falling back to latest release')
        clone_release_or_default(repo_url, name, latest_release, target_dir=target_dir)
    export_git_archive(package_dir, package_dir)


def export_local_repository(name: str, source_dir: Path, *, target_dir: Path) -> None:
    """Export HEAD of a local repository in place of the latest release."""
    print(f'Exporting {name} from {source_dir}...')
    export_git_archive(source_dir, target_dir / name)
    result = subprocess.run(
        ['git', 'rev-parse', '--abbrev-ref', 'HEAD'], check=True, capture_output=True, text=True, cwd=source_dir
    )
    print(f'-> Exported {result.stdout.strip()!r}')


def fetch_remote_refs(repo_url: str) -> tuple[set[str], list[str]]:
    """Return the branch names and tag names of the remote repository without cloning it."""
    result = subprocess.run(
        ['git', 'ls-remote', '--heads', '--tags', '--refs', repo_url],
        check=True, capture_output=True, text=True,
    )
    branches: set[str] = set()
    tags: list[str] = []
    # Each line looks like: "<sha>\trefs/<heads|tags>/<name>". --refs drops the peeled "^{}" entries.
    for line in result.stdout.splitlines():
        ref = line.split('\t', 1)[1]
        if ref.startswith('refs/heads/'):
            branches.add(ref.removeprefix('refs/heads/'))
        elif ref.startswith('refs/tags/'):
            tags.append(ref.removeprefix('refs/tags/'))
    return branches, tags


def get_sorted_releases(tags: list[str], tag_prefix: str | None) -> Generator[tuple[PackageVersion, str]]:
    used_versions = set()
    releases: list[tuple[PackageVersion, str]] = []
    for tag in tags:
        version = version_match_prefix(tag, tag_prefix)
        if version and version not in used_versions:
            used_versions.add(version)
            releases.append((version, tag))
    yield from sorted(releases, key=lambda r: r[0], reverse=True)

def clone_release_or_default(repo_url: str, name: str, latest_release: tuple[PackageVersion, str] | None, *, target_dir: Path) -> None:
    """Clone the latest release tag, or the default branch when there are no releases."""
    if latest_release:
        tag = latest_release[1]
        git_clone(repo_url, name, target_dir=target_dir, branch=tag)
        print(f'-> Cloned latest release tag {tag!r}')
    else:
        print('-> Warning: No releases found, falling back to default branch')
        git_clone(repo_url, name, target_dir=target_dir)


def parse_local_package(value: str) -> tuple[str, Path]:
    name, separator, path = value.partition('=')
    if not name or not separator or not path:
        raise argparse.ArgumentTypeError(f'expected NAME=PATH, got {value!r}')
    source_dir = Path(path).expanduser().resolve()
    if not (source_dir / '.git').exists():
        raise argparse.ArgumentTypeError(f'{source_dir} is not a git repository')
    return name, source_dir


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Clone or update all LSP-related repositories for local development.",
    )
    parser.add_argument(
        "--exclude",
        metavar="NAME",
        action="append",
        default=[],
        help="Package name to skip. Can be repeated (e.g. --exclude LSP-typescript --exclude LSP-eslint).",
    )
    parser.add_argument(
        "--only",
        metavar="NAME",
        action="append",
        default=[],
        help="Check out only the package NAME and LSP, which all packages depend on. Removes the other packages from "
        "earlier runs. Can be repeated (e.g. --only LSP-pyright --local LSP-pyright=.).",
    )
    parser.add_argument(
        "--preferred-branch",
        metavar="BRANCH",
        default=None,
        dest="branch",
        help="Branch to check out in every repository after cloning. Falls back to the default branch if not found.",
    )
    parser.add_argument(
        "--local",
        metavar="NAME=PATH",
        action="append",
        default=[],
        type=parse_local_package,
        help="Export HEAD of the local git repository PATH as the package or LSP dependency NAME instead of using the "
        "latest release. Can be repeated (e.g. --local LSP=../LSP --local lsp_utils=../lsp_utils).",
    )
    parser.add_argument(
        "--no-collect-dependencies",
        action="store_true",
        help="Do not collect the dependencies of the packages into repositories/requirements-packages.txt. Use this "
        "option if you replace packages after the checkout, and then run collect-dependencies.py.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    excluded: set[str] = set(args.exclude)
    local_packages: dict[str, Path] = dict(args.local)

    try:
        repositories_dir = SCRIPT_DIR.parent / 'repositories'

        st_version = download_latest_sublime_text(repositories_dir)

        packages, dependency_names = get_lsp_packages_and_dependencies(st_version)
        package_names = {p["name"] for p in packages}
        if unknown_names := set(args.only) - package_names:
            raise SystemExit(f"Error: --only names unknown packages: {', '.join(sorted(unknown_names))}")
        selected_names = {*args.only, 'LSP'} if args.only else package_names
        for name in local_packages.keys() - package_names - dependency_names:
            print(f"Warning: {name} is not a package or an LSP dependency, ignoring --local {name}")

        for p in packages:
            package_name: str = p["name"]
            if package_name not in selected_names:
                package_dir = repositories_dir / package_name
                if package_dir.is_dir():
                    print(f"Removing {package_name} (not selected by --only)")
                    shutil.rmtree(package_dir)
                continue
            if package_name in local_packages:
                export_local_repository(package_name, local_packages[package_name], target_dir=repositories_dir)
                continue
            if package_name in excluded:
                print(f"Skipping {package_name} (excluded)")
                continue
            repo_url: str = p["details"]
            tag_prefix = p["tag_prefix"]
            clone_repository(repo_url, package_name, tag_prefix, target_dir=repositories_dir, branch_override=args.branch)

        # A dependency is installed from its wheel (see collect_dependencies), unless it is exported from a local
        # repository. Remove an export of an earlier run, because it would replace the wheel.
        for name in sorted(dependency_names):
            dependency_dir = repositories_dir / name
            if name in local_packages:
                export_local_repository(name, local_packages[name], target_dir=repositories_dir)
            elif dependency_dir.is_dir():
                print(f"Removing {name} (exported by an earlier run)")
                shutil.rmtree(dependency_dir)

        if not args.no_collect_dependencies:
            collect_dependencies(st_version)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
