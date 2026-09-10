import time
import requests
from typing import Optional, Dict, Any, List
from app.core.config import settings
from app.core.logging import logger
from app.ai.providers.base import AbstractAIProvider
from app.ai.schemas import (
    AIClassificationResult,
    AIAttributeResult,
    AIDescriptionResult,
    ProviderHealth
)
from app.ai.watsonx_parser import parse_watsonx_json, WatsonxParsingError
from app.ai.prompts.classification import CLASSIFICATION_PROMPT_TEMPLATE
from app.ai.prompts.extraction import EXTRACTION_PROMPT_TEMPLATE
from app.ai.prompts.description import DESCRIPTION_PROMPT_TEMPLATE

class WatsonxProvider(AbstractAIProvider):
    def __init__(self):
        self.api_key = (settings.WATSONX_API_KEY or "").strip()
        self.project_id = (settings.WATSONX_PROJECT_ID or "").strip()
        self.url = settings.WATSONX_URL.rstrip("/")
        self.model_id = settings.WATSONX_MODEL_ID
        
        self.iam_token: Optional[str] = None
        self.token_expiry: float = 0.0
        self.circuit_open = False
        self.circuit_reason = ""

        if not self.api_key or self.api_key.startswith("your_") or not self.project_id or self.project_id.startswith("your_"):
            self.circuit_open = True
            self.circuit_reason = "IBM watsonx credentials (WATSONX_API_KEY/WATSONX_PROJECT_ID) not configured."
        else:
            logger.info(f"WatsonxProvider configured. Model: {self.model_id}, Project ID: {self.project_id[:6]}...")

    @property
    def provider_name(self) -> str:
        return "IBM watsonx.ai"

    def is_available(self) -> bool:
        return not self.circuit_open

    def is_circuit_open(self) -> bool:
        return self.circuit_open

    def get_health(self) -> ProviderHealth:
        if self.is_available():
            return ProviderHealth(
                provider_name=self.provider_name,
                status="AVAILABLE",
                circuit_open=False,
                message=f"IBM watsonx.ai operational (model={self.model_id})"
            )
        else:
            status_code = "QUOTA_EXHAUSTED" if "429" in self.circuit_reason or "rate limit" in self.circuit_reason.lower() else "UNAVAILABLE"
            return ProviderHealth(
                provider_name=self.provider_name,
                status=status_code,
                circuit_open=True,
                message=self.circuit_reason or "watsonx.ai circuit is open."
            )

    def _get_iam_token(self) -> str:
        now = time.time()
        if self.iam_token and now < self.token_expiry - 60:
            return self.iam_token

        iam_url = "https://iam.cloud.ibm.com/identity/token"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = {
            "grant_type": "urn:ibm:params:oauth:grant-type:apikey",
            "apikey": self.api_key
        }
        
        try:
            resp = requests.post(iam_url, headers=headers, data=data, timeout=10)
        except Exception as e:
            self.circuit_open = True
            self.circuit_reason = f"IBM IAM connection failure: {e}"
            raise RuntimeError(self.circuit_reason)

        if resp.status_code in [401, 403, 404]:
            self.circuit_open = True
            self.circuit_reason = f"IBM IAM Auth failure ({resp.status_code}): {resp.text}"
            raise RuntimeError(self.circuit_reason)
        elif resp.status_code != 200:
            self.circuit_open = True
            self.circuit_reason = f"IBM IAM Auth error ({resp.status_code}): {resp.text}"
            raise RuntimeError(self.circuit_reason)
            
        token_data = resp.json()
        self.iam_token = token_data.get("access_token")
        expires_in = token_data.get("expires_in", 3600)
        self.token_expiry = now + expires_in
        return self.iam_token

    def _generate(self, prompt: str, max_retries: int = 2) -> str:
        if not self.is_available():
            raise RuntimeError(f"WatsonxProvider unavailable: {self.circuit_reason}")

        last_error = None
        for attempt in range(max_retries + 1):
            try:
                token = self._get_iam_token()
                endpoint = f"{self.url}/ml/v1/text/generation?version=2023-05-29"
                headers = {
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                }
                payload = {
                    "input": prompt,
                    "parameters": {
                        "decoding_method": "greedy",
                        "max_new_tokens": 512,
                        "min_new_tokens": 1
                    },
                    "model_id": self.model_id,
                    "project_id": self.project_id
                }

                resp = requests.post(endpoint, headers=headers, json=payload, timeout=20)

                # 401, 403, 404: Fail Fast
                if resp.status_code in [401, 403, 404]:
                    self.circuit_open = True
                    self.circuit_reason = f"watsonx API fatal status {resp.status_code}: {resp.text}"
                    raise RuntimeError(self.circuit_reason)

                # 429: Bounded retry then trip circuit breaker
                if resp.status_code == 429:
                    err_text = resp.text
                    if attempt < max_retries:
                        time.sleep(0.8 * (attempt + 1))
                        continue
                    else:
                        self.circuit_open = True
                        self.circuit_reason = f"watsonx API circuit open after rate limit retries (429): {err_text}"
                        raise RuntimeError(self.circuit_reason)

                # 5xx: Bounded exponential backoff
                if resp.status_code >= 500:
                    err_text = resp.text
                    if attempt < max_retries:
                        time.sleep(1.0 * (2 ** attempt))
                        continue
                    else:
                        raise RuntimeError(f"watsonx server error ({resp.status_code}): {err_text}")

                if resp.status_code != 200:
                    raise RuntimeError(f"watsonx unexpected status ({resp.status_code}): {resp.text}")

                result_json = resp.json()
                results = result_json.get("results", [])
                if results and "generated_text" in results[0]:
                    return results[0]["generated_text"]
                return ""
            except Exception as e:
                last_error = e
                err_str = str(e)
                if any(k in err_str for k in ["401", "403", "404"]):
                    self.circuit_open = True
                    self.circuit_reason = f"Circuit open due to auth/endpoint error: {e}"
                    raise e

                if attempt >= max_retries:
                    logger.warning(f"WatsonxProvider execution error: {e}")
                    if any(k in err_str for k in ["429", "ConnectionError", "getaddrinfo"]):
                        self.circuit_open = True
                        self.circuit_reason = f"Circuit open due to network/rate error: {e}"
                    raise e
                time.sleep(0.5)
        raise last_error

    def classify_product(
        self, mpn: str, description: str, manufacturer: str, brand: str
    ) -> AIClassificationResult:
        prompt = CLASSIFICATION_PROMPT_TEMPLATE.format(
            mpn=mpn, description=description, manufacturer=manufacturer, brand=brand
        )
        raw_text = self._generate(prompt)
        try:
            parsed = parse_watsonx_json(raw_text)
            if not isinstance(parsed, dict):
                parsed = {}
        except WatsonxParsingError as e:
            logger.warning(f"watsonx classification parse failed: {e}. Falling back safely.")
            return AIClassificationResult(
                department="General Industrial",
                class_name="Unclassified",
                fine_class="UNKNOWN",
                classpath="General Industrial>Unclassified>UNKNOWN",
                confidence=0.50,
                reason="watsonx output non-JSON (safe review fallback)"
            )

        return AIClassificationResult(
            department=parsed.get("department", "General Industrial"),
            class_name=parsed.get("class_name", "Unclassified"),
            fine_class=parsed.get("fine_class", "UNKNOWN"),
            classpath=parsed.get("classpath", "General Industrial>Unclassified>UNKNOWN"),
            confidence=float(parsed.get("confidence", 0.85)),
            reason=parsed.get("reason", "watsonx.ai taxonomy classification")
        )

    def extract_attributes(
        self, mpn: str, description: str, classpath: str, lov_context: str = ""
    ) -> List[AIAttributeResult]:
        prompt = EXTRACTION_PROMPT_TEMPLATE.format(
            mpn=mpn, description=description, classpath=classpath, lov_context=lov_context
        )
        raw_text = self._generate(prompt)
        try:
            parsed = parse_watsonx_json(raw_text)
        except WatsonxParsingError as e:
            logger.warning(f"watsonx attribute parse failed: {e}")
            return []

        results = []
        if isinstance(parsed, list):
            for seq, item in enumerate(parsed, 1):
                if isinstance(item, dict):
                    results.append(
                        AIAttributeResult(
                            sequence=seq,
                            label=str(item.get("label", item.get("attribute", f"PARAM_{seq}"))).upper(),
                            raw_value=str(item.get("value", item.get("raw_value", ""))),
                            normalized_value=str(item.get("normalized_value", item.get("value", ""))),
                            uom=str(item.get("uom", "")),
                            confidence=0.88
                        )
                    )
        return results

    def generate_descriptions(
        self, mpn: str, manufacturer: str, brand: str, noun: str, attributes: str
    ) -> AIDescriptionResult:
        prompt = DESCRIPTION_PROMPT_TEMPLATE.format(
            mpn=mpn, manufacturer=manufacturer, brand=brand, noun=noun, attributes=attributes
        )
        raw_text = self._generate(prompt)
        try:
            parsed = parse_watsonx_json(raw_text)
            if not isinstance(parsed, dict):
                parsed = {}
        except WatsonxParsingError as e:
            logger.warning(f"watsonx description parse failed: {e}")
            parsed = {}

        return AIDescriptionResult(
            product_name=parsed.get("product_name", f"{brand} {noun} {mpn}"),
            mobile_desc=parsed.get("mobile_desc", f"{brand} {noun} {mpn}"[:35]),
            invoice_desc=parsed.get("invoice_desc", f"{brand} {noun} {mpn}".upper()[:30]),
            short_desc=parsed.get("short_desc", f"{brand} {noun} {mpn} Industrial Spec"),
            long_desc=parsed.get("long_desc", f"{brand} {noun} (MPN: {mpn}) by {manufacturer}"),
            retail_desc=parsed.get("retail_desc", f"High grade {brand} {noun}"),
            marketing_description=parsed.get("marketing_description", f"Commercial {brand} {noun}"),
            item_features=parsed.get("item_features", [f"Heavy-duty {noun}", f"Mfr: {manufacturer}"])
        )
