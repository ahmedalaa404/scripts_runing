#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════╗
║          Script 2 — pgAdmin 4 Desktop Installer                      ║
║          Target OS : Ubuntu 24.04 LTS (Noble Numbat)                ║
║          Python    : 3.12+                                           ║
╠══════════════════════════════════════════════════════════════════════╣
║  What this script does:                                              ║
║  1. Validates the OS is Ubuntu 24.04 (Noble).                        ║
║  2. Imports the official pgAdmin4 GPG key safely.                    ║
║  3. Adds the correct pgAdmin4 apt repository for Noble.              ║
║  4. Installs pgadmin4-desktop (GUI application, no Apache needed).   ║
║  5. Verifies the installation by checking the binary.                ║
║  6. Falls back to the Jammy repo if Noble packages are unavailable.  ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import subprocess
import sys
import os
import time
from pathlib import Path

# ─────────────────────────── ANSI Colors ────────────────────────────────────
RESET  = "\033[0m"
BOLD   = "\033[1m"
GREEN  = "\033[92m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
RED    = "\033[91m"
BLUE   = "\033[94m"
DIM    = "\033[2m"

def ok(msg: str)      -> None: print(f"{GREEN}  ✅  {msg}{RESET}")
def warn(msg: str)    -> None: print(f"{YELLOW}  ⚠️   {msg}{RESET}")
def err(msg: str)     -> None: print(f"{RED}  ❌  {msg}{RESET}")
def info(msg: str)    -> None: print(f"{CYAN}  ℹ️   {msg}{RESET}")
def step(msg: str)    -> None:
    sep = "─" * 62
    print(f"\n{BOLD}{BLUE}{sep}\n  ▶  {msg}\n{sep}{RESET}")
def title(msg: str)   -> None:
    sep = "═" * 62
    print(f"\n{BOLD}{CYAN}{sep}\n  {msg}\n{sep}{RESET}")
def cmd_echo(c: str)  -> None: print(f"{DIM}  $ {c}{RESET}")


# ─────────────────────────── Shell Helpers ───────────────────────────────────
def run(cmd: str, check: bool = True, capture: bool = False) -> subprocess.CompletedProcess:
    """
    Executes a shell command via /bin/bash.
    - check=True exits the script on failure.
    - capture=True returns stdout/stderr for inspection.
    """
    cmd_echo(cmd)
    result = subprocess.run(
        cmd,
        shell=True,
        executable="/bin/bash",
        text=True,
        capture_output=capture,
    )
    if check and result.returncode != 0:
        err(f"Command failed (exit {result.returncode}):\n  {cmd}")
        if capture and result.stderr:
            print(f"{RED}{result.stderr.strip()}{RESET}")
        sys.exit(1)
    return result


def capture_output(cmd: str) -> str:
    """Runs a command and returns stripped stdout."""
    r = subprocess.run(
        cmd, shell=True, executable="/bin/bash",
        capture_output=True, text=True
    )
    return r.stdout.strip()


def package_installed(pkg: str) -> bool:
    """Returns True if the dpkg package is in 'installed' state."""
    r = subprocess.run(
        f"dpkg -s {pkg} 2>/dev/null | grep -q 'Status: install ok installed'",
        shell=True
    )
    return r.returncode == 0


# ─────────────────────────── Checks ─────────────────────────────────────────
def ensure_root() -> None:
    """يتأكد إن السكريبت شغّال بصلاحيات root."""
    if os.geteuid() != 0:
        err("Run with sudo: sudo python3 02_pgadmin_desktop_installer.py")
        sys.exit(1)


def detect_ubuntu() -> tuple[str, str]:
    """
    Detects Ubuntu version and codename.
    Returns ('24.04', 'noble') on Ubuntu 24.04 LTS.
    بيكتشف إصدار Ubuntu واسمه (focal/jammy/noble …).
    """
    ver      = capture_output("lsb_release -rs 2>/dev/null") or "unknown"
    codename = capture_output("lsb_release -cs 2>/dev/null") or "unknown"
    return ver, codename


def check_ubuntu_noble(ver: str, codename: str) -> None:
    """
    Warns (but does NOT exit) if the OS is not Ubuntu 24.04 Noble.
    This script is optimized for Noble but may work on Jammy too.
    """
    if codename != "noble":
        warn(f"This script targets Ubuntu 24.04 Noble, but detected: {ver} ({codename})")
        warn("Proceeding anyway — adjust the repo codename if installation fails.")
    else:
        ok(f"Ubuntu {ver} ({codename}) detected ✔")


# ─────────────────────────── Step 1: Install prereqs ────────────────────────
def install_prerequisites() -> None:
    """
    Installs prerequisite packages needed before adding the pgAdmin repo.
    بيثبت الحزم الأساسية اللازمة قبل إضافة الـ repository.
    """
    step("Installing prerequisites (curl, gnupg, apt-transport-https)")
    run("apt-get update -q")
    run("apt-get install -y curl gnupg2 apt-transport-https ca-certificates")
    ok("Prerequisites installed")


# ─────────────────────────── Step 2: Import GPG key ─────────────────────────
def import_pgadmin_gpg_key() -> str:
    """
    Downloads and imports the official pgAdmin4 GPG signing key.
    Writes a binary .gpg keyring file to /usr/share/keyrings/.

    Returns the path to the keyring file.

    بيجيب ويحوّل GPG key الرسمي لـ pgAdmin4 لصيغة binary (dearmored)
    ويحطه في المكان الصح.
    """
    step("Importing pgAdmin4 GPG key")

    keyring_path = "/usr/share/keyrings/pgadmin4-keyring.gpg"
    gpg_key_url  = "https://www.pgadmin.org/static/packages_pgadmin_org.pub"

    # Remove any stale / corrupted keyring first
    # بنمسح أي keyring قديم أو تالف أولاً
    if Path(keyring_path).exists():
        warn(f"Removing existing keyring: {keyring_path}")
        Path(keyring_path).unlink()

    info(f"Downloading GPG key from: {gpg_key_url}")

    # Download the ASCII-armored key, pipe it through gpg --dearmor,
    # and write the binary result directly to the keyring path.
    # curl -fsSL → fail silently on errors, show on server errors
    result = run(
        f"curl -fsSL '{gpg_key_url}' | gpg --dearmor -o '{keyring_path}'",
        check=False, capture=True
    )

    if result.returncode != 0:
        err("Failed to download or import GPG key.")
        err(f"stderr: {result.stderr.strip()[:300]}")
        err("Check your internet connection and try again.")
        sys.exit(1)

    # Verify the file was actually created and is non-empty
    kp = Path(keyring_path)
    if not kp.exists() or kp.stat().st_size == 0:
        err(f"GPG keyring file is missing or empty: {keyring_path}")
        sys.exit(1)

    run(f"chmod 644 '{keyring_path}'")
    ok(f"GPG key imported → {keyring_path}  ({kp.stat().st_size} bytes)")
    return keyring_path


# ─────────────────────────── Step 3: Add Repository ─────────────────────────
def add_pgadmin_repository(keyring_path: str, codename: str) -> str:
    """
    Writes the pgAdmin4 apt sources file for the target codename.
    Tries Noble first; falls back to Jammy if Noble packages not found.

    بيضيف الـ apt repository لـ pgAdmin4.
    بيجرب noble أولاً، ولو الحزم مش موجودة بيرجّع لـ jammy.
    Returns the codename actually used.
    """
    step(f"Adding pgAdmin4 apt repository (codename: {codename})")

    sources_file = "/etc/apt/sources.list.d/pgadmin4.list"
    base_url     = "https://ftp.postgresql.org/pub/pgadmin/pgadmin4/apt"

    def write_repo(cn: str) -> None:
        repo_line = (
            f"deb [signed-by={keyring_path}] "
            f"{base_url}/{cn} pgadmin4 main"
        )
        Path(sources_file).write_text(repo_line + "\n", encoding="utf-8")
        info(f"Written: {sources_file}")
        info(f"  → {repo_line}")

    # ── First attempt: target codename (noble) ──────────────────────────
    write_repo(codename)
    run("apt-get update -q", check=False)  # Soft update; errors handled below

    # Check if pgadmin4-desktop is findable in the newly added repo
    # بنتحقق إن الحزمة موجودة في الـ repo اللي أضفناه
    found = capture_output(
        "apt-cache show pgadmin4-desktop 2>/dev/null | grep -c 'Package:'"
    )

    if found == "0" and codename == "noble":
        # ── Fallback: use Jammy repo ────────────────────────────────────
        # Noble packages might not yet be published; Jammy is compatible
        # على Ubuntu 24.04 ممكن حزم noble مش منشورة بعد — jammy متوافق
        warn("pgadmin4-desktop not found in Noble repo — falling back to Jammy")
        codename = "jammy"
        write_repo(codename)
        run("apt-get update -q")
        found = capture_output(
            "apt-cache show pgadmin4-desktop 2>/dev/null | grep -c 'Package:'"
        )
        if found == "0":
            err("pgadmin4-desktop not found in Jammy repo either.")
            err("Visit https://www.pgadmin.org/download/pgadmin-4-apt/ for help.")
            sys.exit(1)
        ok(f"Package found using Jammy fallback repo")
    else:
        ok(f"Package found in {codename} repo ✔")

    return codename


# ─────────────────────────── Step 4: Install pgadmin4-desktop ───────────────
def install_pgadmin_desktop() -> None:
    """
    Installs pgadmin4-desktop — the standalone Qt-based GUI application.
    Unlike pgadmin4-web, this does NOT require Apache/Nginx/setup scripts.

    بيثبت pgadmin4-desktop — التطبيق المستقل اللي مش محتاج Apache.
    """
    step("Installing pgadmin4-desktop")

    if package_installed("pgadmin4-desktop"):
        warn("pgadmin4-desktop is already installed — skipping")
        return

    # DEBIAN_FRONTEND=noninteractive prevents any apt interactive prompts
    # بنمنع أي prompts تفاعلية أثناء التثبيت
    run("DEBIAN_FRONTEND=noninteractive apt-get install -y pgadmin4-desktop")
    ok("pgadmin4-desktop installed ✔")


# ─────────────────────────── Step 5: Verify ─────────────────────────────────
def verify_installation() -> None:
    """
    Verifies pgAdmin4 desktop was correctly installed by checking
    both the dpkg status and the executable binary.

    بيتحقق من نجاح التثبيت بطريقتين: dpkg status والـ binary.
    """
    step("Verifying pgAdmin4 desktop installation")

    # Check dpkg status
    if not package_installed("pgadmin4-desktop"):
        err("dpkg reports pgadmin4-desktop is NOT installed correctly.")
        sys.exit(1)
    ok("dpkg status: install ok installed ✔")

    # Find the installed binary / launcher
    binary = capture_output("which pgadmin4 2>/dev/null")
    if not binary:
        # Common alternative location
        binary = capture_output("find /usr/pgadmin4 -name 'pgadmin4' -type f 2>/dev/null | head -1")

    if binary:
        ok(f"Binary found → {binary}")
    else:
        warn("pgadmin4 binary not found in PATH — may be launched from the Applications menu")

    # Check version
    version_output = capture_output(
        "dpkg -l pgadmin4-desktop 2>/dev/null | awk 'NR==6{print $3}'"
    )
    if version_output:
        ok(f"Installed version: {version_output}")


# ─────────────────────────── Step 6: Print Summary ──────────────────────────
def print_summary(codename_used: str) -> None:
    """Prints a clean post-installation summary."""
    sep = "═" * 62
    print(f"""
{BOLD}{GREEN}{sep}
  ✅  pgAdmin 4 Desktop Installation Complete!
{sep}{RESET}
  {CYAN}Type      :{RESET}  Desktop (Qt GUI — no web server required)
  {CYAN}Repo      :{RESET}  pgAdmin4 apt / {codename_used}

  {BOLD}How to launch:{RESET}
  {YELLOW}  Option 1:{RESET} Search "pgAdmin" in the Applications menu
  {YELLOW}  Option 2:{RESET} Run 'pgadmin4' in a terminal

  {BOLD}Connect to PostgreSQL:{RESET}
  {CYAN}  Host     :{RESET}  127.0.0.1
  {CYAN}  Port     :{RESET}  5432
  {CYAN}  Username :{RESET}  postgres
  {CYAN}  Password :{RESET}  admin  (set by Script 1)

  {BOLD}Documentation:{RESET}
  {YELLOW}  https://www.pgadmin.org/docs/{RESET}
{BOLD}{GREEN}{sep}{RESET}
""")


# ─────────────────────────── MAIN ───────────────────────────────────────────
def main() -> None:
    title("🖥️   pgAdmin 4 Desktop Installer — Ubuntu 24.04 LTS")
    ensure_root()

    ver, codename = detect_ubuntu()
    info(f"Detected OS: Ubuntu {ver} ({codename})")
    check_ubuntu_noble(ver, codename)

    install_prerequisites()
    keyring_path    = import_pgadmin_gpg_key()
    codename_used   = add_pgadmin_repository(keyring_path, codename)
    install_pgadmin_desktop()
    verify_installation()
    print_summary(codename_used)


if __name__ == "__main__":
    main()
