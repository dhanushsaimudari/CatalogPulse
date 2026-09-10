import re
from typing import Dict, Any, List, Optional, Tuple
from app.core.config import settings
from app.core.logging import logger
from app.ai.providers.base import AbstractAIProvider
from app.ai.providers.watsonx_provider import WatsonxProvider
from app.ai.providers.gemini_provider import GeminiProvider
from app.ai.schemas import (
    AIClassificationResult,
    AIAttributeResult,
    AIDescriptionResult,
    AIProviderStatusEnum,
    ProviderHealth
)

from threading import Lock

class AIProviderRouter:
    """
    SORTOLOG IQ Central Provider Router
    
    PRIMARY AI PROVIDER:   IBM watsonx.ai (meta-llama/llama-3-3-70b-instruct)
    SECONDARY AI PROVIDER: Google Gemini API (gemini-2.5-flash)
    FALLBACK ENGINE:       Local Deterministic Intelligence Core
    """
    def __init__(self):
        self.primary_provider: AbstractAIProvider = WatsonxProvider()
        self.secondary_provider: AbstractAIProvider = GeminiProvider()
        self._classify_cache: Dict[str, Tuple[AIClassificationResult, str]] = {}
        self._extract_cache: Dict[str, Tuple[List[AIAttributeResult], str]] = {}
        self._desc_cache: Dict[str, Tuple[AIDescriptionResult, str]] = {}
        self._cache_lock = Lock()

    def get_overall_status(self) -> Tuple[AIProviderStatusEnum, str]:
        if self.primary_provider.is_available():
            return AIProviderStatusEnum.AI_AVAILABLE, "IBM watsonx.ai Primary Active (meta-llama/llama-3-3-70b-instruct)."
        elif self.secondary_provider.is_available():
            return AIProviderStatusEnum.AI_FALLBACK_ACTIVE, "IBM watsonx.ai unavailable. Switching to Gemini API Secondary Fallback."
        elif self.primary_provider.is_circuit_open() and "quota" in self.primary_provider.get_health().message.lower():
            return AIProviderStatusEnum.AI_QUOTA_EXHAUSTED, "AI Provider quota/rate limit exhausted. Local deterministic engine active."
        else:
            return AIProviderStatusEnum.AI_DISABLED, "AI Providers Unavailable. Operating in Local Deterministic Engine Mode."

    def get_provider_health(self) -> Dict[str, ProviderHealth]:
        return {
            "watsonx": self.primary_provider.get_health(),
            "gemini": self.secondary_provider.get_health()
        }

    def _deterministic_classify(self, description: str) -> AIClassificationResult:
        desc_upper = description.upper()
        if any(k in desc_upper for k in ["DISHWASHER", "REFRIGERATOR", "RANGE", "MICROWAVE", "OVEN", "FREEZER"]):
            noun = "Built-In Dishwashers" if "DISHWASHER" in desc_upper else "Major Kitchen Appliances"
            return AIClassificationResult(
                department="Appliances & Consumer Electronics",
                class_name="Kitchen Appliances",
                fine_class=noun,
                classpath=f"Appliances & Consumer Electronics>Kitchen Appliances>{noun}",
                confidence=0.96,
                reason="Deterministic industrial keyword match (Kitchen Appliances)"
            )
        elif any(k in desc_upper for k in ["CUT-OFF", "CUTOFF", "GRINDING WHEEL", "GRINDING DISC", "FLAP DISC", "ABRASIVE", "SANDING DISC", "SANDPAPER"]):
            noun = "Metal Cut-Off Discs" if ("CUT-OFF" in desc_upper or "CUTOFF" in desc_upper) else "Abrasive Wheels & Discs"
            return AIClassificationResult(
                department="Abrasives & Cutting Tools",
                class_name="Abrasive Discs",
                fine_class=noun,
                classpath=f"Abrasives & Cutting Tools>Abrasive Discs>{noun}",
                confidence=0.96,
                reason="Deterministic industrial keyword match (Abrasive Discs)"
            )
        elif any(k in desc_upper for k in ["LED", "BULB", "LAMP", "LIGHT BULB", "LUMINAIRE"]):
            noun = "LED Replacement Lamps" if "LED" in desc_upper else "Lamps & Bulbs"
            return AIClassificationResult(
                department="Electrical & Lighting",
                class_name="Lamps & Bulbs",
                fine_class=noun,
                classpath=f"Electrical & Lighting>Lamps & Bulbs>{noun}",
                confidence=0.96,
                reason="Deterministic industrial keyword match (Lighting)"
            )
        elif any(k in desc_upper for k in ["SWITCH", "RECEPTACLE", "DUPLEX", "WALL PLATE", "OUTLET", "WIRE", "CABLE"]):
            return AIClassificationResult(
                department="Electrical & Lighting",
                class_name="Wiring Devices",
                fine_class="Switches & Receptacles",
                classpath="Electrical & Lighting>Wiring Devices>Switches & Receptacles",
                confidence=0.95,
                reason="Deterministic industrial keyword match (Wiring Devices)"
            )
        elif any(k in desc_upper for k in ["DECKING", "DECK BOARD", "COMPOSITE DECK", "FASCIA", "RAILING", "BALUSTER"]):
            noun = "Composite Decking" if "COMPOSITE" in desc_upper or "DECK" in desc_upper else "Decking & Railing"
            return AIClassificationResult(
                department="Building Materials",
                class_name="Decking & Railing",
                fine_class=noun,
                classpath=f"Building Materials>Decking & Railing>{noun}",
                confidence=0.96,
                reason="Deterministic industrial keyword match (Decking & Building Materials)"
            )
        elif any(k in desc_upper for k in ["BOLT", "CAP SCREW", "HEX SCREW", "MACHINE SCREW", "WOOD SCREW", "DRYWALL SCREW", "ANCHOR", "WASHER", "NUT"]):
            noun = "Hex Head Bolts" if "HEX" in desc_upper or "BOLT" in desc_upper else "Standard Fasteners"
            return AIClassificationResult(
                department="Fasteners & Hardware",
                class_name="Bolts & Screws",
                fine_class=noun,
                classpath=f"Fasteners & Hardware>Bolts & Screws>{noun}",
                confidence=0.96,
                reason="Deterministic industrial keyword match (Fasteners)"
            )
        elif any(k in desc_upper for k in ["VALVE", "VLV", "BALL VALVE", "BALL VLV", "CHECK VALVE", "GATE VALVE", "PIPE FITTING", "NIPPLE", "COUPLING", "CPLG", "ELBOW", "TEE"]):
            noun = "Ball Valves" if ("BALL" in desc_upper or "VLV" in desc_upper) else "Plumbing Valves & Fittings"
            return AIClassificationResult(
                department="Plumbing & Pumps",
                class_name="Valves & Fittings",
                fine_class=noun,
                classpath=f"Plumbing & Pumps>Valves & Fittings>{noun}",
                confidence=0.96,
                reason="Deterministic industrial keyword match (Plumbing)"
            )
        elif any(k in desc_upper for k in ["SNIP", "SNIPS", "CRIMPER", "PLIER", "PLIERS", "CUTTER", "SHEAR", "SHEARS", "WRENCH", "SCREWDRIVER", "HAMMER", "TOOL", "SLIM DRIVER", "DRIVER", "BIT", "PHILLIPS BIT"]):
            if "BIT" in desc_upper:
                noun = "Driver Bits & Accessories"
                cls_name = "Power Tool Accessories"
            elif "DRIVER" in desc_upper or "SCREWDRIVER" in desc_upper:
                noun = "Screwdrivers & Nut Drivers"
                cls_name = "Hand Tools"
            else:
                noun = "Crimpers & Cutters" if ("CRIMPER" in desc_upper or "CUTTER" in desc_upper) else "Hand Tools & Snips"
                cls_name = "Hand Tools"
            return AIClassificationResult(
                department="Hand & Power Tools",
                class_name=cls_name,
                fine_class=noun,
                classpath=f"Hand & Power Tools>{cls_name}>{noun}",
                confidence=0.95,
                reason="Deterministic industrial keyword match (Tools)"
            )
        elif any(k in desc_upper for k in ["MOTION LT", "LIGHT", "FIXTURE", "FLOODLIGHT", "LUMINAIRE"]):
            return AIClassificationResult(
                department="Electrical & Lighting",
                class_name="Lighting Fixtures",
                fine_class="Commercial & Residential Fixtures",
                classpath="Electrical & Lighting>Lighting Fixtures>Commercial & Residential Fixtures",
                confidence=0.95,
                reason="Deterministic industrial keyword match (Lighting Fixtures)"
            )
        elif any(k in desc_upper for k in ["FAN", "CEILING FAN", "EXHAUST FAN"]):
            return AIClassificationResult(
                department="Appliances & Ventilation",
                class_name="Fans & Air Movement",
                fine_class="Ceiling & Exhaust Fans",
                classpath="Appliances & Ventilation>Fans & Air Movement>Ceiling & Exhaust Fans",
                confidence=0.95,
                reason="Deterministic industrial keyword match (Fans & Ventilation)"
            )
        elif any(k in desc_upper for k in ["HEATED JACKET", "HEATED HOODIE", "JACKET KIT", "HOODIE KIT", "HEATED VEST"]):
            return AIClassificationResult(
                department="Safety & Workwear",
                class_name="Workwear & Outerwear",
                fine_class="Heated Gear & Apparel",
                classpath="Safety & Workwear>Workwear & Outerwear>Heated Gear & Apparel",
                confidence=0.95,
                reason="Deterministic industrial keyword match (Heated Apparel)"
            )
        elif any(k in desc_upper for k in ["PNEUMATIC", "TUBING", "HOSE", "CYLINDER", "ACTUATOR", "FRL", "AIR FITTING"]):
            noun = "Pneumatic Tubing & Hoses" if ("TUBING" in desc_upper or "HOSE" in desc_upper) else "Pneumatic Cylinders & Actuators"
            return AIClassificationResult(
                department="Industrial & Fluid Power",
                class_name="Pneumatics",
                fine_class=noun,
                classpath=f"Industrial & Fluid Power>Pneumatics>{noun}",
                confidence=0.95,
                reason="Deterministic industrial keyword match (Fluid Power / Pneumatics)"
            )
        elif any(k in desc_upper for k in ["BEARING", "BALL BEARING", "ROLLER BEARING", "PULLEY", "SPROCKET", "V-BELT", "ROLLER CHAIN"]):
            noun = "Ball & Roller Bearings" if "BEARING" in desc_upper else "Power Transmission Components"
            return AIClassificationResult(
                department="Power Transmission",
                class_name="Bearings & Drives",
                fine_class=noun,
                classpath=f"Power Transmission>Bearings & Drives>{noun}",
                confidence=0.95,
                reason="Deterministic industrial keyword match (Power Transmission)"
            )
        elif any(k in desc_upper for k in ["RESISTOR", "CAPACITOR", "TRANSFORMER", "RELAY", "CONTACTOR", "FUSE", "CIRCUIT BREAKER", "TERMINAL BLOCK"]):
            noun = "Passive Components & Controls"
            return AIClassificationResult(
                department="Electrical & Electronics",
                class_name="Industrial Controls",
                fine_class=noun,
                classpath=f"Electrical & Electronics>Industrial Controls>{noun}",
                confidence=0.95,
                reason="Deterministic industrial keyword match (Electronics & Control)"
            )
        elif any(k in desc_upper for k in ["GLOVE", "GLOVES", "RESPIRATOR", "MASK", "EARPLUG", "SAFETY GLASSES", "HARD HAT"]):
            noun = "Hand Protection & PPE" if "GLOVE" in desc_upper else "Personal Protective Equipment"
            return AIClassificationResult(
                department="Safety & Facilities",
                class_name="Personal Protective Equipment",
                fine_class=noun,
                classpath=f"Safety & Facilities>Personal Protective Equipment>{noun}",
                confidence=0.95,
                reason="Deterministic industrial keyword match (Safety & PPE)"
            )
        elif any(k in desc_upper for k in ["THERMOSTAT", "REFRIGERANT", "HEAT PUMP", "CONDENSER", "FURNACE", "AIR FILTER"]):
            return AIClassificationResult(
                department="HVAC & Refrigeration",
                class_name="Climate Control",
                fine_class="HVAC Equipment & Supplies",
                classpath="HVAC & Refrigeration>Climate Control>HVAC Equipment & Supplies",
                confidence=0.95,
                reason="Deterministic industrial keyword match (HVAC)"
            )
        elif any(k in desc_upper for k in ["ADHESIVE", "SEALANT", "GREASE", "LUBRICANT", "SOLVENT", "EPOXY", "TAPE"]):
            return AIClassificationResult(
                department="Chemicals & Lubricants",
                class_name="Adhesives & Sealants",
                fine_class="Industrial Adhesives & Sealants",
                classpath="Chemicals & Lubricants>Adhesives & Sealants>Industrial Adhesives & Sealants",
                confidence=0.95,
                reason="Deterministic industrial keyword match (Chemicals & Adhesives)"
            )
        else:
            # Dynamic Open-World Noun Phrase Extraction:
            # Extract meaningful industrial noun phrase from description instead of hardcoding UNKNOWN
            words = [w for w in re.split(r'[^A-Za-z0-9]+', description) if len(w) > 2 and not w.isdigit()]
            meaningful_words = [w for w in words if w.upper() not in ["THE", "AND", "FOR", "WITH", "SET", "KIT", "OEM", "NEW", "PCS", "PACK"]]
            if meaningful_words:
                inferred_noun = " ".join(meaningful_words[-2:]).title()
                return AIClassificationResult(
                    department="Industrial Supply",
                    class_name="Specialty Products",
                    fine_class=inferred_noun,
                    classpath=f"Industrial Supply>Specialty Products>{inferred_noun}",
                    confidence=0.75,
                    reason=f"Open-world product noun inference from description ('{inferred_noun}')"
                )
            return AIClassificationResult(
                department="General Industrial",
                class_name="Hardware & Supplies",
                fine_class="UNKNOWN",
                classpath="General Industrial>Hardware & Supplies>UNKNOWN",
                confidence=0.40,
                reason="Local deterministic fallback (Uncertain category)"
            )

    def _deterministic_generate_descriptions(
        self, mpn: str, manufacturer: str, brand: str, noun: str
    ) -> AIDescriptionResult:
        clean_brand = brand.replace("®", "").strip().upper()
        return AIDescriptionResult(
            product_name=f"{brand} {noun} {mpn}".strip(),
            mobile_desc=f"{clean_brand} {noun} {mpn}"[:35],
            invoice_desc=f"{clean_brand} {noun} {mpn}".upper()[:30],
            short_desc=f"{brand} {noun} {mpn} Industrial Spec",
            long_desc=f"{brand} {noun} (MPN: {mpn}) manufactured by {manufacturer}. Engineered for high-performance industrial reliability.",
            retail_desc=f"Upgrade your operations with the {brand} {noun} ({mpn}).",
            marketing_description=f"The {brand} {noun} model {mpn} offers superior efficiency, heavy-duty construction, and trusted performance.",
            item_features=[
                f"Heavy-duty industrial grade {noun}",
                f"Manufactured by {manufacturer}",
                f"Standard commercial voltage & footprint",
                f"Original MPN: {mpn}"
            ]
        )

    def classify_product(
        self, mpn: str, description: str, manufacturer: str, brand: str, session: Optional[Any] = None
    ) -> Tuple[AIClassificationResult, str]:
        cache_key = f"{mpn.strip().lower()}|{description.strip().lower()}|{manufacturer.strip().lower()}|{brand.strip().lower()}"
        with self._cache_lock:
            if cache_key in self._classify_cache:
                return self._classify_cache[cache_key]

        res_tuple = self._do_classify_product(mpn, description, manufacturer, brand, session)
        with self._cache_lock:
            self._classify_cache[cache_key] = res_tuple
        return res_tuple

    def _do_classify_product(
        self, mpn: str, description: str, manufacturer: str, brand: str, session: Optional[Any] = None
    ) -> Tuple[AIClassificationResult, str]:
        if session and getattr(session, "ai_budget_exhausted", False):
            logger.info(f"Session AI budget exhausted for {mpn}. Bypassing AI providers.")
            return self._deterministic_classify(description), "local_engine"

        # 1. Try Primary Provider (IBM watsonx.ai)
        if self.primary_provider.is_available():
            try:
                res = self.primary_provider.classify_product(mpn, description, manufacturer, brand)
                if session:
                    session.record_ai_call("IBM watsonx.ai")
                return res, "IBM watsonx.ai"
            except Exception as e:
                logger.warning(f"Primary AI Provider (IBM watsonx.ai) failed: {e}. Initiating failover.")
                if session:
                    session.record_ai_fallback()

        # 2. Try Secondary Provider (Gemini API Fallback)
        if self.secondary_provider.is_available():
            try:
                logger.info(f"Executing Gemini secondary AI fallback for product {mpn}.")
                res = self.secondary_provider.classify_product(mpn, description, manufacturer, brand)
                if session:
                    session.record_ai_call("Gemini")
                return res, "Gemini (Secondary Fallback)"
            except Exception as e:
                logger.warning(f"Secondary AI Provider (Gemini) failed: {e}.")
                if session:
                    session.record_ai_fallback()

        # 3. Local Deterministic Engine Fallback
        if session:
            session.record_local_decision()
        return self._deterministic_classify(description), "local_engine"

    def extract_attributes(
        self, mpn: str, description: str, classpath: str, lov_context: str = "", session: Optional[Any] = None
    ) -> Tuple[List[AIAttributeResult], str]:
        cache_key = f"{mpn.strip().lower()}|{description.strip().lower()}|{classpath.strip().lower()}"
        with self._cache_lock:
            if cache_key in self._extract_cache:
                return self._extract_cache[cache_key]

        res_tuple = self._do_extract_attributes(mpn, description, classpath, lov_context, session)
        with self._cache_lock:
            self._extract_cache[cache_key] = res_tuple
        return res_tuple

    def _do_extract_attributes(
        self, mpn: str, description: str, classpath: str, lov_context: str = "", session: Optional[Any] = None
    ) -> Tuple[List[AIAttributeResult], str]:
        if session and getattr(session, "ai_budget_exhausted", False):
            return [], "local_engine"

        if self.primary_provider.is_available():
            try:
                res = self.primary_provider.extract_attributes(mpn, description, classpath, lov_context)
                if session:
                    session.record_ai_call("IBM watsonx.ai")
                return res, "IBM watsonx.ai"
            except Exception as e:
                logger.warning(f"Primary AI Provider (IBM watsonx.ai) extraction failed: {e}")
                if session:
                    session.record_ai_fallback()

        if self.secondary_provider.is_available():
            try:
                res = self.secondary_provider.extract_attributes(mpn, description, classpath, lov_context)
                if session:
                    session.record_ai_call("Gemini")
                return res, "Gemini (Secondary Fallback)"
            except Exception as e:
                logger.warning(f"Secondary AI Provider (Gemini) extraction failed: {e}")
                if session:
                    session.record_ai_fallback()

        if session:
            session.record_local_decision()
        return [], "local_engine"

    def generate_descriptions(
        self, mpn: str, manufacturer: str, brand: str, noun: str, attributes: str, session: Optional[Any] = None
    ) -> Tuple[AIDescriptionResult, str]:
        cache_key = f"{mpn.strip().lower()}|{manufacturer.strip().lower()}|{brand.strip().lower()}|{noun.strip().lower()}"
        with self._cache_lock:
            if cache_key in self._desc_cache:
                return self._desc_cache[cache_key]

        res_tuple = self._do_generate_descriptions(mpn, manufacturer, brand, noun, attributes, session)
        with self._cache_lock:
            self._desc_cache[cache_key] = res_tuple
        return res_tuple

    def _do_generate_descriptions(
        self, mpn: str, manufacturer: str, brand: str, noun: str, attributes: str, session: Optional[Any] = None
    ) -> Tuple[AIDescriptionResult, str]:
        if session and getattr(session, "ai_budget_exhausted", False):
            return self._deterministic_generate_descriptions(mpn, manufacturer, brand, noun), "local_engine"

        if self.primary_provider.is_available():
            try:
                res = self.primary_provider.generate_descriptions(mpn, manufacturer, brand, noun, attributes)
                if session:
                    session.record_ai_call("IBM watsonx.ai")
                return res, "IBM watsonx.ai"
            except Exception as e:
                logger.warning(f"Primary AI Provider (IBM watsonx.ai) description generation failed: {e}")
                if session:
                    session.record_ai_fallback()

        if self.secondary_provider.is_available():
            try:
                res = self.secondary_provider.generate_descriptions(mpn, manufacturer, brand, noun, attributes)
                if session:
                    session.record_ai_call("Gemini")
                return res, "Gemini (Secondary Fallback)"
            except Exception as e:
                logger.warning(f"Secondary AI Provider (Gemini) description generation failed: {e}")
                if session:
                    session.record_ai_fallback()

        if session:
            session.record_local_decision()
        return self._deterministic_generate_descriptions(mpn, manufacturer, brand, noun), "local_engine"

ai_provider_router = AIProviderRouter()
