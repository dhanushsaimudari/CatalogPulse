import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from app.services.ingestion_service import ingestion_service
from app.services.processing_service import processing_service
from app.services.export_service import export_service
from app.session.session_manager import session_manager

def main():
    sanity_path = os.path.join(os.path.dirname(__file__), "..", "backend", "storage_data", "inputs", "import-1e365f74_sortolog_sanity_test.csv")
    with open(sanity_path, "rb") as f:
        _, _, candidates = ingestion_service.process_import("sanity.csv", f.read())

    session = session_manager.create_session("demo-verification-session", seed_demo=False)
    products = processing_service.process_candidates_batch(session, candidates)

    print(f"Total Processed: {len(products)}")
    for p in products:
        print(f"\n==================================================")
        print(f"RAW INPUT:")
        print(f"  MPN: {p.identity.mfg_part_num}")
        print(f"  RAW DESC: {p.content.product_name}")
        print(f"IDENTIFIED PRODUCT:")
        print(f"  Canonical Manufacturer: {p.identity.manufacturer.canonical_value} (Status: {p.identity.manufacturer.status})")
        print(f"  Canonical Brand: {p.identity.brand.canonical_value} (Status: {p.identity.brand.status})")
        print(f"  Classification: {p.classification.classpath}")
        print(f"DYNAMIC ATTRIBUTES:")
        for a in p.attributes:
            uom_str = f" {a.uom}" if a.uom else ""
            print(f"  * {a.label} = {a.normalized_value}{uom_str} [lov={a.lov_matched}, status={a.status}]")

    print("\n\n==================================================")
    print("SAMPLE CLEAN INTELLIGENCE CSV (First 6 lines):")
    print("==================================================")
    clean_csv = export_service.export_clean_intelligence_csv(products[:4])
    for line in clean_csv.splitlines()[:6]:
        print(line)

    print("\n\n==================================================")
    print("SAMPLE 252-COLUMN UNILOG CSV (First product attributes populated):")
    print("==================================================")
    unilog_csv = export_service.export_products_to_csv(products[:1])
    lines = unilog_csv.splitlines()
    header_cols = lines[0].split(",")
    val_cols = lines[1].split(",")
    for h, v in zip(header_cols, val_cols):
        if v.strip() and v.strip() != '""':
            print(f"  {h} = {v}")

if __name__ == "__main__":
    main()
