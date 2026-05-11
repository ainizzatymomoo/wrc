"""
AI Engine Module (OpenRouter Integration)
==========================================
Uses LLM via OpenRouter API to:
1. Intelligently extract & recognize data from PDF text
2. Auto-match extracted data to BLESS2 form fields
3. Understand page DOM structure and map fields dynamically

Supports any model available on OpenRouter (GPT-4o, Claude, Gemini, etc.)
"""

import os
import json
import re
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass

import httpx
from loguru import logger


@dataclass
class AIConfig:
    """AI Engine configuration."""
    api_key: str = ""
    base_url: str = "https://openrouter.ai/api/v1"
    model: str = "openai/gpt-4o-mini"  # Default to cost-effective model
    fallback_model: str = "google/gemini-2.0-flash-001"
    max_tokens: int = 4096
    temperature: float = 0.1  # Low temp for structured extraction
    timeout: int = 60
    site_url: str = "https://github.com/ainizzatymomoo/wrc"
    app_name: str = "BLESS2-AutoFill"


class AIEngine:
    """
    AI-powered engine for intelligent PDF parsing and form field matching.
    Uses OpenRouter API (OpenAI-compatible) to access multiple LLM providers.
    """

    def __init__(self, config: Optional[AIConfig] = None):
        """
        Initialize AI Engine.
        
        Args:
            config: AI configuration. If not provided, reads from env vars.
        """
        self.config = config or AIConfig()
        
        # Get API key from config or environment
        if not self.config.api_key:
            self.config.api_key = os.getenv("OPENROUTER_API_KEY", "")
        
        if not self.config.api_key:
            logger.warning("OpenRouter API key not set! Set OPENROUTER_API_KEY env var.")
        
        self.headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": self.config.site_url,
            "X-Title": self.config.app_name,
        }
        
        logger.info("AI Engine initialized (model: {})", self.config.model)

    # ==========================================
    # 1. INTELLIGENT PDF DATA EXTRACTION
    # ==========================================

    def extract_from_pdf_text(self, raw_text: str, document_type: str = "auto") -> Dict[str, Any]:
        """
        Use AI to intelligently extract structured business data from PDF text.
        Much more accurate than regex-based extraction.
        
        Args:
            raw_text: Raw text extracted from PDF
            document_type: Hint about document type (or "auto" for AI to detect)
            
        Returns:
            Structured dictionary of extracted fields
        """
        prompt = f"""You are an expert at extracting structured data from Malaysian business documents.

Analyze the following document text and extract ALL relevant business information.
Document type hint: {document_type}

EXTRACT THE FOLLOWING (return empty string "" if not found):

1. COMPANY INFO:
   - company_name (full registered name)
   - registration_number (SSM/MyCoID - 12 digit number, may have suffix like -A, -T, -V)
   - old_registration_number (old format e.g. 123456-A)
   - company_type (Sdn Bhd, Bhd, Enterprise, Partnership, LLP)
   - incorporation_date (format: DD/MM/YYYY)
   - business_nature (description of main business activity)
   - msic_code (5-digit MSIC code)
   - msic_description
   - status (Active, Dormant, Winding Up, Struck Off)

2. ADDRESS:
   - registered_address (full address)
   - business_address (if different from registered)
   - postcode (5-digit Malaysian postcode)
   - city
   - state (Malaysian state name)
   - country (default: MALAYSIA)

3. FINANCIAL:
   - paid_up_capital (numeric value in RM)
   - authorized_capital

4. CONTACT:
   - phone (with area code)
   - fax
   - email
   - website

5. DIRECTORS (array of objects):
   - name
   - ic_number (format: XXXXXX-XX-XXXX)
   - nationality
   - designation (Director, Managing Director, etc.)
   - address
   - date_of_birth (derived from IC if possible, format: DD/MM/YYYY)
   - gender (derived from IC last digit: odd=Male, even=Female)
   - appointment_date

6. SHAREHOLDERS (array of objects):
   - name
   - ic_number
   - shares_held
   - share_percentage

7. COMPANY SECRETARY:
   - name
   - license_number

IMPORTANT RULES:
- For IC numbers: Format as XXXXXX-XX-XXXX (with dashes)
- For dates: Always use DD/MM/YYYY format
- For capital amounts: Just the number, no RM prefix
- If document is in Malay, still output field names in English
- Be thorough - extract EVERYTHING you can find

---
DOCUMENT TEXT:
{raw_text[:8000]}
---

Return as valid JSON only. No markdown, no explanation."""

        response = self._call_api(prompt)
        
        if response:
            try:
                # Clean response - remove markdown code blocks if present
                cleaned = response.strip()
                if cleaned.startswith("```"):
                    cleaned = re.sub(r'^```(?:json)?\n?', '', cleaned)
                    cleaned = re.sub(r'\n?```$', '', cleaned)
                
                data = json.loads(cleaned)
                logger.info("AI extraction successful. Found {} top-level keys", len(data))
                return data
            except json.JSONDecodeError as e:
                logger.error("AI returned invalid JSON: {}", str(e))
                logger.debug("Raw response: {}", response[:500])
                return {}
        
        return {}

    # ==========================================
    # 2. INTELLIGENT FIELD MATCHING
    # ==========================================

    def match_fields_to_form(
        self, 
        extracted_data: Dict[str, Any], 
        page_html: str
    ) -> List[Dict[str, Any]]:
        """
        Use AI to match extracted data to actual form fields on the page.
        Analyzes the DOM structure to find the best matching elements.
        
        Args:
            extracted_data: Data previously extracted from PDFs
            page_html: HTML content of the current BLESS2 form page
            
        Returns:
            List of field mappings with selectors and values
        """
        # Trim HTML to relevant form elements only
        form_elements = self._extract_form_elements(page_html)
        
        prompt = f"""You are an expert web automation engineer. Your task is to match business data to form fields on a Malaysian government website (BLESS2 - Business Licensing Electronic Support System).

AVAILABLE DATA (extracted from PDF):
{json.dumps(extracted_data, indent=2, ensure_ascii=False)[:4000]}

FORM FIELDS FOUND ON PAGE (HTML elements):
{form_elements[:4000]}

YOUR TASK:
For each form field on the page, determine which piece of extracted data should go into it.
Consider:
- Field labels (in Malay or English)
- Field IDs and names
- Placeholder text
- Field types (text, select, radio, checkbox, date)
- Context from surrounding labels

Return a JSON array of mappings:
[
  {{
    "selector": "CSS selector to find the element (be specific)",
    "field_name": "Human readable field name",
    "field_type": "text|select|radio|checkbox|date",
    "value": "The value to fill in",
    "confidence": 0.95,
    "notes": "Any special handling needed"
  }},
  ...
]

RULES:
- Only include fields where you have data to fill
- CSS selectors should be specific enough to uniquely identify the element
- For <select> fields, provide the option value or text
- For radio buttons, provide the value to select
- For dates, use DD/MM/YYYY format
- Set confidence 0.0-1.0 based on how sure you are about the match
- If a field label is in Malay (e.g. "Nama Syarikat"), match it to the English equivalent

Return valid JSON array only."""

        response = self._call_api(prompt)
        
        if response:
            try:
                cleaned = response.strip()
                if cleaned.startswith("```"):
                    cleaned = re.sub(r'^```(?:json)?\n?', '', cleaned)
                    cleaned = re.sub(r'\n?```$', '', cleaned)
                
                mappings = json.loads(cleaned)
                
                # Filter by confidence threshold
                high_confidence = [m for m in mappings if m.get("confidence", 0) >= 0.7]
                
                logger.info("AI matched {} fields ({} high-confidence)", 
                           len(mappings), len(high_confidence))
                return mappings
                
            except json.JSONDecodeError as e:
                logger.error("AI field matching returned invalid JSON: {}", str(e))
                return []
        
        return []

    # ==========================================
    # 3. PAGE ANALYSIS & NAVIGATION
    # ==========================================

    def analyze_page(self, page_html: str, page_url: str = "") -> Dict[str, Any]:
        """
        Analyze a BLESS2 page to understand its structure,
        identify form sections, required fields, and navigation.
        
        Args:
            page_html: HTML content of the page
            page_url: Current page URL
            
        Returns:
            Page analysis with sections, fields, and navigation info
        """
        # Get a trimmed version of HTML focusing on form structure
        form_elements = self._extract_form_elements(page_html)
        
        prompt = f"""Analyze this Malaysian government website (BLESS2) page and describe its form structure.

Page URL: {page_url}

HTML Form Elements:
{form_elements[:6000]}

Identify and return as JSON:
{{
  "page_title": "The page title or form section name",
  "form_sections": [
    {{
      "section_name": "Section name",
      "fields": [
        {{
          "label": "Field label",
          "field_id": "HTML id attribute",
          "field_name": "HTML name attribute",
          "field_type": "text|select|radio|checkbox|date|textarea|file",
          "required": true/false,
          "options": ["option1", "option2"],  // for select/radio only
          "placeholder": "",
          "css_selector": "specific CSS selector"
        }}
      ]
    }}
  ],
  "navigation": {{
    "next_button": "CSS selector for next/continue button",
    "prev_button": "CSS selector for back button",
    "submit_button": "CSS selector for submit button",
    "save_draft": "CSS selector for save draft button"
  }},
  "has_captcha": false,
  "notes": "Any special observations about the page"
}}

Return valid JSON only."""

        response = self._call_api(prompt)
        
        if response:
            try:
                cleaned = response.strip()
                if cleaned.startswith("```"):
                    cleaned = re.sub(r'^```(?:json)?\n?', '', cleaned)
                    cleaned = re.sub(r'\n?```$', '', cleaned)
                return json.loads(cleaned)
            except json.JSONDecodeError:
                return {}
        
        return {}

    # ==========================================
    # 4. SMART VALUE FORMATTING
    # ==========================================

    def format_value_for_field(
        self, 
        raw_value: str, 
        field_info: Dict[str, Any]
    ) -> str:
        """
        Use AI to format a value appropriately for a specific field.
        Handles things like date format conversion, state name to code, etc.
        
        Args:
            raw_value: The raw extracted value
            field_info: Information about the target field (type, options, etc.)
            
        Returns:
            Properly formatted value
        """
        # For simple cases, don't waste API calls
        if field_info.get("field_type") == "text" and not field_info.get("options"):
            return raw_value
        
        prompt = f"""Format this value for a form field:

Raw value: "{raw_value}"
Field type: {field_info.get('field_type', 'text')}
Field label: {field_info.get('label', '')}
Available options: {json.dumps(field_info.get('options', []))}
Validation: {field_info.get('validation', '')}

Rules:
- If it's a select field, return the closest matching option VALUE (not label)
- If it's a date field, return in DD/MM/YYYY format
- If it's a phone field, format with country code if missing (+60 for Malaysia)
- If it's a state field with codes, return the state code
- Otherwise return the value formatted appropriately for the field

Return ONLY the formatted value, nothing else."""

        response = self._call_api(prompt, max_tokens=100)
        return response.strip() if response else raw_value

    # ==========================================
    # 5. ERROR RECOVERY
    # ==========================================

    def suggest_fix(self, error_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        When automation encounters an error, ask AI for a fix suggestion.
        
        Args:
            error_context: Dictionary with error details, screenshot, page state
            
        Returns:
            Suggestion dictionary with alternative actions
        """
        prompt = f"""You are debugging a web automation script for BLESS2 (Malaysian business licensing website).

Error encountered:
- Error type: {error_context.get('error_type', 'Unknown')}
- Error message: {error_context.get('error_message', '')}
- Element tried: {error_context.get('selector', '')}
- Page URL: {error_context.get('url', '')}
- Page HTML snippet: {error_context.get('html_snippet', '')[:2000]}

Suggest a fix. Return JSON:
{{
  "alternative_selector": "Try this CSS selector instead",
  "action": "click|type|select|wait|scroll|skip",
  "wait_for": "Optional: element to wait for before retrying",
  "value_transform": "Optional: how to transform the value",
  "explanation": "Why this fix should work"
}}

Return valid JSON only."""

        response = self._call_api(prompt, max_tokens=500)
        
        if response:
            try:
                cleaned = response.strip()
                if cleaned.startswith("```"):
                    cleaned = re.sub(r'^```(?:json)?\n?', '', cleaned)
                    cleaned = re.sub(r'\n?```$', '', cleaned)
                return json.loads(cleaned)
            except json.JSONDecodeError:
                return {"action": "skip", "explanation": "Could not parse AI response"}
        
        return {"action": "skip", "explanation": "AI unavailable"}

    # ==========================================
    # PRIVATE METHODS
    # ==========================================

    def _call_api(self, prompt: str, max_tokens: Optional[int] = None) -> Optional[str]:
        """
        Make a call to the OpenRouter API.
        
        Args:
            prompt: The prompt to send
            max_tokens: Override max tokens for this call
            
        Returns:
            Response text or None if failed
        """
        if not self.config.api_key:
            logger.error("OpenRouter API key not configured!")
            return None
        
        payload = {
            "model": self.config.model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a precise data extraction and web automation assistant. Always return valid JSON when requested. Never include markdown formatting or explanations outside the JSON."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "max_tokens": max_tokens or self.config.max_tokens,
            "temperature": self.config.temperature,
        }
        
        try:
            with httpx.Client(timeout=self.config.timeout) as client:
                response = client.post(
                    f"{self.config.base_url}/chat/completions",
                    headers=self.headers,
                    json=payload,
                )
                
                if response.status_code == 200:
                    data = response.json()
                    content = data["choices"][0]["message"]["content"]
                    
                    # Log token usage
                    usage = data.get("usage", {})
                    logger.debug("API call - Tokens: {} prompt + {} completion = {} total",
                               usage.get("prompt_tokens", "?"),
                               usage.get("completion_tokens", "?"),
                               usage.get("total_tokens", "?"))
                    
                    return content
                    
                elif response.status_code == 429:
                    logger.warning("Rate limited. Waiting...")
                    import time
                    time.sleep(5)
                    return self._call_api_with_fallback(prompt, max_tokens)
                    
                else:
                    logger.error("API error {}: {}", response.status_code, response.text[:200])
                    return self._call_api_with_fallback(prompt, max_tokens)
                    
        except httpx.TimeoutException:
            logger.error("API call timed out")
            return self._call_api_with_fallback(prompt, max_tokens)
        except Exception as e:
            logger.error("API call failed: {}", str(e))
            return None

    def _call_api_with_fallback(self, prompt: str, max_tokens: Optional[int] = None) -> Optional[str]:
        """Try fallback model if primary fails."""
        if self.config.fallback_model == self.config.model:
            return None
            
        logger.info("Trying fallback model: {}", self.config.fallback_model)
        
        payload = {
            "model": self.config.fallback_model,
            "messages": [
                {"role": "system", "content": "You are a precise data extraction assistant. Return valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": max_tokens or self.config.max_tokens,
            "temperature": self.config.temperature,
        }
        
        try:
            with httpx.Client(timeout=self.config.timeout) as client:
                response = client.post(
                    f"{self.config.base_url}/chat/completions",
                    headers=self.headers,
                    json=payload,
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return data["choices"][0]["message"]["content"]
                    
        except Exception as e:
            logger.error("Fallback model also failed: {}", str(e))
        
        return None

    def _extract_form_elements(self, html: str) -> str:
        """
        Extract only form-related HTML elements for analysis.
        Reduces token usage by removing irrelevant HTML.
        """
        # Simple extraction of form-related tags
        patterns = [
            r'<form[^>]*>.*?</form>',
            r'<input[^>]*>',
            r'<select[^>]*>.*?</select>',
            r'<textarea[^>]*>.*?</textarea>',
            r'<label[^>]*>.*?</label>',
            r'<button[^>]*>.*?</button>',
            r'<div[^>]*class="[^"]*form[^"]*"[^>]*>.*?</div>',
            r'<fieldset[^>]*>.*?</fieldset>',
        ]
        
        elements = []
        for pattern in patterns:
            matches = re.findall(pattern, html, re.DOTALL | re.IGNORECASE)
            elements.extend(matches)
        
        if elements:
            return "\n".join(elements[:100])  # Limit to 100 elements
        
        # Fallback: return first 6000 chars of HTML
        return html[:6000]

    def is_configured(self) -> bool:
        """Check if AI engine is properly configured."""
        return bool(self.config.api_key)
