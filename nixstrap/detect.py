"""
Distro and package-format detection from a software repository URL.

Detection strategy (in order):
  1. URL heuristics  — fast, no network needed.
  2. HTTP probing    — confirms the guess by fetching repo metadata files.
  3. Content markers — falls back to examining well-known marker files.
"""

from __future__ import annotations

import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class Distro(Enum):
    """Known Linux distribution families."""

    DEBIAN = "debian"
    UBUNTU = "ubuntu"
    KALI = "kali"
    RASPBIAN = "raspbian"
    FEDORA = "fedora"
    RHEL = "rhel"
    CENTOS = "centos"
    ROCKY = "rocky"
    ALMA = "alma"
    OPENSUSE = "opensuse"
    SLES = "sles"
    ARCH = "arch"
    UNKNOWN = "unknown"


class PackageFormat(Enum):
    """Package formats used by each distro family."""

    DEB = "deb"          # Debian/Ubuntu/Kali family
    RPM = "rpm"          # Red Hat / openSUSE family
    PKG_TAR = "pkg.tar"  # Arch Linux
    TARBALL = "tarball"  # Generic fallback


class BootstrapMethod(Enum):
    """The canonical bootstrap tool for each distro family."""

    DEBOOTSTRAP = "debootstrap"
    DNF = "dnf"
    ZYPPER = "zypper"
    PACSTRAP = "pacstrap"
    TARBALL = "tarball"


@dataclass(frozen=True)
class RepoProfile:
    """Everything nixstrap needs to know about a detected repository."""

    distro: Distro
    package_format: PackageFormat
    bootstrap_method: BootstrapMethod
    nix_packages: tuple[str, ...]   # nixpkgs attribute(s) required at bootstrap time
    codename: Optional[str] = None  # e.g. "bookworm", "39" (Fedora release)

    def describe(self) -> str:
        parts = [f"distro={self.distro.value}", f"format={self.package_format.value}",
                 f"bootstrap={self.bootstrap_method.value}"]
        if self.codename:
            parts.append(f"codename={self.codename}")
        return ", ".join(parts)


# ---------------------------------------------------------------------------
# URL-pattern heuristics
# ---------------------------------------------------------------------------

_DEBIAN_PATTERNS = [
    r"deb\.debian\.org",
    r"ftp\.\w+\.debian\.org",
    r"debian\.org",
    r"mirrors\..*debian",
]

_UBUNTU_PATTERNS = [
    r"archive\.ubuntu\.com",
    r"security\.ubuntu\.com",
    r"ubuntu\.com/ubuntu",
    r"mirrors\..*ubuntu",
]

_KALI_PATTERNS = [r"http\.kali\.org", r"kali\.org"]
_RASPBIAN_PATTERNS = [r"raspbian\.org", r"archive\.raspberrypi"]

_FEDORA_PATTERNS = [
    r"dl\.fedoraproject\.org",
    r"fedoraproject\.org",
    r"mirrors\.fedora",
]

_CENTOS_PATTERNS = [r"vault\.centos\.org", r"centos\.org", r"mirrors\.centos"]
_ROCKY_PATTERNS = [r"dl\.rockylinux\.org", r"rockylinux\.org"]
_ALMA_PATTERNS = [r"repo\.almalinux\.org", r"almalinux\.org"]
_RHEL_PATTERNS = [r"cdn\.redhat\.com", r"redhat\.com"]

_OPENSUSE_PATTERNS = [
    r"download\.opensuse\.org",
    r"mirrors\.opensuse",
    r"opensuse\.org",
]

_SLES_PATTERNS = [r"scc\.suse\.com", r"updates\.suse\.com", r"nu\.novell\.com"]
_ARCH_PATTERNS = [
    r"archive\.archlinux\.org",
    r"geo\.mirror\.pkgbuild\.com",
    r"archlinux\.org",
    r"mirrors\..*arch",
]


def _matches(url: str, patterns: list[str]) -> bool:
    for p in patterns:
        if re.search(p, url, re.IGNORECASE):
            return True
    return False


def _guess_from_url(url: str) -> Optional[Distro]:
    """Return a distro guess based purely on URL patterns, or None."""
    if _matches(url, _KALI_PATTERNS):
        return Distro.KALI
    if _matches(url, _RASPBIAN_PATTERNS):
        return Distro.RASPBIAN
    if _matches(url, _UBUNTU_PATTERNS):
        return Distro.UBUNTU
    if _matches(url, _DEBIAN_PATTERNS):
        return Distro.DEBIAN
    if _matches(url, _RHEL_PATTERNS):
        return Distro.RHEL
    if _matches(url, _CENTOS_PATTERNS):
        return Distro.CENTOS
    if _matches(url, _ROCKY_PATTERNS):
        return Distro.ROCKY
    if _matches(url, _ALMA_PATTERNS):
        return Distro.ALMA
    if _matches(url, _FEDORA_PATTERNS):
        return Distro.FEDORA
    if _matches(url, _SLES_PATTERNS):
        return Distro.SLES
    if _matches(url, _OPENSUSE_PATTERNS):
        return Distro.OPENSUSE
    if _matches(url, _ARCH_PATTERNS):
        return Distro.ARCH
    return None


# ---------------------------------------------------------------------------
# HTTP probing helpers
# ---------------------------------------------------------------------------

_TIMEOUT = 10  # seconds


def _url_exists(url: str) -> bool:
    """Return True if *url* responds with HTTP 2xx."""
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            return resp.status < 300
    except (urllib.error.URLError, OSError):
        return False


def _fetch_text(url: str, max_bytes: int = 8192) -> Optional[str]:
    """Fetch *url* and return the decoded body (truncated), or None on error."""
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            return resp.read(max_bytes).decode("utf-8", errors="replace")
    except (urllib.error.URLError, OSError):
        return None


def _probe_apt(base_url: str) -> bool:
    """Return True if *base_url* looks like an APT repository."""
    url = base_url.rstrip("/")
    # A Release file under dists/ is the canonical APT marker.
    return (
        _url_exists(f"{url}/dists/")
        or _url_exists(f"{url}/InRelease")
        or _url_exists(f"{url}/Release")
    )


def _probe_rpm(base_url: str) -> bool:
    """Return True if *base_url* looks like an RPM repository."""
    url = base_url.rstrip("/")
    return _url_exists(f"{url}/repodata/repomd.xml")


def _probe_arch(base_url: str) -> bool:
    """Return True if *base_url* looks like an Arch Linux repository."""
    url = base_url.rstrip("/")
    # Arch repos expose *.db files at the root.
    for db in ("core.db", "extra.db", "community.db", "x86_64/core.db"):
        if _url_exists(f"{url}/{db}"):
            return True
    return False


def _detect_rpm_variant(base_url: str, url_guess: Optional[Distro]) -> Distro:
    """
    Distinguish openSUSE/SLES from Fedora/CentOS/RHEL by inspecting repomd.xml.
    Falls back to the URL-pattern guess when content is unavailable.
    """
    url = base_url.rstrip("/")
    content = _fetch_text(f"{url}/repodata/repomd.xml")
    if content:
        if re.search(r"opensuse|suse|sles", content, re.IGNORECASE):
            return Distro.OPENSUSE
        if re.search(r"fedora", content, re.IGNORECASE):
            return Distro.FEDORA
        if re.search(r"centos", content, re.IGNORECASE):
            return Distro.CENTOS
        if re.search(r"rocky", content, re.IGNORECASE):
            return Distro.ROCKY
        if re.search(r"alma", content, re.IGNORECASE):
            return Distro.ALMA
    if url_guess and url_guess in (
        Distro.FEDORA, Distro.CENTOS, Distro.ROCKY,
        Distro.ALMA, Distro.RHEL, Distro.OPENSUSE, Distro.SLES,
    ):
        return url_guess
    return Distro.FEDORA  # sensible default for unknown RPM repos


def _detect_apt_variant(base_url: str, url_guess: Optional[Distro]) -> Distro:
    """
    Distinguish Debian variants by checking the Release file.
    Falls back to the URL-pattern guess.
    """
    url = base_url.rstrip("/")
    for candidate in (f"{url}/InRelease", f"{url}/Release"):
        content = _fetch_text(candidate)
        if content:
            if re.search(r"ubuntu", content, re.IGNORECASE):
                return Distro.UBUNTU
            if re.search(r"kali", content, re.IGNORECASE):
                return Distro.KALI
            if re.search(r"raspbian", content, re.IGNORECASE):
                return Distro.RASPBIAN
            if re.search(r"debian", content, re.IGNORECASE):
                return Distro.DEBIAN
    if url_guess and url_guess in (
        Distro.DEBIAN, Distro.UBUNTU, Distro.KALI, Distro.RASPBIAN
    ):
        return url_guess
    return Distro.DEBIAN  # sensible default for unknown APT repos


# ---------------------------------------------------------------------------
# Codename extraction
# ---------------------------------------------------------------------------

def _extract_apt_codename(base_url: str) -> Optional[str]:
    """Try to read the 'Codename:' field from an APT Release file."""
    url = base_url.rstrip("/")
    for candidate in (f"{url}/InRelease", f"{url}/Release"):
        content = _fetch_text(candidate)
        if content:
            m = re.search(r"^Codename:\s*(\S+)", content, re.MULTILINE)
            if m:
                return m.group(1)
    return None


def _extract_rpm_codename(base_url: str) -> Optional[str]:
    """Try to extract a release identifier from an RPM repomd.xml."""
    url = base_url.rstrip("/")
    content = _fetch_text(f"{url}/repodata/repomd.xml")
    if content:
        m = re.search(r'<revision[^>]*>\s*(\d[\w.]*)', content)
        if m:
            return m.group(1)
    return None


# ---------------------------------------------------------------------------
# Distro → RepoProfile mapping
# ---------------------------------------------------------------------------

def _profile_for(distro: Distro, codename: Optional[str] = None) -> RepoProfile:
    """Return the canonical RepoProfile for *distro*."""
    if distro in (Distro.DEBIAN, Distro.UBUNTU, Distro.KALI, Distro.RASPBIAN):
        return RepoProfile(
            distro=distro,
            package_format=PackageFormat.DEB,
            bootstrap_method=BootstrapMethod.DEBOOTSTRAP,
            nix_packages=("debootstrap",),
            codename=codename,
        )
    if distro in (Distro.FEDORA, Distro.RHEL, Distro.CENTOS, Distro.ROCKY, Distro.ALMA):
        return RepoProfile(
            distro=distro,
            package_format=PackageFormat.RPM,
            bootstrap_method=BootstrapMethod.DNF,
            nix_packages=("dnf",),
            codename=codename,
        )
    if distro in (Distro.OPENSUSE, Distro.SLES):
        return RepoProfile(
            distro=distro,
            package_format=PackageFormat.RPM,
            bootstrap_method=BootstrapMethod.ZYPPER,
            nix_packages=("zypper",),
            codename=codename,
        )
    if distro == Distro.ARCH:
        return RepoProfile(
            distro=distro,
            package_format=PackageFormat.PKG_TAR,
            bootstrap_method=BootstrapMethod.PACSTRAP,
            nix_packages=("arch-install-scripts",),
            codename=codename,
        )
    return RepoProfile(
        distro=Distro.UNKNOWN,
        package_format=PackageFormat.TARBALL,
        bootstrap_method=BootstrapMethod.TARBALL,
        nix_packages=("curl", "gnutar"),
        codename=codename,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def detect(repo_url: str, probe: bool = True) -> RepoProfile:
    """
    Detect the distro and package format for *repo_url*.

    Parameters
    ----------
    repo_url:
        The base URL of the software repository (e.g.
        ``http://deb.debian.org/debian``).
    probe:
        When *True* (default) make HTTP requests to confirm the guess.
        Set to *False* for offline/fast detection using URL heuristics only.

    Returns
    -------
    RepoProfile
        A frozen dataclass describing everything nixstrap needs in order to
        choose the right backend and nix packages.
    """
    url_guess = _guess_from_url(repo_url)

    if not probe:
        distro = url_guess or Distro.UNKNOWN
        return _profile_for(distro)

    # --- APT? ---
    if _probe_apt(repo_url):
        distro = _detect_apt_variant(repo_url, url_guess)
        codename = _extract_apt_codename(repo_url)
        return _profile_for(distro, codename)

    # --- RPM? ---
    if _probe_rpm(repo_url):
        distro = _detect_rpm_variant(repo_url, url_guess)
        codename = _extract_rpm_codename(repo_url)
        return _profile_for(distro, codename)

    # --- Arch? ---
    if _probe_arch(repo_url):
        return _profile_for(Distro.ARCH)

    # --- URL heuristic only (probe inconclusive) ---
    distro = url_guess or Distro.UNKNOWN
    return _profile_for(distro)
