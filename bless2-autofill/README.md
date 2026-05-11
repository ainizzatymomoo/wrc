<p align="center">
  <img src="https://img.shields.io/badge/Python-3.9+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/Selenium-43B02A?style=for-the-badge&logo=selenium&logoColor=white" alt="Selenium">
  <img src="https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/OpenRouter_AI-6366F1?style=for-the-badge&logo=openai&logoColor=white" alt="OpenRouter">
  <img src="https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge" alt="MIT License">
</p>

<h1 align="center">BLESS2 Auto-Fill System</h1>

<p align="center">
  <strong>Sistem automasi penuh untuk parse dokumen PDF perniagaan & auto-fill borang BLESS 2.0</strong>
</p>

<p align="center">
  <a href="#-quick-start">Quick Start</a> &bull;
  <a href="#-features">Features</a> &bull;
  <a href="#-web-gui">Web GUI</a> &bull;
  <a href="#-ai-powered">AI Powered</a> &bull;
  <a href="#-documentation">Docs</a>
</p>

---

## Apa Ni?

> Upload PDF syarikat anda &rarr; Sistem extract semua info &rarr; Auto-isi borang [BLESS 2.0](https://bless2.bless.gov.my/bless2/private) untuk anda.

BLESS 2.0 (Business Licensing Electronic Support System) adalah sistem kerajaan Malaysia untuk permohonan lesen perniagaan. Sistem ini **menghapuskan kerja manual** mengisi borang berulang kali dengan mengautomasikan keseluruhan proses.

```
  PDF Syarikat           AI Extract Data          Auto-Fill BLESS2
 ┌───────────┐         ┌─────────────────┐       ┌──────────────┐
 │  SSM      │         │  Nama Syarikat  │       │  ✅ Negeri    │
 │  Form 9   │  ────►  │  No. SSM        │ ────► │  ✅ Email     │
 │  Form 49  │         │  Alamat         │       │  ✅ Telefon   │
 │  Profile  │         │  Tel/Email/Fax  │       │  ✅ Aktiviti  │
 └───────────┘         └─────────────────┘       └──────────────┘
```

---

## &#x1F680; Quick Start

```bash
# 1. Clone & setup
git clone https://github.com/ainizzatymomoo/wrc.git
cd wrc/bless2-autofill
pip install -r requirements.txt

# 2. Setup credentials
cp .env.example .env
# Edit .env → masukkan BLESS2_USERNAME, BLESS2_PASSWORD, OPENROUTER_API_KEY

# 3. Preview dulu (recommended!)
python main.py --pdf ./documents/ --preview

# 4. Full auto-fill
python main.py --pdf ./documents/ -u YOUR_ID -pw YOUR_PASS
```

Atau guna **Web GUI**:
```bash
python run_gui.py
# Buka http://localhost:8000
```

---

## &#x2728; Features

| Feature | Keterangan |
|---------|------------|
| **PDF Parsing** | Extract data dari SSM Profile, Form 9/24/49, Annual Return, dll. |
| **AI-Powered Extraction** | OpenRouter AI (GPT-4o, Claude, Gemini) untuk accuracy 90%+ |
| **Smart Field Matching** | AI analyze page DOM & match fields secara dynamic |
| **Web Dashboard** | GUI cantik di localhost:8000 dengan drag-drop upload |
| **Real-Time Progress** | WebSocket live updates semasa automation berjalan |
| **Multiple Modes** | Preview, Dry Run, Full Auto-Fill, Headless |
| **Error Recovery** | AI suggest fix bila field gagal diisi |
| **Session Resume** | Boleh resume dari last checkpoint |
| **Screenshot Debug** | Auto-capture screenshots pada setiap step |

---

## &#x1F3AF; Lesen Yang Disokong

| Lesen | Agensi | Bahagian Auto-Fill |
|-------|--------|-------------------|
| Permit Barang Kawalan Berjadual | KPDNKK | A, B (partial), Perakuan |
| Lesen CSA Borong | KPDNHEP | A, B (partial), Perakuan |

---

## &#x1F4C4; Dokumen PDF Yang Disokong

| Dokumen | Data Yang Di-Extract |
|---------|---------------------|
| SSM Company Profile | Nama, No. Pendaftaran, Alamat, Pengarah, Modal, MSIC |
| Certificate of Incorporation | Nama, Jenis Syarikat, Tarikh Pemerbadanan |
| Form 9 | Certificate details |
| Form 24 (Annual Return) | Syarikat, Pemegang Saham |
| Form 49 (Director) | Nama, IC, Jawatan Pengarah |
| Financial Statements | Modal Berbayar |
| **Any Business PDF** | Auto-detect & extract (AI-powered) |

---

## &#x1F310; Web GUI

<p align="center"><strong>Dashboard di <code>http://localhost:8000</code></strong></p>

```bash
python run_gui.py
```

**3 langkah mudah:**

| Step | Aksi | Screenshot |
|------|------|-----------|
| 1 | Drag & drop PDF files | Upload zone |
| 2 | Preview extracted data | Table view |
| 3 | Enter credentials → Run | Progress bar + live log |

**Features Web GUI:**
- Drag & drop PDF upload
- Real-time extraction preview
- Live automation progress (WebSocket)
- Download JSON export
- Error log visualization

---

## &#x1F9E0; AI Powered

Integrate dengan **OpenRouter** untuk akses 300+ model AI:

```env
# .env
OPENROUTER_API_KEY=sk-or-v1-xxxxx
```

### Apa Yang AI Buat:

| Fungsi | Tanpa AI | Dengan AI |
|--------|----------|-----------|
| PDF Extraction | Regex (60-70%) | Context-aware (90-95%) |
| Field Matching | Static selectors | Dynamic page analysis |
| Error Handling | Retry same selector | AI suggest alternative |
| Format Handling | Limited patterns | Any format/language |

### Model Yang Tersedia:

| Model | Speed | Kos | Best For |
|-------|-------|-----|----------|
| `openai/gpt-4o-mini` | Fast | ~RM0.005/run | Default, best balance |
| `openai/gpt-4o` | Medium | ~RM0.05/run | Maximum accuracy |
| `anthropic/claude-3.5-sonnet` | Medium | ~RM0.06/run | Complex documents |
| `google/gemini-2.0-flash-001` | Fastest | ~RM0.002/run | Budget option |

---

## &#x1F4CB; Struktur Borang BLESS2

Berdasarkan **manual rasmi BLESS2**:

```
┌─────────────────────────────────────────────────────────────┐
│  BAHAGIAN A - Butir Pemohon/Syarikat          [AUTO-FILL]   │
│  ├── Negeri                              ✅ dari PDF        │
│  ├── Cawangan Agensi                     ⚠️  manual        │
│  ├── Bentuk Perniagaan (ROC/ROB/PLT)     ✅ dari PDF        │
│  ├── Aktiviti Perniagaan                 ✅ dari PDF        │
│  ├── No. Telefon Pejabat                 ✅ dari PDF        │
│  ├── No. Telefon Bimbit                  ✅ dari PDF        │
│  ├── No. Faks                            ✅ dari PDF        │
│  └── Email                               ✅ dari PDF        │
├─────────────────────────────────────────────────────────────┤
│  BAHAGIAN B - Butir Permit/Barang             [PARTIAL]     │
│  ├── Tujuan Pembelian                    ❌ manual          │
│  ├── Tempoh Permit                       ❌ manual          │
│  ├── Jenis Barang                        ❌ manual          │
│  └── Alamat Stor                         ✅ dari PDF        │
├─────────────────────────────────────────────────────────────┤
│  BAHAGIAN C - Syarikat Pembekal               [MANUAL]      │
├─────────────────────────────────────────────────────────────┤
│  BAHAGIAN D - Kelulusan Jabatan/Agensi        [MANUAL]      │
├─────────────────────────────────────────────────────────────┤
│  BAHAGIAN E/F - Dokumen Upload                [MANUAL]      │
├─────────────────────────────────────────────────────────────┤
│  PERAKUAN - Declaration                       [AUTO-TICK]   │
└─────────────────────────────────────────────────────────────┘
```

---

## &#x1F6E0;&#xFE0F; Modes Penggunaan

| Mode | Command | Guna Bila |
|------|---------|-----------|
| **Preview** | `--preview` | Nak tengok data yang di-extract tanpa buka browser |
| **Dry Run** | `--dry-run` | Export ke JSON untuk review/integration |
| **Full** | (default) | Parse + Login + Fill borang |
| **Headless** | `--headless` | Browser di background (untuk server/cron) |
| **Keep Open** | `--keep-open` | Browser kekal buka untuk semak manual |
| **Auto Submit** | `--auto-submit` | Auto-hantar (HATI-HATI!) |

---

## &#x1F4C2; Struktur Projek

```
bless2-autofill/
├── main.py                          # CLI entry point
├── run_gui.py                       # Web GUI (localhost:8000)
├── requirements.txt                 # Dependencies
├── .env.example                     # Template credentials
│
├── config/
│   ├── settings.yaml                # Main config
│   ├── bless2_form_definitions.py   # Permit Barang Kawalan spec
│   └── lesen_csa_borong_definitions.py  # Lesen CSA Borong spec
│
├── src/
│   ├── pdf_parser.py                # PDF extraction engine
│   ├── field_mapper.py              # Data → BLESS2 field mapping
│   ├── browser_automation.py        # Selenium browser control
│   ├── ai_engine.py                 # OpenRouter AI integration
│   └── orchestrator.py              # Workflow coordinator
│
├── web/
│   ├── app.py                       # FastAPI + WebSocket backend
│   └── static/index.html            # Dashboard UI
│
└── docs/
    └── AUTOMATION_MANUAL.md         # Manual lengkap (400+ lines)
```

---

## &#x2699;&#xFE0F; Configuration

### Environment Variables (`.env`)

```env
BLESS2_USERNAME=your_bless_id
BLESS2_PASSWORD=your_password
OPENROUTER_API_KEY=sk-or-v1-xxxxx    # Optional: untuk AI
```

### Config File (`config/settings.yaml`)

```yaml
headless: false
timeout: 30
slow_mode: true
ocr_enabled: false
ai_model: "openai/gpt-4o-mini"
ai_confidence_threshold: 0.7
```

---

## &#x1F4D6; Documentation

| Dokumen | Lokasi | Isi |
|---------|--------|-----|
| README | `README.md` | Overview & quick start |
| **Manual Lengkap** | [`docs/AUTOMATION_MANUAL.md`](docs/AUTOMATION_MANUAL.md) | Step-by-step guide, troubleshooting, field reference |
| Form Specs | `config/bless2_form_definitions.py` | Exact BLESS2 form structure |
| Config Example | `config/settings.yaml` | All available settings |

---

## &#x26A0;&#xFE0F; Penting

> **SENTIASA guna `--preview` dulu sebelum full auto-fill.**

```bash
# BETUL - preview dulu
python main.py --pdf ./docs/ --preview
python main.py --pdf ./docs/ -u ID -pw PASS --keep-open

# BAHAYA - jangan buat tanpa review!
python main.py --pdf ./docs/ -u ID -pw PASS --auto-submit  # ⚠️
```

---

## &#x1F512; Keselamatan

| Item | Status |
|------|--------|
| `.env` dalam `.gitignore` | &#x2705; |
| Credentials encrypted in memory | &#x2705; |
| Screenshots auto-cleanup option | &#x2705; |
| No data sent to external (except OpenRouter) | &#x2705; |
| PDF files excluded from git | &#x2705; |

---

## &#x1F91D; Contributing

```bash
# 1. Fork repo
# 2. Create branch
git checkout -b feature/new-license-support

# 3. Make changes & commit
git commit -m "feat: add support for Lesen XYZ"

# 4. Push & PR
git push origin feature/new-license-support
```

---

## &#x1F4DC; License

MIT License - Free to use, modify, and distribute.

---

<p align="center">
  <strong>Built with &#x2764;&#xFE0F; for Malaysian businesses</strong><br>
  <sub>Automate the boring stuff. Focus on growing your business.</sub>
</p>
