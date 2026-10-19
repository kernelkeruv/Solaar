#!/usr/bin/env bash
# Fedora/RHEL-family Solaar installation helper.
# Safe default: observation only. Never modifies host security policy.
set -Eeuo pipefail

usage() {
  cat <<'USAGE'
Usage: tools/install-rhel.sh [--check | --install | --source] [--dry-run]
  --check    Read-only environment and package diagnostics (default)
  --install  Install distro packages using dnf (preferred on Fedora)
  --source   Install this checkout in an isolated, system-site-packages venv
  --dry-run  Print mutating commands without executing them
  --help     Show this help

--source does not clone, pull, edit shell rc files, or change udev rules.
Review the repository and use a trusted checkout before running --source.
USAGE
}
mode=check
dry_run=0
selected=0
while (($#)); do
  case "$1" in
    --check|--install|--source)
      ((selected == 0)) || { echo "Choose one mode only" >&2; exit 2; }
      mode="${1#--}"; selected=1 ;;
    --dry-run) dry_run=1 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
  shift
done

note() { printf '%s\n' "$*"; }
warn() { printf 'WARNING: %s\n' "$*" >&2; }
need() { command -v "$1" >/dev/null 2>&1 || { echo "Missing command: $1" >&2; exit 1; }; }
run() {
  if ((dry_run)); then
    printf 'DRY RUN:'
    printf ' %q' "$@"
    printf '\n'
  else
    "$@"
  fi
}

[[ -r /etc/os-release ]] || { echo "Missing /etc/os-release" >&2; exit 1; }
# /etc/os-release is supplied by the operating system.
# shellcheck disable=SC1091
source /etc/os-release
os_id="${ID:-unknown}"
os_family=" ${ID_LIKE:-} "
case "$os_id" in
  fedora|rhel|centos|rocky|almalinux|ol) : ;;
  *) if [[ "$os_family" != *" rhel "* && "$os_family" != *" fedora "* ]]; then
       if [[ "$mode" != check ]]; then
         echo "Unsupported distro ($os_id); refusing package changes." >&2
         exit 1
       fi
       warn "Detected $os_id, not a verified Fedora/RHEL family distribution."
     fi ;;
esac

if [[ "$mode" == check ]]; then
  note "Distribution: ${PRETTY_NAME:-$os_id}"
  note "Solaar executable: $(command -v solaar || printf 'not found')"
  if command -v rpm >/dev/null 2>&1; then
    rpm -q solaar solaar-udev || true
  fi
  if [[ -f /etc/udev/rules.d/42-logitech-unify-permissions.rules ]]; then
    warn "Local /etc udev rule exists; inspect for vendor-rule shadowing."
  elif [[ -f /usr/lib/udev/rules.d/42-logitech-unify-permissions.rules ]]; then
    note "Packaged udev rule found in /usr/lib/udev/rules.d"
  else
    warn "No known Solaar udev rule found."
  fi
  if [[ -r /proc/sys/crypto/fips_enabled ]]; then
    read -r kernel_fips < /proc/sys/crypto/fips_enabled || kernel_fips="unknown"
    note "Kernel FIPS flag: $kernel_fips (not a compliance attestation)"
  fi
  if command -v update-crypto-policies >/dev/null 2>&1; then
    note "Crypto policy: $(update-crypto-policies --show 2>/dev/null || printf 'unavailable')"
  fi
  if command -v getenforce >/dev/null 2>&1; then
    note "SELinux: $(getenforce 2>/dev/null || printf 'unavailable')"
  fi
  note "No changes made. Fedora FIPS mode does not imply CMVP validation."
  exit 0
fi

if (( !dry_run )); then
  need dnf
  need sudo
  if (( EUID == 0 )); then
    echo "Run as an ordinary user; do not invoke this installer as root." >&2
    exit 1
  fi
fi

if [[ "$mode" == install ]]; then
  note "Installing distribution packages; dnf will request confirmation."
  run sudo dnf install solaar solaar-udev
  if ((!dry_run)); then
    note "Installed package versions:"
    rpm -q solaar solaar-udev
  fi
  exit 0
fi

# Source/development build. Fedora's Python is externally managed: never pip
# into the system interpreter and never bypass PEP 668.
if ((!dry_run)); then need python3; fi
repo="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
[[ -f "$repo/setup.py" && -f "$repo/lib/solaar/version" ]] || {
  echo "Installer must run from a valid Solaar checkout." >&2; exit 1;
}
venv="${XDG_DATA_HOME:-$HOME/.local/share}/solaar-dev/venv"
[[ ! -L "$venv" ]] || { echo "Refusing symlinked venv path: $venv" >&2; exit 1; }
if [[ -e "$venv" && ! -f "$venv/pyvenv.cfg" ]]; then
  echo "Refusing to overwrite non-venv path: $venv" >&2; exit 1
fi

note "Source checkout: $repo"
note "Virtual environment: $venv"
note "Using packaged Python/GTK/DBus dependencies. No PyPI downloads."
run sudo dnf install python3 python3-pip python3-setuptools python3-wheel \
  python3-dbus python3-gobject python3-evdev python3-psutil \
  python3-pyudev python3-pyyaml python3-xlib solaar-udev

if ((!dry_run)); then
  umask 077
  mkdir -p -- "$(dirname -- "$venv")"
fi
if [[ ! -f "$venv/pyvenv.cfg" ]]; then
  run python3 -m venv --system-site-packages "$venv"
fi
run "$venv/bin/python" -m pip install --no-index --no-deps \
  --no-build-isolation --editable "$repo"
if ((!dry_run)); then
  "$venv/bin/solaar" --version
  note "Source build entry point: $venv/bin/solaar"
  note "Does not change packaged /usr/bin/solaar or shell aliases."
fi
