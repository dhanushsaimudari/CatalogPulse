import unittest
import os
import sys
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app
from app.schemas.product import (
    ProductSchema, SourceDataSchema, ProductIdentitySchema, ValueMatchSchema,
    ClassificationDataSchema, ProductContentSchema, ProductAttributeSchema,
    QualityScoreSchema, ComponentScoreSchema
)
from app.schemas.review import ReviewItemSchema
from app.session.session_manager import session_manager
from app.services.review_service import review_service


class TestReviewBulkFix(unittest.TestCase):
    def setUp(self):
        self.session_id = "test-bulk-fix-sess"
        self.session = session_manager.create_session(self.session_id, seed_demo=False)
        self.client = TestClient(app)

        dummy_quality = QualityScoreSchema(
            overall_score=75.0,
            status="NEEDS_REVIEW",
            sub_scores=ComponentScoreSchema(
                brand_normalization=75.0,
                classification=75.0,
                attributes=75.0,
                descriptions=75.0,
                digital_assets=75.0,
                evidence=75.0
            ),
            breakdown_notes=[]
        )

        self.product = ProductSchema(
            id="prod-bulk-01",
            source_row_id=1,
            source_data=SourceDataSchema(
                mfg_part_num="MPN-BULK-01",
                part_desc="Test Bulk Product Part",
                e1_brand="Diablo",
                unilog_brand="Diablo",
                dib_brand="",
                part_manuf="Freud Inc"
            ),
            identity=ProductIdentitySchema(
                mfg_part_num="MPN-BULK-01",
                manufacturer=ValueMatchSchema(raw_value="Freud Inc", canonical_value="Freud Inc", confidence=0.9, status="MATCHED"),
                brand=ValueMatchSchema(raw_value="Diablo", canonical_value="Diablo", confidence=0.8, status="RAW")
            ),
            classification=ClassificationDataSchema(
                department="Tools",
                class_name="Hand Tools",
                fine_class="Cutters",
                classpath="Tools>Hand Tools>Cutters",
                confidence=0.9,
                reason="Initial classification"
            ),
            content=ProductContentSchema(
                product_name="Diablo Cutters MPN-BULK-01",
                mobile_desc="Diablo Cutters",
                invoice_desc="lowercase invoice desc",
                short_desc="Short Description",
                long_desc="Long Description",
                retail_desc="Retail Description",
                marketing_description="Marketing Description",
                item_features=[]
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
                )
            ],
            validations=[],
            quality=dummy_quality,
            requires_review=True,
            created_at="2026-08-17T00:00:00Z",
            updated_at="2026-08-17T00:00:00Z"
        )
        self.session.add_product(self.product)

        # Create 3 review items
        self.rev1 = ReviewItemSchema(
            review_id="rev-bulk-01",
            product_id=self.product.id,
            mfg_part_num="MPN-BULK-01",
            product_name=self.product.content.product_name,
            field="brand",
            field_name="brand",
            issue_type="R-BRD-001",
            severity="WARNING",
            current_value="Diablo",
            suggested_value="Diablo®",
            reason="Brand missing registered trademark",
            quality_score=75.0,
            status="PENDING",
            created_at="2026-08-17T00:00:00Z"
        )
        self.rev2 = ReviewItemSchema(
            review_id="rev-bulk-02",
            product_id=self.product.id,
            mfg_part_num="MPN-BULK-01",
            product_name=self.product.content.product_name,
            field="invoice_desc",
            field_name="invoice_desc",
            issue_type="R-CASE-INVOICE",
            severity="WARNING",
            current_value="lowercase invoice desc",
            suggested_value="UPPERCASE INVOICE DESC",
            reason="Invoice desc must be uppercase",
            quality_score=75.0,
            status="PENDING",
            created_at="2026-08-17T00:00:00Z"
        )
        self.rev_missing_attr = ReviewItemSchema(
            review_id="rev-bulk-03-missing",
            product_id=self.product.id,
            mfg_part_num="MPN-BULK-01",
            product_name=self.product.content.product_name,
            field="attribute.FINISH",
            field_name="attribute.FINISH",
            issue_type="R-ATTR-FINISH",
            severity="WARNING",
            current_value="",
            suggested_value="Polished Chrome",
            reason="Missing attribute that does not exist on product",
            quality_score=75.0,
            status="PENDING",
            created_at="2026-08-17T00:00:00Z"
        )
        self.session.add_review(self.rev1)
        self.session.add_review(self.rev2)
        self.session.add_review(self.rev_missing_attr)

    def test_01_fix_selected_single_review(self):
        """Test Fix Selected with 1 selected review item."""
        res = review_service.bulk_fix_reviews(self.session, review_ids=["rev-bulk-01"])
        self.assertEqual(res["status"], "COMPLETED")
        self.assertEqual(res["selected_count"], 1)
        self.assertEqual(res["applied_count"], 1)
        self.assertEqual(res["failed_count"], 0)

        # Verify review status updated
        rev = self.session.get_review("rev-bulk-01")
        self.assertEqual(rev.status, "AUTO_FIXED")

        # Verify product updated
        prod = self.session.get_product(self.product.id)
        self.assertEqual(prod.identity.brand.canonical_value, "Diablo®")

        # Other reviews must remain pending
        pending = self.session.list_reviews(status="PENDING")
        pending_ids = [r.review_id for r in pending]
        self.assertNotIn("rev-bulk-01", pending_ids)
        self.assertIn("rev-bulk-02", pending_ids)
        self.assertIn("rev-bulk-03-missing", pending_ids)

    def test_02_fix_selected_multiple_reviews(self):
        """Test Fix Selected with multiple selected reviews."""
        res = review_service.bulk_fix_reviews(self.session, review_ids=["rev-bulk-01", "rev-bulk-02"])
        self.assertEqual(res["status"], "COMPLETED")
        self.assertEqual(res["selected_count"], 2)
        self.assertEqual(res["applied_count"], 2)
        self.assertEqual(res["failed_count"], 0)

        # Verify product values
        prod = self.session.get_product(self.product.id)
        self.assertEqual(prod.identity.brand.canonical_value, "Diablo®")
        self.assertEqual(prod.content.invoice_desc, "UPPERCASE INVOICE DESC")

        # Verify review statuses
        self.assertEqual(self.session.get_review("rev-bulk-01").status, "AUTO_FIXED")
        self.assertEqual(self.session.get_review("rev-bulk-02").status, "AUTO_FIXED")

    def test_03_fix_all_multiple_fixable_reviews(self):
        """Test Fix All with multiple eligible reviews."""
        res = review_service.bulk_fix_reviews(self.session, fix_all=True)
        self.assertEqual(res["status"], "COMPLETED")
        # All 3 had non-empty suggested values, 2 should apply and 1 should fail safely
        self.assertEqual(res["applied_count"], 2)
        self.assertEqual(res["failed_count"], 1)

        # Fixed items updated
        prod = self.session.get_product(self.product.id)
        self.assertEqual(prod.identity.brand.canonical_value, "Diablo®")
        self.assertEqual(prod.content.invoice_desc, "UPPERCASE INVOICE DESC")

        # The missing attribute item remains PENDING
        self.assertEqual(self.session.get_review("rev-bulk-03-missing").status, "PENDING")

    def test_04_one_failed_bulk_item_does_not_prevent_other_items_from_being_fixed(self):
        """
        Verify that selecting a review item that fails (e.g. missing attribute)
        does NOT prevent other selected items from being fixed.
        """
        res = review_service.bulk_fix_reviews(
            self.session,
            review_ids=["rev-bulk-01", "rev-bulk-03-missing", "rev-bulk-02"]
        )
        self.assertEqual(res["status"], "COMPLETED")
        self.assertEqual(res["selected_count"], 3)
        self.assertEqual(res["applied_count"], 2)
        self.assertEqual(res["failed_count"], 1)

        # rev-bulk-01 and rev-bulk-02 were successfully applied
        prod = self.session.get_product(self.product.id)
        self.assertEqual(prod.identity.brand.canonical_value, "Diablo®")
        self.assertEqual(prod.content.invoice_desc, "UPPERCASE INVOICE DESC")

    def test_05_missing_attribute_never_mutates_attributes_zero_or_unrelated(self):
        """
        Verify that attempting to autofix an attribute review that doesn't match any product
        attribute never corrupts attributes[0] or any existing attribute.
        """
        prod_before = self.session.get_product(self.product.id)
        original_attr0_val = prod_before.attributes[0].normalized_value
        original_attr0_lbl = prod_before.attributes[0].label
        self.assertEqual(original_attr0_lbl, "PRESSURE RATING")
        self.assertEqual(original_attr0_val, "600 PSI")

        res = review_service.bulk_fix_reviews(self.session, review_ids=["rev-bulk-03-missing"])
        self.assertEqual(res["applied_count"], 0)
        self.assertEqual(res["failed_count"], 1)

        prod_after = self.session.get_product(self.product.id)
        self.assertEqual(prod_after.attributes[0].label, "PRESSURE RATING")
        self.assertEqual(prod_after.attributes[0].normalized_value, "600 PSI")
        self.assertNotEqual(prod_after.attributes[0].normalized_value, "Polished Chrome")
        self.assertEqual(len(prod_after.attributes), 2)

    def test_06_individual_actions_still_work(self):
        """Verify individual approve, reject, and autofix still work as expected."""
        # Individual autofix
        res_fix = review_service.autofix_review(self.session, "rev-bulk-01")
        self.assertIsNotNone(res_fix)
        self.assertEqual(res_fix.status, "AUTO_FIXED")

        # Individual reject
        res_rej = review_service.reject_review(self.session, "rev-bulk-02")
        self.assertIsNotNone(res_rej)
        self.assertEqual(res_rej.status, "REJECTED")

        # Individual approve on a new review
        rev_app = ReviewItemSchema(
            review_id="rev-bulk-04",
            product_id=self.product.id,
            mfg_part_num="MPN-BULK-01",
            product_name=self.product.content.product_name,
            field="mobile_desc",
            field_name="mobile_desc",
            issue_type="R-DESC-001",
            severity="WARNING",
            current_value="Diablo Cutters",
            suggested_value="Diablo Premium Cutters",
            reason="Update mobile description",
            quality_score=75.0,
            status="PENDING",
            created_at="2026-08-17T00:00:00Z"
        )
        self.session.add_review(rev_app)
        res_app = review_service.approve_review(self.session, "rev-bulk-04")
        self.assertIsNotNone(res_app)
        self.assertEqual(res_app.status, "APPROVED")
        prod = self.session.get_product(self.product.id)
        self.assertEqual(prod.content.mobile_desc, "Diablo Premium Cutters")

    def test_07_fastapi_bulk_fix_endpoints(self):
        """Verify the FastAPI REST endpoints for bulk-fix."""
        # Test /api/v1/sessions/{session_id}/reviews/bulk-fix
        payload = {"review_ids": ["rev-bulk-01", "rev-bulk-02"], "fix_all": False}
        res = self.client.post(f"/api/v1/sessions/{self.session_id}/reviews/bulk-fix", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "COMPLETED")
        self.assertEqual(data["applied_count"], 2)

        # Test /api/v1/reviews/bulk-fix with session_id query param
        res2 = self.client.post(
            f"/api/v1/reviews/bulk-fix?session_id={self.session_id}",
            json={"fix_all": True}
        )
        self.assertEqual(res2.status_code, 200)
        data2 = res2.json()
        self.assertEqual(data2["status"], "COMPLETED")

    def test_08_clean_csv_export_endpoint_works(self):
        """Verify Clean Intelligence CSV export endpoint remains functional."""
        res = self.client.post(f"/api/v1/sessions/{self.session_id}/export-clean")
        self.assertEqual(res.status_code, 200)
        self.assertIn("text/csv", res.headers.get("content-type", ""))
        self.assertIn("Sortolog_Session", res.headers.get("content-disposition", ""))
        self.assertIn("Clean_Intelligence", res.headers.get("content-disposition", ""))

        # Verify 252-column export backend endpoint also remains functional
        res_252 = self.client.post(f"/api/v1/sessions/{self.session_id}/export")
        self.assertEqual(res_252.status_code, 200)
        self.assertIn("text/csv", res_252.headers.get("content-type", ""))
        self.assertIn("Unilog_Delivery", res_252.headers.get("content-disposition", ""))

    def test_09_frontend_header_only_has_clean_csv(self):
        """Verify Header.tsx contains Download Clean CSV and no 252-column button."""
        header_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../frontend/components/layout/Header.tsx"))
        self.assertTrue(os.path.exists(header_path))
        with open(header_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Download Clean CSV button exists
        self.assertIn("Download Clean CSV", content)
        self.assertIn("handleExportCleanCsv", content)

        # 252-column button must NOT be in Header.tsx
        self.assertNotIn("252-Col Delivery", content)
        self.assertNotIn("title=\"Export 252-Column Unilog Delivery CSV\"", content)
        self.assertNotIn("handleExportCsv", content)


if __name__ == "__main__":
    unittest.main()
