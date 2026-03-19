"""
Command-line interface for nixstrap.

Usage::

    nixstrap <repo-url> <target-dir> [options]

nixstrap auto-detects the distro from *repo-url* and bootstraps a rootfs
directory at *target-dir* using the official tooling for that distro — all
supplied on-demand by Nix.
"""

from __future__ import annotations

import sys
from pathlib import Path

import click

from nixstrap import __version__
from nixstrap.detect import detect
from nixstrap.nix import nix_available
from nixstrap.backends.debootstrap import DebootstrapBackend
from nixstrap.backends.dnf import DnfBackend
from nixstrap.backends.zypper import ZypperBackend
from nixstrap.backends.pacstrap import PacstrapBackend
from nixstrap.backends.tarball import TarballBackend
from nixstrap.detect import BootstrapMethod


def _build_backend(profile, repo_url: str, target: Path):
    """Instantiate the correct backend for *profile*."""
    method = profile.bootstrap_method
    if method == BootstrapMethod.DEBOOTSTRAP:
        return DebootstrapBackend(repo_url, target, codename=profile.codename)
    if method == BootstrapMethod.DNF:
        return DnfBackend(repo_url, target, codename=profile.codename)
    if method == BootstrapMethod.ZYPPER:
        return ZypperBackend(repo_url, target, codename=profile.codename)
    if method == BootstrapMethod.PACSTRAP:
        return PacstrapBackend(repo_url, target, codename=profile.codename)
    return TarballBackend(repo_url, target, codename=profile.codename)


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.argument("repo_url")
@click.argument("target", type=click.Path(file_okay=False, path_type=Path))
@click.option(
    "--no-probe",
    is_flag=True,
    default=False,
    help="Skip HTTP probing; use URL-pattern detection only (faster, offline).",
)
@click.option(
    "--codename",
    default=None,
    metavar="NAME",
    help="Override the distro codename / release detected from the repo "
         "(e.g. 'bookworm', '39').",
)
@click.version_option(__version__, "-V", "--version")
def main(repo_url: str, target: Path, no_probe: bool, codename: str | None) -> None:
    """
    Bootstrap a Linux rootfs directory from any distro's software repository.

    \b
    REPO_URL   Base URL of the software repository to bootstrap from.
    TARGET     Directory that will become the rootfs (created if absent).

    \b
    Examples:
      nixstrap http://deb.debian.org/debian        /mnt/rootfs
      nixstrap https://dl.fedoraproject.org/pub/fedora/linux/releases/39/Everything/x86_64/os/ /mnt/rootfs
      nixstrap https://download.opensuse.org/distribution/leap/15.5/repo/oss/ /mnt/rootfs
      nixstrap https://geo.mirror.pkgbuild.com/    /mnt/rootfs
    """
    if not nix_available():
        click.echo(
            "error: Nix is not installed or not on PATH.\n"
            "       Install it from https://nixos.org/download and try again.",
            err=True,
        )
        sys.exit(1)

    click.echo(f"nixstrap {__version__}  repo={repo_url}  target={target}")

    probe = not no_probe
    click.echo(f"  Detecting distro from repo {'(URL heuristics only)' if no_probe else '(probing repo)'}…")
    profile = detect(repo_url, probe=probe)

    # Allow --codename to override what was detected.
    if codename:
        from dataclasses import replace
        profile = replace(profile, codename=codename)  # type: ignore[call-arg]

    click.echo(f"  Detected: {profile.describe()}")
    click.echo(f"  Nix packages needed: {', '.join(profile.nix_packages)}")
    click.echo(f"  Bootstrap tool: {profile.bootstrap_method.value}")
    click.echo(f"  Target directory: {target}")

    backend = _build_backend(profile, repo_url, target)

    click.echo(f"\nStarting bootstrap with backend '{backend.name}'…")
    backend.bootstrap()
    click.echo(f"\nDone.  Rootfs is at {target}")
