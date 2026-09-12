DESCRIPTION_PROMPT_TEMPLATE = """
Synthesize multi-channel commerce descriptions for this product candidate based STRICTLY and ONLY on the supplied source data.

GROUNDING RULES:
1. SOURCE FACTS ONLY: Use only information explicitly present in the supplied product data and validated attributes.
2. NO FABRICATED CLAIMS: Do NOT infer durability, quality, performance, or benefits.
   Strictly NEVER generate unsupported claims such as:
   - "high-performance"
   - "industrial-grade"
   - "premium quality"
   - "engineered for reliability"
   - "engineered for high-performance"
   - "durable" or "long-lasting"
   - "best-in-class"
   - "professional-grade"
   - "superior performance" or "superior efficiency"
   - "heavy-duty"
3. MISSING IS VALID: If information (e.g. material, dimensions, specs) is not supplied, omit it completely. A concise, factual description is preferred over a fabricated one.

PRODUCT DATA:
MPN: {mpn}
Manufacturer: {manufacturer}
Brand: {brand}
Noun: {noun}
Attributes: {attributes}

OUTPUT REQUIREMENT:
Return valid JSON with keys:
"product_name", "mobile_desc", "invoice_desc", "short_desc", "long_desc", "retail_desc", "marketing_description", "item_features"
"""
