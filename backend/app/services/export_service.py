import csv
import io
import os
import re
from typing import List, Dict, Any, Optional
from app.schemas.product import ProductSchema
from app.storage.ibm_object_storage import storage_adapter

class ExportService:
    def __init__(self):
        self.headers = self._load_delivery_headers()

    def _load_delivery_headers(self) -> List[str]:
        candidate_paths = [
            os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "output_columns.json")),
            os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "output_columns.json")),
            os.path.abspath("output_columns.json"),
        ]
        for output_json_path in candidate_paths:
            if os.path.exists(output_json_path):
                try:
                    import json
                    with open(output_json_path, "r", encoding="utf-8") as f:
                        headers = json.load(f)
                        if isinstance(headers, list) and len(headers) == 252:
                            return headers
                except Exception:
                    pass
        
        expected_csv_path = "sample_data/Unihack_ Expected Output - Delivery Format.csv"
        if os.path.exists(expected_csv_path):
            try:
                with open(expected_csv_path, "r", encoding="utf-8-sig") as f:
                    reader = csv.reader(f)
                    h = next(reader)
                    if len(h) == 252:
                        return h
            except Exception:
                pass
        
        return []

    def _get_raw_column(self, raw_cols: Dict[str, Any], key: str) -> str:
        if not raw_cols:
            return ""
        if key in raw_cols and raw_cols[key] is not None:
            val = str(raw_cols[key]).strip()
            if val and val.lower() not in ["nan", "none", "null"]:
                return val
        clean_k = re.sub(r'[^a-zA-Z0-9]', '', key).lower()
        for rk, rv in raw_cols.items():
            if rv is not None and re.sub(r'[^a-zA-Z0-9]', '', rk).lower() == clean_k:
                val = str(rv).strip()
                if val and val.lower() not in ["nan", "none", "null"]:
                    return val
        return ""

    def export_products_to_csv(self, products: List[ProductSchema]) -> str:
        output_buffer = io.StringIO()
        writer = csv.writer(output_buffer)

        # 1. Write Header Row (exact 252 columns from source of truth)
        writer.writerow(self.headers)

        # 2. Write Product Rows
        for p in products:
            raw_cols = p.source_data.raw_columns if (p.source_data and p.source_data.raw_columns) else {}
            row = []
            for col in self.headers:
                val = ""
                col_upper = col.upper().strip()

                # Attribute pattern matching (ATTRIBUTE_LABEL 1..50, ATTRIBUTE_VALUE 1..50, ATTRIBUTE_UOM 1..50)
                m_label = re.match(r"^ATTRIBUTE[ _]LABEL[ _](\d+)$", col_upper)
                m_val = re.match(r"^ATTRIBUTE[ _]VAL(?:UE)?[ _](\d+)$", col_upper)
                m_uom = re.match(r"^ATTRIBUTE[ _]UOM[ _](\d+)$", col_upper)
                m_feat = re.match(r"^ITEM[ _]FEATURES?[ _](\d+)$", col_upper)

                if m_label:
                    idx = int(m_label.group(1)) - 1
                    if idx < len(p.attributes) and p.attributes[idx].label:
                        val = p.attributes[idx].label
                    else:
                        val = self._get_raw_column(raw_cols, col)
                elif m_val:
                    idx = int(m_val.group(1)) - 1
                    if idx < len(p.attributes):
                        attr = p.attributes[idx]
                        val = attr.normalized_value or attr.raw_value or ""
                    else:
                        val = self._get_raw_column(raw_cols, col)
                elif m_uom:
                    idx = int(m_uom.group(1)) - 1
                    if idx < len(p.attributes) and p.attributes[idx].uom:
                        val = p.attributes[idx].uom
                    else:
                        val = self._get_raw_column(raw_cols, col)
                elif m_feat:
                    idx = int(m_feat.group(1)) - 1
                    features = p.content.item_features if (p.content and p.content.item_features) else []
                    if idx < len(features) and features[idx]:
                        val = features[idx]
                    else:
                        val = self._get_raw_column(raw_cols, col)
                elif col_upper in ["MFG_PART_NUM", "MFG PART NUM"]:
                    val = (p.source_data.mfg_part_num if p.source_data and p.source_data.mfg_part_num else "") or (p.identity.mfg_part_num if p.identity else "") or self._get_raw_column(raw_cols, col)
                elif col_upper in ["PART_NUMBER", "MANUFACTURER_PART_NUMBER", "PART NUMBER", "MANUFACTURER PART NUMBER"]:
                    val = (p.identity.mfg_part_num if p.identity and p.identity.mfg_part_num else "") or self._get_raw_column(raw_cols, col)
                elif col_upper in ["SKU - MY_PART_NUMBER", "SKU - MY PART NUMBER"]:
                    val = self._get_raw_column(raw_cols, col) or (p.identity.mfg_part_num if p.identity else "")
                elif col_upper in ["ALTERNATE_PART_NUMBER", "ALTERNATE PART NUMBER"]:
                    val = self._get_raw_column(raw_cols, col) or (p.identity.mfg_part_num if p.identity else "")
                elif col_upper in ["BRAND_NAME", "BRAND NAME", "TRADE_NAME", "TRADE NAME"]:
                    val = (p.identity.brand.canonical_value if (p.identity and p.identity.brand and p.identity.brand.canonical_value) else "") or self._get_raw_column(raw_cols, col)
                elif col_upper in ["MANUFACTURER_NAME", "MANUFACTURER NAME"]:
                    val = (p.identity.manufacturer.canonical_value if (p.identity and p.identity.manufacturer and p.identity.manufacturer.canonical_value) else "") or self._get_raw_column(raw_cols, col)
                elif col_upper in ["CLASSPATH", "CATEGORY_PATH", "CATEGORY PATH"]:
                    val = (p.classification.classpath if (p.classification and p.classification.classpath) else "") or self._get_raw_column(raw_cols, col)
                elif col_upper in ["PRODUCT NAME", "PRODUCT_NAME"]:
                    val = (p.content.product_name if (p.content and p.content.product_name) else "") or self._get_raw_column(raw_cols, col)
                elif col_upper in ["MOBILE_DESC", "MOBILE DESC"]:
                    val = (p.content.mobile_desc if (p.content and p.content.mobile_desc) else "") or self._get_raw_column(raw_cols, col)
                elif col_upper in ["INVOICE_DESC", "INVOICE DESC"]:
                    val = (p.content.invoice_desc if (p.content and p.content.invoice_desc) else "") or self._get_raw_column(raw_cols, col)
                elif col_upper in ["SHORT_DESC", "SHORT DESC"]:
                    val = (p.content.short_desc if (p.content and p.content.short_desc) else "") or self._get_raw_column(raw_cols, col)
                elif col_upper in ["LONG_DESC1", "LONG DESC1", "LONG_DESC", "LONG DESC"]:
                    val = (p.content.long_desc if (p.content and p.content.long_desc) else "") or self._get_raw_column(raw_cols, col)
                elif col_upper in ["RETAIL_DESC", "RETAIL DESC"]:
                    val = (p.content.retail_desc if (p.content and p.content.retail_desc) else "") or self._get_raw_column(raw_cols, col)
                elif col_upper in ["MARKETING_DESCRIPTION", "MARKETING DESCRIPTION"]:
                    val = (p.content.marketing_description if (p.content and p.content.marketing_description) else "") or self._get_raw_column(raw_cols, col)
                elif col_upper == "DEPT":
                    val = self._get_raw_column(raw_cols, "Dept") or (p.classification.department if p.classification else "")
                elif col_upper == "CLASS":
                    val = self._get_raw_column(raw_cols, "Class") or (p.classification.class_name if p.classification else "")
                elif col_upper == "FINE":
                    val = self._get_raw_column(raw_cols, "Fine") or (p.classification.fine_class if p.classification else "")
                elif col_upper in ["PART_DESC", "PART DESC"]:
                    val = (p.source_data.part_desc if p.source_data else "") or self._get_raw_column(raw_cols, col)
                elif col_upper in ["E1_BRAND", "E1 BRAND"]:
                    val = (p.source_data.e1_brand if p.source_data else "") or self._get_raw_column(raw_cols, col)
                elif col_upper in ["UNILOG_BRAND", "UNILOG BRAND"]:
                    val = (p.source_data.unilog_brand if p.source_data else "") or self._get_raw_column(raw_cols, col)
                elif col_upper in ["DIB_BRAND", "DIB BRAND"]:
                    val = (p.source_data.dib_brand if p.source_data else "") or self._get_raw_column(raw_cols, col)
                elif col_upper in ["PART_MANUF", "PART MANUF"]:
                    val = (p.source_data.part_manuf if p.source_data else "") or self._get_raw_column(raw_cols, col)
                elif col_upper in ["WITH", "STANDARD/APPROVALS", "PROP 65", "APPLICATION", "INCLUDES"]:
                    val = self._get_raw_column(raw_cols, col)
                else:
                    val = self._get_raw_column(raw_cols, col)

                row.append(val)
            writer.writerow(row)

        csv_content = output_buffer.getvalue()
        object_key = f"outputs/unilog_export_delivery_{len(products)}_skus.csv"
        try:
            storage_adapter.save_csv(csv_content, object_key)
        except Exception:
            pass
        return csv_content

    def export_clean_intelligence_csv(self, products: List[ProductSchema]) -> str:
        """
        Phase 9 — Clean Intelligence CSV Export.
        Contains only meaningful, populated product information with dynamic attributes.
        Human-readable, no redundant filler or unused placeholder slots.
        """
        output_buffer = io.StringIO()
        writer = csv.writer(output_buffer)

        # 1. Discover all distinct populated attribute labels across the product list in order
        dynamic_labels: List[str] = []
        seen_labels = set()
        for p in products:
            for attr in p.attributes:
                if attr.label and (attr.raw_value or attr.normalized_value):
                    lbl = attr.label.strip()
                    lbl_norm = lbl.upper()
                    if lbl_norm not in seen_labels and lbl_norm not in [
                        "MANUFACTURER PART NUMBER", "PRIMARY BRAND", "MANUFACTURER", "BRAND", "PRODUCT TYPE"
                    ]:
                        seen_labels.add(lbl_norm)
                        dynamic_labels.append(lbl)

        # 2. Build Human-Readable Clean Headers
        core_headers = [
            "PART_NUMBER",
            "PRODUCT_NAME",
            "MANUFACTURER",
            "BRAND",
            "DEPARTMENT",
            "CLASS",
            "FINE",
            "CLASSPATH",
            "PRODUCT_TYPE",
            "SHORT_DESCRIPTION",
            "LONG_DESCRIPTION",
        ]
        # Format dynamic headers cleanly, e.g. "WHEEL_DIAMETER", "WATTAGE", "MATERIAL_TYPE"
        dynamic_header_cols = [
            re.sub(r'[^A-Za-z0-9_]', '_', lbl.strip().upper()).replace('__', '_')
            for lbl in dynamic_labels
        ]
        full_headers = core_headers + dynamic_header_cols
        writer.writerow(full_headers)

        # 3. Write Data Rows
        for p in products:
            part_num = (p.identity.mfg_part_num if p.identity else "") or (p.source_data.mfg_part_num if p.source_data else "")
            prod_name = p.content.product_name if p.content else ""
            mfr = p.identity.manufacturer.canonical_value if (p.identity and p.identity.manufacturer) else ""
            brand = p.identity.brand.canonical_value if (p.identity and p.identity.brand) else ""
            dept = p.classification.department if p.classification else ""
            cls_name = p.classification.class_name if p.classification else ""
            fine = p.classification.fine_class if p.classification else ""
            classpath = p.classification.classpath if p.classification else ""
            short_desc = p.content.short_desc if p.content else ""
            long_desc = p.content.long_desc if p.content else ""

            # Extract Product Type from attributes or fine class
            prod_type = ""
            for attr in p.attributes:
                if attr.label and attr.label.strip().upper() == "PRODUCT TYPE":
                    prod_type = attr.normalized_value or attr.raw_value or ""
                    break
            if not prod_type and p.classification:
                prod_type = p.classification.fine_class or ""

            # Map product attributes by label
            prod_attr_map: Dict[str, str] = {}
            for attr in p.attributes:
                if attr.label:
                    val = attr.normalized_value or attr.raw_value or ""
                    if val:
                        uom_str = f" {attr.uom}" if attr.uom and not str(val).endswith(attr.uom) else ""
                        prod_attr_map[attr.label.strip().upper()] = f"{val}{uom_str}".strip()

            row = [
                part_num,
                prod_name,
                mfr,
                brand,
                dept,
                cls_name,
                fine,
                classpath,
                prod_type,
                short_desc,
                long_desc,
            ]
            for lbl in dynamic_labels:
                row.append(prod_attr_map.get(lbl.strip().upper(), ""))

            writer.writerow(row)

        csv_content = output_buffer.getvalue()
        object_key = f"outputs/clean_intelligence_{len(products)}_skus.csv"
        try:
            storage_adapter.save_csv(csv_content, object_key)
        except Exception:
            pass
        return csv_content

export_service = ExportService()
