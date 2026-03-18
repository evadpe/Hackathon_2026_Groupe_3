from pathlib import Path
import json
import random
import shutil

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent.parent

RAW_COHERENT_DIR = BASE_DIR / "data" / "raw" / "documents"
RAW_INCOHERENT_DIR = BASE_DIR / "data" / "raw" / "bundles" / "incoherent"

TRAIN_DIR = BASE_DIR / "data" / "train"
VAL_DIR = BASE_DIR / "data" / "val"
TEST_DIR = BASE_DIR / "data" / "test"

RANDOM_SEED = 42


import os
import stat
import time


def handle_remove_readonly(func, path, exc):
    """
    Corrige les problèmes de suppression sur Windows
    quand un fichier est en lecture seule.
    """
    os.chmod(path, stat.S_IWRITE)
    func(path)


def ensure_clean_dir(path: Path) -> None:
    if path.exists():
        for _ in range(3):
            try:
                shutil.rmtree(path, onerror=handle_remove_readonly)
                break
            except PermissionError:
                time.sleep(1)
        else:
            raise PermissionError(
                f"Impossible de supprimer le dossier {path}. "
                "Fermez les PDF ouverts ou les dossiers utilisés par Windows/VS Code."
            )

    path.mkdir(parents=True, exist_ok=True)


def build_coherent_metadata(supplier_id: str) -> dict:
    return {
        "bundle_id": f"bundle_{supplier_id}",
        "scenario": "normal_pdf_clean",
        "source_supplier_id": supplier_id,
        "expected_flags": [],
        "expected_status": "valid",
        "documents": [
            "purchase_order.pdf",
            "quote.pdf",
            "invoice.pdf",
        ],
    }


def collect_coherent_bundles() -> list[dict]:
    bundles = []

    if not RAW_COHERENT_DIR.exists():
        return bundles

    for supplier_dir in RAW_COHERENT_DIR.iterdir():
        if not supplier_dir.is_dir():
            continue

        purchase_order = supplier_dir / "purchase_order.pdf"
        quote = supplier_dir / "quote.pdf"
        invoice = supplier_dir / "invoice.pdf"

        if purchase_order.exists() and quote.exists() and invoice.exists():
            bundles.append(
                {
                    "bundle_name": supplier_dir.name,
                    "bundle_path": supplier_dir,
                    "bundle_type": "coherent",
                    "supplier_id": supplier_dir.name,
                    "scenario": "normal_pdf_clean",
                    "expected_status": "valid",
                    "expected_flags": [],
                }
            )

    return bundles


def collect_incoherent_bundles() -> list[dict]:
    bundles = []

    if not RAW_INCOHERENT_DIR.exists():
        return bundles

    for bundle_dir in RAW_INCOHERENT_DIR.iterdir():
        if not bundle_dir.is_dir():
            continue

        metadata_file = bundle_dir / "metadata.json"
        if not metadata_file.exists():
            continue

        with open(metadata_file, "r", encoding="utf-8") as f:
            metadata = json.load(f)

        bundles.append(
            {
                "bundle_name": bundle_dir.name,
                "bundle_path": bundle_dir,
                "bundle_type": "incoherent",
                "supplier_id": metadata.get("source_supplier_id", "unknown_supplier"),
                "scenario": metadata.get("scenario", "unknown"),
                "expected_status": metadata.get("expected_status", "invalid"),
                "expected_flags": metadata.get("expected_flags", []),
            }
        )

    return bundles


def compute_split_supplier_ids(supplier_ids: list[str]) -> tuple[set[str], set[str], set[str]]:
    supplier_ids = supplier_ids[:]
    random.Random(RANDOM_SEED).shuffle(supplier_ids)

    n = len(supplier_ids)

    if n == 0:
        return set(), set(), set()

    if n == 1:
        return {supplier_ids[0]}, set(), set()

    if n == 2:
        return {supplier_ids[0]}, {supplier_ids[1]}, set()

    train_count = max(1, int(n * 0.7))
    val_count = max(1, int(n * 0.15))
    test_count = n - train_count - val_count

    if test_count <= 0:
        test_count = 1
        if train_count > 1:
            train_count -= 1
        else:
            val_count -= 1

    train_ids = set(supplier_ids[:train_count])
    val_ids = set(supplier_ids[train_count:train_count + val_count])
    test_ids = set(supplier_ids[train_count + val_count:train_count + val_count + test_count])

    return train_ids, val_ids, test_ids


def create_split_dirs() -> None:
    for split_dir in [TRAIN_DIR, VAL_DIR, TEST_DIR]:
        ensure_clean_dir(split_dir)
        (split_dir / "coherent").mkdir(parents=True, exist_ok=True)
        (split_dir / "incoherent").mkdir(parents=True, exist_ok=True)


def destination_split_for_supplier(
    supplier_id: str,
    train_ids: set[str],
    val_ids: set[str],
    test_ids: set[str],
) -> str:
    if supplier_id in train_ids:
        return "train"
    if supplier_id in val_ids:
        return "val"
    if supplier_id in test_ids:
        return "test"
    return "train"


def split_dir_from_name(split_name: str) -> Path:
    if split_name == "train":
        return TRAIN_DIR
    if split_name == "val":
        return VAL_DIR
    return TEST_DIR


def copy_bundle(bundle: dict, split_name: str) -> dict:
    split_base = split_dir_from_name(split_name)
    bundle_type = bundle["bundle_type"]
    destination_dir = split_base / bundle_type / bundle["bundle_name"]

    if destination_dir.exists():
        shutil.rmtree(destination_dir)

    shutil.copytree(bundle["bundle_path"], destination_dir)

    # Pour les bundles cohérents, on crée un metadata.json si absent
    if bundle_type == "coherent":
        metadata_path = destination_dir / "metadata.json"
        if not metadata_path.exists():
            metadata = build_coherent_metadata(bundle["supplier_id"])
            with open(metadata_path, "w", encoding="utf-8") as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)

    return {
        "split": split_name,
        "bundle_type": bundle["bundle_type"],
        "bundle_name": bundle["bundle_name"],
        "supplier_id": bundle["supplier_id"],
        "scenario": bundle["scenario"],
        "expected_status": bundle["expected_status"],
        "expected_flags": json.dumps(bundle["expected_flags"], ensure_ascii=False),
        "path": str(destination_dir.relative_to(BASE_DIR)),
    }


def main() -> None:
    coherent_bundles = collect_coherent_bundles()
    incoherent_bundles = collect_incoherent_bundles()

    all_bundles = coherent_bundles + incoherent_bundles

    if not all_bundles:
        raise ValueError("Aucun bundle trouvé. Générez d'abord vos bundles cohérents/incohérents.")

    supplier_ids = sorted({bundle["supplier_id"] for bundle in all_bundles})
    train_ids, val_ids, test_ids = compute_split_supplier_ids(supplier_ids)

    create_split_dirs()

    manifest_rows = []

    for bundle in all_bundles:
        split_name = destination_split_for_supplier(
            bundle["supplier_id"],
            train_ids,
            val_ids,
            test_ids,
        )
        row = copy_bundle(bundle, split_name)
        manifest_rows.append(row)

    manifest_df = pd.DataFrame(manifest_rows)

    for split_name, split_dir in [("train", TRAIN_DIR), ("val", VAL_DIR), ("test", TEST_DIR)]:
        split_manifest = manifest_df[manifest_df["split"] == split_name]
        split_manifest.to_csv(split_dir / "manifest.csv", index=False, encoding="utf-8-sig")

    print("Dataset split terminé avec succès.")
    print(f"Train suppliers: {sorted(train_ids)}")
    print(f"Val suppliers: {sorted(val_ids)}")
    print(f"Test suppliers: {sorted(test_ids)}")
    print()
    print(f"Manifest train : {TRAIN_DIR / 'manifest.csv'}")
    print(f"Manifest val   : {VAL_DIR / 'manifest.csv'}")
    print(f"Manifest test  : {TEST_DIR / 'manifest.csv'}")


if __name__ == "__main__":
    main()