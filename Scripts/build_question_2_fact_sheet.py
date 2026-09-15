from pathlib import Path

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Table, TableStyle


PROJECT = Path(__file__).resolve().parents[1]
RESULTS = PROJECT / "Output" / "results" / "question_2"
THRESHOLDS = RESULTS / "burden_threshold_summary.csv"
RESIDUALS = RESULTS / "residual_income_summary.csv"
COVERAGE = RESULTS / "universe_coverage.csv"
COMPOSITION = RESULTS / "burden_tenure_composition.csv"
NEGATIVE = RESULTS / "negative_residual_audit.csv"
CHART = PROJECT / "Viz" / "question_2_burden_and_residual.png"
OUTPUT = PROJECT / "Deliverables" / "ficha_resultados_pregunta_2.pdf"

BLUE = colors.HexColor("#245A73")
LIGHT_BLUE = colors.HexColor("#EAF2F6")
GRAY = colors.HexColor("#555555")
LIGHT_GRAY = colors.HexColor("#D9DEE2")


def money(value):
    return f"${value:,.0f}".replace(",", ".")


def percent(value):
    return f"{value:.1f}%".replace(".", ",")


def integer(value):
    return f"{value:,.0f}".replace(",", ".")


def money_iqr(row):
    return (
        f"{money(row['median_residual_income_per_capita_cop'])}<br/>"
        f"[{money(row['q1_residual_income_per_capita_cop'])} - "
        f"{money(row['q3_residual_income_per_capita_cop'])}]"
    )


styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name="FactTitle", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=17.5, leading=20, spaceAfter=2))
styles.add(ParagraphStyle(name="Subtitle", parent=styles["Normal"], fontSize=8.5, leading=10.5, textColor=GRAY, spaceAfter=6))
styles.add(ParagraphStyle(name="Question", parent=styles["BodyText"], fontName="Helvetica-Bold", fontSize=9.1, leading=11, spaceAfter=5))
styles.add(ParagraphStyle(name="Section", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=11, leading=13, textColor=BLUE, spaceBefore=4, spaceAfter=4))
styles.add(ParagraphStyle(name="Body", parent=styles["BodyText"], fontSize=7.5, leading=9.2, spaceAfter=4))
styles.add(ParagraphStyle(name="Tiny", parent=styles["BodyText"], fontSize=6.6, leading=8.0, textColor=GRAY, spaceAfter=3))
styles.add(ParagraphStyle(name="Cell", parent=styles["BodyText"], fontSize=6.35, leading=7.5))
styles.add(ParagraphStyle(name="CellCenter", parent=styles["Cell"], alignment=TA_CENTER))
styles.add(ParagraphStyle(name="CellWhite", parent=styles["CellCenter"], fontName="Helvetica-Bold", textColor=colors.white))


def P(text, style="Body"):
    return Paragraph(str(text), styles[style])


def footer(canvas, document):
    canvas.saveState()
    canvas.setStrokeColor(LIGHT_GRAY)
    canvas.line(0.55 * inch, 0.43 * inch, 7.95 * inch, 0.43 * inch)
    canvas.setFont("Helvetica", 6.5)
    canvas.setFillColor(GRAY)
    canvas.drawString(0.55 * inch, 0.27 * inch, "Fuente: elaboración propia con microdatos GEIH 2025 del DANE.")
    canvas.drawRightString(7.95 * inch, 0.27 * inch, f"Página {document.page}")
    canvas.restoreState()


def styled_table(data, widths):
    table = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
    commands = [
        ("GRID", (0, 0), (-1, -1), 0.35, LIGHT_GRAY),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3.2),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3.2),
        ("TOPPADDING", (0, 0), (-1, -1), 2.8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.8),
        ("BACKGROUND", (0, 0), (-1, 0), BLUE),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
    ]
    for row in range(2, len(data), 2):
        commands.append(("BACKGROUND", (0, row), (-1, row), LIGHT_BLUE))
    table.setStyle(TableStyle(commands))
    return table


thresholds = pd.read_csv(THRESHOLDS)
residuals = pd.read_csv(RESIDUALS)
coverage = pd.read_csv(COVERAGE)
composition = pd.read_csv(COMPOSITION)
negative = pd.read_csv(NEGATIVE)

geo_cali = "Cali A.M."
geo_country = "Colombia (incluye Cali A.M.)"
cali_t = thresholds.loc[thresholds["geography"].eq(geo_cali)].set_index("threshold_group")
country_t = thresholds.loc[thresholds["geography"].eq(geo_country)].set_index("threshold_group")
cali_r = residuals.loc[residuals["geography"].eq(geo_cali)].set_index("burden_group")
country_r = residuals.loc[residuals["geography"].eq(geo_country)].set_index("burden_group")

doc = SimpleDocTemplate(
    str(OUTPUT), pagesize=letter, rightMargin=0.55 * inch, leftMargin=0.55 * inch,
    topMargin=0.40 * inch, bottomMargin=0.56 * inch,
    title="Ficha de resultados Pregunta 2 GEIH 2025", author="Grupo 4",
)
story = [
    P("Ficha de resultados - Pregunta 2", "FactTitle"),
    P("Asequibilidad de la vivienda | Grupo 4 | Cali A.M. y Colombia | GEIH 2025", "Subtitle"),
    P("¿Cuántos hogares presentan una carga habitacional superior al 30% o al 50%, y cuánto ingreso residual per cápita les queda?", "Question"),
]

measurement = [
    [P("Elemento", "CellWhite"), P("Definición aplicada", "CellWhite")],
    [P("Carga", "Cell"), P("Pago efectivo (P5100 o P5140) / ingreso mensual completo y positivo del hogar × 100.", "Cell")],
    [P("Universo estimable", "Cell"), P("Propietarios pagando y arrendatarios con pago e ingreso válidos. Vivienda pagada y otras formas permanecen en el universo descriptivo, sin estimación de carga.", "Cell")],
    [P("Ingreso residual", "Cell"), P("(Ingreso del hogar - pago efectivo) / P6008. Se conservan los valores negativos.", "Cell")],
    [P("Pesos", "Cell"), P("FEX_C18; hogares mensuales promedio = suma anual de ponderadores / 12. Colombia incluye Cali A.M.", "Cell")],
]
story.append(styled_table(measurement, [1.12 * inch, 6.24 * inch]))
story.append(P("1. Umbrales e ingreso residual", "Section"))
story.append(Image(str(CHART), width=7.30 * inch, height=3.08 * inch))

threshold_header = [
    P("Umbral", "CellWhite"), P("Hogares Cali", "CellWhite"), P("% Cali", "CellWhite"),
    P("Hogares Colombia", "CellWhite"), P("% Colombia", "CellWhite"),
]
threshold_rows = [threshold_header]
for label in ["Carga <= 30%", "Carga > 30%", "Carga > 50%"]:
    display_label = "Carga hasta 30%" if label == "Carga <= 30%" else label
    threshold_rows.append([
        P(display_label, "Cell"),
        P(integer(cali_t.loc[label, "average_monthly_households"]), "CellCenter"),
        P(percent(cali_t.loc[label, "weighted_share_of_estimable_percent"]), "CellCenter"),
        P(integer(country_t.loc[label, "average_monthly_households"]), "CellCenter"),
        P(percent(country_t.loc[label, "weighted_share_of_estimable_percent"]), "CellCenter"),
    ])
story.append(styled_table(threshold_rows, [1.30 * inch, 1.42 * inch, 1.12 * inch, 1.60 * inch, 1.32 * inch]))

residual_header = [P("Grupo", "CellWhite"), P("Cali: residual pc<br/>Md [Q1 - Q3]", "CellWhite"), P("Colombia: residual pc<br/>Md [Q1 - Q3]", "CellWhite")]
residual_rows = [residual_header]
for label in ["Carga <= 30%", "Carga > 30%"]:
    display_label = "Carga hasta 30%" if label == "Carga <= 30%" else label
    residual_rows.append([
        P(display_label, "Cell"),
        P(money_iqr(cali_r.loc[label]), "CellCenter"),
        P(money_iqr(country_r.loc[label]), "CellCenter"),
    ])
story.append(styled_table(residual_rows, [1.54 * inch, 2.91 * inch, 2.91 * inch]))
story.append(P(
    "En Cali A.M., 196.157 hogares mensuales promedio con carga estimable superan el 30% y 73.005 superan el 50%. El ingreso residual per cápita mediano es de $1.005.875 en el grupo con carga hasta 30% y $308.333 en el grupo >30%. Las proporciones nacionales son cercanas, pero las cifras absolutas responden a universos territoriales distintos.",
    "Body",
))
story.append(P(
    "El grupo >50% está contenido dentro de >30%; por ello sus cantidades no deben sumarse. Punto del gráfico de residual: mediana ponderada; línea: Q1-Q3.",
    "Tiny",
))

story.append(PageBreak())
story.append(P("2. Cobertura y auditoría", "FactTitle"))
story.append(P("La cobertura delimita a qué hogares representan las proporciones de la primera página.", "Subtitle"))

story.append(P("Universo completo y carga estimable", "Section"))
coverage_header = [
    P("Tenencia", "CellWhite"), P("% universo Cali", "CellWhite"), P("Estimables Cali", "CellWhite"),
    P("% universo país", "CellWhite"), P("Estimables país", "CellWhite"), P("Tratamiento", "CellWhite"),
]
coverage_rows = [coverage_header]
short = {
    "Propietarios con vivienda pagada": "Vivienda pagada",
    "Propietarios que pagan su vivienda": "Pagando vivienda",
    "Arrendatarios": "Arrendatarios",
    "Otras formas de tenencia": "Otras formas",
}
for tenure in short:
    c = coverage.loc[(coverage["geography"].eq(geo_cali)) & (coverage["tenure_group"].eq(tenure))].iloc[0]
    n = coverage.loc[(coverage["geography"].eq(geo_country)) & (coverage["tenure_group"].eq(tenure))].iloc[0]
    treatment = "Estimable" if tenure in ["Propietarios que pagan su vivienda", "Arrendatarios"] else ("Sin estimación" if tenure.startswith("Propietarios") else "Pago n. d.")
    coverage_rows.append([
        P(short[tenure], "Cell"), P(percent(c["share_of_full_universe_percent"]), "CellCenter"),
        P(integer(c["estimable_average_monthly_households"]), "CellCenter"), P(percent(n["share_of_full_universe_percent"]), "CellCenter"),
        P(integer(n["estimable_average_monthly_households"]), "CellCenter"), P(treatment, "CellCenter"),
    ])
story.append(styled_table(coverage_rows, [1.26 * inch, 1.06 * inch, 1.13 * inch, 1.06 * inch, 1.13 * inch, 1.36 * inch]))
total_cali = coverage.loc[coverage["geography"].eq(geo_cali)]
total_country = coverage.loc[coverage["geography"].eq(geo_country)]
story.append(P(
    f"Universo completo: {integer(total_cali['average_monthly_households'].sum())} hogares mensuales "
    f"en Cali y {integer(total_country['average_monthly_households'].sum())} en Colombia. "
    f"Muestra hogar-mes: {integer(total_cali['sample_household_months'].sum())} / "
    f"{integer(total_country['sample_household_months'].sum())}; carga estimable: "
    f"{integer(total_cali['estimable_sample'].sum())} / "
    f"{integer(total_country['estimable_sample'].sum())}, respectivamente.",
    "Tiny",
))
story.append(P(
    "Los propietarios con vivienda pagada están incluidos en el universo, pero no se les estima carga: el cero de arriendo o cuota no representa sus demás costos. Para otras formas, el pago efectivo es n. d. La clasificación cubre aproximadamente 467.249 hogares mensuales en Cali A.M. y 8.071.174 en Colombia.",
    "Body",
))

story.append(P("Composición de la carga elevada", "Section"))
composition_header = [P("Tenencia", "CellWhite"), P("Cali >30%", "CellWhite"), P("Colombia >30%", "CellWhite"), P("Negativos dentro de tenencia<br/>Cali / país", "CellWhite")]
composition_rows = [composition_header]
neg_cali = negative.loc[negative["geography"].eq(geo_cali)].set_index("tenure_group")
neg_country = negative.loc[negative["geography"].eq(geo_country)].set_index("tenure_group")
for tenure in ["Propietarios que pagan su vivienda", "Arrendatarios"]:
    c = composition.loc[(composition["geography"].eq(geo_cali)) & (composition["burden_group"].eq("Carga > 30%")) & (composition["tenure_group"].eq(tenure))].iloc[0]
    n = composition.loc[(composition["geography"].eq(geo_country)) & (composition["burden_group"].eq("Carga > 30%")) & (composition["tenure_group"].eq(tenure))].iloc[0]
    composition_rows.append([
        P(short[tenure], "Cell"), P(percent(c["share_within_burden_group_percent"]), "CellCenter"),
        P(percent(n["share_within_burden_group_percent"]), "CellCenter"),
        P(f"{percent(neg_cali.loc[tenure, 'share_within_tenure_percent'])} / {percent(neg_country.loc[tenure, 'share_within_tenure_percent'])}", "CellCenter"),
    ])
story.append(styled_table(composition_rows, [2.12 * inch, 1.28 * inch, 1.46 * inch, 2.50 * inch]))
story.append(P(
    "Los arrendatarios representan 95,8% de los hogares con carga >30% en Cali A.M. y 93,1% en Colombia dentro del universo estimable. Esta composición refleja que el grupo estimable contiene muchos más arrendatarios que propietarios pagando; no demuestra que arrendar cause la carga observada.",
    "Body",
))

story.append(P("Residuales negativos", "Section"))
negative_header = [
    P("Territorio", "CellWhite"), P("Muestra", "CellWhite"), P("Hogares", "CellWhite"), P("% estimable", "CellWhite"),
    P("Mínimo", "CellWhite"), P("P1", "CellWhite"), P("P5", "CellWhite"), P("Mediana", "CellWhite"),
]
negative_rows = [negative_header]
for geography, label in [(geo_cali, "Cali A.M."), (geo_country, "Colombia")]:
    row = negative.loc[(negative["geography"].eq(geography)) & (negative["tenure_group"].eq("Total estimable"))].iloc[0]
    negative_rows.append([
        P(label, "Cell"), P(integer(row["negative_sample_household_months"]), "CellCenter"),
        P(integer(row["negative_average_monthly_households"]), "CellCenter"), P(percent(row["share_of_all_estimable_percent"]), "CellCenter"),
        P(money(row["minimum_residual_income_cop"]), "CellCenter"), P(money(row["p1_residual_income_cop"]), "CellCenter"),
        P(money(row["p5_residual_income_cop"]), "CellCenter"), P(money(row["median_residual_income_cop"]), "CellCenter"),
    ])
story.append(styled_table(negative_rows, [0.82 * inch, 0.62 * inch, 0.72 * inch, 0.72 * inch, 1.16 * inch, 1.04 * inch, 1.04 * inch, 1.10 * inch]))
story.append(P(
    "Los residuales negativos representan 4,70% en Cali A.M. y 3,79% en Colombia, por debajo del corte editorial propuesto del 5%; se mencionan y auditan sin crear un tercer grupo gráfico. Todos se conciliaron con el ingreso reconstruido y el pago de las bases intermedias: pago mayor que ingreso y carga >100%. Los extremos se conservan; esto no certifica la exactitud del reporte original.",
    "Body",
))

story.append(P("Alcance y fuentes", "Section"))
story.append(P(
    "La GEIH no registra montos de servicios públicos; la carga observada puede subestimar el compromiso habitacional total. Los códigos 98 y 99 se tratan como montos no disponibles. El valor 999999999, sin definición documentada en los archivos entregados, se conserva en la auditoría de frecuencia y se excluye operacionalmente del ingreso. Carga y residual comparten ingreso y pago en su cálculo: su asociación es parcialmente mecánica, sin interpretación causal.",
    "Body",
))
story.append(P(
    'Umbrales: <link href="https://www.census.gov/library/stories/2022/12/housing-costs-burden.html">U.S. Census Bureau (2022), Housing Costs Burden</link>; <link href="https://www.huduser.gov/portal/datasets/cp/CHAS/bg_chas.html">HUD, CHAS Background</link>. Census sustenta >30%; HUD documenta también carga severa >50%. Su concepto incluye más componentes que los observables en esta GEIH.',
    "Tiny",
))
story.append(P(
    "Uso de IA. Se utilizó OpenAI Codex para revisar variables, programar controles, auditar extremos y diseñar la ficha. El grupo definió el universo y los umbrales; Codex propuso el corte editorial del 5%; las cifras se validaron con salidas reproducibles.",
    "Tiny",
))

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
doc.build(story, onFirstPage=footer, onLaterPages=footer)
print(OUTPUT)
