"""Answer Question 1 using GEIH 2025 household microdata.

Original question
-----------------
How much do households spend on housing and utilities, and what proportion
does this represent relative to their income?

The available GEIH files identify monthly rent or mortgage payments, but they
do not report monetary utility payments. Therefore, the operational response
measures the effective housing payment observed in the survey and documents
the missing utility amounts as a limitation.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

# Reuse the income construction already validated for Question 3. Importing
# these functions prevents two scripts from applying different income rules.
from answer_question_3 import (
    HOUSEHOLD_KEY,
    MONTHS_IN_YEAR,
    aggregate_income_by_household,
    build_person_income,
    classify_tenure,
    weighted_quantile,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
HOUSEHOLD_PATH = PROJECT_ROOT / "Output" / "household_core_2025.parquet"
PERSON_PATH = PROJECT_ROOT / "Output" / "person_components_2025.parquet"
RESULTS_DIR = PROJECT_ROOT / "Output" / "results" / "question_1"
VIZ_DIR = PROJECT_ROOT / "Viz"

CALI_AREA_CODE = "76"
TENURE_ORDER = [
    "Propietarios con vivienda pagada",
    "Propietarios que pagan su vivienda",
    "Arrendatarios",
    "Otras formas de tenencia",
]
SPECIAL_AMOUNT_CODES = [98, 99, 999_999_999]


def clean_payment(values: pd.Series) -> pd.Series:
    """Convert payment values to numeric and remove nonresponse codes."""
    numeric = pd.to_numeric(values, errors="coerce")
    numeric = numeric.mask(numeric.isin(SPECIAL_AMOUNT_CODES))
    # Use a regular float series so missing values can be assigned safely.
    return pd.Series(
        numeric.to_numpy(dtype=float, na_value=np.nan), index=values.index
    )


def build_analytical_households(
    households: pd.DataFrame, household_income: pd.DataFrame
) -> pd.DataFrame:
    """Join household income and calculate effective housing payments."""
    data = households.merge(
        household_income,
        on=HOUSEHOLD_KEY,
        how="left",
        validate="one_to_one",
    )

    if data["household_income"].isna().any():
        raise ValueError("Some households have no matching income record.")
    if not data["P6008"].eq(data["counted_household_members"]).all():
        raise ValueError("P6008 does not match the number of person records.")

    data["tenure_code"] = pd.to_numeric(
        data["P5090"], errors="coerce"
    ).astype("Int64")
    data["tenure_group"] = classify_tenure(data["tenure_code"])
    data = data.loc[data["tenure_group"].notna()].copy()
    data["annual_weight"] = data["FEX_C18"] / MONTHS_IN_YEAR

    clean_mortgage = clean_payment(data["P5100"])
    clean_rent = clean_payment(data["P5140"])

    # A zero for fully paid homeowners only means that the survey observes no
    # rent or mortgage instalment. It is not total housing expenditure.
    data["effective_payment"] = np.nan
    data.loc[data["tenure_code"].eq(1), "effective_payment"] = 0.0
    data.loc[data["tenure_code"].eq(2), "effective_payment"] = clean_mortgage
    data.loc[data["tenure_code"].eq(3), "effective_payment"] = clean_rent

    data["payment_status"] = "Pago efectivo no observable"
    data.loc[data["tenure_code"].eq(1), "payment_status"] = (
        "Sin arriendo o cuota de adquisición"
    )
    reported_payment = data["tenure_code"].isin([2, 3]) & data[
        "effective_payment"
    ].notna()
    missing_reported_payment = data["tenure_code"].isin([2, 3]) & data[
        "effective_payment"
    ].isna()
    data.loc[reported_payment, "payment_status"] = "Monto efectivo observado"
    data.loc[missing_reported_payment, "payment_status"] = (
        "Monto efectivo no informado"
    )

    valid_income = data["household_income"].gt(0) & ~data[
        "income_incomplete"
    ].fillna(True).astype(bool)
    data["valid_income"] = valid_income
    data["effective_burden_percent"] = np.where(
        valid_income & data["effective_payment"].notna(),
        100 * data["effective_payment"] / data["household_income"],
        np.nan,
    )
    return data


def add_distribution(
    result: dict[str, float | int | str],
    group: pd.DataFrame,
    column: str,
    output_name: str,
) -> None:
    """Add weighted Q1, median and Q3 to one summary row."""
    result[f"q1_{output_name}"] = weighted_quantile(
        group[column], group["annual_weight"], 0.25
    )
    result[f"median_{output_name}"] = weighted_quantile(
        group[column], group["annual_weight"], 0.50
    )
    result[f"q3_{output_name}"] = weighted_quantile(
        group[column], group["annual_weight"], 0.75
    )


def summarize_tenure(
    group: pd.DataFrame, geography: str, tenure_group: str
) -> dict[str, float | int | str]:
    """Summarize payment and burden for one geography-tenure group."""
    result: dict[str, float | int | str] = {
        "geography": geography,
        "tenure_group": tenure_group,
        "sample_household_months": len(group),
        "average_monthly_households": float(group["annual_weight"].sum()),
        "valid_payment_sample": int(group["effective_payment"].notna().sum()),
        "valid_burden_sample": int(
            group["effective_burden_percent"].notna().sum()
        ),
        "payment_data_status": (
            "n. d."
            if tenure_group == "Otras formas de tenencia"
            else "Disponible con las restricciones documentadas"
        ),
    }
    add_distribution(
        result, group, "effective_payment", "effective_payment_cop"
    )
    add_distribution(
        result,
        group,
        "effective_burden_percent",
        "effective_burden_percent",
    )
    return result


def build_summary(data: pd.DataFrame) -> pd.DataFrame:
    """Create the eight geography-tenure result rows."""
    geographies = {
        "Cali A.M.": data["AREA"].astype(str).eq(CALI_AREA_CODE),
        "Colombia (incluye Cali A.M.)": pd.Series(True, index=data.index),
    }
    rows = []
    for geography, geography_filter in geographies.items():
        geography_data = data.loc[geography_filter]
        for tenure_group in TENURE_ORDER:
            group = geography_data.loc[
                geography_data["tenure_group"].eq(tenure_group)
            ]
            rows.append(summarize_tenure(group, geography, tenure_group))
    return pd.DataFrame(rows)


def build_coverage(data: pd.DataFrame) -> pd.DataFrame:
    """Report how much of the universe has an identifiable cash payment."""
    status_order = [
        "Monto efectivo observado",
        "Sin arriendo o cuota de adquisición",
        "Monto efectivo no informado",
        "Pago efectivo no observable",
    ]
    geographies = {
        "Cali A.M.": data["AREA"].astype(str).eq(CALI_AREA_CODE),
        "Colombia (incluye Cali A.M.)": pd.Series(True, index=data.index),
    }
    rows = []
    for geography, geography_filter in geographies.items():
        geography_data = data.loc[geography_filter]
        total_weight = geography_data["annual_weight"].sum()
        for status in status_order:
            group = geography_data.loc[geography_data["payment_status"].eq(status)]
            group_weight = group["annual_weight"].sum()
            rows.append(
                {
                    "geography": geography,
                    "payment_status": status,
                    "sample_household_months": len(group),
                    "average_monthly_households": float(group_weight),
                    "weighted_share_percent": float(100 * group_weight / total_weight),
                }
            )
    return pd.DataFrame(rows)


def create_chart(summary: pd.DataFrame) -> Path:
    """Plot medians with Q1-Q3 intervals for payment and burden."""
    geographies = ["Cali A.M.", "Colombia (incluye Cali A.M.)"]
    colors = {geographies[0]: "#146C94", geographies[1]: "#D47B36"}
    short_labels = ["Pagada", "Pagando", "Arriendo", "Otras"]
    figure, axes = plt.subplots(1, 2, figsize=(13.5, 5.6))
    specs = [
        ("effective_payment_cop", "Pago efectivo mensual", "COP"),
        (
            "effective_burden_percent",
            "Carga habitacional efectiva",
            "% del ingreso del hogar",
        ),
    ]
    x = np.arange(len(TENURE_ORDER))

    for axis, (metric, title, ylabel) in zip(axes, specs):
        for offset, geography in zip([-0.10, 0.10], geographies):
            block = (
                summary.loc[summary["geography"].eq(geography)]
                .set_index("tenure_group")
                .reindex(TENURE_ORDER)
            )
            median = block[f"median_{metric}"].astype(float).to_numpy()
            q1 = block[f"q1_{metric}"].astype(float).to_numpy()
            q3 = block[f"q3_{metric}"].astype(float).to_numpy()
            valid = np.isfinite(median) & np.isfinite(q1) & np.isfinite(q3)
            axis.errorbar(
                x[valid] + offset,
                median[valid],
                yerr=np.vstack(
                    [median[valid] - q1[valid], q3[valid] - median[valid]]
                ),
                fmt="o",
                markersize=6,
                linewidth=1.5,
                capsize=4,
                color=colors[geography],
                label=geography,
            )
        axis.text(3, axis.get_ylim()[0], "n. d.", ha="center", va="bottom")
        axis.set_title(title, fontsize=12, fontweight="bold")
        axis.set_ylabel(ylabel)
        axis.set_xticks(x, short_labels)
        axis.grid(axis="y", alpha=0.2)
        axis.spines[["top", "right"]].set_visible(False)

    axes[0].yaxis.set_major_formatter(
        FuncFormatter(lambda value, position: f"${value / 1_000_000:.1f} M")
    )
    axes[0].legend(frameon=False, fontsize=8, loc="upper left")
    figure.suptitle(
        "Pago efectivo de vivienda y carga sobre el ingreso",
        fontsize=15,
        fontweight="bold",
    )
    figure.text(
        0.5,
        0.01,
        "Punto: mediana ponderada. Línea: Q1-Q3. n. d.: no disponible. GEIH 2025.",
        ha="center",
        fontsize=8.5,
        color="#555555",
    )
    figure.tight_layout(rect=[0, 0.05, 1, 0.94])
    chart_path = VIZ_DIR / "question_1_effective_payment.png"
    figure.savefig(chart_path, dpi=220, bbox_inches="tight")
    plt.close(figure)
    return chart_path


def validate_results(
    data: pd.DataFrame, summary: pd.DataFrame, coverage: pd.DataFrame
) -> dict[str, object]:
    """Run checks required to defend the estimates."""
    quartile_checks = []
    for metric in ["effective_payment_cop", "effective_burden_percent"]:
        available = summary[f"median_{metric}"].notna()
        ordered = (
            summary.loc[available, f"q1_{metric}"]
            .le(summary.loc[available, f"median_{metric}"])
            & summary.loc[available, f"median_{metric}"].le(
                summary.loc[available, f"q3_{metric}"]
            )
        )
        quartile_checks.append(bool(ordered.all()))

    other = data["tenure_code"].isin([4, 5, 6, 7])
    paid = data["tenure_code"].eq(1)
    coverage_totals = coverage.groupby("geography")[
        "weighted_share_percent"
    ].sum()
    status = "PASS" if all(
        [
            len(summary) == 8,
            all(quartile_checks),
            data.loc[other, "effective_payment"].isna().all(),
            data.loc[paid, "effective_payment"].eq(0).all(),
            np.allclose(coverage_totals.to_numpy(), 100),
        ]
    ) else "FAIL"

    return {
        "status": status,
        "months": sorted(data["survey_month"].astype(int).unique().tolist()),
        "national_sample_household_months": len(data),
        "cali_sample_household_months": int(
            data["AREA"].astype(str).eq(CALI_AREA_CODE).sum()
        ),
        "summary_rows": len(summary),
        "coverage_rows": len(coverage),
        "income_incomplete_households": int(data["income_incomplete"].sum()),
        "zero_or_negative_income_households": int(
            data["household_income"].le(0).sum()
        ),
        "mortgage_nonresponse_codes_98_99": int(
            data.loc[data["tenure_code"].eq(2), "P5100"].isin([98, 99]).sum()
        ),
        "rent_nonresponse_codes_98_99": int(
            data.loc[data["tenure_code"].eq(3), "P5140"].isin([98, 99]).sum()
        ),
        "other_tenure_cash_payment_share_estimable": False,
        "other_tenure_cash_payment_share_note": (
            "The questionnaire does not ask these households for an effective "
            "payment. Their cash-payment proportion is not estimable."
        ),
        "nd_definition": (
            "n. d. means no disponible. It marks information that the survey "
            "does not collect or cannot estimate; it is not a numeric zero."
        ),
        "summary_statistics": "weighted Q1, median and Q3",
        "effective_payment_definition": (
            "P5100 for homeowners paying, P5140 for tenants, zero rent or "
            "mortgage instalment for fully paid homeowners, and n. d. for other tenure"
        ),
        "utilities_included": False,
        "utilities_limitation": (
            "GEIH records access to some utilities but not their monetary payments."
        ),
        "country_reference": "Colombia includes Cali A.M.; results are not added together.",
    }


def main() -> int:
    """Execute the complete Question 1 workflow."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    VIZ_DIR.mkdir(parents=True, exist_ok=True)

    households = pd.read_parquet(HOUSEHOLD_PATH)
    people = pd.read_parquet(PERSON_PATH)
    if households.duplicated(HOUSEHOLD_KEY).any():
        raise ValueError("The household key is not unique.")
    if people.duplicated(HOUSEHOLD_KEY + ["ORDEN"]).any():
        raise ValueError("The person key is not unique.")

    people = build_person_income(people)
    sentinel_columns = [
        "P7500S1A1",
        "P7500S2A1",
        "P7500S3A1",
        "P7510S1A1",
        "P7510S2A1",
        "P7510S3A1",
        "P7510S5A1",
    ]
    sentinel_counts = {
        column: int(people[column].eq(999_999_999).sum())
        for column in sentinel_columns
        if people[column].eq(999_999_999).any()
    }
    household_income = aggregate_income_by_household(people)
    analytical = build_analytical_households(households, household_income)
    summary = build_summary(analytical)
    coverage = build_coverage(analytical)
    chart_path = create_chart(summary)
    validation = validate_results(analytical, summary, coverage)
    validation["income_value_999999999_records"] = sentinel_counts
    validation["income_value_999999999_total"] = sum(sentinel_counts.values())
    validation["income_value_999999999_interpretation"] = (
        "Undocumented extreme value treated operationally as missing; it is not "
        "assigned the documented meanings of codes 98 or 99."
    )

    if validation["status"] != "PASS":
        raise ValueError("Question 1 validation failed.")

    analytical.to_parquet(
        RESULTS_DIR / "analytical_households_question_1.parquet", index=False
    )
    summary.to_csv(
        RESULTS_DIR / "effective_payment_summary.csv", index=False, encoding="utf-8-sig"
    )
    coverage.to_csv(
        RESULTS_DIR / "payment_coverage.csv", index=False, encoding="utf-8-sig"
    )
    validation.update(
        {
            "analytical_output": str(
                (RESULTS_DIR / "analytical_households_question_1.parquet").relative_to(
                    PROJECT_ROOT
                )
            ),
            "summary_output": str(
                (RESULTS_DIR / "effective_payment_summary.csv").relative_to(PROJECT_ROOT)
            ),
            "coverage_output": str(
                (RESULTS_DIR / "payment_coverage.csv").relative_to(PROJECT_ROOT)
            ),
            "chart_output": str(chart_path.relative_to(PROJECT_ROOT)),
        }
    )
    (RESULTS_DIR / "validation.json").write_text(
        json.dumps(validation, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    display_columns = [
        "geography",
        "tenure_group",
        "sample_household_months",
        "q1_effective_payment_cop",
        "median_effective_payment_cop",
        "q3_effective_payment_cop",
        "q1_effective_burden_percent",
        "median_effective_burden_percent",
        "q3_effective_burden_percent",
    ]
    print("QUESTION 1: EFFECTIVE HOUSING PAYMENT")
    print(summary[display_columns].round(2).to_string(index=False))
    print("\nRESULT: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
