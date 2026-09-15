# Asequibilidad de la vivienda en Cali A.M.

Actividad grupal de Capstone I basada en los microdatos de la Gran Encuesta
Integrada de Hogares (GEIH) de 2025.

## Preguntas asignadas

1. **Camilo Villota:** ¿Cuánto destinan los hogares a vivienda y servicios
   públicos, y qué proporción representa frente a sus ingresos?
2. **Jostyn Saldarriaga:** ¿Cuántos hogares presentan una carga habitacional
   superior al 30 % o al 50 %, y cuánto ingreso residual per cápita les queda?
3. **Juan Estiven Silva:** ¿Qué brechas existen entre arrendatarios,
   propietarios que pagan su vivienda y propietarios con vivienda pagada?

Las tres preguntas cuentan con código, resultados, visualización y ficha.

## Alcance común

Las estimaciones cubren enero-diciembre de 2025 y se presentan para Cali A.M.
(Cali-Yumbo, `AREA = 76`) y Colombia. Se utiliza `FEX_C18`; las cantidades
mensuales promedio de hogares durante el año se calculan dividiendo entre doce la suma de los
ponderadores mensuales.

La GEIH disponible no contiene montos de servicios públicos. Por ello, cualquier
indicador que use gasto efectivo en vivienda debe declarar que incluye arriendo
o cuota de adquisición, según el régimen de tenencia, pero no servicios públicos.

## Indicadores

El promedio mensual de hogares representados durante los doce cortes
transversales se calcula como:

$$
\widehat{N}_{mensual}=\frac{\sum_{h=1}^{n}FEX\_C18_h}{12}
$$

El ingreso mensual del hogar es la suma del ingreso monetario construido para
sus integrantes:

$$
Y_h=\sum_{i=1}^{n_h}Y_{ih}
$$

El pago efectivo observado se define según la forma de tenencia:

$$
G_h^{ef}=\begin{cases}
0, & \text{vivienda totalmente pagada en las preguntas 1 y 3} \\
P5100_h, & \text{propietario que paga su vivienda} \\
P5140_h, & \text{arrendatario} \\
\text{n. d.}, & \text{otras formas de tenencia}
\end{cases}
$$

La carga efectiva, expresada como porcentaje numérico (por ejemplo, 30 significa
30%), y el ingreso residual per cápita son:

$$
B_h^{ef}=\frac{G_h^{ef}}{Y_h}\times100
$$

$$
R_h^{pc}=\frac{Y_h-G_h^{ef}}{P6008_h}
$$

En la pregunta 2, $B_h^{ef}$ y $R_h^{pc}$ se estiman únicamente para
propietarios que pagan y arrendatarios con ingreso y pago válidos. En la
pregunta 3, el costo equivalente se mantiene separado del pago efectivo.

## Estructura útil

- `Scripts/`: auditoría, construcción de las bases y respuestas reproducibles.
- `Output/`: bases Parquet y tablas de resultados.
- `Viz/`: gráficos utilizados en las fichas.
- `Deliverables/`: fichas individuales en PDF.
- `methodological_decisions_log.md`: bitácora viva de decisiones, supuestos y asuntos pendientes.
- `Raw/`: archivos originales locales, excluidos de GitHub por su tamaño.

## Estado de la pregunta 1

La pregunta conserva su redacción original, pero la respuesta monetaria mide el
pago efectivo de vivienda observado: cuota de adquisición (`P5100`) o arriendo
(`P5140`). La GEIH identifica la disponibilidad de algunos servicios públicos,
pero no cuánto paga el hogar por ellos. `n. d.` significa **no disponible** y no
equivale a cero.

En Cali A.M., el pago mediano es \$900.000 entre propietarios que pagan su
vivienda y \$600.000 entre arrendatarios. Las cargas medianas correspondientes
son 18,1% y 27,3%. La medición registra un monto efectivo para 58,5% de los
hogares; el pago no es observable para el 15,3% agrupado en otras formas de
tenencia.

Archivos correspondientes:

- `Scripts/answer_question_1.py`
- `Output/results/question_1/`
- `Viz/question_1_effective_payment.png`
- `Deliverables/ficha_resultados_pregunta_1.pdf`

## Estado de la pregunta 2

La carga efectiva se estima para propietarios que pagan su vivienda y
arrendatarios con ingreso completo y positivo y pago informado. Los propietarios
con vivienda pagada y las otras formas permanecen en el universo descriptivo,
pero no reciben una estimación de carga en esta pregunta.

En Cali A.M., aproximadamente 196.157 hogares mensuales promedio con carga
estimable superan el 30% y 73.005 superan el 50%. El ingreso residual per cápita
mediano es \$1.005.875 entre los hogares con carga hasta 30% y \$308.333 entre los
que superan ese umbral. Los residuales negativos representan 4,70% del universo
estimable y se documentan en una auditoría separada. El corte editorial de 5%
propuesto en la implementación solo organiza su presentación; no es un estándar
estadístico ni elimina casos. Véase MD-18 en la bitácora.

Archivos correspondientes:

- `Scripts/answer_question_2.py`
- `Output/results/question_2/`
- `Viz/question_2_burden_and_residual.png`
- `Deliverables/ficha_resultados_pregunta_2.pdf`

## Estado de la pregunta 3

La pregunta 3 presenta dos niveles de análisis: una comparación general por
tenencia y una comparación dentro de cuatro niveles educativos del jefe del
hogar. Cada mediana ponderada se acompaña por los cuartiles 1 y 3.

En Cali A.M., el ingreso per cápita mediano es \$1.690.278 entre propietarios que
pagan, \$1.256.667 entre propietarios con vivienda pagada, \$925.000 entre
arrendatarios y \$788.853 en otras formas de tenencia. La carga equivalente
mediana es 21,6%, 24,3%, 27,3% y 32,4%, respectivamente.

Archivos correspondientes:

- `Scripts/answer_question_3.py`
- `Output/results/question_3/`
- `Viz/question_3_tenure_gaps.png`
- `Viz/question_3_education_gaps.png`
- `Deliverables/ficha_resultados_pregunta_3.pdf`

## Ejecución

Flujo verificado con Python 3.12. Desde la raíz del proyecto, crear el entorno
solo si todavía no existe:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Para reconstruir desde los originales locales (requiere `Raw/` completo):

```powershell
python Scripts\audit_source_files.py
python Scripts\build_selected_modules.py
```

Para reproducir resultados y fichas desde los Parquet incluidos en el repositorio:

```powershell
python Scripts\answer_question_1.py
python Scripts\answer_question_2.py
python Scripts\answer_question_3.py
python Scripts\build_question_1_fact_sheet.py
python Scripts\build_question_2_fact_sheet.py
python Scripts\build_question_3_fact_sheet.py
```

Las ejecuciones de las preguntas deben terminar con:

```text
QUESTION 1: EFFECTIVE HOUSING PAYMENT
RESULT: PASS
QUESTION 2: BURDEN THRESHOLDS AND RESIDUAL INCOME
RESULT: PASS
QUESTION 3: TENURE GAPS BY EDUCATION
RESULT: PASS
```

## Datos y reproducibilidad

Los scripts usan rutas relativas a la raíz del proyecto. Los dos archivos
Parquet necesarios para ejecutar los análisis se conservan en `Output`. Los 192
archivos originales CSV y SAV permanecen localmente en `Raw` y no se publican
en GitHub. Quien clone el repositorio puede comenzar con las respuestas y los
generadores de fichas, sin ejecutar la auditoría de fuentes ni la construcción
desde `Raw/`. Las dependencias declaradas cubren los ocho scripts actuales;
ReportLab genera los PDF. La pregunta 2 utiliza la salida de la pregunta 1.

La auditoría revisa llaves, uniones, cobertura, consistencia entre preguntas y
dependencias. Sus informes quedan en `Output/results/validation/` y en los
`validation.json` de cada pregunta. Los códigos de no respuesta se excluyen de
los montos. Los valores extremos conservados se concilian con las bases
intermedias; ello verifica el procesamiento, no la exactitud de lo declarado.
Las limitaciones vigentes se registran en MD-13, MD-15 y MD-18 de la bitácora.

## Uso de inteligencia artificial

Se utilizó OpenAI Codex para revisar el diccionario, escribir y depurar el
código y preparar la presentación. Las variables, categorías y cifras se
contrastaron con la documentación GEIH, los archivos fuente y los controles de
ejecución incluidos en el repositorio.
