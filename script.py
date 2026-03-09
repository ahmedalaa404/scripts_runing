#!/usr/bin/env python3
"""
╔════════════════════════════════════════════════════════════════╗
║            Odoo Multi-Version Interactive Installer            ║
║        Supports Ubuntu 20.04 / 22.04 / 24.04                  ║
║                                                                ║
║  Features:                                                     ║
║  • تثبيت أكتر من إصدار Odoo في نفس الوقت                     ║
║  • كل إصدار ليه DB user + pgAdmin server + service مستقل      ║
║  • Python مضبوط لكل إصدار تلقائياً                            ║
║  • setuptools==68.2.2 fix لـ Odoo 17/18/19                    ║
║  • pg_hba.conf يتضبط تلقائي                                   ║
║  • odoo.conf داخل مجلد الـ clone                              ║
║  • Report كامل في الـ home في الآخر                           ║
╚════════════════════════════════════════════════════════════════╝

Python per Odoo version:
  15 → 3.8  (fallback 3.9 — venv rebuilt auto on failure)
  16 → 3.10
  17 → 3.11  + setuptools==68.2.2 fix
  18 → 3.11  + setuptools==68.2.2 fix
  19 → 3.11  + setuptools==68.2.2 fix
"""

import subprocess, os, sys, getpass, datetime, shutil, time

# ═══════════════════════════ Colors ══════════════════════════════
G = "\033[92m"   # green
Y = "\033[93m"   # yellow
C = "\033[96m"   # cyan
R = "\033[91m"   # red
B = "\033[1m"    # bold
X = "\033[0m"    # reset

REPORT_LINES: list[str] = []
ISSUES: list[str] = []   # تجمع كل الأخطاء — تتطبع في الآخر بدل sys.exit

def add_issue(msg: str):
    """سجّل مشكلة للآخر بدل ما توقف السكريبت"""
    ISSUES.append(msg)
    err(f"[مشكلة سُجّلت] {msg}")

# ═══════════════════════════ Logging ═════════════════════════════
def title(msg):
    sep = "═" * 60
    print(f"\n{B}{C}{sep}\n  {msg}\n{sep}{X}")
    REPORT_LINES.append(f"\n{'═'*60}\n  {msg}\n{'═'*60}")

def section(msg):
    print(f"\n{B}{C}── {msg} ──{X}")
    REPORT_LINES.append(f"\n── {msg} ──")

def ok(msg):
    print(f"{G}  ✅ {msg}{X}")
    REPORT_LINES.append(f"  ✅ {msg}")

def warn(msg):
    print(f"{Y}  ⚠️  {msg}{X}")
    REPORT_LINES.append(f"  ⚠️  {msg}")

def err(msg):
    print(f"{R}  ❌ {msg}{X}")
    REPORT_LINES.append(f"  ❌ {msg}")

def info(msg):
    print(f"{C}  ℹ️  {msg}{X}")

# ═══════════════════════════ Shell helpers ════════════════════════
def run(cmd: str, check=True, silent=False, soft=False) -> subprocess.CompletedProcess:
    """
    soft=True  → لو فشل: سجّل في ISSUES وكمّل (بدون sys.exit)
    check=True → لو فشل: sys.exit (السلوك القديم)
    لو الأمر apt/pip وفشل بسبب النت → ينتظر ويعيد تلقائياً
    """
    is_network_cmd = any(x in cmd for x in
                         ["apt ", "apt-get ", "git clone", "curl ", "wget ", "pip install"])

    if not silent:
        print(f"\n{C}  ▶  {cmd}{X}\n")

    for attempt in range(1, 4):
        r = subprocess.run(cmd, shell=True, executable="/bin/bash",
                           capture_output=silent)
        if r.returncode == 0:
            return r

        # فشل — نتحقق هل السبب النت؟
        if is_network_cmd and attempt < 3 and not check_internet():
            warn(f"فشل (محاولة {attempt}/3) — النت مقطوع، ننتظر ...")
            if wait_for_internet(cmd[:60]):
                warn(f"النت رجع — محاولة {attempt + 1}/3 ...")
                continue
            else:
                # المستخدم اختار الخروج من الانتظار
                break
        else:
            break   # فشل بسبب تاني مش النت — وقّف

    # وصلنا هنا يعني فشل نهائي
    if silent and r.stderr:
        print(r.stderr.decode(errors="replace"))
    if soft:
        add_issue(f"أمر فشل (سيُكمل): {cmd[:120]}")
    elif check:
        err(f"فشل الأمر: {cmd}")
        sys.exit(1)
    return r

def run_ok(cmd: str) -> bool:
    return subprocess.run(cmd, shell=True, capture_output=True).returncode == 0

def capture(cmd: str) -> str:
    return subprocess.run(cmd, shell=True, capture_output=True,
                          text=True).stdout.strip()

def check_internet(timeout: int = 6) -> bool:
    """تحقق من وجود اتصال بالإنترنت"""
    r = subprocess.run(
        f"curl -s --max-time {timeout} https://github.com -o /dev/null -w '%{{http_code}}'",
        shell=True, capture_output=True, text=True)
    return r.stdout.strip().startswith("2") or r.stdout.strip().startswith("3")

def wait_for_internet(action: str = ""):
    """
    لو النت مش موجود — ينتظر ويحاول كل 15 ثانية.
    بيعرض رسالة للمستخدم ويديه خيار يكمل أو يوقف.
    """
    if check_internet():
        return True
    msg = f"انقطع الاتصال بالإنترنت"
    if action:
        msg += f" أثناء: {action}"
    warn(msg)
    print(f"\n{Y}  ⏳ الانتظار حتى يرجع الإنترنت ...{X}")
    print(f"  {C}(اضغط Ctrl+C مرتين للخروج){X}\n")
    attempt = 0
    while True:
        time.sleep(15)
        attempt += 1
        if check_internet():
            ok(f"✅ الإنترنت رجع بعد {attempt * 15} ثانية — هنكمل")
            return True
        print(f"  {Y}  محاولة {attempt} — لسه مش موجود ...{X}")
        if attempt % 4 == 0:   # كل دقيقة
            try:
                ans = input(
                    f"\n{B}{Y}  ❓ الإنترنت لسه مقطوع — تكمل الانتظار؟ [Y/n]: {X}"
                ).strip().lower()
                if ans == "n":
                    add_issue(f"تم التخطي بسبب انقطاع النت: {action}")
                    return False
            except (KeyboardInterrupt, EOFError):
                add_issue(f"تم الإيقاف يدوياً أثناء: {action}")
                return False

def is_clone_complete(odoo_dir: str) -> bool:
    """
    تحقق إن الـ clone مكتمل وصالح للاستخدام.
    لو النت فصل في النص، المجلد بيتعمل لكن ناقص.
    علامات الـ clone الكامل:
    - odoo-bin موجود
    - odoo/__init__.py موجود
    - requirements.txt موجود
    - .git موجود وفيه HEAD
    """
    checks = [
        os.path.isfile(os.path.join(odoo_dir, "odoo-bin")),
        os.path.isfile(os.path.join(odoo_dir, "odoo", "__init__.py")),
        os.path.isfile(os.path.join(odoo_dir, "requirements.txt")),
        os.path.isfile(os.path.join(odoo_dir, ".git", "HEAD")),
    ]
    return all(checks)

# ═══════════════════════════ Input helpers ════════════════════════
def ask_yn(q: str, default=None) -> bool:
    hint = " [Y/n]" if default is True else " [y/N]" if default is False else " (y/n)"
    while True:
        a = input(f"\n{B}{Y}  ❓ {q}{hint}: {X}").strip().lower()
        if not a and default is not None:
            return default
        if a in ("y", "yes", "ي", "ايوه", "ايوا", "نعم"):
            return True
        if a in ("n", "no", "لا"):
            return False
        print("     اكتب y أو n")

def ask_multi(prompt: str, choices: list, notes: list = None) -> list:
    """
    يعرض قايمة ويخلي المستخدم يختار أكتر من حاجة.
    مثال: 1,3,5 أو all أو 1-3
    """
    print(f"\n{B}  {prompt}{X}")
    for i, c in enumerate(choices, 1):
        note = f"  {Y}({notes[i-1]}){X}" if notes else ""
        print(f"    {C}{i}{X}) {c}{note}")
    print(f"    {C}a{X}) كل الإصدارات")
    print(f"\n  {Y}اكتب أرقام مفصولة بفاصلة (مثلاً: 1,3) أو a للكل:{X}")

    while True:
        raw = input("  اختيارك: ").strip().lower()
        if raw in ("a", "all", "كل", "الكل"):
            return choices[:]
        try:
            # support "1-3" ranges too
            selected = []
            for part in raw.split(","):
                part = part.strip()
                if "-" in part:
                    s, e = part.split("-")
                    selected += choices[int(s)-1 : int(e)]
                else:
                    selected.append(choices[int(part)-1])
            if selected:
                return selected
        except (ValueError, IndexError):
            pass
        print("     اختيار غير صحيح — جرب: 1,2 أو 1-3 أو a")

def ask_path(prompt: str, default: str) -> str:
    print(f"\n{B}  {prompt}{X}")
    print(f"  Default: {C}{default}{X}  (اضغط Enter للقبول)")
    raw = input("  المسار: ").strip()
    if not raw:
        return default
    if not os.path.isdir(raw):
        warn(f"'{raw}' مش موجود — هستخدم الـ default")
        return default
    return raw

# ═══════════════════════════ Constants ═══════════════════════════
PYTHON_MATRIX = {
    # version: (primary, fallback, note)
    "15.0": ("python3.8",  "python3.9",  "3.8 / fallback 3.9"),
    "16.0": ("python3.10", "python3.10", "3.10 stable"),
    "17.0": ("python3.11", "python3.11", "3.11 + setuptools fix"),
    "18.0": ("python3.11", "python3.11", "3.11 + setuptools fix"),
    "19.0": ("python3.11", "python3.11", "3.11 + setuptools fix"),
}
ODOO_PORTS = {
    "15.0": 8015, "16.0": 8016, "17.0": 8017,
    "18.0": 8018, "19.0": 8019,
}
# DB user per Odoo version — كل إصدار ليه user مستقل
ODOO_DB_USERS = {
    "15.0": ("odoo15", "odoo15"),
    "16.0": ("odoo16", "odoo16"),
    "17.0": ("odoo17", "odoo17"),
    "18.0": ("odoo18", "odoo18"),
    "19.0": ("odoo19", "odoo19"),
}

HOME         = os.path.expanduser("~")
CURRENT_USER = getpass.getuser()
NOW          = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

DESKTOP = os.path.join(HOME, "Desktop")
DEFAULT_BASE = DESKTOP if os.path.isdir(DESKTOP) else HOME

PGA_EMAIL = "admin@admin.com"
PGA_PASS  = "admin"

# ═══════════════════════════ OS Detection ════════════════════════
def detect_ubuntu() -> tuple[str, str]:
    ver  = capture("lsb_release -rs 2>/dev/null") or "22.04"
    name = capture("lsb_release -cs 2>/dev/null") or "jammy"
    return ver, name

# ═══════════════════════════ Python Install ═══════════════════════
def _py_exists(py: str) -> bool:
    return run_ok(f"which {py}")

def install_python_bin(py: str, ubuntu_ver: str) -> bool:
    if _py_exists(py):
        warn(f"{py} موجود بالفعل")
        return True

    major = ubuntu_ver.split(".")[0]
    info(f"تثبيت {py} على Ubuntu {ubuntu_ver} ...")

    run("sudo apt-get install -y software-properties-common", silent=True)
    run("sudo add-apt-repository ppa:deadsnakes/ppa -y", silent=True)
    run("sudo apt-get update -q", silent=True)

    if major == "24" and py in ("python3.8", "python3.9"):
        warn(f"Ubuntu 24 + {py}: pip يدوي بعد التثبيت")
        run(f"sudo apt-get install -y {py} {py}-venv {py}-dev", check=False)
        run(f'curl -sS https://bootstrap.pypa.io/pip/{py[6:]}/get-pip.py | sudo {py}',
            check=False)
    elif major == "20" and py == "python3.11":
        run(f"sudo apt-get install -y {py} {py}-venv {py}-dev {py}-distutils",
            check=False)
    else:
        run(f"sudo apt-get install -y {py} {py}-venv {py}-dev", check=False)

    if py in ("python3.8", "python3.9", "python3.10"):
        run(f"sudo apt-get install -y {py}-distutils", check=False)

    if _py_exists(py):
        ok(f"تم تثبيت {capture(f'{py} --version')}")
        return True
    err(f"فشل تثبيت {py}")
    return False

def ensure_python(odoo_ver: str, ubuntu_ver: str) -> str | None:
    primary, fallback, _ = PYTHON_MATRIX[odoo_ver]
    if install_python_bin(primary, ubuntu_ver):
        return primary
    if primary != fallback:
        warn(f"جارى تجربة fallback {fallback}")
        if install_python_bin(fallback, ubuntu_ver):
            return fallback
    add_issue(f"تعذر تثبيت Python لـ Odoo {odoo_ver} — تم تخطي هذا الإصدار")
    return None

# ═══════════════════════════ Venv & pip ══════════════════════════
def venv_pip(venv_dir: str, cmd: str):
    run(f"source {venv_dir}/bin/activate && {cmd}")

def create_venv(py: str, venv_dir: str):
    run(f"{py} -m venv {venv_dir}")

def base_pip_setup(venv_dir: str, odoo_ver: str):
    """pip upgrade + setuptools fix + psycopg2-binary + build tools"""
    venv_pip(venv_dir, "pip install --upgrade pip wheel")
    if odoo_ver in ("16.0", "17.0", "18.0", "19.0"):
        # ── مشكلة pkg_resources في Odoo 16/17/18/19 ──
        #
        # السبب: setuptools >= 69 شالت pkg_resources من الـ default path
        # المشكلة بتظهر في **مكانين**:
        #
        # 1) في الـ venv مباشرة → نحل بـ setuptools==68.2.2
        # 2) في الـ pip build subprocess (زي cbor2) → pip بيعمل
        #    بيئة مؤقتة (pip-build-env) بياخد فيها setuptools الجديد
        #    ومش بيورث الـ version اللي في الـ venv
        #
        # الحل: setuptools==68.2.2 + --no-build-isolation
        warn(f"Odoo {odoo_ver}: تثبيت setuptools==68.2.2 (pkg_resources fix)")
        venv_pip(venv_dir, "pip install setuptools==68.2.2")

        # تثبيت build dependencies يدوياً عشان --no-build-isolation يشتغل
        venv_pip(venv_dir, "pip install wheel setuptools==68.2.2 "
                           "flit_core pbr hatchling hatch-vcs")
    else:
        venv_pip(venv_dir, "pip install --upgrade setuptools")
    venv_pip(venv_dir, "pip install psycopg2-binary")


# ── الـ packages اللي Odoo بيحتاجها دايماً ──
# بعض الـ packages بتتـ skip أو بتفشل في الـ install العادي
# وبتظهر كـ ImportError لما Odoo يشتغل
# ده list شامل مبني على errors حقيقية ظهرت في التثبيت
CRITICAL_PACKAGES = {
    # كل الإصدارات
    "all": [
        "decorator",           # ImportError: No module named 'decorator'
        "passlib",             # login issues
        "babel",               # date/number formatting
        "lxml",                # XML processing
        "pillow",              # image processing
        "python-dateutil",     # date handling
        "pytz",                # timezone
        "requests",            # HTTP
        "werkzeug",            # WSGI
        "psycopg2-binary",     # PostgreSQL
        "pydot",               # graph generation
        "python-stdnum",       # VAT validation
        "vobject",             # vCard/iCal
        "xlrd",                # Excel read
        "xlwt",                # Excel write
        "PyYAML",              # YAML
        "chardet",             # encoding detection
        "cryptography",        # encryption
        "idna",                # internationalized domain names
        "urllib3",             # HTTP client
        "certifi",             # SSL certificates
        "polib",               # .po translation files
        "qrcode",              # QR code generation
        "reportlab",           # PDF generation
        "pypdf2",              # PDF manipulation
        "html2text",           # HTML to text
        "geoip2",              # GeoIP
        "libsass",             # SASS compiler
        "num2words",           # numbers to words
        "ofxparse",            # OFX financial files
        "Jinja2",              # templating
        "MarkupSafe",          # HTML escaping
        "greenlet",            # coroutines
    ],
    # خاص بـ Odoo 16/17/18/19
    "16+": [
        "cbor2",               # CBOR serialization
        "asn1crypto",          # ASN.1 parsing
        "pyOpenSSL",           # SSL
        "freezegun",           # time mocking (tests)
        "stdnum",              # alias for python-stdnum
        "rjsmin",              # JS minification
        "cssselect",           # CSS selectors
    ],
}

def verify_and_fix_packages(venv_dir: str, odoo_ver: str):
    """
    بعد تثبيت الـ requirements، بيتحقق إن كل الـ critical packages
    موجودة فعلاً — في call واحد بدل ما يعمل call لكل package.
    لو في حاجة ناقصة بيثبتها مباشرة.
    """
    section("التحقق من الـ critical packages")

    to_install = CRITICAL_PACKAGES["all"][:]
    if odoo_ver in ("16.0", "17.0", "18.0", "19.0"):
        to_install += CRITICAL_PACKAGES["16+"]

    # map: package name → import name
    IMPORT_MAP = {
        "pillow":           "PIL",
        "pyyaml":           "yaml",
        "pypdf2":           "PyPDF2",
        "pyopenssl":        "OpenSSL",
        "psycopg2-binary":  "psycopg2",
        "python-dateutil":  "dateutil",
        "python-stdnum":    "stdnum",
        "werkzeug":         "werkzeug",
        "libsass":          "sass",
        "markupsafe":       "markupsafe",
        "jinja2":           "jinja2",
    }

    # بناء script بيعمل import لكل الـ packages دفعة واحدة
    # وبيرجع list بالناقصين على stdout
    checks = []
    for pkg in to_install:
        key  = pkg.lower()
        iname = IMPORT_MAP.get(key, key.replace("-", "_"))
        checks.append(f"('{pkg}', '{iname}')")

    check_script = (
        "import sys\n"
        "missing = []\n"
        f"pairs = [{', '.join(checks)}]\n"
        "for pkg, mod in pairs:\n"
        "    try:\n"
        "        __import__(mod)\n"
        "    except ImportError:\n"
        "        missing.append(pkg)\n"
        "print('|'.join(missing))"
    )

    r = subprocess.run(
        f"source {venv_dir}/bin/activate && python -c \"{check_script}\"",
        shell=True, executable="/bin/bash",
        capture_output=True, text=True)

    raw = r.stdout.strip()
    missing = [p for p in raw.split("|") if p]

    if not missing:
        ok("كل الـ critical packages موجودة ✔")
        return

    warn(f"packages ناقصة ({len(missing)}): {', '.join(missing)}")

    # ثبّت الناقصين دفعة واحدة أولاً
    pkgs_str = " ".join(f'"{p}"' for p in missing)
    r2 = subprocess.run(
        f"source {venv_dir}/bin/activate && "
        f"pip install {pkgs_str} --no-build-isolation",
        shell=True, executable="/bin/bash")

    if r2.returncode == 0:
        ok(f"تم تثبيت {len(missing)} packages ناقصة ✔")
        return

    # لو فشلت دفعة — جرّب كل package لوحده
    failed = []
    for pkg in missing:
        r3 = subprocess.run(
            f"source {venv_dir}/bin/activate && "
            f"pip install \"{pkg}\" --no-build-isolation",
            shell=True, executable="/bin/bash", capture_output=True)
        if r3.returncode == 0:
            ok(f"  ✅ {pkg}")
        else:
            failed.append(pkg)
            warn(f"  ❌ {pkg} فشل")

    if failed:
        add_issue(
            f"Odoo {odoo_ver}: packages ناقصة فشل تثبيتها — شغّل يدوياً:\n"
            + "\n".join(
                f"     source {venv_dir}/bin/activate && "
                f"pip install \"{p}\"" for p in failed
            )
        )


def _pip_install_req(venv_dir: str, req_file: str,
                     odoo_ver: str, extra_flags: str = "") -> bool:
    """
    تثبيت requirements مع الـ flags الصح لكل إصدار.
    Odoo 16/17/18/19 → --no-build-isolation
    لو فشل بسبب النت → ينتظر ويعيد تلقائياً (حتى 3 مرات)
    """
    if odoo_ver in ("16.0", "17.0", "18.0", "19.0"):
        flags = "--no-build-isolation " + extra_flags
    else:
        flags = extra_flags

    for attempt in range(1, 4):
        r = subprocess.run(
            f"source {venv_dir}/bin/activate && "
            f"pip install -r {req_file} {flags}",
            shell=True, executable="/bin/bash")
        if r.returncode == 0:
            return True

        # نتحقق هل الفشل بسبب النت؟
        if attempt < 3:
            if not check_internet():
                warn(f"pip فشل (محاولة {attempt}/3) — النت مقطوع، ننتظر ...")
                if not wait_for_internet(f"pip install requirements Odoo {odoo_ver}"):
                    return False
                warn(f"النت رجع — محاولة {attempt + 1}/3 ...")
            else:
                # فشل بسبب حاجة تانية مش النت — منتظرش
                return False
    return False

def install_requirements(venv_dir: str, req_file: str,
                          odoo_ver: str, py_bin: str,
                          ubuntu_ver: str) -> str:
    base_pip_setup(venv_dir, odoo_ver)

    section("تثبيت requirements.txt")

    # المحاولة الأولى — مع --no-build-isolation لـ Odoo 17/18/19
    if _pip_install_req(venv_dir, req_file, odoo_ver):
        ok("تم تثبيت كل الـ requirements")
    else:
        # المحاولة الثانية — مع --ignore-requires-python برضو
        warn("المحاولة الأولى فشلت — هنجرب مع --ignore-requires-python")
        if _pip_install_req(venv_dir, req_file, odoo_ver,
                            "--ignore-requires-python"):
            ok("requirements تم (مع ignore pins)")
        elif odoo_ver == "15.0" and py_bin == "python3.8":
            # Odoo 15 fallback: امسح venv وأعد بـ 3.9
            warn("Odoo 15 + 3.8 فشل — بنعيد البناء بـ python3.9")
            shutil.rmtree(venv_dir, ignore_errors=True)
            if install_python_bin("python3.9", ubuntu_ver):
                create_venv("python3.9", venv_dir)
                base_pip_setup(venv_dir, odoo_ver)
                if _pip_install_req(venv_dir, req_file, odoo_ver,
                                    "--ignore-requires-python"):
                    ok("تم إعادة البناء بـ python3.9")
                    py_bin = "python3.9"
                else:
                    add_issue(
                        f"Odoo {odoo_ver}: فشل requirements حتى مع python3.9")
            else:
                add_issue(f"Odoo {odoo_ver}: فشل تثبيت python3.9")
        else:
            add_issue(
                f"Odoo {odoo_ver}: فشل تثبيت requirements — شغّل يدوياً:\n"
                f"     source {venv_dir}/bin/activate\n"
                f"     pip install setuptools==68.2.2\n"
                f"     pip install -r {req_file} --no-build-isolation")

    # ── التحقق من الـ critical packages بعد الـ requirements ──
    # حتى لو الـ requirements اتثبتت، في packages ممكن تكون اتـ skip
    # أو فشلت بصمت وبتطلع ImportError لما Odoo يشتغل (زي decorator)
    verify_and_fix_packages(venv_dir, odoo_ver)

    return py_bin

# ═══════════════════════════ PostgreSQL helpers ═══════════════════
def pg_create_user(db_user: str, db_pass: str) -> bool:
    """
    إنشاء أو تحديث يوزر في PostgreSQL.
    بيكتب SQL في ملف temp وبيشغّله بـ sudo -u postgres psql
    عشان يستخدم peer authentication (مش password) ويتجنب
    مشكلة $$ و shell quoting كلها.
    """
    sql = (
        f"DO $body$\n"
        f"BEGIN\n"
        f"  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='{db_user}') THEN\n"
        f"    CREATE ROLE {db_user} WITH LOGIN CREATEDB PASSWORD '{db_pass}';\n"
        f"  ELSE\n"
        f"    ALTER  ROLE {db_user} WITH LOGIN CREATEDB PASSWORD '{db_pass}';\n"
        f"  END IF;\n"
        f"END\n"
        f"$body$;\n"
    )
    # نكتب SQL في ملف temp يقدر postgres يقراه
    sql_file = f"/tmp/pg_create_{db_user}.sql"
    try:
        with open(sql_file, "w") as f:
            f.write(sql)
        # sudo chmod عشان postgres يقدر يقراه
        subprocess.run(f"chmod 644 {sql_file}", shell=True)
        r = subprocess.run(
            f"sudo -u postgres psql -f {sql_file}",
            shell=True, capture_output=True, text=True)
        if r.returncode == 0:
            return True
        err(f"pg_create_user({db_user}): {r.stderr.strip()[:200]}")
        return False
    finally:
        # امسح الـ SQL file بعد الاستخدام
        subprocess.run(f"rm -f {sql_file}", shell=True)

def pg_fix_hba() -> str:
    """
    ضبط pg_hba.conf:
    - local   peer  → md5
    - host    lines → md5  (أو إضافتهم لو مش موجودين)
    ده بيضمن إن psql -h localhost يشتغل صح
    """
    hba = capture(
        "sudo find /etc/postgresql -name pg_hba.conf 2>/dev/null "
        "| sort | tail -1")
    if not hba:
        hba = capture(
            "sudo find /var/lib/pgsql -name pg_hba.conf 2>/dev/null | tail -1")
    if not hba:
        warn("pg_hba.conf مش موجود — auth قد تحتاج ضبط يدوي")
        return "not found"

    # local peer → md5
    run(f"sudo sed -i 's/^local\\(.*\\)peer$/local\\1md5/' {hba}", check=False)
    # host scram-sha-256 → md5
    run(f"sudo sed -i 's/^host\\(.*\\)scram-sha-256$/host\\1md5/' {hba}",
        check=False)

    # تحقق إن host 127.0.0.1 موجود بـ md5 — لو مش موجود أضفه
    has_host = capture(
        f"sudo grep -c '^host.*127.0.0.1.*md5' {hba} 2>/dev/null") or "0"
    if has_host.strip() == "0":
        run(f"sudo sh -c 'echo \""
            f"host    all             all             127.0.0.1/32            md5\n"
            f"host    all             all             ::1/128                 md5"
            f"\" >> {hba}'", check=False)
        ok("أضفنا host md5 lines لـ 127.0.0.1 و ::1")

    run("sudo systemctl restart postgresql")
    ok(f"pg_hba.conf → md5  ({hba})")
    return hba

def pg_test_connection(db_user: str, db_pass: str) -> bool:
    """
    اختبار الاتصال بـ PostgreSQL.
    بيجرب -h localhost (md5) ولو فشل بيجرب peer عن طريق postgres
    """
    # الطريقة الأساسية: md5 عبر localhost
    r = subprocess.run(
        f'psql -U {db_user} -h 127.0.0.1 -c "SELECT 1" postgres',
        shell=True, capture_output=True,
        env={**os.environ, "PGPASSWORD": db_pass})
    if r.returncode == 0:
        return True
    # fallback: peer عبر sudo
    r2 = subprocess.run(
        f'sudo -u postgres psql -U {db_user} -c "SELECT 1" postgres',
        shell=True, capture_output=True)
    return r2.returncode == 0

# ═══════════════════════════ pgAdmin server reg ═══════════════════
def pgadmin_register_server(name: str, db_user: str, db_pass: str,
                             port: int = 5432):
    """
    يضيف سيرفر في pgAdmin4 SQLite DB تلقائياً.
    بيكتب الـ Python في ملف temp بدل sudo python3 -c "..."
    عشان يتجنب Syntax error: "(" unexpected من الـ shell
    """
    pga_db = capture(
        "sudo find /var/lib/pgadmin /home -name 'pgadmin4.db' "
        "2>/dev/null | head -1")
    if not pga_db:
        warn(f"pgAdmin DB مش موجود — أضف '{name}' يدوياً (localhost:{port})")
        return

    # بنكتب script في ملف حقيقي عشان نتجنب shell quoting كاملاً
    script_path = f"/tmp/pga_reg_{db_user.replace('.','_')}.py"
    script_lines = [
        "import sqlite3\n",
        f"conn = sqlite3.connect(r'{pga_db}')\n",
        "cur  = conn.cursor()\n",
        f"cur.execute('SELECT COUNT(*) FROM server WHERE name=?', ('{name}',))\n",
        "if cur.fetchone()[0] == 0:\n",
        "    cur.execute(\n",
        "        'INSERT INTO server '\n",
        "        '(user_id,servergroup_id,name,host,port,maintenance_db,'\n",
        "        'username,ssl_mode,connect_timeout,tunnel_port) '\n",
        "        'VALUES (1,1,?,?,?,?,?,?,?,?)',\n",
        f"        ('{name}', 'localhost', {port}, 'postgres',\n",
        f"         '{db_user}', 'prefer', 10, 22)\n",
        "    )\n",
        "    conn.commit()\n",
        "    print('added')\n",
        "else:\n",
        "    print('exists')\n",
        "conn.close()\n",
    ]
    try:
        with open(script_path, "w") as f:
            f.writelines(script_lines)
        r = subprocess.run(
            f"sudo python3 {script_path}",
            shell=True, capture_output=True, text=True)
        if "added" in r.stdout:
            ok(f"pgAdmin: تم إضافة سيرفر '{name}'")
        elif "exists" in r.stdout:
            warn(f"pgAdmin: '{name}' موجود بالفعل")
        else:
            warn(f"pgAdmin register فشل: {r.stderr.strip()[:120]}")
    finally:
        subprocess.run(f"rm -f {script_path}", shell=True)

# ═══════════════════════════ Odoo installer ═══════════════════════
def install_odoo_version(ver: str, base_path: str,
                         ubuntu_ver: str, ubuntu_name: str,
                         installed_versions: list) -> dict | None:
    """
    يثبت إصدار Odoo واحد كامل.
    لو حصل أي error → يسجّله في ISSUES ويكمل (مش بيوقف).
    يرجع None لو فشل فشل كامل.
    """
    short     = ver.split(".")[0]
    db_user, db_pass = ODOO_DB_USERS[ver]
    port      = ODOO_PORTS[ver]
    odoo_dir  = os.path.join(base_path, f"odoo{short}")

    # ── كل حاجة داخل مجلد الـ clone مع بعض ──
    # odoo17/
    # ├── venv/          ← virtualenv جوا
    # ├── odoo.conf      ← config جوا
    # ├── odoo.log       ← log جوا (مع rotate تلقائي)
    # └── addons/ ...    ← source code
    venv_dir  = os.path.join(odoo_dir, "venv")
    conf_file = os.path.join(odoo_dir, "odoo.conf")
    log_file  = os.path.join(odoo_dir, "odoo.log")
    service   = f"odoo{short}"

    title(f"🟣 تثبيت Odoo {ver}")

    try:
        # ── Python ──
        section(f"Python لـ Odoo {ver}")
        py_bin = ensure_python(ver, ubuntu_ver)
        if py_bin is None:
            # المشكلة اتسجلت في ensure_python — تخطي هذا الإصدار
            return None
        ok(f"Python: {py_bin}  ({capture(f'{py_bin} --version')})")

        # ── Clone ──
        section("Clone")
        clone_needed = False
        if not os.path.isdir(odoo_dir):
            clone_needed = True
        elif not is_clone_complete(odoo_dir):
            warn(f"{odoo_dir} موجود لكن ناقص (النت فصل في النص؟) — هنمسحه ونعيد")
            import shutil as _sh
            _sh.rmtree(odoo_dir, ignore_errors=True)
            clone_needed = True
        else:
            warn(f"{odoo_dir} موجود ومكتمل — تخطي clone")

        if clone_needed:
            # تحقق من النت قبل الـ clone
            if not wait_for_internet(f"git clone Odoo {ver}"):
                add_issue(f"Odoo {ver}: تخطي clone بسبب انقطاع النت")
                return None

            for attempt in range(1, 4):   # 3 محاولات
                r = run(
                    f"git clone https://github.com/odoo/odoo.git "
                    f"--depth 1 --branch {ver} {odoo_dir}",
                    check=False)
                if r.returncode == 0 and is_clone_complete(odoo_dir):
                    ok(f"Clone → {odoo_dir}")
                    break
                # فشل أو ناقص
                if attempt < 3:
                    warn(f"Clone فشل (محاولة {attempt}/3) — "
                         f"نتحقق من النت وننتظر ...")
                    import shutil as _sh
                    _sh.rmtree(odoo_dir, ignore_errors=True)
                    if not wait_for_internet(f"إعادة clone Odoo {ver}"):
                        add_issue(f"Odoo {ver}: فشل clone بعد {attempt} محاولات")
                        return None
                else:
                    add_issue(
                        f"Odoo {ver}: git clone فشل بعد 3 محاولات — "
                        f"شغّل يدوياً:\n"
                        f"     git clone https://github.com/odoo/odoo.git "
                        f"--depth 1 --branch {ver} {odoo_dir}")
                    return None

        # ── Virtualenv ──
        section("Virtualenv")
        if not os.path.isdir(venv_dir):
            r = run(f"{py_bin} -m venv {venv_dir}", check=False)
            if r.returncode != 0:
                add_issue(f"Odoo {ver}: فشل إنشاء venv بـ {py_bin}")
                return None
            ok(f"venv → {venv_dir}")
        else:
            warn(f"{venv_dir} موجود")

        # ── Requirements ──
        req_file = os.path.join(odoo_dir, "requirements.txt")
        py_bin   = install_requirements(venv_dir, req_file,
                                        ver, py_bin, ubuntu_ver)

        # ── DB user ──
        section(f"DB user: {db_user}")
        if not pg_create_user(db_user, db_pass):
            add_issue(f"Odoo {ver}: فشل إنشاء DB user {db_user} — "
                      f"شغّل يدوياً: sudo -u postgres createuser "
                      f"--createdb --login {db_user}")
        else:
            ok(f"PostgreSQL user: {db_user} / {db_pass}")

        # ── odoo.conf داخل الـ clone ──
        section("odoo.conf")
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
        with open(conf_file, "w") as f:
            f.write(conf_content)
        ok(f"Config → {conf_file}")

        # ── logrotate — عشان الـ log ما يكبرش لأنهاية ──
        # بيعمل rotate يومي، بيحتفظ بـ 30 يوم، بيضغطهم
        logrotate_conf = (
            f"{log_file} {{\n"
            f"    daily\n"                   # rotate يومياً
            f"    rotate 30\n"              # احتفظ بـ 30 نسخة = شهر
            f"    compress\n"               # اضغط الـ logs القديمة (.gz)
            f"    delaycompress\n"          # أخّر الضغط ليوم واحد بعد الـ rotate
            f"    missingok\n"              # متوقفش لو الملف مش موجود
            f"    notifempty\n"             # متعملش rotate لو الملف فاضي
            f"    copytruncate\n"           # انسخ وفرّغ بدل ما تنقل (عشان Odoo فاتح الملف)
            f"    su {CURRENT_USER} {CURRENT_USER}\n"
            f"}}\n"
        )
        logrotate_path = f"/etc/logrotate.d/{service}"
        tmp_lr = f"/tmp/{service}_logrotate"
        with open(tmp_lr, "w") as f:
            f.write(logrotate_conf)
        run(f"sudo mv {tmp_lr} {logrotate_path}", soft=True)
        run(f"sudo chmod 644 {logrotate_path}", soft=True)
        ok(f"logrotate → {logrotate_path}  (daily, 30 days, compressed)")

        # ── systemd service ──
        section(f"systemd service: {service}")
        svc_content = (
            f"[Unit]\n"
            f"Description=Odoo {ver}\n"
            f"After=network.target postgresql.service\n\n"
            f"[Service]\n"
            f"Type=simple\n"
            f"User={CURRENT_USER}\n"
            f"WorkingDirectory={odoo_dir}\n"
            f"ExecStart={venv_dir}/bin/python {odoo_dir}/odoo-bin "
            f"-c {conf_file}\n"
            f"Restart=on-failure\n"
            f"RestartSec=5\n"
            f"StandardOutput=journal\n"
            f"StandardError=journal\n\n"
            f"[Install]\n"
            f"WantedBy=multi-user.target\n"
        )
        tmp_svc = f"/tmp/{service}.service"
        with open(tmp_svc, "w") as f:
            f.write(svc_content)
        run(f"sudo mv {tmp_svc} /etc/systemd/system/{service}.service", soft=True)
        run("sudo systemctl daemon-reload", soft=True)
        run(f"sudo systemctl enable {service}", soft=True)
        run(f"sudo systemctl start {service}", soft=True)

        time.sleep(4)
        status = capture(f"sudo systemctl is-active {service}")
        if status == "active":
            ok(f"Odoo {ver} شغال ✔  → http://localhost:{port}")
        else:
            add_issue(f"Odoo {ver}: service status='{status}' — "
                      f"راجع: sudo journalctl -u {service} -f")

        run(f"sudo systemctl status {service} --no-pager", check=False)

        return {
            "ver": ver, "py_bin": py_bin, "port": port,
            "odoo_dir": odoo_dir, "venv_dir": venv_dir,
            "conf_file": conf_file, "log_file": log_file,
            "service": service, "db_user": db_user, "db_pass": db_pass,
            "status": status,
        }

    except Exception as ex:
        add_issue(f"Odoo {ver}: خطأ غير متوقع — {ex}")
        return None

# ════════════════════════════════════════════════════════════════
#  MAIN
# ════════════════════════════════════════════════════════════════

print(f"""{B}{C}
╔════════════════════════════════════════════════════════════════╗
║          Odoo Multi-Version Interactive Installer              ║
╚════════════════════════════════════════════════════════════════╝
{X}""")

UBUNTU_VER, UBUNTU_NAME = detect_ubuntu()
print(f"{C}  🖥️  Ubuntu : {UBUNTU_VER} ({UBUNTU_NAME}){X}")
print(f"{C}  👤 User   : {CURRENT_USER}{X}\n")
REPORT_LINES += [f"Date  : {NOW}",
                 f"Ubuntu: {UBUNTU_VER} ({UBUNTU_NAME})",
                 f"User  : {CURRENT_USER}"]

# ─────────────────────── Step 0: اختيارات ───────────────────────
title("📋 اختار المكونات")

DO_SYSTEM   = ask_yn("تثبيت الحزم الأساسية للنظام؟", default=True)
DO_POSTGRES = ask_yn("تثبيت PostgreSQL؟", default=True)
DO_PGADMIN  = ask_yn("تثبيت pgAdmin 4؟", default=True)
DO_ODOO     = ask_yn("تثبيت Odoo؟", default=True)

chosen_versions: list[str] = []
BASE_PATH = DEFAULT_BASE

if DO_ODOO:
    all_vers  = list(PYTHON_MATRIX.keys())
    all_notes = [PYTHON_MATRIX[v][2] for v in all_vers]
    chosen_versions = ask_multi(
        "اختار إصدارات Odoo (ممكن تختار أكتر من واحد):",
        all_vers, all_notes)

    BASE_PATH = ask_path(
        "مسار تثبيت Odoo (الـ clone والـ venv هيتحطوا جوا):",
        DEFAULT_BASE)

# ─────────────────────── ملخص ───────────────────────────────────
title("📝 ملخص")
print(f"  Ubuntu          : {UBUNTU_VER} ({UBUNTU_NAME})")
print(f"  الحزم الأساسية : {'✅' if DO_SYSTEM   else '❌'}")
print(f"  PostgreSQL      : {'✅' if DO_POSTGRES else '❌'}")
print(f"  pgAdmin 4       : {'✅' if DO_PGADMIN  else '❌'}")
if DO_ODOO:
    for v in chosen_versions:
        db_u, db_p = ODOO_DB_USERS[v]
        py = PYTHON_MATRIX[v][0]
        print(f"  Odoo {v}        : ✅  py={py}  port={ODOO_PORTS[v]}"
              f"  db={db_u}/{db_p}")
    print(f"  Install path    : {BASE_PATH}")
else:
    print(f"  Odoo            : ❌")

if not ask_yn("\nتأكيد — تكمل؟", default=True):
    print("  تم الإلغاء.")
    sys.exit(0)

# ═══════════════════════ Step 1: System Deps ═════════════════════
if DO_SYSTEM:
    title("📦 الحزم الأساسية  (بدون apt upgrade)")
    run("sudo apt-get update -q")
    run("sudo apt-get install -y git wget curl build-essential "
        "software-properties-common gnupg2 lsb-release ca-certificates")

    if DO_ODOO:
        run("sudo apt-get install -y python3-pip "
            "libxslt-dev libzip-dev libldap2-dev libsasl2-dev "
            "python3-setuptools node-less libjpeg-dev "
            "zlib1g-dev libpq-dev libxml2-dev libssl-dev")

        # wkhtmltopdf — package مختلف لكل Ubuntu
        major = UBUNTU_VER.split(".")[0]
        WK = {
            "20": "https://github.com/wkhtmltopdf/packaging/releases/download"
                  "/0.12.6.1-2/wkhtmltox_0.12.6.1-2.focal_amd64.deb",
            "22": "https://github.com/wkhtmltopdf/packaging/releases/download"
                  "/0.12.6.1-2/wkhtmltox_0.12.6.1-2.jammy_amd64.deb",
            "24": "https://github.com/wkhtmltopdf/packaging/releases/download"
                  "/0.12.6.1-2/wkhtmltox_0.12.6.1-2.jammy_amd64.deb",
        }
        wk_url = WK.get(major, WK["22"])
        if major == "24":
            warn("Ubuntu 24: wkhtmltopdf من jammy (متوافق)")
        run(f"wget -q {wk_url} -O /tmp/wkhtmltox.deb")
        run("sudo apt-get install -y /tmp/wkhtmltox.deb || sudo apt-get -yf install")

    ok("تم تثبيت الحزم الأساسية")
    REPORT_LINES.append("[System] ✅")
else:
    warn("تخطي الحزم الأساسية")
    REPORT_LINES.append("[System] ❌ skipped")

# ═══════════════════════ Step 2: PostgreSQL ══════════════════════
PG_HBA = "not found"

if DO_POSTGRES:
    title("🐘 PostgreSQL")
    run("sudo apt-get install -y postgresql postgresql-contrib")
    run("sudo systemctl enable postgresql --now")

    # يوزر admin عام للـ pgAdmin
    pg_create_user("admin", "admin")
    ok("PostgreSQL admin user: admin / admin")

    # يوزر لكل إصدار Odoo
    if DO_ODOO:
        for v in chosen_versions:
            du, dp = ODOO_DB_USERS[v]
            pg_create_user(du, dp)

    # pg_hba.conf fix
    PG_HBA = pg_fix_hba()

    # test
    if pg_test_connection("admin", "admin"):
        ok("اتصال PostgreSQL ✔")
    else:
        warn("الاتصال فشل — راجع pg_hba.conf يدوياً")

    PG_VER = capture("psql --version")
    REPORT_LINES += [f"[PostgreSQL] ✅ {PG_VER}",
                     f"[PostgreSQL] admin / admin",
                     f"[PostgreSQL] pg_hba={PG_HBA}"]
else:
    warn("تخطي PostgreSQL")
    REPORT_LINES.append("[PostgreSQL] ❌ skipped")

# ═══════════════════════ Step 3: pgAdmin 4 ═══════════════════════
if DO_PGADMIN:
    title("🖥️  pgAdmin 4")
    major = UBUNTU_VER.split(".")[0]

    PGA_CODENAMES = {"20": "focal", "22": "jammy", "24": "noble"}
    codename = PGA_CODENAMES.get(major, UBUNTU_NAME)

    # لو الـ key موجود بالفعل نمسحه أولاً عشان gpg ما يسألش
    run("sudo rm -f /usr/share/keyrings/pgadmin.gpg", check=False)
    run("curl -fsS https://www.pgadmin.org/static/packages_pgadmin_org.pub "
        "| sudo gpg --dearmor -o /usr/share/keyrings/pgadmin.gpg")
    run(f"sudo sh -c 'echo \"deb [signed-by=/usr/share/keyrings/pgadmin.gpg] "
        f"https://ftp.postgresql.org/pub/pgadmin/pgadmin4/apt/{codename} "
        f"pgadmin4 main\" > /etc/apt/sources.list.d/pgadmin4.list'")
    run("sudo apt-get update -q")
    r = subprocess.run("sudo apt-get install -y pgadmin4-web",
                       shell=True)
    if r.returncode != 0 and major == "24":
        warn("noble فشل — fallback إلى jammy")
        run("sudo sh -c 'echo \"deb [signed-by=/usr/share/keyrings/pgadmin.gpg] "
            "https://ftp.postgresql.org/pub/pgadmin/pgadmin4/apt/jammy "
            "pgadmin4 main\" > /etc/apt/sources.list.d/pgadmin4.list'")
        run("sudo apt-get update -q")
        run("sudo apt-get install -y pgadmin4-web")

    run(f'sudo bash -c "PGADMIN_SETUP_EMAIL=\'{PGA_EMAIL}\' '
        f'PGADMIN_SETUP_PASSWORD=\'{PGA_PASS}\' '
        f'/usr/pgadmin4/bin/setup-web.sh --yes"')

    ok(f"pgAdmin → http://localhost/pgadmin4  |  {PGA_EMAIL} / {PGA_PASS}")

    # أضف سيرفر admin عام
    pgadmin_register_server("Local PostgreSQL (admin)", "admin", "admin")

    # أضف سيرفر لكل إصدار Odoo
    if DO_ODOO:
        for v in chosen_versions:
            du, dp = ODOO_DB_USERS[v]
            pgadmin_register_server(f"Odoo {v} DB", du, dp)

    REPORT_LINES += [f"[pgAdmin] ✅ http://localhost/pgadmin4",
                     f"[pgAdmin] {PGA_EMAIL} / {PGA_PASS}"]
else:
    warn("تخطي pgAdmin")
    REPORT_LINES.append("[pgAdmin] ❌ skipped")

# ═══════════════════════ Step 4: Odoo (multi) ════════════════════
installed_info: list[dict] = []

if DO_ODOO:
    os.makedirs(BASE_PATH, exist_ok=True)

    for ver in chosen_versions:
        info_dict = install_odoo_version(
            ver, BASE_PATH, UBUNTU_VER, UBUNTU_NAME, installed_info)

        if info_dict is None:
            # المشكلة اتسجلت بالفعل في ISSUES — نكمل للإصدار الجاي
            warn(f"تم تخطي Odoo {ver} بسبب خطأ — راجع ملخص المشاكل في الآخر")
            continue

        installed_info.append(info_dict)

        if DO_PGADMIN:
            pgadmin_register_server(
                f"Odoo {ver} DB",
                info_dict["db_user"],
                info_dict["db_pass"])

        REPORT_LINES += [
            f"[Odoo {ver}] ✅ python={info_dict['py_bin']}",
            f"[Odoo {ver}] port={info_dict['port']}",
            f"[Odoo {ver}] dir={info_dict['odoo_dir']}",
            f"[Odoo {ver}] venv={info_dict['venv_dir']}",
            f"[Odoo {ver}] conf={info_dict['conf_file']}",
            f"[Odoo {ver}] log={info_dict['log_file']}",
            f"[Odoo {ver}] service={info_dict['service']}",
            f"[Odoo {ver}] db={info_dict['db_user']}/{info_dict['db_pass']}",
            f"[Odoo {ver}] status={info_dict['status']}",
        ]
else:
    warn("تخطي Odoo")
    REPORT_LINES.append("[Odoo] ❌ skipped")

# ═══════════════ آخر خطوة: فحص DB users في PostgreSQL ═══════════
# ده بيتعمل في الآخر خالص بعد انتهاء كل حاجة
title("🔍 فحص نهائي — التحقق من DB users في PostgreSQL")

DB_CHECK_RESULTS = []

if DO_POSTGRES and installed_info:
    section("التحقق من يوزر admin العام")
    if pg_test_connection("admin", "admin"):
        ok("admin / admin  ✔  موجود ويشتغل")
        DB_CHECK_RESULTS.append(("admin", "admin", "✅"))
    else:
        warn("admin موجود لكن الاتصال فشل — هنعيد إنشاءه")
        pg_create_user("admin", "admin")
        run("sudo systemctl restart postgresql")
        if pg_test_connection("admin", "admin"):
            ok("admin  ✔  تم الإصلاح")
            DB_CHECK_RESULTS.append(("admin", "admin", "✅ (fixed)"))
        else:
            err("admin  ✘  فشل — راجع pg_hba.conf يدوياً")
            DB_CHECK_RESULTS.append(("admin", "admin", "❌"))

    for d in installed_info:
        section(f"التحقق من يوزر {d['db_user']} (Odoo {d['ver']})")
        # هل اليوزر موجود في PostgreSQL أصلاً؟
        exists = capture(
            f"sudo -u postgres psql -tAc "
            f"\"SELECT 1 FROM pg_roles WHERE rolname='{d['db_user']}';\""
        ).strip() == "1"

        if not exists:
            warn(f"{d['db_user']} مش موجود في PostgreSQL — هنعمله دلوقتي")
            pg_create_user(d["db_user"], d["db_pass"])
            ok(f"تم إنشاء {d['db_user']}")

        # اختبار الاتصال
        if pg_test_connection(d["db_user"], d["db_pass"]):
            ok(f"{d['db_user']} / {d['db_pass']}  ✔  موجود ويشتغل")
            DB_CHECK_RESULTS.append((d["db_user"], d["db_pass"], "✅"))
        else:
            warn(f"{d['db_user']} موجود لكن الاتصال فشل — هنعيد ضبط الباسورد")
            pg_create_user(d["db_user"], d["db_pass"])
            run("sudo systemctl restart postgresql")
            if pg_test_connection(d["db_user"], d["db_pass"]):
                ok(f"{d['db_user']}  ✔  تم الإصلاح")
                DB_CHECK_RESULTS.append((d["db_user"], d["db_pass"], "✅ (fixed)"))
            else:
                err(f"{d['db_user']}  ✘  فشل")
                DB_CHECK_RESULTS.append((d["db_user"], d["db_pass"], "❌"))

    REPORT_LINES.append("\n── DB Users Final Check ──")
    for u, p, s in DB_CHECK_RESULTS:
        REPORT_LINES.append(f"  {s}  {u} / {p}")
else:
    warn("تخطي فحص DB users (PostgreSQL مش متثبت أو مفيش Odoo)")

# ═══════════════════════ Report File ═════════════════════════════
REPORT_PATH = os.path.join(HOME, "odoo_setup_report.txt")

# بناء قسم كل إصدار Odoo في الـ report
odoo_blocks = ""
for d in installed_info:
    odoo_blocks += f"""
┌─ Odoo {d['ver']} {'─'*46}
│  URL          : http://localhost:{d['port']}
│  Master PW    : admin
│  DB User      : {d['db_user']}
│  DB Password  : {d['db_pass']}
│  Python       : {d['py_bin']}
│  Source dir   : {d['odoo_dir']}
│  Virtualenv   : {d['venv_dir']}
│  Config file  : {d['conf_file']}  ← داخل الـ clone
│  Log file     : {d['log_file']}
│  Service      : {d['service']}
│  Status       : {d['status']}
└{'─'*56}
  sudo systemctl start   {d['service']}
  sudo systemctl stop    {d['service']}
  sudo systemctl restart {d['service']}
  sudo journalctl -u {d['service']} -f
  # debug manual:
  source {d['venv_dir']}/bin/activate
  python {d['odoo_dir']}/odoo-bin -c {d['conf_file']}
"""

pg_block = ""
if DO_POSTGRES:
    pg_block = f"""
┌─ PostgreSQL {'─'*47}
│  Admin user   : admin / admin
│  pg_hba.conf  : {PG_HBA}
│  Per-version users:
""" + "".join(
    f"│    Odoo {v}: {ODOO_DB_USERS[v][0]} / {ODOO_DB_USERS[v][1]}\n"
    for v in chosen_versions
) + f"└{'─'*56}\n"

pga_block = ""
if DO_PGADMIN:
    pga_block = f"""
┌─ pgAdmin 4 {'─'*48}
│  URL          : http://localhost/pgadmin4
│  Email        : {PGA_EMAIL}
│  Password     : {PGA_PASS}
│  Servers added: Local PostgreSQL
""" + "".join(
    f"│               Odoo {v} DB\n"
    for v in chosen_versions
) + f"└{'─'*56}\n"

report_body = f"""
╔════════════════════════════════════════════════════════════════╗
║                    Odoo Setup Report                           ║
╚════════════════════════════════════════════════════════════════╝

Date    : {NOW}
Ubuntu  : {UBUNTU_VER} ({UBUNTU_NAME})
User    : {CURRENT_USER}

{'═'*60}
 Installation Log
{'═'*60}
{chr(10).join(REPORT_LINES)}

{'═'*60}
 Credentials & Paths
{'═'*60}
{odoo_blocks}
{pg_block}
{pga_block}
{'═'*60}
 Python Version Policy
{'═'*60}
  Odoo 15 → python3.8  (fallback 3.9, venv rebuilt auto)
  Odoo 16 → python3.10
  Odoo 17 → python3.11  +  setuptools==68.2.2  (pkg_resources fix)
  Odoo 18 → python3.11  +  setuptools==68.2.2  (pkg_resources fix)
  Odoo 19 → python3.11  +  setuptools==68.2.2  (pkg_resources fix)
"""

with open(REPORT_PATH, "w", encoding="utf-8") as f:
    f.write(report_body)

# ═══════════════════════ Final Summary ═══════════════════════════
title("🎉 انتهى التثبيت!")

for d in installed_info:
    st = "✅" if d["status"] == "active" else "⚠️ "
    print(f"  {st} Odoo {d['ver']} → {G}http://localhost:{d['port']}{X}"
          f"  (DB: {d['db_user']}/{d['db_pass']})")

if DO_PGADMIN:
    print(f"  ✅ pgAdmin     → {G}http://localhost/pgadmin4{X}"
          f"  ({PGA_EMAIL})")

print(f"\n  {Y}📄 Report → {REPORT_PATH}{X}")
print(f"  {C}cat {REPORT_PATH}{X}\n")

# ══════════ ملخص المشاكل — لو في حاجة محتاج تعملها يدوياً ═══════
if ISSUES:
    print(f"\n{B}{Y}{'═'*60}")
    print(f"  ⚠️  يوجد {len(ISSUES)} مشكلة تحتاج مراجعة يدوية:")
    print(f"{'═'*60}{X}\n")
    for i, issue in enumerate(ISSUES, 1):
        print(f"  {Y}{i}. {issue}{X}")

    # كتابة المشاكل في الـ report
    with open(REPORT_PATH, "a", encoding="utf-8") as f:
        f.write(f"\n{'═'*60}\n")
        f.write(f" ⚠️  مشاكل تحتاج مراجعة يدوية ({len(ISSUES)})\n")
        f.write(f"{'═'*60}\n")
        for i, issue in enumerate(ISSUES, 1):
            f.write(f"  {i}. {issue}\n")
    print(f"\n  {Y}المشاكل دي اتكتبت في الـ report كمان ⬆{X}\n")
else:
    print(f"\n  {G}✅ كل حاجة اتثبتت من غير مشاكل!{X}\n")

# ════════════════════════════════════════════════════════════════
#  🤲 من زكاة العلم والوقت
# ════════════════════════════════════════════════════════════════
print(f"""
{B}{C}  {'═'*60}
{X}
{B}  🤲  دعاء{X}

  اللهم إنا نسألك علماً نافعاً، ورزقاً طيباً، وعملاً متقبلاً.
  اللهم بارك لنا في أوقاتنا وأعمارنا وأعمالنا،
  واجعل ما تعلمناه وعلّمناه في ميزان حسناتنا.
  اللهم انفع به من أخذه، ووفّق كل من سعى في نشر العلم
  وخدمة إخوانه بلا مقابل — فإن من زكاة العلم تعليمه.
  وصلى الله على سيدنا محمد وعلى آله وصحبه أجمعين.

{C}  {'═'*60}{X}
""")  # اللهم آمين 🤲
