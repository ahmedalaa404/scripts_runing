#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════╗
║          Script 3 — Odoo Source Cloner (Connection Optimized)        ║
║          Versions  : 15.0 → 18.0                                     ║
║          Target OS : Ubuntu 24.04 LTS (Noble Numbat)                 ║
║          Python    : 3.12+                                           ║
╠══════════════════════════════════════════════════════════════════════╣
║  Features:                                                           ║
║  • Interactive version selection (single or multiple)                ║
║  • Global Git tuning for slow / unstable internet connections        ║
║  • --depth 1 shallow clone for maximum speed                         ║
║  • Clone integrity verification (odoo-bin + key files check)         ║
║  • Automatic retry logic: up to 3 attempts per version               ║
║  • Partial clone detection and cleanup before retry                  ║
║  • Per-version Python virtualenv creation + requirements install     ║
║  • Full colored terminal output with progress indicators             ║
╚══════════════════════════════════════════════════════════════════════╝

Git parameters applied (slow internet fix / إصلاح النت البطيء):
  http.postBuffer  = 524288000  (500 MB — prevents mid-clone disconnects)
  core.compression = 0          (no compression — faster on slow lines)
  http.lowSpeedLimit = 0        (disable speed-based timeout)
  http.lowSpeedTime  = 999999   (never abort due to low speed)
"""

import subprocess
import sys
import os
import shutil
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
MAGENTA = "\033[95m"
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
def banner(msg: str)  -> None:
    sep = "━" * 62
    print(f"\n{BOLD}{MAGENTA}{sep}\n  {msg}\n{sep}{RESET}")
def cmd_echo(c: str)  -> None: print(f"{DIM}  $ {c}{RESET}")


# ─────────────────────────── Constants ──────────────────────────────────────
ODOO_REPO   = "https://github.com/odoo/odoo.git"
MAX_RETRIES = 3

# Supported versions with their metadata
# الإصدارات المدعومة مع معلوماتها
VERSIONS: dict[str, dict] = {
    "15.0": {
        "python":      "python3.8",
        "port":        8015,
        "note":        "Python 3.8 — LTS stable branch",
        "setuptools":  None,          # use latest setuptools
    },
    "16.0": {
        "python":      "python3.11",
        "port":        8016,
        "note":        "Python 3.11 — setuptools pin required",
        "setuptools":  "68.2.2",
    },
    "17.0": {
        "python":      "python3.11",
        "port":        8017,
        "note":        "Python 3.11 — setuptools pin required",
        "setuptools":  "68.2.2",
    },
    "18.0": {
        "python":      "python3.11",
        "port":        8018,
        "note":        "Python 3.11 — setuptools pin required",
        "setuptools":  "68.2.2",
    },
}

# Files that MUST exist for a clone to be considered complete / intact
# الملفات اللازمة عشان نعتبر الـ clone مكتمل وصالح
INTEGRITY_CHECKS = [
    "odoo-bin",                       # Main launcher
    "odoo/__init__.py",               # Core package marker
    "requirements.txt",               # Dependencies list
    ".git/HEAD",                      # Git metadata (proves clone finished)
    "odoo/release.py",                # Version info
]


# ─────────────────────────── Shell Helpers ───────────────────────────────────
def run(
    cmd: str,
    check: bool = True,
    capture: bool = False,
    env: dict | None = None,
) -> subprocess.CompletedProcess:
    """
    Wrapper around subprocess.run with consistent options.
    Merges 'env' with current environment if provided.
    """
    cmd_echo(cmd)
    merged_env = {**os.environ, **(env or {})}
    result = subprocess.run(
        cmd,
        shell=True,
        executable="/bin/bash",
        text=True,
        capture_output=capture,
        env=merged_env,
    )
    if check and result.returncode != 0:
        err(f"Command failed (exit {result.returncode}): {cmd}")
        if capture and result.stderr:
            print(f"{RED}{result.stderr.strip()[:500]}{RESET}")
        sys.exit(1)
    return result


def capture_output(cmd: str) -> str:
    """Runs a command and returns stripped stdout."""
    r = subprocess.run(
        cmd, shell=True, executable="/bin/bash",
        capture_output=True, text=True
    )
    return r.stdout.strip()


def check_internet(timeout: int = 8) -> bool:
    """
    Quick internet connectivity check via GitHub.
    Returns True if reachable, False otherwise.
    بيتحقق من وجود اتصال بالإنترنت عبر GitHub.
    """
    r = subprocess.run(
        f"curl -s --max-time {timeout} -o /dev/null -w '%{{http_code}}' "
        f"https://github.com",
        shell=True, capture_output=True, text=True
    )
    code = r.stdout.strip()
    return code.startswith("2") or code.startswith("3")


def wait_for_internet(context: str = "", max_wait_seconds: int = 600) -> bool:
    """
    Waits up to max_wait_seconds for internet to come back.
    Checks every 15 seconds and prompts user every minute.

    بينتظر لحد ما يرجع النت — بيسأل المستخدم كل دقيقة إذا يكمل أو يوقف.
    """
    if check_internet():
        return True
    warn(f"No internet connection{' (' + context + ')' if context else ''}")
    info("Waiting for connectivity (checking every 15s) …")
    info("Press Ctrl+C to abort\n")

    elapsed = 0
    check_interval = 15

    while elapsed < max_wait_seconds:
        time.sleep(check_interval)
        elapsed += check_interval
        if check_internet():
            ok(f"✅ Internet restored after {elapsed}s — resuming")
            return True
        print(f"  {YELLOW}  [{elapsed}s] Still waiting for internet …{RESET}")

        # Prompt user every ~60 seconds
        if elapsed % 60 == 0:
            try:
                ans = input(f"\n  {BOLD}{YELLOW}  Continue waiting? [Y/n]: {RESET}").strip().lower()
                if ans == "n":
                    return False
            except (KeyboardInterrupt, EOFError):
                print()
                return False

    err(f"Timed out waiting for internet ({max_wait_seconds}s)")
    return False


# ─────────────────────────── Git Configuration ──────────────────────────────
def configure_git_for_slow_internet() -> None:
    """
    Applies global Git settings optimized for slow / unreliable internet.
    These settings prevent Git from aborting long-running clones.

    بيضبط إعدادات Git العالمية عشان تتحمل النت البطيء أو غير المستقر.

    Parameters explained:
      http.postBuffer  → Max buffer size for HTTP POST (500 MB).
                         Prevents "fatal: the remote end hung up unexpectedly"
                         on large repos over slow connections.
                         بيزود الـ buffer عشان الـ clone ما يقطعش في النص.

      core.compression → 0 = disable zlib compression.
                         Saves CPU on slow machines; trades bandwidth for speed.
                         بيوقف الضغط — أسرع على النت البطيء.

      http.lowSpeedLimit → Minimum bytes/sec threshold (0 = disabled).
                           Without this, Git aborts if speed drops below 1000 B/s.
                           بيعطل حد أدنى للسرعة.

      http.lowSpeedTime  → Seconds to wait at low speed before aborting.
                           999999 ≈ never abort due to low speed.
                           بيعطل timeout السرعة البطيئة تقريباً خالص.
    """
    step("Configuring Git for slow/unstable internet connections")

    git_settings = {
        "http.postBuffer":   "524288000",   # 500 MB
        "core.compression":  "0",
        "http.lowSpeedLimit": "0",
        "http.lowSpeedTime":  "999999",
    }

    for key, value in git_settings.items():
        result = run(f"git config --global {key} {value}", check=False, capture=True)
        if result.returncode == 0:
            ok(f"git config --global {key} = {value}")
        else:
            warn(f"Could not set git config {key}: {result.stderr.strip()[:100]}")

    # Also set a reasonable TCP keepalive via GIT_HTTP_USER_AGENT is not
    # needed, but we can set GIT_CURL_VERBOSE for debugging if needed.
    # بيعرض الإعدادات الحالية للتأكد
    info("Current git http settings:")
    run("git config --global --list | grep -E 'http|core.comp'", check=False)


# ─────────────────────────── Clone Integrity ─────────────────────────────────
def verify_clone_integrity(odoo_dir: str) -> tuple[bool, list[str]]:
    """
    Checks that all required files exist inside the cloned directory.
    Returns (is_complete, list_of_missing_files).

    بيتحقق إن كل الملفات الأساسية موجودة بعد الـ clone.
    Returns: (True/False, [قائمة الملفات الناقصة])
    """
    missing = []
    for relative_path in INTEGRITY_CHECKS:
        full_path = os.path.join(odoo_dir, relative_path)
        if not os.path.exists(full_path):
            missing.append(relative_path)
    return (len(missing) == 0), missing


def cleanup_partial_clone(odoo_dir: str) -> None:
    """
    Removes a partial or corrupted clone directory before retrying.
    Handles permission errors gracefully.

    بيحذف الـ clone الناقص أو التالف قبل المحاولة التانية.
    """
    if os.path.exists(odoo_dir):
        warn(f"Removing incomplete clone: {odoo_dir}")
        try:
            shutil.rmtree(odoo_dir)
            ok(f"Removed: {odoo_dir}")
        except OSError as e:
            warn(f"Could not fully remove {odoo_dir}: {e}")
            warn("Attempting forced removal with sudo …")
            run(f"sudo rm -rf '{odoo_dir}'", check=False)


# ─────────────────────────── Clone Logic ────────────────────────────────────
def clone_odoo_version(ver: str, target_dir: str) -> bool:
    """
    Clones a specific Odoo version with retry logic.

    Strategy:
      - Attempt up to MAX_RETRIES (3) times.
      - After each failed attempt: clean up, wait for internet, then retry.
      - After success: verify clone integrity before returning True.

    Returns True on success, False on all retries exhausted.

    بيعمل clone لإصدار Odoo معين مع إعادة المحاولة حتى 3 مرات.
    """
    odoo_dir = os.path.join(target_dir, f"odoo{ver.split('.')[0]}")
    banner(f"Cloning Odoo {ver} → {odoo_dir}")

    # ── Check if a valid clone already exists ───────────────────────────
    if os.path.isdir(odoo_dir):
        complete, missing = verify_clone_integrity(odoo_dir)
        if complete:
            ok(f"Odoo {ver} already cloned and intact — skipping clone ✔")
            return True
        else:
            warn(f"Existing directory is incomplete (missing: {', '.join(missing)})")
            warn("Will remove and re-clone …")
            cleanup_partial_clone(odoo_dir)

    # ── Retry loop ───────────────────────────────────────────────────────
    for attempt in range(1, MAX_RETRIES + 1):
        print(f"\n  {BOLD}{CYAN}  🔄  Clone attempt {attempt}/{MAX_RETRIES} "
              f"(Odoo {ver}){RESET}")

        # Ensure internet before each attempt
        # بنتحقق من النت قبل كل محاولة
        if not wait_for_internet(f"git clone Odoo {ver}"):
            err(f"Aborted — no internet for Odoo {ver} clone")
            return False

        # Build the git clone command
        # بنبني أمر الـ clone
        clone_cmd = (
            f"git clone {ODOO_REPO} "
            f"--depth 1 "               # Shallow clone — fastest method
            f"--single-branch "         # Only fetch the target branch
            f"--branch {ver} "
            f"--progress "              # Show progress in terminal
            f'"{odoo_dir}"'
        )

        info(f"Running: {clone_cmd}")
        start_time = time.time()

        # Run clone — don't use check=True so we can handle failure ourselves
        # مش بنستخدم check=True عشان نتحكم في التعامل مع الفشل
        result = subprocess.run(
            clone_cmd,
            shell=True,
            executable="/bin/bash",
            text=True,
        )

        elapsed = time.time() - start_time
        duration_str = f"{int(elapsed // 60)}m {int(elapsed % 60)}s"

        if result.returncode == 0:
            # Verify integrity even on apparent success
            # بنتحقق من الـ clone حتى لو Git قال إنه نجح
            complete, missing = verify_clone_integrity(odoo_dir)
            if complete:
                ok(f"Clone complete ✔  (took {duration_str})")
                ok(f"Location: {odoo_dir}")
                return True
            else:
                warn(f"Git reported success but clone is incomplete!")
                warn(f"Missing: {', '.join(missing)}")
                # Fall through to cleanup and retry
                # ننزل للـ cleanup ونعيد المحاولة
        else:
            warn(f"Clone failed after {duration_str} (exit code {result.returncode})")

        # ── Cleanup before next attempt ──────────────────────────────────
        cleanup_partial_clone(odoo_dir)

        if attempt < MAX_RETRIES:
            wait_secs = attempt * 5   # Progressive delay: 5s, 10s
            info(f"Waiting {wait_secs}s before attempt {attempt + 1} …")
            time.sleep(wait_secs)
        else:
            err(f"All {MAX_RETRIES} clone attempts failed for Odoo {ver}")
            err(f"Manual command: git clone {ODOO_REPO} --depth 1 --branch {ver} {odoo_dir}")

    return False


# ─────────────────────────── Python / Venv ──────────────────────────────────
def check_python_available(py_bin: str) -> bool:
    """Returns True if the requested Python binary is on PATH."""
    return shutil.which(py_bin) is not None


def create_virtualenv(py_bin: str, venv_dir: str) -> bool:
    """
    Creates a Python virtualenv using the specified Python binary.
    Returns True on success.

    بيعمل virtualenv بالـ Python المناسب لكل إصدار Odoo.
    """
    step(f"Creating virtualenv with {py_bin}")

    if os.path.isdir(venv_dir) and os.path.isfile(os.path.join(venv_dir, "bin/activate")):
        warn(f"Virtualenv already exists: {venv_dir}")
        return True

    if not check_python_available(py_bin):
        err(f"Python binary not found: {py_bin}")
        info(f"Install it with: sudo add-apt-repository ppa:deadsnakes/ppa && "
             f"sudo apt-get install -y {py_bin} {py_bin}-venv {py_bin}-dev")
        return False

    result = run(f"{py_bin} -m venv '{venv_dir}'", check=False, capture=True)
    if result.returncode != 0:
        err(f"Failed to create venv: {result.stderr.strip()[:300]}")
        return False

    ok(f"Virtualenv created → {venv_dir}")
    return True


def install_odoo_requirements(
    venv_dir: str,
    req_file: str,
    ver: str,
    setuptools_version: str | None,
) -> bool:
    """
    Installs Odoo requirements.txt inside the virtualenv.

    Handles the setuptools==68.2.2 pin for Odoo 16+, which fixes
    the 'pkg_resources' ImportError introduced in setuptools >= 69.

    بيثبت المتطلبات جوا الـ venv مع فيكس setuptools لـ Odoo 16/17/18.

    Returns True on success.
    """
    step(f"Installing requirements for Odoo {ver}")

    pip = os.path.join(venv_dir, "bin/pip")

    if not os.path.isfile(req_file):
        err(f"requirements.txt not found: {req_file}")
        return False

    # ── Base pip upgrade ─────────────────────────────────────────────────
    info("Upgrading pip and wheel …")
    run(f"'{pip}' install --upgrade pip wheel --quiet", check=False)

    # ── setuptools version pin ───────────────────────────────────────────
    if setuptools_version:
        # Odoo 16/17/18: pin setuptools to avoid pkg_resources removal
        # بنثبت setuptools قديم عشان pkg_resources تشتغل مع Odoo 16+
        info(f"Pinning setuptools=={setuptools_version} (pkg_resources fix) …")
        r = run(
            f"'{pip}' install setuptools=={setuptools_version} --quiet",
            check=False, capture=True
        )
        if r.returncode == 0:
            ok(f"setuptools=={setuptools_version} installed")
        else:
            warn(f"setuptools pin failed: {r.stderr.strip()[:200]}")
    else:
        run(f"'{pip}' install --upgrade setuptools --quiet", check=False)

    # ── Install requirements ─────────────────────────────────────────────
    flags = "--prefer-binary"  # Prefer pre-built wheels to avoid compilation
    if setuptools_version:
        # --no-build-isolation prevents pip from creating isolated build envs
        # that would re-download a newer setuptools and break the pin.
        # بيمنع pip من إنشاء بيئة مؤقتة تجيب setuptools جديد وتكسر الـ pin
        flags += " --no-build-isolation"

    info(f"Installing requirements.txt (flags: {flags}) …")
    r = run(
        f"'{pip}' install -r '{req_file}' {flags}",
        check=False, capture=True
    )

    if r.returncode == 0:
        ok("All requirements installed ✔")
        return True

    # ── Retry with --ignore-requires-python ─────────────────────────────
    warn("First attempt failed — retrying with --ignore-requires-python …")
    r2 = run(
        f"'{pip}' install -r '{req_file}' {flags} --ignore-requires-python",
        check=False, capture=True
    )
    if r2.returncode == 0:
        ok("Requirements installed (with --ignore-requires-python) ✔")
        return True

    err(f"Failed to install requirements for Odoo {ver}")
    err(f"stderr tail: {r2.stderr.strip()[-400:]}")
    info(f"Manual fix:\n  source {venv_dir}/bin/activate\n"
         f"  pip install setuptools==68.2.2\n"
         f"  pip install -r {req_file} --no-build-isolation")
    return False


# ─────────────────────────── Interactive Selection ───────────────────────────
def ask_versions() -> list[str]:
    """
    Interactive menu for selecting one or more Odoo versions to clone.
    Supports: individual numbers, comma-separated, ranges (1-3), or 'a' for all.

    قائمة تفاعلية لاختيار الإصدارات المطلوبة.
    """
    all_vers = list(VERSIONS.keys())

    print(f"\n{BOLD}  Available Odoo Versions:{RESET}")
    for i, v in enumerate(all_vers, 1):
        meta = VERSIONS[v]
        print(f"  {CYAN}  {i}{RESET}) Odoo {v:<6} "
              f"{BLUE}port={meta['port']}{RESET}  "
              f"{DIM}{meta['note']}{RESET}")
    print(f"  {CYAN}  a{RESET}) All versions\n")

    while True:
        raw = input(
            f"  {BOLD}{YELLOW}  Select versions (e.g. 1,3 or 1-3 or a): {RESET}"
        ).strip().lower()

        if raw in ("a", "all"):
            return all_vers[:]

        selected = []
        try:
            for part in raw.split(","):
                part = part.strip()
                if "-" in part:
                    s, e = part.split("-", 1)
                    selected.extend(all_vers[int(s) - 1 : int(e)])
                else:
                    selected.append(all_vers[int(part) - 1])
            if selected:
                return selected
        except (ValueError, IndexError):
            pass

        print(f"  {RED}  Invalid input — try: 1,2 or 1-4 or a{RESET}")


def ask_path(default: str) -> str:
    """
    Prompts for the base installation directory.
    Falls back to the default if the input is empty or invalid.

    بيسأل المستخدم عن مجلد التثبيت.
    """
    print(f"\n  {BOLD}Base installation directory:{RESET}")
    print(f"  Default: {CYAN}{default}{RESET}  (press Enter to accept)")
    raw = input("  Path: ").strip()

    if not raw:
        return default
    if not os.path.isdir(raw):
        warn(f"'{raw}' does not exist — will be created")
    return raw


def ask_install_reqs() -> bool:
    """Ask whether to also install Python requirements after cloning."""
    ans = input(
        f"\n  {BOLD}{YELLOW}  Also install Python requirements after cloning? [Y/n]: {RESET}"
    ).strip().lower()
    return ans not in ("n", "no")


# ─────────────────────────── Summary Report ─────────────────────────────────
def print_final_report(results: list[dict]) -> None:
    """
    Prints a comprehensive post-run report showing status for each version.
    طباعة تقرير نهائي كامل عن كل إصدار.
    """
    sep = "═" * 62
    print(f"\n{BOLD}{CYAN}{sep}")
    print(f"  📋  Odoo Cloner — Final Report")
    print(f"{sep}{RESET}\n")

    for r in results:
        ver      = r["ver"]
        odoo_dir = r["odoo_dir"]
        venv_dir = r["venv_dir"]
        conf     = r["conf_file"]
        status   = r["status"]   # "ok" | "clone_failed" | "venv_failed"

        icon = "✅" if status == "ok" else "❌"
        print(f"  {icon}  {BOLD}Odoo {ver}{RESET}"
              f"  [{VERSIONS[ver]['python']}  port={VERSIONS[ver]['port']}]")

        if status == "ok":
            print(f"     {CYAN}Dir   :{RESET}  {odoo_dir}")
            print(f"     {CYAN}Venv  :{RESET}  {venv_dir}")
            print(f"     {CYAN}Conf  :{RESET}  {conf}")
            print(f"\n     {YELLOW}# Run Odoo {ver}:{RESET}")
            print(f"     source {venv_dir}/bin/activate")
            print(f"     python {odoo_dir}/odoo-bin -c {conf} --dev=all")
            print(f"     # → http://localhost:{VERSIONS[ver]['port']}\n")
        else:
            print(f"     {RED}Status: {status}{RESET}\n")

    ok_count   = sum(1 for r in results if r["status"] == "ok")
    fail_count = len(results) - ok_count
    print(f"\n  {GREEN}{ok_count} succeeded{RESET}  |  "
          f"{RED}{fail_count} failed{RESET}")
    print(f"\n{BOLD}{CYAN}{sep}{RESET}\n")


# ─────────────────────────── Per-version installer ───────────────────────────
def install_version(
    ver: str,
    base_path: str,
    install_reqs: bool,
) -> dict:
    """
    Orchestrates the full installation for one Odoo version:
      1. Clone
      2. Virtualenv
      3. Requirements (optional)
      4. odoo.conf generation

    Returns a result dict for the final report.

    يدير كل خطوات تثبيت إصدار Odoo واحد ويرجع نتيجة للتقرير النهائي.
    """
    short    = ver.split(".")[0]
    meta     = VERSIONS[ver]
    py_bin   = meta["python"]
    port     = meta["port"]
    setuptools_ver = meta["setuptools"]

    odoo_dir = os.path.join(base_path, f"odoo{short}")
    venv_dir = os.path.join(odoo_dir, "venv")
    conf_file = os.path.join(odoo_dir, "odoo.conf")
    log_file  = os.path.join(odoo_dir, "odoo.log")

    result = {
        "ver":       ver,
        "odoo_dir":  odoo_dir,
        "venv_dir":  venv_dir,
        "conf_file": conf_file,
        "status":    "clone_failed",
    }

    # ── 1. Clone ─────────────────────────────────────────────────────────
    if not clone_odoo_version(ver, base_path):
        return result

    # ── 2. Virtualenv ────────────────────────────────────────────────────
    if not create_virtualenv(py_bin, venv_dir):
        result["status"] = "venv_failed"
        return result

    # ── 3. Requirements ──────────────────────────────────────────────────
    if install_reqs:
        req_file = os.path.join(odoo_dir, "requirements.txt")
        install_odoo_requirements(venv_dir, req_file, ver, setuptools_ver)

    # ── 4. Generate odoo.conf ────────────────────────────────────────────
    step(f"Generating odoo.conf for Odoo {ver}")
    db_user = f"odoo{short}"
    db_pass = f"odoo{short}"
    conf_content = (
        f"[options]\n"
        f"addons_path   = {os.path.join(odoo_dir, 'addons')}\n"
        f"admin_passwd  = admin\n"
        f"db_host       = localhost\n"
        f"db_port       = 5432\n"
        f"db_user       = {db_user}\n"
        f"db_password   = {db_pass}\n"
        f"db_name       = False\n"
        f"xmlrpc_port   = {port}\n"
        f"logfile       = {log_file}\n"
        f"log_level     = info\n"
        f"without_demo  = False\n"
    )
    Path(conf_file).write_text(conf_content, encoding="utf-8")
    ok(f"Config → {conf_file}")

    result["status"] = "ok"
    return result


# ─────────────────────────── MAIN ───────────────────────────────────────────
def main() -> None:
    title("🟣  Odoo Source Cloner — Connection Optimized (15.0 → 18.0)")

    # ── Pre-flight: internet check ───────────────────────────────────────
    step("Checking internet connectivity")
    if check_internet():
        ok("Internet connection available ✔")
    else:
        warn("No internet — waiting …")
        if not wait_for_internet("pre-flight check"):
            err("Cannot proceed without internet. Exiting.")
            sys.exit(1)

    # ── Pre-flight: git check ────────────────────────────────────────────
    if not shutil.which("git"):
        err("git is not installed. Run: sudo apt-get install -y git")
        sys.exit(1)
    ok(f"git found: {capture_output('git --version')}")

    # ── Apply global Git tuning ──────────────────────────────────────────
    configure_git_for_slow_internet()

    # ── Interactive selection ────────────────────────────────────────────
    title("📋  Select Odoo Versions to Clone")

    chosen_versions = ask_versions()
    info(f"Selected: {', '.join(chosen_versions)}")

    default_base = os.path.join(Path.home(), "Desktop") \
        if os.path.isdir(os.path.join(Path.home(), "Desktop")) \
        else str(Path.home())
    base_path = ask_path(default_base)
    os.makedirs(base_path, exist_ok=True)
    ok(f"Installation base: {base_path}")

    install_reqs = ask_install_reqs()

    # ── Confirm ──────────────────────────────────────────────────────────
    print(f"\n  {BOLD}Summary:{RESET}")
    print(f"    Versions : {', '.join(chosen_versions)}")
    print(f"    Base dir : {base_path}")
    print(f"    Install requirements: {'Yes' if install_reqs else 'No'}")
    ans = input(f"\n  {BOLD}{YELLOW}  Proceed? [Y/n]: {RESET}").strip().lower()
    if ans == "n":
        print("  Cancelled.")
        sys.exit(0)

    # ── Process each version ─────────────────────────────────────────────
    all_results: list[dict] = []

    for ver in chosen_versions:
        banner(f"Processing Odoo {ver}")
        result = install_version(ver, base_path, install_reqs)
        all_results.append(result)

    # ── Final report ─────────────────────────────────────────────────────
    print_final_report(all_results)


if __name__ == "__main__":
    main()
