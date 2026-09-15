"""Answer Question 3 for Cali A.M. and Colombia using GEIH 2025.

Question
--------
What gaps exist between tenants, homeowners paying for their dwelling,
homeowners whose dwelling is fully paid, and other tenure arrangements?
How do these gaps vary with the education of the household head?

The script produces two levels of analysis:

1. General comparison across tenure groups.
2. Comparison across tenure groups within four education groups.

Medians are the main statistics. First and third weighted quartiles accompany
every median so dispersion remains visible without relying on averages that are
sensitive to the long right tail of income and housing costs.
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


PROJECT_ROOT = Path(__file__).resolve().parents[1]
HOUSEHOLD_PATH = PROJECT_ROOT / "Output" / "household_core_2025.parquet"
PERSON_PATH = PROJECT_ROOT / "Output" / "person_components_2025.parquet"
RESULTS_DIR = PROJECT_ROOT / "Output" / "results" / "question_3"
VIZ_DIR = PROJECT_ROOT / "Viz"

CALI_AREA_CODE = "76"
MONTHS_IN_YEAR = 12
HOUSEHOLD_KEY = [
    "survey_year",
    "survey_month",
    "DIRECTORIO",
    "SECUENCIA_P",
    "HOGAR",
]

TENURE_ORDER = [
    "Propietarios con vivienda pagada",
    "Propietarios que pagan su vivienda",
    "Arrendatarios",
    "Otras formas de tenencia",
]

EDUCATION_ORDER = [
    "Primaria o menos",
    "Secundaria y media",
    "Técnico, tecnólogo o pregrado",
    "Postgrado",
]

MONTHLY_OTHER_INCOME = [
    ("P7500S1", "P7500S1A1"),  # Rent received from assets.
    ("P7500S2", "P7500S2A1"),  # Pensions.
    ("P7500S3", "P7500S3A1"),  # Alimony.
]

ANNUAL_OTHER_INCOME = [
    ("P7510S1", "P7510S1A1"),  # Transfers from households in Colombia.
    ("P7510S2", "P7510S2A1"),  # Transfers from households abroad.
    ("P7510S3", "P7510S3A1"),  # Institutional aid.
    ("P7510S5", "P7510S5A1"),  # Interest, dividends and investment income.
]

MISSING_AMOUNT_CODES = [98, 99, 999_999_999]


def weighted_quantile(
    values: pd.Series, weights: pd.Series, quantile: float
) -> float:
    """Return a weighted quantile between zero and one."""
    valid = values.notna() & weights.notna() & weights.gt(0)
    if not valid.any():
        return float("nan")

    ordered = pd.DataFrame(
        {
            "value": values.loc[valid].astype(float),
            "weight": weights.loc[valid].astype(float),
        }
    ).sort_values("value")
    cutoff = ordered["weight"].sum() * quantile
    return float(
        ordered.loc[ordered["weight"].cumsum().ge(cutoff), "value"].iloc[0]
    )


def weighted_share(condition: pd.Series, weights: pd.Series) -> float:
    """Calculate the weighted percentage satisfying a condition."""
    valid = condition.notna() & weights.notna() & weights.gt(0)
    if not valid.any():
        return float("nan")
    numerator = weights.loc[valid & condition.fillna(False)].sum()
    denominator = weights.loc[valid].sum()
    return float(100 * numerator / denominator)


def clean_reported_amount(values: pd.Series) -> pd.Series:
    """Replace GEIH nonresponse codes with missing values."""
    numeric = pd.to_numeric(values, errors="coerce")
    numeric = numeric.mask(numeric.isin(MISSING_AMOUNT_CODES))
    return pd.Series(
        numeric.to_numpy(dtype=float, na_value=np.nan), index=values.index
    )


def conditional_income_component(
    people: pd.DataFrame,
    indicator: str,
    amount: str,
    monthly_divisor: int = 1,
) -> tuple[pd.Series, pd.Series]:
    """Create one income component and flag unanswered positive reports."""
    clean_amount = clean_reported_amount(people[amount])
    reported_yes = people[indicator].eq(1).fillna(False)
    reported_unknown = people[indicator].eq(9).fillna(False)

    component = pd.Series(0.0, index=people.index)
    component.loc[reported_yes] = (
        clean_amount.loc[reported_yes].fillna(0).astype(float) / monthly_divisor
    )
    incomplete = reported_unknown | (reported_yes & clean_amount.isna())
    return component, incomplete


def build_person_income(people: pd.DataFrame) -> pd.DataFrame:
    """Construct current monthly monetary income for every person."""
    employed = people["is_employed_record"].fillna(False).astype(bool)
    unpaid_family_worker = employed & people["P6430"].eq(6).fillna(False)
    clean_labour_income = clean_reported_amount(people["INGLABO"])

    # Missing INGLABO is zero when the employed module does not apply or when
    # the person is an unpaid family worker. Other employed records with a
    # missing constructed labour income are marked as incomplete.
    unexpected_missing_labour = (
        employed & ~unpaid_family_worker & clean_labour_income.isna()
    )
    people["person_income"] = clean_labour_income.fillna(0).astype(float)
    people["income_incomplete"] = unexpected_missing_labour

    # P7070 is not added because it is already incorporated in INGLABO.
    occasional_work, occasional_unknown = conditional_income_component(
        people, "P7422", "P7422S1"
    )
    people["person_income"] += occasional_work
    people["income_incomplete"] |= occasional_unknown

    for indicator, amount in MONTHLY_OTHER_INCOME:
        component, incomplete = conditional_income_component(
            people, indicator, amount
        )
        people["person_income"] += component
        people["income_incomplete"] |= incomplete

    for indicator, amount in ANNUAL_OTHER_INCOME:
        component, incomplete = conditional_income_component(
            people, indicator, amount, monthly_divisor=12
        )
        people["person_income"] += component
        people["income_incomplete"] |= incomplete

    return people


def aggregate_income_by_household(people: pd.DataFrame) -> pd.DataFrame:
    """Add the incomes of all people belonging to the same household."""
    return (
        people.groupby(HOUSEHOLD_KEY, as_index=False)
        .agg(
            household_income=("person_income", "sum"),
            income_incomplete=("income_incomplete", "max"),
            counted_household_members=("ORDEN", "size"),
        )
    )


def select_household_heads(people: pd.DataFrame) -> pd.DataFrame:
    """Keep the education reported by the unique household head."""
    heads = people.loc[
        people["P6050"].eq(1), HOUSEHOLD_KEY + ["P3042"]
    ].copy()
    if heads.duplicated(HOUSEHOLD_KEY).any():
        raise ValueError("Some households have more than one household head.")
    return heads.rename(columns={"P3042": "head_education_code"})


def classify_tenure(codes: pd.Series) -> pd.Series:
    """Group the seven GEIH tenure codes into four analytical categories."""
    numeric_codes = pd.to_numeric(codes, errors="coerce")
    labels = np.select(
        [
            numeric_codes.eq(1),
            numeric_codes.eq(2),
            numeric_codes.eq(3),
            numeric_codes.isin([4, 5, 6, 7]),
        ],
        TENURE_ORDER,
        default=None,
    )
    return pd.Series(labels, index=codes.index, dtype="object")


def classify_education(codes: pd.Series) -> pd.Series:
    """Create the four education groups defined for the household head."""
    numeric_codes = pd.to_numeric(codes, errors="coerce")
    labels = np.select(
        [
            numeric_codes.isin([1, 2, 3]),
            numeric_codes.isin([4, 5, 6, 7]),
            numeric_codes.isin([8, 9, 10]),
            numeric_codes.isin([11, 12, 13]),
        ],
        EDUCATION_ORDER,
        default=None,
    )
    return pd.Series(labels, index=codes.index, dtype="object")


def build_analytical_households(
    households: pd.DataFrame,
    household_income: pd.DataFrame,
    household_heads: pd.DataFrame,
) -> pd.DataFrame:
    """Join household information and calculate affordability indicators."""
    data = households.merge(
        household_income,
        on=HOUSEHOLD_KEY,
        how="left",
        validate="one_to_one",
    ).merge(
        household_heads,
        on=HOUSEHOLD_KEY,
        how="left",
        validate="one_to_one",
    )

    if data["household_income"].isna().any():
        raise ValueError("Some households have no matching income record.")
    if data["head_education_code"].isna().all():
        raise ValueError("No household-head education records were joined.")
    if not data["P6008"].eq(data["counted_household_members"]).all():
        raise ValueError("P6008 does not match the number of person records.")

    data["tenure_code"] = pd.to_numeric(data["P5090"], errors="coerce").astype(
        "Int64"
    )
    data["tenure_group"] = classify_tenure(data["tenure_code"])
    data = data.loc[data["tenure_group"].notna()].copy()
    data["education_group"] = classify_education(data["head_education_code"])
    data["annual_weight"] = data["FEX_C18"] / MONTHS_IN_YEAR

    clean_mortgage = clean_reported_amount(data["P5100"])
    clean_estimated_rent = clean_reported_amount(data["P5130"])
    clean_rent = clean_reported_amount(data["P5140"])

    # Effective cash payment is unavailable for other tenure arrangements.
    data["effective_payment"] = np.nan
    data.loc[data["tenure_code"].eq(1), "effective_payment"] = 0.0
    data.loc[data["tenure_code"].eq(2), "effective_payment"] = clean_mortgage
    data.loc[data["tenure_code"].eq(3), "effective_payment"] = clean_rent

    # P5130 is estimated rent for owners and other tenure arrangements.
    data["equivalent_cost"] = clean_estimated_rent
    data.loc[data["tenure_code"].eq(3), "equivalent_cost"] = clean_rent

    valid_income = (
        data["household_income"].gt(0)
        & ~data["income_incomplete"].fillna(True).astype(bool)
    )
    data["valid_income"] = valid_income
    data["income_per_capita"] = np.where(
        valid_income,
        data["household_income"] / data["P6008"],
        np.nan,
    )
    data["effective_burden_percent"] = np.where(
        valid_income & data["effective_payment"].notna(),
        100 * data["effective_payment"] / data["household_income"],
        np.nan,
    )
    data["equivalent_burden_percent"] = np.where(
        valid_income,
        100 * data["equivalent_cost"] / data["household_income"],
        np.nan,
    )
    return data


def add_distribution(
    result: dict[str, float | int | str],
    group: pd.DataFrame,
    column: str,
    output_name: str,
) -> None:
    """Add Q1, median and Q3 for one variable to a summary row."""
    result[f"q1_{output_name}"] = weighted_quantile(
        group[column], group["annual_weight"], 0.25
    )
    result[f"median_{output_name}"] = weighted_quantile(
        group[column], group["annual_weight"], 0.50
    )
    result[f"q3_{output_name}"] = weighted_quantile(
        group[column], group["annual_weight"], 0.75
    )


def summarize_group(
    group: pd.DataFrame,
    geography: str,
    education_group: str,
    tenure_group: str,
) -> dict[str, float | int | str]:
    """Summarize one geography, education and tenure cell."""
    sample_size = len(group)
    result: dict[str, float | int | str] = {
        "geography": geography,
        "education_group": education_group,
        "tenure_group": tenure_group,
        "sample_household_months": sample_size,
        "cell_size_flag": (
            "under_50" if sample_size < 50 else "under_100" if sample_size < 100 else "adequate"
        ),
        "average_monthly_households": float(group["annual_weight"].sum()),
        "valid_income_sample": int(group["income_per_capita"].notna().sum()),
        "valid_effective_sample": int(
            group["effective_burden_percent"].notna().sum()
        ),
        "valid_equivalent_sample": int(
            group["equivalent_burden_percent"].notna().sum()
        ),
    }

    add_distribution(result, group, "income_per_capita", "income_per_capita_cop")
    add_distribution(result, group, "effective_payment", "effective_payment_cop")
    add_distribution(
        result, group, "effective_burden_percent", "effective_burden_percent"
    )
    add_distribution(result, group, "equivalent_cost", "equivalent_cost_cop")
    add_distribution(
        result, group, "equivalent_burden_percent", "equivalent_burden_percent"
    )

    effective_over_30 = group["effective_burden_percent"].gt(30).where(
        group["effective_burden_percent"].notna()
    )
    equivalent_over_30 = group["equivalent_burden_percent"].gt(30).where(
        group["equivalent_burden_percent"].notna()
    )
    result["effective_over_30_percent"] = weighted_share(
        effective_over_30, group["annual_weight"]
    )
    result["equivalent_over_30_percent"] = weighted_share(
        equivalent_over_30, group["annual_weight"]
    )
    return result


def build_summary(data: pd.DataFrame) -> pd.DataFrame:
    """Build general and education-stratified results."""
    rows = []
    geographies = {
        "Cali A.M.": data["AREA"].eq(CALI_AREA_CODE),
        "Colombia (incluye Cali A.M.)": pd.Series(True, index=data.index),
    }

    for geography, geography_filter in geographies.items():
        geography_data = data.loc[geography_filter]
        education_levels = ["General"] + EDUCATION_ORDER
        for education_group in education_levels:
            if education_group == "General":
                education_data = geography_data
            else:
                education_data = geography_data.loc[
                    geography_data["education_group"].eq(education_group)
                ]

            for tenure_group in TENURE_ORDER:
                group = education_data.loc[
                    education_data["tenure_group"].eq(tenure_group)
                ]
                rows.append(
                    summarize_group(
                        group, geography, education_group, tenure_group
                    )
                )
    return pd.DataFrame(rows)


def build_gaps(summary: pd.DataFrame) -> pd.DataFrame:
    """Calculate median gaps using tenants as the reference group."""
    metrics = {
        "median_income_per_capita_cop": "COP",
        "median_effective_payment_cop": "COP",
        "median_effective_burden_percent": "percentage points",
        "median_equivalent_burden_percent": "percentage points",
    }
    rows = []

    for (geography, education), block in summary.groupby(
        ["geography", "education_group"], sort=False
    ):
        tenants = block.loc[block["tenure_group"].eq("Arrendatarios")].iloc[0]
        for comparison_group in [group for group in TENURE_ORDER if group != "Arrendatarios"]:
            comparison = block.loc[
                block["tenure_group"].eq(comparison_group)
            ].iloc[0]
            for metric, unit in metrics.items():
                reference_value = float(tenants[metric])
                comparison_value = float(comparison[metric])
                if np.isnan(reference_value) or np.isnan(comparison_value):
                    continue
                absolute_gap = reference_value - comparison_value
                relative_gap = (
                    100 * absolute_gap / comparison_value
                    if comparison_value != 0
                    else float("nan")
                )
                rows.append(
                    {
                        "geography": geography,
                        "education_group": education,
                        "reference_group": "Arrendatarios",
                        "comparison_group": comparison_group,
                        "metric": metric,
                        "unit": unit,
                        "reference_value": reference_value,
                        "comparison_value": comparison_value,
                        "absolute_gap": absolute_gap,
                        "relative_gap_percent": relative_gap,
                    }
                )
    return pd.DataFrame(rows)


def plot_iqr_points(
    axis: plt.Axes,
    block: pd.DataFrame,
    category_order: list[str],
    category_column: str,
    metric: str,
    series_column: str,
    series_order: list[str],
    colors: dict[str, str],
) -> None:
    """Draw median points with Q1-Q3 vertical intervals."""
    offsets = np.linspace(-0.27, 0.27, len(series_order))
    x = np.arange(len(category_order))
    for offset, series in zip(offsets, series_order):
        indexed = block.loc[block[series_column].eq(series)].set_index(
            category_column
        ).reindex(category_order)
        median = indexed[f"median_{metric}"].astype(float).to_numpy()
        q1 = indexed[f"q1_{metric}"].astype(float).to_numpy()
        q3 = indexed[f"q3_{metric}"].astype(float).to_numpy()
        valid = np.isfinite(median) & np.isfinite(q1) & np.isfinite(q3)
        axis.errorbar(
            x[valid] + offset,
            median[valid],
            yerr=np.vstack([median[valid] - q1[valid], q3[valid] - median[valid]]),
            fmt="o",
            markersize=5,
            linewidth=1.4,
            capsize=3,
            color=colors[series],
            label=series,
        )


def create_general_chart(summary: pd.DataFrame) -> Path:
    """Plot general tenure medians and interquartile ranges."""
    block = summary.loc[summary["education_group"].eq("General")]
    geographies = ["Cali A.M.", "Colombia (incluye Cali A.M.)"]
    colors = {
        "Cali A.M.": "#146C94",
        "Colombia (incluye Cali A.M.)": "#D47B36",
    }
    figure, axes = plt.subplots(1, 2, figsize=(13.5, 5.6))
    specs = [
        ("income_per_capita_cop", "Ingreso per cápita", "COP"),
        (
            "equivalent_burden_percent",
            "Carga habitacional equivalente",
            "% del ingreso del hogar",
        ),
    ]
    short_tenure = ["Pagada", "Pagando", "Arriendo", "Otras"]

    for axis, (metric, title, ylabel) in zip(axes, specs):
        plot_iqr_points(
            axis,
            block,
            TENURE_ORDER,
            "tenure_group",
            metric,
            "geography",
            geographies,
            colors,
        )
        axis.set_title(title, fontsize=12, fontweight="bold")
        axis.set_ylabel(ylabel)
        axis.set_xticks(np.arange(len(TENURE_ORDER)), short_tenure)
        axis.grid(axis="y", alpha=0.2)
        axis.spines[["top", "right"]].set_visible(False)

    axes[0].yaxis.set_major_formatter(
        FuncFormatter(lambda value, position: f"${value / 1_000_000:.1f} M")
    )
    axes[0].legend(frameon=False, fontsize=8, loc="upper left")
    figure.suptitle(
        "Comparación general por forma de tenencia",
        fontsize=15,
        fontweight="bold",
    )
    figure.text(
        0.5,
        0.01,
        "Punto: mediana ponderada. Línea: cuartiles 1 y 3. Fuente: GEIH 2025.",
        ha="center",
        fontsize=8.5,
        color="#555555",
    )
    figure.tight_layout(rect=[0, 0.05, 1, 0.94])
    chart_path = VIZ_DIR / "question_3_tenure_gaps.png"
    figure.savefig(chart_path, dpi=220, bbox_inches="tight")
    plt.close(figure)
    return chart_path


def create_education_chart(summary: pd.DataFrame) -> Path:
    """Plot tenure comparisons inside each household-head education group."""
    block = summary.loc[summary["education_group"].ne("General")]
    geographies = ["Cali A.M.", "Colombia (incluye Cali A.M.)"]
    colors = {
        "Propietarios con vivienda pagada": "#24557A",
        "Propietarios que pagan su vivienda": "#D47B36",
        "Arrendatarios": "#6B8E23",
        "Otras formas de tenencia": "#7A5195",
    }
    figure, axes = plt.subplots(2, 2, figsize=(13.5, 9.0), sharex=True)
    specs = [
        ("income_per_capita_cop", "Ingreso per cápita", "COP"),
        (
            "equivalent_burden_percent",
            "Carga equivalente",
            "% del ingreso",
        ),
    ]
    short_education = ["Primaria\no menos", "Secundaria\ny media", "Técnico a\npregrado", "Postgrado"]

    for row, geography in enumerate(geographies):
        geography_block = block.loc[block["geography"].eq(geography)]
        for column, (metric, title, ylabel) in enumerate(specs):
            axis = axes[row, column]
            plot_iqr_points(
                axis,
                geography_block,
                EDUCATION_ORDER,
                "education_group",
                metric,
                "tenure_group",
                TENURE_ORDER,
                colors,
            )
            axis.set_title(f"{geography}: {title}", fontsize=10.5, fontweight="bold")
            axis.set_ylabel(ylabel)
            axis.set_xticks(np.arange(len(EDUCATION_ORDER)), short_education)
            axis.grid(axis="y", alpha=0.2)
            axis.spines[["top", "right"]].set_visible(False)
            if metric.endswith("_cop"):
                axis.yaxis.set_major_formatter(
                    FuncFormatter(lambda value, position: f"${value / 1_000_000:.1f} M")
                )

    handles, labels = axes[0, 0].get_legend_handles_labels()
    figure.legend(
        handles,
        ["Pagada", "Pagando", "Arriendo", "Otras"],
        loc="upper center",
        ncol=4,
        frameon=False,
        bbox_to_anchor=(0.5, 0.965),
    )
    figure.suptitle(
        "Brechas de tenencia según educación del jefe del hogar",
        fontsize=15,
        fontweight="bold",
        y=0.995,
    )
    figure.text(
        0.5,
        0.01,
        "Punto: mediana ponderada. Línea: cuartiles 1 y 3. Fuente: GEIH 2025.",
        ha="center",
        fontsize=8.5,
        color="#555555",
    )
    figure.tight_layout(rect=[0, 0.05, 1, 0.93])
    chart_path = VIZ_DIR / "question_3_education_gaps.png"
    figure.savefig(chart_path, dpi=220, bbox_inches="tight")
    plt.close(figure)
    return chart_path


def main() -> int:
    """Run Question 3 and save reproducible outputs."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    VIZ_DIR.mkdir(parents=True, exist_ok=True)

    household_columns = HOUSEHOLD_KEY + [
        "AREA",
        "FEX_C18",
        "P5090",
        "P5100",
        "P5130",
        "P5140",
        "P6008",
    ]
    person_columns = HOUSEHOLD_KEY + [
        "ORDEN",
        "P6050",
        "P3042",
        "is_employed_record",
        "P6430",
        "INGLABO",
        "P7422",
        "P7422S1",
    ]
    for indicator, amount in MONTHLY_OTHER_INCOME + ANNUAL_OTHER_INCOME:
        person_columns.extend([indicator, amount])

    households = pd.read_parquet(HOUSEHOLD_PATH, columns=household_columns)
    people = pd.read_parquet(PERSON_PATH, columns=person_columns)

    household_heads = select_household_heads(people)
    people = build_person_income(people)
    household_income = aggregate_income_by_household(people)
    analytical = build_analytical_households(
        households, household_income, household_heads
    )

    if sorted(analytical["survey_month"].unique()) != list(range(1, 13)):
        raise ValueError("The analytical dataset does not contain all 12 months.")
    if analytical["annual_weight"].isna().any() or analytical["annual_weight"].le(0).any():
        raise ValueError("The analytical dataset contains invalid survey weights.")

    summary = build_summary(analytical)
    gaps = build_gaps(summary)
    general_chart = create_general_chart(summary)
    education_chart = create_education_chart(summary)

    summary_path = RESULTS_DIR / "tenure_gap_summary.csv"
    gaps_path = RESULTS_DIR / "tenure_gap_differences.csv"
    validation_path = RESULTS_DIR / "validation.json"

    # Only summaries and figures are needed by the final fact sheet.
    summary.to_csv(summary_path, index=False, encoding="utf-8-sig")
    gaps.to_csv(gaps_path, index=False, encoding="utf-8-sig")

    small_cells = summary.loc[
        summary["education_group"].ne("General")
        & summary["sample_household_months"].lt(100),
        ["geography", "education_group", "tenure_group", "sample_household_months"],
    ].to_dict(orient="records")

    validation = {
        "status": "PASS",
        "months": sorted(analytical["survey_month"].unique().tolist()),
        "national_sample_household_months": len(analytical),
        "cali_sample_household_months": int(
            analytical["AREA"].eq(CALI_AREA_CODE).sum()
        ),
        "households_without_head": int(analytical["head_education_code"].isna().sum()),
        "education_not_classified": int(analytical["education_group"].isna().sum()),
        "income_incomplete_households": int(analytical["income_incomplete"].sum()),
        "cali_income_incomplete_households": int(
            (
                analytical["AREA"].eq(CALI_AREA_CODE)
                & analytical["income_incomplete"]
            ).sum()
        ),
        "zero_or_negative_income_households": int(
            analytical["household_income"].le(0).sum()
        ),
        "other_tenure_effective_payment_unobservable": int(
            analytical["tenure_group"].eq("Otras formas de tenencia").sum()
        ),
        "mortgage_nonresponse_codes_98_99": int(
            analytical.loc[analytical["tenure_code"].eq(2), "P5100"]
            .isin([98, 99])
            .sum()
        ),
        "rent_nonresponse_codes_98_99": int(
            analytical.loc[analytical["tenure_code"].eq(3), "P5140"]
            .isin([98, 99])
            .sum()
        ),
        "estimated_rent_nonresponse_codes_98_99": int(
            analytical.loc[~analytical["tenure_code"].eq(3), "P5130"]
            .isin([98, 99])
            .sum()
        ),
        "missing_effective_payment_for_payers": int(
            analytical.loc[analytical["tenure_code"].isin([2, 3]), "effective_payment"]
            .isna()
            .sum()
        ),
        "summary_rows": len(summary),
        "small_education_tenure_cells_under_100": small_cells,
        "summary_statistics": "weighted Q1, median and Q3",
        "income_definition": (
            "INGLABO + P7422S1 + monthly P7500 amounts + monthly equivalent "
            "of P7510 annual amounts"
        ),
        "effective_payment_definition": (
            "P5140 for tenants, P5100 for homeowners paying, zero for fully "
            "paid homeowners, and unobservable for other tenure arrangements"
        ),
        "equivalent_cost_definition": (
            "P5140 for tenants and P5130 estimated rent for all other tenure groups"
        ),
        "education_definition": "P3042 reported by the household head (P6050 = 1)",
        "services_included": False,
        "services_limitation": (
            "The selected GEIH modules do not report monetary utility payments."
        ),
        "summary_output": str(summary_path.relative_to(PROJECT_ROOT)),
        "gaps_output": str(gaps_path.relative_to(PROJECT_ROOT)),
        "general_chart_output": str(general_chart.relative_to(PROJECT_ROOT)),
        "education_chart_output": str(education_chart.relative_to(PROJECT_ROOT)),
    }
    validation_path.write_text(
        json.dumps(validation, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    display_columns = [
        "geography",
        "education_group",
        "tenure_group",
        "sample_household_months",
        "q1_income_per_capita_cop",
        "median_income_per_capita_cop",
        "q3_income_per_capita_cop",
        "q1_equivalent_burden_percent",
        "median_equivalent_burden_percent",
        "q3_equivalent_burden_percent",
    ]
    print("QUESTION 3: TENURE GAPS BY EDUCATION")
    print(
        summary.loc[summary["education_group"].eq("General"), display_columns]
        .round(2)
        .to_string(index=False)
    )
    print("\nRESULT: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
