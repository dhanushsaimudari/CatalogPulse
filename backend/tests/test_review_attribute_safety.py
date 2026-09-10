import sys
import os
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.schemas.product import (
    ProductSchema, SourceDataSchema, ProductIdentitySchema, ValueMatchSchema,
    ClassificationDataSchema, ProductContentSchema, ProductAttributeSchema,
    QualityScoreSchema, ComponentScoreSchema
)
from app.schemas.review import ReviewItemSchema
from app.session.session_manager import session_manager
from app.services.review_service import review_service

class TestReviewAttributeSafety(unittest.TestCase):
    def setUp(self):
        self.session = session_manager.create_session("test-review-safety-sess", seed_demo=False)
        dummy_quality = QualityScoreSchema(
            overall_score=75.0,
            status="NEEDS_REVIEW",
            sub_scores=ComponentScoreSchema(
                brand_normalization=80.0,
                classification=80.0,
                attributes=80.0,
                descriptions=80.0,
                digital_assets=70.0,
                evidence=70.0
            ),
            breakdown_notes=[]
        )
        self.product = ProductSchema(
            id="prod-valve-01",
            source_row_id=1,
            source_data=SourceDataSchema(
                mfg_part_num="BV-600",
                part_desc="3/4 in Brass Full Port Ball Valve FNPT x FNPT 600 PSI WOG",
                e1_brand="Apollo",
                unilog_brand="Apollo",
                dib_brand="",
                part_manuf="Apollo Valves",
                raw_columns={}
            ),
            identity=ProductIdentitySchema(
                mfg_part_num="BV-600",
                manufacturer=ValueMatchSchema(raw_value="Apollo Valves", canonical_value="Apollo Valves", confidence=0.98, status="MATCHED"),
                brand=ValueMatchSchema(raw_value="Apollo", canonical_value="Apollo®", confidence=0.98, status="MATCHED")
            ),
            classification=ClassificationDataSchema(
                department="Plumbing",
                class_name="Valves",
                fine_class="Ball Valves",
                classpath="Plumbing > Valves > Ball Valves > Full Port Ball Valves",
                confidence=0.95,
                reason="Valve matching"
            ),
            content=ProductContentSchema(
                product_name="Apollo 3/4 in Brass Ball Valve 600 PSI",
                mobile_desc="Apollo 3/4 in Brass Ball Valve",
                invoice_desc="APOLLO 3/4 IN BRASS BALL VALVE",
                short_desc="Apollo 3/4 in Brass Ball Valve 600 PSI",
                long_desc="Apollo 3/4 in Brass Full Port Ball Valve FNPT x FNPT 600 PSI WOG",
                retail_desc="Apollo Brass Ball Valve 600 PSI",
                marketing_description="Full port ball valve with brass construction.",
                item_features=["Full port design", "600 PSI rating"]
            ),
            attributes=[
                ProductAttributeSchema(
                    sequence=1,
                    label="PRESSURE RATING",
                    raw_value="600 PSI",
                    normalized_value="600 PSI",
                    uom="PSI",
                    status="VALID"
                ),
                ProductAttributeSchema(
                    sequence=2,
                    label="MATERIAL",
                    raw_value="Brass",
                    normalized_value="Brass",
                    uom="",
                    status="VALID"
                ),
                ProductAttributeSchema(
                    sequence=3,
                    label="CONNECTION TYPE",
                    raw_value="FNPT",
                    normalized_value="FNPT",
                    uom="",
                    status="VALID"
                ),
            ],
            validations=[],
            quality=dummy_quality,
            requires_review=True,
            created_at="2026-08-17T00:00:00Z",
            updated_at="2026-08-17T00:00:00Z"
        )
        self.session.add_product(self.product)

    def test_unmatched_attribute_review_does_not_corrupt_attributes_zero(self):
        """
        Verify that attempting to autofix or approve a review for a non-existent
        attribute (e.g. FINISH) NEVER modifies attributes[0] (PRESSURE RATING)
        or any other existing attribute.
        """
        review_finish = ReviewItemSchema(
            review_id="rev-finish-01",
            product_id=self.product.id,
            mfg_part_num="BV-600",
            product_name=self.product.content.product_name,
            field="attribute.FINISH",
            field_name="attribute.FINISH",
            issue_type="R-ATTR-FINISH",
            severity="WARNING",
            current_value="",
            suggested_value="Polished Chrome",
            reason="Missing finish attribute",
            quality_score=80.0,
            status="PENDING",
            created_at="2026-08-17T00:00:00Z"
        )
        self.session.add_review(review_finish)

        # 1. Attempt auto-fix for the non-existent attribute
        res = review_service.autofix_review(self.session, "rev-finish-01")
        self.assertIsNone(res, "Autofix should return None when target attribute is not present on product")

        # 2. Verify attributes[0] was NOT corrupted
        prod = self.session.get_product(self.product.id)
        self.assertEqual(prod.attributes[0].label, "PRESSURE RATING")
        self.assertEqual(prod.attributes[0].normalized_value, "600 PSI")
        self.assertNotEqual(prod.attributes[0].normalized_value, "Polished Chrome")

        # 3. Verify all other existing attributes remain intact
        self.assertEqual(prod.attributes[1].label, "MATERIAL")
        self.assertEqual(prod.attributes[1].normalized_value, "Brass")
        self.assertEqual(prod.attributes[2].label, "CONNECTION TYPE")
        self.assertEqual(prod.attributes[2].normalized_value, "FNPT")
        self.assertEqual(len(prod.attributes), 3, "No extra attributes should have been added or corrupted")

        # 4. Attempt approve_review on the non-existent attribute
        approve_res = review_service.approve_review(self.session, "rev-finish-01")
        self.assertIsNone(approve_res, "Approve should return None when target attribute is not present on product")

        # Re-verify attributes[0] remains 600 PSI
        prod_after_approve = self.session.get_product(self.product.id)
        self.assertEqual(prod_after_approve.attributes[0].normalized_value, "600 PSI")

    def test_matched_attribute_review_updates_correctly(self):
        """
        Verify that an existing attribute (e.g. PRESSURE RATING) CAN be updated
        safely when requested by a review action.
        """
        review_pressure = ReviewItemSchema(
            review_id="rev-pressure-01",
            product_id=self.product.id,
            mfg_part_num="BV-600",
            product_name=self.product.content.product_name,
            field="attribute.PRESSURE RATING",
            field_name="attribute.PRESSURE RATING",
            issue_type="R-UOM-002",
            severity="WARNING",
            current_value="600 PSI",
            suggested_value="800 PSI",
            reason="Update pressure rating",
            quality_score=80.0,
            status="PENDING",
            created_at="2026-08-17T00:00:00Z"
        )
        self.session.add_review(review_pressure)

        res = review_service.autofix_review(self.session, "rev-pressure-01")
        self.assertIsNotNone(res)
        self.assertEqual(res.status, "AUTO_FIXED")

        prod = self.session.get_product(self.product.id)
        self.assertEqual(prod.attributes[0].label, "PRESSURE RATING")
        self.assertEqual(prod.attributes[0].normalized_value, "800 PSI")
        # Other attributes remain untouched
        self.assertEqual(prod.attributes[1].label, "MATERIAL")
        self.assertEqual(prod.attributes[1].normalized_value, "Brass")

if __name__ == "__main__":
    unittest.main()
