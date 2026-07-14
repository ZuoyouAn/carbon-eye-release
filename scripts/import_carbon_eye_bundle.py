from __future__ import annotations

import argparse
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from shutil import copy2


SOURCE_FILES = (
    "sip_electricity_official.csv",
    "sip_electricity_missing_years_template.csv",
    "jiangsu_electricity_emission_factors.csv",
    "sip_electricity_scope2_estimate.csv",
    "sip_economic_activity_official.csv",
    "sip_economic_carbon_intensity.csv",
    "sip_monitoring_sites.csv",
    "sip_characteristic_air_snapshot.csv",
    "industry_profile.csv",
    "source_registry.csv",
    "weather_field_schema.csv",
)

APPLICATION_JSON_FILES = (
    "park_electricity_emissions.json",
    "sip_economic_carbon_intensity.json",
    "park_environment_snapshot.json",
    "industry_profile.json",
    "source_registry.json",
    "data_manifest.json",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def copy_required(source_dir: Path, target_dir: Path, names: tuple[str, ...]) -> list[Path]:
    target_dir.mkdir(parents=True, exist_ok=True)
    copied: list[Path] = []
    for name in names:
        source = source_dir / name
        if not source.is_file():
            raise FileNotFoundError(f"Required bundle file is missing: {source}")
        target = target_dir / name
        copy2(source, target)
        copied.append(target)
    return copied


def write_report(project_root: Path, copied: list[Path], pdfs: list[Path]) -> None:
    lines = [
        "# Carbon Eye Data Import Report",
        "",
        f"Generated: {datetime.now(timezone.utc).astimezone().isoformat(timespec='seconds')}",
        "",
        "The files below were copied from the approved data bundle without value changes.",
        "",
        "## Imported Data",
        "",
        "| Destination | SHA-256 | Bytes |",
        "| --- | --- | ---: |",
    ]
    for path in copied:
        relative = path.relative_to(project_root).as_posix()
        lines.append(f"| `{relative}` | `{sha256(path)}` | {path.stat().st_size} |")

    lines.extend(["", "## Official Source Documents", ""])
    if pdfs:
        lines.extend(["| Destination | SHA-256 | Bytes |", "| --- | --- | ---: |"])
        for path in pdfs:
            relative = path.relative_to(project_root).as_posix()
            lines.append(f"| `{relative}` | `{sha256(path)}` | {path.stat().st_size} |")
    else:
        lines.append("No PDF was copied. Consult `backend/data/carbon_eye/source_registry.json` for official URLs.")

    lines.extend(
        [
            "",
            "## Import Boundary",
            "",
            "This import preserves the supplied values. It does not fill the 2020-2022 electricity-data gap or create any new emissions observations.",
            "",
        ]
    )
    (project_root / "DATA_IMPORT_REPORT.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Copy and verify the approved Carbon Eye data bundle.")
    parser.add_argument("--bundle-root", type=Path, required=True)
    parser.add_argument("--project-root", type=Path, required=True)
    args = parser.parse_args()

    bundle_root = args.bundle_root.resolve()
    project_root = args.project_root.resolve()
    data_dir = bundle_root / "01_data"
    source_docs_dir = bundle_root / "00_sources"
    carbon_dir = project_root / "backend" / "data" / "carbon_eye"

    copied = copy_required(data_dir, carbon_dir / "sources", SOURCE_FILES)
    copied.extend(copy_required(data_dir, carbon_dir, APPLICATION_JSON_FILES))

    target_docs = project_root / "docs" / "data_sources"
    target_docs.mkdir(parents=True, exist_ok=True)
    pdfs: list[Path] = []
    for source in source_docs_dir.glob("*.pdf"):
        target = target_docs / source.name
        copy2(source, target)
        pdfs.append(target)

    write_report(project_root, copied, pdfs)
    print(f"Imported {len(copied)} data files and {len(pdfs)} PDF files.")


if __name__ == "__main__":
    main()
