"""
Field Mapper Module
===================
Maps extracted PDF data to BLESS2 website form fields.
Handles data transformation, validation, and formatting for
the Malaysian Business Licensing Electronic Support System.
"""

import re
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from loguru import logger

from .pdf_parser import ExtractedData, CompanyInfo, DirectorInfo


@dataclass
class FormField:
    """Represents a single form field on the BLESS2 website."""
    field_id: str                    # HTML element ID or name
    field_name: str                  # Human-readable field name
    field_type: str                  # text, select, radio, checkbox, date, textarea
    value: str = ""                  # Value to fill
    selector: str = ""              # CSS selector or XPath
    required: bool = False
    options: List[str] = field(default_factory=list)  # For select/radio fields
    validation_regex: str = ""
    section: str = ""               # Form section name
    notes: str = ""                 # Any special handling notes


@dataclass
class FormSection:
    """Represents a section of the BLESS2 form."""
    name: str
    fields: List[FormField] = field(default_factory=list)
    url_path: str = ""              # URL path for this section


class FieldMapper:
    """
    Maps extracted data to BLESS2 form fields.
    
    The BLESS2 system typically requires:
    1. Company Information - Basic company details
    2. Business Details - Nature of business, MSIC codes
    3. Director/Owner Information - Personal details of directors
    4. Address Information - Registered and business addresses
    5. Financial Information - Capital and revenue details
    6. License-Specific Fields - Varies by license type
    """

    # State code mapping for BLESS2 dropdowns
    STATE_CODES = {
        "JOHOR": "01",
        "KEDAH": "02",
        "KELANTAN": "03",
        "MELAKA": "04",
        "NEGERI SEMBILAN": "05",
        "PAHANG": "06",
        "PERAK": "07",
        "PERLIS": "08",
        "PULAU PINANG": "09",
        "SABAH": "10",
        "SARAWAK": "11",
        "SELANGOR": "12",
        "TERENGGANU": "13",
        "W.P. KUALA LUMPUR": "14",
        "W.P. PUTRAJAYA": "15",
        "W.P. LABUAN": "16",
        "WILAYAH PERSEKUTUAN": "14",
    }

    # Company type mapping
    COMPANY_TYPE_CODES = {
        "PRIVATE COMPANY LIMITED BY SHARES": "01",
        "SDN BHD": "01",
        "SENDIRIAN BERHAD": "01",
        "PUBLIC COMPANY LIMITED BY SHARES": "02",
        "BHD": "02",
        "BERHAD": "02",
        "SOLE PROPRIETORSHIP": "03",
        "ENTERPRISE": "03",
        "PARTNERSHIP": "04",
        "LIMITED LIABILITY PARTNERSHIP": "05",
        "LLP": "05",
    }

    # Nationality mapping
    NATIONALITY_CODES = {
        "MALAYSIAN": "MY",
        "MALAYSIA": "MY",
        "SINGAPOREAN": "SG",
        "SINGAPORE": "SG",
        "INDONESIAN": "ID",
        "INDONESIA": "ID",
        "CHINESE": "CN",
        "CHINA": "CN",
        "INDIAN": "IN",
        "INDIA": "IN",
        "BRITISH": "GB",
        "AMERICAN": "US",
        "AUSTRALIAN": "AU",
        "JAPANESE": "JP",
        "KOREAN": "KR",
    }

    def __init__(self, form_config: Optional[Dict] = None):
        """
        Initialize Field Mapper.
        
        Args:
            form_config: Optional custom form configuration override
        """
        self.form_config = form_config or self._default_form_config()
        self.mapped_sections: List[FormSection] = []
        logger.info("Field Mapper initialized")

    def map_data(self, extracted_data: ExtractedData) -> List[FormSection]:
        """
        Map extracted PDF data to BLESS2 form sections.
        
        Args:
            extracted_data: Data extracted from PDF parser
            
        Returns:
            List of FormSection with mapped field values
        """
        self.mapped_sections = []
        
        # Section 1: Company Information
        self._map_company_info(extracted_data.company)
        
        # Section 2: Business Details
        self._map_business_details(extracted_data.company)
        
        # Section 3: Address Information
        self._map_address_info(extracted_data.company)
        
        # Section 4: Director/Owner Information
        if extracted_data.directors:
            self._map_director_info(extracted_data.directors)
            
        # Section 5: Financial Information
        self._map_financial_info(extracted_data.company)
        
        # Section 6: Contact Information
        self._map_contact_info(extracted_data.company)
        
        logger.info("Mapped {} sections with total {} fields", 
                   len(self.mapped_sections),
                   sum(len(s.fields) for s in self.mapped_sections))
        
        return self.mapped_sections

    def _map_company_info(self, company: CompanyInfo):
        """Map company information section."""
        section = FormSection(
            name="Company Information",
            url_path="/bless2/private/application/company-info"
        )
        
        # Company Name
        section.fields.append(FormField(
            field_id="companyName",
            field_name="Nama Syarikat / Company Name",
            field_type="text",
            value=company.company_name,
            selector="input[name='companyName'], #companyName, input[id*='company'][id*='name']",
            required=True,
            section="Company Information"
        ))
        
        # Registration Number (SSM/MyCoID)
        section.fields.append(FormField(
            field_id="registrationNo",
            field_name="No. Pendaftaran / Registration No.",
            field_type="text",
            value=self._format_registration_number(company.registration_number),
            selector="input[name='registrationNo'], #registrationNo, input[id*='reg'][id*='no'], input[id*='ssm']",
            required=True,
            section="Company Information"
        ))
        
        # Old Registration Number
        if company.old_registration_number:
            section.fields.append(FormField(
                field_id="oldRegistrationNo",
                field_name="No. Pendaftaran Lama / Old Registration No.",
                field_type="text",
                value=company.old_registration_number,
                selector="input[name='oldRegistrationNo'], #oldRegistrationNo",
                required=False,
                section="Company Information"
            ))
        
        # Company Type
        company_type_code = self._get_company_type_code(company.company_type)
        section.fields.append(FormField(
            field_id="companyType",
            field_name="Jenis Syarikat / Company Type",
            field_type="select",
            value=company_type_code,
            selector="select[name='companyType'], #companyType, select[id*='company'][id*='type']",
            required=True,
            options=list(self.COMPANY_TYPE_CODES.keys()),
            section="Company Information"
        ))
        
        # Incorporation Date
        section.fields.append(FormField(
            field_id="incorporationDate",
            field_name="Tarikh Pemerbadanan / Incorporation Date",
            field_type="date",
            value=self._format_date(company.incorporation_date),
            selector="input[name='incorporationDate'], #incorporationDate, input[type='date'][id*='incorp']",
            required=True,
            section="Company Information"
        ))
        
        # Company Status
        section.fields.append(FormField(
            field_id="companyStatus",
            field_name="Status Syarikat / Company Status",
            field_type="select",
            value=company.status or "ACTIVE",
            selector="select[name='companyStatus'], #companyStatus",
            required=False,
            options=["ACTIVE", "DORMANT", "WINDING UP"],
            section="Company Information"
        ))
        
        self.mapped_sections.append(section)

    def _map_business_details(self, company: CompanyInfo):
        """Map business details section."""
        section = FormSection(
            name="Business Details",
            url_path="/bless2/private/application/business-details"
        )
        
        # Nature of Business
        section.fields.append(FormField(
            field_id="businessNature",
            field_name="Jenis Perniagaan / Nature of Business",
            field_type="textarea",
            value=company.business_nature,
            selector="textarea[name='businessNature'], #businessNature, textarea[id*='nature'], input[id*='nature']",
            required=True,
            section="Business Details"
        ))
        
        # MSIC Code
        section.fields.append(FormField(
            field_id="msicCode",
            field_name="Kod MSIC / MSIC Code",
            field_type="text",
            value=company.msic_code,
            selector="input[name='msicCode'], #msicCode, input[id*='msic']",
            required=True,
            section="Business Details"
        ))
        
        # MSIC Description
        section.fields.append(FormField(
            field_id="msicDescription",
            field_name="Keterangan MSIC / MSIC Description",
            field_type="text",
            value=company.msic_description or company.business_nature,
            selector="input[name='msicDescription'], #msicDescription",
            required=False,
            section="Business Details"
        ))
        
        self.mapped_sections.append(section)

    def _map_address_info(self, company: CompanyInfo):
        """Map address information section."""
        section = FormSection(
            name="Address Information",
            url_path="/bless2/private/application/address"
        )
        
        # Registered Address
        section.fields.append(FormField(
            field_id="registeredAddress",
            field_name="Alamat Berdaftar / Registered Address",
            field_type="textarea",
            value=company.registered_address,
            selector="textarea[name='registeredAddress'], #registeredAddress, textarea[id*='reg'][id*='addr']",
            required=True,
            section="Address Information"
        ))
        
        # Business Address
        section.fields.append(FormField(
            field_id="businessAddress",
            field_name="Alamat Perniagaan / Business Address",
            field_type="textarea",
            value=company.business_address or company.registered_address,
            selector="textarea[name='businessAddress'], #businessAddress, textarea[id*='bus'][id*='addr']",
            required=True,
            section="Address Information"
        ))
        
        # Postcode
        section.fields.append(FormField(
            field_id="postcode",
            field_name="Poskod / Postcode",
            field_type="text",
            value=company.postcode,
            selector="input[name='postcode'], #postcode, input[id*='postcode'], input[id*='poskod']",
            required=True,
            validation_regex=r"^\d{5}$",
            section="Address Information"
        ))
        
        # City
        section.fields.append(FormField(
            field_id="city",
            field_name="Bandar / City",
            field_type="text",
            value=company.city,
            selector="input[name='city'], #city, input[id*='city'], input[id*='bandar']",
            required=True,
            section="Address Information"
        ))
        
        # State
        state_code = self.STATE_CODES.get(company.state.upper(), "") if company.state else ""
        section.fields.append(FormField(
            field_id="state",
            field_name="Negeri / State",
            field_type="select",
            value=state_code or company.state,
            selector="select[name='state'], #state, select[id*='state'], select[id*='negeri']",
            required=True,
            options=list(self.STATE_CODES.keys()),
            section="Address Information"
        ))
        
        # Country
        section.fields.append(FormField(
            field_id="country",
            field_name="Negara / Country",
            field_type="select",
            value="MY",
            selector="select[name='country'], #country, select[id*='country'], select[id*='negara']",
            required=False,
            section="Address Information"
        ))
        
        self.mapped_sections.append(section)

    def _map_director_info(self, directors: List[DirectorInfo]):
        """Map director/owner information section."""
        section = FormSection(
            name="Director Information",
            url_path="/bless2/private/application/director-info"
        )
        
        for idx, director in enumerate(directors):
            prefix = f"director[{idx}]"
            
            # Director Name
            section.fields.append(FormField(
                field_id=f"{prefix}.name",
                field_name=f"Nama Pengarah {idx+1} / Director {idx+1} Name",
                field_type="text",
                value=director.name,
                selector=f"input[name='{prefix}.name'], input[id*='director'][id*='name']:nth-of-type({idx+1})",
                required=True,
                section="Director Information"
            ))
            
            # IC Number
            section.fields.append(FormField(
                field_id=f"{prefix}.icNumber",
                field_name=f"No. KP Pengarah {idx+1} / Director {idx+1} IC No.",
                field_type="text",
                value=self._format_ic_number(director.ic_number),
                selector=f"input[name='{prefix}.icNumber'], input[id*='director'][id*='ic']:nth-of-type({idx+1})",
                required=True,
                validation_regex=r"^\d{6}-\d{2}-\d{4}$",
                section="Director Information"
            ))
            
            # Nationality
            nationality_code = self.NATIONALITY_CODES.get(director.nationality.upper(), "MY") if director.nationality else "MY"
            section.fields.append(FormField(
                field_id=f"{prefix}.nationality",
                field_name=f"Kewarganegaraan Pengarah {idx+1} / Director {idx+1} Nationality",
                field_type="select",
                value=nationality_code,
                selector=f"select[name='{prefix}.nationality']",
                required=True,
                section="Director Information"
            ))
            
            # Gender
            section.fields.append(FormField(
                field_id=f"{prefix}.gender",
                field_name=f"Jantina Pengarah {idx+1} / Director {idx+1} Gender",
                field_type="radio",
                value=director.gender or "",
                selector=f"input[name='{prefix}.gender']",
                required=True,
                options=["Male", "Female"],
                section="Director Information"
            ))
            
            # Date of Birth
            section.fields.append(FormField(
                field_id=f"{prefix}.dob",
                field_name=f"Tarikh Lahir Pengarah {idx+1} / Director {idx+1} DOB",
                field_type="date",
                value=self._format_date(director.date_of_birth),
                selector=f"input[name='{prefix}.dob'], input[type='date'][id*='director'][id*='dob']",
                required=True,
                section="Director Information"
            ))
            
            # Address
            section.fields.append(FormField(
                field_id=f"{prefix}.address",
                field_name=f"Alamat Pengarah {idx+1} / Director {idx+1} Address",
                field_type="textarea",
                value=director.address,
                selector=f"textarea[name='{prefix}.address']",
                required=False,
                section="Director Information"
            ))
            
            # Designation
            section.fields.append(FormField(
                field_id=f"{prefix}.designation",
                field_name=f"Jawatan Pengarah {idx+1} / Director {idx+1} Designation",
                field_type="select",
                value=director.designation,
                selector=f"select[name='{prefix}.designation']",
                required=False,
                options=["Director", "Managing Director", "Executive Director", "Independent Director"],
                section="Director Information"
            ))
        
        self.mapped_sections.append(section)

    def _map_financial_info(self, company: CompanyInfo):
        """Map financial information section."""
        section = FormSection(
            name="Financial Information",
            url_path="/bless2/private/application/financial"
        )
        
        # Paid-up Capital
        section.fields.append(FormField(
            field_id="paidUpCapital",
            field_name="Modal Berbayar / Paid-up Capital (RM)",
            field_type="text",
            value=self._format_currency(company.paid_up_capital),
            selector="input[name='paidUpCapital'], #paidUpCapital, input[id*='capital'], input[id*='modal']",
            required=True,
            section="Financial Information"
        ))
        
        # Authorized Capital
        if company.authorized_capital:
            section.fields.append(FormField(
                field_id="authorizedCapital",
                field_name="Modal Dibenarkan / Authorized Capital (RM)",
                field_type="text",
                value=self._format_currency(company.authorized_capital),
                selector="input[name='authorizedCapital'], #authorizedCapital",
                required=False,
                section="Financial Information"
            ))
        
        self.mapped_sections.append(section)

    def _map_contact_info(self, company: CompanyInfo):
        """Map contact information section."""
        section = FormSection(
            name="Contact Information",
            url_path="/bless2/private/application/contact"
        )
        
        # Phone
        section.fields.append(FormField(
            field_id="phone",
            field_name="No. Telefon / Phone Number",
            field_type="text",
            value=company.phone,
            selector="input[name='phone'], #phone, input[id*='phone'], input[id*='tel']",
            required=True,
            section="Contact Information"
        ))
        
        # Fax
        section.fields.append(FormField(
            field_id="fax",
            field_name="No. Faks / Fax Number",
            field_type="text",
            value=company.fax,
            selector="input[name='fax'], #fax, input[id*='fax']",
            required=False,
            section="Contact Information"
        ))
        
        # Email
        section.fields.append(FormField(
            field_id="email",
            field_name="Emel / Email",
            field_type="text",
            value=company.email,
            selector="input[name='email'], #email, input[id*='email'], input[type='email']",
            required=True,
            validation_regex=r"^[\w\.\-]+@[\w\.\-]+\.\w+$",
            section="Contact Information"
        ))
        
        # Website
        section.fields.append(FormField(
            field_id="website",
            field_name="Laman Web / Website",
            field_type="text",
            value=company.website,
            selector="input[name='website'], #website, input[id*='website'], input[id*='url']",
            required=False,
            section="Contact Information"
        ))
        
        self.mapped_sections.append(section)

    # ==========================================
    # Helper / Formatting Methods
    # ==========================================

    def _format_registration_number(self, reg_no: str) -> str:
        """Format registration number to standard format."""
        if not reg_no:
            return ""
        # Remove spaces and ensure proper format
        cleaned = re.sub(r'[\s]', '', reg_no)
        return cleaned

    def _format_ic_number(self, ic: str) -> str:
        """Format IC number to standard XXXXXX-XX-XXXX format."""
        if not ic:
            return ""
        # Remove existing dashes and spaces
        digits = re.sub(r'[\-\s]', '', ic)
        if len(digits) == 12:
            return f"{digits[0:6]}-{digits[6:8]}-{digits[8:12]}"
        return ic

    def _format_date(self, date_str: str) -> str:
        """Format date to DD/MM/YYYY format (common in Malaysian forms)."""
        if not date_str:
            return ""
            
        # Try various input formats
        import re
        from datetime import datetime
        
        formats_to_try = [
            r"(\d{1,2})/(\d{1,2})/(\d{4})",  # DD/MM/YYYY
            r"(\d{4})-(\d{2})-(\d{2})",        # YYYY-MM-DD
            r"(\d{1,2})\s+(\w+)\s+(\d{4})",    # DD Month YYYY
        ]
        
        # Already in DD/MM/YYYY format
        if re.match(r'\d{1,2}/\d{1,2}/\d{4}', date_str):
            return date_str
            
        # ISO format
        iso_match = re.match(r'(\d{4})-(\d{2})-(\d{2})', date_str)
        if iso_match:
            return f"{iso_match.group(3)}/{iso_match.group(2)}/{iso_match.group(1)}"
        
        return date_str

    def _format_currency(self, amount: str) -> str:
        """Format currency amount (remove RM prefix, add commas)."""
        if not amount:
            return ""
        # Remove RM/MYR prefix and spaces
        cleaned = re.sub(r'[RM\sMYR]', '', amount)
        # Remove existing commas
        cleaned = cleaned.replace(',', '')
        
        try:
            value = float(cleaned)
            return f"{value:,.2f}"
        except ValueError:
            return cleaned

    def _get_company_type_code(self, company_type: str) -> str:
        """Get the company type code for dropdown selection."""
        if not company_type:
            return ""
        for key, code in self.COMPANY_TYPE_CODES.items():
            if key.upper() in company_type.upper() or company_type.upper() in key.upper():
                return code
        return ""

    def _default_form_config(self) -> Dict:
        """Default form configuration."""
        return {
            "base_url": "https://bless2.bless.gov.my/bless2/private",
            "timeout": 30,
            "retry_attempts": 3,
        }

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
                "total_fields": len(section.fields),
                "filled_fields": sum(1 for f in section.fields if f.value),
                "fields": fields_info,
            }
        return summary

    def export_to_dict(self) -> Dict[str, Any]:
        """Export all mapped data as a dictionary for JSON serialization."""
        result = {}
        for section in self.mapped_sections:
            section_data = {}
            for f in section.fields:
                section_data[f.field_id] = {
                    "value": f.value,
                    "type": f.field_type,
                    "selector": f.selector,
                    "required": f.required,
                }
            result[section.name] = section_data
        return result
