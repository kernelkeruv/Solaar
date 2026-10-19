#!/usr/bin/env python3
"""Read-only Fedora/RHEL Solaar posture report. No machine identifiers."""
import argparse
import json
import shutil
import subprocess
from pathlib import Path

RULE_NAME = "42-logitech-unify-permissions.rules"


def run(*args):
    """Return one bounded diagnostic line; failures are reported, not hidden."""
    if shutil.which(args[0]) is None:
        return "not installed"
    try:
        result = subprocess.run(
            args, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            text=True, timeout=4, check=False
        )
    except (OSError, subprocess.TimeoutExpired):
        return "unavailable"
    if result.returncode:
        return "unavailable"
    return " ".join(result.stdout.strip().split())[:240] or "no output"


def kernel_fips():
    try:
        value = Path("/proc/sys/crypto/fips_enabled").read_text(encoding="ascii").strip()
    except (OSError, UnicodeError):
        return "unknown"
    return value if value in ("0", "1") else "unknown"


def distro():
    result = {}
    try:
        lines = Path("/etc/os-release").read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError):
        return {"id": "unknown", "version": "unknown"}
    for line in lines:
        if "=" not in line or line.lstrip().startswith("#"):
            continue
        key, value = line.split("=", 1)
        if key in ("ID", "VERSION_ID"):
            result[key] = value.strip().strip('"').strip("'")
    return {"id": result.get("ID", "unknown"), "version": result.get("VERSION_ID", "unknown")}


def report():
    os_data = distro()
    override = Path("/etc/udev/rules.d") / RULE_NAME
    packaged = Path("/usr/lib/udev/rules.d") / RULE_NAME
    result = {
        "distribution": os_data,
        "solaar_rpm": run("rpm", "-q", "solaar"),
        "solaar_udev_rpm": run("rpm", "-q", "solaar-udev"),
        "kernel_fips_flag": kernel_fips(),
        "crypto_policy": run("update-crypto-policies", "--show"),
        "selinux_mode": run("getenforce"),
        "auditd_service": run("systemctl", "is-active", "auditd"),
        "secure_boot": run("mokutil", "--sb-state"),
        "vendor_udev_rule_present": packaged.is_file(),
        "local_udev_rule_present": override.is_file(),
        "desktop_session": "Wayland" if "wayland" in (__import__("os").environ.get("XDG_SESSION_TYPE", "").lower()) else "other or unspecified",
        "compliance": "NOT ASSESSED. Kernel flag, policy and package state do not prove FIPS 140-3 validation or overall system compliance.",
    }
    result["observations"] = []
    if override.is_file():
        result["observations"].append(
            "Review local /etc/udev rules against the vendor-provided rules; avoid broad access modes."
        )
    if os_data["id"] == "fedora":
        result["observations"].append(
            "Fedora does not submit its cryptographic modules for CMVP validation; FIPS mode is not a compliance certificate."
        )
    if result["selinux_mode"] != "Enforcing":
        result["observations"].append(
            "SELinux is not reported Enforcing; review local system policy without disabling security controls."
        )
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Print stable JSON fields for an offline audit")
    args = parser.parse_args(argv)
    data = report()
    if args.json:
        print(json.dumps(data, indent=2, sort_keys=True))
    else:
        for key, value in data.items():
            if key == "observations":
                for item in value:
                    print("Observation: " + item)
            else:
                print("{}: {}".format(key, value))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
