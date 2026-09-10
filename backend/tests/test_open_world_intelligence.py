import unittest
import os
import sys
import csv
import io

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.processing_service import processing_service
from app.services.local_cleaner import local_cleaner
from app.services.export_service import export_service
from app.evaluation.evaluator import evaluator_engine
from app.session.session_models import ProcessingSession

class TestOpenWorldProductIntelligence(unittest.TestCase):
    def setUp(self):
        self.session = ProcessingSession(session_id="test-open-world-session")

    def test_01_ball_valve_plumbing(self):
        candidate = {
            "source_row_id": 1,
            "mpn": "BV-75-BR",
            "description": "3/4 in Brass Full Port Ball Valve FNPT x FNPT 600 PSI WOG",
            "e1_brand": "APOLLO",
            "unilog_brand": "APOLLO",
            "dib_brand": "",
            "part_manuf": "Apollo Valves",
            "raw_row": {}
        }
        product = processing_service.process_candidate(self.session, candidate)
        attrs = {a.label: a.normalized_value or a.raw_value for a in product.attributes}

        self.assertIn(product.classification.department, ["Plumbing & Pumps", "Industrial & Fluid Power"])
        self.assertEqual(attrs.get("Nominal Size"), "3/4")
        self.assertEqual(attrs.get("Material"), "Brass")
        self.assertEqual(attrs.get("Pressure Rating"), "600 PSI")
        self.assertEqual(attrs.get("Connection Type"), "FNPT")
        self.assertIn("Product Type", attrs)
        self.assertIn("Valve", attrs["Product Type"])

    def test_02_abrasive_film_disc(self):
        candidate = {
            "source_row_id": 2,
            "mpn": "775L-P150",
            "description": "5 in 775L Stikit Film Disc P150 Grit Ceramic Grain",
            "e1_brand": "3M",
            "unilog_brand": "3M",
            "dib_brand": "",
            "part_manuf": "3M (1234)",
            "raw_row": {}
        }
        product = processing_service.process_candidate(self.session, candidate)
        attrs = {a.label: a.normalized_value or a.raw_value for a in product.attributes}

        self.assertEqual(product.identity.manufacturer.canonical_value, "3M")
        self.assertEqual(attrs.get("Abrasive Grit"), "P150")
        self.assertEqual(attrs.get("Disc Diameter"), "5")
        self.assertIn(attrs.get("Product Type", ""), ["Film Disc", "Abrasive Film Disc", "Abrasive Disc"])

    def test_03_led_bulb_lighting(self):
        candidate = {
            "source_row_id": 3,
            "mpn": "LED-A19-60W",
            "description": "Philips A19 LED Bulb 60W Equivalent 2700K Warm White 120V",
            "e1_brand": "PHILIPS",
            "unilog_brand": "PHILIPS",
            "dib_brand": "",
            "part_manuf": "Philips Lighting",
            "raw_row": {}
        }
        product = processing_service.process_candidate(self.session, candidate)
        attrs = {a.label: a.normalized_value or a.raw_value for a in product.attributes}

        self.assertEqual(product.classification.department, "Electrical & Lighting")
        self.assertEqual(attrs.get("Wattage"), "60")
        self.assertEqual(attrs.get("Voltage"), "120")
        self.assertEqual(attrs.get("Bulb Shape"), "A19")
        self.assertEqual(attrs.get("Color Temperature"), "2700K")
        self.assertIn("Bulb", attrs.get("Product Type", ""))

    def test_04_bolt_fastener(self):
        candidate = {
            "source_row_id": 4,
            "mpn": "HEX-2520-SS",
            "description": "1/4-20 x 1 in Hex Head Cap Screw Stainless Steel Grade 316",
            "e1_brand": "",
            "unilog_brand": "",
            "dib_brand": "",
            "part_manuf": "",
            "raw_row": {}
        }
        product = processing_service.process_candidate(self.session, candidate)
        attrs = {a.label: a.normalized_value or a.raw_value for a in product.attributes}

        self.assertEqual(attrs.get("Thread Size"), "1/4-20")
        self.assertEqual(attrs.get("Fastener Head Style"), "Hex Head")
        self.assertEqual(attrs.get("Material"), "Stainless Steel")
        self.assertIn("Screw", attrs.get("Product Type", ""))

    def test_05_electrical_breaker(self):
        candidate = {
            "source_row_id": 5,
            "mpn": "QO120",
            "description": "Square D QO 20 Amp 1-Pole Circuit Breaker 120V",
            "e1_brand": "SQUARE D",
            "unilog_brand": "SQUARE D",
            "dib_brand": "",
            "part_manuf": "Square D",
            "raw_row": {}
        }
        product = processing_service.process_candidate(self.session, candidate)
        attrs = {a.label: a.normalized_value or a.raw_value for a in product.attributes}

        self.assertEqual(attrs.get("Amperage"), "20")
        self.assertEqual(attrs.get("Voltage"), "120")
        self.assertIn("Circuit Breaker", attrs.get("Product Type", ""))

    def test_06_plumbing_fitting(self):
        candidate = {
            "source_row_id": 6,
            "mpn": "CPLG-38-BR",
            "description": "3/8 in Brass Coupling FNPT x FNPT",
            "e1_brand": "",
            "unilog_brand": "",
            "dib_brand": "",
            "part_manuf": "Dixon Valve",
            "raw_row": {}
        }
        product = processing_service.process_candidate(self.session, candidate)
        attrs = {a.label: a.normalized_value or a.raw_value for a in product.attributes}

        self.assertEqual(attrs.get("Nominal Size"), "3/8")
        self.assertEqual(attrs.get("Material"), "Brass")
        self.assertEqual(attrs.get("Connection Type"), "FNPT")
        self.assertIn("Fitting", attrs.get("Product Type", ""))

    def test_07_hvac_product(self):
        candidate = {
            "source_row_id": 7,
            "mpn": "TH8321WF",
            "description": "Honeywell VisionPRO 8000 Touchscreen Programmable Thermostat 24V",
            "e1_brand": "HONEYWELL",
            "unilog_brand": "HONEYWELL",
            "dib_brand": "",
            "part_manuf": "Honeywell",
            "raw_row": {}
        }
        product = processing_service.process_candidate(self.session, candidate)
        attrs = {a.label: a.normalized_value or a.raw_value for a in product.attributes}

        self.assertEqual(attrs.get("Voltage"), "24")
        self.assertIn("Thermostat", attrs.get("Product Type", ""))

    def test_08_construction_material(self):
        candidate = {
            "source_row_id": 8,
            "mpn": "DECK-PVC-20",
            "description": "Composite Decking Board PVC 20 FT x 6 IN Brown Woodgrain",
            "e1_brand": "TREX",
            "unilog_brand": "TREX",
            "dib_brand": "",
            "part_manuf": "Trex Company",
            "raw_row": {}
        }
        product = processing_service.process_candidate(self.session, candidate)
        attrs = {a.label: a.normalized_value or a.raw_value for a in product.attributes}

        self.assertEqual(attrs.get("Material"), "PVC")
        self.assertIn(attrs.get("Length"), ["20 FT", "20 ft"])
        self.assertIn(attrs.get("Width"), ["6 IN", "6 in"])
        self.assertEqual(attrs.get("Color / Finish"), "Brown")

    def test_09_aviation_snips_tool(self):
        candidate = {
            "source_row_id": 9,
            "mpn": "M1R",
            "description": "Wiss Left Cut Aviation Snip 18 Gauge Cold Rolled Steel",
            "e1_brand": "WISS",
            "unilog_brand": "WISS",
            "dib_brand": "",
            "part_manuf": "Apex Tool Group",
            "raw_row": {}
        }
        product = processing_service.process_candidate(self.session, candidate)
        attrs = {a.label: a.normalized_value or a.raw_value for a in product.attributes}

        self.assertEqual(attrs.get("Cutting Capacity"), "18 Gauge")
        self.assertIn("Snip", attrs.get("Product Type", ""))

    def test_10_unknown_source_manufacturer_preservation(self):
        candidate = {
            "source_row_id": 10,
            "mpn": "PUMP-900",
            "description": "High Pressure Centrifugal Water Pump 5 HP 230V Cast Iron",
            "e1_brand": "ABC Industrial Pvt Ltd",
            "unilog_brand": "ABC Industrial Pvt Ltd",
            "dib_brand": "",
            "part_manuf": "ABC Industrial Pvt Ltd",
            "raw_row": {}
        }
        product = processing_service.process_candidate(self.session, candidate)

        # CRITICAL Open-world rule: Unknown manufacturer MUST NOT be converted to GENERIC or UNKNOWN
        self.assertEqual(product.identity.manufacturer.canonical_value, "ABC Industrial Pvt Ltd")
        self.assertEqual(product.identity.manufacturer.status, "UNVERIFIED")
        self.assertNotEqual(product.identity.manufacturer.canonical_value.upper(), "GENERIC")
        self.assertNotEqual(product.identity.manufacturer.canonical_value.upper(), "UNKNOWN")

    def test_11_negative_constraints_and_no_fabrication(self):
        candidate = {
            "source_row_id": 11,
            "mpn": "TOOL-BASIC",
            "description": "General Utility Blade Pack 5 PK",
            "e1_brand": "",
            "unilog_brand": "",
            "dib_brand": "",
            "part_manuf": "",
            "raw_row": {}
        }
        product = processing_service.process_candidate(self.session, candidate)
        attrs = {a.label: a.normalized_value or a.raw_value for a in product.attributes}

        # Negative constraint 1: No fabricated pressure rating
        self.assertNotIn("Pressure Rating", attrs)
        # Negative constraint 2: No fabricated voltage
        self.assertNotIn("Voltage", attrs)
        # Negative constraint 3: No requirement to fill 50 attributes
        self.assertLess(len(product.attributes), 20)
        # Packaging quantity extracted accurately
        self.assertEqual(attrs.get("Package Quantity"), "5")

    def test_12_commercial_raw_columns_preservation(self):
        candidate = {
            "source_row_id": 12,
            "mpn": "PART-COMM",
            "description": "Steel Bracket 10 IN Heavy Duty",
            "e1_brand": "",
            "unilog_brand": "",
            "dib_brand": "",
            "part_manuf": "",
            "raw_row": {
                "Cost": "12.50",
                "List Price": "24.99",
                "Stock": "150",
                "Country of Origin": "USA",
                "UPC": "012345678901"
            }
        }
        product = processing_service.process_candidate(self.session, candidate)
        attrs = {a.label: a.normalized_value or a.raw_value for a in product.attributes}

        self.assertEqual(attrs.get("Unit Cost"), "12.50")
        self.assertEqual(attrs.get("List Price"), "24.99")
        self.assertEqual(attrs.get("Stock Quantity"), "150")
        self.assertEqual(attrs.get("Country of Origin"), "USA")
        self.assertEqual(attrs.get("UPC"), "012345678901")

    def test_13_dual_export_contracts(self):
        candidate = {
            "source_row_id": 13,
            "mpn": "VALVE-TEST",
            "description": "1/2 in Brass Ball Valve 400 PSI",
            "e1_brand": "NIBCO",
            "unilog_brand": "NIBCO",
            "dib_brand": "",
            "part_manuf": "NIBCO Inc",
            "raw_row": {}
        }
        product = processing_service.process_candidate(self.session, candidate)

        # 1. Test 252-column delivery projection
        csv_252 = export_service.export_products_to_csv([product])
        reader_252 = csv.reader(io.StringIO(csv_252))
        header_252 = next(reader_252)
        self.assertEqual(len(header_252), 252, "Delivery projection MUST have exactly 252 columns")

        # 2. Test Clean Intelligence CSV export
        clean_csv = export_service.export_clean_intelligence_csv([product])
        reader_clean = csv.reader(io.StringIO(clean_csv))
        header_clean = next(reader_clean)
        data_row = next(reader_clean)

        self.assertIn("PRODUCT_TYPE", header_clean)
        self.assertIn("PART_NUMBER", header_clean)
        self.assertIn("CLASSPATH", header_clean)
        prod_type_idx = header_clean.index("PRODUCT_TYPE")
        self.assertIn("Valve", data_row[prod_type_idx])

    def test_14_evaluator_unverified_preservation_and_coverage(self):
        candidate = {
            "source_row_id": 14,
            "mpn": "SPECIAL-01",
            "description": "Custom Sensor Unit 24V",
            "e1_brand": "Specialty Controls Corp",
            "unilog_brand": "Specialty Controls Corp",
            "dib_brand": "",
            "part_manuf": "Specialty Controls Corp",
            "raw_row": {}
        }
        product = processing_service.process_candidate(self.session, candidate)
        self.session.products[product.id] = product
        self.session.total_records = 1

        eval_result = evaluator_engine.run_benchmark_evaluation(self.session)
        self.assertEqual(eval_result.domain_scores.manufacturer, 100.0)
        self.assertEqual(eval_result.processing_coverage, 100.0)
        self.assertFalse(eval_result.ground_truth_available)

if __name__ == "__main__":
    unittest.main()
