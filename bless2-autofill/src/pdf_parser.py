"""
PDF Parser Module
=================
Extracts structured information from various Malaysian business documents:
- SSM Company Profile / Certificate of Incorporation
- Business Registration Forms
- Director IC/Passport documents
- Financial Statements
- Company Constitution (M&A)
"""

import re
import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime

import pdfplumber
from loguru import logger


@dataclass
class CompanyInfo:
    """Structured company information extracted from PDFs."""
    company_name: str = ""
    company_name_malay: str = ""
    registration_number: str = ""  # SSM No / MyCoID
    old_registration_number: str = ""  # Old format ROC/ROB
    company_type: str = ""  # Sdn Bhd, Bhd, Enterprise, etc.
    incorporation_date: str = ""
    business_nature: str = ""
    msic_code: str = ""
    msic_description: str = ""
    paid_up_capital: str = ""
    authorized_capital: str = ""
    registered_address: str = ""
    business_address: str = ""
    postcode: str = ""
    city: str = ""
    state: str = ""
    country: str = "MALAYSIA"
    phone: str = ""
    fax: str = ""
    email: str = ""
    website: str = ""
    status: str = ""  # Active, Dormant, etc.


@dataclass
class DirectorInfo:
    """Director/Shareholder information."""
    name: str = ""
    ic_number: str = ""  # NRIC / Passport
    nationality: str = ""
    address: str = ""
    date_of_birth: str = ""
    gender: str = ""
    designation: str = ""  # Director, Secretary, Shareholder
    appointment_date: str = ""
    shares_held: str = ""
    share_percentage: str = ""


@dataclass
class ExtractedData:
    """Complete extracted data from all PDF documents."""
    company: CompanyInfo = field(default_factory=CompanyInfo)
    directors: List[DirectorInfo] = field(default_factory=list)
    shareholders: List[DirectorInfo] = field(default_factory=list)
    secretary: Optional[DirectorInfo] = None
    raw_text: str = ""
    source_files: List[str] = field(default_factory=list)
    extraction_date: str = field(default_factory=lambda: datetime.now().isoformat())
    confidence_score: float = 0.0


class PDFParser:
    """
    Main PDF parser that extracts business information from Malaysian documents.
    Supports multiple document types and uses pattern matching for extraction.
    """

    # Malaysian state list for validation
    STATES = [
        "JOHOR", "KEDAH", "KELANTAN", "MELAKA", "NEGERI SEMBILAN",
        "PAHANG", "PERAK", "PERLIS", "PULAU PINANG", "SABAH",
        "SARAWAK", "SELANGOR", "TERENGGANU", "WILAYAH PERSEKUTUAN",
        "W.P. KUALA LUMPUR", "W.P. PUTRAJAYA", "W.P. LABUAN"
    ]

    # Common patterns for Malaysian business documents
    PATTERNS = {
        # SSM Registration Number formats
        "new_reg_no": r"(?:(?:Registration|Company)\s*(?:No|Number)|No\.\s*Syarikat|No\.\s*Pendaftaran)\s*[:\-]?\s*(\d{12}[\-]?[A-Z]?)",
        "old_reg_no": r"(?:\d{5,6}[\-][A-Z])",
        "mycoid": r"(\d{12})",
        
        # Company name patterns
        "sdn_bhd": r"(.+?)\s*(?:SDN\.?\s*BHD\.?|SENDIRIAN\s*BERHAD)",
        "bhd": r"(.+?)\s*(?:BHD\.?|BERHAD)",
        "enterprise": r"(.+?)\s*(?:ENTERPRISE|TRADING|INDUSTRIES)",
        
        # IC Number (NRIC)
        "ic_number": r"(\d{6}[\-]?\d{2}[\-]?\d{4})",
        
        # Date patterns
        "date_dmy": r"(\d{1,2}[\s/\-]\w+[\s/\-]\d{4})",
        "date_iso": r"(\d{4}[\-/]\d{2}[\-/]\d{2})",
        
        # Address patterns
        "postcode": r"\b(\d{5})\b",
        "phone": r"(?:Tel|Phone|No\.\s*Tel)[:\s]*([+\d\-\s()]{8,15})",
        "fax": r"(?:Fax|Faksimili)[:\s]*([+\d\-\s()]{8,15})",
        "email": r"[\w\.\-]+@[\w\.\-]+\.\w+",
        
        # Financial patterns
        "capital": r"(?:Modal|Capital|Paid[\-\s]?up)\s*[:\-]?\s*(?:RM|MYR)?\s*([\d,]+\.?\d*)",
        
        # MSIC Code
        "msic": r"(?:MSIC|Kod\s*MSIC)\s*[:\-]?\s*(\d{5})",
    }

    def __init__(self, ocr_enabled: bool = False):
        """
        Initialize PDF Parser.
        
        Args:
            ocr_enabled: Whether to use OCR for scanned documents
        """
        self.ocr_enabled = ocr_enabled
        self.extracted_data = ExtractedData()
        logger.info("PDF Parser initialized (OCR: {})", ocr_enabled)

    def parse_directory(self, directory: str) -> ExtractedData:
        """
        Parse all PDF files in a directory.
        
        Args:
            directory: Path to directory containing PDF files
            
        Returns:
            ExtractedData with all extracted information
        """
        pdf_files = list(Path(directory).glob("*.pdf")) + list(Path(directory).glob("*.PDF"))
        
        if not pdf_files:
            logger.warning("No PDF files found in {}", directory)
            return self.extracted_data

        logger.info("Found {} PDF files to process", len(pdf_files))
        
        for pdf_file in pdf_files:
            self.parse_file(str(pdf_file))
        
        self._calculate_confidence()
        return self.extracted_data

    def parse_file(self, file_path: str) -> ExtractedData:
        """
        Parse a single PDF file and extract relevant information.
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            ExtractedData with extracted information
        """
        if not os.path.exists(file_path):
            logger.error("File not found: {}", file_path)
            return self.extracted_data

        logger.info("Parsing file: {}", file_path)
        self.extracted_data.source_files.append(file_path)

        try:
            text = self._extract_text(file_path)
            self.extracted_data.raw_text += f"\n{'='*50}\n{file_path}\n{'='*50}\n{text}"
            
            # Detect document type and extract accordingly
            doc_type = self._detect_document_type(text)
            logger.info("Detected document type: {}", doc_type)
            
            if doc_type == "ssm_profile":
                self._extract_ssm_profile(text)
            elif doc_type == "certificate_incorporation":
                self._extract_certificate(text)
            elif doc_type == "form_9":
                self._extract_form9(text)
            elif doc_type == "form_24":
                self._extract_form24(text)
            elif doc_type == "form_49":
                self._extract_form49(text)
            elif doc_type == "annual_return":
                self._extract_annual_return(text)
            else:
                # Generic extraction
                self._extract_generic(text)
                
        except Exception as e:
            logger.error("Error parsing {}: {}", file_path, str(e))

        return self.extracted_data

    def _extract_text(self, file_path: str) -> str:
        """Extract text from PDF using pdfplumber."""
        full_text = ""
        
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    full_text += page_text + "\n"
                    
                # Also extract tables
                tables = page.extract_tables()
                for table in tables:
                    for row in table:
                        if row:
                            full_text += " | ".join([str(cell) if cell else "" for cell in row]) + "\n"
        
        if not full_text.strip() and self.ocr_enabled:
            full_text = self._ocr_extract(file_path)
            
        return full_text

    def _ocr_extract(self, file_path: str) -> str:
        """Extract text using OCR for scanned documents."""
        try:
            import pytesseract
            from pdf2image import convert_from_path
            
            images = convert_from_path(file_path)
            text = ""
            for image in images:
                text += pytesseract.image_to_string(image, lang='eng+msa') + "\n"
            return text
        except ImportError:
            logger.warning("OCR dependencies not installed. Install pytesseract and pdf2image.")
            return ""
        except Exception as e:
            logger.error("OCR extraction failed: {}", str(e))
            return ""

    def _detect_document_type(self, text: str) -> str:
        """Detect the type of Malaysian business document."""
        text_upper = text.upper()
        
        if "COMPANY PROFILE" in text_upper or "PROFIL SYARIKAT" in text_upper:
            return "ssm_profile"
        elif "CERTIFICATE OF INCORPORATION" in text_upper or "PERAKUAN PEMERBADANAN" in text_upper:
            return "certificate_incorporation"
        elif "FORM 9" in text_upper or "BORANG 9" in text_upper:
            return "form_9"
        elif "FORM 24" in text_upper or "BORANG 24" in text_upper:
            return "form_24"
        elif "FORM 49" in text_upper or "BORANG 49" in text_upper:
            return "form_49"
        elif "ANNUAL RETURN" in text_upper or "PENYATA TAHUNAN" in text_upper:
            return "annual_return"
        else:
            return "generic"

    def _extract_ssm_profile(self, text: str):
        """Extract data from SSM Company Profile document."""
        lines = text.split('\n')
        company = self.extracted_data.company
        
        for i, line in enumerate(lines):
            line_clean = line.strip()
            line_upper = line_clean.upper()
            
            # Registration Number
            if any(keyword in line_upper for keyword in ["REGISTRATION NO", "NO. PENDAFTARAN", "COMPANY NO"]):
                reg_match = re.search(r'(\d{12}[\-]?[A-Z]?)', line_clean)
                if reg_match:
                    company.registration_number = reg_match.group(1)
                    
            # Company Name
            if any(keyword in line_upper for keyword in ["COMPANY NAME", "NAMA SYARIKAT"]):
                # Usually the value is on the same line or next line
                name_match = re.search(r'(?:Company Name|Nama Syarikat)\s*[:\-]?\s*(.+)', line_clean, re.IGNORECASE)
                if name_match:
                    company.company_name = name_match.group(1).strip()
                elif i + 1 < len(lines) and lines[i+1].strip():
                    company.company_name = lines[i+1].strip()
            
            # Company Type
            if any(keyword in line_upper for keyword in ["COMPANY TYPE", "JENIS SYARIKAT"]):
                type_match = re.search(r'(?:Company Type|Jenis Syarikat)\s*[:\-]?\s*(.+)', line_clean, re.IGNORECASE)
                if type_match:
                    company.company_type = type_match.group(1).strip()
                    
            # Status
            if any(keyword in line_upper for keyword in ["COMPANY STATUS", "STATUS SYARIKAT"]):
                status_match = re.search(r'(?:Company Status|Status Syarikat)\s*[:\-]?\s*(.+)', line_clean, re.IGNORECASE)
                if status_match:
                    company.status = status_match.group(1).strip()
                    
            # Incorporation Date
            if any(keyword in line_upper for keyword in ["INCORPORATION DATE", "TARIKH PEMERBADANAN", "DATE OF REGISTRATION"]):
                date_match = re.search(r'(\d{1,2}[\s/\-]\w+[\s/\-]\d{4}|\d{4}[\-/]\d{2}[\-/]\d{2}|\d{2}/\d{2}/\d{4})', line_clean)
                if date_match:
                    company.incorporation_date = date_match.group(1)
                    
            # Registered Address
            if any(keyword in line_upper for keyword in ["REGISTERED ADDRESS", "ALAMAT BERDAFTAR"]):
                address_lines = []
                for j in range(i+1, min(i+5, len(lines))):
                    if lines[j].strip() and not any(kw in lines[j].upper() for kw in ["BUSINESS ADDRESS", "NATURE", "MSIC", "PRINCIPAL"]):
                        address_lines.append(lines[j].strip())
                    else:
                        break
                if address_lines:
                    company.registered_address = ", ".join(address_lines)
                    self._extract_address_parts(company.registered_address, company)
                    
            # Business Address
            if any(keyword in line_upper for keyword in ["BUSINESS ADDRESS", "ALAMAT PERNIAGAAN"]):
                address_lines = []
                for j in range(i+1, min(i+5, len(lines))):
                    if lines[j].strip() and not any(kw in lines[j].upper() for kw in ["NATURE", "MSIC", "PHONE", "TEL"]):
                        address_lines.append(lines[j].strip())
                    else:
                        break
                if address_lines:
                    company.business_address = ", ".join(address_lines)
                    
            # Nature of Business / MSIC
            if any(keyword in line_upper for keyword in ["NATURE OF BUSINESS", "JENIS PERNIAGAAN", "PRINCIPAL ACTIVITY"]):
                nature_match = re.search(r'(?:Nature of Business|Jenis Perniagaan|Principal Activity)\s*[:\-]?\s*(.+)', line_clean, re.IGNORECASE)
                if nature_match:
                    company.business_nature = nature_match.group(1).strip()
                elif i + 1 < len(lines):
                    company.business_nature = lines[i+1].strip()
            
            # MSIC Code
            msic_match = re.search(self.PATTERNS["msic"], line_clean)
            if msic_match:
                company.msic_code = msic_match.group(1)
                
            # Paid-up Capital
            if any(keyword in line_upper for keyword in ["PAID-UP", "PAID UP", "MODAL BERBAYAR"]):
                capital_match = re.search(r'(?:RM|MYR)?\s*([\d,]+\.?\d*)', line_clean)
                if capital_match:
                    company.paid_up_capital = capital_match.group(1)
                    
            # Phone
            phone_match = re.search(self.PATTERNS["phone"], line_clean)
            if phone_match:
                company.phone = phone_match.group(1).strip()
                
            # Fax
            fax_match = re.search(self.PATTERNS["fax"], line_clean)
            if fax_match:
                company.fax = fax_match.group(1).strip()
                
            # Email
            email_match = re.search(self.PATTERNS["email"], line_clean)
            if email_match:
                company.email = email_match.group(0)

        # Extract directors section
        self._extract_directors_from_text(text)

    def _extract_certificate(self, text: str):
        """Extract data from Certificate of Incorporation."""
        company = self.extracted_data.company
        
        # Company name - usually appears prominently
        name_patterns = [
            r"certify that\s+(.+?)\s+is",
            r"memperakui bahawa\s+(.+?)\s+adalah",
            r"company name[:\s]+(.+?)(?:\n|$)",
        ]
        
        for pattern in name_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                company.company_name = match.group(1).strip()
                break
        
        # Registration number
        reg_match = re.search(r'(\d{12}[\-]?[A-Z]?)', text)
        if reg_match:
            company.registration_number = reg_match.group(1)
            
        # Incorporation date
        date_match = re.search(r'(?:on and from the|dari)\s+(\d{1,2}\s*\w+\s*(?:day of\s*)?\w+\s*\d{4})', text, re.IGNORECASE)
        if date_match:
            company.incorporation_date = date_match.group(1)
            
        # Company type
        if "private company" in text.lower() or "syarikat sendirian" in text.lower():
            company.company_type = "Private Company Limited by Shares"
        elif "public company" in text.lower():
            company.company_type = "Public Company Limited by Shares"

    def _extract_form9(self, text: str):
        """Extract data from Form 9 (Certificate of Incorporation)."""
        self._extract_certificate(text)

    def _extract_form24(self, text: str):
        """Extract data from Form 24 (Annual Return of Company with Share Capital)."""
        self._extract_ssm_profile(text)
        
    def _extract_form49(self, text: str):
        """Extract data from Form 49 (Directors/Officers notification)."""
        self._extract_directors_from_text(text)

    def _extract_annual_return(self, text: str):
        """Extract data from Annual Return."""
        self._extract_ssm_profile(text)

    def _extract_generic(self, text: str):
        """Generic extraction for unrecognized document types."""
        company = self.extracted_data.company
        
        # Try to extract any registration number
        reg_match = re.search(r'(\d{12}[\-]?[A-Z]?)', text)
        if reg_match and not company.registration_number:
            company.registration_number = reg_match.group(1)
            
        # Try to extract company name (look for SDN BHD pattern)
        name_match = re.search(r'([A-Z][A-Z\s&\.\-]+(?:SDN\.?\s*BHD\.?|BERHAD|ENTERPRISE|TRADING))', text)
        if name_match and not company.company_name:
            company.company_name = name_match.group(1).strip()
            
        # Extract email
        email_match = re.search(self.PATTERNS["email"], text)
        if email_match and not company.email:
            company.email = email_match.group(0)
            
        # Extract phone
        phone_match = re.search(self.PATTERNS["phone"], text)
        if phone_match and not company.phone:
            company.phone = phone_match.group(1).strip()

        # Try to find directors
        self._extract_directors_from_text(text)

    def _extract_directors_from_text(self, text: str):
        """Extract director information from text."""
        lines = text.split('\n')
        in_director_section = False
        current_director = None
        
        for i, line in enumerate(lines):
            line_clean = line.strip()
            line_upper = line_clean.upper()
            
            # Detect director section
            if any(keyword in line_upper for keyword in ["DIRECTOR", "PENGARAH", "OFFICER"]):
                in_director_section = True
                continue
                
            if in_director_section:
                # Look for IC number as anchor for new director entry
                ic_match = re.search(self.PATTERNS["ic_number"], line_clean)
                
                if ic_match:
                    # Check if this IC is already known
                    ic_num = ic_match.group(1)
                    existing = [d for d in self.extracted_data.directors if d.ic_number == ic_num]
                    
                    if not existing:
                        current_director = DirectorInfo()
                        current_director.ic_number = ic_num
                        
                        # Try to get name from previous or same line
                        name_part = line_clean[:line_clean.find(ic_num)].strip()
                        if name_part and len(name_part) > 3:
                            current_director.name = name_part.rstrip('- :')
                        elif i > 0 and lines[i-1].strip():
                            current_director.name = lines[i-1].strip()
                            
                        # Extract DOB from IC (first 6 digits = YYMMDD)
                        ic_digits = ic_num.replace("-", "")
                        if len(ic_digits) >= 6:
                            year = int(ic_digits[0:2])
                            month = ic_digits[2:4]
                            day = ic_digits[4:6]
                            year = 1900 + year if year > 30 else 2000 + year
                            current_director.date_of_birth = f"{day}/{month}/{year}"
                            
                            # Gender from last digit
                            if len(ic_digits) == 12:
                                last_digit = int(ic_digits[-1])
                                current_director.gender = "Male" if last_digit % 2 != 0 else "Female"
                        
                        current_director.nationality = "MALAYSIAN"
                        current_director.designation = "Director"
                        self.extracted_data.directors.append(current_director)
                        
                # End of director section detection
                if any(keyword in line_upper for keyword in ["SECRETARY", "SETIAUSAHA", "SHAREHOLDER", "SHARE CAPITAL"]):
                    in_director_section = False

    def _extract_address_parts(self, address: str, company: CompanyInfo):
        """Extract postcode, city, and state from address string."""
        # Postcode
        postcode_match = re.search(r'\b(\d{5})\b', address)
        if postcode_match:
            company.postcode = postcode_match.group(1)
            
        # State
        for state in self.STATES:
            if state.upper() in address.upper():
                company.state = state
                break
                
        # City - typically appears before postcode or state
        if company.postcode:
            # City is usually after postcode
            city_match = re.search(r'\d{5}\s+([A-Za-z\s]+?)(?:,|\.|$)', address)
            if city_match:
                company.city = city_match.group(1).strip()

    def _calculate_confidence(self):
        """Calculate confidence score based on completeness of extraction."""
        company = self.extracted_data.company
        score = 0.0
        total_fields = 10  # Key fields
        
        if company.company_name:
            score += 1
        if company.registration_number:
            score += 1
        if company.company_type:
            score += 1
        if company.incorporation_date:
            score += 1
        if company.registered_address:
            score += 1
        if company.business_nature:
            score += 1
        if company.paid_up_capital:
            score += 1
        if company.postcode:
            score += 1
        if company.state:
            score += 1
        if self.extracted_data.directors:
            score += 1
            
        self.extracted_data.confidence_score = score / total_fields

    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of extracted data."""
        data = self.extracted_data
        return {
            "company_name": data.company.company_name,
            "registration_number": data.company.registration_number,
            "company_type": data.company.company_type,
            "incorporation_date": data.company.incorporation_date,
            "business_nature": data.company.business_nature,
            "registered_address": data.company.registered_address,
            "state": data.company.state,
            "directors_count": len(data.directors),
            "confidence_score": f"{data.confidence_score:.0%}",
            "source_files": data.source_files,
        }
