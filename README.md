# nixstrap

A modern replacement for Debootstrap, Pacstrap, tarballs, and package managers
to create a rootfs directory using **Nix** and any Unix/Linux software
repository.

nixstrap works like VLC with FFmpeg: just as VLC wraps FFmpeg commands to add
features on top of them, nixstrap wraps `nix-shell`/`nix run` calls to provide
each distro's official bootstrap tooling **on demand** — without requiring
`debootstrap`, `dnf`, `zypper`, or `pacstrap` to be pre-installed on the host.

---

## How it works

1. **You supply a repo URL** — nixstrap inspects it (HTTP probe + URL-pattern
   heuristics) to detect the distro and package format automatically.
2. **nixstrap picks the right tool** — Debian/Ubuntu → `debootstrap`, Fedora/RHEL
   → `dnf --installroot`, openSUSE/SLES → `zypper --root`, Arch Linux →
   `pacstrap`.
3. **Nix provides the tool** — nixstrap calls `nix-shell -p <tool>` so the
   bootstrap program is fetched by Nix at runtime.  Your host only needs Nix.
4. **A rootfs directory is created** — ready to chroot into, package into an
   image, or containerise (future feature).

```
nixstrap <repo-url> <target-dir>
```

---

## Requirements

* [Nix](https://nixos.org/download) (any version with `nix-shell` on `$PATH`)
* Python ≥ 3.10

---

## Installation

### Via Nix flake (recommended)

```sh
nix run github:w3devel/nixstrap -- <repo-url> <target-dir>
```

Or install permanently:

```sh
nix profile install github:w3devel/nixstrap
```

### Via pip

```sh
pip install nixstrap
```

---

## Usage

```
Usage: nixstrap [OPTIONS] REPO_URL TARGET

  Bootstrap a Linux rootfs directory from any distro's software repository.

  REPO_URL   Base URL of the software repository to bootstrap from.
  TARGET     Directory that will become the rootfs (created if absent).

Options:
  --no-probe       Skip HTTP probing; use URL-pattern detection only
                   (faster, offline).
  --codename NAME  Override the detected distro codename / release
                   (e.g. 'bookworm', '39').
  -V, --version    Show the version and exit.
  -h, --help       Show this message and exit.
```

### Examples

```sh
# Debian (bookworm auto-detected from repo metadata)
nixstrap http://deb.debian.org/debian /mnt/rootfs

# Ubuntu
nixstrap http://archive.ubuntu.com/ubuntu /mnt/rootfs --codename noble

# Fedora 39
nixstrap https://dl.fedoraproject.org/pub/fedora/linux/releases/39/Everything/x86_64/os/ /mnt/rootfs

# openSUSE Leap 15.5
nixstrap https://download.opensuse.org/distribution/leap/15.5/repo/oss/ /mnt/rootfs

# Arch Linux
nixstrap https://geo.mirror.pkgbuild.com/ /mnt/rootfs

# Fast offline detection (skip HTTP repo probe)
nixstrap http://deb.debian.org/debian /mnt/rootfs --no-probe
```

---

## Supported distros

| Distro family                              | Bootstrap tool        | Package format | Nix package            |
|--------------------------------------------|-----------------------|----------------|------------------------|
| Debian / Ubuntu / Kali / Raspbian          | `debootstrap`         | `.deb`         | `debootstrap`          |
| Fedora / RHEL / CentOS / Rocky / Alma      | `dnf --installroot`   | `.rpm`         | `dnf`                  |
| openSUSE / SLES                            | `zypper --root`       | `.rpm`         | `zypper`               |
| Arch Linux                                 | `pacstrap`            | `.pkg.tar`     | `arch-install-scripts` |
| Generic / Unknown                          | `curl \| tar`         | tarball        | `curl`, `gnutar`       |

---

## Architecture

```
nixstrap/
├── nixstrap/
│   ├── cli.py          # Click-based CLI entry point
│   ├── detect.py       # Repo/distro detection (URL heuristics + HTTP probing)
│   ├── nix.py          # Nix integration layer (nix-shell / nix run wrappers)
│   └── backends/
│       ├── base.py          # Abstract BaseBackend
│       ├── debootstrap.py   # Debian/Ubuntu backend
│       ├── dnf.py           # Fedora/RHEL/CentOS/Rocky/Alma backend
│       ├── zypper.py        # openSUSE/SLES backend
│       ├── pacstrap.py      # Arch Linux backend
│       └── tarball.py       # Generic tarball fallback
├── tests/              # pytest test suite (all offline, network/nix mocked)
├── flake.nix           # Nix flake for building/running nixstrap itself
└── pyproject.toml
```

### Using Nix as the foundation

nixstrap calls `nix-shell -p <tool> --run <command>` for every bootstrap
operation.  This is intentional:

* **No pre-installed tools required** — the host only needs Nix.
* **Reproducibility** — Nix pins exact versions of every bootstrap tool.
* **Future extensibility** — additional Nix primitives (`nix build`,
  `nix store`, etc.) can be layered on to produce images, OCI containers,
  VM disks, and more in future releases.

---

## Development

```sh
# Enter dev shell
nix develop

# Or install dev dependencies via pip
pip install -e ".[dev]"

# Run tests
pytest
```

---

## Roadmap

* [x] Core: detect distro from repo URL and bootstrap rootfs directory
* [ ] Image output: produce raw/qcow2/vmdk images via `nix build`
* [ ] Container output: export as OCI / Docker / Podman images
* [ ] Cross-architecture bootstrapping (`--arch`)
* [ ] Custom package lists via config file
