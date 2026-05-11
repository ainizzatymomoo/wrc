# BLESS2 Auto-Fill System - Manual Automasi Lengkap

## Versi: 1.0 | Tarikh: Mei 2026

---

## ISI KANDUNGAN

1. [Pengenalan](#1-pengenalan)
2. [Keperluan Sistem](#2-keperluan-sistem)
3. [Pemasangan & Setup](#3-pemasangan--setup)
4. [Cara Penggunaan](#4-cara-penggunaan)
5. [Flow Automasi BLESS2](#5-flow-automasi-bless2)
6. [Struktur Borang BLESS2](#6-struktur-borang-bless2)
7. [AI Integration (OpenRouter)](#7-ai-integration-openrouter)
8. [Web GUI (localhost:8000)](#8-web-gui-localhost8000)
9. [CLI Mode (Terminal)](#9-cli-mode-terminal)
10. [Troubleshooting](#10-troubleshooting)
11. [Senarai Field Auto-Fill](#11-senarai-field-auto-fill)
12. [Keselamatan & Amalan Terbaik](#12-keselamatan--amalan-terbaik)

---

## 1. PENGENALAN

### Apa Itu BLESS2 Auto-Fill?

Sistem ini secara automatik:
1. **Membaca (parse) dokumen PDF** perniagaan anda (SSM Profile, Certificate of Incorporation, Form 9/24/49, dll.)
2. **Mengextract maklumat** syarikat (nama, no. pendaftaran, alamat, telefon, email, dll.)
3. **Mengisi borang BLESS2** di website `https://bless2.bless.gov.my/bless2/private` secara automatik

### Lesen Yang Disokong

| Lesen | Agensi | Status |
|-------|--------|--------|
| Permit Barang Kawalan Berjadual | KPDNKK | Disokong |
| Lesen CSA Borong | KPDNHEP | Disokong |
| Lesen lain | Pelbagai | Boleh dikonfigurasi |

### Jenis Dokumen PDF Yang Disokong

| Dokumen | Maklumat Yang Di-Extract |
|---------|--------------------------|
| SSM Company Profile | Nama, No. Pendaftaran, Alamat, Pengarah, Modal |
| Certificate of Incorporation (Form 9) | Nama, Jenis Syarikat, Tarikh Pemerbadanan |
| Form 24 (Annual Return) | Butiran syarikat, Pemegang saham |
| Form 49 (Director Notification) | Maklumat pengarah |
| Financial Statements | Modal berbayar |
| Generic Business Documents | Auto-detect semua maklumat |

---

## 2. KEPERLUAN SISTEM

### Minimum Requirements

| Komponen | Keperluan |
|----------|-----------|
| OS | Windows 10+, macOS 12+, Ubuntu 20.04+ |
| Python | 3.9 atau lebih tinggi |
| Browser | Google Chrome (versi terkini) |
| RAM | Minimum 4GB |
| Internet | Diperlukan untuk akses BLESS2 & OpenRouter API |

### Software Dependencies

```
Python 3.9+
Google Chrome (latest)
ChromeDriver (auto-install oleh webdriver-manager)
```

### Optional (untuk OCR - scanned PDFs)

```
# Ubuntu/Debian
sudo apt-get install tesseract-ocr tesseract-ocr-msa poppler-utils

# macOS
brew install tesseract poppler

# Windows
# Download dari: https://github.com/UB-Mannheim/tesseract/wiki
```

---

## 3. PEMASANGAN & SETUP

### Langkah 1: Clone Repository

```bash
git clone https://github.com/ainizzatymomoo/wrc.git
cd wrc/bless2-autofill
```

### Langkah 2: Install Python Dependencies

```bash
pip install -r requirements.txt
```

### Langkah 3: Setup Environment Variables

```bash
cp .env.example .env
```

Edit file `.env`:

```env
# WAJIB - Credentials BLESS2
BLESS2_USERNAME=your_bless_id
BLESS2_PASSWORD=your_password

# OPTIONAL - OpenRouter AI (untuk intelligent extraction)
OPENROUTER_API_KEY=sk-or-v1-xxxxxxxxxxxxx

# OPTIONAL - Model AI (default: gpt-4o-mini)
# AI_MODEL=openai/gpt-4o-mini
```

### Langkah 4: Verify Installation

```bash
python main.py --help
```

Output sepatutnya:

```
usage: main.py [-h] --pdf PDF [--username USERNAME] [--password PASSWORD]
               [--config CONFIG] [--output OUTPUT] [--dry-run] [--preview]
               [--headless] [--auto-submit] [--ocr] [--keep-open]
```

---

## 4. CARA PENGGUNAAN

### 4.1 Quick Start (3 langkah)

```bash
# 1. Letak PDF dokumen syarikat dalam folder
mkdir documents
cp /path/to/ssm_profile.pdf ./documents/

# 2. Preview dulu (RECOMMENDED - tengok apa yang akan diisi)
python main.py --pdf ./documents/ --preview

# 3. Run auto-fill
python main.py --pdf ./documents/ -u YOUR_BLESS_ID -pw YOUR_PASSWORD
```

### 4.2 Modes Yang Tersedia

| Mode | Command | Apa Yang Berlaku |
|------|---------|------------------|
| Preview | `--preview` | Papar data extracted, TANPA buka browser |
| Dry Run | `--dry-run` | Extract & map sahaja, export ke JSON |
| Full Auto-Fill | (default) | Parse PDF + Login + Isi borang |
| Headless | `--headless` | Browser jalan di background |
| Auto-Submit | `--auto-submit` | Auto-submit selepas isi (BAHAYA!) |

### 4.3 Contoh Penggunaan Terperinci

**Preview sahaja:**
```bash
python main.py --pdf ./ssm_profile.pdf --preview
```

**Dry run (export ke JSON):**
```bash
python main.py --pdf ./documents/ --dry-run --output ./data.json
```

**Full auto-fill dengan browser visible:**
```bash
python main.py --pdf ./documents/ -u MYID -pw MYPASS
```

**Full auto-fill headless (background):**
```bash
python main.py --pdf ./documents/ -u MYID -pw MYPASS --headless
```

**Dengan OCR untuk scanned PDFs:**
```bash
python main.py --pdf ./scanned_docs/ --ocr --preview
```

**Menggunakan config file:**
```bash
python main.py --pdf ./documents/ --config ./config/settings.yaml
```

---

## 5. FLOW AUTOMASI BLESS2

### Flow Lengkap (Berdasarkan Manual Rasmi BLESS2)

```
┌─────────────────────────────────────────────────────────────────┐
│                     FLOW AUTOMASI BLESS2                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  STEP 1: PDF PARSING                                             │
│  ─────────────────                                               │
│  • Baca semua PDF dalam folder                                   │
│  • Extract text menggunakan pdfplumber                           │
│  • Detect jenis dokumen (SSM Profile, Form 9, dll.)             │
│  • Extract structured data (nama, alamat, IC, dll.)              │
│  • [Optional] AI-enhanced extraction via OpenRouter              │
│                                                                   │
│  STEP 2: FIELD MAPPING                                           │
│  ────────────────────                                            │
│  • Map data ke BLESS2 form fields                                │
│  • Convert formats (state → code, IC → XX-XX-XXXX)              │
│  • Validate data completeness                                    │
│  • Generate mapping report                                       │
│                                                                   │
│  STEP 3: BROWSER AUTOMATION                                      │
│  ──────────────────────────                                      │
│  • Buka Chrome (visible/headless)                                │
│  • Navigate ke BLESS2 login page                                 │
│  • Login dengan credentials                                      │
│  • Navigate: Dashboard → My License → My Tray                   │
│  • Buka form (click Edit icon)                                   │
│  • Isi BAHAGIAN A (company details)                              │
│  • Isi BAHAGIAN B (permit/goods - sebahagian)                    │
│  • Skip BAHAGIAN C-D (manual entry needed)                       │
│  • Skip BAHAGIAN E-F (document upload)                           │
│  • [Optional] Tick PERAKUAN & Submit                             │
│                                                                   │
│  STEP 4: SAVE & REPORT                                           │
│  ────────────────────                                            │
│  • Save session (boleh resume kemudian)                          │
│  • Screenshot setiap step                                        │
│  • Export results ke JSON                                        │
│  • Log semua actions                                             │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

### Navigation Flow Di Website BLESS2

```
LOGIN PAGE
    │
    ▼
DASHBOARD (Applicant Dashboard)
    │
    ├── My License
    │       ├── Active License(s) ──→ Add New License ──→ Search ──→ Add to Tray
    │       └── My Tray ──→ [INCOMPLETE forms listed here]
    │                           │
    │                           ▼ (Click Edit icon)
    │                     ONLINE FORM
    │                           │
    │                           ├── BAHAGIAN A (Company Info)    ◄── AUTO-FILL
    │                           ├── BAHAGIAN B (Permit Details)  ◄── PARTIAL AUTO-FILL
    │                           ├── BAHAGIAN C (Supplier)        ◄── MANUAL
    │                           ├── BAHAGIAN D (Agency Approvals)◄── MANUAL
    │                           ├── BAHAGIAN E (Checklist/Docs)  ◄── UPLOAD
    │                           ├── BAHAGIAN F (Support Docs)    ◄── UPLOAD
    │                           └── PERAKUAN (Declaration)       ◄── AUTO-TICK
    │                                   │
    │                                   ▼
    │                              SUBMIT / SAVE DRAFT
    │
    └── My Task (Applicant)
            ├── My Task (RTA notifications)
            └── Track & Monitoring
```

---

## 6. STRUKTUR BORANG BLESS2

### BAHAGIAN A - Butir-Butir Pemohon/Syarikat

| # | Field | Jenis | Auto-Fill? | Sumber Data |
|---|-------|-------|------------|-------------|
| 1 | Negeri | Dropdown | ✅ Ya | Alamat syarikat → state |
| 2 | Cawangan Agensi Pemprosesan | Dropdown | ⚠️ Separa | Bergantung pada negeri |
| 3 | Bentuk Perniagaan | Dropdown | ✅ Ya | Jenis syarikat (ROC/ROB/PLT) |
| 4 | Aktiviti Perniagaan | Text | ✅ Ya | Nature of business |
| 5 | No. Telefon Pejabat | Text | ✅ Ya | Company phone |
| 6 | No. Telefon Bimbit | Text | ✅ Ya | Company phone/mobile |
| 7 | No. Faks | Text | ✅ Ya | Company fax |
| 8 | Email | Text | ✅ Ya | Company email |

**Nota untuk Lesen CSA Borong:**
- Tambahan: Tick checkbox "Borong"
- Tambahan: Alamat Surat Menyurat (boleh tick "Sama seperti Alamat Perniagaan")
- Tambahan: No. HP

### BAHAGIAN B - Butir-Butir Permit / Maklumat Barang

| # | Field | Jenis | Auto-Fill? | Nota |
|---|-------|-------|------------|------|
| 1 | Tujuan Pembelian | Text | ❌ | User input |
| 2 | Tempoh Permit (Mula) | Date | ❌ | User input |
| 3 | Tempoh Permit (Hingga) | Date | ❌ | User input |
| 4 | Jenis Barang Kawalan | Radio | ❌ | Petroleum / Bukan Petroleum |
| 5 | Alamat Stor | Address Popup | ✅ Ya | Business address dari PDF |
| 6 | Jumlah Kuantiti | Text | ❌ | User input |
| 7 | Unit of Measurement | Dropdown | ❌ | User input |

### BAHAGIAN C - Maklumat Syarikat Pembekal

| # | Field | Auto-Fill? | Nota |
|---|-------|------------|------|
| 1 | Barang Kawalan | ❌ | Dropdown |
| 2 | No. Lesen Barang Kawalan | ❌ | Text (search) |
| 3 | Tarikh Tamat | ⚠️ Auto | Auto-extract dari no. lesen |
| 4 | Nama Syarikat Pembekal | ⚠️ Auto | Auto-extract dari no. lesen |
| 5 | No. Pendaftaran Syarikat | ⚠️ Auto | Auto-extract dari no. lesen |
| 6 | Alamat Syarikat Pembekal | ⚠️ Auto | Auto-extract dari no. lesen |

**Nota:** BLESS2 system akan auto-populate field 3-6 jika No. Lesen wujud dalam sistem.

### BAHAGIAN D - Lesen/Kelulusan Jabatan/Agensi

| # | Field | Auto-Fill? | Nota |
|---|-------|------------|------|
| 1 | No. Rujukan Bomba | ❌ | Manual |
| 2 | No. Rujukan PDA | ❌ | Manual |
| 3 | No. Rujukan PBT | ❌ | Manual |
| 4 | No. Lesen | ❌ | Manual |
| 5 | Tarikh Luput | ❌ | Manual |

### BAHAGIAN E & F - Dokumen

- Upload softcopy dokumen sokongan (PDF/image)
- Tidak boleh auto-fill (memerlukan physical documents)

### PERAKUAN (Declaration)

| Field | Auto-Fill? | Action |
|-------|------------|--------|
| Checkbox Perakuan | ✅ Ya | Tick checkbox |
| Submit | ⚠️ Optional | Hanya jika `--auto-submit` flag |

---

## 7. AI INTEGRATION (OpenRouter)

### Kenapa Guna AI?

| Tanpa AI | Dengan AI |
|----------|-----------|
| Regex pattern matching sahaja | Faham konteks & bahasa Melayu |
| Accuracy ~60-70% | Accuracy ~90-95% |
| Tak boleh handle format baru | Adapt secara automatik |
| Static CSS selectors | Dynamic page analysis |
| Kalau gagal → stuck | AI suggest alternative fix |

### Setup OpenRouter

1. Pergi ke [https://openrouter.ai/keys](https://openrouter.ai/keys)
2. Create new API key
3. Tambah dalam `.env`:

```env
OPENROUTER_API_KEY=sk-or-v1-your-key-here
```

### Model Yang Tersedia

| Model | Speed | Kos/1M token | Kegunaan |
|-------|-------|--------------|----------|
| `openai/gpt-4o-mini` (default) | Pantas | ~$0.15 | Best balance |
| `openai/gpt-4o` | Sederhana | ~$2.50 | Paling accurate |
| `anthropic/claude-3.5-sonnet` | Sederhana | ~$3.00 | Great structured data |
| `google/gemini-2.0-flash-001` | Sangat pantas | ~$0.08 | Paling murah |

### Tukar Model

Edit `config/settings.yaml`:

```yaml
ai_model: "openai/gpt-4o-mini"
ai_fallback_model: "google/gemini-2.0-flash-001"
```

### Apa Yang AI Buat:

1. **PDF Extraction** - Baca raw text PDF, extract semua data dengan context understanding
2. **Field Matching** - Analyze page DOM, padankan data ke form fields secara dynamic
3. **Page Analysis** - Faham structure page, identify sections & navigation
4. **Value Formatting** - Convert format (tarikh, state code, phone format)
5. **Error Recovery** - Kalau gagal isi field, AI suggest alternative selector

### Anggaran Kos

Setiap run penuh biasanya guna ~2000-5000 tokens:
- GPT-4o-mini: ~RM0.005 per run
- GPT-4o: ~RM0.05 per run
- Gemini Flash: ~RM0.002 per run

---

## 8. WEB GUI (localhost:8000)

### Start Server

```bash
cd bless2-autofill
python run_gui.py
```

Buka browser → `http://localhost:8000`

### Features

| Step | Apa Yang Boleh Buat |
|------|---------------------|
| Step 1 - Upload | Drag & drop PDF files |
| Step 2 - Preview | Tengok semua extracted data dalam table |
| Step 3 - Auto-Fill | Masukkan credentials → Run automation |

### Real-Time Progress

- WebSocket connection untuk live updates
- Progress bar
- Log box dengan semua steps
- Error reporting

### Screenshots

Sistem auto-capture screenshots pada:
- Login page
- Setiap section form
- Bila ada error
- Selepas submission

Disimpan di `./screenshots/`

---

## 9. CLI MODE (Terminal)

### Semua Command Options

```bash
python main.py \
  --pdf ./documents/           # Path ke PDF file/folder (WAJIB)
  --username YOUR_ID           # BLESS2 username
  --password YOUR_PASS         # BLESS2 password
  --config ./config/settings.yaml  # Config file
  --output ./data.json         # Output JSON file
  --dry-run                    # Extract sahaja, tanpa browser
  --preview                    # Preview formatted table
  --headless                   # Browser di background
  --auto-submit                # Auto-submit selepas isi
  --ocr                        # Enable OCR untuk scanned PDFs
  --keep-open                  # Jangan tutup browser selepas siap
```

### Output Files

| File | Keterangan |
|------|------------|
| `./extracted_data.json` | Data yang di-extract dari PDF |
| `./bless2_results.json` | Results selepas automation |
| `./bless2_session.json` | Session data (cookies, progress) |
| `./bless2_autofill.log` | Log file terperinci |
| `./screenshots/*.png` | Screenshots untuk debugging |

---

## 10. TROUBLESHOOTING

### PDF Tidak Dapat Dibaca

**Simptom:** Data extracted kosong atau sangat sedikit.

**Penyelesaian:**
```bash
# Cuba dengan OCR enabled
python main.py --pdf ./documents/ --ocr --preview

# Pastikan tesseract installed
tesseract --version
```

### Browser Tidak Dapat Dibuka

**Simptom:** Error `WebDriverException` atau `ChromeDriver not found`

**Penyelesaian:**
```bash
# Pastikan Chrome installed
google-chrome --version

# Update webdriver-manager
pip install --upgrade webdriver-manager

# Atau install chromedriver manual
# Download dari: https://chromedriver.chromium.org/downloads
```

### Login Gagal

**Simptom:** `Login may have failed. Current URL: .../public/login`

**Penyelesaian:**
1. Pastikan credentials betul
2. Cuba login manual dulu di browser
3. Mungkin ada CAPTCHA - perlu isi manual
4. Akaun mungkin locked - hubungi admin BLESS2

### Field Tidak Dapat Diisi

**Simptom:** `Failed to fill field after 3 attempts`

**Penyelesaian:**
1. Semak folder `./screenshots/` untuk debug
2. BLESS2 mungkin update layout - perlu update selectors
3. Cuba guna AI mode (set `OPENROUTER_API_KEY`) untuk dynamic matching
4. Report issue di GitHub repo

### API OpenRouter Error

**Simptom:** `API error 401` atau `Rate limited`

**Penyelesaian:**
1. Semak API key betul dalam `.env`
2. Semak credit balance di https://openrouter.ai/activity
3. Cuba tukar model ke yang lebih murah:
   ```yaml
   ai_model: "google/gemini-2.0-flash-001"
   ```

### Session Expired

**Simptom:** Form tiba-tiba redirect ke login page.

**Penyelesaian:**
```bash
# Resume dari session yang saved
python main.py --pdf ./documents/ -u ID -pw PASS --keep-open
```

---

## 11. SENARAI FIELD AUTO-FILL

### Fields Yang Boleh Auto-Fill Dari PDF

| Field BLESS2 | Sumber Dalam PDF | Bahagian |
|--------------|------------------|----------|
| Negeri | Alamat berdaftar → extract state | A |
| Bentuk Perniagaan | Company type (Sdn Bhd=ROC, Enterprise=ROB) | A |
| Aktiviti Perniagaan | Nature of Business / Principal Activity | A |
| No. Telefon Pejabat | Phone number dalam company profile | A |
| No. Telefon Bimbit | Mobile / HP number | A |
| No. Faks | Fax number | A |
| Email | Email address | A |
| Alamat Stor | Business address / Registered address | B |
| Perakuan (checkbox) | Auto-tick | PERAKUAN |

### Fields Yang TIDAK Boleh Auto-Fill

| Field | Sebab | Bahagian |
|-------|-------|----------|
| Cawangan Agensi | Bergantung pada negeri & jenis lesen | A |
| Tujuan Pembelian | User-specific | B |
| Tempoh Permit | User-specific dates | B |
| Jenis Barang | User-specific selection | B |
| Kuantiti | User-specific | B |
| No. Lesen Pembekal | External reference | C |
| No. Rujukan Bomba/PDA/PBT | External approvals | D |
| Upload Dokumen | Physical documents required | E/F |

---

## 12. KESELAMATAN & AMALAN TERBAIK

### DO (Buat)

- ✅ Sentiasa guna `--preview` atau `--dry-run` DULU sebelum full auto-fill
- ✅ Semak data dalam preview table sebelum proceed
- ✅ Guna `--keep-open` untuk review manual sebelum submit
- ✅ Simpan `.env` secara lokal sahaja
- ✅ Backup PDF dokumen asal
- ✅ Semak screenshots selepas run untuk pastikan betul

### DON'T (Jangan)

- ❌ JANGAN commit `.env` file ke git
- ❌ JANGAN guna `--auto-submit` tanpa review dulu
- ❌ JANGAN share BLESS2 credentials
- ❌ JANGAN share OpenRouter API key
- ❌ JANGAN upload PDF sensitif ke public repo
- ❌ JANGAN run automation semasa internet tak stabil

### File Yang TIDAK Boleh Di-Commit

```
.env                    # Credentials
screenshots/            # Mungkin ada data sensitif
output/                 # Extracted data
logs/                   # Mungkin ada credentials
*.pdf                   # Dokumen perniagaan
session_data.json       # Cookies & session
```

---

## LAMPIRAN

### A. Struktur Projek

```
bless2-autofill/
├── main.py                          # CLI entry point
├── run_gui.py                       # Web GUI entry point
├── requirements.txt                 # Python dependencies
├── .env.example                     # Template env variables
├── .gitignore                       # Git ignore rules
│
├── config/
│   ├── settings.yaml                # Main configuration
│   ├── bless2_form_definitions.py   # Permit Barang Kawalan form spec
│   └── lesen_csa_borong_definitions.py  # Lesen CSA Borong form spec
│
├── src/
│   ├── __init__.py
│   ├── pdf_parser.py                # PDF text extraction & parsing
│   ├── field_mapper.py              # Map data → BLESS2 form fields
│   ├── browser_automation.py        # Selenium browser control
│   ├── ai_engine.py                 # OpenRouter AI integration
│   └── orchestrator.py              # Main workflow coordinator
│
├── web/
│   ├── app.py                       # FastAPI backend
│   └── static/
│       └── index.html               # Dashboard frontend
│
├── docs/
│   └── AUTOMATION_MANUAL.md         # Manual ini
│
├── templates/                       # Custom mapping templates
├── tests/                           # Unit tests
├── screenshots/                     # Auto-captured screenshots
├── output/                          # Exported data
└── logs/                            # Log files
```

### B. Environment Variables

| Variable | Wajib? | Keterangan |
|----------|--------|------------|
| `BLESS2_USERNAME` | Ya* | BLESS2 login ID |
| `BLESS2_PASSWORD` | Ya* | BLESS2 password |
| `OPENROUTER_API_KEY` | Tidak | AI API key untuk intelligent extraction |
| `AI_MODEL` | Tidak | Override AI model (default: gpt-4o-mini) |
| `BLESS2_BASE_URL` | Tidak | Override base URL |

*Wajib untuk auto-fill mode. Tidak perlu untuk `--preview` dan `--dry-run`.

### C. Config File (settings.yaml)

```yaml
# Browser
headless: false
timeout: 30
slow_mode: true
slow_mode_delay: 0.5

# PDF
ocr_enabled: false

# AI
ai_model: "openai/gpt-4o-mini"
ai_fallback_model: "google/gemini-2.0-flash-001"
ai_confidence_threshold: 0.7

# Logging
log_level: "INFO"
```

---

**Disediakan oleh:** BLESS2 Auto-Fill System v1.0
**Berdasarkan:** Manual Rasmi BLESS2 (Permit Barang Kawalan & Lesen CSA Borong)
