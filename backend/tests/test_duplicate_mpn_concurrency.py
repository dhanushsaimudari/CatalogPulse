import sys
import os
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.session.session_manager import session_manager
from app.services.processing_service import processing_service
from app.services.ingestion_service import ingestion_service

class TestDuplicateMpnConcurrency(unittest.TestCase):
    def test_concurrent_duplicate_mpn_batch_processing(self):
        """
        Verify that processing a batch of identical MPNs concurrently
        produces distinct products for all rows with zero data loss or collisions.
        """
        session = session_manager.create_session("test-dupe-concurrency", seed_demo=False)
        duplicate_mpn = "AVM6EV"
        total_duplicates = 20

        candidates = [
            {
                "source_row_id": i,
                "mpn": duplicate_mpn,
                "description": f"Micro Switch Premium Basic Switch Unit #{i}",
                "part_manuf": "Honeywell Sensing & Control",
                "unilog_brand": "Honeywell",
                "raw_row": {"Row_Num": str(i), "Mfg_Part_Num": duplicate_mpn}
            }
            for i in range(1, total_duplicates + 1)
        ]

        processed_products = processing_service.process_candidates_batch(
            session=session,
            candidates=candidates,
            max_workers=10
        )

        # 1. Total processed products must match total input rows exactly
        self.assertEqual(len(processed_products), total_duplicates, "Every candidate row must be processed and returned")
        self.assertEqual(len(session.products), total_duplicates, "Session must contain all duplicate rows without overwrites")

        # 2. All product IDs must be unique
        product_ids = [p.id for p in processed_products]
        self.assertEqual(len(set(product_ids)), total_duplicates, "All assigned product IDs must be distinct and collision-free")

        # 3. All MPN values must remain unchanged
        for prod in processed_products:
            self.assertEqual(prod.identity.mfg_part_num, duplicate_mpn, "MPN must be preserved exactly as input")

    def test_actual_benchmark_1000_row_count_integrity(self):
        """
        Verify that the official 1,000-row benchmark dataset (which contains duplicate MPNs)
        processes all 1,000 rows into exactly 1,000 session products with zero collisions.
        """
        benchmark_path = os.path.join(
            os.path.dirname(__file__), "..", "storage_data", "inputs", "import-2fe6606a_Unihack_ Sample Dataset - Input.csv"
        )
        if not os.path.exists(benchmark_path):
            self.skipTest("Benchmark CSV file not present in storage_data/inputs")

        with open(benchmark_path, "rb") as f:
            content_bytes = f.read()

        _, total_rows, candidates = ingestion_service.process_import(
            "Unihack_ Sample Dataset - Input.csv", content_bytes
        )
        self.assertEqual(total_rows, 1000)
        self.assertEqual(len(candidates), 1000)

        session = session_manager.create_session("benchmark-1000-full-sess", seed_demo=False)
        processed = processing_service.process_candidates_batch(
            session=session,
            candidates=candidates,
            max_workers=10
        )

        self.assertEqual(len(processed), 1000, "Expected all 1,000 candidates to be returned from batch processing")
        self.assertEqual(len(session.products), 1000, "Expected exactly 1,000 products preserved in session")
        self.assertEqual(len(set(p.id for p in session.products.values())), 1000, "All 1,000 product IDs must be unique")

if __name__ == "__main__":
    unittest.main()
