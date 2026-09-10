import unittest
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.validation.content_validator import content_validator, CHAR_LIMITS
from app.validation.auto_fix import auto_fix_service
from app.schemas.product import (
    ProductSchema, ProductIdentitySchema, ProductContentSchema, ValueMatchSchema,
    SourceDataSchema, ClassificationDataSchema, QualityScoreSchema, ComponentScoreSchema
)

class TestDescriptionLimits(unittest.TestCase):
    def test_description_boundaries(self):
        """Test exact limit, limit + 1, empty, and valid value for all description channels."""
        for field, max_len in CHAR_LIMITS.items():
            # 1. Empty value -> Valid
            empty_payload = {field: ""}
            res_empty = content_validator.validate_descriptions(empty_payload)
            len_warnings_empty = [r for r in res_empty if r["rule_id"] == f"R-LEN-{field.upper()}"]
            self.assertEqual(len(len_warnings_empty), 0, f"Empty string failed for {field}")

            # 2. Valid value below limit -> Valid
            valid_str = "A" * (max_len - 1)
            if field == "invoice_desc":
                valid_str = valid_str.upper()
            res_valid = content_validator.validate_descriptions({field: valid_str})
            len_warnings_valid = [r for r in res_valid if r["rule_id"] == f"R-LEN-{field.upper()}"]
            self.assertEqual(len(len_warnings_valid), 0, f"Valid value failed for {field}")

            # 3. Exact limit boundary -> Valid
            exact_str = "B" * max_len
            if field == "invoice_desc":
                exact_str = exact_str.upper()
            res_exact = content_validator.validate_descriptions({field: exact_str})
            len_warnings_exact = [r for r in res_exact if r["rule_id"] == f"R-LEN-{field.upper()}"]
            self.assertEqual(len(len_warnings_exact), 0, f"Exact limit failed for {field}")

            # 4. Limit + 1 -> Exceeds boundary (FAIL / WARNING)
            exceed_str = "C" * (max_len + 1)
            res_exceed = content_validator.validate_descriptions({field: exceed_str})
            len_warnings_exceed = [r for r in res_exceed if r["rule_id"] == f"R-LEN-{field.upper()}"]
            self.assertEqual(len(len_warnings_exceed), 1, f"Limit + 1 should fail for {field}")
            self.assertEqual(len_warnings_exceed[0]["status"], "FAIL")
            self.assertEqual(len(len_warnings_exceed[0]["expected_value"]), max_len)

    def test_auto_fix_description_truncation(self):
        """Test AutoFixService truncates long descriptions to their respective CHAR_LIMITS."""
        prod = ProductSchema(
            id="PROD_DESC_TEST",
            session_id="SESS_TEST",
            source_row_id=1,
            source_data=SourceDataSchema(mfg_part_num="MPN-1", part_desc="Desc", e1_brand="Brand", unilog_brand="Brand", dib_brand="Brand", part_manuf="Mfr"),
            identity=ProductIdentitySchema(
                mfg_part_num="MPN-1",
                manufacturer=ValueMatchSchema(raw_value="Mfr", canonical_value="Mfr", confidence=0.9, status="MATCHED"),
                brand=ValueMatchSchema(raw_value="Brand", canonical_value="Brand®", confidence=1.0, status="MATCHED")
            ),
            classification=ClassificationDataSchema(department="Dep", class_name="Cls", fine_class="Fn", classpath="Dep>Cls>Fn", confidence=0.9, reason="Test"),
            content=ProductContentSchema(
                product_name="Sample",
                mobile_desc="M" * 40,      # limit 35
                invoice_desc="inv lowercase" * 3, # limit 30 & lowercase
                short_desc="S" * 60,       # limit 50
                long_desc="L" * 900,       # limit 800
                retail_desc="R" * 200,     # limit 150
                marketing_description="K" * 2500 # limit 2000
            ),
            attributes=[],
            quality=QualityScoreSchema(
                overall_score=85.0,
                status="PASS",
                sub_scores=ComponentScoreSchema(brand_normalization=90.0, classification=90.0, attributes=85.0, descriptions=85.0, digital_assets=90.0, evidence=90.0),
                breakdown_notes=[]
            ),
            validations=[],
            created_at="2026-08-17T00:00:00Z",
            updated_at="2026-08-17T00:00:00Z"
        )

        fixed_prod, fixes_count = auto_fix_service.apply_auto_fixes(prod)
        self.assertGreater(fixes_count, 0)
        self.assertEqual(len(fixed_prod.content.mobile_desc), 35)
        self.assertEqual(len(fixed_prod.content.invoice_desc), 30)
        self.assertEqual(fixed_prod.content.invoice_desc, fixed_prod.content.invoice_desc.upper())
        self.assertEqual(len(fixed_prod.content.short_desc), 50)
        self.assertEqual(len(fixed_prod.content.long_desc), 800)
        self.assertEqual(len(fixed_prod.content.retail_desc), 150)
        self.assertEqual(len(fixed_prod.content.marketing_description), 2000)

if __name__ == "__main__":
    unittest.main()
