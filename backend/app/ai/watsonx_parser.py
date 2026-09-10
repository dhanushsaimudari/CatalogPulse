import json
import re
from typing import Any, Dict, List, Union

class WatsonxParsingError(ValueError):
    """Raised when IBM watsonx.ai (Llama 3.3 70B) output cannot be extracted or parsed."""
    pass

def parse_watsonx_json(raw_text: str) -> Union[Dict[str, Any], List[Any]]:
    """
    Dedicated parser for IBM watsonx.ai (meta-llama/llama-3-3-70b-instruct) output.
    Performs bounded extraction and safe repair without invoking any other provider logic.
    """
    if not raw_text or not raw_text.strip():
        raise WatsonxParsingError("IBM watsonx.ai returned empty response text.")

    clean_text = raw_text.strip()

    # Strip markdown code fencing (```json ... ``` or ``` ...)
    if "```" in clean_text:
        # Match inside ```json ... ``` or ``` ... ```
        match = re.search(r"```(?:json)?\s*(.*?)\s*```", clean_text, re.DOTALL)
        if match:
            clean_text = match.group(1).strip()
        else:
            clean_text = re.sub(r"^```(?:json)?\s*", "", clean_text)
            clean_text = re.sub(r"\s*```$", "", clean_text)

    # 1. Direct JSON parse attempt
    try:
        return json.loads(clean_text)
    except json.JSONDecodeError:
        pass

    # 2. Bounded regex search for outer JSON object or array
    match = re.search(r"(\{.*\}|\[.*\])", clean_text, re.DOTALL)
    if match:
        candidate = match.group(1).strip()
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

        # 3. Bounded safe repair: fix trailing commas before closing braces/brackets
        repaired = re.sub(r",\s*(\}|\])", r"\1", candidate)
        try:
            return json.loads(repaired)
        except json.JSONDecodeError:
            pass

        # 4. Safe single-to-double quote repair if no inner unescaped double quotes
        if "'" in repaired and '"' not in repaired:
            try:
                return json.loads(repaired.replace("'", '"'))
            except json.JSONDecodeError:
                pass

    snippet = raw_text[:250].replace("\n", " ")
    raise WatsonxParsingError(f"Failed to extract valid JSON from IBM watsonx.ai response: {snippet}")
