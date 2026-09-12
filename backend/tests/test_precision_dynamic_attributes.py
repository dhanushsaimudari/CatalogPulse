import sys
import os
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.processing_service import processing_service
from app.session.session_models import ProcessingSession
from app.ai.ai_provider_router import ai_provider_router

class TestPrecisionDynamicAttributes(unittest.TestCase):
    def setUp(self):
        self.session = ProcessingSession(session_id="test-precision-dynamic-attributes")

    def test_01_mpn_fragment_not_thread_size_cut_off_disc(self):
        """Input: 49-94-0001 ... Metal Cut Off Disc -> Must NOT produce THREAD_SIZE = 49-94."""
        candidate = {
            "source_row_id": 101,
            "mpn": "49-94-0001",
            "description": "49-94-0001 Milwaukee 4-1/2 in. x .045 in. x 7/8 in. Metal Cut Off Disc",
            "e1_brand": "MILWAUKEE",
            "unilog_brand": "MILWAUKEE",
            "dib_brand": "",
            "part_manuf": "Milwaukee Tool",
            "raw_row": {}
        }
        product = processing_service.process_candidate(self.session, candidate)
        attrs = {a.label.upper(): a.normalized_value or a.raw_value for a in product.attributes}

        self.assertNotIn("THREAD SIZE", attrs, "MPN fragment 49-94 must NOT be extracted as THREAD_SIZE")
        self.assertNotIn("THREAD_SIZE", attrs)
        # Should have valid abrasive specs
        self.assertEqual(attrs.get("DISC DIAMETER"), "4-1/2")
        self.assertEqual(attrs.get("WHEEL THICKNESS"), ".045")
        self.assertEqual(attrs.get("ARBOR SIZE"), "7/8")

    def test_02_mpn_fragment_not_thread_size_or_voltage(self):
        """Input: 5B-332-120 ... HIOLIT 5" P120 -> Must NOT produce THREAD_SIZE = 332-120 or VOLTAGE = 120."""
        candidate = {
            "source_row_id": 102,
            "mpn": "5B-332-120",
            "description": "5B-332-120 Mirka HIOLIT 5 in P120 Grip Disc",
            "e1_brand": "MIRKA",
            "unilog_brand": "MIRKA",
            "dib_brand": "",
            "part_manuf": "Mirka USA",
            "raw_row": {}
        }
        product = processing_service.process_candidate(self.session, candidate)
        attrs = {a.label.upper(): a.normalized_value or a.raw_value for a in product.attributes}

        self.assertNotIn("THREAD SIZE", attrs, "MPN fragment 332-120 must NOT be extracted as THREAD_SIZE")
        self.assertNotIn("VOLTAGE", attrs, "Fragment 120 from MPN/P120 must NOT be extracted as VOLTAGE on abrasive disc")
        self.assertEqual(attrs.get("ABRASIVE GRIT"), "P120")
        self.assertEqual(attrs.get("DISC DIAMETER"), "5")

    def test_03_organizer_does_not_receive_base_type(self):
        """Input: T-90043 Deep Medium Organizer -> Must NOT produce BASE_TYPE = E26 Medium."""
        candidate = {
            "source_row_id": 103,
            "mpn": "T-90043",
            "description": "T-90043 Deep Medium Organizer Storage Box",
            "e1_brand": "MAKITA",
            "unilog_brand": "MAKITA",
            "dib_brand": "",
            "part_manuf": "Makita USA",
            "raw_row": {}
        }
        product = processing_service.process_candidate(self.session, candidate)
        attrs = {a.label.upper(): a.normalized_value or a.raw_value for a in product.attributes}

        self.assertNotIn("BASE TYPE", attrs, "'Medium' in Organizer must NOT produce BASE_TYPE")
        self.assertNotIn("BASE_TYPE", attrs)
        self.assertNotIn("THREAD SIZE", attrs)
        self.assertNotIn("VOLTAGE", attrs)
        self.assertIn("ORGANIZER", attrs.get("PRODUCT TYPE", "").upper())

    def test_04_m18_m12_not_interpreted_as_voltage(self):
        """Input: M18 product references -> Must NOT automatically produce VOLTAGE = 18 V without voltage context."""
        candidate = {
            "source_row_id": 104,
            "mpn": "2719-20",
            "description": "Milwaukee M18 FUEL HACKZALL One-Handed Reciprocating Saw Bare Tool",
            "e1_brand": "MILWAUKEE",
            "unilog_brand": "MILWAUKEE",
            "dib_brand": "",
            "part_manuf": "Milwaukee Tool",
            "raw_row": {}
        }
        product = processing_service.process_candidate(self.session, candidate)
        attrs = {a.label.upper(): a.normalized_value or a.raw_value for a in product.attributes}

        self.assertNotIn("VOLTAGE", attrs, "Platform name M18 must NOT automatically become VOLTAGE without explicit volt context")
        self.assertNotIn("THREAD SIZE", attrs, "M18 must NOT become THREAD_SIZE")

    def test_05_non_electrical_product_does_not_receive_amperage(self):
        """A non-electrical product must NOT receive AMPERAGE."""
        candidate = {
            "source_row_id": 105,
            "mpn": "VLV-100",
            "description": "1 in Stainless Steel Full Port Ball Valve Class 150 Flanged 20 A Grade",
            "e1_brand": "APOLLO",
            "unilog_brand": "APOLLO",
            "dib_brand": "",
            "part_manuf": "Apollo Valves",
            "raw_row": {}
        }
        product = processing_service.process_candidate(self.session, candidate)
        attrs = {a.label.upper(): a.normalized_value or a.raw_value for a in product.attributes}

        self.assertNotIn("AMPERAGE", attrs, "Non-electrical plumbing valve must NOT receive AMPERAGE from '20 A Grade'")
        self.assertEqual(attrs.get("MATERIAL"), "Stainless Steel")
        self.assertEqual(attrs.get("CONNECTION TYPE"), "FLANGED")

    def test_06_unrelated_product_does_not_receive_grit_or_base_type(self):
        """Unrelated product must NOT receive BASE_TYPE or GRIT."""
        candidate = {
            "source_row_id": 106,
            "mpn": "SNIP-10G",
            "description": "Malco Offset Aviation Snips 10G Left Cut",
            "e1_brand": "MALCO",
            "unilog_brand": "MALCO",
            "dib_brand": "",
            "part_manuf": "Malco Products",
            "raw_row": {}
        }
        product = processing_service.process_candidate(self.session, candidate)
        attrs = {a.label.upper(): a.normalized_value or a.raw_value for a in product.attributes}

        self.assertNotIn("GRIT", attrs, "'10G' in snips must NOT become GRIT")
        self.assertNotIn("ABRASIVE GRIT", attrs)
        self.assertNotIn("BASE TYPE", attrs)
        self.assertEqual(attrs.get("CUT DIRECTION"), "Left Cut")

    def test_07_grounded_descriptions_contain_no_unsupported_marketing_claims(self):
        """Descriptions must NOT contain unsupported generic claims like 'Engineered for high-performance industrial reliability'."""
        desc_res, provider = ai_provider_router.generate_descriptions(
            mpn="49-94-0001",
            manufacturer="Milwaukee Tool",
            brand="Milwaukee®",
            noun="Cut Off Disc",
            attributes="[]"
        )
        forbidden_phrases = [
            "engineered for high-performance industrial reliability",
            "engineered for reliability",
            "high-performance",
            "industrial-grade",
            "premium quality",
            "durable",
            "heavy-duty industrial grade",
            "standard commercial voltage & footprint",
            "upgrade your operations with",
            "superior efficiency"
        ]
        combined_text = f"{desc_res.long_desc} {desc_res.retail_desc} {desc_res.marketing_description} {' '.join(desc_res.item_features)}".lower()
        for phrase in forbidden_phrases:
            self.assertNotIn(phrase, combined_text, f"Forbidden marketing phrase '{phrase}' found in description!")

        # Must be grounded in facts
        self.assertIn("milwaukee", desc_res.product_name.lower())
        self.assertIn("cut off disc", desc_res.product_name.lower())
        self.assertIn("49-94-0001", desc_res.long_desc)

    def test_08_existing_valid_fastener_thread_size_still_works(self):
        """Verified fastener thread size (1/4-20) continues to be extracted accurately."""
        candidate = {
            "source_row_id": 108,
            "mpn": "HEX-1420-1",
            "description": "1/4-20 x 1 in Hex Head Cap Screw Stainless Steel 316",
            "e1_brand": "",
            "unilog_brand": "",
            "dib_brand": "",
            "part_manuf": "",
            "raw_row": {}
        }
        product = processing_service.process_candidate(self.session, candidate)
        attrs = {a.label.upper(): a.normalized_value or a.raw_value for a in product.attributes}

        self.assertEqual(attrs.get("THREAD SIZE"), "1/4-20")
        self.assertEqual(attrs.get("MATERIAL"), "Stainless Steel")
        self.assertEqual(attrs.get("FASTENER HEAD STYLE"), "Hex Head")
        self.assertEqual(attrs.get("LENGTH"), "1")

    def test_09_existing_valid_lighting_attributes_still_work(self):
        """Verified lighting specs (Wattage, Voltage, Base Type, Bulb Shape) continue to work."""
        candidate = {
            "source_row_id": 109,
            "mpn": "PHIL-A19-9W",
            "description": "Philips A19 LED Light Bulb 9W 120V E26 Medium Base 2700K",
            "e1_brand": "PHILIPS",
            "unilog_brand": "PHILIPS",
            "dib_brand": "",
            "part_manuf": "Philips Lighting",
            "raw_row": {}
        }
        product = processing_service.process_candidate(self.session, candidate)
        attrs = {a.label.upper(): a.normalized_value or a.raw_value for a in product.attributes}

        self.assertEqual(attrs.get("WATTAGE"), "9")
        self.assertEqual(attrs.get("VOLTAGE"), "120")
        self.assertEqual(attrs.get("BASE TYPE"), "E26 Medium")
        self.assertEqual(attrs.get("BULB SHAPE"), "A19")
        self.assertEqual(attrs.get("COLOR TEMPERATURE"), "2700K")

    def test_10_contextual_natural_voltage_phrasing(self):
        """Natural description 'operates at 120 volts' is correctly extracted."""
        candidate = {
            "source_row_id": 110,
            "mpn": "FAN-52",
            "description": "Hunter 52 in Ceiling Fan with LED Light Kit, operates at 120 volts AC",
            "e1_brand": "HUNTER",
            "unilog_brand": "HUNTER",
            "dib_brand": "",
            "part_manuf": "Hunter Fan Company",
            "raw_row": {}
        }
        product = processing_service.process_candidate(self.session, candidate)
        attrs = {a.label.upper(): a.normalized_value or a.raw_value for a in product.attributes}

        self.assertEqual(attrs.get("VOLTAGE"), "120")

if __name__ == "__main__":
    unittest.main()
