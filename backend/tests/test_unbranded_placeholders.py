import unittest
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.local_cleaner import local_cleaner
from app.validation.auto_fix import auto_fix_service
from app.validation.engine import validation_engine
from app.schemas.product import (
    ProductSchema, SourceDataSchema, ProductIdentitySchema, ValueMatchSchema,
    ClassificationDataSchema, ProductContentSchema, QualityScoreSchema, ComponentScoreSchema
)
from app.session.session_models import ProcessingSession
from app.services.processing_service import processing_service

class TestUnbrandedAndReviewState(unittest.TestCase):
    def test_01_unbranded_placeholders_preserved_without_trademark(self):
        placeholders = [
            "-- Unbranded --",
            "-- No Unilog Brand --",
            "-- No DIB Brand --"
        ]
        for p in placeholders:
            canonical, status, conf = local_cleaner.resolve_brand(p)
            self.assertEqual(canonical, p, f"Expected {p} to be preserved exactly")
            self.assertFalse(canonical.endswith("®"), f"{p} must NOT have ® appended")

    def test_02_autofix_does_not_add_trademark_to_unbranded(self):
        dummy_quality = QualityScoreSchema(
            overall_score=85.0, status="PASS",
            sub_scores=ComponentScoreSchema(brand_normalization=90.0, classification=90.0, attributes=85.0, descriptions=85.0, digital_assets=90.0, evidence=90.0),
            breakdown_notes=[]
        )
        for p_str in ["-- Unbranded --", "-- No Unilog Brand --", "-- No DIB Brand --"]:
            prod = ProductSchema(
                id="prod-unbranded",
                source_row_id=1,
                source_data=SourceDataSchema(mfg_part_num="MPN-1", part_desc="Desc", e1_brand="", unilog_brand="", dib_brand="", part_manuf="Mfr"),
                identity=ProductIdentitySchema(
                    mfg_part_num="MPN-1",
                    manufacturer=ValueMatchSchema(raw_value="Mfr", canonical_value="Mfr", confidence=0.9, status="MATCHED"),
                    brand=ValueMatchSchema(raw_value=p_str, canonical_value=p_str, confidence=1.0, status="UNBRANDED")
                ),
                classification=ClassificationDataSchema(department="Dep", class_name="Cls", fine_class="Fn", classpath="Dep>Cls>Fn", confidence=0.9, reason="Test"),
                content=ProductContentSchema(product_name="Name", mobile_desc="Mob", invoice_desc="INV", short_desc="Short", long_desc="Long", retail_desc="Ret", marketing_description="Mktg"),
                attributes=[],
                quality=dummy_quality,
                validations=[],
                created_at="2026-08-17T00:00:00Z",
                updated_at="2026-08-17T00:00:00Z"
            )

            # Validation must pass without complaining about missing ®
            validations = validation_engine.validate_product(prod)
            brand_val = [v for v in validations if v.target_field == "brand"]
            self.assertTrue(len(brand_val) > 0)
            self.assertEqual(brand_val[0].status, "PASS", f"Validation for {p_str} should PASS without ®")

            # Autofix must not mutate the placeholder
            fixed_prod, fixes = auto_fix_service.apply_auto_fixes(prod)
            self.assertEqual(fixed_prod.identity.brand.canonical_value, p_str)

    def test_03_never_allow_requires_review_with_zero_reviews(self):
        session = ProcessingSession(session_id="test-review-queue-check")
        candidate = {
            "source_row_id": 1,
            "mpn": "TEST-MPN-ROUTING",
            "description": "Obscure industrial item with low classification",
            "part_manuf": "Unknown MFR",
            "unilog_brand": "-- No Unilog Brand --"
        }
        prod = processing_service.process_candidate(session, candidate)
        if prod.requires_review:
            reviews = session.list_reviews(status="PENDING")
            prod_reviews = [r for r in reviews if r.product_id == prod.id]
            self.assertGreater(len(prod_reviews), 0, "requires_review=True must NEVER have 0 reviews in queue")

if __name__ == "__main__":
    unittest.main()
