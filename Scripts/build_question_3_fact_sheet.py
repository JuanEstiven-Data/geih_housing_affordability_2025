from pathlib import Path

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Table,
    TableStyle,
)


PROJECT = Path(__file__).resolve().parents[1]
SUMMARY = PROJECT / "Output" / "results" / "question_3" / "tenure_gap_summary.csv"
GENERAL_CHART = PROJECT / "Viz" / "question_3_tenure_gaps.png"
EDUCATION_CHART = PROJECT / "Viz" / "question_3_education_gaps.png"
OUTPUT = PROJECT / "Deliverables" / "ficha_resultados_pregunta_3.pdf"

BLUE = colors.HexColor("#245A73")
LIGHT_BLUE = colors.HexColor("#EAF2F6")
GRAY = colors.HexColor("#555555")
LIGHT_GRAY = colors.HexColor("#D9DEE2")


def money(value):
    if pd.isna(value):
        return "No observable"
    return f"${value:,.0f}".replace(",", ".")


def percent(value):
    if pd.isna(value):
        return "No observable"
    return f"{value:.1f}%".replace(".", ",")


def money_iqr(row, metric):
    return (
        f"{money(row[f'median_{metric}'])}<br/>"
        f"[{money(row[f'q1_{metric}'])} - {money(row[f'q3_{metric}'])}]"
    )


def percent_iqr(row, metric):
    return (
        f"{percent(row[f'median_{metric}'])}<br/>"
        f"[{percent(row[f'q1_{metric}'])} - {percent(row[f'q3_{metric}'])}]"
    )


styles = getSampleStyleSheet()
styles.add(
    ParagraphStyle(
        name="FactTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=21,
        textColor=colors.black,
        spaceAfter=3,
    )
)
styles.add(
    ParagraphStyle(
        name="Subtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.7,
        leading=11,
        textColor=GRAY,
        spaceAfter=7,
    )
)
styles.add(
    ParagraphStyle(
        name="Section",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=11.2,
        leading=13,
        textColor=BLUE,
        spaceBefore=5,
        spaceAfter=4,
    )
)
styles.add(
    ParagraphStyle(
        name="BodySmall",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=7.6,
        leading=9.5,
        textColor=colors.black,
        spaceAfter=4,
    )
)
styles.add(
    ParagraphStyle(
        name="BodyTiny",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=6.8,
        leading=8.4,
        textColor=colors.black,
        spaceAfter=3,
    )
)
styles.add(
    ParagraphStyle(
        name="Cell",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=6.5,
        leading=7.8,
        textColor=colors.black,
    )
)
styles.add(
    ParagraphStyle(
        name="CellCenter",
        parent=styles["Cell"],
        alignment=TA_CENTER,
    )
)
styles.add(
    ParagraphStyle(
        name="CellWhite",
        parent=styles["BodyText"],
        fontName="Helvetica-Bold",
        fontSize=6.5,
        leading=7.8,
        textColor=colors.white,
        alignment=TA_CENTER,
    )
)
styles.add(
    ParagraphStyle(
        name="Question",
        parent=styles["BodyText"],
        fontName="Helvetica-Bold",
        fontSize=9.2,
        leading=11.4,
        textColor=colors.black,
        spaceAfter=5,
    )
)


def P(text, style="BodySmall"):
    return Paragraph(str(text), styles[style])


def page_footer(canvas, document):
    canvas.saveState()
    canvas.setStrokeColor(LIGHT_GRAY)
    canvas.line(0.55 * inch, 0.43 * inch, 7.95 * inch, 0.43 * inch)
    canvas.setFont("Helvetica", 6.8)
    canvas.setFillColor(GRAY)
    canvas.drawString(
        0.55 * inch,
        0.27 * inch,
        "Fuente: elaboración propia con microdatos GEIH 2025 del DANE.",
    )
    canvas.drawRightString(7.95 * inch, 0.27 * inch, f"Página {document.page}")
    canvas.restoreState()


def styled_table(data, widths, font_size=6.5):
    table = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
    commands = [
        ("GRID", (0, 0), (-1, -1), 0.35, LIGHT_GRAY),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3.5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3.5),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, -1), font_size),
        ("BACKGROUND", (0, 0), (-1, 0), BLUE),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
    ]
    for row in range(2, len(data), 2):
        commands.append(("BACKGROUND", (0, row), (-1, row), LIGHT_BLUE))
    table.setStyle(TableStyle(commands))
    return table


summary = pd.read_csv(SUMMARY)
general = summary.loc[summary["education_group"].eq("General")]
cali_general = general.loc[general["geography"].eq("Cali A.M.")].set_index(
    "tenure_group"
)
country_general = general.loc[
    general["geography"].eq("Colombia (incluye Cali A.M.)")
].set_index("tenure_group")
cali_education = summary.loc[
    summary["geography"].eq("Cali A.M.")
    & summary["education_group"].ne("General")
]

paid = "Propietarios con vivienda pagada"
paying = "Propietarios que pagan su vivienda"
renters = "Arrendatarios"
other = "Otras formas de tenencia"
tenure_order = [paid, paying, renters, other]
short_names = {
    paid: "Vivienda pagada",
    paying: "Pagando vivienda",
    renters: "Arrendatarios",
    other: "Otras formas",
}

doc = SimpleDocTemplate(
    str(OUTPUT),
    pagesize=letter,
    rightMargin=0.55 * inch,
    leftMargin=0.55 * inch,
    topMargin=0.43 * inch,
    bottomMargin=0.56 * inch,
    title="Ficha de resultados Pregunta 3 GEIH 2025",
    author="Grupo 4",
)

story = []
story.append(P("Ficha de resultados - Pregunta 3", "FactTitle"))
story.append(
    P(
        "Asequibilidad de la vivienda | Grupo 4 | Cali A.M. y Colombia | GEIH 2025",
        "Subtitle",
    )
)
story.append(
    P(
        "¿Qué brechas existen entre arrendatarios, propietarios que pagan su "
        "vivienda y propietarios con vivienda pagada, y cómo varían según la "
        "educación del jefe del hogar?",
        "Question",
    )
)

measurement = [
    [P("Elemento", "CellWhite"), P("Definición aplicada", "CellWhite")],
    [
        P("Unidad y alcance", "Cell"),
        P(
            "Hogar-mes, enero-diciembre de 2025. Cali A.M. = AREA 76. "
            "Colombia incluye Cali A.M.",
            "Cell",
        ),
    ],
    [
        P("Tenencia", "Cell"),
        P(
            "P5090: vivienda pagada; pagando vivienda; arrendatarios; y otras "
            "formas (usufructo, posesión sin título, propiedad colectiva y otra).",
            "Cell",
        ),
    ],
    [
        P("Educación", "Cell"),
        P(
            "P3042 del jefe (P6050 = 1): primaria o menos; secundaria y media; "
            "técnico, tecnólogo o pregrado; postgrado.",
            "Cell",
        ),
    ],
    [
        P("Medición", "Cell"),
        P(
            "Ingreso mensual del hogar agregado desde personas. Pago efectivo: "
            "P5100 o P5140; cero para vivienda pagada y no observable para otras. "
            "Costo equivalente: P5130, o P5140 para arrendatarios.",
            "Cell",
        ),
    ],
    [
        P("Resumen y pesos", "Cell"),
        P(
            "Mediana ponderada acompañada por cuartiles 1 y 3. Se usa FEX_C18; "
            "hogares mensuales promedio = suma anual de pesos / 12.",
            "Cell",
        ),
    ],
]
story.append(styled_table(measurement, [1.08 * inch, 6.28 * inch]))
story.append(P("1. Comparación general por forma de tenencia", "Section"))
story.append(Image(str(GENERAL_CHART), width=7.30 * inch, height=3.08 * inch))

general_header = [
    P("Tenencia", "CellWhite"),
    P("Muestra<br/>Cali / país", "CellWhite"),
    P("Ingreso pc Cali<br/>Md [Q1 - Q3]", "CellWhite"),
    P("Carga equivalente Cali<br/>Md [Q1 - Q3]", "CellWhite"),
    P("Ingreso pc país<br/>Md [Q1 - Q3]", "CellWhite"),
    P("Carga equivalente país<br/>Md [Q1 - Q3]", "CellWhite"),
]
general_rows = [general_header]
for tenure in tenure_order:
    cali_row = cali_general.loc[tenure]
    country_row = country_general.loc[tenure]
    sample_label = (
        f"{int(cali_row['sample_household_months']):,} / "
        f"{int(country_row['sample_household_months']):,}"
    ).replace(",", ".")
    general_rows.append(
        [
            P(short_names[tenure], "Cell"),
            P(sample_label, "CellCenter"),
            P(money_iqr(cali_row, "income_per_capita_cop"), "CellCenter"),
            P(percent_iqr(cali_row, "equivalent_burden_percent"), "CellCenter"),
            P(money_iqr(country_row, "income_per_capita_cop"), "CellCenter"),
            P(percent_iqr(country_row, "equivalent_burden_percent"), "CellCenter"),
        ]
    )
story.append(
    styled_table(
        general_rows,
        [1.05 * inch, 0.78 * inch, 1.42 * inch, 1.39 * inch, 1.42 * inch, 1.39 * inch],
        font_size=6.2,
    )
)
story.append(
    P(
        "Lectura general. En Cali A.M., quienes pagan vivienda presentan el mayor "
        "ingreso per cápita mediano ($1.690.278) y la menor carga equivalente entre "
        "los grupos con costo comparable (21,6%). Arrendatarios registran $925.000 "
        "y 27,3%; otras formas, $788.853 y 32,4%. Los intervalos Q1-Q3 muestran una "
        "dispersión amplia que la mediana general no debe ocultar.",
        "BodyTiny",
    )
)

story.append(PageBreak())
story.append(P("2. Comparación por educación del jefe", "FactTitle"))
story.append(
    P(
        "Medianas ponderadas; las líneas verticales representan los cuartiles 1 y 3.",
        "Subtitle",
    )
)
story.append(Image(str(EDUCATION_CHART), width=7.32 * inch, height=4.88 * inch))

education_header = [
    P("Educación del jefe", "CellWhite"),
    P("Vivienda pagada", "CellWhite"),
    P("Pagando vivienda", "CellWhite"),
    P("Arrendatarios", "CellWhite"),
    P("Otras formas", "CellWhite"),
]
education_rows = [education_header]
education_order = [
    "Primaria o menos",
    "Secundaria y media",
    "Técnico, tecnólogo o pregrado",
    "Postgrado",
]
for education in education_order:
    block = cali_education.loc[
        cali_education["education_group"].eq(education)
    ].set_index("tenure_group")
    education_rows.append(
        [
            P(education, "Cell"),
            *[
                P(
                    percent_iqr(block.loc[tenure], "equivalent_burden_percent"),
                    "CellCenter",
                )
                for tenure in tenure_order
            ],
        ]
    )
story.append(
    styled_table(
        education_rows,
        [1.42 * inch, 1.48 * inch, 1.48 * inch, 1.48 * inch, 1.48 * inch],
        font_size=6.2,
    )
)
story.append(
    P(
        "Carga equivalente en Cali A.M. - Md [Q1 - Q3]. La carga tiende a disminuir al "
        "aumentar la educación del jefe. Entre postgraduados, vivienda pagada, "
        "pagando y arriendo convergen alrededor de 16%; otras formas alcanzan "
        "25,5%, con 37 casos válidos de 39 observaciones. También requieren "
        "cautela primaria-pagando (43 válidos de 44) y postgrado-pagando (85 de 94).",
        "BodyTiny",
    )
)
story.append(P("Interpretación y límites", "Section"))
story.append(
    P(
        "Las brechas varían entre niveles educativos; esta comparación es compatible "
        "con diferencias de composición, sin cuantificar su contribución. Dentro de primaria, "
        "secundaria y formación técnica o universitaria, arrendatarios y otras "
        "formas suelen enfrentar mayor carga equivalente que quienes pagan la "
        "vivienda. Los resultados son descriptivos: educación y tenencia no son "
        "asignadas aleatoriamente. La educación representa al jefe, no a todos los "
        "integrantes.",
        "BodySmall",
    )
)
story.append(
    P(
        "La GEIH usada no registra montos de servicios públicos. P5130 es un "
        "arriendo estimado y no un desembolso. La carga efectiva de otras formas "
        "no es observable. Los códigos de no respuesta se excluyen de los montos. Los hogares con ingreso incompleto, cero o negativo no "
        "entran en razones de carga. Los resultados nacionales incluyen Cali A.M.",
        "BodySmall",
    )
)
story.append(P("Uso de inteligencia artificial", "Section"))
story.append(
    P(
        "Se utilizó OpenAI Codex para revisar variables, programar controles, "
        "depurar el análisis y diseñar la ficha. El grupo definió la pregunta, los "
        "grupos educativos, la tenencia, el uso de mediana y cuartiles y la "
        "interpretación final. Las cifras se validaron contra las salidas "
        "reproducibles del código.",
        "BodyTiny",
    )
)

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
doc.build(story, onFirstPage=page_footer, onLaterPages=page_footer)
print(OUTPUT)
