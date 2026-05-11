"""
Field Mapper Module
===================
Maps extracted PDF data to BLESS2 website form fields.
Updated based on official BLESS2 manuals:
- Permit Barang Kawalan Berjadual (KPDNKK)
- Lesen CSA Borong (KPDNHEP)

Form structure follows BAHAGIAN A through F + PERAKUAN.
"""

import re
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from loguru import logger

from .pdf_parser import ExtractedData, CompanyInfo, DirectorInfo


@dataclass
class FormField:
    """Represents a single form field on the BLESS2 website."""
    field_id: str
    field_name: str
    field_type: str  # text, select, radio, checkbox, date, textarea, file_upload, address_popup
    value: str = ""
    selector: str = ""
    required: bool = False
    options: List[str] = field(default_factory=list)
    validation_regex: str = ""
    section: str = ""
    notes: str = ""


@dataclass
class FormSection:
    """Represents a BAHAGIAN (section) of the BLESS2 form."""
    name: str
    title_malay: str = ""
    title_english: str = ""
    fields: List[FormField] = field(default_factory=list)
    url_path: str = ""
    notes: str = ""


class FieldMapper:
    """
    Maps extracted data to BLESS2 form fields.

    Based on official BLESS2 manual, form is divided into:
    - BAHAGIAN A: Butir-Butir Pemohon/Syarikat (Applicant/Company Details)
    - BAHAGIAN B: Butir-Butir Permit/Barang (Permit/Goods Details)
    - BAHAGIAN C: Maklumat Syarikat Pembekal (Supplier Info)
    - BAHAGIAN D: Butir-Butir Lesen/Kelulusan (License/Approval from Agencies)
    - BAHAGIAN E: Senarai Semak / Dokumen Mandatori (Checklist/Documents)
    - BAHAGIAN F: Dokumen Sokongan (Supporting Documents)
    - PERAKUAN: Declaration checkbox + Submit
    """

    # State mapping for BLESS2 dropdowns
    STATE_CODES = {
        "JOHOR": "01", "KEDAH": "02", "KELANTAN": "03",
        "MELAKA": "04", "NEGERI SEMBILAN": "05", "PAHANG": "06",
        "PERAK": "07", "PERLIS": "08", "PULAU PINANG": "09",
        "SABAH": "10", "SARAWAK": "11", "SELANGOR": "12",
        "TERENGGANU": "13", "W.P. KUALA LUMPUR": "14",
        "W.P. PUTRAJAYA": "15", "W.P. LABUAN": "16",
        "WILAYAH PERSEKUTUAN": "14",
    }

    # Bentuk Perniagaan (Business Entity Type) for BLESS2 dropdown
    BENTUK_PERNIAGAAN = {
        "PRIVATE COMPANY LIMITED BY SHARES": "ROC",
        "SDN BHD": "ROC",
        "SENDIRIAN BERHAD": "ROC",
        "PUBLIC COMPANY LIMITED BY SHARES": "ROC",
        "BHD": "ROC",
        "BERHAD": "ROC",
        "SOLE PROPRIETORSHIP": "ROB",
        "ENTERPRISE": "ROB",
        "PARTNERSHIP": "ROB",
        "LIMITED LIABILITY PARTNERSHIP": "PLT",
        "LLP": "PLT",
        "COOPERATIVE": "Cooperative",
        "KOPERASI": "Cooperative",
    }

    def __init__(self, form_config: Optional[Dict] = None):
        self.form_config = form_config or {}
        self.mapped_sections: List[FormSection] = []
        logger.info("Field Mapper initialized (BLESS2 Bahagian structure)")

    def map_data(self, extracted_data: ExtractedData) -> List[FormSection]:
        """
        Map extracted PDF data to BLESS2 BAHAGIAN sections.
        """
        self.mapped_sections = []

        # BAHAGIAN A - Company/Applicant details (from PDF)
        self._map_bahagian_a(extracted_data)

        # BAHAGIAN B - Permit/Goods details (partially from PDF)
        self._map_bahagian_b(extracted_data)

        # BAHAGIAN C - Supplier company info
        self._map_bahagian_c(extracted_data)

        # BAHAGIAN D - Agency approvals/licenses
        self._map_bahagian_d(extracted_data)

        # BAHAGIAN E - Document checklist (review only)
        self._map_bahagian_e(extracted_data)

        # BAHAGIAN F / PERAKUAN - Documents & Declaration
        self._map_bahagian_f_perakuan(extracted_data)

        logger.info("Mapped {} sections with {} total fields",
                   len(self.mapped_sections),
                   sum(len(s.fields) for s in self.mapped_sections))

        return self.mapped_sections

    def _map_bahagian_a(self, data: ExtractedData):
        """
        BAHAGIAN A - BUTIR-BUTIR PEMOHON/SYARIKAT / MAKLUMAT PERMOHONAN
        Core company information extracted from PDF documents.
        """
        company = data.company
        section = FormSection(
            name="BAHAGIAN A",
            title_malay="Butir-Butir Pemohon / Syarikat",
            title_english="Applicant / Company Details",
        )

        # Negeri (State)
        state_value = self._resolve_state(company.state)
        section.fields.append(FormField(
            field_id="negeri",
            field_name="Negeri",
            field_type="select",
            value=state_value,
            selector="select[id*='negeri'], select[name*='negeri'], select[id*='state']",
            required=True,
            options=list(self.STATE_CODES.keys()),
            section="BAHAGIAN A",
        ))

        # Cawangan Agensi Pemprosesan (Processing Branch)
        section.fields.append(FormField(
            field_id="cawangan_agensi",
            field_name="Cawangan Agensi Pemprosesan",
            field_type="select",
            value="",  # User must select - depends on state
            selector="select[id*='cawangan'], select[name*='cawangan'], select[id*='branch']",
            required=True,
            section="BAHAGIAN A",
            notes="Depends on Negeri selection. Cannot auto-fill without knowing agency.",
        ))

        # Bentuk Perniagaan (Business Entity Type)
        bentuk = self._resolve_bentuk_perniagaan(company.company_type)
        section.fields.append(FormField(
            field_id="bentuk_perniagaan",
            field_name="Bentuk Perniagaan",
            field_type="select",
            value=bentuk,
            selector="select[id*='bentuk'], select[name*='bentuk'], select[id*='businessType']",
            required=True,
            options=["Individual", "ROC", "ROB", "PLT", "Cooperative", "Government Organization", "ROS"],
            section="BAHAGIAN A",
        ))

        # Aktiviti Perniagaan (Business Activity)
        section.fields.append(FormField(
            field_id="aktiviti_perniagaan",
            field_name="Aktiviti Perniagaan",
            field_type="text",
            value=company.business_nature,
            selector="input[id*='aktiviti'], input[name*='aktiviti'], textarea[id*='aktiviti'], input[id*='activity']",
            required=True,
            section="BAHAGIAN A",
        ))

        # No. Telefon Pejabat (Office Phone)
        section.fields.append(FormField(
            field_id="no_telefon_pejabat",
            field_name="No. Telefon Pejabat",
            field_type="text",
            value=company.phone,
            selector="input[id*='noTel'], input[name*='noTel'], input[id*='phone'], input[id*='telefon']",
            required=True,
            section="BAHAGIAN A",
        ))

        # No. Telefon Bimbit (Mobile)
        section.fields.append(FormField(
            field_id="no_telefon_bimbit",
            field_name="No. Telefon Bimbit / No. HP",
            field_type="text",
            value=company.phone,  # Use same as office if no mobile
            selector="input[id*='bimbit'], input[name*='bimbit'], input[id*='mobile'], input[id*='hp'], input[id*='noHp']",
            required=True,
            section="BAHAGIAN A",
        ))

        # No. Faks (Fax)
        section.fields.append(FormField(
            field_id="no_faks",
            field_name="No. Faks",
            field_type="text",
            value=company.fax,
            selector="input[id*='faks'], input[name*='faks'], input[id*='fax']",
            required=True,
            section="BAHAGIAN A",
        ))

        # Email
        section.fields.append(FormField(
            field_id="email",
            field_name="Email",
            field_type="text",
            value=company.email,
            selector="input[id*='email'], input[name*='email'], input[type='email']",
            required=True,
            section="BAHAGIAN A",
            validation_regex=r"^[\w\.\-]+@[\w\.\-]+\.\w+$",
        ))

        self.mapped_sections.append(section)

    def _map_bahagian_b(self, data: ExtractedData):
        """
        BAHAGIAN B - BUTIR-BUTIR PERMIT / MAKLUMAT BARANG KUANTITI
        Permit details and goods information. Most fields are user-specific.
        """
        section = FormSection(
            name="BAHAGIAN B",
            title_malay="Butir-Butir Permit / Maklumat Barang",
            title_english="Permit Details / Goods Information",
            notes="Most fields require manual input (permit period, goods type, quantities)",
        )

        # Alamat Stor (Storage Address) - can be auto-filled from business address
        section.fields.append(FormField(
            field_id="alamat_stor",
            field_name="Alamat Stor dan Tempat Simpanan / Alamat Stor (Tempat Simpanan Barang)",
            field_type="address_popup",
            value=data.company.business_address or data.company.registered_address,
            selector="button:contains('Tambah'), button[id*='addAddress'], button[id*='addAlamat']",
            required=True,
            section="BAHAGIAN B",
            notes="Click Add button to open popup. Address from company registration.",
        ))

        self.mapped_sections.append(section)

    def _map_bahagian_c(self, data: ExtractedData):
        """
        BAHAGIAN C - BUTIR-BUTIR SYARIKAT PEMBEKAL / MAKLUMAT SYARIKAT PEMBEKAL
        Supplier company details. Mostly manual or auto-extracted from license no.
        """
        section = FormSection(
            name="BAHAGIAN C",
            title_malay="Maklumat Syarikat Pembekal",
            title_english="Supplier Company Information",
            notes="System auto-extracts from license number if exists. Otherwise manual entry.",
        )

        # These are typically filled by searching a license number
        # The system auto-populates: Tarikh Tamat, Nama Syarikat, No. Pendaftaran, Alamat
        section.fields.append(FormField(
            field_id="no_lesen_pembekal",
            field_name="No. Lesen Barang Kawalan",
            field_type="text",
            value="",
            selector="input[id*='noLesen'], input[name*='noLesen']",
            required=True,
            section="BAHAGIAN C",
            notes="Enter license no and click Search. System auto-fills supplier details.",
        ))

        self.mapped_sections.append(section)

    def _map_bahagian_d(self, data: ExtractedData):
        """
        BAHAGIAN D - BUTIR-BUTIR LESEN/KELULUSAN DARIPADA JABATAN/AGENSI
        Agency approvals and reference numbers. User-specific.
        """
        section = FormSection(
            name="BAHAGIAN D",
            title_malay="Butir-Butir Lesen/Kelulusan Daripada Jabatan/Agensi",
            title_english="License/Approval Details from Department/Agency",
            notes="Reference numbers from Fire Dept, PDA, Local Authority. User must provide.",
        )

        # No auto-fill possible - these are external reference numbers
        section.fields.append(FormField(
            field_id="no_rujukan_pbt",
            field_name="No. Rujukan - Kelulusan Pihak Berkuasa Tempatan",
            field_type="text",
            value="",
            selector="input[id*='pbt'], input[name*='pbt'], input[id*='rujukan'], input[id*='majlis']",
            required=True,
            section="BAHAGIAN D",
            notes="Local authority approval reference number",
        ))

        self.mapped_sections.append(section)

    def _map_bahagian_e(self, data: ExtractedData):
        """
        BAHAGIAN E - SENARAI SEMAK / DOKUMEN MANDATORI
        Checklist review section. No fields to fill.
        """
        section = FormSection(
            name="BAHAGIAN E",
            title_malay="Senarai Semak / Dokumen Mandatori",
            title_english="Checklist / Mandatory Documents",
            notes="Review section or document upload. Check items and upload softcopy.",
        )

        section.fields.append(FormField(
            field_id="upload_docs",
            field_name="Upload Dokumen Sokongan / Mandatori",
            field_type="file_upload",
            value="",
            selector="button:contains('Upload'), input[type='file'], button[id*='upload']",
            required=True,
            section="BAHAGIAN E",
            notes="Upload softcopy of all mandatory documents",
        ))

        self.mapped_sections.append(section)

    def _map_bahagian_f_perakuan(self, data: ExtractedData):
        """
        BAHAGIAN F (if exists) + PERAKUAN - Declaration
        """
        section = FormSection(
            name="PERAKUAN",
            title_malay="Perakuan",
            title_english="Declaration",
            notes="Tick checkbox to declare, then submit",
        )

        section.fields.append(FormField(
            field_id="perakuan_checkbox",
            field_name="Perakuan Pemohon (Declaration Checkbox)",
            field_type="checkbox",
            value="true",
            selector="input[type='checkbox'][id*='perakuan'], input[type='checkbox'][id*='declare'], input[type='checkbox'][name*='perakuan']",
            required=True,
            section="PERAKUAN",
            notes="Must tick before submit",
        ))

        self.mapped_sections.append(section)

    # ==========================================
    # Helper Methods
    # ==========================================

    def _resolve_state(self, state_raw: str) -> str:
        """Resolve state name to BLESS2 dropdown value."""
        if not state_raw:
            return ""
        state_upper = state_raw.upper().strip()
        # Direct match
        if state_upper in self.STATE_CODES:
            return state_upper
        # Partial match
        for state_name in self.STATE_CODES:
            if state_upper in state_name or state_name in state_upper:
                return state_name
        return state_raw

    def _resolve_bentuk_perniagaan(self, company_type: str) -> str:
        """Resolve company type to BLESS2 'Bentuk Perniagaan' value."""
        if not company_type:
            return ""
        ct_upper = company_type.upper().strip()
        for key, value in self.BENTUK_PERNIAGAAN.items():
            if key in ct_upper or ct_upper in key:
                return value
        # Default: if contains SDN BHD → ROC
        if "SDN" in ct_upper or "BHD" in ct_upper:
            return "ROC"
        if "ENTERPRISE" in ct_upper or "TRADING" in ct_upper:
            return "ROB"
        return ""

    def get_mapped_summary(self) -> Dict[str, Any]:
        """Get summary of mapped fields."""
        summary = {}
        for section in self.mapped_sections:
            fields_info = []
            for f in section.fields:
                fields_info.append({
                    "field": f.field_name,
                    "value": f.value[:50] + "..." if len(f.value) > 50 else f.value,
                    "required": f.required,
                    "has_value": bool(f.value),
                })
            summary[section.name] = {
                "title": section.title_malay,
                "total_fields": len(section.fields),
                "filled_fields": sum(1 for f in section.fields if f.value),
                "fields": fields_info,
            }
        return summary

    def export_to_dict(self) -> Dict[str, Any]:
        """Export all mapped data as a dictionary."""
        result = {}
        for section in self.mapped_sections:
            section_data = {}
            for f in section.fields:
                section_data[f.field_id] = {
                    "label": f.field_name,
                    "value": f.value,
                    "type": f.field_type,
                    "selector": f.selector,
                    "required": f.required,
                    "notes": f.notes,
                }
            result[section.name] = {
                "title_malay": section.title_malay,
                "title_english": section.title_english,
                "notes": section.notes,
                "fields": section_data,
            }
        return result

    def get_bahagian_a_data(self) -> Dict[str, str]:
        """
        Get BAHAGIAN A data as a flat dict for browser_automation.fill_bahagian_a().
        """
        data = {}
        for section in self.mapped_sections:
            if section.name == "BAHAGIAN A":
                for f in section.fields:
                    # Map field_id to the key expected by fill_bahagian_a
                    key_map = {
                        "negeri": "state",
                        "cawangan_agensi": "cawangan",
                        "bentuk_perniagaan": "company_type",
                        "aktiviti_perniagaan": "business_nature",
                        "no_telefon_pejabat": "phone",
                        "no_telefon_bimbit": "mobile",
                        "no_faks": "fax",
                        "email": "email",
                    }
                    mapped_key = key_map.get(f.field_id, f.field_id)
                    data[mapped_key] = f.value
                break
        return data
