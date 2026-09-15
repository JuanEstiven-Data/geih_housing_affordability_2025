"""Check that the 2025 GEIH source files are complete and usable.

The audit answers three simple questions before the data are processed:

1. Are the eight expected modules present in CSV and SAV for every month?
2. Do the five modules used by this study contain the required variables?
3. Does the month stored in each required SAV agree with its folder?

The script only reads ``Raw`` and writes validation reports. It never changes
the original microdata.
"""

from __future__ import annotations

import json
import re
import sys
import unicodedata
from dataclasses import asdict, dataclass
from pathlib import Path

import pandas as pd
try:
    import pyreadstat
except ModuleNotFoundError:  # CSV fallback keeps the inventory audit usable.
    pyreadstat = None


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "Raw"
VALIDATION_DIR = PROJECT_ROOT / "Output" / "results" / "validation"

YEAR = 2025
MONTHS = range(1, 13)
FORMATS = ("sav", "csv")

# STEP 1: Define the expected files. Names are compared after removing accents,
# spaces and punctuation because DANE filenames vary slightly between months.
EXPECTED_MODULES = {
    "demographics": "caracteristicasgeneralesseguridadsocialensaludyeducacion",
    "household": "datosdelhogarylavivienda",
    "labor_force": "fuerzadetrabajo",
    "migration": "migracion",
    "not_employed": "noocupados",
    "employed": "ocupados",
    "other_work": "otrasformasdetrabajo",
    "other_income": "otrosingresoseimpuestos",
}

# STEP 2: Define the minimum variables required by the research questions.
# The construction script retains additional income components, but these are
# the variables that must exist for a source release to pass this first audit.
REQUIRED_COLUMNS = {
    "household": {
        "DIRECTORIO",
        "SECUENCIA_P",
        "HOGAR",
        "P5090",
        "P5100",
        "P5130",
        "P5140",
        "P6008",
        "AREA",
        "FEX_C18",
        "MES",
    },
    "demographics": {
        "DIRECTORIO",
        "SECUENCIA_P",
        "HOGAR",
        "ORDEN",
        "P6050",
        "P6040",
        "P3271",
        "P3042",
        "MES",
    },
    "employed": {
        "DIRECTORIO",
        "SECUENCIA_P",
        "HOGAR",
        "ORDEN",
        "INGLABO",
        "P6500",
        "P6750",
        "P7070",
        "MES",
    },
    "not_employed": {
        "DIRECTORIO",
        "SECUENCIA_P",
        "HOGAR",
        "ORDEN",
        "P7422",
        "P7422S1",
        "MES",
    },
    "other_income": {
        "DIRECTORIO",
        "SECUENCIA_P",
        "HOGAR",
        "ORDEN",
        "P7500S1A1",
        "P7500S2A1",
        "P7500S3A1",
        "P7510S1A1",
        "P7510S2A1",
        "P7510S3A1",
        "P7510S5A1",
        "MES",
    },
}


@dataclass
class FileAudit:
    month: int
    file_format: str
    folder: str
    module: str
    file_name: str | None
    exists: bool
    size_bytes: int | None
    duplicate_matches: int


@dataclass
class SchemaAudit:
    month: int
    module: str
    file_name: str
    schema_source: str
    readable: bool
    column_count: int | None
    row_count: int | None
    missing_columns: str
    month_values: str
    passed: bool
    error: str


def normalize_text(value: str) -> str:
    """Return a lowercase ASCII string without spaces or punctuation."""
    normalized = unicodedata.normalize("NFKD", value)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]", "", ascii_text.lower())


def identify_module(file_path: Path) -> str | None:
    """Match one source filename to its standardized module name."""
    normalized_stem = normalize_text(file_path.stem)
    for module, expected_stem in EXPECTED_MODULES.items():
        if normalized_stem == expected_stem:
            return module
    return None


def normalize_column(value: object) -> str:
    """Standardize a column name before comparing it with the dictionary."""
    return str(value).strip().upper()


def read_csv_header(file_path: Path) -> pd.Index:
    """Read a CSV header using the encodings found in the GEIH releases."""
    last_error: UnicodeDecodeError | None = None
    for encoding in ("cp1252", "utf-8-sig", "latin-1"):
        try:
            frame = pd.read_csv(
                file_path,
                sep=None,
                engine="python",
                encoding=encoding,
                nrows=0,
            )
            return frame.columns
        except UnicodeDecodeError as exc:
            last_error = exc
    raise last_error or UnicodeDecodeError("utf-8", b"", 0, 1, "unknown")


def audit_inventory() -> tuple[list[FileAudit], dict[tuple[int, str, str], Path]]:
    """Inventory all expected monthly files and record unique matches."""
    records: list[FileAudit] = []
    located_files: dict[tuple[int, str, str], Path] = {}

    for month in MONTHS:
        for file_format in FORMATS:
            folder = RAW_DIR / f"{month:02d}_{YEAR}_{file_format}"
            files = list(folder.glob(f"*.{file_format}")) if folder.exists() else []

            # Extension matching on Windows is case-insensitive, but this
            # fallback also keeps the audit portable.
            if folder.exists() and not files:
                files = [
                    path
                    for path in folder.iterdir()
                    if path.is_file() and path.suffix.lower() == f".{file_format}"
                ]

            module_matches: dict[str, list[Path]] = {
                module: [] for module in EXPECTED_MODULES
            }
            for file_path in files:
                module = identify_module(file_path)
                if module is not None:
                    module_matches[module].append(file_path)

            for module, matches in module_matches.items():
                match = matches[0] if len(matches) == 1 else None
                if match is not None:
                    located_files[(month, file_format, module)] = match

                records.append(
                    FileAudit(
                        month=month,
                        file_format=file_format,
                        folder=folder.name,
                        module=module,
                        file_name=match.name if match else None,
                        exists=len(matches) == 1,
                        size_bytes=match.stat().st_size if match else None,
                        duplicate_matches=max(0, len(matches) - 1),
                    )
                )

    return records, located_files


def audit_sav_schema(
    located_files: dict[tuple[int, str, str], Path],
) -> list[SchemaAudit]:
    """Check variables and survey month in each required SAV module."""
    records: list[SchemaAudit] = []

    for month in MONTHS:
        for module, required_columns in REQUIRED_COLUMNS.items():
            file_path = located_files.get((month, "sav", module))
            if file_path is None:
                records.append(
                    SchemaAudit(
                        month=month,
                        module=module,
                        file_name="",
                        schema_source="none",
                        readable=False,
                        column_count=None,
                        row_count=None,
                        missing_columns=",".join(sorted(required_columns)),
                        month_values="",
                        passed=False,
                        error="Required SAV file was not found uniquely.",
                    )
                )
                continue

            try:
                # CSV fallback allows a basic variable check when pyreadstat is
                # unavailable. It cannot validate SAV row counts or MES values.
                if pyreadstat is None:
                    csv_path = located_files.get((month, "csv", module))
                    if csv_path is None:
                        raise FileNotFoundError(
                            "pyreadstat is unavailable and no CSV counterpart was found."
                        )
                    header_columns = read_csv_header(csv_path)
                    available_columns = {
                        normalize_column(column) for column in header_columns
                    }
                    missing = sorted(required_columns - available_columns)
                    records.append(
                        SchemaAudit(
                            month=month,
                            module=module,
                            file_name=file_path.name,
                            schema_source="csv_fallback",
                            readable=True,
                            column_count=len(header_columns),
                            row_count=None,
                            missing_columns=",".join(missing),
                            month_values="not_checked",
                            passed=not missing,
                            error="",
                        )
                    )
                    continue

                # Metadata-only reading avoids loading all SAV columns.
                empty_frame, metadata = pyreadstat.read_sav(
                    file_path,
                    metadataonly=True,
                )
                del empty_frame
                available_columns = {
                    normalize_column(column) for column in metadata.column_names
                }
                missing = sorted(required_columns - available_columns)

                month_values: list[str] = []
                if "MES" in available_columns:
                    month_frame, _ = pyreadstat.read_sav(
                        file_path,
                        usecols=["MES"],
                        apply_value_formats=False,
                    )
                    month_values = sorted(
                        {
                            str(value).strip()
                            for value in month_frame["MES"].dropna().unique()
                        }
                    )

                accepted_month_values = {
                    str(month),
                    f"{month:02d}",
                    f"{float(month):.1f}",
                }
                month_is_consistent = (
                    bool(month_values)
                    and set(month_values).issubset(accepted_month_values)
                )

                records.append(
                    SchemaAudit(
                        month=month,
                        module=module,
                        file_name=file_path.name,
                        schema_source="sav_metadata",
                        readable=True,
                        column_count=len(metadata.column_names),
                        row_count=metadata.number_rows,
                        missing_columns=",".join(missing),
                        month_values=",".join(month_values),
                        passed=not missing and month_is_consistent,
                        error="" if month_is_consistent else "MES does not match folder.",
                    )
                )
            except Exception as exc:  # Report the file and continue the audit.
                records.append(
                    SchemaAudit(
                        month=month,
                        module=module,
                        file_name=file_path.name,
                        schema_source="sav_metadata" if pyreadstat else "csv_fallback",
                        readable=False,
                        column_count=None,
                        row_count=None,
                        missing_columns="",
                        month_values="",
                        passed=False,
                        error=f"{type(exc).__name__}: {exc}",
                    )
                )

    return records


def main() -> int:
    VALIDATION_DIR.mkdir(parents=True, exist_ok=True)

    # STEP 3: Run both checks and save detailed, reproducible reports.
    inventory, located_files = audit_inventory()
    schemas = audit_sav_schema(located_files)

    inventory_frame = pd.DataFrame(asdict(record) for record in inventory)
    schema_frame = pd.DataFrame(asdict(record) for record in schemas)

    inventory_path = VALIDATION_DIR / "source_file_inventory.csv"
    schema_path = VALIDATION_DIR / "source_schema_audit.csv"
    summary_path = VALIDATION_DIR / "source_audit_summary.json"

    inventory_frame.to_csv(inventory_path, index=False, encoding="utf-8-sig")
    schema_frame.to_csv(schema_path, index=False, encoding="utf-8-sig")

    expected_folder_count = len(list(MONTHS)) * len(FORMATS)
    existing_folders = sum(
        (RAW_DIR / f"{month:02d}_{YEAR}_{fmt}").is_dir()
        for month in MONTHS
        for fmt in FORMATS
    )
    expected_file_count = expected_folder_count * len(EXPECTED_MODULES)
    unique_expected_files = int(inventory_frame["exists"].sum())
    required_sav_count = len(list(MONTHS)) * len(REQUIRED_COLUMNS)
    located_required_sav = sum(
        (month, "sav", module) in located_files
        for month in MONTHS
        for module in REQUIRED_COLUMNS
    )
    passed_schema_checks = int(schema_frame["passed"].sum())

    # The audit passes only when all expected files and variables are present.
    passed = all(
        (
            existing_folders == expected_folder_count,
            unique_expected_files == expected_file_count,
            located_required_sav == required_sav_count,
            passed_schema_checks == required_sav_count,
        )
    )

    used_csv_fallback = pyreadstat is None
    status = (
        "PASS_WITH_WARNING"
        if passed and used_csv_fallback
        else "PASS"
        if passed
        else "FAIL"
    )
    summary = {
        "status": status,
        "schema_source": "csv_fallback" if used_csv_fallback else "sav_metadata",
        "expected_folders": expected_folder_count,
        "existing_folders": existing_folders,
        "expected_files": expected_file_count,
        "unique_expected_files": unique_expected_files,
        "required_sav_files": required_sav_count,
        "located_required_sav_files": located_required_sav,
        "schema_checks": required_sav_count,
        "passed_schema_checks": passed_schema_checks,
        "inventory_report": str(inventory_path.relative_to(PROJECT_ROOT)),
        "schema_report": str(schema_path.relative_to(PROJECT_ROOT)),
    }
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("GEIH 2025 SOURCE AUDIT")
    print(f"Folders:             {existing_folders}/{expected_folder_count}")
    print(f"Expected files:      {unique_expected_files}/{expected_file_count}")
    print(f"Required SAV files:  {located_required_sav}/{required_sav_count}")
    print(f"Schema checks:       {passed_schema_checks}/{required_sav_count}")
    print(f"RESULT: {summary['status']}")
    if used_csv_fallback:
        print("WARNING: pyreadstat is unavailable; schemas were checked from CSV counterparts.")
    print(f"Reports: {VALIDATION_DIR.relative_to(PROJECT_ROOT)}")

    if not passed:
        failed_files = inventory_frame.loc[
            ~inventory_frame["exists"],
            ["month", "file_format", "module", "duplicate_matches"],
        ]
        failed_schemas = schema_frame.loc[
            ~schema_frame["passed"],
            ["month", "module", "missing_columns", "month_values", "error"],
        ]
        if not failed_files.empty:
            print("\nMissing or duplicated files:")
            print(failed_files.to_string(index=False))
        if not failed_schemas.empty:
            print("\nFailed schema checks:")
            print(failed_schemas.to_string(index=False))

    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
