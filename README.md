# 🟣 Odoo Multi-Version Installer — v2.0

<div align="center">

![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python&logoColor=white)
![Ubuntu](https://img.shields.io/badge/Ubuntu-24.04%20LTS-E95420?logo=ubuntu&logoColor=white)
![Odoo](https://img.shields.io/badge/Odoo-15%20%7C%2016%20%7C%2017%20%7C%2018-714B67?logo=odoo&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-PGDG%20Latest-336791?logo=postgresql&logoColor=white)
![pgAdmin](https://img.shields.io/badge/pgAdmin4-Desktop-blue?logo=postgresql&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)
![Scripts](https://img.shields.io/badge/Scripts-3%20Modular-blueviolet)

**سكريبتات Python موديولار لتثبيت بيئة تطوير Odoo كاملة على Ubuntu 24.04**
ثلاث سكريبتات مستقلة — كل واحدة متخصصة في جزء واحد — قابلة للتعديل والتوسعة بسهولة

[🚀 تشغيل سريع](#-تشغيل-سريع) • [🏗️ المعمارية](#-معمارية-المشروع) • [🔧 للمطورين](#-دليل-المطور) • [📋 المميزات الجديدة](#-الجديد-في-v20) • [🔐 Credentials](#-الـ-credentials-الافتراضية)

</div>

---

## 📌 نبذة عن المشروع

**ثلاث سكريبتات Python متخصصة** تغطي كل مرحلة من مراحل إعداد بيئة Odoo:

| السكريبت | المهمة | يحتاج sudo؟ |
|----------|--------|-------------|
| `01_postgresql_installer.py` | تثبيت وإعداد PostgreSQL بالكامل | ✅ نعم |
| `02_pgadmin_desktop_installer.py` | تثبيت pgAdmin 4 Desktop | ✅ نعم |
| `03_odoo_cloner.py` | Clone + Venv + Requirements لكل إصدار | ❌ لا |

كل سكريبت يعمل **بشكل مستقل** — تقدر تشغّل اللي تحتاجه بس، أو تشغّلهم كلهم بالترتيب.

---

## ✨ الجديد في v2.0

### 🏗️ معمارية موديولار كاملة
بدل سكريبت واحد ضخم — ثلاث سكريبتات متخصصة. كل سكريبت:
- مسؤول عن جزء واحد واضح (Single Responsibility)
- قابل للاختبار بشكل منفصل
- قابل للتعديل بدون التأثير على الأجزاء التانية

### 🐘 PostgreSQL من PGDG (مش Ubuntu الافتراضي)
Script 1 بيثبت **أحدث إصدار PostgreSQL** من الـ repository الرسمي لـ PGDG — مش الإصدار القديم اللي بييجي مع Ubuntu. ده بيدي:
- أحدث features وأمان
- performance أحسن
- دعم لـ extensions حديثة

### 🔍 pg_hba.conf Dynamic Detection (3-Layer)
بدل hardcode للمسار — النظام بيدور على `pg_hba.conf` بثلاث طرق:
```
Layer 1: find /etc/postgresql -name pg_hba.conf  ← الأشيع
Layer 2: sudo -u postgres psql -c 'SHOW hba_file'  ← يسأل PostgreSQL نفسه
Layer 3: pg_config --sysconfdir  ← الحل الأخير
```

### 🔑 Password Setting بدون Shell Injection
Script 1 بيستخدم **طريقتين آمنتين** لضبط الباسوردات:
```python
# Linux user → chpasswd via stdin (no shell quoting issues)
# DB superuser → SQL written to temp file, executed via psql -f
```

### 🌐 Git Slow-Internet Fix (Script 3)
Script 3 بيضبط 4 Git parameters عالمية قبل أي clone:
```
http.postBuffer  = 524288000   ← يمنع "remote hung up" على النت البطيء
core.compression = 0           ← أسرع على الخطوط البطيئة
http.lowSpeedLimit = 0         ← يعطل الـ speed threshold
http.lowSpeedTime  = 999999    ← صبر شبه لا نهائي
```

### ✅ Clone Integrity Verification (5 Checkpoints)
Script 3 بيتحقق من 5 ملفات أساسية بعد كل clone:
```
odoo-bin          ← الـ launcher الرئيسي
odoo/__init__.py  ← علامة الـ core package
requirements.txt  ← قائمة الـ dependencies
.git/HEAD         ← proof إن الـ clone اكتمل
odoo/release.py   ← معلومات الإصدار
```

### 🖥️ pgAdmin4 Desktop (مش Web)
Script 2 بيثبت `pgadmin4-desktop` — التطبيق الـ Qt المستقل. **مزاياه:**
- مش محتاج Apache أو Nginx
- مش محتاج `setup-web.sh` أو email setup
- أبسط في التثبيت والاستخدام
- Noble → Jammy fallback تلقائي

---

## 🏗️ معمارية المشروع

```
odoo-installer/
├── 01_postgresql_installer.py    ← Script 1: PostgreSQL
├── 02_pgadmin_desktop_installer.py  ← Script 2: pgAdmin 4
├── 03_odoo_cloner.py             ← Script 3: Odoo Cloner
└── README.md
```

### تدفق التنفيذ

```
┌─────────────────────────────────────────────────────────┐
│                    01_postgresql_installer.py            │
│                                                         │
│  Add PGDG Repo → Install PG → Start Service →          │
│  Find pg_hba → Patch Auth → Set Passwords → Verify     │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│                 02_pgadmin_desktop_installer.py          │
│                                                         │
│  Install Prereqs → Import GPG Key → Add Repo →          │
│  Install pgadmin4-desktop → Verify                      │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│                      03_odoo_cloner.py                  │
│                                                         │
│  Configure Git → Select Versions → Clone (3 retries) → │
│  Verify Integrity → Create Venv → Install Reqs →        │
│  Generate odoo.conf                                     │
└─────────────────────────────────────────────────────────┘
```

---

## 🚀 تشغيل سريع

```bash
# Clone الريبو
git clone https://github.com/ahmedalaa404/scripts_runing.git
cd scripts_runing

# Step 1: PostgreSQL (يحتاج sudo)
sudo python3 01_postgresql_installer.py

# Step 2: pgAdmin Desktop (يحتاج sudo)
sudo python3 02_pgadmin_desktop_installer.py

# Step 3: Odoo Cloner (بدون sudo)
python3 03_odoo_cloner.py
```

> ✅ **Python 3.12** هو الافتراضي على Ubuntu 24.04 — لا تحتاج أي تثبيت مسبق للسكريبتات نفسها

---

## 🐍 Python Matrix

| Odoo | Python | ملاحظة |
|------|--------|--------|
| **15.0** | 3.8 | Ubuntu 20 native — الأكثر استقراراً |
| **16.0** | 3.11 | `setuptools==68.2.2` fix مدمج |
| **17.0** | 3.11 | `setuptools==68.2.2` fix مدمج |
| **18.0** | 3.11 | `setuptools==68.2.2` fix مدمج |

> **`pkg_resources` Fix:** السكريبت بيثبت `setuptools==68.2.2` مع `--no-build-isolation` لـ Odoo 16+ — ده بيحل `ModuleNotFoundError: No module named 'pkg_resources'` نهائياً

---

## 📋 مثال على تشغيل Script 3

```
╔══════════════════════════════════════════════════════════════╗
║        Odoo Source Cloner — Connection Optimized (15→18)    ║
╚══════════════════════════════════════════════════════════════╝

  Available Odoo Versions:
    1) Odoo 15.0   port=8015  Python 3.8 — LTS stable branch
    2) Odoo 16.0   port=8016  Python 3.11 — setuptools pin required
    3) Odoo 17.0   port=8017  Python 3.11 — setuptools pin required
    4) Odoo 18.0   port=8018  Python 3.11 — setuptools pin required
    a) All versions

  Select versions (e.g. 1,3 or 1-3 or a): 2,3

  Base installation directory:
  Default: /home/ahmed/Desktop  (press Enter to accept)
  Path: [Enter]

  Also install Python requirements after cloning? [Y/n]: y

  ✅  Internet connection available ✔
  ✅  git found: git version 2.43.0
  ✅  git config http.postBuffer = 524288000
  ✅  git config core.compression = 0
  ✅  git config http.lowSpeedLimit = 0
  ✅  git config http.lowSpeedTime = 999999

  🔄  Clone attempt 1/3 (Odoo 16.0)
  ✅  Clone complete ✔  (took 2m 15s)
```

---

## 🏗️ هيكل الملفات بعد التثبيت

```
~/Desktop/
├── odoo15/
│   ├── venv/           ← Python 3.8 virtualenv
│   ├── odoo.conf       ← config مخصص (port 8015, db=odoo15)
│   ├── odoo.log        ← log file
│   └── ...             ← source code
│
├── odoo16/
│   ├── venv/           ← Python 3.11 + setuptools==68.2.2
│   ├── odoo.conf       ← port 8016, db=odoo16
│   └── ...
│
└── odoo17/
    ├── venv/           ← Python 3.11 + setuptools==68.2.2
    ├── odoo.conf       ← port 8017, db=odoo17
    └── ...
```

> كل إصدار **self-contained** — venv + conf + log جوا نفس المجلد

---

## 🔐 الـ Credentials الافتراضية

### Odoo

| الإصدار | URL | Master Password |
|---------|-----|----------------|
| Odoo 15 | http://localhost:8015 | `admin` |
| Odoo 16 | http://localhost:8016 | `admin` |
| Odoo 17 | http://localhost:8017 | `admin` |
| Odoo 18 | http://localhost:8018 | `admin` |

### PostgreSQL

| | User | Password |
|-|------|----------|
| **Linux + DB superuser** | `postgres` | `admin` |
| **Odoo 15** | `odoo15` | `odoo15` |
| **Odoo 16** | `odoo16` | `odoo16` |
| **Odoo 17** | `odoo17` | `odoo17` |
| **Odoo 18** | `odoo18` | `odoo18` |

```bash
# اتصال سريع للتحقق
PGPASSWORD=admin psql -U postgres -h 127.0.0.1
```

### pgAdmin 4

| | |
|-|-|
| **نوع التثبيت** | Desktop (Qt GUI) |
| **تشغيل** | من قائمة التطبيقات أو `pgadmin4` في الـ terminal |
| **Host** | 127.0.0.1 |
| **Port** | 5432 |
| **User** | postgres |
| **Password** | admin |

---

## ⚙️ تشغيل Odoo يدوياً

```bash
# Odoo 17 — تشغيل عادي
source ~/Desktop/odoo17/venv/bin/activate
python ~/Desktop/odoo17/odoo-bin -c ~/Desktop/odoo17/odoo.conf

# مع Dev Mode (لإعادة تحميل التغييرات تلقائياً)
python ~/Desktop/odoo17/odoo-bin -c ~/Desktop/odoo17/odoo.conf --dev=all

# ثم افتح المتصفح على
http://localhost:8017
```

---

## 🛠️ الـ Worst-Case Scenarios المعالجة

| المشكلة | الحل التلقائي |
|---------|---------------|
| `ModuleNotFoundError: pkg_resources` | `setuptools==68.2.2` + `--no-build-isolation` |
| `psycopg2` build فشل | `psycopg2-binary` بدلاً منه |
| Clone ناقص (النت فصل في النص) | 5-checkpoint verification + cleanup + retry |
| النت بطيء جداً → Git timeout | `http.lowSpeedTime=999999` يمنع الـ abort |
| `pg_hba.conf` في path غير متوقع | 3-layer dynamic detection |
| pgAdmin repo مش متاح على noble | Noble → Jammy fallback تلقائي |
| wkhtmltopdf على Ubuntu 24 | jammy package (متوافق) |
| `$$` يتفسر كـ PID في shell | SQL يُكتب في temp file وينفّذ بـ `psql -f` |
| `chpasswd` permissions | stdin-based، مش shell argument |
| GPG key تالف أو قديم | حذف + إعادة import كاملة |

---

## 🔧 دليل المطور

هذا القسم للمطورين اللي عايزين يعدّلوا أو يوسّعوا السكريبتات.

---

### 🔌 إضافة إصدار Odoo جديد (مثال: 19.0)

**في `03_odoo_cloner.py`** — ابحث عن `VERSIONS` dictionary وأضف:

```python
VERSIONS: dict[str, dict] = {
    # ... الإصدارات الموجودة ...
    "19.0": {
        "python":      "python3.11",   # عدّل لو Odoo 19 بيحتاج Python مختلف
        "port":        8019,
        "note":        "Python 3.11 — setuptools pin required",
        "setuptools":  "68.2.2",       # None لو مش محتاج pin
    },
}
```

ده كل اللي محتاج تعمله — باقي الـ logic بيتعامل مع أي إصدار تضيفه تلقائياً.

---

### 🔌 إضافة DB User في Script 1

في `01_postgresql_installer.py` أضف function بعد `set_postgres_passwords()`:

```python
def create_odoo_db_users(versions: list[str]) -> None:
    """Creates a dedicated PostgreSQL user for each Odoo version."""
    step("Creating per-version Odoo DB users")
    for ver in versions:
        short = ver.split(".")[0]
        user  = f"odoo{short}"
        sql_file = f"/tmp/pg_create_{user}.sql"
        Path(sql_file).write_text(
            f"DO $body$\n"
            f"BEGIN\n"
            f"  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='{user}') THEN\n"
            f"    CREATE ROLE {user} WITH LOGIN CREATEDB PASSWORD '{user}';\n"
            f"  ELSE\n"
            f"    ALTER ROLE {user} WITH LOGIN CREATEDB PASSWORD '{user}';\n"
            f"  END IF;\n"
            f"END\n$body$;\n"
        )
        r = subprocess.run(f"sudo -u postgres psql -f {sql_file}",
                           shell=True, capture_output=True)
        os.unlink(sql_file)
        ok(f"User created: {user} / {user}") if r.returncode == 0 \
            else warn(f"Failed: {user}")
```

---

### 🔌 تخصيص Git Parameters لنت أبطأ

في `03_odoo_cloner.py` ابحث عن `configure_git_for_slow_internet()`:

```python
git_settings = {
    "http.postBuffer":    "524288000",   # زود لـ 1073741824 (1GB) لو اللباقة كبيرة
    "core.compression":   "0",
    "http.lowSpeedLimit": "0",
    "http.lowSpeedTime":  "999999",
    # تقدر تضيف:
    "http.connecttimeout": "60",         # timeout الاتصال الأولي (ثانية)
    "http.keepAlive":      "true",       # يفضّل TCP connections مفتوحة
}
```

---

### 🔌 تغيير عدد محاولات الـ Clone

في `03_odoo_cloner.py`:

```python
MAX_RETRIES = 3   # ← غيّره لـ 5 لو النت غير مستقر جداً
```

---

### 🔌 إضافة packages إضافية للـ Venv

في `03_odoo_cloner.py` داخل `install_odoo_requirements()`:

```python
# بعد تثبيت requirements.txt، أضف packages إضافية
EXTRA_PACKAGES = [
    "debugpy",         # Remote debugging (VS Code / PyCharm)
    "ipython",         # Interactive shell أحسن
    "watchdog",        # File watching للـ dev mode
]

info("Installing extra dev packages …")
run(f"'{pip}' install {' '.join(EXTRA_PACKAGES)} --quiet", check=False)
```

---

### 🔌 تغيير مسار التثبيت الافتراضي

في `03_odoo_cloner.py`:

```python
# السطر الحالي
default_base = os.path.join(Path.home(), "Desktop") \
    if os.path.isdir(os.path.join(Path.home(), "Desktop")) \
    else str(Path.home())

# بدّله لمسار ثابت من اختيارك:
default_base = "/opt/odoo"          # للـ production
default_base = "/srv/odoo"          # بديل شائع
default_base = str(Path.home())     # الـ home directory دايماً
```

---

### 🔌 إضافة Integrity Check جديد

في `03_odoo_cloner.py` ابحث عن `INTEGRITY_CHECKS`:

```python
INTEGRITY_CHECKS = [
    "odoo-bin",
    "odoo/__init__.py",
    "requirements.txt",
    ".git/HEAD",
    "odoo/release.py",
    # أضف هنا:
    "addons/__init__.py",         # تحقق من وجود مجلد الـ addons
    "setup.cfg",                  # موجود في Odoo 16+
]
```

---

### 🔌 تشغيل Script معين بدون Interactive Mode

تقدر تعدّل أي script عشان يقبل arguments من الـ command line:

```python
# في نهاية 03_odoo_cloner.py، بدل main() الحالية، أضف:
import argparse

def main_cli() -> None:
    parser = argparse.ArgumentParser(description="Odoo Cloner")
    parser.add_argument("--versions", nargs="+",
                        choices=list(VERSIONS.keys()),
                        help="Odoo versions to clone")
    parser.add_argument("--base-path", default=str(Path.home() / "Desktop"))
    parser.add_argument("--no-requirements", action="store_true")
    args = parser.parse_args()

    if args.versions:
        # Non-interactive mode
        chosen = args.versions
        install_reqs = not args.no_requirements
        configure_git_for_slow_internet()
        results = [install_version(v, args.base_path, install_reqs)
                   for v in chosen]
        print_final_report(results)
    else:
        main()   # Fallback to interactive

if __name__ == "__main__":
    main_cli()
```

```bash
# استخدام بدون interaction:
python3 03_odoo_cloner.py --versions 16.0 17.0 --base-path /opt/odoo
```

---

### 🔌 إضافة systemd Service بعد الـ Clone

أضف هذه الـ function في `03_odoo_cloner.py` واستدعها بعد `install_version()`:

```python
def create_systemd_service(ver: str, odoo_dir: str,
                            venv_dir: str, conf_file: str,
                            current_user: str) -> bool:
    """Creates and enables a systemd service for an Odoo version."""
    import getpass
    short   = ver.split(".")[0]
    service = f"odoo{short}"
    unit    = f"/etc/systemd/system/{service}.service"
    user    = current_user or getpass.getuser()

    content = (
        f"[Unit]\n"
        f"Description=Odoo {ver}\n"
        f"After=network.target postgresql.service\n\n"
        f"[Service]\n"
        f"Type=simple\n"
        f"User={user}\n"
        f"ExecStart={venv_dir}/bin/python {odoo_dir}/odoo-bin "
        f"-c {conf_file}\n"
        f"Restart=on-failure\n"
        f"RestartSec=5\n\n"
        f"[Install]\n"
        f"WantedBy=multi-user.target\n"
    )
    tmp = f"/tmp/{service}.service"
    Path(tmp).write_text(content)
    r = subprocess.run(f"sudo mv {tmp} {unit} && "
                       f"sudo systemctl daemon-reload && "
                       f"sudo systemctl enable {service}",
                       shell=True)
    return r.returncode == 0
```

---

### 🎨 تخصيص ألوان الـ Output

كل سكريبت يحتوي على قسم `ANSI Colors` في البداية. لتغيير الألوان:

```python
# القيم الحالية
GREEN  = "\033[92m"    # bright green
YELLOW = "\033[93m"    # bright yellow
CYAN   = "\033[96m"    # bright cyan

# بدائل متاحة
GREEN  = "\033[32m"    # standard green (أهدأ)
YELLOW = "\033[33m"    # standard yellow
CYAN   = "\033[36m"    # standard cyan

# لإلغاء الألوان كلياً (مفيد للـ CI/CD logs)
GREEN = YELLOW = CYAN = RED = BLUE = MAGENTA = BOLD = DIM = RESET = ""
```

---

## 📦 المتطلبات

| المتطلب | الإصدار | ملاحظة |
|---------|---------|--------|
| Ubuntu | 24.04 LTS | Noble Numbat |
| Python | 3.12 | افتراضي في Ubuntu 24.04 |
| صلاحيات | `sudo` | للـ Scripts 1 و 2 فقط |
| إنترنت | — | لتحميل الحزم والـ clone |
| مساحة | ~3-5 GB/version | للـ source + venv |

---

## ⚠️ نظام الأخطاء

كل سكريبت يستخدم نهج **fail-fast مع context واضح**:

```
❌  Command failed (exit 1): sudo apt-get install pgadmin4-desktop
  E: Package 'pgadmin4-desktop' has no installation candidate
  [Noble → Jammy fallback activated automatically]
```

Script 3 يستخدم **soft errors** — لو package واحد فشل، الباقي يكمل وبيعرض تقرير في الآخر.

---

## 🤝 المساهمة

Pull Requests مرحب بيها في أي من هذه المجالات:

- إضافة دعم لـ Odoo 19+
- دعم Ubuntu 22.04 / 20.04 في الـ Scripts الجديدة
- CLI non-interactive mode كامل
- دعم ARM64 (Apple Silicon / Raspberry Pi)
- وحدات اختبار (pytest) لكل function

**خطوات المساهمة:**
1. Fork الريبو
2. `git checkout -b feature/your-feature`
3. `git commit -m 'Add: your feature description'`
4. `git push origin feature/your-feature`
5. افتح Pull Request

---

## 👨‍💻 المطور

**Ahmed Alaa**
- 📧 [az.ahmed.alaa@gmail.com](mailto:az.ahmed.alaa@gmail.com)
- 🐙 [@ahmedalaa404](https://github.com/ahmedalaa404)

---

## 📜 الرخصة

MIT License — حر في الاستخدام والتعديل والتوزيع

---

<div align="center">

**🤲 اللهم انفع به من أخذه — فإن من زكاة العلم تعليمه**

</div>