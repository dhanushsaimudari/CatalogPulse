from app.schemas.review import ReviewItemSchema
from app.session.session_models import ProcessingSession
from app.validation.engine import validation_engine
from app.services.quality_service import quality_service
from typing import Optional, List

class ReviewService:
    def _apply_value_to_product(self, product, field: str, new_value: str) -> bool:
        if not field or not new_value:
            return False

        field_norm = field.strip().lower()
        if field_norm in ["brand", "brand_name"]:
            if product.identity and product.identity.brand:
                product.identity.brand.canonical_value = new_value
                product.identity.brand.status = "HUMAN_APPROVED"
                return True
        elif field_norm in ["manufacturer", "manufacturer_name", "part_manuf"]:
            if product.identity and product.identity.manufacturer:
                product.identity.manufacturer.canonical_value = new_value
                product.identity.manufacturer.status = "HUMAN_APPROVED"
                return True
        elif field_norm in ["mfg_part_num", "part_number", "mpn"]:
            if product.identity:
                product.identity.mfg_part_num = new_value
            if product.source_data:
                product.source_data.mfg_part_num = new_value
            return True
        elif field_norm in ["classpath", "category_path"]:
            if product.classification:
                product.classification.classpath = new_value
                parts = [p.strip() for p in new_value.split(">") if p.strip()]
                if len(parts) >= 1:
                    product.classification.department = parts[0]
                if len(parts) >= 2:
                    product.classification.class_name = parts[1]
                if len(parts) >= 3:
                    product.classification.fine_class = parts[2]
                return True
        elif field_norm in ["mobile_desc"]:
            if product.content:
                product.content.mobile_desc = new_value
                return True
        elif field_norm in ["invoice_desc"]:
            if product.content:
                product.content.invoice_desc = new_value
                return True
        elif field_norm in ["short_desc"]:
            if product.content:
                product.content.short_desc = new_value
                return True
        elif field_norm in ["long_desc", "long_desc1"]:
            if product.content:
                product.content.long_desc = new_value
                return True
        elif field_norm in ["retail_desc"]:
            if product.content:
                product.content.retail_desc = new_value
                return True
        elif field_norm in ["marketing_description"]:
            if product.content:
                product.content.marketing_description = new_value
                return True
        elif field_norm in ["product_name"]:
            if product.content:
                product.content.product_name = new_value
                return True
        elif "attribute" in field_norm:
            clean_lbl = field_norm.replace("attribute.", "").replace("attribute_", "").strip().upper()
            for attr in product.attributes:
                if attr.label.strip().upper() == clean_lbl:
                    attr.normalized_value = new_value
                    attr.raw_value = new_value
                    attr.status = "VALID"
                    return True
            # CRITICAL DEMO-SAFETY: NEVER modify another attribute or attributes[0]!
            return False

        return False

    def _sync_product_quality_and_review_state(self, session: ProcessingSession, product) -> None:
        # Revalidate product
        product.validations = validation_engine.validate_product(product)
        # Recalculate quality score
        product.quality = quality_service.calculate_quality(product, product.validations)
        # Recalculate requires_review
        pending_reviews = [
            r for r in session.list_reviews(status=None)
            if r.product_id == product.id and r.status == "PENDING"
        ]
        has_failing_validations = any(v.status == "FAIL" for v in (product.validations or []))
        product.requires_review = bool(pending_reviews or has_failing_validations)
        session.add_product(product)

    def approve_review(self, session: ProcessingSession, review_id: str) -> Optional[ReviewItemSchema]:
        review = session.get_review(review_id)
        if not review:
            return None
        
        product = session.get_product(review.product_id)
        if not product:
            return None

        target_value = review.suggested_value or review.current_value
        applied = False
        if target_value:
            applied = self._apply_value_to_product(product, review.field, target_value)

        if not applied:
            return None

        updated_review = session.update_review_status(review_id, "APPROVED")
        self._sync_product_quality_and_review_state(session, product)

        session.log_event(
            product_id=product.id,
            event_type="HUMAN_APPROVAL",
            description=f"Approved review item '{review.field}' value '{target_value}'.",
            field=review.field,
            old_value=review.current_value,
            new_value=target_value,
            actor="HUMAN_REVIEWER"
        )

        return updated_review

    def reject_review(self, session: ProcessingSession, review_id: str) -> Optional[ReviewItemSchema]:
        review = session.get_review(review_id)
        if not review:
            return None
        
        updated_review = session.update_review_status(review_id, "REJECTED")
        product = session.get_product(review.product_id)
        
        if product:
            self._sync_product_quality_and_review_state(session, product)

            session.log_event(
                product_id=product.id,
                event_type="HUMAN_REJECTION",
                description=f"Rejected suggestion for field '{review.field}'. Kept current value '{review.current_value}'.",
                field=review.field,
                old_value=review.current_value,
                new_value=review.current_value,
                actor="HUMAN_REVIEWER"
            )

        return updated_review

    def autofix_review(self, session: ProcessingSession, review_id: str) -> Optional[ReviewItemSchema]:
        review = session.get_review(review_id)
        if not review:
            return None
        
        product = session.get_product(review.product_id)
        if not product:
            return None

        target_value = review.suggested_value or review.current_value
        applied = False
        if target_value:
            applied = self._apply_value_to_product(product, review.field, target_value)

        if not applied:
            return None

        updated_review = session.update_review_status(review_id, "AUTO_FIXED")
        self._sync_product_quality_and_review_state(session, product)

        session.log_event(
            product_id=product.id,
            event_type="AUTO_FIX_APPLIED",
            description=f"Deterministic auto-fix applied to field '{review.field}'. Updated to '{target_value}'.",
            field=review.field,
            old_value=review.current_value,
            new_value=target_value,
            actor="AUTO_FIX_ENGINE"
        )

        return updated_review

    def edit_review(self, session: ProcessingSession, review_id: str, custom_value: str) -> Optional[ReviewItemSchema]:
        review = session.get_review(review_id)
        if not review:
            return None

        product = session.get_product(review.product_id)
        if not product:
            return None

        applied = self._apply_value_to_product(product, review.field, custom_value)
        if not applied:
            return None

        updated_review = session.update_review_status(review_id, "EDITED")
        review.suggested_value = custom_value
        self._sync_product_quality_and_review_state(session, product)

        session.log_event(
            product_id=product.id,
            event_type="HUMAN_EDIT",
            description=f"Reviewer manually edited field '{review.field}' to '{custom_value}'.",
            field=review.field,
            old_value=review.current_value,
            new_value=custom_value,
            actor="HUMAN_REVIEWER"
        )

        return updated_review

    def bulk_fix_reviews(
        self,
        session: ProcessingSession,
        review_ids: Optional[List[str]] = None,
        fix_all: bool = False
    ) -> dict:
        """
        Supervisor-level bulk review action.
        Fixes selected review items or all eligible review items with valid suggestions.
        Does not automatically apply uncertain changes that are not eligible.
        Updates product fields, audit trails, recalculates product quality, and preserves unresolved items.
        """
        all_pending = session.list_reviews(status="PENDING")
        applied_count = 0
        failed_count = 0
        applied_results = []
        affected_product_ids = set()

        if fix_all:
            eligible_reviews = [
                r for r in all_pending
                if r.suggested_value and str(r.suggested_value).strip() not in ["", "REQUIRED"]
            ]
            selected_count = len(eligible_reviews)
            for rev in eligible_reviews:
                try:
                    res = self.autofix_review(session, rev.review_id)
                    if res:
                        applied_count += 1
                        applied_results.append(res.model_dump())
                        affected_product_ids.add(rev.product_id)
                    else:
                        failed_count += 1
                except Exception:
                    failed_count += 1

        elif review_ids:
            target_set = set(review_ids)
            selected_count = len(review_ids)
            pending_by_id = {r.review_id: r for r in all_pending if r.review_id in target_set}
            missing_ids_count = len(target_set - set(pending_by_id.keys()))
            failed_count += missing_ids_count

            eligible_reviews = list(pending_by_id.values())
            for rev in eligible_reviews:
                try:
                    res = self.autofix_review(session, rev.review_id)
                    if res:
                        applied_count += 1
                        applied_results.append(res.model_dump())
                        affected_product_ids.add(rev.product_id)
                    else:
                        failed_count += 1
                except Exception:
                    failed_count += 1
        else:
            eligible_reviews = []
            selected_count = 0

        if applied_count > 0:
            from app.evaluation.evaluator import evaluator_engine
            eval_res = evaluator_engine.run_benchmark_evaluation(session)
            session.evaluation = eval_res

        remaining_pending = len(session.list_reviews(status="PENDING"))

        return {
            "status": "COMPLETED",
            "selected_count": selected_count,
            "eligible_count": len(eligible_reviews),
            "applied_count": applied_count,
            "failed_count": failed_count,
            "remaining_pending": remaining_pending,
            "affected_products_count": len(affected_product_ids)
        }

review_service = ReviewService()
