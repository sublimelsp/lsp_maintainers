from __future__ import annotations

import re

from pep440 import PEP440InvalidVersionError, PEP440Version


class PackageVersion(PEP440Version):
    __slots__ = ["_str"]

    _date_time_regex = re.compile(r"^\d{4}\.\d{2}\.\d{2}(?:\.\d{2}\.\d{2}\.\d{2})?$")

    def __init__(self, ver):
        """
        Initialize a ``PackageVersion`` instance.

        The initializer acts as compatibility layer to convert legacy version schemes
        into a ``PEP440Version``.

        If the version is based on a date, converts to 0.0.1+yyyy.mm.dd.hh.mm.ss.

        :param ver:
            A string, dict with 'version' key, or a SemVer object

        :raises:
            TypeError, if ver is not a ``str``.
            ValueError, if ver is no valid version string
        """

        if not isinstance(ver, str):
            raise TypeError(f"{ver!r} is not a string")

        # Store original version string with `v` trimmed to maintain backward compatibility
        # with regards to not normalize it.
        # The one and only use case is to keep existing CI tests working without change.
        if ver[0] == 'v':
            self._str = ver[1:]
        else:
            self._str = ver

        # We prepend 0 to all date-based version numbers so that developers
        # may switch to explicit versioning from GitHub/GitLab/BitBucket
        # versioning based on commit dates.
        #
        # The resulting semver is alwass 0.0.1 with timestamp being used
        # as build number, so any explicitly choosen version (via tags) will
        # be greater, once a package moves from branch to tag based releases.
        #
        # The result looks like:
        # 0.0.1+2020.07.15.10.50.38
        match = self._date_time_regex.match(ver)
        if match:
            ver = "0.0.1+" + ver

        try:
            super().__init__(ver)
        except PEP440InvalidVersionError:
            # maybe semver with incompatible pre-release tag
            # if, so treat it as dev build with local version
            if "-" in ver:
                ver, pre = ver.split("-", 1)
                if ver and pre:
                    super().__init__(ver + "-dev+" + pre)
                    return
            raise

    def __str__(self):
        return self._str
