"""Build the two intermediate datasets needed for the housing analysis.

Input
-----
The script reads the CSV version of five monthly GEIH modules. DANE supplies
the same microdata as CSV and SAV. CSV is used here because it is easier to
read with pandas; the source audit checks that the required variables also
exist in the SAV files.

Output
------
1. ``household_core_2025.parquet``: one row per household and month.
2. ``person_components_2025.parquet``: one row per person and month.

Two files are necessary at this stage because housing payments are reported
once per household, while income is reported by each person. Joining them
before adding personal income would repeat the same housing payment for every
household member. A later script will add income by household and then create
one analytical household-level dataset.
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from audit_source_files import audit_inventory


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "Output"
VALIDATION_DIR = OUTPUT_DIR / "results" / "validation"

YEAR = 2025
MONTHS = range(1, 13)

# These variables identify the same observation across GEIH modules.
# The survey period is included because household identifiers may repeat over
# different monthly files.
HOUSEHOLD_KEY = [
    "survey_year",
    "survey_month",
    "DIRECTORIO",
    "SECUENCIA_P",
    "HOGAR",
]
PERSON_KEY = HOUSEHOLD_KEY + ["ORDEN"]

# STEP 1: Select only the questions needed for the first three objectives.
# Household module: location, survey weight, tenure and housing payments.
HOUSEHOLD_COLUMNS = [
    "PERIODO",
    "PER",
    "MES",
    "DIRECTORIO",
    "SECUENCIA_P",
    "HOGAR",
    "AREA",
    "CLASE",
    "DPTO",
    "FEX_C18",
    "P5090",
    "P5100",
    "P5110",
    "P5130",
    "P5140",
    "P6008",
]

# Demographic module: household relationship, age, sex and education.
DEMOGRAPHIC_COLUMNS = [
    "MES",
    "DIRECTORIO",
    "SECUENCIA_P",
    "HOGAR",
    "ORDEN",
    "P6050",
    "P6040",
    "P3271",
    "P3042",
]

# Employed module: reported labour income and its possible components.
# Components are kept separately until the income definition is documented.
EMPLOYED_COLUMNS = [
    "MES",
    "DIRECTORIO",
    "SECUENCIA_P",
    "HOGAR",
    "ORDEN",
    "INGLABO",
    "P6430",
    "P6500",
    "P6510",
    "P6510S1",
    "P6510S2",
    "P6590",
    "P6590S1",
    "P6600",
    "P6600S1",
    "P6610",
    "P6610S1",
    "P6620",
    "P6620S1",
    "P6585S1",
    "P6585S1A1",
    "P6585S1A2",
    "P6585S2",
    "P6585S2A1",
    "P6585S2A2",
    "P6585S3",
    "P6585S3A1",
    "P6585S3A2",
    "P6585S4",
    "P6585S4A1",
    "P6585S4A2",
    "P6545",
    "P6545S1",
    "P6545S2",
    "P6580",
    "P6580S1",
    "P6580S2",
    "P6630S1",
    "P6630S1A1",
    "P6630S2",
    "P6630S2A1",
    "P6630S3",
    "P6630S3A1",
    "P6630S4",
    "P6630S4A1",
    "P6630S6",
    "P6630S6A1",
    "P3051",
    "P3054",
    "P3054S1",
    "P3055",
    "P3055S1",
    "P3057",
    "P6760",
    "P6750",
    "P3073",
    "P550",
    "P7070",
]

# Not-employed module: income reported by people outside employment.
NOT_EMPLOYED_COLUMNS = [
    "MES",
    "DIRECTORIO",
    "SECUENCIA_P",
    "HOGAR",
    "ORDEN",
    "DSI",
    "FFT",
    "P7422",
    "P7422S1",
]

# Other-income module: rents, pensions, transfers, aid and investment income.
OTHER_INCOME_COLUMNS = [
    "MES",
    "DIRECTORIO",
    "SECUENCIA_P",
    "HOGAR",
    "ORDEN",
    "P7495",
    "P7500S1",
    "P7500S1A1",
    "P7500S2",
    "P7500S2A1",
    "P7500S3",
    "P7500S3A1",
    "P7505",
    "P7510S1",
    "P7510S1A1",
    "P7510S2",
    "P7510S2A1",
    "P7510S3",
    "P7510S3A1",
    "P7510S5",
    "P7510S5A1",
]

MODULE_COLUMNS = {
    "household": HOUSEHOLD_COLUMNS,
    "demographics": DEMOGRAPHIC_COLUMNS,
    "employed": EMPLOYED_COLUMNS,
    "not_employed": NOT_EMPLOYED_COLUMNS,
    "other_income": OTHER_INCOME_COLUMNS,
}


def detect_csv_format(file_path: Path) -> tuple[str, str]:
    """Identify the text encoding and separator used by one CSV file."""
    # DANE's 2025 CSV exports may contain Windows-1252 characters after an
    # ASCII-only prefix, so UTF-8 sampling can produce a false positive.
    for encoding in ("cp1252", "utf-8-sig", "latin-1"):
        try:
            with file_path.open("r", encoding=encoding) as stream:
                sample = stream.read(65_536)
        except UnicodeDecodeError:
            continue
        delimiter = csv.Sniffer().sniff(sample, delimiters=",;|\t").delimiter
        return encoding, delimiter
    raise UnicodeError(f"Unable to detect encoding for {file_path}")


def clean_identifier(series: pd.Series) -> pd.Series:
    """Store identifiers as clean text so monthly joins are stable."""
    return (
        series.astype("string")
        .str.strip()
        .str.replace(r"\.0$", "", regex=True)
        .replace({"": pd.NA, "nan": pd.NA, "None": pd.NA})
    )


def read_selected_csv(
    file_path: Path,
    selected_columns: list[str],
    month: int,
) -> pd.DataFrame:
    """Read selected columns and standardize their names and data types."""
    encoding, delimiter = detect_csv_format(file_path)
    header = pd.read_csv(
        file_path,
        sep=delimiter,
        encoding=encoding,
        nrows=0,
    )
    header_lookup = {str(column).strip().upper(): column for column in header.columns}
    missing = [column for column in selected_columns if column not in header_lookup]
    if missing:
        raise ValueError(
            f"Missing columns in {file_path.name}: {', '.join(sorted(missing))}"
        )

    source_columns = [header_lookup[column] for column in selected_columns]
    frame = pd.read_csv(
        file_path,
        sep=delimiter,
        encoding=encoding,
        usecols=source_columns,
        low_memory=False,
    )
    frame = frame.rename(columns=lambda column: str(column).strip().upper())

    # The month written inside the file must agree with its source folder.
    source_month = pd.to_numeric(frame["MES"], errors="coerce")
    unexpected_months = sorted(
        source_month.dropna().loc[source_month.dropna().ne(month)].unique().tolist()
    )
    if unexpected_months:
        raise ValueError(
            f"MES does not match folder {month:02d}: {unexpected_months}"
        )

    frame = frame.drop(columns="MES")
    frame.insert(0, "survey_year", YEAR)
    frame.insert(1, "survey_month", month)

    for column in ("DIRECTORIO", "SECUENCIA_P", "HOGAR", "ORDEN", "AREA", "DPTO"):
        if column in frame.columns:
            frame[column] = clean_identifier(frame[column])

    # Identifiers stay as text. Survey answers and amounts become numeric.
    numeric_columns = [
        column
        for column in frame.columns
        if column
        not in {
            "DIRECTORIO",
            "SECUENCIA_P",
            "HOGAR",
            "ORDEN",
            "AREA",
            "DPTO",
        }
    ]
    for column in numeric_columns:
        frame[column] = pd.to_numeric(frame[column], errors="coerce").astype("Float64")

    frame["survey_year"] = frame["survey_year"].astype("int16")
    frame["survey_month"] = frame["survey_month"].astype("int8")
    return frame


def assert_unique(frame: pd.DataFrame, key: list[str], label: str) -> None:
    """Stop the process if a dataset has missing or repeated identifiers."""
    missing_key = frame[key].isna().any(axis=1)
    if missing_key.any():
        raise ValueError(f"{label}: {int(missing_key.sum())} rows have incomplete keys.")

    duplicate_count = int(frame.duplicated(key, keep=False).sum())
    if duplicate_count:
        raise ValueError(f"{label}: {duplicate_count} rows have duplicated keys.")


def count_unmatched(
    source: pd.DataFrame,
    target: pd.DataFrame,
    key: list[str],
) -> int:
    """Count source records that do not exist in the reference dataset."""
    source_keys = pd.MultiIndex.from_frame(source[key])
    target_keys = pd.MultiIndex.from_frame(target[key])
    return int((~source_keys.isin(target_keys)).sum())


def write_parquet_part(
    writer: pq.ParquetWriter | None,
    frame: pd.DataFrame,
    output_path: Path,
) -> pq.ParquetWriter:
    """Append one month to a Parquet file without keeping the year in memory."""
    table = pa.Table.from_pandas(frame, preserve_index=False)
    if writer is None:
        writer = pq.ParquetWriter(output_path, table.schema, compression="snappy")
    writer.write_table(table)
    return writer


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    VALIDATION_DIR.mkdir(parents=True, exist_ok=True)

    # STEP 2: Locate the five modules for every month before reading data.
    _, located_files = audit_inventory()
    missing_files = [
        (month, module)
        for month in MONTHS
        for module in MODULE_COLUMNS
        if (month, "csv", module) not in located_files
    ]
    if missing_files:
        raise FileNotFoundError(f"Missing required CSV modules: {missing_files}")

    household_path = OUTPUT_DIR / "household_core_2025.parquet"
    person_path = OUTPUT_DIR / "person_components_2025.parquet"
    household_temp = household_path.with_suffix(".tmp.parquet")
    person_temp = person_path.with_suffix(".tmp.parquet")

    household_writer: pq.ParquetWriter | None = None
    person_writer: pq.ParquetWriter | None = None
    validation_records: list[dict[str, int | str]] = []

    # STEP 3: Read, validate, join and save one month at a time. Monthly
    # processing is the only relatively advanced part of this script and keeps
    # memory use low when working with the complete national microdata.
    try:
        for month in MONTHS:
            frames = {
                module: read_selected_csv(
                    located_files[(month, "csv", module)],
                    columns,
                    month,
                )
                for module, columns in MODULE_COLUMNS.items()
            }

            household = frames["household"]
            demographics = frames["demographics"]
            employed = frames["employed"]
            not_employed = frames["not_employed"]
            other_income = frames["other_income"]

            # Every household or person must appear only once in its module.
            assert_unique(household, HOUSEHOLD_KEY, f"{month:02d} household")
            for label, frame in (
                ("demographics", demographics),
                ("employed", employed),
                ("not_employed", not_employed),
                ("other_income", other_income),
            ):
                assert_unique(frame, PERSON_KEY, f"{month:02d} {label}")

            # Personal income modules must be subsets of the demographic file.
            employed_unmatched = count_unmatched(
                employed, demographics, PERSON_KEY
            )
            not_employed_unmatched = count_unmatched(
                not_employed, demographics, PERSON_KEY
            )
            other_income_unmatched = count_unmatched(
                other_income, demographics, PERSON_KEY
            )
            labor_overlap = len(
                pd.MultiIndex.from_frame(employed[PERSON_KEY]).intersection(
                    pd.MultiIndex.from_frame(not_employed[PERSON_KEY])
                )
            )

            if any(
                (
                    employed_unmatched,
                    not_employed_unmatched,
                    other_income_unmatched,
                    labor_overlap,
                )
            ):
                raise ValueError(
                    f"Month {month:02d} has invalid person-module relationships: "
                    f"employed_unmatched={employed_unmatched}, "
                    f"not_employed_unmatched={not_employed_unmatched}, "
                    f"other_income_unmatched={other_income_unmatched}, "
                    f"labor_overlap={labor_overlap}."
                )

            # Flags distinguish a missing module record from a reported zero.
            employed = employed.assign(is_employed_record=True)
            not_employed = not_employed.assign(is_not_employed_record=True)
            other_income = other_income.assign(has_other_income_record=True)

            # Demographics is the reference population. Left joins retain every
            # person even when an income module does not apply to that person.
            person_components = demographics.merge(
                employed,
                on=PERSON_KEY,
                how="left",
                validate="one_to_one",
            )
            person_components = person_components.merge(
                not_employed,
                on=PERSON_KEY,
                how="left",
                validate="one_to_one",
            )
            person_components = person_components.merge(
                other_income,
                on=PERSON_KEY,
                how="left",
                validate="one_to_one",
            )

            for flag in (
                "is_employed_record",
                "is_not_employed_record",
                "has_other_income_record",
            ):
                person_components[flag] = person_components[flag].fillna(False).astype(
                    "bool"
                )

            assert_unique(
                person_components,
                PERSON_KEY,
                f"{month:02d} combined persons",
            )

            # Housing and person records remain separate because their units of
            # observation differ at this stage.
            household_writer = write_parquet_part(
                household_writer,
                household,
                household_temp,
            )
            person_writer = write_parquet_part(
                person_writer,
                person_components,
                person_temp,
            )

            validation_records.append(
                {
                    "survey_month": month,
                    "household_rows": len(household),
                    "demographic_rows": len(demographics),
                    "employed_rows": len(employed),
                    "not_employed_rows": len(not_employed),
                    "other_income_rows": len(other_income),
                    "combined_person_rows": len(person_components),
                    "employed_unmatched": employed_unmatched,
                    "not_employed_unmatched": not_employed_unmatched,
                    "other_income_unmatched": other_income_unmatched,
                    "labor_overlap": labor_overlap,
                }
            )
            print(
                f"Month {month:02d}: "
                f"{len(household):,} households, "
                f"{len(person_components):,} persons"
            )
    finally:
        if household_writer is not None:
            household_writer.close()
        if person_writer is not None:
            person_writer.close()

    # STEP 4: Replace final outputs only after all twelve months succeed.
    household_temp.replace(household_path)
    person_temp.replace(person_path)

    validation_frame = pd.DataFrame(validation_records)
    validation_path = VALIDATION_DIR / "selected_modules_build.csv"
    validation_frame.to_csv(validation_path, index=False, encoding="utf-8-sig")

    summary = {
        "status": "PASS",
        "input_format": "csv",
        "months_processed": len(validation_frame),
        "household_rows": int(validation_frame["household_rows"].sum()),
        "person_rows": int(validation_frame["combined_person_rows"].sum()),
        "household_unit": "one household-month",
        "person_unit": "one person-month",
        "separate_outputs_reason": (
            "Housing payments are measured at household level and income "
            "components are measured at person level."
        ),
        "household_output": str(household_path.relative_to(PROJECT_ROOT)),
        "person_output": str(person_path.relative_to(PROJECT_ROOT)),
        "validation_output": str(validation_path.relative_to(PROJECT_ROOT)),
        "income_status": "Components retained separately; household income not yet calculated.",
    }
    summary_path = VALIDATION_DIR / "selected_modules_build_summary.json"
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("\nSELECTED MODULE BUILD")
    print("Input format:     CSV")
    print(f"Months processed: {summary['months_processed']}/12")
    print(f"Household rows:   {summary['household_rows']:,}")
    print(f"Person rows:      {summary['person_rows']:,}")
    print("RESULT: PASS")
    print(f"Households: {summary['household_output']}")
    print(f"Persons:    {summary['person_output']}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(f"BUILD FAILED: {type(exc).__name__}: {exc}", file=sys.stderr)
        sys.exit(1)
