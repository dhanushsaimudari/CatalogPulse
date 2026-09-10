import sys
import os
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.ingestion_service import ingestion_service
from app.services.processing_service import processing_service
from app.services.export_service import export_service
from app.evaluation.evaluator import evaluator_engine
from app.session.session_manager import session_manager

class TestBenchmark1000Integrity(unittest.TestCase):
    def test_actual_benchmark_1000_row_integrity(self):
        benchmark_path = os.path.join(
            os.path.dirname(__file__), "..", "storage_data", "inputs", "import-2fe6606a_Unihack_ Sample Dataset - Input.csv"
        )
        if not os.path.exists(benchmark_path):
            self.skipTest("Benchmark CSV file not present")

        with open(benchmark_path, "rb") as f:
            content_bytes = f.read()

        import_id, total_rows, candidates = ingestion_service.process_import(
            "Unihack_ Sample Dataset - Input.csv", content_bytes
        )
        self.assertEqual(total_rows, 1000, "Expected input to parse exactly 1000 rows")
        self.assertEqual(len(candidates), 1000, "Expected candidates to contain exactly 1000 items")

        # Test collision handling: find the duplicates in candidates
        mpn_counts = {}
        for c in candidates:
            m = c.get("mpn")
            mpn_counts[m] = mpn_counts.get(m, 0) + 1
        duplicates = [m for m, cnt in mpn_counts.items() if cnt > 1]
        self.assertIn("AVM6EV", duplicates, "AVM6EV should be duplicate MPN in benchmark")

        # Test processing a slice containing duplicate rows to verify no collision overwrites
        dupe_candidates = [c for c in candidates if c.get("mpn") == "AVM6EV"]
        self.assertEqual(len(dupe_candidates), 2, "Expected 2 occurrences of AVM6EV")

        session = session_manager.create_session("dupe-test-sess", seed_demo=False)
        p1 = processing_service.process_candidate(session, dupe_candidates[0])
        p2 = processing_service.process_candidate(session, dupe_candidates[1])

        self.assertEqual(len(session.products), 2, "Both duplicate MPN rows must be preserved in session")
        self.assertNotEqual(p1.id, p2.id, "Duplicate MPN rows must receive distinct collision-free IDs")

        # Run evaluation on session with duplicates
        eval_report = evaluator_engine.run_benchmark_evaluation(session=session)
        self.assertEqual(eval_report.total_evaluated, 2, "Evaluator must evaluate all session products")

        # Run 252-col export and clean export
        csv_252 = export_service.export_products_to_csv(list(session.products.values()))
        lines_252 = [line for line in csv_252.strip().split("\n") if line.strip()]
        self.assertEqual(len(lines_252), 3, "Header + 2 data rows expected in 252-col export")

        csv_clean = export_service.export_clean_intelligence_csv(list(session.products.values()))
        lines_clean = [line for line in csv_clean.strip().split("\n") if line.strip()]
        self.assertEqual(len(lines_clean), 3, "Header + 2 data rows expected in clean export")

if __name__ == "__main__":
    unittest.main()
