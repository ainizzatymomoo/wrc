"""
BLESS2 Form Definitions - Lesen CSA Borong
============================================
Based on: User Manual Lesen CSA Borong (New) - Applicant
Agency: KPDNHEP (Kementerian Perdagangan Dalam Negeri Dan Hal Ehwal Pengguna)
"""

# ==========================================
# FORM SECTIONS - LESEN CSA BORONG
# ==========================================

LESEN_CSA_BORONG_SECTIONS = {
    "bahagian_a": {
        "title": "BAHAGIAN A - MAKLUMAT PERMOHONAN",
        "title_en": "Section A - Application Information",
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
                "source": None,
                "selectors": [
                    "select[id*='cawangan']",
                    "select[name*='cawangan']",
                    "select[id*='branch']",
                ],
            },
            {
                "id": "jenis_borong",
                "label": "Borong",
                "label_en": "Wholesale",
                "type": "checkbox",
                "required": True,
                "value": "true",
                "source": None,
                "notes": "Tick item for Borong",
                "selectors": [
                    "input[type='checkbox'][id*='borong']",
                    "input[type='checkbox'][name*='borong']",
                    "input[type='checkbox'][value*='borong']",
                ],
            },
            {
                "id": "alamat_surat",
                "label": "Alamat Surat Menyurat",
                "label_en": "Correspondence Address",
                "type": "address_or_same",
                "required": True,
                "source": "company.registered_address",
                "notes": "Tick 'Sama seperti Alamat Perniagaan/Syarikat' if same. If not, click Add button.",
                "selectors": [
                    "input[type='checkbox'][id*='sama']",
                    "input[type='checkbox'][id*='same']",
                    "button:contains('Tambah')",
                ],
            },
            {
                "id": "no_hp",
                "label": "No. HP",
                "label_en": "Mobile Number",
                "type": "text",
                "required": True,
                "source": "company.phone",
                "selectors": [
                    "input[id*='noHp']",
                    "input[name*='noHp']",
                    "input[id*='mobile']",
                    "input[id*='hp']",
                ],
            },
        ],
    },
    "bahagian_b": {
        "title": "BAHAGIAN B - MAKLUMAT BARANG KUANTITI",
        "title_en": "Section B - Goods Quantity Information",
        "notes": "Fill in kuantiti and Alamat Stor according to items selected in Bahagian A",
        "fields": [
            {
                "id": "jumlah_kuantiti",
                "label": "Jumlah Kuantiti",
                "label_en": "Total Quantity",
                "type": "text",
                "required": True,
                "source": None,
                "notes": "Click Add button first to open form",
                "selectors": [
                    "input[id*='kuantiti']",
                    "input[name*='kuantiti']",
                    "input[id*='quantity']",
                ],
            },
            {
                "id": "unit_measurement",
                "label": "Unit of Measurement",
                "label_en": "Unit of Measurement",
                "type": "select",
                "required": True,
                "source": None,
                "selectors": [
                    "select[id*='unit']",
                    "select[name*='unit']",
                ],
            },
            {
                "id": "alamat_stor",
                "label": "Alamat Stor (Tempat Simpanan Barang)",
                "label_en": "Store Address (Goods Storage Location)",
                "type": "address_popup",
                "required": True,
                "source": "company.business_address",
                "notes": "Click Add button to open popup, add address, then Save and Close",
                "selectors": [
                    "button:contains('Tambah')",
                    "button[id*='addAlamat']",
                ],
            },
        ],
    },
    "bahagian_c": {
        "title": "BAHAGIAN C - MAKLUMAT SYARIKAT PEMBEKAL",
        "title_en": "Section C - Supplier Company Information",
        "notes": "Click Add button to fill in supplier details",
        "fields": [
            {
                "id": "nama_pembekal",
                "label": "Nama Syarikat Pembekal",
                "label_en": "Supplier Company Name",
                "type": "text",
                "required": True,
                "source": None,
                "selectors": [
                    "input[id*='namaPembekal']",
                    "input[name*='namaPembekal']",
                    "input[id*='supplierName']",
                ],
            },
            {
                "id": "alamat_pembekal",
                "label": "Alamat Syarikat Pembekal",
                "label_en": "Supplier Company Address",
                "type": "address_popup",
                "required": True,
                "source": None,
                "notes": "Click Add button to open popup for address entry",
                "selectors": [
                    "button:contains('Tambah')",
                    "button[id*='addAlamatPembekal']",
                ],
            },
        ],
    },
    "bahagian_d": {
        "title": "BAHAGIAN D - BUTIR-BUTIR LESEN/KELULUSAN DARIPADA JABATAN AGENSI BERKAITAN",
        "title_en": "Section D - License/Approval from Related Department/Agency",
        "fields": [
            {
                "id": "no_rujukan_pbt",
                "label": "No. Rujukan - Kelulusan Pihak Berkuasa/Majlis Kerajaan Tempatan",
                "label_en": "Reference No. - Local Authority Approval",
                "type": "text",
                "required": True,
                "source": None,
                "notes": "Mandatory for petroleum items",
                "selectors": [
                    "input[id*='pbt']",
                    "input[name*='pbt']",
                    "input[id*='rujukan']",
                ],
            },
        ],
    },
    "bahagian_e": {
        "title": "BAHAGIAN E - DOKUMEN MANDATORI - DOCUMENT CHECKLIST",
        "title_en": "Section E - Mandatory Documents - Document Checklist",
        "fields": [
            {
                "id": "upload_docs",
                "label": "Upload Dokumen Mandatori",
                "label_en": "Upload Mandatory Documents",
                "type": "file_upload",
                "required": True,
                "source": None,
                "notes": "Upload softcopy of all mandatory items. Click Upload button for each.",
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
                "notes": "Must tick checkbox before submitting",
                "selectors": [
                    "input[type='checkbox'][id*='perakuan']",
                    "input[type='checkbox'][id*='declare']",
                    "input[type='checkbox'][name*='perakuan']",
                    "input[type='checkbox'][name*='declare']",
                ],
            },
        ],
    },
}
