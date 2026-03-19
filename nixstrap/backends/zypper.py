"""
openSUSE / SLES backend.

Uses ``zypper`` (provided by Nix) to create a rootfs directory.  This follows
the documented ``zypper --root`` approach used by KIWI and the openSUSE build
service.

Official documentation:
  https://documentation.suse.com/smart/linux/html/concept-zypper/index.html
  https://en.opensuse.org/SDB:Zypper_usage  (--root option)
"""

from __future__ import annotations

import shlex
from pathlib import Path

from nixstrap.backends.base import BaseBackend
from nixstrap.nix import run_in_nix_shell

_DEFAULT_PACKAGES = ("bash", "coreutils", "zypper", "glibc")


class ZypperBackend(BaseBackend):
    """Bootstrap an openSUSE / SLES rootfs with ``zypper --root``."""

    name = "zypper"

    def __init__(
        self,
        repo_url: str,
        target: Path,
        codename: str | None = None,
        packages: tuple[str, ...] | list[str] | None = None,
    ) -> None:
        super().__init__(repo_url, target, codename)
        self.packages = tuple(packages) if packages else _DEFAULT_PACKAGES

    def bootstrap(self) -> None:
        """
        Run the canonical zypper bootstrap sequence::

            nix-shell -p zypper --run \\
                "zypper --root TARGET addrepo REPO_URL nixstrap-repo \\
                 && zypper --root TARGET --gpg-auto-import-keys refresh \\
                 && zypper --root TARGET install --no-confirm PACKAGES..."
        """
        self.prepare_target()

        target_str = shlex.quote(str(self.target))
        repo_str = shlex.quote(self.repo_url)
        pkg_str = " ".join(shlex.quote(p) for p in self.packages)

        command = (
            f"zypper --root {target_str} addrepo {repo_str} nixstrap-repo"
            f" && zypper --root {target_str} --gpg-auto-import-keys refresh"
            f" && zypper --root {target_str} install --no-confirm {pkg_str}"
        )

        run_in_nix_shell(
            packages=("zypper",),
            command=command,
        )
