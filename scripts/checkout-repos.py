#!/usr/bin/env python3

from __future__ import annotations

import argparse
import re
import subprocess
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

from utils import get_all_packages

ST4_WEB_URL = 'https://www.sublimetext.com/download_thanks'
SCRIPT_DIR = Path(__file__).resolve().parent



def download_st4(target_dir: Path) -> int:
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


def run_subprocess(args: 'list[str]', *, cwd: Path) -> None:
    subprocess.run(args, check=True, cwd=cwd)  # noqa: S607


def clone_repository(repo_url: str, name: str, *, target_dir: Path) -> None:
    print(f'Cloning {name}...')
    package_dir = target_dir / name
    if not package_dir.is_dir():
        run_subprocess(["git", "clone", "--depth=1", repo_url, name], cwd=target_dir)
    else:
        run_subprocess(['git', 'reset', '--hard'], cwd=package_dir)
        run_subprocess(['git', 'pull'], cwd=package_dir)


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
    return parser.parse_args()


def main():
    args = parse_args()
    excluded: set[str] = set(args.exclude)

    try:
        repositories_dir = SCRIPT_DIR.parent / 'repositories'

        st_version = download_st4(repositories_dir)

        for p in get_all_packages(st_version):
            package_name: str = p["name"]
            if package_name in excluded:
                print(f"Skipping {package_name} (excluded)")
                continue
            repo_url: str = p["details"]
            clone_repository(repo_url, package_name, target_dir=repositories_dir)

        if 'lsp_utils' not in excluded:
            clone_repository('https://github.com/sublimelsp/lsp_utils.git', 'lsp_utils', target_dir=repositories_dir)
        if 'sublime_aio' not in excluded:
            clone_repository('https://github.com/packagecontrol/sublime_aio.git', 'sublime_aio', target_dir=repositories_dir)
        if 'sublime_lib' not in excluded:
            clone_repository('https://github.com/SublimeText/sublime_lib.git', 'sublime_lib', target_dir=repositories_dir)
            run_subprocess(['rm', '-rf', 'sublime_lib/stubs'], cwd=repositories_dir)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
