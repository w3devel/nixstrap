"""
Tests for nixstrap.detect — distro/repo auto-detection.

All network calls are mocked so these tests run completely offline.
"""

from __future__ import annotations

import urllib.error
from unittest.mock import patch, MagicMock

import pytest

from nixstrap.detect import (
    Distro,
    PackageFormat,
    BootstrapMethod,
    detect,
    _guess_from_url,
    _profile_for,
)


# ---------------------------------------------------------------------------
# URL heuristic tests (_guess_from_url)
# ---------------------------------------------------------------------------

class TestGuessFromUrl:
    def test_debian_org(self):
        assert _guess_from_url("http://deb.debian.org/debian") == Distro.DEBIAN

    def test_ubuntu_archive(self):
        assert _guess_from_url("http://archive.ubuntu.com/ubuntu") == Distro.UBUNTU

    def test_kali(self):
        assert _guess_from_url("http://http.kali.org/kali") == Distro.KALI

    def test_raspbian(self):
        assert _guess_from_url("http://raspbian.org/raspbian") == Distro.RASPBIAN

    def test_fedora(self):
        assert _guess_from_url(
            "https://dl.fedoraproject.org/pub/fedora/linux/releases/39/Everything/x86_64/os/"
        ) == Distro.FEDORA

    def test_centos(self):
        assert _guess_from_url("http://vault.centos.org/8/BaseOS/x86_64/os/") == Distro.CENTOS

    def test_rocky(self):
        assert _guess_from_url("https://dl.rockylinux.org/pub/rocky/9/BaseOS/x86_64/os/") == Distro.ROCKY

    def test_alma(self):
        assert _guess_from_url("https://repo.almalinux.org/almalinux/9/BaseOS/x86_64/os/") == Distro.ALMA

    def test_opensuse(self):
        assert _guess_from_url(
            "https://download.opensuse.org/distribution/leap/15.5/repo/oss/"
        ) == Distro.OPENSUSE

    def test_arch(self):
        assert _guess_from_url("https://geo.mirror.pkgbuild.com/") == Distro.ARCH

    def test_unknown(self):
        assert _guess_from_url("https://example.com/myrepo") is None


# ---------------------------------------------------------------------------
# _profile_for
# ---------------------------------------------------------------------------

class TestProfileFor:
    def test_debian_profile(self):
        p = _profile_for(Distro.DEBIAN, codename="bookworm")
        assert p.package_format == PackageFormat.DEB
        assert p.bootstrap_method == BootstrapMethod.DEBOOTSTRAP
        assert "debootstrap" in p.nix_packages
        assert p.codename == "bookworm"

    def test_ubuntu_profile(self):
        p = _profile_for(Distro.UBUNTU)
        assert p.package_format == PackageFormat.DEB
        assert p.bootstrap_method == BootstrapMethod.DEBOOTSTRAP

    def test_fedora_profile(self):
        p = _profile_for(Distro.FEDORA, codename="39")
        assert p.package_format == PackageFormat.RPM
        assert p.bootstrap_method == BootstrapMethod.DNF
        assert "dnf" in p.nix_packages

    def test_centos_profile(self):
        p = _profile_for(Distro.CENTOS)
        assert p.bootstrap_method == BootstrapMethod.DNF

    def test_rocky_profile(self):
        p = _profile_for(Distro.ROCKY)
        assert p.bootstrap_method == BootstrapMethod.DNF

    def test_alma_profile(self):
        p = _profile_for(Distro.ALMA)
        assert p.bootstrap_method == BootstrapMethod.DNF

    def test_opensuse_profile(self):
        p = _profile_for(Distro.OPENSUSE)
        assert p.package_format == PackageFormat.RPM
        assert p.bootstrap_method == BootstrapMethod.ZYPPER
        assert "zypper" in p.nix_packages

    def test_sles_profile(self):
        p = _profile_for(Distro.SLES)
        assert p.bootstrap_method == BootstrapMethod.ZYPPER

    def test_arch_profile(self):
        p = _profile_for(Distro.ARCH)
        assert p.package_format == PackageFormat.PKG_TAR
        assert p.bootstrap_method == BootstrapMethod.PACSTRAP
        assert "arch-install-scripts" in p.nix_packages

    def test_unknown_profile(self):
        p = _profile_for(Distro.UNKNOWN)
        assert p.package_format == PackageFormat.TARBALL
        assert p.bootstrap_method == BootstrapMethod.TARBALL


# ---------------------------------------------------------------------------
# detect() — offline mode (probe=False)
# ---------------------------------------------------------------------------

class TestDetectOffline:
    """detect() with probe=False should rely on URL heuristics only."""

    def test_debian_offline(self):
        p = detect("http://deb.debian.org/debian", probe=False)
        assert p.distro == Distro.DEBIAN
        assert p.bootstrap_method == BootstrapMethod.DEBOOTSTRAP

    def test_ubuntu_offline(self):
        p = detect("http://archive.ubuntu.com/ubuntu", probe=False)
        assert p.distro == Distro.UBUNTU

    def test_fedora_offline(self):
        p = detect(
            "https://dl.fedoraproject.org/pub/fedora/linux/releases/39/Everything/x86_64/os/",
            probe=False,
        )
        assert p.distro == Distro.FEDORA
        assert p.bootstrap_method == BootstrapMethod.DNF

    def test_opensuse_offline(self):
        p = detect(
            "https://download.opensuse.org/distribution/leap/15.5/repo/oss/",
            probe=False,
        )
        assert p.distro == Distro.OPENSUSE
        assert p.bootstrap_method == BootstrapMethod.ZYPPER

    def test_arch_offline(self):
        p = detect("https://geo.mirror.pkgbuild.com/", probe=False)
        assert p.distro == Distro.ARCH
        assert p.bootstrap_method == BootstrapMethod.PACSTRAP

    def test_unknown_offline(self):
        p = detect("https://example.com/myrepo", probe=False)
        assert p.distro == Distro.UNKNOWN
        assert p.bootstrap_method == BootstrapMethod.TARBALL


# ---------------------------------------------------------------------------
# detect() — online mode with mocked HTTP
# ---------------------------------------------------------------------------

def _mock_urlopen_apt(url, timeout=10):
    """Mock that simulates an APT repo by returning 200 for dists/."""
    resp = MagicMock()
    resp.__enter__ = lambda s: s
    resp.__exit__ = MagicMock(return_value=False)
    resp.status = 200
    resp.read.return_value = b"Codename: bookworm\nOrigin: Debian\n"
    return resp


def _mock_urlopen_rpm_fedora(url, timeout=10):
    resp = MagicMock()
    resp.__enter__ = lambda s: s
    resp.__exit__ = MagicMock(return_value=False)
    resp.status = 200
    resp.read.return_value = b'<repomd><revision>39</revision><tags>Fedora</tags></repomd>'
    return resp


def _make_404():
    """Return a callable that raises HTTPError(404) every time."""
    def _raise(*args, **kwargs):
        raise urllib.error.HTTPError(url="", code=404, msg="Not Found", hdrs=None, fp=None)
    return _raise


class TestDetectOnline:
    """detect() with probe=True using mocked urllib.request.urlopen."""

    @patch("nixstrap.detect.urllib.request.urlopen")
    def test_apt_repo_detected(self, mock_urlopen):
        mock_urlopen.side_effect = _mock_urlopen_apt
        p = detect("http://deb.debian.org/debian", probe=True)
        assert p.package_format == PackageFormat.DEB
        assert p.bootstrap_method == BootstrapMethod.DEBOOTSTRAP

    @patch("nixstrap.detect.urllib.request.urlopen")
    def test_apt_repo_codename_extracted(self, mock_urlopen):
        mock_urlopen.side_effect = _mock_urlopen_apt
        p = detect("http://deb.debian.org/debian", probe=True)
        assert p.codename == "bookworm"

    @patch("nixstrap.detect.urllib.request.urlopen")
    def test_rpm_fedora_detected(self, mock_urlopen):
        """When repodata/repomd.xml is present and mentions Fedora → DNF backend."""
        call_count = [0]

        def side_effect(req, timeout=10):
            call_count[0] += 1
            url = req.full_url if hasattr(req, "full_url") else str(req)
            # Deny APT probes
            if "dists" in url or "InRelease" in url or "Release" in url:
                raise urllib.error.HTTPError(url=url, code=404, msg="Not Found", hdrs=None, fp=None)
            # Allow repomd.xml
            resp = MagicMock()
            resp.__enter__ = lambda s: s
            resp.__exit__ = MagicMock(return_value=False)
            resp.status = 200
            resp.read.return_value = b'<repomd><revision>39</revision><tags>fedora</tags></repomd>'
            return resp

        mock_urlopen.side_effect = side_effect
        p = detect(
            "https://dl.fedoraproject.org/pub/fedora/linux/releases/39/Everything/x86_64/os/",
            probe=True,
        )
        assert p.package_format == PackageFormat.RPM
        assert p.bootstrap_method == BootstrapMethod.DNF

    @patch("nixstrap.detect.urllib.request.urlopen")
    def test_all_probes_fail_falls_back_to_url_heuristic(self, mock_urlopen):
        """When all HTTP probes fail, URL heuristics are used."""
        mock_urlopen.side_effect = urllib.error.URLError("connection refused")
        p = detect("http://deb.debian.org/debian", probe=True)
        # URL heuristic correctly identifies debian
        assert p.distro == Distro.DEBIAN
        assert p.bootstrap_method == BootstrapMethod.DEBOOTSTRAP

    @patch("nixstrap.detect.urllib.request.urlopen")
    def test_completely_unknown_repo(self, mock_urlopen):
        mock_urlopen.side_effect = urllib.error.URLError("connection refused")
        p = detect("https://example.com/myrepo", probe=True)
        assert p.distro == Distro.UNKNOWN
        assert p.bootstrap_method == BootstrapMethod.TARBALL


# ---------------------------------------------------------------------------
# RepoProfile.describe()
# ---------------------------------------------------------------------------

class TestRepoProfileDescribe:
    def test_describe_includes_distro(self):
        p = _profile_for(Distro.DEBIAN, codename="bookworm")
        desc = p.describe()
        assert "debian" in desc
        assert "debootstrap" in desc
        assert "bookworm" in desc

    def test_describe_without_codename(self):
        p = _profile_for(Distro.FEDORA)
        desc = p.describe()
        assert "codename" not in desc
