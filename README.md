# 🟣 Odoo Multi-Version Interactive Installer

<div align="center">

![Python](https://img.shields.io/badge/Python-3.8%2B-blue?logo=python&logoColor=white)
![Ubuntu](https://img.shields.io/badge/Ubuntu-20.04%20%7C%2022.04%20%7C%2024.04-E95420?logo=ubuntu&logoColor=white)
![Odoo](https://img.shields.io/badge/Odoo-15%20%7C%2016%20%7C%2017%20%7C%2018%20%7C%2019-714B67?logo=odoo&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Auto%20Setup-336791?logo=postgresql&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)

**سكريبت Python تفاعلي لتثبيت بيئة تطوير Odoo كاملة على Ubuntu**  
يدعم تثبيت أكتر من إصدار في نفس الوقت، مع PostgreSQL وpgAdmin 4 تلقائياً

[🚀 تشغيل سريع](#-طريقة-التشغيل) • [📋 المميزات](#-المميزات) • [🔐 Credentials](#-الـ-credentials-الافتراضية) • [🛠️ Troubleshooting](#-الـ-worst-case-scenarios-المعالجة)

</div>

---

## 📌 نبذة عن المشروع

بدل ما تقضي ساعات في تثبيت Odoo يدوياً وتعاني من مشاكل الـ dependencies والـ Python versions والـ PostgreSQL config — السكريبت ده بيعمل كل ده في خطوة واحدة بشكل تفاعلي.

**صُمم خصيصاً لـ:**
- مطوري Odoo اللي محتاجين environments متعددة على نفس الجهاز
- الشركات اللي بتشتغل على أكتر من إصدار Odoo
- أي حد عايز يقوم بيئة Odoo احترافية بأسرع وقت

---

## ✨ المميزات

| الميزة | التفاصيل |
|--------|----------|
| 🔢 **Multi-version** | تثبيت Odoo 15, 16, 17, 18, 19 دفعة واحدة |
| 🐍 **Python تلقائي** | كل إصدار بياخد Python المناسب له تلقائياً |
| 🐘 **PostgreSQL كامل** | يوزر مستقل لكل إصدار + ضبط `pg_hba.conf` + test connection |
| 🖥️ **pgAdmin 4** | تثبيت + إعداد + إضافة كل السيرفرات تلقائياً |
| 🔧 **systemd service** | كل إصدار بيشتغل كـ service مستقل عند بدء التشغيل |
| 📁 **Self-contained** | venv + conf + log كلهم جوا مجلد الـ clone |
| 🔄 **Log Rotation** | logrotate يومي، 30 يوم، compressed — الـ log مش بيكبر |
| ⚠️ **Error Recovery** | أي error بيتسجل وبيكمل، في الآخر بيقولك إيه اللي محتاج تعمله |
| 🛠️ **Smart Fallbacks** | venv فشل؟ بيمسحه ويعيد. psycopg2 فشل؟ بيجرب binary. |
| 📄 **Setup Report** | ملف `odoo_setup_report.txt` بكل الـ credentials والمسارات |

---

## 🖥️ الأنظمة المدعومة

| Ubuntu | الكود | الحالة |
|--------|-------|--------|
| 20.04 | focal | ✅ مدعوم بالكامل |
| 22.04 | jammy | ✅ مدعوم بالكامل |
| 24.04 | noble | ✅ مدعوم بالكامل |

---

## 🐍 Python Matrix

كل إصدار Odoo بيتثبت مع Python المحدد ليه بناءً على research وتجارب فعلية:

| Odoo | Python | السبب |
|------|--------|-------|
| **15.0** | 3.8 → fallback 3.9 | native في Ubuntu 20، الأكثر استقراراً |
| **16.0** | 3.10 | officially recommended |
| **17.0** | 3.11 | stable + `setuptools==68.2.2` fix |
| **18.0** | 3.11 | stable + `setuptools==68.2.2` fix |
| **19.0** | 3.11 | stable + `setuptools==68.2.2` fix |

> **`pkg_resources` Fix مدمج:** الإصدارات الجديدة من setuptools شالت `pkg_resources` من الـ default path — السكريبت بيثبت `setuptools==68.2.2` تلقائياً قبل الـ requirements لـ Odoo 17/18/19 وده بيحل:
> ```
> ModuleNotFoundError: No module named 'pkg_resources'
> ```

---

## 🚀 طريقة التشغيل

```bash
# 1. Clone الريبو
git clone https://github.com/ahmedalaa404/scripts_runing.git
cd scripts_runing

# 2. شغّل السكريبت
python3 odoo_setup.py
```

> ✅ **لا تحتاج أي تثبيت مسبق** — السكريبت بيثبت كل حاجة بنفسه بما فيها Python والـ dependencies

---

## 📋 مثال على الـ Interactive Prompts

```
╔════════════════════════════════════════════════════════════════╗
║          Odoo Multi-Version Interactive Installer              ║
╚════════════════════════════════════════════════════════════════╝

  🖥️  Ubuntu : 22.04 (jammy)
  👤 User   : ahmed

── اختار المكونات ──
  ❓ تثبيت الحزم الأساسية للنظام؟ [Y/n]: y
  ❓ تثبيت PostgreSQL؟ [Y/n]: y
  ❓ تثبيت pgAdmin 4؟ [Y/n]: y
  ❓ تثبيت Odoo؟ [Y/n]: y

  اختار إصدارات Odoo (ممكن تختار أكتر من واحد):
    1) 15.0  (3.8 / fallback 3.9)
    2) 16.0  (3.10 stable)
    3) 17.0  (3.11 + setuptools fix)
    4) 18.0  (3.11 + setuptools fix)
    5) 19.0  (3.11 + setuptools fix)
    a) كل الإصدارات

  اختيارك: 2,3     ← هيثبت Odoo 16 و 17 مع بعض

  مسار التثبيت (default: ~/Desktop): [Enter]

── ملخص ──
  Odoo 16.0 : ✅  py=python3.10  port=8016  db=odoo16/odoo16
  Odoo 17.0 : ✅  py=python3.11  port=8017  db=odoo17/odoo17

  ❓ تأكيد — تكمل؟ [Y/n]: y
```

---

## 🏗️ هيكل الملفات بعد التثبيت

```
~/Desktop/
├── odoo16/                    ← Odoo 16 source
│   ├── venv/                  ← virtualenv جوا الـ clone ✅
│   ├── odoo.conf              ← config جوا الـ clone ✅
│   ├── odoo.log               ← log مع rotate تلقائي ✅
│   ├── addons/
│   ├── odoo-bin
│   └── ...
│
├── odoo17/                    ← Odoo 17 source
│   ├── venv/
│   ├── odoo.conf
│   ├── odoo.log
│   └── ...
│
~/odoo_setup_report.txt        ← report كامل بكل الـ credentials
/etc/logrotate.d/odoo16        ← logrotate config
/etc/logrotate.d/odoo17
/etc/systemd/system/odoo16.service
/etc/systemd/system/odoo17.service
```

> كل إصدار **self-contained** — تقدر تنقل المجلد أو تعمله backup بسهولة

---

## 🔐 الـ Credentials الافتراضية

### Odoo

| الإصدار | URL | Master Password |
|---------|-----|----------------|
| Odoo 15 | http://localhost:8015 | `admin` |
| Odoo 16 | http://localhost:8016 | `admin` |
| Odoo 17 | http://localhost:8017 | `admin` |
| Odoo 18 | http://localhost:8018 | `admin` |
| Odoo 19 | http://localhost:8019 | `admin` |

### PostgreSQL

| | User | Password |
|-|------|----------|
| **Admin (عام)** | `admin` | `admin` |
| **Odoo 15** | `odoo15` | `odoo15` |
| **Odoo 16** | `odoo16` | `odoo16` |
| **Odoo 17** | `odoo17` | `odoo17` |
| **Odoo 18** | `odoo18` | `odoo18` |
| **Odoo 19** | `odoo19` | `odoo19` |

### pgAdmin 4

| | |
|-|-|
| **URL** | http://localhost/pgadmin4 |
| **Email** | `admin@admin.com` |
| **Password** | `admin` |

> ✅ كل الـ PostgreSQL servers بتتضاف في pgAdmin تلقائياً

---

## ⚙️ إدارة الـ Services

```bash
# تشغيل / إيقاف / restart
sudo systemctl start   odoo17
sudo systemctl stop    odoo17
sudo systemctl restart odoo17
sudo systemctl status  odoo17

# متابعة الـ logs مباشرة
sudo journalctl -u odoo17 -f

# تشغيل يدوي للـ debug
source ~/Desktop/odoo17/venv/bin/activate
python ~/Desktop/odoo17/odoo-bin -c ~/Desktop/odoo17/odoo.conf

# اختبار الـ log rotation يدوياً
sudo logrotate -f /etc/logrotate.d/odoo17
```

---

## 🔄 تثبيت إصدار إضافي لاحقاً

```bash
python3 odoo_setup.py

  ❓ تثبيت PostgreSQL؟ [Y/n]: n    ← موجود بالفعل، تخطي
  ❓ تثبيت pgAdmin 4؟  [Y/n]: n    ← موجود بالفعل، تخطي
  ❓ تثبيت Odoo؟       [Y/n]: y
  اختيارك: 1                        ← هيثبت Odoo 15 بس
```

---

## 🛠️ الـ Worst-Case Scenarios المعالجة

| المشكلة | الحل التلقائي |
|---------|---------------|
| `ModuleNotFoundError: pkg_resources` | `setuptools==68.2.2` قبل الـ requirements |
| `psycopg2` build فشل | تحويل لـ `psycopg2-binary` تلقائياً |
| Odoo 15 + Python 3.8 requirements فشلت | مسح الـ venv وإعادة بناء بـ Python 3.9 |
| Ubuntu 24 + Python 3.8 (no distutils) | تثبيت pip يدوي بعد deadsnakes |
| Ubuntu 24 + pgAdmin (urllib3 conflict) | استخدام APT repo رسمي بدل pip |
| `pg_hba.conf` في path غير معتاد | `find` تلقائي في كل الـ paths |
| pgAdmin APT repo فشل على noble | fallback لـ jammy تلقائياً |
| wkhtmltopdf على Ubuntu 24 | استخدام jammy package (متوافق) |
| `$$` يتفسر كـ PID في shell | استخدام `$body$` + heredoc |
| DB user مش موجود في PostgreSQL | إنشاء تلقائي في الفحص النهائي |
| أي error أثناء التثبيت | يتسجل في ISSUES ويكمل — ملخص في الآخر |

---

## ⚠️ نظام تتبع الأخطاء

السكريبت **مش بيوقف** لو حصل error — بيكمل وبيجمع المشاكل، وفي الآخر بيعرضلك ملخص:

```
══════════════════════════════════════════════════════════
  ⚠️  يوجد 2 مشكلة تحتاج مراجعة يدوية:
══════════════════════════════════════════════════════════

  1. Odoo 15: git clone فشل — تحقق من الاتصال بالإنترنت
  2. Odoo 15: فشل إنشاء DB user odoo15 — شغّل يدوياً:
     sudo -u postgres createuser --createdb --login odoo15
```

> المشاكل دي بتتكتب في `~/odoo_setup_report.txt` كمان

---

## 📄 Setup Report

في الآخر السكريبت بيكتب `~/odoo_setup_report.txt`:

```
╔════════════════════════════════════════════════════════════════╗
║                    Odoo Setup Report                           ║
╚════════════════════════════════════════════════════════════════╝

Date    : 2025-06-15 14:30:00
Ubuntu  : 22.04 (jammy)
User    : ahmed

┌─ Odoo 17.0 ────────────────────────────────────────────
│  URL          : http://localhost:8017
│  Master PW    : admin
│  DB User      : odoo17 / odoo17
│  Python       : python3.11
│  Source dir   : /home/ahmed/Desktop/odoo17
│  Config file  : /home/ahmed/Desktop/odoo17/odoo.conf
│  Service      : odoo17
│  Status       : active
└────────────────────────────────────────────────────────

  sudo systemctl start   odoo17
  sudo systemctl stop    odoo17
  sudo systemctl restart odoo17
  sudo journalctl -u odoo17 -f
```

---

## 📦 المتطلبات

- Ubuntu 20.04 / 22.04 / 24.04
- Python 3 (موجود افتراضياً في أي Ubuntu)
- صلاحيات `sudo`
- اتصال بالإنترنت

---

## 🤝 المساهمة

أي Pull Request أو Issue مرحب بيه!

1. Fork الريبو
2. عمل branch جديد: `git checkout -b feature/your-feature`
3. Commit التغييرات: `git commit -m 'Add some feature'`
4. Push: `git push origin feature/your-feature`
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
