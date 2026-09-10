import unittest
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.session.session_manager import session_manager
from app.services.ingestion_service import ingestion_service
from app.services.processing_service import processing_service
from app.services.export_service import export_service
from app.evaluation.evaluator import evaluator_engine

class TestSanityDataset(unittest.TestCase):
    def test_process_sanity_dataset(self):
        sanity_csv_path = os.path.join(os.path.dirname(__file__), "..", "storage_data", "inputs", "import-1e365f74_sortolog_sanity_test.csv")
        self.assertTrue(os.path.exists(sanity_csv_path), "Sanity CSV must exist")

        with open(sanity_csv_path, "rb") as f:
            content_bytes = f.read()

        import_id, total_count, candidates = ingestion_service.process_import("sortolog_sanity_test.csv", content_bytes)
        self.assertEqual(len(candidates), 15, "Expected exactly 15 candidate rows in sanity test dataset")

        session = session_manager.create_session("test-sanity-session-01", seed_demo=False)
        processed = processing_service.process_candidates_batch(session, candidates, max_workers=4)
        self.assertEqual(len(processed), 15, "Expected all 15 candidates to be processed without loss")

        # Verify each product individually
        products_map = {p.identity.mfg_part_num: p for p in processed}

        # 1. SFQ125 - Valve
        p1 = products_map["SFQ125"]
        self.assertIn("Watts", p1.identity.manufacturer.canonical_value)
        self.assertIn("Valve", p1.classification.classpath)
        attr_labels = [a.label for a in p1.attributes]
        self.assertNotIn("MANUFACTURER PART NUMBER", attr_labels)
        self.assertNotIn("PRIMARY BRAND", attr_labels)
        self.assertIn("Connection Size", attr_labels)
        self.assertIn("Pressure Rating", attr_labels)

        # 2. DBD0900994101F - Freud Diablo Cut-off Disc
        p_disc = products_map["DBD0900994101F"]
        self.assertEqual(p_disc.identity.manufacturer.canonical_value, "Freud Inc.")
        self.assertEqual(p_disc.identity.brand.canonical_value, "Diablo®")
        self.assertIn("Abrasive", p_disc.classification.department)
        disc_labels = [a.label for a in p_disc.attributes]
        self.assertIn("Wheel Diameter", disc_labels)

        # 3. 586891 - Philips LED
        p_led = products_map["586891"]
        self.assertEqual(p_led.identity.manufacturer.canonical_value, "Philips Lighting")
        self.assertEqual(p_led.identity.brand.canonical_value, "Philips®")
        self.assertIn("Lighting", p_led.classification.department)
        led_labels = [a.label for a in p_led.attributes]
        self.assertIn("Wattage", led_labels)
        self.assertIn("Bulb Shape", led_labels)

        # 4. TREX-1X6-WALNUT - Decking
        p_deck = products_map["TREX-1X6-WALNUT"]
        self.assertIn("Building Materials", p_deck.classification.department)
        deck_labels = [a.label for a in p_deck.attributes]
        self.assertIn("Length", deck_labels)
        self.assertIn("Material Type", deck_labels)

        # Verify exports
        unilog_csv = export_service.export_products_to_csv(processed)
        self.assertEqual(len(unilog_csv.splitlines()[0].split(",")), 252, "Unilog export must have exactly 252 columns")

        clean_csv = export_service.export_clean_intelligence_csv(processed)
        clean_lines = clean_csv.splitlines()
        self.assertGreater(len(clean_lines), 15)
        clean_headers = clean_lines[0].split(",")
        self.assertIn("PART_NUMBER", clean_headers)
        self.assertIn("MANUFACTURER", clean_headers)
        self.assertIn("BRAND", clean_headers)
        self.assertNotIn("ATTRIBUTE_LABEL_1", clean_headers)

        # Run evaluation
        eval_res = evaluator_engine.run_benchmark_evaluation(session)
        self.assertEqual(eval_res.products_evaluated, 15)
        self.assertGreater(eval_res.overall_accuracy, 75.0)

if __name__ == "__main__":
    unittest.main()
