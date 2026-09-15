from pathlib import Path

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Table, TableStyle


PROJECT = Path(__file__).resolve().parents[1]
SUMMARY = PROJECT / "Output" / "results" / "question_1" / "effective_payment_summary.csv"
COVERAGE = PROJECT / "Output" / "results" / "question_1" / "payment_coverage.csv"
CHART = PROJECT / "Viz" / "question_1_effective_payment.png"
OUTPUT = PROJECT / "Deliverables" / "ficha_resultados_pregunta_1.pdf"

BLUE = colors.HexColor("#245A73")
LIGHT_BLUE = colors.HexColor("#EAF2F6")
GRAY = colors.HexColor("#555555")
LIGHT_GRAY = colors.HexColor("#D9DEE2")


def money(value):
    if pd.isna(value):
        return "n. d."
    return f"${value:,.0f}".replace(",", ".")


def percent(value):
    if pd.isna(value):
        return "n. d."
    return f"{value:.1f}%".replace(".", ",")


def money_iqr(row):
    if pd.isna(row["median_effective_payment_cop"]):
        return "n. d."
    return (
        f"{money(row['median_effective_payment_cop'])}<br/>"
        f"[{money(row['q1_effective_payment_cop'])} - "
        f"{money(row['q3_effective_payment_cop'])}]"
    )


def burden_iqr(row):
    if pd.isna(row["median_effective_burden_percent"]):
        return "n. d."
    return (
        f"{percent(row['median_effective_burden_percent'])}<br/>"
        f"[{percent(row['q1_effective_burden_percent'])} - "
        f"{percent(row['q3_effective_burden_percent'])}]"
    )


styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name="FactTitle", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=17, leading=19, spaceAfter=2))
styles.add(ParagraphStyle(name="Subtitle", parent=styles["Normal"], fontSize=8.3, leading=10, textColor=GRAY, spaceAfter=5))
styles.add(ParagraphStyle(name="Question", parent=styles["BodyText"], fontName="Helvetica-Bold", fontSize=8.8, leading=10.6, spaceAfter=4))
styles.add(ParagraphStyle(name="Section", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=10.5, leading=12, textColor=BLUE, spaceBefore=3, spaceAfter=3))
styles.add(ParagraphStyle(name="Body", parent=styles["BodyText"], fontSize=7.1, leading=8.7, spaceAfter=3))
styles.add(ParagraphStyle(name="Tiny", parent=styles["BodyText"], fontSize=6.2, leading=7.3, textColor=GRAY, spaceAfter=2))
styles.add(ParagraphStyle(name="Cell", parent=styles["BodyText"], fontSize=6.1, leading=7.2))
styles.add(ParagraphStyle(name="CellCenter", parent=styles["Cell"], alignment=TA_CENTER))
styles.add(ParagraphStyle(name="CellWhite", parent=styles["CellCenter"], fontName="Helvetica-Bold", textColor=colors.white))


def P(text, style="Body"):
    return Paragraph(str(text), styles[style])


def footer(canvas, document):
    canvas.saveState()
    canvas.setStrokeColor(LIGHT_GRAY)
    canvas.line(0.55 * inch, 0.42 * inch, 7.95 * inch, 0.42 * inch)
    canvas.setFont("Helvetica", 6.3)
    canvas.setFillColor(GRAY)
    canvas.drawString(0.55 * inch, 0.26 * inch, "Fuente: elaboración propia con microdatos GEIH 2025 del DANE.")
    canvas.drawRightString(7.95 * inch, 0.26 * inch, f"Página {document.page}")
    canvas.restoreState()


def styled_table(data, widths):
    table = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
    commands = [
        ("GRID", (0, 0), (-1, -1), 0.35, LIGHT_GRAY),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 2.4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.4),
        ("BACKGROUND", (0, 0), (-1, 0), BLUE),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
    ]
    for row in range(2, len(data), 2):
        commands.append(("BACKGROUND", (0, row), (-1, row), LIGHT_BLUE))
    table.setStyle(TableStyle(commands))
    return table


summary = pd.read_csv(SUMMARY)
coverage = pd.read_csv(COVERAGE)
cali = summary.loc[summary["geography"].eq("Cali A.M.")].set_index("tenure_group")
country = summary.loc[summary["geography"].eq("Colombia (incluye Cali A.M.)")].set_index("tenure_group")
cali_coverage = coverage.loc[coverage["geography"].eq("Cali A.M.")].set_index("payment_status")
country_coverage = coverage.loc[coverage["geography"].eq("Colombia (incluye Cali A.M.)")].set_index("payment_status")

tenure_order = [
    "Propietarios con vivienda pagada",
    "Propietarios que pagan su vivienda",
    "Arrendatarios",
    "Otras formas de tenencia",
]
short_names = {
    tenure_order[0]: "Vivienda pagada",
    tenure_order[1]: "Pagando vivienda",
    tenure_order[2]: "Arrendatarios",
    tenure_order[3]: "Otras formas",
}

doc = SimpleDocTemplate(
    str(OUTPUT), pagesize=letter, rightMargin=0.55 * inch, leftMargin=0.55 * inch,
    topMargin=0.38 * inch, bottomMargin=0.52 * inch,
    title="Ficha de resultados Pregunta 1 GEIH 2025", author="Grupo 4",
)
story = [
    P("Ficha de resultados - Pregunta 1", "FactTitle"),
    P("Asequibilidad de la vivienda | Grupo 4 | Cali A.M. y Colombia | GEIH 2025", "Subtitle"),
    P("¿Cuánto destinan los hogares a vivienda y servicios públicos, y qué proporción representa frente a sus ingresos?", "Question"),
]

measurement = [
    [P("Elemento", "CellWhite"), P("Definición aplicada", "CellWhite")],
    [P("Medida", "Cell"), P("Pago efectivo mensual observado: cuota de adquisición P5100 o arriendo P5140. La carga divide ese pago entre el ingreso mensual del hogar.", "Cell")],
    [P("Tenencia", "Cell"), P("Vivienda pagada: $0 de arriendo/cuota; pagando y arriendo: monto declarado; otras formas: n. d. (no disponible).", "Cell")],
    [P("Resumen", "Cell"), P("Mediana ponderada [Q1 - Q3]. FEX_C18; hogares mensuales promedio = suma anual de ponderadores / 12. Colombia incluye Cali A.M.", "Cell")],
]
story.append(styled_table(measurement, [1.02 * inch, 6.34 * inch]))
story.append(P("Resultados", "Section"))
story.append(Image(str(CHART), width=7.30 * inch, height=3.08 * inch))

header = [
    P("Tenencia", "CellWhite"),
    P("Pago Cali<br/>Md [Q1 - Q3]", "CellWhite"),
    P("Carga Cali<br/>Md [Q1 - Q3]", "CellWhite"),
    P("Pago Colombia<br/>Md [Q1 - Q3]", "CellWhite"),
    P("Carga Colombia<br/>Md [Q1 - Q3]", "CellWhite"),
]
rows = [header]
for tenure in tenure_order:
    rows.append([
        P(short_names[tenure], "Cell"),
        P(money_iqr(cali.loc[tenure]), "CellCenter"),
        P(burden_iqr(cali.loc[tenure]), "CellCenter"),
        P(money_iqr(country.loc[tenure]), "CellCenter"),
        P(burden_iqr(country.loc[tenure]), "CellCenter"),
    ])
story.append(styled_table(rows, [1.28 * inch, 1.52 * inch, 1.30 * inch, 1.65 * inch, 1.61 * inch]))

coverage_header = [P("Cobertura de la medición", "CellWhite"), P("Cali A.M.", "CellWhite"), P("Colombia", "CellWhite")]
coverage_rows = [coverage_header]
for status in [
    "Monto efectivo observado",
    "Sin arriendo o cuota de adquisición",
    "Monto efectivo no informado",
    "Pago efectivo no observable",
]:
    coverage_rows.append([
        P(status, "Cell"),
        P(percent(cali_coverage.loc[status, "weighted_share_percent"]), "CellCenter"),
        P(percent(country_coverage.loc[status, "weighted_share_percent"]), "CellCenter"),
    ])
story.append(P("Cobertura y lectura", "Section"))
story.append(styled_table(coverage_rows, [4.20 * inch, 1.58 * inch, 1.58 * inch]))
story.append(P(
    f"Muestra total (hogares-mes): Cali {int(cali['sample_household_months'].sum()):,}; "
    f"Colombia {int(country['sample_household_months'].sum()):,}. "
    f"Casos con carga válida: {int(cali['valid_burden_sample'].sum()):,} y "
    f"{int(country['valid_burden_sample'].sum()):,}, respectivamente. "
    "Las tablas CSV detallan la muestra válida por tenencia e indicador.",
    "Tiny",
))
story.append(P(
    "En Cali A.M., el pago mediano es $900.000 para propietarios que pagan y $600.000 para arrendatarios. Sin embargo, la carga mediana es menor entre quienes pagan vivienda (18,1%) que entre arrendatarios (27,3%), porque el indicador también refleja el ingreso del hogar. El 58,5% de los hogares tiene un monto efectivo observado; para 15,3%, agrupado en otras formas de tenencia, la encuesta no formula una pregunta de desembolso equivalente.",
    "Body",
))
story.append(P(
    "Limitación. Se conserva la pregunta original, pero la respuesta monetaria no incluye servicios públicos: la GEIH identifica la disponibilidad de algunos servicios, no cuánto paga el hogar por ellos. El cero de una vivienda pagada significa ausencia de arriendo o cuota de adquisición, no gasto habitacional total. n. d. significa no disponible y no equivale a cero. Los hogares con ingreso incompleto, cero o negativo no entran en la carga. Resultados descriptivos, sin interpretación causal.",
    "Tiny",
))
story.append(P(
    "Uso de IA. Se utilizó OpenAI Codex para revisar variables, programar controles, depurar el análisis y diseñar la ficha. El grupo definió las medidas, restricciones e interpretación; las cifras se validaron con salidas reproducibles.",
    "Tiny",
))

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
doc.build(story, onFirstPage=footer, onLaterPages=footer)
print(OUTPUT)
