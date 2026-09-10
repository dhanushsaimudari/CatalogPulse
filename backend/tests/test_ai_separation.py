import unittest
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.ai.watsonx_parser import parse_watsonx_json, WatsonxParsingError
from app.ai.response_parser import parse_json_response

class TestAIProviderSeparation(unittest.TestCase):
    def test_01_watsonx_parser_extracts_markdown_json(self):
        sample = '```json\n{"department": "Tools", "class_name": "Hand Tools", "fine_class": "Pliers", "confidence": 0.92}\n```'
        res = parse_watsonx_json(sample)
        self.assertEqual(res["department"], "Tools")
        self.assertEqual(res["confidence"], 0.92)

    def test_02_watsonx_parser_repairs_trailing_comma(self):
        sample = '{\n  "department": "Abrasives",\n  "class_name": "Discs",\n}'
        res = parse_watsonx_json(sample)
        self.assertEqual(res["department"], "Abrasives")
        self.assertEqual(res["class_name"], "Discs")

    def test_03_watsonx_parser_does_not_reference_gemini_on_error(self):
        try:
            parse_watsonx_json("This is purely non-json text that cannot be parsed.")
            self.fail("Expected WatsonxParsingError")
        except WatsonxParsingError as e:
            self.assertNotIn("Gemini", str(e), "Watsonx parser error must NEVER mention Gemini")
            self.assertIn("watsonx", str(e).lower())

if __name__ == "__main__":
    unittest.main()
