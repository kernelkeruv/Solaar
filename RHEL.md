# Fedora 44 and RHEL-family: secure Solaar installation

This is a **distro-first, non-destructive** installation and review workflow.
The upstream project is [pwr-Solaar/Solaar](https://github.com/pwr-Solaar/Solaar).
The local installer in this repository is a developer helper, not an
independent security product, and does not attest to FIPS certification.

## Recommended on Fedora 44: install the RPMs

Fedora packages both `solaar` and `solaar-udev`. The packaged rule is
normally installed under `/usr/lib/udev/rules.d/`, maintained by RPM.
This approach avoids modifying the system Python environment and avoids
installing unreviewed scripts as root.

From a trusted checkout:

```bash
bash tools/install-rhel.sh --check
bash tools/install-rhel.sh --install --dry-run
bash tools/install-rhel.sh --install
rpm -q solaar solaar-udev
rpm -V solaar solaar-udev
solaar --version
```

The actual mutating step runs `sudo dnf install solaar solaar-udev`,
allowing DNF to prompt for approval. It **does not** add custom repos, disable
GPG verification, change SELinux, modify Secure Boot, change crypto policies,
reload or retrigger udev globally, or change `/dev/hidraw*` permissions.
If RPM verification reports differences, inspect them before acting.

A user who merely wants to run Solaar does not need to clone this repository.
The latest Fedora package may be newer than this fork's source checkout.

## Source-development installation (Fedora 44 / RHEL family)

Use only when developing or testing a reviewed source checkout. This
installer uses an isolated `venv --system-site-packages` so native GTK,
DBus, and evdev dependencies are provided by signed distro packages.
Only the source checkout is installed in the venv, via pip with
`--no-index --no-deps --no-build-isolation --editable`. No PyPI access,
`sudo pip`, `--break-system-packages`, or global Python replacement is used.

```bash
bash tools/install-rhel.sh --source --dry-run
bash tools/install-rhel.sh --source
"${XDG_DATA_HOME:-$HOME/.local/share}/solaar-dev/venv/bin/solaar" --version
```

The installer does not `git clone` or `git pull`, so you must control and
review the source revision in advance. Python build steps can execute the
local checkout's `setup.py` and can write build metadata in the checkout.
For a high-assurance investigation use a disposable VM and trust-reviewed
dependency RPMs, not arbitrary local or online source code.

RHEL, Rocky, AlmaLinux, CentOS Stream and Oracle Linux package names or
availability depend on configured **approved** repositories. The installer
fails rather than automatically enabling EPEL, third-party repositories,
unsigned packages, or insecure package signatures. For hardened RHEL
deployments, prefer a vendor-supported packaged build when available and
review installed component validation status against the relevant Red Hat
certificate's tested operational environment.

## Optional read-only security posture report

```bash
python3 tools/fedora-security-report.py
python3 tools/fedora-security-report.py --json
```

Reports only coarse OS version, RPM versions, udev rule presence,
SELinux, auditd service status, Secure Boot state, kernel FIPS flag,
system crypto-policy name and desktop session type. It does not inspect
input-device event contents, keyboard activity, secrets, host identifiers
or original evidence. Use `--json` for a locally controlled report;
review the information before sharing it.

For independent verification:

```bash
cat /proc/sys/crypto/fips_enabled
update-crypto-policies --show
getenforce
systemctl is-active auditd
mokutil --sb-state
rpm -q solaar solaar-udev
rpm -V solaar solaar-udev
```

Some commands are optional depending on installed packages. The reporting
command is never elevated and does not change any controls.

## FIPS 140-3: precise meaning

**Fedora is not a CMVP-validated operating environment by virtue of FIPS
mode, `fips=1`, or a `FIPS` crypto policy.** Fedora does not submit its
cryptographic modules for FIPS 140-3 validation. FIPS mode on Fedora is
primarily useful for development/testing. Using approved algorithms is
also not equivalent to using validated cryptographic modules in an
approved mode or satisfying all system-level controls.

Solaar's Logitech protocol handling, device pairing, and Logitech firmware
are not magically FIPS-certified by this installer. Solaar is an input-device
management application, not a cryptographic validation boundary.
A validated RHEL build requires the exact applicable module versions,
tested operational environment, approved services and deployment controls
documented in the CMVP certificates and Red Hat guidance. No install script
can confer those certifications. Do not toggle FIPS after installation
as a casual hardening measure; for Fedora/RHEL 10, FIPS setup is an
installation/image-build decision with boot and key-management consequences.

References:

- [Fedora FIPS design and limits](https://fedoraproject.org/wiki/Changes/RemoveFipsModeSetup)
- [RHEL 10 installation-time FIPS guidance](https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/10/html/security_hardening/switching-rhel-to-fips-mode)
- [Red Hat certified cryptographic modules](https://access.redhat.com/compliance/fips)

## Least privilege and operational limits

- Leave SELinux enforcing, audit, disk encryption and Secure Boot intact.
- Favor the packaged `solaar-udev` rule. Before adding a local rule, check
  for a shadowing `/etc/udev/rules.d/42-logitech-unify-permissions.rules`.
  Do **not** use `chmod 666 /dev/hidraw*` or broadly grant `plugdev`.
- Seated-user `uaccess` enables raw HID device access, which carries
  firmware/pairing risk. Physical device access is not risk-free.
- Do not run Solaar as root or configure input-monitoring services to
  capture keys by default. The installer avoids `keyd` and `libinput`
  monitoring entirely.
- Fedora KDE Plasma Wayland is supported for the GUI, but some Solaar
  diversion rules depending on X11/XKB are inherently limited under Wayland.
  Do not disable Wayland or SELinux to work around this.
- This installer deliberately leaves existing shell startup files,
  user configuration, udev rules, and pre-existing RPM transactions alone.
  If you need rollback, inspect `dnf history` and the installed package
  list before approving any package removal; do not delete unknown venv
  paths without confirming ownership and contents.

## Developer tests

The GitHub Actions Fedora 44 container workflow runs Bash syntax checks,
non-mutating installer checks, offline security-report tests, and JSON
schema sanity checks. It **does not** prove the whole Solaar GUI, HID
receiver behavior, kernel FIPS validation, or installer privileges on a
production system. Hardware regression testing must be done on an
authorized Fedora/RHEL host.
