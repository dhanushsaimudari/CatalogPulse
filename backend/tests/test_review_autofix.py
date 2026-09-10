import unittest
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.schemas.product import (
    ProductSchema, SourceDataSchema, ProductIdentitySchema, ValueMatchSchema,
    ClassificationDataSchema, ProductContentSchema, ProductAttributeSchema,
    QualityScoreSchema, ComponentScoreSchema
)
from app.schemas.review import ReviewItemSchema
from app.session.session_models import ProcessingSession
from app.services.review_service import review_service

class TestReviewAutofix(unittest.TestCase):
    def setUp(self):
        self.session = ProcessingSession(session_id="test-review-sess")
        dummy_quality = QualityScoreSchema(
            overall_score=70.0,
            status="NEEDS_REVIEW",
            sub_scores=ComponentScoreSchema(
                brand_normalization=70.0,
                classification=70.0,
                attributes=70.0,
                descriptions=70.0,
                digital_assets=70.0,
                evidence=70.0
            ),
            breakdown_notes=[]
        )

        self.product = ProductSchema(
            id="prod-review-1",
            source_row_id=1,
            source_data=SourceDataSchema(
                mfg_part_num="MPN-100",
                part_desc="Test Part",
                e1_brand="",
                unilog_brand="",
                dib_brand="",
                part_manuf="Freud Inc"
            ),
            identity=ProductIdentitySchema(
                mfg_part_num="MPN-100",
                manufacturer=ValueMatchSchema(raw_value="Freud Inc", canonical_value="Freud Inc", confidence=0.9, status="MATCHED"),
                brand=ValueMatchSchema(raw_value="DIABLO", canonical_value="Diablo", confidence=0.8, status="RAW")
            ),
            classification=ClassificationDataSchema(
                department="Tools",
                class_name="Hand Tools",
                fine_class="Cutters",
                classpath="Tools>Hand Tools>Cutters",
                confidence=0.9,
                reason="Initial"
            ),
            content=ProductContentSchema(
                product_name="Diablo Cutters MPN-100",
                mobile_desc="Diablo Cutters",
                invoice_desc="lowercase invoice",
                short_desc="Short Desc",
                long_desc="Long Desc",
                retail_desc="Retail Desc",
                marketing_description="Mktg Desc",
                item_features=[]
            ),
            attributes=[
                ProductAttributeSchema(sequence=1, label="DIAMETER", raw_value="24 in", normalized_value="24 in", uom="in", status="VALID", lov_matched=True)
            ],
            quality=dummy_quality,
            validations=[],
            requires_review=True,
            created_at="2026-08-17T00:00:00Z",
            updated_at="2026-08-17T00:00:00Z"
        )
        self.session.add_product(self.product)

        # Add 2 reviews for this product
        self.review1 = ReviewItemSchema(
            review_id="rev-01",
            product_id=self.product.id,
            mfg_part_num="MPN-100",
            product_name=self.product.content.product_name,
            field="brand",
            field_name="brand",
            issue_type="R-BRD-001",
            severity="WARNING",
            current_value="Diablo",
            suggested_value="Diablo®",
            reason="Brand missing registered trademark",
            quality_score=70.0,
            status="PENDING",
            created_at="2026-08-17T00:00:00Z"
        )
        self.review2 = ReviewItemSchema(
            review_id="rev-02",
            product_id=self.product.id,
            mfg_part_num="MPN-100",
            product_name=self.product.content.product_name,
            field="invoice_desc",
            field_name="invoice_desc",
            issue_type="R-CASE-INVOICE",
            severity="WARNING",
            current_value="lowercase invoice",
            suggested_value="LOWERCASE INVOICE",
            reason="Invoice desc must be uppercase",
            quality_score=70.0,
            status="PENDING",
            created_at="2026-08-17T00:00:00Z"
        )
        self.session.add_review(self.review1)
        self.session.add_review(self.review2)

    def test_01_autofix_applies_value_and_maintains_requires_review_if_reviews_remain(self):
        # Apply review 1
        res = review_service.autofix_review(self.session, "rev-01")
        self.assertIsNotNone(res)
        self.assertEqual(res.status, "AUTO_FIXED")

        # Product brand must now have suggested value applied!
        updated_prod = self.session.get_product(self.product.id)
        self.assertEqual(updated_prod.identity.brand.canonical_value, "Diablo®")

        # review2 is still pending, so requires_review must remain True!
        self.assertTrue(updated_prod.requires_review)

        # Verify audit event was logged
        events = self.session.get_audit_events_for_product(self.product.id)
        self.assertTrue(any(e["event_type"] == "AUTO_FIX_APPLIED" for e in events))

    def test_02_all_reviews_approved_clears_requires_review(self):
        # Approve review 1
        review_service.approve_review(self.session, "rev-01")
        prod = self.session.get_product(self.product.id)
        self.assertEqual(prod.identity.brand.canonical_value, "Diablo®")
        self.assertTrue(prod.requires_review)

        # Approve review 2
        review_service.approve_review(self.session, "rev-02")
        prod2 = self.session.get_product(self.product.id)
        self.assertEqual(prod2.content.invoice_desc, "LOWERCASE INVOICE")

        # Now all pending reviews are resolved
        self.assertFalse(prod2.requires_review)

    def test_03_edit_review_applies_custom_value(self):
        res = review_service.edit_review(self.session, "rev-01", "CustomBrand®")
        self.assertIsNotNone(res)
        self.assertEqual(res.status, "EDITED")
        prod = self.session.get_product(self.product.id)
        self.assertEqual(prod.identity.brand.canonical_value, "CustomBrand®")

if __name__ == "__main__":
    unittest.main()
