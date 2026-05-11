"""
BLESS2 Form Definitions
========================
Exact form structure based on official BLESS2 manuals:
1. USER MANUAL PERMIT - Permit Barang Kawalan Berjadual (KPDNKK)
2. User Manual Lesen CSA Borong (New) - (KPDNHEP)

This defines the complete BLESS2 navigation flow and form fields
as documented in the official manuals.
"""

# ==========================================
# BLESS2 NAVIGATION FLOW
# ==========================================
# Based on manual analysis, the exact flow is:
#
# 1. Login → Dashboard
# 2. Dashboard → My License → Active License(s)
# 3. Click "Add New License" button
# 4. Select company from "Apply on behalf of" dropdown
# 5. Enter keyword to search license type
# 6. Select license checkbox → "Add to Tray"
# 7. Select License Type (New/Renewal) → Save
# 8. Go to My Tray → Click edit icon to fill form
# 9. Fill form by BAHAGIAN (sections A through F)
# 10. PERAKUAN (Declaration) → tick checkbox → Submit

NAVIGATION_FLOW = {
    "login": {
        "url": "/bless2/public/login",
        "fields": {
            "username": "input[name='username'], input[id='blessId'], #userId",
            "password": "input[type='password'], input[name='password']",
        },
        "submit": "button[type='submit'], input[type='submit']",
    },
    "dashboard": {
        "url": "/bless2/private",
        "menu": {
            "my_license": "My License",
            "active_licenses": "Active License(s)",
            "my_tray": "My Tray",
            "my_task": "My Task (Applicant)",
        },
    },
    "active_licenses": {
        "url": "/bless2/private/myLicense/activeLicense",
        "actions": {
            "add_new": "button:contains('Add New License'), a:contains('Add New License')",
        },
    },
    "add_license": {
        "fields": {
            "apply_on_behalf": "select[id*='behalf'], select[name*='behalf']",
            "keyword_search": "input[id*='keyword'], input[name*='keyword']",
        },
        "actions": {
            "search": "button:contains('Search'), button[id*='search']",
            "add_to_tray": "button:contains('Add to Tray')",
            "select_license_type": "select[id*='licenseType'], select[name*='licenseType']",
            "save": "button:contains('Save'), button[id*='save']",
        },
    },
    "my_tray": {
        "url": "/bless2/private/myLicense/myTray",
        "actions": {
            "edit_form": "i.fa-edit, a[title='Edit'], .edit-icon",
            "submit_selected": "button:contains('Submit'), button[id*='submit']",
            "delete_selected": "button:contains('Delete'), button[id*='delete']",
        },
    },
    "form_actions": {
        "save": "button:contains('Simpan'), button:contains('Save'), button[id*='save']",
        "submit": "button:contains('Hantar'), button:contains('Submit'), button[id*='submit']",
        "reset": "button:contains('Set Semula'), button:contains('Reset')",
        "preview_pdf": "button:contains('Preview'), button[id*='preview']",
        "back_to_tray": "button:contains('Kembali'), button:contains('Back')",
        "checklist": "button:contains('Checklist'), button:contains('Guideline')",
    },
}


# ==========================================
# LICENSE TYPES SUPPORTED
# ==========================================

LICENSE_TYPES = {
    "permit_barang_kawalan": {
        "name": "Permit Barang Kawalan Berjadual",
        "agency": "KPDNKK",
        "keyword": "Barang Kawalan",
        "applicant_types": [
            "Individual",
            "Registrar of Company (ROC)",
            "Registrar of Business (ROB)",
            "Cooperative",
            "Government Organization",
            "Registrar of Society (ROS)",
        ],
        "sections": ["A", "B", "C", "D", "E", "F"],
    },
    "lesen_csa_borong": {
        "name": "Lesen CSA Borong",
        "agency": "KPDNHEP",
        "keyword": "Borong",
        "applicant_types": [
            "Individual",
            "Registrar of Company (ROC)",
            "Registrar of Business (ROB)",
            "Perkongsian Liabiliti Terhad (PLT)",
            "Cooperative",
            "Government Organization",
            "Registrar of Society (ROS)",
            "Ordinan Perlesenan Perdagangan (Sabah)",
            "Ordinan Perlesenan Perniagaan, Profesion dan Perdagangan (Sarawak)",
            "Labuan Financial Services Authority (LFSA)",
            "Institution",
        ],
        "sections": ["A", "B", "C", "D", "E"],
    },
}


# ==========================================
# FORM SECTIONS - PERMIT BARANG KAWALAN
# ==========================================

PERMIT_BARANG_KAWALAN_SECTIONS = {
    "bahagian_a": {
        "title": "BAHAGIAN A - BUTIR-BUTIR PEMOHON/SYARIKAT",
        "title_en": "Section A - Applicant/Company Details",
        "fields": [
            {
                "id": "negeri",
                "label": "Negeri",
                "label_en": "State",
                "type": "select",
                "required": True,
                "source": "company.state",
                "selectors": [
                    "select[id*='negeri']",
                    "select[name*='negeri']",
                    "select[id*='state']",
                ],
            },
            {
                "id": "cawangan_agensi",
                "label": "Cawangan Agensi Pemprosesan",
                "label_en": "Processing Agency Branch",
                "type": "select",
                "required": True,
                "source": None,  # User must select
                "selectors": [
                    "select[id*='cawangan']",
                    "select[name*='cawangan']",
                    "select[id*='branch']",
                ],
            },
            {
                "id": "bentuk_perniagaan",
                "label": "Bentuk Perniagaan",
                "label_en": "Business Type/Entity",
                "type": "select",
                "required": True,
                "source": "company.company_type",
                "selectors": [
                    "select[id*='bentuk']",
                    "select[name*='bentuk']",
                    "select[id*='businessType']",
                ],
            },
            {
                "id": "aktiviti_perniagaan",
                "label": "Aktiviti Perniagaan",
                "label_en": "Business Activity",
                "type": "text",
                "required": True,
                "source": "company.business_nature",
                "selectors": [
                    "input[id*='aktiviti']",
                    "input[name*='aktiviti']",
                    "textarea[id*='aktiviti']",
                    "input[id*='activity']",
                ],
            },
            {
                "id": "no_telefon_pejabat",
                "label": "No. Telefon Pejabat",
                "label_en": "Office Phone Number",
                "type": "text",
                "required": True,
                "source": "company.phone",
                "selectors": [
                    "input[id*='noTel']",
                    "input[name*='noTel']",
                    "input[id*='phone']",
                    "input[id*='telefon']",
                ],
            },
            {
                "id": "no_telefon_bimbit",
                "label": "No. Telefon Bimbit",
                "label_en": "Mobile Phone Number",
                "type": "text",
                "required": True,
                "source": "company.phone",
                "selectors": [
                    "input[id*='bimbit']",
                    "input[name*='bimbit']",
                    "input[id*='mobile']",
                    "input[id*='hp']",
                ],
            },
            {
                "id": "no_faks",
                "label": "No. Faks",
                "label_en": "Fax Number",
                "type": "text",
                "required": True,
                "source": "company.fax",
                "selectors": [
                    "input[id*='faks']",
                    "input[name*='faks']",
                    "input[id*='fax']",
                ],
            },
            {
                "id": "email",
                "label": "Email",
                "label_en": "Email",
                "type": "text",
                "required": True,
                "source": "company.email",
                "selectors": [
                    "input[id*='email']",
                    "input[name*='email']",
                    "input[type='email']",
                ],
            },
        ],
    },
    "bahagian_b": {
        "title": "BAHAGIAN B - BUTIR-BUTIR PERMIT YANG DIPOHON",
        "title_en": "Section B - Permit Details Applied",
        "fields": [
            {
                "id": "tujuan_pembelian",
                "label": "Tujuan Pembelian",
                "label_en": "Purpose of Purchase",
                "type": "text",
                "required": True,
                "source": None,
                "selectors": [
                    "input[id*='tujuan']",
                    "textarea[id*='tujuan']",
                    "input[name*='tujuan']",
                ],
            },
            {
                "id": "tempoh_mula",
                "label": "Tempoh Masa Permit - Mula",
                "label_en": "Permit Period - Start",
                "type": "date",
                "required": True,
                "source": None,
                "selectors": [
                    "input[id*='mula']",
                    "input[name*='mula']",
                    "input[id*='startDate']",
                ],
            },
            {
                "id": "tempoh_hingga",
                "label": "Tempoh Masa Permit - Hingga",
                "label_en": "Permit Period - End",
                "type": "date",
                "required": True,
                "source": None,
                "selectors": [
                    "input[id*='hingga']",
                    "input[name*='hingga']",
                    "input[id*='endDate']",
                ],
            },
            {
                "id": "jenis_barang_kawalan",
                "label": "Jenis Barang Kawalan",
                "label_en": "Type of Controlled Goods",
                "type": "radio",
                "required": True,
                "source": None,
                "options": ["Petroleum", "Bukan Petroleum"],
                "selectors": [
                    "input[name*='jenis'][type='radio']",
                    "input[name*='barangKawalan'][type='radio']",
                ],
            },
            {
                "id": "alamat_stor",
                "label": "Alamat Stor dan Tempat Simpanan",
                "label_en": "Store Address and Storage Location",
                "type": "address_popup",
                "required": True,
                "source": "company.business_address",
                "selectors": [
                    "button:contains('Tambah')",
                    "button[id*='addAddress']",
                ],
            },
        ],
    },
    "bahagian_c": {
        "title": "BAHAGIAN C - BUTIR-BUTIR SYARIKAT PEMBEKAL",
        "title_en": "Section C - Supplier Company Details",
        "fields": [
            {
                "id": "barang_kawalan_pembekal",
                "label": "Barang Kawalan",
                "label_en": "Controlled Goods",
                "type": "select",
                "required": True,
                "source": None,
                "selectors": [
                    "select[id*='barangKawalan']",
                    "select[name*='barangKawalan']",
                ],
            },
            {
                "id": "no_lesen_pembekal",
                "label": "No. Lesen Barang Kawalan",
                "label_en": "Controlled Goods License No.",
                "type": "text",
                "required": True,
                "source": None,
                "notes": "System will auto-extract Tarikh Tamat, Nama Syarikat, No. Pendaftaran, Alamat if license exists in system",
                "selectors": [
                    "input[id*='noLesen']",
                    "input[name*='noLesen']",
                ],
            },
            {
                "id": "tarikh_tamat_lesen",
                "label": "Tarikh Tamat",
                "label_en": "Expiry Date",
                "type": "date",
                "required": True,
                "source": None,
                "notes": "Auto-extracted from license no. Manual entry if not in system.",
                "selectors": [
                    "input[id*='tarikhTamat']",
                    "input[name*='tarikhTamat']",
                    "input[id*='expiryDate']",
                ],
            },
            {
                "id": "nama_syarikat_pembekal",
                "label": "Nama Syarikat Pembekal",
                "label_en": "Supplier Company Name",
                "type": "text",
                "required": True,
                "source": None,
                "notes": "Auto-extracted or manual via popup",
                "selectors": [
                    "input[id*='namaPembekal']",
                    "input[name*='namaPembekal']",
                ],
            },
            {
                "id": "no_pendaftaran_pembekal",
                "label": "No. Pendaftaran Syarikat",
                "label_en": "Supplier Registration No.",
                "type": "text",
                "required": True,
                "source": None,
                "notes": "Auto-extracted from license no.",
                "selectors": [
                    "input[id*='noPendaftaran']",
                    "input[name*='noPendaftaran']",
                ],
            },
            {
                "id": "alamat_pembekal",
                "label": "Alamat Syarikat Pembekal",
                "label_en": "Supplier Company Address",
                "type": "text",
                "required": True,
                "source": None,
                "notes": "Auto-extracted from license no.",
                "selectors": [
                    "textarea[id*='alamatPembekal']",
                    "input[id*='alamatPembekal']",
                ],
            },
        ],
    },
    "bahagian_d": {
        "title": "BAHAGIAN D - BUTIR-BUTIR LESEN/KELULUSAN DARIPADA JABATAN/AGENSI",
        "title_en": "Section D - License/Approval from Department/Agency",
        "fields": [
            {
                "id": "no_rujukan_bomba",
                "label": "No. Rujukan - Kelulusan Jabatan Bomba dan Penyelamat Malaysia",
                "label_en": "Reference No. - Fire & Rescue Dept Approval",
                "type": "text",
                "required": True,
                "source": None,
                "selectors": [
                    "input[id*='bomba']",
                    "input[name*='bomba']",
                ],
            },
            {
                "id": "no_rujukan_pda",
                "label": "No. Rujukan - Kebenaran di Bawah Akta Kemajuan Petroleum 1974 (PDA)",
                "label_en": "Reference No. - Petroleum Development Act 1974",
                "type": "text",
                "required": True,
                "source": None,
                "selectors": [
                    "input[id*='pda']",
                    "input[name*='pda']",
                ],
            },
            {
                "id": "no_rujukan_pbt",
                "label": "No. Rujukan - Kelulusan Pihak Berkuasa/Majlis Kerajaan Tempatan",
                "label_en": "Reference No. - Local Authority Approval",
                "type": "text",
                "required": True,
                "source": None,
                "selectors": [
                    "input[id*='pbt']",
                    "input[name*='pbt']",
                    "input[id*='majlis']",
                ],
            },
            {
                "id": "no_lesen_d",
                "label": "No. Lesen",
                "label_en": "License No.",
                "type": "text",
                "required": True,
                "source": None,
                "selectors": [
                    "input[id*='noLesenD']",
                    "input[name*='noLesen']",
                ],
            },
            {
                "id": "tarikh_luput",
                "label": "Tarikh Luput",
                "label_en": "Expiry Date",
                "type": "date",
                "required": True,
                "source": None,
                "selectors": [
                    "input[id*='tarikhLuput']",
                    "input[name*='tarikhLuput']",
                ],
            },
        ],
    },
    "bahagian_e": {
        "title": "BAHAGIAN E - SENARAI SEMAK",
        "title_en": "Section E - Checklist",
        "fields": [],  # Review only, no input
        "notes": "Applicant reviews the form data. No fields to fill.",
    },
    "bahagian_f": {
        "title": "BAHAGIAN F - DOKUMEN SOKONGAN",
        "title_en": "Section F - Supporting Documents",
        "fields": [
            {
                "id": "upload_docs",
                "label": "Upload Dokumen Sokongan",
                "label_en": "Upload Supporting Documents",
                "type": "file_upload",
                "required": True,
                "source": None,
                "notes": "Click 'Upload' button to upload softcopy documents",
                "selectors": [
                    "button:contains('Upload')",
                    "input[type='file']",
                    "button[id*='upload']",
                ],
            },
        ],
    },
    "perakuan": {
        "title": "PERAKUAN",
        "title_en": "Declaration",
        "fields": [
            {
                "id": "perakuan_checkbox",
                "label": "Perakuan Pemohon",
                "label_en": "Applicant Declaration",
                "type": "checkbox",
                "required": True,
                "value": "true",
                "source": None,
                "notes": "Must tick before submit",
                "selectors": [
                    "input[type='checkbox'][id*='perakuan']",
                    "input[type='checkbox'][id*='declare']",
                    "input[type='checkbox'][name*='perakuan']",
                ],
            },
        ],
    },
}
