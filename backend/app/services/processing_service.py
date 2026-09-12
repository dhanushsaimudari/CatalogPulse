from app.schemas.product import (
    ProductSchema, SourceDataSchema, ProductIdentitySchema, ValueMatchSchema,
    ClassificationDataSchema, ProductContentSchema, ProductAttributeSchema
)
from app.schemas.attributes import ExplanationSchema
from app.ai.ai_provider_router import ai_provider_router
from app.ai.semantic_decision_service import semantic_decision_service
from app.services.local_cleaner import local_cleaner
from app.validation.engine import validation_engine
from app.validation.auto_fix import auto_fix_service
from app.services.quality_service import quality_service
from app.schemas.review import ReviewItemSchema
from app.session.session_models import ProcessingSession
from typing import Dict, Any, Optional, List, Callable
import uuid
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from app.core.logging import logger
import re

class ProcessingService:
    def process_candidate(
        self,
        session: ProcessingSession,
        candidate: Dict[str, Any],
        progress_callback: Optional[Callable[[str, int], None]] = None,
    ) -> ProductSchema:
        def report(stage: str, progress: int) -> None:
            if progress_callback:
                progress_callback(stage, progress)

        row_id = candidate.get("source_row_id", 1)
        mpn = candidate.get("mpn", "")
        raw_desc = candidate.get("description", "")
        raw_mfr = candidate.get("part_manuf", "")
        e1_b = candidate.get("e1_brand", "")
        unilog_b = candidate.get("unilog_brand", "")
        dib_b = candidate.get("dib_brand", "")
        raw_brand_str = unilog_b or dib_b or e1_b or ""

        safe_mpn_slug = re.sub(r'[^a-zA-Z0-9_-]', '_', mpn.strip().lower()) if mpn else ""
        base_id = f"prod-{safe_mpn_slug}" if safe_mpn_slug else f"prod-row-{row_id}"
        if session and hasattr(session, "allocate_product_id"):
            product_id = session.allocate_product_id(base_id, row_id=row_id)
        elif session and hasattr(session, "products") and base_id in session.products:
            product_id = f"{base_id}-{row_id if row_id is not None else uuid.uuid4().hex[:8]}"
        else:
            product_id = base_id

        # 1. Local Master Normalization
        report("MANUFACTURER_BRAND", 10)
        canonical_mfr, mfr_status, mfr_conf = local_cleaner.resolve_manufacturer(raw_mfr, desc=raw_desc, mpn=mpn)
        canonical_brand, brand_status, brand_conf = local_cleaner.resolve_brand(
            raw_brand_str, desc=raw_desc, mfr=canonical_mfr, mpn=mpn
        )

        session.log_event(
            product_id=product_id,
            event_type="INGESTED",
            description=f"Raw item ingested from source row {row_id} (MPN: '{mpn}').",
            actor="INGESTION_SERVICE"
        )
        if raw_brand_str and canonical_brand != raw_brand_str:
            session.log_event(
                product_id=product_id,
                event_type="BRAND_NORMALIZED",
                field="brand",
                old_value=raw_brand_str,
                new_value=canonical_brand,
                description=f"Normalized brand from '{raw_brand_str}' to canonical '{canonical_brand}'.",
                actor="LOCAL_CLEANER"
            )
        if raw_mfr and canonical_mfr != raw_mfr:
            session.log_event(
                product_id=product_id,
                event_type="MANUFACTURER_NORMALIZED",
                field="manufacturer",
                old_value=raw_mfr,
                new_value=canonical_mfr,
                description=f"Normalized manufacturer from '{raw_mfr}' to canonical '{canonical_mfr}'.",
                actor="LOCAL_CLEANER"
            )

        # 2. Semantic Uncertainty Gate
        should_call_ai, gate_reason, local_ctx = semantic_decision_service.evaluate_enrichment_need(
            mpn, raw_desc, raw_mfr, raw_brand_str
        )

        # 3. Taxonomy Classification (Local vs AI)
        report("CLASSIFYING", 25)
        if should_call_ai:
            class_res, provider_used = ai_provider_router.classify_product(
                mpn, raw_desc, canonical_mfr, canonical_brand, session=session
            )
            classification = ClassificationDataSchema(
                department=class_res.department,
                class_name=class_res.class_name,
                fine_class=class_res.fine_class,
                classpath=class_res.classpath,
                confidence=class_res.confidence,
                reason=f"{class_res.reason} (Provider: {provider_used})"
            )
        else:
            session.record_local_decision()
            class_res, _ = ai_provider_router.classify_product(mpn, raw_desc, canonical_mfr, canonical_brand, session=None)
            classification = ClassificationDataSchema(
                department=class_res.department,
                class_name=class_res.class_name,
                fine_class=class_res.fine_class,
                classpath=class_res.classpath,
                confidence=class_res.confidence,
                reason=f"Local deterministic intelligence ({gate_reason})"
            )

        # 4. Attributes & LOV Enrichment
        report("AI_ENRICHMENT", 45)
        sample_attributes: List[ProductAttributeSchema] = []
        if should_call_ai:
            extracted_raw, _ = ai_provider_router.extract_attributes(
                mpn, raw_desc, classification.classpath, session=session
            )
            for item in extracted_raw:
                lbl_upper = item.label.strip().upper()
                # Exclude identity fields that must never be in attributes[]
                if lbl_upper in ["MANUFACTURER PART NUMBER", "PRIMARY BRAND", "MANUFACTURER", "BRAND", "MPN", "SKU"]:
                    continue
                # Precision Gate: Contextual evidence & product category relevance
                if not self.is_attribute_valid_and_grounded(
                    item.label, item.raw_value, item.normalized_value, raw_desc, mpn, classification
                ):
                    continue
                sample_attributes.append(
                    ProductAttributeSchema(
                        sequence=len(sample_attributes) + 1,
                        label=item.label,
                        raw_value=item.raw_value,
                        normalized_value=item.normalized_value,
                        uom=local_cleaner.normalize_uom(item.uom) if item.uom else "",
                        status="VALID" if item.raw_value else "NEEDS_REVIEW",
                        lov_matched=bool(item.raw_value),
                        explanation=ExplanationSchema(
                            raw_source=f"{mpn} Specifications",
                            ai_interpretation=f"Extracted {item.label} value",
                            lov_status=f"LOV Matched ({item.normalized_value})" if item.raw_value else "Unmatched",
                            uom_status=f"UOM Standard ({item.uom})" if item.uom else "N/A",
                            validation_result="PASS" if item.raw_value else "REVIEW"
                        )
                    )
                )

        # Dynamic attribute discovery from product evidence (no universal hardcoded list, no MPN/Brand)
        raw_row_data = candidate.get("raw_row", {})
        discovered_attrs = self.discover_dynamic_attributes(
            mpn, raw_desc, classification, canonical_mfr, canonical_brand, raw_row=raw_row_data
        )
        existing_labels = {a.label.strip().upper() for a in sample_attributes}
        for da in discovered_attrs:
            if da.label.strip().upper() not in existing_labels:
                if self.is_attribute_valid_and_grounded(
                    da.label, da.raw_value, da.normalized_value, raw_desc, mpn, classification
                ):
                    da.sequence = len(sample_attributes) + 1
                    sample_attributes.append(da)
                    existing_labels.add(da.label.strip().upper())

        # 5. Content & Description Generation
        report("DESCRIPTION", 65)
        noun = classification.fine_class.split(" ")[-1]
        desc_res, desc_provider = ai_provider_router.generate_descriptions(
            mpn, canonical_mfr, canonical_brand, noun, str(sample_attributes), session=session if should_call_ai else None
        )
        content = ProductContentSchema(
            product_name=desc_res.product_name,
            mobile_desc=desc_res.mobile_desc[:35] if desc_res.mobile_desc else "",
            invoice_desc=(desc_res.invoice_desc[:30] if desc_res.invoice_desc else "").upper(),
            short_desc=desc_res.short_desc[:50] if desc_res.short_desc else "",
            long_desc=desc_res.long_desc[:800] if desc_res.long_desc else "",
            retail_desc=desc_res.retail_desc[:150] if desc_res.retail_desc else "",
            marketing_description=desc_res.marketing_description[:2000] if desc_res.marketing_description else "",
            item_features=desc_res.item_features or []
        )

        now_iso = datetime.now(timezone.utc).isoformat()

        # Build Candidate Schema
        product = ProductSchema(
            id=product_id,
            source_row_id=row_id,
            source_data=SourceDataSchema(
                mfg_part_num=mpn,
                part_desc=raw_desc,
                e1_brand=e1_b,
                unilog_brand=unilog_b,
                dib_brand=dib_b,
                part_manuf=raw_mfr,
                raw_columns=raw_row_data
            ),
            identity=ProductIdentitySchema(
                mfg_part_num=mpn,
                manufacturer=ValueMatchSchema(raw_value=raw_mfr, canonical_value=canonical_mfr, confidence=mfr_conf, status=mfr_status),
                brand=ValueMatchSchema(raw_value=raw_brand_str, canonical_value=canonical_brand, confidence=brand_conf, status=brand_status)
            ),
            classification=classification,
            content=content,
            attributes=sample_attributes,
            quality=quality_service.calculate_quality(
                ProductSchema.model_construct(
                    id=product_id, source_row_id=row_id,
                    source_data=SourceDataSchema(mfg_part_num=mpn, part_desc=raw_desc, e1_brand="", unilog_brand="", dib_brand="", part_manuf=raw_mfr),
                    identity=ProductIdentitySchema(mfg_part_num=mpn, manufacturer=ValueMatchSchema(raw_value=raw_mfr, canonical_value=canonical_mfr, confidence=0.98, status="MATCHED"), brand=ValueMatchSchema(raw_value=raw_brand_str, canonical_value=canonical_brand, confidence=0.95, status="MATCHED")),
                    classification=classification, content=content, quality=None, validations=[], created_at="", updated_at=""
                ),
                []
            ),

            created_at=now_iso,
            updated_at=now_iso
        )

        # 6. Validation
        report("VALIDATING", 80)
        validations = validation_engine.validate_product(product)
        product.validations = validations
        for v in validations:
            if v.status == "FAIL":
                session.log_event(
                    product_id=product.id,
                    event_type="VALIDATION_FAILED",
                    field=v.target_field,
                    description=f"Validation failed for rule {v.rule_id}: {v.message}",
                    actor="VALIDATION_ENGINE"
                )

        # 7. Auto-Fix
        product, fixes_applied = auto_fix_service.apply_auto_fixes(product)
        if fixes_applied > 0:
            product.validations = validation_engine.validate_product(product)
            session.log_event(
                product_id=product.id,
                event_type="AUTO_FIX_APPLIED",
                description=f"Applied {fixes_applied} deterministic auto-fixes to product {product.id}.",
                actor="AUTO_FIX_ENGINE"
            )

        # 8. Final Quality Score
        product.quality = quality_service.calculate_quality(product, product.validations)

        # 9. Review Routing
        report("QUALITY_REVIEW", 95)
        has_failed_validation = any(v.status == "FAIL" for v in product.validations)
        is_unknown_class = product.classification.fine_class == "UNKNOWN" or product.classification.confidence < 0.80
        is_low_quality = product.quality.status in ["NEEDS_REVIEW", "CRITICAL"] or product.quality.overall_score < 80.0

        if has_failed_validation or is_unknown_class or is_low_quality:
            product.requires_review = True
            reviews_added = 0
            for v in product.validations:
                if v.severity in ["WARNING", "ERROR", "CRITICAL"] and v.status == "FAIL":
                    review_item = ReviewItemSchema(
                        review_id=f"rev-{uuid.uuid4().hex[:8]}",
                        product_id=product.id,
                        mfg_part_num=product.identity.mfg_part_num,
                        product_name=product.content.product_name,
                        field=v.target_field,
                        field_name=v.target_field,
                        issue_type=v.rule_id,
                        severity=v.severity,
                        current_value=str(v.current_value or ""),
                        suggested_value=str(v.expected_value or ""),
                        reason=v.message,
                        quality_score=product.quality.overall_score,
                        status="PENDING",
                        created_at=now_iso
                    )
                    session.add_review(review_item)
                    reviews_added += 1

            # Fallback: if requires_review is True, never allow an empty review queue
            if reviews_added == 0:
                if is_unknown_class:
                    session.add_review(ReviewItemSchema(
                        review_id=f"rev-{uuid.uuid4().hex[:8]}",
                        product_id=product.id,
                        mfg_part_num=product.identity.mfg_part_num,
                        product_name=product.content.product_name,
                        field="classpath",
                        field_name="classpath",
                        issue_type="R-TAX-001",
                        severity="WARNING",
                        current_value=product.classification.classpath,
                        suggested_value="General Industrial>Hardware & Supplies>Components",
                        reason=f"Taxonomy classification uncertain (fine class: {product.classification.fine_class}, confidence: {product.classification.confidence:.2f}).",
                        quality_score=product.quality.overall_score,
                        status="PENDING",
                        created_at=now_iso
                    ))
                elif is_low_quality:
                    session.add_review(ReviewItemSchema(
                        review_id=f"rev-{uuid.uuid4().hex[:8]}",
                        product_id=product.id,
                        mfg_part_num=product.identity.mfg_part_num,
                        product_name=product.content.product_name,
                        field="quality_score",
                        field_name="quality_score",
                        issue_type="R-QUAL-001",
                        severity="WARNING",
                        current_value=str(product.quality.overall_score),
                        suggested_value="85.0",
                        reason=f"Overall quality score ({product.quality.overall_score}) is below standard threshold.",
                        quality_score=product.quality.overall_score,
                        status="PENDING",
                        created_at=now_iso
                    ))
                elif not product.identity.mfg_part_num:
                    session.add_review(ReviewItemSchema(
                        review_id=f"rev-{uuid.uuid4().hex[:8]}",
                        product_id=product.id,
                        mfg_part_num=product.identity.mfg_part_num or "UNKNOWN",
                        product_name=product.content.product_name,
                        field="mfg_part_num",
                        field_name="mfg_part_num",
                        issue_type="R-MPN-001",
                        severity="CRITICAL",
                        current_value="",
                        suggested_value="REQUIRED",
                        reason="Manufacturer part number is missing.",
                        quality_score=product.quality.overall_score,
                        status="PENDING",
                        created_at=now_iso
                    ))
        else:
            product.requires_review = False

        # Save to In-Memory Session
        session.add_product(product)
        session.log_event(
            product_id=product.id,
            event_type="ENRICHMENT_COMPLETE",
            description=f"Enriched product {product.id} with overall quality score {product.quality.overall_score}/100."
        )

        return product

    def is_attribute_valid_and_grounded(
        self,
        label: str,
        raw_val: str,
        norm_val: str,
        desc: str,
        mpn: str,
        classification: Optional[ClassificationDataSchema] = None
    ) -> bool:
        """
        Precision gate: Validates that candidate dynamic attributes are:
        1. Fully supported and contextually grounded in source evidence (CONTEXT > REGEX).
        2. Relevant to the specific product category (product-type-aware extraction).
        3. NOT an arbitrary MPN fragment, platform code (e.g. M18, M12), or ungrounded number.
        4. Prefer missing over incorrect: if unsupported or doubtful, discard.
        """
        if not label or not raw_val or not str(raw_val).strip():
            return False
        
        lbl_upper = label.strip().upper()
        raw_upper = str(raw_val).strip().upper()
        norm_upper = str(norm_val).strip().upper() if norm_val else raw_upper
        desc_upper = (desc or "").upper()
        mpn_upper = (mpn or "").strip().upper()
        classpath = classification.classpath.upper() if classification and classification.classpath else ""
        fine_class = classification.fine_class.upper() if classification and classification.fine_class else ""
        class_corpus = f"{classpath} {fine_class}"

        # 1. Reject identity fields that must never be attributes
        if lbl_upper in ["MANUFACTURER PART NUMBER", "PRIMARY BRAND", "MANUFACTURER", "BRAND", "MPN", "SKU"]:
            return False

        # 2. Reject placeholder / null / ungrounded values
        if raw_upper in ["UNKNOWN", "N/A", "NONE", "NULL", "UNCLASSIFIED", "--", "-", "N / A"]:
            return False

        # 3. MPN token protection: extract tokens from MPN
        mpn_tokens = set()
        if mpn_upper:
            mpn_tokens.add(mpn_upper)
            parts = [p for p in re.split(r'[-/._\s]+', mpn_upper) if p]
            for p in parts:
                if len(p) >= 2:
                    mpn_tokens.add(p)
            for i in range(len(parts) - 1):
                mpn_tokens.add(f"{parts[i]}-{parts[i+1]}")
                mpn_tokens.add(f"{parts[i]}/{parts[i+1]}")

        # 4. Domain / Category detection
        is_abrasive = any(k in class_corpus or k in desc_upper for k in [
            "ABRASIVE", "DISC", "WHEEL", "CUT-OFF", "CUT OFF", "GRIND", "SANDING", "FILM DISC", "FLAP DISC", "HIOLIT", "ABRANET", "STIKIT"
        ])
        is_lighting = any(k in class_corpus or k in desc_upper for k in [
            "LIGHTING", "BULB", "LAMP", "LUMINAIRE", "FLOODLIGHT", "LED BULB", "A19", "BR30", "PAR38"
        ])
        is_fastener = any(k in class_corpus or k in desc_upper for k in [
            "FASTENER", "SCREW", "BOLT", "NUT", "WASHER", "CAP SCREW", "HEX BOLT", "MACHINE SCREW", "WOOD SCREW"
        ])
        is_organizer = any(k in class_corpus or k in desc_upper for k in [
            "ORGANIZER", "STORAGE", "BOX", "BIN", "CABINET", "TOTE", "CASE", "CHEST", "DRAWER", "LUMBER", "DECKING"
        ])
        is_tool = any(k in class_corpus or k in desc_upper for k in [
            "TOOL", "SNIP", "SNIPS", "CRIMPER", "PLIERS", "CUTTER", "WRENCH", "SHEARS", "DRILL", "SAW", "HACKZALL"
        ])
        is_electrical = is_lighting or any(k in class_corpus or k in desc_upper for k in [
            "ELECTRICAL", "BREAKER", "SWITCH", "RECEPTACLE", "OUTLET", "WIRE", "CABLE", "CONTACTOR", "RELAY", "FUSE",
            "MOTOR", "THERMOSTAT", "HEAT PUMP", "WATT", "VOLT", "VAC", "VDC", "AMPERAGE", "AMP", "POWERED", "ELECTRIC"
        ])

        # 5. Attribute-specific contextual validation

        # THREAD_SIZE
        if lbl_upper in ["THREAD SIZE", "THREAD_SIZE", "THREAD"]:
            # Never on abrasives, cut-off wheels, or organizers
            if is_abrasive or is_organizer:
                return False
            # If it's an MPN fragment, absolutely reject
            if raw_upper in mpn_tokens or norm_upper in mpn_tokens:
                return False
            # Must have thread context or verified fastener thread pattern
            has_thread_ctx = any(k in desc_upper for k in ["THREAD", "THREADED", "THREADS", "NPT", "UNC", "UNF", "TPI", "PITCH"])
            is_valid_fastener_pattern = bool(
                re.search(r'\b(?:\d+/\d+-\d+|#(?:[0-9]|1[0-2])-\d{2}|[0-9]{1,2}-\d{2})\b', raw_upper) or
                re.search(r'\bM\d+\s*[xX]\s*\d+\b', raw_upper)
            )
            if not (has_thread_ctx or (is_fastener and is_valid_fastener_pattern)):
                return False
            # Arbitrary numbers like 49-94 or 332-120 must fail
            if re.match(r'^\d{2,}-\d{2,}$', raw_upper):
                parts = raw_upper.split("-")
                gauge = int(parts[0]) if parts[0].isdigit() else -1
                if gauge > 12:
                    return False
            # Bare platform numbers like M18, M12 are not thread sizes
            if re.match(r'^M(?:12|18|28|36)$', raw_upper):
                if not any(k in desc_upper for k in ["THREAD", "PITCH"]):
                    return False

        # BASE_TYPE
        if lbl_upper in ["BASE TYPE", "BASE_TYPE", "LAMP BASE", "SOCKET BASE"]:
            if is_organizer or is_abrasive or is_tool or not (is_lighting or "BASE" in desc_upper or "SOCKET" in desc_upper):
                return False
            if "MEDIUM" in raw_upper and not any(k in desc_upper for k in ["MED BASE", "MEDIUM BASE", "E26", "BASE: MEDIUM", "LAMP", "BULB"]):
                return False

        # VOLTAGE
        if lbl_upper in ["VOLTAGE", "OPERATING VOLTAGE", "NOMINAL VOLTAGE"]:
            if (is_abrasive or is_organizer or is_fastener) and not is_electrical:
                return False
            # Bare M18 / M12 or MPN fragments are NOT voltage
            if raw_upper in mpn_tokens or norm_upper in mpn_tokens:
                desc_no_mpn = desc_upper.replace(mpn_upper, " ")
                if not re.search(r'\b' + re.escape(raw_upper) + r'\s*(?:V|VOLTS?|VAC|VDC)\b', desc_no_mpn):
                    return False
            has_volt_ctx = any(k in desc_upper for k in ["VOLT", "VOLTS", "VAC", "VDC", "VOLTAGE", "OPERATES AT"]) or re.search(r'\b\d+\s*V\b', desc_upper)
            if not has_volt_ctx:
                return False

        # AMPERAGE
        if lbl_upper in ["AMPERAGE", "CURRENT", "RATED CURRENT", "AMPS"]:
            if (is_abrasive or is_organizer or is_fastener) and not is_electrical:
                return False
            if raw_upper in mpn_tokens or norm_upper in mpn_tokens:
                return False
            has_amp_ctx = any(k in desc_upper for k in ["AMP", "AMPS", "AMPERAGE", "CURRENT"]) or (is_electrical and re.search(r'\b\d+\s*A\b', desc_upper))
            if not has_amp_ctx:
                return False

        # GRIT
        if lbl_upper in ["GRIT", "ABRASIVE GRIT"]:
            if not is_abrasive:
                return False
            has_grit_ctx = bool(re.search(r'\b(?:P\d{2,4}|\d{2,4}\s*GRIT|GRIT)\b', desc_upper))
            if not has_grit_ctx:
                return False

        # TOOL_TYPE
        if lbl_upper in ["TOOL TYPE", "TOOL_TYPE"]:
            if not is_tool:
                return False

        # LENGTH
        if lbl_upper == "LENGTH":
            # On cut-off wheels and abrasive discs, dimensions are Dia x Thk x Arbor, not Length
            if is_abrasive and any(k in desc_upper for k in ["CUT-OFF", "CUT OFF", "GRINDING WHEEL", "DISC"]):
                if not any(k in desc_upper for k in ["LENGTH", "LONG", "FT", "FEET"]):
                    return False

        return True

    def discover_dynamic_attributes(
        self,
        mpn: str,
        desc: str,
        classification: ClassificationDataSchema,
        canonical_mfr: str,
        canonical_brand: str,
        raw_row: Optional[Dict[str, Any]] = None
    ) -> List[ProductAttributeSchema]:
        """
        Discovers and extracts dynamic, product-specific semantic attributes using open-world intelligence.
        Never fabricates values. Never creates MPN or Brand as dynamic attributes.
        Labels are specific, semantic, and human-readable.
        Preserves commercial fields from user-uploaded raw columns without hallucinating if absent.
        """
        attrs: List[ProductAttributeSchema] = []
        desc_clean = local_cleaner.clean_text(desc)
        desc_upper = desc_clean.upper()
        classpath = classification.classpath if classification else ""
        class_upper = classpath.upper()
        raw_row = raw_row or {}
        mpn_upper = (mpn or "").strip().upper()

        # Extract MPN tokens to prevent any MPN fragments from becoming engineering attributes
        mpn_tokens = set()
        if mpn_upper:
            mpn_tokens.add(mpn_upper)
            parts = [p for p in re.split(r'[-/._\s]+', mpn_upper) if p]
            for p in parts:
                if len(p) >= 2:
                    mpn_tokens.add(p)
            for i in range(len(parts) - 1):
                mpn_tokens.add(f"{parts[i]}-{parts[i+1]}")
                mpn_tokens.add(f"{parts[i]}/{parts[i+1]}")

        # Domain flags
        is_abrasive = any(k in class_upper or k in desc_upper for k in [
            "ABRASIVE", "DISC", "WHEEL", "CUT-OFF", "CUT OFF", "GRIND", "SANDING", "FILM DISC", "FLAP DISC", "HIOLIT", "ABRANET", "STIKIT"
        ])
        is_lighting = any(k in class_upper or k in desc_upper for k in [
            "LIGHTING", "BULB", "LAMP", "LUMINAIRE", "FLOODLIGHT", "LED BULB", "A19", "BR30", "PAR38"
        ])
        is_fastener = any(k in class_upper or k in desc_upper for k in [
            "FASTENER", "SCREW", "BOLT", "NUT", "WASHER", "CAP SCREW", "HEX BOLT", "MACHINE SCREW", "WOOD SCREW"
        ])
        is_organizer = any(k in class_upper or k in desc_upper for k in [
            "ORGANIZER", "STORAGE", "BOX", "BIN", "CABINET", "TOTE", "CASE", "CHEST", "DRAWER", "LUMBER", "DECKING"
        ])
        is_tool = any(k in class_upper or k in desc_upper for k in [
            "HAND TOOL", "POWER TOOL", "SNIP", "SNIPS", "CRIMPER", "PLIERS", "CUTTER", "WRENCH", "SHEARS"
        ])
        is_electrical = is_lighting or any(k in class_upper or k in desc_upper for k in [
            "ELECTRICAL", "BREAKER", "SWITCH", "RECEPTACLE", "OUTLET", "WIRE", "CABLE", "CONTACTOR", "RELAY", "FUSE",
            "MOTOR", "THERMOSTAT", "HEAT PUMP", "WATT", "VOLT", "VAC", "VDC", "AMPERAGE", "AMP", "POWERED", "ELECTRIC"
        ])

        seq = 1
        added_labels = set()

        def add_attr(label: str, raw_val: str, norm_val: str, uom: str = "", explanation: str = "", source: str = ""):
            nonlocal seq
            if not raw_val or not str(raw_val).strip():
                return
            lbl_clean = label.strip()
            lbl_upper = lbl_clean.upper()
            if lbl_upper in ["MANUFACTURER PART NUMBER", "PRIMARY BRAND", "MANUFACTURER", "BRAND", "MPN", "SKU"]:
                return
            if lbl_upper in added_labels:
                return
            # Gate every candidate through precision filter
            if not self.is_attribute_valid_and_grounded(lbl_clean, raw_val, norm_val, desc, mpn, classification):
                return

            clean_uom = local_cleaner.normalize_uom(uom) if uom else ""
            src_str = source or f"Product Evidence ({mpn})"
            attrs.append(
                ProductAttributeSchema(
                    sequence=seq,
                    label=lbl_clean,
                    raw_value=str(raw_val).strip(),
                    normalized_value=str(norm_val).strip(),
                    uom=clean_uom,
                    status="VALID",
                    lov_matched=True,
                    explanation=ExplanationSchema(
                        raw_source=src_str,
                        ai_interpretation=explanation or f"Extracted semantic property '{lbl_clean}'",
                        lov_status=f"LOV Matched ({norm_val})",
                        uom_status=f"Standard UOM ({clean_uom})" if clean_uom else "N/A",
                        validation_result="PASS"
                    )
                )
            )
            added_labels.add(lbl_upper)
            seq += 1

        # 1. Dynamic Product Type (Semantic Anchor)
        product_type = ""
        for explicit_type in [
            "BALL VALVE", "CHECK VALVE", "GATE VALVE", "BUTTERFLY VALVE", "GLOBE VALVE",
            "VALVE", "PIPE COUPLING", "COUPLING FITTING", "COUPLING", "NIPPLE", "ELBOW", "TEE", "ADAPTER", "BUSHING", "UNION",
            "CIRCUIT BREAKER", "DISCONNECT SWITCH", "FUSE", "RELAY", "CONTACTOR",
            "LED BULB", "LIGHT BULB", "FLOODLIGHT", "LUMINAIRE",
            "AVIATION SNIP", "AVIATION SNIPS", "SNIP", "SNIPS", "CRIMPER", "PLIERS", "CUTTER", "WRENCH", "SCREWDRIVER",
            "CAP SCREW", "HEX SCREW", "MACHINE SCREW", "WOOD SCREW", "HEX BOLT", "BOLT", "NUT", "WASHER",
            "ABRASIVE FILM DISC", "ABRASIVE DISC", "FILM DISC", "FLAP DISC", "GRINDING WHEEL", "CUT-OFF WHEEL", "SANDING DISC",
            "DEEP MEDIUM ORGANIZER", "ORGANIZER", "STORAGE BOX", "TOOL BOX",
            "THERMOSTAT", "HEAT PUMP", "AIR FILTER", "DECKING BOARD", "COMPOSITE DECKING",
            "CENTRIFUGAL PUMP", "WATER PUMP", "UTILITY BLADE", "BLADE"
        ]:
            if re.search(r'\b' + re.escape(explicit_type) + r'\b', desc_upper):
                if explicit_type == "FILM DISC" and "ABRASIVE" in desc_upper:
                    product_type = "Abrasive Film Disc"
                elif explicit_type == "COUPLING" and any(k in desc_upper for k in ["BRASS", "PIPE", "FNPT", "MNPT", "PLUMBING"]):
                    product_type = "Coupling Fitting"
                elif explicit_type == "DEEP MEDIUM ORGANIZER":
                    product_type = "Organizer"
                else:
                    product_type = explicit_type.title()
                break

        if not product_type and classification and classification.fine_class and classification.fine_class != "UNKNOWN":
            product_type = classification.fine_class
        elif not product_type:
            words = [w for w in re.split(r'[^A-Za-z0-9]+', desc_clean) if len(w) > 2 and not w.isdigit()]
            meaningful = [w for w in words if w.upper() not in ["THE", "AND", "FOR", "WITH", "SET", "KIT", "OEM", "NEW", "PCS", "PACK"]]
            if meaningful:
                product_type = " ".join(meaningful[-2:]).title()
        if product_type:
            add_attr("Product Type", product_type, product_type, "", "Primary functional product type classification")

        # 2. Universal Materials Formulation
        materials = [
            "STAINLESS STEEL", "CARBON STEEL", "BRASS", "BRONZE", "POLYURETHANE",
            "CELLULAR PVC", "PVC", "CPVC", "POLYETHYLENE", "ALUMINUM", "COPPER",
            "NYLON", "RUBBER", "NITRILE", "SILICONE", "TEFLON", "PTFE",
            "CAST IRON", "DUCTILE IRON", "ZINC", "CERAMIC", "TITANIUM", "WOOD", "COMPOSITE"
        ]
        for mat in materials:
            if re.search(r'\b' + re.escape(mat) + r'\b', desc_upper):
                mat_formatted = mat if mat in ["PVC", "CPVC", "PTFE"] else mat.title()
                add_attr("Material", mat_formatted, mat_formatted, "", "Base engineering material formulation")
                add_attr("Material Type", mat_formatted, mat_formatted, "", "Base engineering material formulation")
                break

        # 3. Universal Nominal Size & Dimensions
        m_sz = re.search(r'\b(1/16|1/8|3/16|1/4|5/16|3/8|7/16|1/2|5/8|3/4|7/8|1[- ]?1/4|1[- ]?1/2|2[- ]?1/2)(?:\s*(?:IN(?:CH(?:ES)?)?|"))?\b|\b([1-4])\s*(?:IN(?:CH(?:ES)?)?|")\b', desc_upper)
        if m_sz:
            sz_val = (m_sz.group(1) or m_sz.group(2)).replace(" ", "-")
            if sz_val not in mpn_tokens:
                add_attr("Nominal Size", sz_val, sz_val, "IN", "Nominal product size specification")
                if any(k in class_upper or k in desc_upper for k in ["VALVE", "VLV", "FITTING", "PIPE", "CPLG", "TUBING", "HOSE", "PLUMBING", "PNEUMATIC"]):
                    add_attr("Connection Size", sz_val, sz_val, "IN", "Inlet/outlet connection port size")

        # Length (Feet or Inches) - NOT for abrasive cut-off discs
        m_len_ft = re.search(r'\b(8|10|12|16|20|24|50|100|250|500)\s*(?:FT|FOOT|FEET|\')\b', desc_upper)
        if m_len_ft:
            add_attr("Length", f"{m_len_ft.group(1)} FT", f"{m_len_ft.group(1)} FT", "FT", "Nominal overall length")
        elif not is_abrasive:
            m_len_in = re.search(r'(?:X\s*)(\d+(?:[./]\d+)?)\s*(?:IN(?:CH(?:ES)?)?|"|\b)', desc_upper)
            if m_len_in and m_len_in.group(1) not in ["0.045", "1/16"] and m_len_in.group(1) not in mpn_tokens:
                add_attr("Length", m_len_in.group(1), m_len_in.group(1), "IN", "Fastener or tool shank length")

        # Board / Dimension Width
        m_wid = re.search(r'\b(5[- ]?1/2|6|8|12)\s*(?:IN|INCH(?:ES)?|")\b', desc_upper)
        if m_wid and ("DECK" in class_upper or "BUILDING" in class_upper or "LUMBER" in desc_upper or "DECK" in desc_upper):
            val = m_wid.group(1).replace(" ", "-")
            add_attr("Width", f"{val} IN", f"{val} IN", "IN", "Board nominal width")

        # Color / Finish
        for clr in ["BROWN", "GREY", "GRAY", "WHITE", "BLACK", "RED", "BLUE", "GREEN", "YELLOW"]:
            if re.search(r'\b' + clr + r'\b', desc_upper):
                add_attr("Color / Finish", clr.title(), clr.title(), "", "Product visual finish or color")
                break

        # Abrasive Wheel / Disc Dimensions
        if is_abrasive:
            # Check 3-dimensional pattern: Diameter x Thickness x Arbor (e.g. 4-1/2 in. x .045 in. x 7/8 in.)
            m_3dim = re.search(r'\b(4[- ]?1/2|4\.5|[4-9]|12|14)\s*(?:IN(?:CH(?:ES)?)?\.?|"|\b)?\s*[xX]\s*(0?\.\d+|\d+/\d+)\s*(?:IN(?:CH(?:ES)?)?\.?|"|\b)?\s*[xX]\s*([0-9/.-]+(?:-\d+)?)\s*(?:IN(?:CH(?:ES)?)?\.?|MM|"|\b)?', desc_upper)
            if m_3dim:
                d_val = m_3dim.group(1).replace(" ", "-")
                t_val = m_3dim.group(2)
                a_val = m_3dim.group(3)
                if "DISC" in desc_upper or "FILM" in desc_upper:
                    add_attr("Disc Diameter", d_val, d_val, "IN", "Abrasive disc outer diameter")
                add_attr("Wheel Diameter", d_val, d_val, "IN", "Abrasive wheel outer diameter")
                add_attr("Wheel Thickness", t_val, t_val, "IN", "Abrasive wheel thickness/kerf")
                if a_val not in mpn_tokens:
                    add_attr("Arbor Size", a_val, a_val, "IN" if "/" in a_val else "", "Wheel mounting arbor size")
            else:
                m_dia = re.search(r'\b(4[- ]?1/2|4\.5|5|6|7|9|12|14)\s*(?:["\']|IN(?:CH(?:ES)?)?\.?|\b)', desc_upper)
                if m_dia:
                    val = m_dia.group(1).replace(" ", "-")
                    if "DISC" in desc_upper or "FILM" in desc_upper:
                        add_attr("Disc Diameter", val, val, "IN", "Abrasive disc outer diameter")
                    add_attr("Wheel Diameter", val, val, "IN", "Abrasive wheel outer diameter")

                m_thk = re.search(r'(?:X\s*|\b)(0?\.\d+|(?<!-)(?:1/16|1/8|3/32|1/32|3/16|1/4))\s*(?:["\']|IN(?:CH(?:ES)?)?\.?|\b)', desc_upper)
                if m_thk and (not m_dia or m_thk.group(1) not in m_dia.group(1)):
                    val = m_thk.group(1)
                    add_attr("Wheel Thickness", val, val, "IN", "Abrasive wheel thickness/kerf")

                m_arbor = re.search(r'(?:ARBOR|BORE|HOLE)\s*(?:SIZE\s*)?[:=]?\s*([0-9/.-]+(?:-\d+)?)\s*(?:IN|MM|"|\b)?|\b([0-9/.-]+(?:-\d+)?)\s*(?:IN|MM|")?\s*(?:ARBOR|BORE)\b|(?:[xX]\s*[0-9/.-]+\s*(?:IN(?:CH(?:ES)?)?\.?|")?\s*[xX]\s*)([0-9/.-]+(?:-\d+)?)', desc_upper)
                if m_arbor:
                    arb_val = m_arbor.group(1) or m_arbor.group(2) or m_arbor.group(3)
                    if arb_val and arb_val not in ["0.045", "1/16", ".045"] and arb_val not in mpn_tokens:
                        add_attr("Arbor Size", arb_val, arb_val, "IN" if "/" in arb_val else "", "Wheel mounting arbor size")

            m_grit = re.search(r'\b(P\d{2,4}|\d{2,4}\s*GRIT)\b', desc_upper)
            if m_grit:
                raw_g = m_grit.group(1).replace("GRIT", "").strip()
                add_attr("Grit", raw_g, raw_g, "", "Abrasive grit rating")
                add_attr("Abrasive Grit", raw_g, raw_g, "", "Abrasive grit rating")

            for mat in ["ALUMINUM OXIDE", "SILICON CARBIDE", "ZIRCONIA ALUMINA", "CERAMIC", "DIAMOND"]:
                if mat in desc_upper:
                    add_attr("Abrasive Material", mat.title(), mat.title(), "", "Abrasive grain material composition")
                    break

            m_rpm = re.search(r'\b(\d{4,5})\s*RPM\b', desc_upper)
            if m_rpm:
                add_attr("Maximum RPM", m_rpm.group(1), m_rpm.group(1), "RPM", "Safe maximum operating rotational speed")

        # 4. Fluid & Pneumatic Connections & Pressure
        if any(k in class_upper or k in desc_upper for k in ["VALVE", "VLV", "FITTING", "PIPE", "CPLG", "PLUMBING", "PNEUMATIC"]):
            connection_types = ["FNPT", "MNPT", "NPT", "PUSH-TO-CONNECT", "COMPRESSION", "BARBED", "SWEAT", "PRESS", "PEX", "FLANGED", "SOCKET", "TRI-CLAMP"]
            for ct in connection_types:
                if re.search(r'\b' + re.escape(ct) + r'\b', desc_upper):
                    add_attr("Connection Type", ct, ct, "", "Plumbing or pneumatic joint connection style")
                    break

            m_psi = re.search(r'\b(\d{2,5})\s*(?:PSI|BAR|KPA|WOG|CWP)\b', desc_upper)
            if m_psi:
                add_attr("Pressure Rating", f"{m_psi.group(1)} PSI", f"{m_psi.group(1)} PSI", "PSI", "Maximum rated operating pressure")

        # 5. Electrical & Lighting (Strict Contextual Evidence Only)
        if is_electrical:
            m_watt = re.search(r'\b(\d+(?:\.\d+)?)\s*(?:W|WATT|WATTS)\b', desc_upper)
            if m_watt and m_watt.group(1) not in mpn_tokens:
                add_attr("Wattage", m_watt.group(1), m_watt.group(1), "W", "Electrical power consumption rating")

            # Voltage with contextual semantic association (e.g. 'operates at 120 volts', '120V', '24V')
            m_volt = re.search(r'(?:OPERATES\s+AT\s+|RATED\s+(?:FOR|AT)\s+|VOLTAGE\s*[:=]?\s*|\b)(12|24|120|208|230|240|277|480|600)\s*(?:V|VOLTS?|VAC|VDC)\b', desc_upper)
            if m_volt:
                volt_candidate = m_volt.group(1)
                # Ensure it is not an MPN fragment without context
                desc_no_mpn = desc_upper.replace(mpn_upper, " ")
                if re.search(r'\b' + volt_candidate + r'\s*(?:V|VOLTS?|VAC|VDC)\b', desc_no_mpn):
                    add_attr("Voltage", volt_candidate, volt_candidate, "V", "Nominal operating voltage")

            # Amperage with explicit electrical context
            m_amp = re.search(r'(?:AMPERAGE\s*[:=]?\s*|\b)(\d+(?:\.\d+)?)\s*(?:AMPS?|AMPERES?)\b|\b(\d+(?:\.\d+)?)\s*A\b', desc_upper)
            if m_amp:
                amp_candidate = m_amp.group(1) or m_amp.group(2)
                if amp_candidate not in mpn_tokens:
                    add_attr("Amperage", amp_candidate, amp_candidate, "A", "Rated electrical current")

            if is_lighting:
                for shape in ["A19", "BR30", "PAR38", "PAR20", "PAR30", "T8", "T5", "MR16", "GU10", "ED17", "G25", "B11"]:
                    if re.search(r'\b' + shape + r'\b', desc_upper):
                        add_attr("Bulb Shape", shape, shape, "", "ANSI bulb shape code")
                        break

                for base in ["E26", "E39", "E12", "GU24", "GU10", "BI-PIN", "G13", "MOGUL", "CANDELABRA"]:
                    if re.search(r'\b' + base + r'\b', desc_upper):
                        b_name = "E26 Medium" if base == "E26" else ("E12 Candelabra" if base in ["E12", "CANDELABRA"] else base.title())
                        add_attr("Base Type", b_name, b_name, "", "Lamp socket base interface")
                        break
                # Only match 'MEDIUM' if explicitly accompanied by lighting base keywords
                if re.search(r'\b(?:MED(?:IUM)?\s*BASE|BASE\s*:\s*MED(?:IUM)?|E26\s*MEDIUM|MEDIUM\s*SCREW\s*BASE)\b', desc_upper):
                    add_attr("Base Type", "E26 Medium", "E26 Medium", "", "Lamp socket base interface")

                m_cct = re.search(r'\b([2-6]\d00)\s*K\b', desc_upper)
                if m_cct:
                    add_attr("Color Temperature", f"{m_cct.group(1)}K", f"{m_cct.group(1)}K", "K", "Correlated color temperature rating")

                m_lm = re.search(r'\b(\d{3,5})\s*(?:LM|LUMENS?)\b', desc_upper)
                if m_lm:
                    add_attr("Lumens", m_lm.group(1), m_lm.group(1), "LM", "Luminous flux output")

                if "DIMMABLE" in desc_upper and "NON-DIMMABLE" not in desc_upper:
                    add_attr("Dimmable", "Yes", "Yes", "", "Dimming capability")
                elif "NON-DIMMABLE" in desc_upper:
                    add_attr("Dimmable", "No", "No", "", "Dimming capability")

        # 6. Fasteners & Mechanical Screws (Strict MPN Protection)
        if is_fastener or any(k in desc_upper for k in ["THREAD", "THREADED", "UNC", "UNF", "TPI"]):
            # Specific fastener thread pattern: fraction-TPI (e.g. 1/4-20) or gauge-TPI (e.g. 10-24) or metric pitch (e.g. M8x1.25)
            m_thread = re.search(r'\b(\d+/\d+-\d+|#(?:[0-9]|1[0-2])-\d{2}|(?:[1-9]|1[0-2])-\d{2}|M\d+\s*[xX]\s*\d+(?:\.\d+)?)\b', desc_upper)
            if m_thread and m_thread.group(1) not in mpn_tokens:
                add_attr("Thread Size", m_thread.group(1), m_thread.group(1), "", "Screw/bolt thread size and pitch")

            for hd in ["HEX HEAD", "PAN HEAD", "FLAT HEAD", "SOCKET HEAD", "ROUND HEAD", "TRUSS HEAD", "BUTTON HEAD"]:
                if hd in desc_upper:
                    add_attr("Head Type", hd.title(), hd.title(), "", "Fastener head style")
                    add_attr("Fastener Head Style", hd.title(), hd.title(), "", "Fastener head style")
                    break

            for fn in ["ZINC PLATED", "HOT DIPPED GALVANIZED", "BLACK OXIDE", "YELLOW ZINC", "PLAIN"]:
                if fn in desc_upper:
                    add_attr("Finish", fn.title(), fn.title(), "", "Surface protective coating")
                    break

        # 7. Hand Tools & Cutters
        if is_tool:
            for tt in ["AVIATION SNIPS", "OFFSET SNIPS", "CRIMPER", "DIAGONAL CUTTERS", "LONG NOSE PLIERS", "WIRE STRIPPER", "SHEARS"]:
                if tt in desc_upper:
                    add_attr("Tool Type", tt.title(), tt.title(), "", "Hand tool design classification")
                    break

            m_ga = re.search(r'\b(\d{1,2})\s*(?:GA|GAUGE)\b', desc_upper)
            if m_ga and m_ga.group(1) not in mpn_tokens:
                add_attr("Cutting Capacity", f"{m_ga.group(1)} Gauge", f"{m_ga.group(1)} Gauge", "", "Maximum cutting material thickness")

            for ct_dir in ["LEFT CUT", "RIGHT CUT", "STRAIGHT CUT", "BULLDOG"]:
                if ct_dir in desc_upper:
                    add_attr("Cut Direction", ct_dir.title(), ct_dir.title(), "", "Cutting blade orientation")
                    break

        # 8. Appliances
        if any(k in class_upper or k in desc_upper for k in ["APPLIANCE", "DISHWASHER", "FRIDGE", "REFRIGERATOR"]):
            app_t = "Built-In Dishwasher" if "DISHWASHER" in desc_upper else ("Refrigerator" if ("FRIDGE" in desc_upper or "REFRIGERATOR" in desc_upper) else "Kitchen Appliance")
            add_attr("Appliance Type", app_t, app_t, "", "Appliance functional category")
            for fin in ["STAINLESS STEEL", "BLACK STAINLESS", "WHITE", "BLACK", "PANEL READY"]:
                if fin in desc_upper:
                    add_attr("Finish / Color", fin.title(), fin.title(), "", "Exterior appliance finish")
                    break

        # 9. Pack / Packaging Quantity
        m_qty = re.search(r'(?:PACK OF\s*(\d+)|PK OF\s*(\d+)|\bBOX OF\s*(\d+)|\bBAG OF\s*(\d+)|\bQTY:?\s*(\d+)|\b(\d+)\s*(?:PK|PACK|PC|PCS)\b)', desc_upper)
        if m_qty:
            val = next((g for g in m_qty.groups() if g is not None), None)
            if val and val not in mpn_tokens:
                add_attr("Package Quantity", val, val, "", "Item packaging count")
                add_attr("Pack Quantity", val, val, "", "Item packaging count")

        # 10. Commercial Fields from Customer Upload (Preserved, NEVER Fabricated)
        if raw_row and isinstance(raw_row, dict):
            commercial_maps = [
                (["cost", "unit_cost", "unit cost", "net_cost", "net cost"], "Unit Cost"),
                (["price", "list_price", "list price", "retail_price", "retail price"], "List Price"),
                (["stock", "quantity", "inventory", "qty_on_hand", "qty on hand"], "Stock Quantity"),
                (["country", "country_of_origin", "country of origin", "coo", "origin"], "Country of Origin"),
                (["upc", "ean", "barcode"], "UPC"),
                (["weight", "gross_weight", "gross weight", "net_weight", "net weight"], "Weight"),
            ]
            raw_row_lower = {str(k).strip().lower(): v for k, v in raw_row.items() if v is not None and str(v).strip()}
            for keys, attr_label in commercial_maps:
                for k in keys:
                    if k in raw_row_lower:
                        val_str = str(raw_row_lower[k]).strip()
                        if val_str and val_str.upper() not in ["N/A", "NONE", "NULL", "UNKNOWN", ""]:
                            add_attr(attr_label, val_str, val_str, "", f"Customer supplied commercial data ({k})", source="RAW_INPUT")
                        break

        return attrs

    def _create_error_fallback_product(
        self,
        session: Optional[ProcessingSession],
        candidate: Dict[str, Any],
        error: str = ""
    ) -> ProductSchema:
        row_id = candidate.get("source_row_id", 1)
        mpn = candidate.get("mpn", "")
        raw_desc = candidate.get("description", "")
        raw_mfr = candidate.get("part_manuf", "")
        raw_row_data = candidate.get("raw_row", {})
        e1_b = candidate.get("e1_brand", "")
        unilog_b = candidate.get("unilog_brand", "")
        dib_b = candidate.get("dib_brand", "")

        safe_mpn_slug = re.sub(r'[^a-zA-Z0-9_-]', '_', mpn.strip().lower()) if mpn else ""
        base_id = f"prod-{safe_mpn_slug}" if safe_mpn_slug else f"prod-row-{row_id}"
        if session and hasattr(session, "allocate_product_id"):
            product_id = session.allocate_product_id(base_id, row_id=row_id)
        else:
            product_id = f"{base_id}-{uuid.uuid4().hex[:8]}"

        now_iso = datetime.now(timezone.utc).isoformat()

        classification = ClassificationDataSchema(
            department="General Industrial",
            class_name="Industrial Supplies",
            fine_class="Unclassified",
            classpath="General Industrial > Industrial Supplies > Other > Unclassified",
            confidence=0.0,
            reason=f"Processing fallback: {error}"
        )
        content = ProductContentSchema(
            product_name=raw_desc or mpn or "Unclassified Product",
            mobile_desc=raw_desc[:60] if raw_desc else "",
            invoice_desc=(raw_desc[:40] if raw_desc else "").upper(),
            short_desc=raw_desc[:255] if raw_desc else "",
            long_desc=raw_desc,
            retail_desc=raw_desc[:150] if raw_desc else "",
            marketing_description=raw_desc[:2000] if raw_desc else "",
            item_features=[]
        )

        fallback_product = ProductSchema(
            id=product_id,
            source_row_id=row_id,
            source_data=SourceDataSchema(
                mfg_part_num=mpn,
                part_desc=raw_desc,
                e1_brand=e1_b,
                unilog_brand=unilog_b,
                dib_brand=dib_b,
                part_manuf=raw_mfr,
                raw_columns=raw_row_data
            ),
            identity=ProductIdentitySchema(
                mfg_part_num=mpn,
                manufacturer=ValueMatchSchema(raw_value=raw_mfr, canonical_value=raw_mfr or "-- Unbranded --", confidence=0.5, status="UNVERIFIED"),
                brand=ValueMatchSchema(raw_value="", canonical_value="-- Unbranded --", confidence=0.5, status="UNBRANDED")
            ),
            classification=classification,
            content=content,
            attributes=[],
            validations=[],
            quality=quality_service.calculate_quality(
                ProductSchema.model_construct(
                    id=product_id, source_row_id=row_id,
                    source_data=SourceDataSchema(mfg_part_num=mpn, part_desc=raw_desc, e1_brand="", unilog_brand="", dib_brand="", part_manuf=raw_mfr),
                    identity=ProductIdentitySchema(mfg_part_num=mpn, manufacturer=ValueMatchSchema(raw_value=raw_mfr, canonical_value=raw_mfr, confidence=0.5, status="UNVERIFIED"), brand=ValueMatchSchema(raw_value="", canonical_value="-- Unbranded --", confidence=0.5, status="UNBRANDED")),
                    classification=classification, content=content, quality=None, validations=[], created_at="", updated_at=""
                ),
                []
            ),
            requires_review=True,
            created_at=now_iso,
            updated_at=now_iso
        )

        if session and hasattr(session, "add_product"):
            session.add_product(fallback_product)
            session.log_event(
                product_id=product_id,
                event_type="PROCESSING_ERROR",
                description=f"Processing failed for source row {row_id} (MPN: '{mpn}'): {error}",
                actor="PROCESSING_SERVICE"
            )

        return fallback_product

    def process_candidates_batch(
        self,
        session: ProcessingSession,
        candidates: List[Dict[str, Any]],
        max_workers: int = 10,
        progress_callback: Optional[Callable[[str, int], None]] = None
    ) -> List[ProductSchema]:
        if not candidates:
            return []

        if len(candidates) <= 1:
            results = []
            for i, cand in enumerate(candidates, start=1):
                res = self.process_candidate(
                    session,
                    cand,
                    progress_callback=progress_callback
                )
                results.append(res)
            return results

        results: List[Optional[ProductSchema]] = [None] * len(candidates)
        completed_count = 0
        lock = Lock()

        def _worker(idx: int, cand: Dict[str, Any]):
            nonlocal completed_count
            try:
                prod = self.process_candidate(session, cand)
                results[idx] = prod
            except Exception as e:
                logger.exception("Failed processing candidate row %s: %s", cand.get("source_row_id", idx), e)
                try:
                    fallback_prod = self._create_error_fallback_product(session, cand, error=str(e))
                    results[idx] = fallback_prod
                except Exception as inner_e:
                    logger.error("Failed creating fallback product for row %s: %s", cand.get("source_row_id", idx), inner_e)
            finally:
                with lock:
                    completed_count += 1
                    pct = min(99, int((completed_count / len(candidates)) * 100))
                    if progress_callback:
                        progress_callback("ENRICHING_BATCH", pct)

        workers = min(max_workers, len(candidates))
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [executor.submit(_worker, i, cand) for i, cand in enumerate(candidates)]
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    logger.error(f"Batch worker execution error: {e}")

        return [r for r in results if r is not None]

processing_service = ProcessingService()
