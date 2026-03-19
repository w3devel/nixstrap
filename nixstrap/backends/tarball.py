"""
Generic tarball backend — fallback for unknown or tarball-based repos.

Downloads a tarball from the supplied URL and extracts it into the target
directory.  ``curl`` and ``tar`` are provided by Nix so the host does not need
them pre-installed.
"""

from __future__ import annotations

import shlex
from pathlib import Path

from nixstrap.backends.base import BaseBackend
from nixstrap.nix import run_in_nix_shell


class TarballBackend(BaseBackend):
    """Extract a tarball from *repo_url* into *target*."""

    name = "tarball"

    def bootstrap(self) -> None:
        """
        Run::

            nix-shell -p curl -p tar --run \\
                "curl -fsSL REPO_URL | tar -xz --strip-components=1 -C TARGET"
        """
        self.prepare_target()

        target_str = shlex.quote(str(self.target))
        repo_str = shlex.quote(self.repo_url)

        command = (
            f"curl -fsSL {repo_str} "
            f"| tar -xz --strip-components=1 -C {target_str}"
        )

        run_in_nix_shell(
            packages=("curl", "gnutar"),
            command=command,
        )
