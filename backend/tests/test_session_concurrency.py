import unittest
import os
import sys
import threading
import tempfile
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.session.session_models import ProcessingSession
from app.session.session_manager import session_manager
from app.schemas.product import (
    ProductSchema, SourceDataSchema, ProductIdentitySchema, ValueMatchSchema,
    ClassificationDataSchema, ProductContentSchema, QualityScoreSchema, ComponentScoreSchema
)
from app.schemas.review import ReviewItemSchema

class TestSessionConcurrencyAndCleanup(unittest.TestCase):
    def test_concurrent_session_operations(self):
        """Spawns multiple threads reading and writing to the same session simultaneously."""
        session = ProcessingSession(session_id="CONCURRENCY_TEST_SESSION")
        num_threads = 8
        items_per_thread = 25
        errors = []

        dummy_quality = QualityScoreSchema(
            overall_score=88.0,
            status="PASS",
            sub_scores=ComponentScoreSchema(brand_normalization=90.0, classification=90.0, attributes=85.0, descriptions=85.0, digital_assets=90.0, evidence=90.0),
            breakdown_notes=[]
        )

        def worker(thread_idx: int):
            try:
                for i in range(items_per_thread):
                    prod_id = f"PROD_{thread_idx}_{i}"
                    p = ProductSchema(
                        id=prod_id,
                        session_id=session.session_id,
                        source_row_id=thread_idx * 100 + i,
                        source_data=SourceDataSchema(mfg_part_num=f"MPN-{thread_idx}-{i}", part_desc="Desc", e1_brand="B", unilog_brand="B", dib_brand="B", part_manuf="M"),
                        identity=ProductIdentitySchema(
                            mfg_part_num=f"MPN-{thread_idx}-{i}",
                            manufacturer=ValueMatchSchema(raw_value="M", canonical_value="M", confidence=1.0, status="MATCHED"),
                            brand=ValueMatchSchema(raw_value="B", canonical_value="B®", confidence=1.0, status="MATCHED")
                        ),
                        classification=ClassificationDataSchema(department="Dep", class_name="Cls", fine_class="Fn", classpath="Dep>Cls>Fn", confidence=1.0, reason="Test"),
                        content=ProductContentSchema(product_name=f"Name {thread_idx} {i}", mobile_desc="M", invoice_desc="INV", short_desc="S", long_desc="L", retail_desc="R", marketing_description="M"),
                        attributes=[],
                        quality=dummy_quality,
                        validations=[],
                        created_at="2026-08-17T00:00:00Z",
                        updated_at="2026-08-17T00:00:00Z"
                    )
                    session.add_product(p)

                    # Interleaved review addition and status update
                    rev_id = f"REV_{thread_idx}_{i}"
                    rev = ReviewItemSchema(
                        review_id=rev_id,
                        product_id=prod_id,
                        mfg_part_num=f"MPN-{thread_idx}-{i}",
                        issue_type="BRAND_MISSING_TRADEMARK",
                        field="brand",
                        current_value="B",
                        suggested_value="B®",
                        reason="Trademark missing",
                        severity="WARNING",
                        status="PENDING",
                        created_at="2026-08-17T00:00:00Z"
                    )
                    session.add_review(rev)
                    session.update_review_status(rev_id, "APPROVED" if i % 2 == 0 else "REJECTED")

                    # Interleaved audit logging and counter tracking
                    session.log_event(product_id=prod_id, event_type="TEST_EVENT", description="Concurrent write")
                    session.record_ai_call()
                    session.record_local_decision()

                    # Interleaved reads and analytics calculations
                    _ = session.get_product(prod_id)
                    _ = session.list_products(skip=0, limit=10)
                    _ = session.calculate_analytics()

            except Exception as e:
                errors.append(f"Thread {thread_idx} failed: {e}")

        threads = [threading.Thread(target=worker, args=(t,)) for t in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0, f"Encountered concurrency errors: {errors}")
        total_expected = num_threads * items_per_thread
        self.assertEqual(len(session.products), total_expected)
        self.assertEqual(len(session.reviews), total_expected)
        self.assertEqual(len(session.audit_events), total_expected)
        self.assertEqual(session.ai_requests_count, total_expected)
        self.assertEqual(session.local_decisions_count, total_expected)

        # Final analytics calculation should be accurate
        analytics = session.calculate_analytics()
        self.assertEqual(analytics["total_products_processed"], total_expected)

    def test_session_cleanup_removes_temporary_files(self):
        """Verifies temporary files registered in session are cleaned up on session deletion."""
        mgr = session_manager
        session = mgr.create_session("CLEANUP_TEST_SESSION")

        # Create temporary files
        temp_fd1, temp_path1 = tempfile.mkstemp(prefix="sortolog_test1_", suffix=".tmp")
        os.close(temp_fd1)
        temp_fd2, temp_path2 = tempfile.mkstemp(prefix="sortolog_test2_", suffix=".tmp")
        os.close(temp_fd2)

        session.add_temporary_file(temp_path1)
        session.add_temporary_file(temp_path2)

        self.assertTrue(os.path.exists(temp_path1))
        self.assertTrue(os.path.exists(temp_path2))

        # Delete session
        deleted = mgr.delete_session(session.session_id)
        self.assertTrue(deleted)

        # Temporary files must be removed from disk
        self.assertFalse(os.path.exists(temp_path1), "temp_path1 was not removed upon session deletion")
        self.assertFalse(os.path.exists(temp_path2), "temp_path2 was not removed upon session deletion")

if __name__ == "__main__":
    unittest.main()
