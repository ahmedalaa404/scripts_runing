#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════╗
║          Script 1 — PostgreSQL Master Installer                      ║
║          Target OS : Ubuntu 24.04 LTS (Noble Numbat)                ║
║          Python    : 3.12+                                           ║
╠══════════════════════════════════════════════════════════════════════╣
║  What this script does:                                              ║
║  1. Installs the latest stable PostgreSQL from the official PGDG     ║
║     apt repository (not Ubuntu's default older version).             ║
║  2. Ensures the service is enabled and running.                      ║
║  3. Dynamically locates pg_hba.conf regardless of PG version.        ║
║  4. Rewrites auth methods: peer/scram-sha-256 → md5.                 ║
║  5. Sets the postgres Linux user password → 'admin'.                 ║
║  6. Sets the postgres DB superuser password → 'admin'.               ║
║  7. Restarts PostgreSQL and verifies connectivity.                   ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import subprocess
import sys
import os
import re
import shutil
import time
from pathlib import Path

# ─────────────────────────── ANSI Colors ────────────────────────────────────
# ألوان الـ Terminal عشان الـ output يكون واضح وسهل يتقرأ
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

# ─────────────────────────── Shell Helper ───────────────────────────────────
def run(
    cmd: str,
    check: bool = True,
    capture: bool = False,
    input_text: str | None = None,
) -> subprocess.CompletedProcess:
    """
    Wrapper around subprocess.run.
    - Always runs via /bin/bash for full shell syntax support.
    - Captures stderr so errors are visible on failure.
    - 'check=True' raises CalledProcessError on non-zero exit.
    """
    cmd_echo(cmd)
    result = subprocess.run(
        cmd,
        shell=True,
        executable="/bin/bash",
        text=True,
        capture_output=capture,
        input=input_text,
        stderr=None if not capture else subprocess.PIPE,
    )
    if check and result.returncode != 0:
        err(f"Command failed (exit {result.returncode}): {cmd}")
        if capture and result.stderr:
            print(f"{RED}{result.stderr.strip()}{RESET}")
        sys.exit(1)
    return result


def capture_output(cmd: str) -> str:
    """Run a command and return its stdout as a stripped string."""
    r = subprocess.run(
        cmd, shell=True, executable="/bin/bash",
        capture_output=True, text=True
    )
    return r.stdout.strip()


# ─────────────────────────── Root Check ─────────────────────────────────────
def ensure_root() -> None:
    """يتأكد إن السكريبت شغّال بـ sudo — مطلوب لتثبيت الحزم."""
    if os.geteuid() != 0:
        err("This script must be run with sudo: sudo python3 01_postgresql_installer.py")
        sys.exit(1)


# ─────────────────────────── Step 1: Add PGDG Repo ──────────────────────────
def add_pgdg_repository() -> None:
    """
    Adds the official PostgreSQL Global Development Group (PGDG) apt
    repository for Ubuntu 24.04 Noble. This gives us the latest stable
    PostgreSQL instead of the older Ubuntu-bundled version.

    يضيف الـ repository الرسمي لـ PostgreSQL عشان نجيب أحدث إصدار.
    """
    step("Adding official PGDG apt repository")

    keyring_path = "/usr/share/keyrings/postgresql-keyring.gpg"

    # Remove any stale key to avoid GPG prompts
    # بنمسح أي key قديم عشان ما يبقاش في تعارض
    run(f"rm -f {keyring_path}", check=False)

    info("Downloading and importing PGDG GPG key …")
    run(
        f"curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc "
        f"| gpg --dearmor -o {keyring_path}"
    )
    run(f"chmod 644 {keyring_path}")

    # Write the apt source list
    # بنكتب الـ source list للـ Ubuntu 24.04 (noble)
    sources_file = "/etc/apt/sources.list.d/pgdg.list"
    repo_line = (
        "deb [signed-by=/usr/share/keyrings/postgresql-keyring.gpg] "
        "https://apt.postgresql.org/pub/repos/apt noble-pgdg main"
    )
    Path(sources_file).write_text(repo_line + "\n", encoding="utf-8")
    ok(f"Repository file written → {sources_file}")

    run("apt-get update -q")
    ok("Package lists updated")


# ─────────────────────────── Step 2: Install PostgreSQL ─────────────────────
def install_postgresql() -> str:
    """
    Installs the latest stable PostgreSQL (e.g., postgresql-16 or
    postgresql-17) and returns the detected version string like '16'.

    يثبت أحدث إصدار PostgreSQL ويرجع رقم الإصدار.
    """
    step("Installing PostgreSQL")

    run("apt-get install -y postgresql postgresql-contrib postgresql-client")

    # Detect the installed version dynamically
    # بنكتشف الإصدار المثبت بدل ما نحدده يدوياً
    pg_ver = capture_output(
        "pg_config --version 2>/dev/null | grep -oP '[0-9]+' | head -1"
    )
    if not pg_ver:
        pg_ver = capture_output(
            "ls /etc/postgresql/ | sort -V | tail -1"
        )
    if not pg_ver:
        err("Could not detect PostgreSQL version after installation.")
        sys.exit(1)

    ok(f"Detected PostgreSQL version: {pg_ver}")
    return pg_ver


# ─────────────────────────── Step 3: Start & Enable Service ─────────────────
def start_postgresql_service() -> None:
    """يشغّل ويفعّل خدمة PostgreSQL عشان تبدأ تلقائياً مع الجهاز."""
    step("Enabling and starting PostgreSQL service")

    run("systemctl enable postgresql")
    run("systemctl start postgresql")

    # Give the service a moment to fully initialize
    time.sleep(2)

    status = capture_output("systemctl is-active postgresql")
    if status == "active":
        ok("PostgreSQL service is ACTIVE ✔")
    else:
        err(f"PostgreSQL service status: '{status}' — check: journalctl -xe")
        sys.exit(1)


# ─────────────────────────── Step 4: Find pg_hba.conf ───────────────────────
def find_pg_hba_conf() -> str:
    """
    Dynamically locates pg_hba.conf using 'find'. This is more robust
    than hardcoding the path because the PostgreSQL version number varies.

    بيدور على pg_hba.conf ديناميكياً عشان المسار بيتغير مع كل إصدار.
    Expected path pattern: /etc/postgresql/{version}/main/pg_hba.conf
    """
    step("Locating pg_hba.conf dynamically")

    # Strategy 1: find under /etc/postgresql (most common on Ubuntu/Debian)
    hba = capture_output(
        "find /etc/postgresql -name pg_hba.conf 2>/dev/null "
        "| sort -V | tail -1"
    )

    # Strategy 2: ask PostgreSQL itself via psql
    if not hba:
        hba = capture_output(
            "sudo -u postgres psql -tAc 'SHOW hba_file;' 2>/dev/null"
        )

    # Strategy 3: use pg_config (last resort)
    if not hba:
        pg_conf_dir = capture_output("pg_config --sysconfdir 2>/dev/null")
        candidate = os.path.join(pg_conf_dir, "pg_hba.conf")
        if os.path.isfile(candidate):
            hba = candidate

    if not hba or not os.path.isfile(hba):
        err("Could not locate pg_hba.conf — please configure authentication manually.")
        sys.exit(1)

    ok(f"Found pg_hba.conf → {hba}")
    return hba


# ─────────────────────────── Step 5: Patch pg_hba.conf ──────────────────────
def patch_pg_hba(hba_path: str) -> None:
    """
    Rewrites authentication methods in pg_hba.conf:
      • peer          → md5   (for local Unix socket connections)
      • scram-sha-256 → md5   (for host TCP connections)

    Also ensures 127.0.0.1 and ::1 host entries exist with md5.

    بيعدّل pg_hba.conf:
    - peer          → md5
    - scram-sha-256 → md5
    وبيتأكد إن host entries لـ 127.0.0.1 موجودة بـ md5
    """
    step("Patching pg_hba.conf (setting auth methods to md5)")

    # Create a timestamped backup before touching anything
    # بنعمل backup قبل أي تعديل
    backup_path = hba_path + ".backup_" + time.strftime("%Y%m%d_%H%M%S")
    shutil.copy2(hba_path, backup_path)
    ok(f"Backup created → {backup_path}")

    original = Path(hba_path).read_text(encoding="utf-8")
    lines = original.splitlines()
    patched_lines = []
    changes_made = 0

    for line in lines:
        stripped = line.strip()

        # Skip comments and empty lines — leave them untouched
        # بنتجاهل الـ comments والأسطر الفاضية
        if stripped.startswith("#") or not stripped:
            patched_lines.append(line)
            continue

        new_line = line

        # Replace 'peer' with 'md5' — matches whole word to avoid partial replace
        # بنبدّل peer بـ md5 بدقة (كلمة كاملة)
        if re.search(r'\bpeer\b', line):
            new_line = re.sub(r'\bpeer\b', 'md5', new_line)
            changes_made += 1

        # Replace 'scram-sha-256' with 'md5'
        if 'scram-sha-256' in new_line:
            new_line = new_line.replace('scram-sha-256', 'md5')
            changes_made += 1

        # Replace 'ident' with 'md5' (sometimes present on fresh installs)
        if re.search(r'\bident\b', new_line):
            new_line = re.sub(r'\bident\b', 'md5', new_line)
            changes_made += 1

        patched_lines.append(new_line)

    patched_content = "\n".join(patched_lines) + "\n"

    # Ensure host entries for localhost exist
    # بنتأكد إن host entries لـ localhost موجودة بـ md5
    ipv4_entry = "host    all             all             127.0.0.1/32            md5"
    ipv6_entry = "host    all             all             ::1/128                 md5"

    if "127.0.0.1/32" not in patched_content:
        patched_content += f"\n{ipv4_entry}\n"
        changes_made += 1
        info("Added missing 127.0.0.1/32 md5 host entry")

    if "::1/128" not in patched_content:
        patched_content += f"{ipv6_entry}\n"
        changes_made += 1
        info("Added missing ::1/128 md5 host entry")

    Path(hba_path).write_text(patched_content, encoding="utf-8")
    ok(f"pg_hba.conf updated ({changes_made} change(s) applied)")


# ─────────────────────────── Step 6: Set Passwords ──────────────────────────
def set_postgres_passwords() -> None:
    """
    Two separate password operations:

    A) Linux OS password for the 'postgres' system user → 'admin'
       Using 'chpasswd' which is non-interactive and scriptable.
       يضبط باسورد المستخدم postgres على مستوى Linux.

    B) PostgreSQL DB superuser password → 'admin'
       Using ALTER USER via psql (peer auth still works before hba restart).
       يضبط باسورد الـ superuser في PostgreSQL.
    """
    step("Setting passwords for postgres (Linux user + DB superuser)")

    # ── A: Linux user password via chpasswd ──────────────────────────────
    # chpasswd reads 'user:password' from stdin — safe, no shell quoting issues
    # بنستخدم chpasswd مع stdin — أأمن طريقة ومافيش مشاكل quoting
    info("Setting Linux 'postgres' user password via chpasswd …")
    result = subprocess.run(
        "chpasswd",
        shell=False,
        input="postgres:admin\n",
        text=True,
        capture_output=True,
    )
    if result.returncode == 0:
        ok("Linux 'postgres' user password set to 'admin'")
    else:
        warn(f"chpasswd failed: {result.stderr.strip()} — you may need to set it manually")

    # ── B: PostgreSQL DB superuser password ──────────────────────────────
    # We write the SQL to a temp file to avoid all shell escaping issues.
    # بنكتب SQL في ملف temp عشان نتجنب مشاكل الـ shell quoting كلياً
    sql_file = "/tmp/pg_set_password.sql"
    Path(sql_file).write_text(
        "ALTER USER postgres WITH PASSWORD 'admin';\n",
        encoding="utf-8"
    )
    os.chmod(sql_file, 0o644)

    info("Setting PostgreSQL DB superuser password via psql …")
    r = subprocess.run(
        f"sudo -u postgres psql -f {sql_file}",
        shell=True, text=True, capture_output=True
    )
    # Clean up the temp file immediately
    # بنمسح الملف المؤقت فوراً بعد الاستخدام
    os.unlink(sql_file)

    if r.returncode == 0:
        ok("PostgreSQL DB superuser 'postgres' password set to 'admin'")
    else:
        err(f"Failed to set DB password: {r.stderr.strip()}")
        warn("This may succeed after service restart — continuing …")


# ─────────────────────────── Step 7: Restart & Verify ───────────────────────
def restart_and_verify() -> None:
    """
    Restarts PostgreSQL so pg_hba.conf changes take effect,
    then verifies connectivity using md5 auth over localhost.

    بيعيد تشغيل PostgreSQL عشان التغييرات تتطبق، وبيتحقق من الاتصال.
    """
    step("Restarting PostgreSQL and verifying connectivity")

    run("systemctl restart postgresql")
    time.sleep(3)  # Wait for full initialization

    status = capture_output("systemctl is-active postgresql")
    if status != "active":
        err(f"Service not active after restart: {status}")
        sys.exit(1)
    ok("PostgreSQL restarted successfully ✔")

    # Verify TCP connection with md5 password auth
    # بنتحقق من الاتصال عبر localhost بـ password authentication
    info("Testing connection via localhost with password auth (md5) …")
    r = subprocess.run(
        'psql -U postgres -h 127.0.0.1 -c "SELECT version();" postgres',
        shell=True,
        text=True,
        capture_output=True,
        env={**os.environ, "PGPASSWORD": "admin"},
    )
    if r.returncode == 0:
        pg_version_line = r.stdout.strip().split("\n")[2].strip()
        ok(f"Connection verified ✔  {pg_version_line[:60]}")
    else:
        warn(f"TCP connection test failed: {r.stderr.strip()[:200]}")
        warn("Try connecting manually: PGPASSWORD=admin psql -U postgres -h 127.0.0.1")


# ─────────────────────────── Step 8: Print Summary ──────────────────────────
def print_summary(hba_path: str, pg_ver: str) -> None:
    """Prints a clean summary of what was installed and configured."""
    sep = "═" * 62
    print(f"""
{BOLD}{GREEN}{sep}
  ✅  PostgreSQL Installation Complete!
{sep}{RESET}
  {CYAN}Version    :{RESET}  PostgreSQL {pg_ver}
  {CYAN}Service    :{RESET}  systemctl status postgresql
  {CYAN}pg_hba     :{RESET}  {hba_path}
  {CYAN}Auth method:{RESET}  md5 (local + host)

  {BOLD}Credentials:{RESET}
  {CYAN}  Linux user :{RESET}  postgres / admin
  {CYAN}  DB user    :{RESET}  postgres / admin

  {BOLD}Quick connect:{RESET}
  {YELLOW}  PGPASSWORD=admin psql -U postgres -h 127.0.0.1{RESET}

  {BOLD}Log:{RESET}
  {YELLOW}  journalctl -u postgresql -n 50 --no-pager{RESET}
{BOLD}{GREEN}{sep}{RESET}
""")


# ─────────────────────────── MAIN ───────────────────────────────────────────
def main() -> None:
    title("🐘  PostgreSQL Master Installer — Ubuntu 24.04 LTS")
    ensure_root()

    add_pgdg_repository()
    pg_ver = install_postgresql()
    start_postgresql_service()
    hba_path = find_pg_hba_conf()
    patch_pg_hba(hba_path)

    # Set passwords BEFORE restarting so peer auth is still available
    # بنضبط الباسوردات قبل الـ restart عشان peer auth لسه شغّالة
    set_postgres_passwords()

    restart_and_verify()
    print_summary(hba_path, pg_ver)


if __name__ == "__main__":
    main()
