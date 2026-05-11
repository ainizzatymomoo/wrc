# BLESS2 Auto-Fill System

Sistem automatik yang parse semua maklumat berkaitan dari softcopy PDF dan auto-fill field yang berkaitan di laman web [BLESS 2.0](https://bless2.bless.gov.my/bless2/private) (Business Licensing Electronic Support System).

## 🎯 Apa yang dilakukan sistem ini?

1. **Parse PDF** - Extract semua maklumat dari dokumen perniagaan (SSM Certificate, Company Profile, Form 9/24/49, dll.)
2. **Map Fields** - Mapping data yang di-extract ke form fields BLESS2 secara automatik
3. **Auto-Fill** - Guna Selenium untuk buka browser dan isi borang BLESS2 secara automatik

## 📁 Jenis Dokumen yang Disokong

| Dokumen | Maklumat yang Di-Extract |
|---------|--------------------------|
| SSM Company Profile | Nama syarikat, No. pendaftaran, alamat, pengarah, modal |
| Certificate of Incorporation (Form 9) | Nama syarikat, jenis syarikat, tarikh pemerbadanan |
| Form 24 (Annual Return) | Butiran syarikat, pemegang saham |
| Form 49 (Director Notification) | Maklumat pengarah/pegawai |
| Financial Statements | Modal berbayar, aset |
| Generic Business Documents | Auto-detect dan extract maklumat yang boleh dikenalpasti |

## 🚀 Quick Start

### 1. Install Dependencies

```bash
cd bless2-autofill
pip install -r requirements.txt

# Untuk OCR (optional - untuk scanned PDFs):
# Ubuntu/Debian:
sudo apt-get install tesseract-ocr tesseract-ocr-msa poppler-utils
# macOS:
brew install tesseract poppler
```

### 2. Setup Credentials

```bash
cp .env.example .env
# Edit .env dan masukkan BLESS2 username & password anda
```

### 3. Jalankan Sistem

```bash
# Preview sahaja (tengok apa yang akan diisi)
python main.py --pdf ./documents/ --preview

# Dry run (extract data sahaja, export ke JSON)
python main.py --pdf ./documents/ --dry-run --output ./output.json

# Full auto-fill
python main.py --pdf ./documents/ --username YOUR_ID --password YOUR_PASS

# Headless mode (tanpa paparan browser)
python main.py --pdf ./documents/ -u YOUR_ID -pw YOUR_PASS --headless
```

## 📖 Penggunaan Terperinci

### Mode Preview
Lihat data yang akan diisi tanpa buka browser:
```bash
python main.py --pdf ./ssm_profile.pdf --preview
```

Output contoh:
```
════════════════════════════════════════════════════════
BLESS2 AUTO-FILL PREVIEW
════════════════════════════════════════════════════════

📋 Company Information
──────────────────────────────
  ✅ Nama Syarikat / Company Name [REQUIRED]
     → ABC TECHNOLOGIES SDN BHD
  ✅ No. Pendaftaran / Registration No. [REQUIRED]
     → 202001012345
  ✅ Jenis Syarikat / Company Type [REQUIRED]
     → 01 (Private Company)
...
```

### Mode Dry Run
Extract data dan simpan ke JSON untuk review:
```bash
python main.py --pdf ./documents/ --dry-run --output ./data.json
```

### Full Auto-Fill
```bash
# Dengan credentials dari environment
export BLESS2_USERNAME="your_id"
export BLESS2_PASSWORD="your_pass"
python main.py --pdf ./documents/

# Atau dengan arguments
python main.py --pdf ./documents/ -u YOUR_ID -pw YOUR_PASS

# Auto-submit selepas isi
python main.py --pdf ./documents/ -u YOUR_ID -pw YOUR_PASS --auto-submit
```

### Dengan Config File
```bash
python main.py --pdf ./documents/ --config ./config/settings.yaml
```

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    BLESS2 Auto-Fill System                    │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────┐    ┌──────────────┐    ┌──────────────────┐  │
│  │  PDF     │    │   Field      │    │   Browser        │  │
│  │  Parser  │───▶│   Mapper     │───▶│   Automation     │  │
│  │          │    │              │    │   (Selenium)     │  │
│  └──────────┘    └──────────────┘    └──────────────────┘  │
│       │                │                      │             │
│       ▼                ▼                      ▼             │
│  ExtractedData   FormSections          BLESS2 Website       │
│  (structured)    (mapped fields)       (auto-filled)        │
│                                                              │
├─────────────────────────────────────────────────────────────┤
│                     Orchestrator                             │
│  (coordinates all steps, handles errors, logging)           │
└─────────────────────────────────────────────────────────────┘
```

## 📂 Struktur Projek

```
bless2-autofill/
├── main.py                 # Entry point utama
├── requirements.txt        # Python dependencies
├── .env.example           # Template environment variables
├── .gitignore
├── config/
│   └── settings.yaml      # Configuration file
├── src/
│   ├── __init__.py
│   ├── pdf_parser.py      # Modul parse PDF
│   ├── field_mapper.py    # Modul mapping data ke form fields
│   ├── browser_automation.py  # Modul automasi browser (Selenium)
│   └── orchestrator.py    # Koordinator utama
├── templates/             # Custom field mapping templates
├── docs/                  # Dokumentasi tambahan
└── tests/                 # Unit tests
```

## ⚙️ Configuration

Edit `config/settings.yaml` untuk customize:

```yaml
# Browser settings
headless: false          # true untuk jalankan tanpa paparan
timeout: 30              # timeout dalam saat
slow_mode: true          # tambah delay antara setiap action

# PDF settings
ocr_enabled: false       # true untuk scanned PDFs

# Override specific fields
field_overrides:
  phone: "+603-1234 5678"
  email: "admin@company.com"
```

## 🔧 Troubleshooting

### PDF tidak dapat dibaca
- Pastikan PDF bukan image/scan. Jika ya, enable OCR:
  ```bash
  python main.py --pdf ./documents/ --ocr --dry-run
  ```

### Browser tidak dapat dibuka
- Pastikan Chrome/Chromium sudah diinstall
- Pastikan `chromedriver` versi sepadan dengan Chrome anda
- Cuba gunakan: `pip install webdriver-manager`

### Field tidak dapat diisi
- Sistem akan ambil screenshot jika ada error
- Semak folder `./screenshots/` untuk debug
- Mungkin perlu update CSS selectors dalam `field_mapper.py`

### Login gagal
- Pastikan credentials betul dalam `.env`
- BLESS2 mungkin ada captcha - perlu isi manual jika ada

## 🛡️ Keselamatan

- **JANGAN** commit `.env` file ke git
- Credentials disimpan secara lokal sahaja
- Screenshots mungkin mengandungi data sensitif - semak sebelum share
- PDF dokumen perniagaan adalah sulit - jangan upload ke public repo

## 📝 Nota Penting

1. Sistem ini memerlukan akses internet ke `bless2.bless.gov.my`
2. Pastikan akaun BLESS2 anda aktif dan boleh login
3. Gunakan `--preview` atau `--dry-run` dulu sebelum full auto-fill
4. **Sentiasa semak data yang diisi sebelum submit** - gunakan `--keep-open` untuk review manual
5. Jika laman web BLESS2 berubah layout, CSS selectors mungkin perlu dikemaskini

## 🤝 Contributing

1. Fork repo ini
2. Buat feature branch
3. Submit Pull Request

## 📄 License

MIT License - Gunakan mengikut keperluan anda.
