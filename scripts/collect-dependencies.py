#!/usr/bin/env python3

"""
Collect the Package Control libraries that the packages in the `repositories` directory depend on.

The checkout-repos.py script does this after cloning. Run this script again after you add or replace a package in
`repositories` yourself.
"""

from __future__ import annotations

from dependencies import collect_dependencies, get_st_version


def main() -> None:
    collect_dependencies(get_st_version())


if __name__ == "__main__":
    main()
