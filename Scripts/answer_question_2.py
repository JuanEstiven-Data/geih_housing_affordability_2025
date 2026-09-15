"""Answer Question 2 using the validated output from Question 1.

Question
--------
How many households have a housing burden above 30% or 50%, and how much
residual income per person remains after their effective housing payment?

Only tenants and homeowners paying for their dwelling have an observed cash
payment that can support this classification. Fully paid homeowners and other
tenure arrangements remain in the descriptive universe, but their effective
burden is not estimated for this question.
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

from answer_question_3 import (
    HOUSEHOLD_KEY,
    aggregate_income_by_household,
    build_person_income,
    clean_reported_amount,
    weighted_quantile,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
INPUT_PATH = (
    PROJECT_ROOT
    / "Output"
    / "results"
    / "question_1"
    / "analytical_households_question_1.parquet"
)
RESULTS_DIR = PROJECT_ROOT / "Output" / "results" / "question_2"
VIZ_DIR = PROJECT_ROOT / "Viz"

CALI_AREA_CODE = "76"
# Editorial cutoff proposed during implementation, not a statistical standard.
# It changes presentation only; all valid negative residuals are retained.
MATERIAL_NEGATIVE_SHARE = 5.0
TENURE_ORDER = [
    "Propietarios con vivienda pagada",
    "Propietarios que pagan su vivienda",
    "Arrendatarios",
    "Otras formas de tenencia",
]
ESTIMABLE_TENURE = [
    "Propietarios que pagan su vivienda",
    "Arrendatarios",
]
BURDEN_GROUPS = ["Carga <= 30%", "Carga > 30%"]


def weighted_share(condition: pd.Series, weights: pd.Series) -> float:
    """Calculate a weighted percentage for a Boolean condition."""
    valid = condition.notna() & weights.notna() & weights.gt(0)
    if not valid.any():
        return float("nan")
    return float(
        100
        * weights.loc[valid & condition.fillna(False)].sum()
        / weights.loc[valid].sum()
    )


def prepare_analysis(data: pd.DataFrame) -> pd.DataFrame:
    """Apply the Question 2 eligibility and classification rules."""
    required = {
        "AREA",
        "tenure_group",
        "household_income",
        "effective_payment",
        "valid_income",
        "annual_weight",
        "P6008",
    }
    missing = required.difference(data.columns)
    if missing:
        raise ValueError(f"Question 1 output lacks columns: {sorted(missing)}")

    data = data.copy()
    data["burden_estimable"] = (
        data["tenure_group"].isin(ESTIMABLE_TENURE)
        & data["valid_income"].fillna(False).astype(bool)
        & data["effective_payment"].notna()
    )

    # Fully paid homeowners remain in the universe, but their structural zero
    # from Question 1 is not interpreted as their complete housing burden here.
    data["burden_percent"] = np.where(
        data["burden_estimable"],
        100 * data["effective_payment"] / data["household_income"],
        np.nan,
    )
    data["burden_group"] = pd.NA
    data.loc[
        data["burden_estimable"] & data["burden_percent"].le(30),
        "burden_group",
    ] = "Carga <= 30%"
    data.loc[
        data["burden_estimable"] & data["burden_percent"].gt(30),
        "burden_group",
    ] = "Carga > 30%"
    data["severe_burden"] = (
        data["burden_percent"].gt(50).where(data["burden_estimable"])
    )

    data["residual_income"] = np.where(
        data["burden_estimable"],
        data["household_income"] - data["effective_payment"],
        np.nan,
    )
    data["residual_income_per_capita"] = np.where(
        data["burden_estimable"],
        data["residual_income"] / data["P6008"],
        np.nan,
    )
    data["negative_residual"] = (
        data["residual_income"].lt(0).where(data["burden_estimable"])
    )
    return data


def geography_masks(data: pd.DataFrame) -> dict[str, pd.Series]:
    """Return the two geographical universes required by the activity."""
    return {
        "Cali A.M.": data["AREA"].astype(str).eq(CALI_AREA_CODE),
        "Colombia (incluye Cali A.M.)": pd.Series(True, index=data.index),
    }


def build_universe_coverage(data: pd.DataFrame) -> pd.DataFrame:
    """Describe the full universe and the burden-estimable portion."""
    rows = []
    for geography, mask in geography_masks(data).items():
        geography_data = data.loc[mask]
        total_weight = geography_data["annual_weight"].sum()
        for tenure in TENURE_ORDER:
            group = geography_data.loc[geography_data["tenure_group"].eq(tenure)]
            estimable = group.loc[group["burden_estimable"]]
            if tenure in ESTIMABLE_TENURE:
                note = "Estimable cuando ingreso y pago son válidos"
            elif tenure == "Propietarios con vivienda pagada":
                note = "Incluido en el universo; carga no estimada"
            else:
                note = "Incluido en el universo; pago efectivo n. d."
            rows.append(
                {
                    "geography": geography,
                    "tenure_group": tenure,
                    "sample_household_months": len(group),
                    "average_monthly_households": float(
                        group["annual_weight"].sum()
                    ),
                    "share_of_full_universe_percent": float(
                        100 * group["annual_weight"].sum() / total_weight
                    ),
                    "estimable_sample": len(estimable),
                    "estimable_average_monthly_households": float(
                        estimable["annual_weight"].sum()
                    ),
                    "estimation_note": note,
                }
            )
    return pd.DataFrame(rows)


def build_threshold_summary(data: pd.DataFrame) -> pd.DataFrame:
    """Count households at the 30% and 50% burden thresholds."""
    rows = []
    for geography, mask in geography_masks(data).items():
        eligible = data.loc[mask & data["burden_estimable"]]
        total_weight = eligible["annual_weight"].sum()
        definitions = [
            ("Carga <= 30%", eligible["burden_percent"].le(30)),
            ("Carga > 30%", eligible["burden_percent"].gt(30)),
            ("Carga > 50%", eligible["burden_percent"].gt(50)),
        ]
        for label, condition in definitions:
            group = eligible.loc[condition]
            rows.append(
                {
                    "geography": geography,
                    "threshold_group": label,
                    "sample_household_months": len(group),
                    "average_monthly_households": float(
                        group["annual_weight"].sum()
                    ),
                    "weighted_share_of_estimable_percent": float(
                        100 * group["annual_weight"].sum() / total_weight
                    ),
                    "estimable_sample_household_months": len(eligible),
                    "estimable_average_monthly_households": float(total_weight),
                }
            )
    return pd.DataFrame(rows)


def add_distribution(
    row: dict[str, float | int | str],
    group: pd.DataFrame,
    column: str,
    output_name: str,
) -> None:
    """Add weighted Q1, median and Q3 to a summary row."""
    row[f"q1_{output_name}"] = weighted_quantile(
        group[column], group["annual_weight"], 0.25
    )
    row[f"median_{output_name}"] = weighted_quantile(
        group[column], group["annual_weight"], 0.50
    )
    row[f"q3_{output_name}"] = weighted_quantile(
        group[column], group["annual_weight"], 0.75
    )


def build_residual_summary(data: pd.DataFrame) -> pd.DataFrame:
    """Compare residual income across the two mutually exclusive groups."""
    rows = []
    for geography, mask in geography_masks(data).items():
        geography_data = data.loc[mask & data["burden_estimable"]]
        for burden_group in BURDEN_GROUPS:
            group = geography_data.loc[
                geography_data["burden_group"].eq(burden_group)
            ]
            row: dict[str, float | int | str] = {
                "geography": geography,
                "burden_group": burden_group,
                "sample_household_months": len(group),
                "average_monthly_households": float(
                    group["annual_weight"].sum()
                ),
                "negative_residual_sample": int(
                    group["negative_residual"].fillna(False).sum()
                ),
                "negative_residual_weighted_share_percent": weighted_share(
                    group["negative_residual"], group["annual_weight"]
                ),
            }
            add_distribution(
                row,
                group,
                "residual_income_per_capita",
                "residual_income_per_capita_cop",
            )
            rows.append(row)
    return pd.DataFrame(rows)


def build_tenure_composition(data: pd.DataFrame) -> pd.DataFrame:
    """Show which observed-payment tenures form each burden group."""
    rows = []
    for geography, mask in geography_masks(data).items():
        geography_data = data.loc[mask & data["burden_estimable"]]
        for burden_group in BURDEN_GROUPS:
            burden_data = geography_data.loc[
                geography_data["burden_group"].eq(burden_group)
            ]
            total_weight = burden_data["annual_weight"].sum()
            for tenure in ESTIMABLE_TENURE:
                group = burden_data.loc[
                    burden_data["tenure_group"].eq(tenure)
                ]
                rows.append(
                    {
                        "geography": geography,
                        "burden_group": burden_group,
                        "tenure_group": tenure,
                        "sample_household_months": len(group),
                        "average_monthly_households": float(
                            group["annual_weight"].sum()
                        ),
                        "share_within_burden_group_percent": float(
                            100 * group["annual_weight"].sum() / total_weight
                        ),
                    }
                )
    return pd.DataFrame(rows)


def weighted_percentile(
    values: pd.Series, weights: pd.Series, percentile: float
) -> float:
    """Use the common weighted-quantile function for audit percentiles."""
    return weighted_quantile(values, weights, percentile / 100)


def build_negative_audit(data: pd.DataFrame) -> pd.DataFrame:
    """Summarize negative residuals without publishing household identifiers."""
    rows = []
    for geography, mask in geography_masks(data).items():
        eligible = data.loc[mask & data["burden_estimable"]]
        total_weight = eligible["annual_weight"].sum()
        for tenure in ["Total estimable"] + ESTIMABLE_TENURE:
            if tenure == "Total estimable":
                reference = eligible
            else:
                reference = eligible.loc[eligible["tenure_group"].eq(tenure)]
            negative = reference.loc[reference["negative_residual"].fillna(False)]
            reference_weight = reference["annual_weight"].sum()
            negative_weight = negative["annual_weight"].sum()
            rows.append(
                {
                    "geography": geography,
                    "tenure_group": tenure,
                    "negative_sample_household_months": len(negative),
                    "negative_average_monthly_households": float(negative_weight),
                    "share_of_all_estimable_percent": float(
                        100 * negative_weight / total_weight
                    ),
                    "share_within_tenure_percent": float(
                        100 * negative_weight / reference_weight
                    ),
                    "minimum_residual_income_cop": float(
                        negative["residual_income"].min()
                    ),
                    "p1_residual_income_cop": weighted_percentile(
                        negative["residual_income"], negative["annual_weight"], 1
                    ),
                    "p5_residual_income_cop": weighted_percentile(
                        negative["residual_income"], negative["annual_weight"], 5
                    ),
                    "median_residual_income_cop": weighted_percentile(
                        negative["residual_income"], negative["annual_weight"], 50
                    ),
                }
            )
    return pd.DataFrame(rows)


def reconcile_negative_records(data: pd.DataFrame) -> pd.DataFrame:
    """Reconcile every negative residual with the two selected source bases.

    Rebuild personal income from the retained GEIH components, and compare
    payment directly with P5100 or P5140. This checks processing consistency;
    it cannot verify whether respondents reported their amounts correctly.
    The exported audit omits household identifiers and geographic codes.
    """
    negative = data.loc[
        data["burden_estimable"] & data["residual_income"].lt(0),
        HOUSEHOLD_KEY + ["tenure_group", "household_income", "effective_payment",
                         "residual_income", "residual_income_per_capita", "P6008"],
    ].copy()
    households = pd.read_parquet(PROJECT_ROOT / "Output/household_core_2025.parquet")
    people = pd.read_parquet(PROJECT_ROOT / "Output/person_components_2025.parquet")
    people = people.merge(negative[HOUSEHOLD_KEY], on=HOUSEHOLD_KEY,
                          how="inner", validate="many_to_one")
    source_income = aggregate_income_by_household(build_person_income(people))
    source_income = source_income.rename(columns={"household_income": "source_income"})
    source_housing = households[HOUSEHOLD_KEY + ["P5090", "P5100", "P5140", "P6008"]]
    source_housing = source_housing.rename(columns={"P6008": "source_members"})
    audit = negative.merge(source_income, on=HOUSEHOLD_KEY, how="left",
                           validate="one_to_one").merge(
        source_housing, on=HOUSEHOLD_KEY, how="left", validate="one_to_one")
    audit["payment_variable"] = np.where(audit["P5090"].eq(2), "P5100", "P5140")
    audit["source_payment"] = clean_reported_amount(
        audit["P5100"].where(audit["P5090"].eq(2), audit["P5140"]))
    audit["source_residual"] = audit["source_income"] - audit["source_payment"]
    audit["income_matches"] = np.isclose(audit["household_income"], audit["source_income"])
    audit["payment_matches"] = np.isclose(audit["effective_payment"], audit["source_payment"])
    audit["residual_matches"] = np.isclose(audit["residual_income"], audit["source_residual"])
    audit["members_match"] = (audit["P6008"].eq(audit["source_members"])
                              & audit["P6008"].eq(audit["counted_household_members"]))
    audit["source_income_complete"] = ~audit["income_incomplete"].fillna(True).astype(bool)
    audit["negative_sign_confirmed"] = (audit["source_residual"].lt(0)
                                        & audit["source_income"].gt(0))
    checks = ["income_matches", "payment_matches", "residual_matches", "members_match",
              "source_income_complete", "negative_sign_confirmed"]
    if not audit[checks].all().all():
        raise ValueError("Negative residuals do not reconcile with selected source data.")
    columns = ["tenure_group", "payment_variable", "source_income", "source_payment",
               "source_members", "source_residual", "residual_income_per_capita"] + checks
    audit = audit.sort_values("source_residual")[columns].reset_index(drop=True)
    audit.insert(0, "audit_case", np.arange(1, len(audit) + 1))
    return audit


def create_chart(
    thresholds: pd.DataFrame, residuals: pd.DataFrame
) -> Path:
    """Create the two panels needed for the Question 2 fact sheet."""
    geographies = ["Cali A.M.", "Colombia (incluye Cali A.M.)"]
    colors = {geographies[0]: "#146C94", geographies[1]: "#D47B36"}
    figure, axes = plt.subplots(1, 2, figsize=(13.5, 5.6))

    threshold_order = ["Carga <= 30%", "Carga > 30%", "Carga > 50%"]
    x = np.arange(len(threshold_order))
    width = 0.34
    for index, geography in enumerate(geographies):
        block = (
            thresholds.loc[thresholds["geography"].eq(geography)]
            .set_index("threshold_group")
            .reindex(threshold_order)
        )
        axes[0].bar(
            x + (index - 0.5) * width,
            block["weighted_share_of_estimable_percent"],
            width,
            label=geography,
            color=colors[geography],
        )
    axes[0].set_xticks(x, ["≤ 30%", "> 30%", "> 50%"])
    axes[0].set_ylabel("% de hogares con carga estimable")
    axes[0].set_title("Hogares según umbral de carga", fontweight="bold")
    axes[0].legend(frameon=False, fontsize=8)

    residual_order = BURDEN_GROUPS
    x = np.arange(len(residual_order))
    for offset, geography in zip([-0.10, 0.10], geographies):
        block = (
            residuals.loc[residuals["geography"].eq(geography)]
            .set_index("burden_group")
            .reindex(residual_order)
        )
        median = block["median_residual_income_per_capita_cop"].to_numpy()
        q1 = block["q1_residual_income_per_capita_cop"].to_numpy()
        q3 = block["q3_residual_income_per_capita_cop"].to_numpy()
        axes[1].errorbar(
            x + offset,
            median,
            yerr=np.vstack([median - q1, q3 - median]),
            fmt="o",
            markersize=6,
            linewidth=1.5,
            capsize=4,
            color=colors[geography],
            label=geography,
        )
    axes[1].axhline(0, color="#777777", linewidth=0.8)
    axes[1].set_xticks(x, ["≤ 30%", "> 30%"])
    axes[1].set_ylabel("COP por persona")
    axes[1].set_title("Ingreso residual per cápita", fontweight="bold")
    axes[1].yaxis.set_major_formatter(
        FuncFormatter(lambda value, position: f"${value / 1_000_000:.1f} M")
    )

    for axis in axes:
        axis.grid(axis="y", alpha=0.2)
        axis.spines[["top", "right"]].set_visible(False)
    figure.suptitle(
        "Carga habitacional e ingreso residual",
        fontsize=15,
        fontweight="bold",
    )
    figure.text(
        0.5,
        0.01,
        "Propietarios pagando y arrendatarios. >50% está incluido en >30%. "
        "Puntos: medianas; líneas: Q1–Q3. GEIH 2025.",
        ha="center",
        fontsize=8.5,
        color="#555555",
    )
    figure.tight_layout(rect=[0, 0.05, 1, 0.94])
    path = VIZ_DIR / "question_2_burden_and_residual.png"
    figure.savefig(path, dpi=220, bbox_inches="tight")
    plt.close(figure)
    return path


def validate_results(
    data: pd.DataFrame,
    coverage: pd.DataFrame,
    thresholds: pd.DataFrame,
    residuals: pd.DataFrame,
    negative_audit: pd.DataFrame,
) -> dict[str, object]:
    """Validate denominators, classifications and negative residuals."""
    eligible = data.loc[data["burden_estimable"]]
    negative = eligible.loc[eligible["negative_residual"].fillna(False)]
    negative_identity = np.isclose(
        negative["residual_income"],
        negative["household_income"] - negative["effective_payment"],
    ).all()
    negative_payment_check = (
        negative["effective_payment"].gt(negative["household_income"]).all()
    )
    negative_burden_check = negative["burden_percent"].gt(100).all()

    main = thresholds.loc[thresholds["threshold_group"].isin(BURDEN_GROUPS)]
    threshold_totals = main.groupby("geography")[
        "weighted_share_of_estimable_percent"
    ].sum()
    coverage_totals = coverage.groupby("geography")[
        "share_of_full_universe_percent"
    ].sum()

    total_negative = negative_audit.loc[
        negative_audit["tenure_group"].eq("Total estimable")
    ]
    separated = bool(
        total_negative["share_of_all_estimable_percent"].ge(
            MATERIAL_NEGATIVE_SHARE
        ).any()
    )
    status = "PASS" if all(
        [
            len(coverage) == 8,
            len(thresholds) == 6,
            len(residuals) == 4,
            np.allclose(threshold_totals.to_numpy(), 100),
            np.allclose(coverage_totals.to_numpy(), 100),
            negative_identity,
            negative_payment_check,
            negative_burden_check,
            data.loc[
                data["tenure_group"].isin(
                    [
                        "Propietarios con vivienda pagada",
                        "Otras formas de tenencia",
                    ]
                ),
                "burden_percent",
            ].isna().all(),
        ]
    ) else "FAIL"

    negative_shares = {
        row["geography"]: row["share_of_all_estimable_percent"]
        for _, row in total_negative.iterrows()
    }
    return {
        "status": status,
        "months": sorted(data["survey_month"].astype(int).unique().tolist()),
        "full_universe_sample_household_months": len(data),
        "estimable_sample_household_months": len(eligible),
        "negative_residual_sample_household_months": len(negative),
        "negative_residual_weighted_shares_percent": negative_shares,
        "negative_residual_materiality_cutoff_percent": MATERIAL_NEGATIVE_SHARE,
        "negative_residual_separate_subgroup": separated,
        "negative_residual_presentation": (
            "Separate subgroup" if separated else "Mention and audited table only"
        ),
        "negative_residual_identity_check": bool(negative_identity),
        "negative_payment_exceeds_income_check": bool(negative_payment_check),
        "negative_burden_exceeds_100_check": bool(negative_burden_check),
        "threshold_denominator": (
            "Tenants and homeowners paying, with complete positive income and "
            "a reported effective payment"
        ),
        "fully_paid_homeowners_rule": (
            "Included in the descriptive universe; effective burden not estimated"
        ),
        "other_tenure_rule": (
            "Included in the descriptive universe; effective payment and burden n. d."
        ),
        "country_reference": "Colombia includes Cali A.M.; estimates are not added.",
    }


def main() -> int:
    """Execute the complete Question 2 workflow."""
    if not INPUT_PATH.exists():
        raise FileNotFoundError(
            "Run Scripts/answer_question_1.py before Question 2."
        )
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    VIZ_DIR.mkdir(parents=True, exist_ok=True)

    data = prepare_analysis(pd.read_parquet(INPUT_PATH))
    coverage = build_universe_coverage(data)
    thresholds = build_threshold_summary(data)
    residuals = build_residual_summary(data)
    composition = build_tenure_composition(data)
    negative_audit = build_negative_audit(data)
    negative_records = reconcile_negative_records(data)
    chart_path = create_chart(thresholds, residuals)
    validation = validate_results(
        data, coverage, thresholds, residuals, negative_audit
    )
    if validation["status"] != "PASS":
        raise ValueError("Question 2 validation failed.")
    validation["negative_source_reconciliation"] = {
        "status": "PASS",
        "records_checked": len(negative_records),
        "sources": ["Output/household_core_2025.parquet", "Output/person_components_2025.parquet"],
        "scope": "Reconstructed income, recorded payment, household size and negative sign; not respondent accuracy.",
    }

    outputs = {
        "coverage_output": RESULTS_DIR / "universe_coverage.csv",
        "threshold_output": RESULTS_DIR / "burden_threshold_summary.csv",
        "residual_output": RESULTS_DIR / "residual_income_summary.csv",
        "composition_output": RESULTS_DIR / "burden_tenure_composition.csv",
        "negative_audit_output": RESULTS_DIR / "negative_residual_audit.csv",
        "negative_records_output": RESULTS_DIR / "negative_residual_records_audit.csv",
    }
    # No later step consumes this household-level frame; keep it in memory.
    coverage.to_csv(outputs["coverage_output"], index=False, encoding="utf-8-sig")
    thresholds.to_csv(outputs["threshold_output"], index=False, encoding="utf-8-sig")
    residuals.to_csv(outputs["residual_output"], index=False, encoding="utf-8-sig")
    composition.to_csv(
        outputs["composition_output"], index=False, encoding="utf-8-sig"
    )
    negative_audit.to_csv(
        outputs["negative_audit_output"], index=False, encoding="utf-8-sig"
    )
    negative_records.to_csv(
        outputs["negative_records_output"], index=False, encoding="utf-8-sig"
    )

    validation["outputs"] = {
        name: str(path.relative_to(PROJECT_ROOT)) for name, path in outputs.items()
    }
    validation["outputs"]["chart_output"] = str(
        chart_path.relative_to(PROJECT_ROOT)
    )
    (RESULTS_DIR / "validation.json").write_text(
        json.dumps(validation, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print("QUESTION 2: BURDEN THRESHOLDS AND RESIDUAL INCOME")
    print(thresholds.round(2).to_string(index=False))
    print("\nRESIDUAL INCOME")
    print(residuals.round(2).to_string(index=False))
    print("\nRESULT: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
