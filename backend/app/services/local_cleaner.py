import re
from typing import Dict, Any, Tuple, Optional, List

MANUFACTURER_MAPPING = {
    "APPLIANCE DEALERS COOPERATIVE (APPDE)": "Rheem Manufacturing",
    "APPLIANCE DEALERS COOPERATIVE": "Rheem Manufacturing",
    "WHIRLPOOL CORP (2890)": "Whirlpool Corporation",
    "FREUD INC (2435)": "Freud Inc.",
    "MALCO PRODUCTS INC (1120)": "Malco Products SBC",
    "MALCO PROD (2370)": "Malco Products SBC",
    "MILWAUKEE ACCESSORY (4031)": "Milwaukee Tool",
    "PHILLIPS LIGHTING (5831)": "Philips Lighting",
    "PHILIPS LIGHTING (5831)": "Philips Lighting",
    "KICHLER LIGHTING (KICLI)": "Kichler Lighting LLC",
    "PARKSITE (6151)": "The AZEK Company / Parksite",
    "BLACK & DECKER/DEWLT (2585)": "Stanley Black & Decker",
    "U S LUMBER (3073)": "U.S. LUMBER Group",
    "BOISE CASCADE BUILDING MATERIALS (BOICA)": "Boise Cascade",
    "SATCO PROD INC (5573)": "Satco Products Inc.",
    "MAKITA USA INC (5142)": "Makita USA Inc.",
    "SOUTHWIRE/G TURNER (6603)": "Southwire Company LLC",
    "LEVITON MFG CO (4927)": "Leviton Manufacturing Co.",
    "FESTOOL USA (FESTO)": "Festool USA",
    "MIRKA ABRASIVES INC (MIRUS)": "Mirka USA Inc.",
    "WATTS REGULATOR CO (WATTS)": "Watts Water Technologies",
    "NIBCO INC (NIBCO)": "NIBCO Inc.",
    "HUNTER FAN CO (4381)": "Hunter Fan Company",
    "COOPER LIGHTING (7638)": "Cooper Lighting Solutions",
    "WERA TOOLS NA INC (WERTO)": "Wera Tools",
    "JAM INDUSTRIAL SUPPLY LLC (JAMIN)": "3M Company / Jam Industrial Supply",
    "UNITED WINDOW & DOOR MANUFACTURING (UNIWI)": "United Window & Door",
    "FENTON BROS ELECTRIC INC (FENBR)": "Fenton Bros Electric",
}

BRAND_MAPPING = {
    "FRIGIDAIRE": "Frigidaire®",
    "WHIRLPOOL": "Whirlpool®",
    "DIABLO": "Diablo®",
    "FREUD": "Freud®",
    "MALCO": "Malco®",
    "MILWAUKEE": "Milwaukee®",
    "MILW": "Milwaukee®",
    "DEWALT": "DEWALT®",
    "BLACK & DECKER": "Black & Decker®",
    "PHILIPS": "Philips®",
    "PHILLIPS": "Philips®",
    "SATCO": "Satco®",
    "NUVO": "Nuvo®",
    "KICHLER": "Kichler®",
    "MAKITA": "Makita®",
    "SOUTHWIRE": "Southwire®",
    "GREENLEE": "Greenlee®",
    "LEVITON": "Leviton®",
    "FESTOOL": "Festool®",
    "TREX": "Trex®",
    "TIMBERTECH": "TimberTech®",
    "AZEK": "AZEK®",
    "MIRKA": "Mirka®",
    "3M": "3M®",
    "WATTS": "Watts®",
    "NIBCO": "NIBCO®",
    "HUNTER": "Hunter®",
    "GE": "GE®",
    "WERA": "Wera®",
    "UNITED WINDOW & DOOR": "United Window & Door®",
    "LP SMARTSIDE": "LP SmartSide®",
    "JAMESHARDIE": "James Hardie®",
    "PROVIA": "ProVia®",
    "HAGER": "Hager®",
    "DSI WESTBURY": "DSI Westbury®",
}

BRAND_SEARCH_PATTERNS = [
    (r"\b(?:MILW|MILWAUKEE)\b", "Milwaukee®", "Milwaukee Tool"),
    (r"\b(?:DIABLO|DBD[0-9A-Z]*|D[0-9]{4,}[A-Z]*)\b", "Diablo®", "Freud Inc."),
    (r"\bFREUD\b", "Freud®", "Freud Inc."),
    (r"\b(?:DEWALT|DEWLT)\b", "DEWALT®", "Stanley Black & Decker"),
    (r"\b(?:PHILIPS|PHILLIPS)\b", "Philips®", "Philips Lighting"),
    (r"\bMAKITA\b", "Makita®", "Makita USA Inc."),
    (r"\bSATCO\b", "Satco®", "Satco Products Inc."),
    (r"\bKICHLER\b", "Kichler®", "Kichler Lighting LLC"),
    (r"\bLEVITON\b", "Leviton®", "Leviton Manufacturing Co."),
    (r"\bSOUTHWIRE\b", "Southwire®", "Southwire Company LLC"),
    (r"\bFESTOOL\b", "Festool®", "Festool USA"),
    (r"\b(?:MIRKA|ABRANET|HIOLIT)\b", "Mirka®", "Mirka USA Inc."),
    (r"\b3M\b", "3M®", "3M Company"),
    (r"\bWATTS\b", "Watts®", "Watts Water Technologies"),
    (r"\bNIBCO\b", "NIBCO®", "NIBCO Inc."),
    (r"\bHUNTER\b", "Hunter®", "Hunter Fan Company"),
    (r"\b(?:GE|GENERAL ELECTRIC)\b", "GE®", "GE Appliances"),
    (r"\bFRIGIDAIRE\b", "Frigidaire®", "Electrolux / Frigidaire"),
    (r"\bWHIRLPOOL\b", "Whirlpool®", "Whirlpool Corporation"),
    (r"\bWERA\b", "Wera®", "Wera Tools"),
    (r"\bMALCO\b", "Malco®", "Malco Products SBC"),
    (r"\bTREX\b", "Trex®", "Trex Company Inc."),
    (r"\b(?:TIMBERTECH|AZEK)\b", "TimberTech®", "The AZEK Company"),
]

FRACTION_MAP = {
    "1/16": "0.0625",
    "1/8": "0.125",
    "3/16": "0.1875",
    "1/4": "0.25",
    "5/16": "0.3125",
    "3/8": "0.375",
    "7/16": "0.4375",
    "1/2": "0.5",
    "9/16": "0.5625",
    "5/8": "0.625",
    "11/16": "0.6875",
    "3/4": "0.75",
    "13/16": "0.8125",
    "7/8": "0.875",
    "15/16": "0.9375",
}

UOM_NORMALIZATION_MAP = {
    "INCH": "IN",
    "INCHES": "IN",
    "IN.": "IN",
    "IN": "IN",
    '"': "IN",
    "FOOT": "FT",
    "FEET": "FT",
    "FT.": "FT",
    "FT": "FT",
    "'": "FT",
    "MILLIMETER": "MM",
    "MILLIMETERS": "MM",
    "MM.": "MM",
    "MM": "MM",
    "VOLTS": "V",
    "VOLT": "V",
    "VDC": "V",
    "VAC": "V",
    "V": "V",
    "AMPS": "A",
    "AMP": "A",
    "A": "A",
    "WATTS": "W",
    "WATT": "W",
    "W": "W",
    "HERTZ": "HZ",
    "HZ": "HZ",
    "HORSEPOWER": "HP",
    "HP": "HP",
    "POUNDS": "LBS",
    "POUND": "LBS",
    "LBS": "LBS",
    "LB": "LBS",
    "PSI": "PSI",
    "RPM": "RPM",
    "KELVIN": "K",
    "K": "K",
    "LUMENS": "LM",
    "LM": "LM",
}

class LocalCleanerService:
    def clean_text(self, raw: str) -> str:
        if not raw:
            return ""
        # Remove redundant whitespace & control characters
        cleaned = re.sub(r'\s+', ' ', str(raw)).strip()
        return cleaned

    def clean_vendor_code(self, raw_mfr: str) -> str:
        """Strip internal vendor codes like (4031) or (5831) from manufacturer name."""
        cleaned = self.clean_text(raw_mfr)
        cleaned = re.sub(r'\s*\([A-Za-z0-9_-]+\)\s*$', '', cleaned).strip()
        return cleaned

    def resolve_manufacturer(
        self,
        raw_mfr: str,
        desc: str = "",
        mpn: str = ""
    ) -> Tuple[str, str, float]:
        """
        Returns (canonical_mfr, status, confidence)
        Master list is a reference vocabulary, not an allowlist.
        Unknown but source-supported manufacturers are preserved as UNVERIFIED (never GENERIC/UNKNOWN).
        If raw_mfr is missing or vendor-code only, inspects desc and mpn for manufacturer evidence.
        """
        cleaned = self.clean_text(raw_mfr)
        stripped = self.clean_vendor_code(cleaned) if cleaned else ""

        # 1. Check known master vocabulary directly
        if cleaned:
            upper = cleaned.upper()
            if upper in MANUFACTURER_MAPPING:
                return MANUFACTURER_MAPPING[upper], "NORMALIZED", 0.98

            stripped_upper = stripped.upper()
            if stripped_upper in MANUFACTURER_MAPPING:
                return MANUFACTURER_MAPPING[stripped_upper], "NORMALIZED", 0.98

        # 2. If raw_mfr provided valid text not in master dictionary, PRESERVE IT (Open-World rule)
        # Never convert source-supported manufacturer to GENERIC or UNKNOWN
        if stripped and stripped.upper() not in ["UNKNOWN", "N/A", "NONE", "NULL", "--", "-", "GENERIC"]:
            # Preserve original casing or clean title case
            return stripped, "UNVERIFIED", 0.88

        # 3. Contextual discovery: if raw_mfr is missing/blank/vendor-code, search desc and mpn
        search_corpus = f"{desc} {mpn} {cleaned}".upper()
        for pattern, _, mfr_name in BRAND_SEARCH_PATTERNS:
            if mfr_name and re.search(pattern, search_corpus, re.IGNORECASE):
                return mfr_name, "NORMALIZED", 0.92

        # 4. Truly unknown manufacturer (no evidence anywhere)
        return "", "UNKNOWN", 0.0

    def resolve_brand(
        self,
        raw_brand: str,
        desc: str = "",
        mfr: str = "",
        mpn: str = ""
    ) -> Tuple[str, str, float]:
        """
        Returns (canonical_brand, status, confidence)
        Preserves unbranded placeholders: '-- Unbranded --', '-- No Unilog Brand --', '-- No DIB Brand --'
        without adding registered trademark symbols ®.
        Resolves brand from description, manufacturer, or MPN when raw_brand is missing or placeholder.
        Never outputs GENERIC®.
        """
        cleaned = self.clean_text(raw_brand)
        unbranded_placeholders = {
            "-- UNBRANDED --",
            "-- NO UNILOG BRAND --",
            "-- NO DIB BRAND --",
            "COMMODITY - UNBRANDED",
            "UNKNOWN",
            "N/A",
            "NONE",
            "NULL",
            "--",
            "-"
        }

        # If raw_brand has a direct valid value
        if cleaned and cleaned.upper() not in unbranded_placeholders and cleaned.upper() != "GENERIC":
            upper = cleaned.upper()
            if upper in BRAND_MAPPING:
                return BRAND_MAPPING[upper], "NORMALIZED", 0.98
            # Clean uppercase brand name
            clean_name = cleaned.rstrip("®").strip()
            return f"{clean_name}®", "NORMALIZED", 0.92

        # Investigate description, manufacturer, and MPN for brand evidence
        search_corpus = f"{desc} {mfr} {mpn}".upper()
        for pattern, brand_name, _ in BRAND_SEARCH_PATTERNS:
            if re.search(pattern, search_corpus, re.IGNORECASE):
                return brand_name, "NORMALIZED", 0.95

        # If raw input specifically was marked unbranded or is genuinely unbranded commodity
        if cleaned.upper() in ["-- UNBRANDED --", "-- NO UNILOG BRAND --", "-- NO DIB BRAND --", "COMMODITY - UNBRANDED"]:
            return cleaned, "UNBRANDED", 1.00

        if not cleaned or cleaned.upper() in ["UNKNOWN", "N/A", "NONE", "NULL", "--", "-", "GENERIC"]:
            return "-- Unbranded --", "UNBRANDED", 1.00

        return "-- Unbranded --", "UNBRANDED", 0.80

    def normalize_uom(self, uom_raw: str) -> str:
        cleaned = self.clean_text(uom_raw).upper()
        return UOM_NORMALIZATION_MAP.get(cleaned, cleaned)

    def normalize_fractions(self, text: str) -> str:
        res = text
        for frac, dec in FRACTION_MAP.items():
            res = re.sub(r'\b' + re.escape(frac) + r'\b', dec, res)
        return res

local_cleaner = LocalCleanerService()
