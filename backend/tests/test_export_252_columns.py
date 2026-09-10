import unittest
import csv
import io
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.schemas.product import (
    ProductSchema, SourceDataSchema, ProductIdentitySchema, ValueMatchSchema,
    ClassificationDataSchema, ProductContentSchema, ProductAttributeSchema,
    QualityScoreSchema, ComponentScoreSchema
)
from app.services.export_service import export_service

class TestExport252Columns(unittest.TestCase):
    def setUp(self):
        candidate_paths = [
            "output_columns.json",
            os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "output_columns.json")),
            os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "output_columns.json")),
        ]
        loaded = False
        for p in candidate_paths:
            if os.path.exists(p):
                with open(p, "r", encoding="utf-8") as f:
                    self.expected_headers = json.load(f)
                    loaded = True
                    break
        if not loaded:
            raise FileNotFoundError("Could not locate output_columns.json in any candidate path.")

    def test_01_exact_252_column_count_and_headers(self):
        self.assertEqual(len(self.expected_headers), 252, "output_columns.json must contain exactly 252 columns")
        self.assertEqual(len(export_service.headers), 252, "export_service headers must match 252 columns")
        self.assertEqual(export_service.headers, self.expected_headers, "Headers must match output_columns.json exactly")

    def test_02_export_product_mapping_with_attributes_and_features(self):
        dummy_quality = QualityScoreSchema(
            overall_score=95.0,
            status="EXCELLENT",
            sub_scores=ComponentScoreSchema(
                brand_normalization=100.0,
                classification=100.0,
                attributes=95.0,
                descriptions=90.0,
                digital_assets=90.0,
                evidence=90.0
            ),
            breakdown_notes=[]
        )

        sample_attrs = [
            ProductAttributeSchema(sequence=1, label="DIAMETER", raw_value="1/2 IN", normalized_value="0.5 IN", uom="IN", status="VALID", lov_matched=True),
            ProductAttributeSchema(sequence=2, label="VOLTAGE", raw_value="120V", normalized_value="120 V", uom="V", status="VALID", lov_matched=True),
        ]

        product = ProductSchema(
            id="prod-test-mpn-123",
            source_row_id=1,
            source_data=SourceDataSchema(
                mfg_part_num="TEST-MPN-123",
                part_desc="Test 1/2 in Industrial Disc",
                e1_brand="DIABLO",
                unilog_brand="DIABLO",
                dib_brand="DIABLO",
                part_manuf="Freud Inc (2435)",
                raw_columns={"With": "Mounting Hardware", "Standard/Approvals": "UL Listed", "UPC": "012345678901"}
            ),
            identity=ProductIdentitySchema(
                mfg_part_num="TEST-MPN-123",
                manufacturer=ValueMatchSchema(raw_value="Freud Inc (2435)", canonical_value="Freud Inc", confidence=0.98, status="NORMALIZED"),
                brand=ValueMatchSchema(raw_value="DIABLO", canonical_value="Diablo®", confidence=0.95, status="NORMALIZED")
            ),
            classification=ClassificationDataSchema(
                department="Abrasives & Cutting Tools",
                class_name="Abrasive Discs",
                fine_class="Metal Cut-Off Discs",
                classpath="Abrasives & Cutting Tools>Abrasive Discs>Metal Cut-Off Discs",
                confidence=0.96,
                reason="AI Classification"
            ),
            content=ProductContentSchema(
                product_name="Diablo® Metal Cut-Off Disc TEST-MPN-123",
                mobile_desc="Diablo Cut-Off Disc TEST-MPN-123"[:35],
                invoice_desc="DIABLO CUT-OFF DISC 120V"[:30],
                short_desc="Diablo® Metal Cut-Off Disc Spec",
                long_desc="Diablo® Metal Cut-Off Disc manufactured by Freud Inc.",
                retail_desc="Premium Diablo® Cut-Off Disc",
                marketing_description="Commercial grade Diablo® metal cut-off disc.",
                item_features=["Heavy-duty cut-off disc", "Engineered for steel cutting"]
            ),
            attributes=sample_attrs,
            quality=dummy_quality,
            validations=[],
            created_at="2026-08-17T00:00:00Z",
            updated_at="2026-08-17T00:00:00Z"
        )

        csv_text = export_service.export_products_to_csv([product])
        reader = csv.reader(io.StringIO(csv_text))
        header_row = next(reader)
        data_row = next(reader)

        self.assertEqual(len(header_row), 252)
        self.assertEqual(len(data_row), 252)

        row_dict = dict(zip(header_row, data_row))

        # Verify key fields
        self.assertEqual(row_dict["PART_NUMBER"], "TEST-MPN-123")
        self.assertEqual(row_dict["MANUFACTURER_PART_NUMBER"], "TEST-MPN-123")
        self.assertEqual(row_dict["MANUFACTURER_NAME"], "Freud Inc")
        self.assertEqual(row_dict["BRAND_NAME"], "Diablo®")
        self.assertEqual(row_dict["Classpath"], "Abrasives & Cutting Tools>Abrasive Discs>Metal Cut-Off Discs")
        self.assertEqual(row_dict["Product Name"], "Diablo® Metal Cut-Off Disc TEST-MPN-123")
        self.assertEqual(row_dict["ITEM_FEATURES_1"], "Heavy-duty cut-off disc")
        self.assertEqual(row_dict["ITEM_FEATURES_2"], "Engineered for steel cutting")

        # Verify space-separated attribute columns
        self.assertEqual(row_dict["ATTRIBUTE_LABEL 1"], "DIAMETER")
        self.assertEqual(row_dict["ATTRIBUTE_VALUE 1"], "0.5 IN")
        self.assertEqual(row_dict["ATTRIBUTE_UOM 1"], "IN")

        self.assertEqual(row_dict["ATTRIBUTE_LABEL 2"], "VOLTAGE")
        self.assertEqual(row_dict["ATTRIBUTE_VALUE 2"], "120 V")
        self.assertEqual(row_dict["ATTRIBUTE_UOM 2"], "V")

        # Verify non-overwritten raw columns
        self.assertEqual(row_dict["With"], "Mounting Hardware")
        self.assertEqual(row_dict["Standard/Approvals"], "UL Listed")
        self.assertEqual(row_dict["UPC"], "012345678901")

if __name__ == "__main__":
    unittest.main()
