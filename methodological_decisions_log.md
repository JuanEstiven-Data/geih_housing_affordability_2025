# Bitácora de decisiones metodológicas

## Propósito del documento

Esta bitácora registra las decisiones metodológicas utilizadas en la actividad
GEIH del Grupo 4. Es un documento vivo: cualquier cambio en la medición, el
universo analítico o la interpretación debe registrarse aquí antes de actualizar
el código, los resultados y las fichas.

**Proyecto:** Asequibilidad de la vivienda y carga habitacional en Cali A.M., 2025

**Fuente:** GEIH 2025, DANE

**Última actualización:** 2026-09-15

**Responsables:** Camilo Villota, Juan Estiven Silva y Jostyn Saldarriaga

## Estados utilizados

- **Confirmada:** decisión adoptada e implementada; no implica que sus supuestos
  o la información declarada por los encuestados estén libres de limitaciones.
- **Provisional:** implementada, pero requiere una comprobación adicional.
- **Pendiente:** debe resolverse antes de contestar la pregunta correspondiente.
- **Reemplazada:** dejó de aplicarse, pero se conserva para documentar el cambio.

## Índice de decisiones

| ID | Decisión | Estado | Aplicación |
|---|---|---|---|
| MD-01 | Estudio descriptivo y distributivo | Confirmada | Proyecto completo |
| MD-02 | Unidad analítica hogar-mes | Confirmada | Proyecto completo |
| MD-03 | Cali A.M. corresponde a `AREA = 76` | Confirmada | Proyecto completo |
| MD-04 | El referente nacional incluye Cali A.M. | Confirmada | Proyecto completo |
| MD-05 | Usar `FEX_C18` y dividir entre 12 las sumas anuales de pesos | Confirmada | Proyecto completo |
| MD-06 | Leer cinco módulos en CSV y auditar los esquemas SAV | Confirmada | Proyecto completo |
| MD-07 | Mantener separadas las bases intermedias de hogares y personas | Confirmada | Proyecto completo |
| MD-08 | No incluir servicios públicos porque no hay montos disponibles | Confirmada | Preguntas 1–3 |
| MD-09 | Mantener tres categorías principales y añadir otras formas agrupadas | Confirmada | Preguntas 1–3 |
| MD-10 | Definir el pago efectivo de vivienda según la tenencia | Confirmada | Preguntas 1–3 |
| MD-11 | Presentar un escenario de costo habitacional equivalente | Confirmada | Pregunta 3 |
| MD-12 | Construir y validar el ingreso monetario corriente mensual del hogar | Confirmada | Preguntas 1–3 |
| MD-13 | Calcular la carga solo con ingreso completo y positivo | Confirmada | Preguntas 1–3 |
| MD-14 | Usar mediana ponderada con cuartiles 1 y 3 | Confirmada | Preguntas 1–3 |
| MD-15 | Agrupar valores de 2025 en pesos corrientes sin deflactar por mes | Provisional | Preguntas 1–3 |
| MD-16 | Interpretar los resultados sin afirmaciones causales | Confirmada | Proyecto completo |
| MD-17 | Incluir cuatro grupos y documentar la cobertura parcial del gasto | Confirmada | Pregunta 1 |
| MD-18 | Comparar carga hasta 30% y superior a 30%, conservando residuales negativos | Confirmada | Pregunta 2 |
| MD-19 | Agrupar y comparar las otras formas de tenencia | Confirmada | Pregunta 3 |
| MD-20 | Delimitar el alcance de los controles contra doble contabilización | Confirmada | Preguntas 1–3 |
| MD-21 | Segmentar la pregunta 3 por educación del jefe del hogar | Confirmada | Pregunta 3 |

## Registro detallado

Las decisiones se presentan en el orden en que se aplican: alcance, datos, medición, reglas de análisis y decisiones específicas de cada pregunta.

### MD-01 — Naturaleza descriptiva y distributiva

- **Estado:** Confirmada.
- **Decisión:** Estimar quién soporta qué carga habitacional y cómo se distribuye.
  No estimar efectos causales de la tenencia o del pago de vivienda sobre el
  bienestar.
- **Razón:** La guía y el objetivo actual requieren caracterización y comparación,
  no identificación causal.
- **Implicación:** Usar cantidades, proporciones, medianas, percentiles y brechas
  ponderadas. Interpretarlas como asociaciones o diferencias descriptivas.

### MD-02 — Unidad analítica hogar-mes

- **Estado:** Confirmada.
- **Decisión:** La unidad final es un hogar observado en un mes de encuesta.
- **Razón:** La tenencia y los pagos de vivienda se registran una vez por hogar,
  mientras que los ingresos se registran para las personas que lo integran.
- **Implementación:** Sumar el ingreso personal mediante `survey_year`,
  `survey_month`, `DIRECTORIO`, `SECUENCIA_P` y `HOGAR`, y unirlo después con el
  registro del hogar.
- **Implicación:** Una fila representa un hogar-mes, no un hogar seguido de manera
  longitudinal. Los archivos mensuales se apilan para describir 2025.

### MD-03 — Definición geográfica de Cali A.M.

- **Estado:** Confirmada.
- **Decisión:** Identificar Cali A.M. mediante `AREA = 76`, correspondiente a
  Cali–Yumbo.
- **Evidencia:** Definición establecida en la guía de la actividad.
- **Implicación:** Toda estimación de Cali debe aplicar exactamente este filtro.

### MD-04 — Colombia incluye Cali A.M.

- **Estado:** Confirmada.
- **Decisión:** La estimación nacional usa todos los registros GEIH, incluido
  `AREA = 76`.
- **Razón:** La actividad solicita resultados para Cali A.M. y Colombia, no para
  Cali A.M. y el resto de Colombia.
- **Implicación:** No hay doble contabilización porque los resultados se presentan
  por separado y nunca se suman. El referente nacional no es independiente de
  Cali; las tablas y figuras deben rotularlo como **“Colombia (incluye Cali A.M.)”.**
- **Comprobación opcional:** Se puede añadir “Resto de Colombia” para interpretar
  la brecha territorial, pero no reemplaza el resultado nacional exigido.

### MD-05 — Ponderadores y doce archivos mensuales

- **Estado:** Confirmada.
- **Decisión:** Utilizar `FEX_C18` en las estimaciones poblacionales.
- **Reglas:**
  - Cantidad promedio mensual de hogares:

    $$
    \widehat{N}_{mensual}=\frac{\sum_{h=1}^{n}FEX\_C18_h}{12}
    $$

  - Proporciones y medias: numerador ponderado dividido por denominador ponderado;
    dividir ambos entre 12 no modifica el resultado.
  - Medianas y percentiles ponderados: usar `FEX_C18`; dividir todos los pesos
    entre 12 tampoco modifica los cuantiles.
  - Reportar siempre el número no ponderado de observaciones hogar-mes.
- **Razón:** Las doce muestras transversales permiten estimar una población mensual
  promedio durante 2025.

### MD-06 — Módulos fuente y formato de lectura

- **Estado:** Confirmada.
- **Decisión:** Construir el análisis con cinco módulos mensuales:
  1. Datos del hogar y la vivienda.
  2. Características generales, seguridad social y educación.
  3. No ocupados.
  4. Ocupados.
  5. Otros ingresos e impuestos.
- **Formato operativo:** Leer los CSV con pandas y usar los SAV para verificar la
  disponibilidad de variables y la consistencia de los esquemas.
- **Razón:** DANE suministra los mismos microdatos en ambos formatos; CSV facilita
  un flujo transparente de Python de nivel intermedio.
- **Implicación:** La elección de CSV es operativa y no cambia la fuente estadística.

### MD-07 — Dos bases intermedias

- **Estado:** Confirmada.
- **Decisión:** Mantener:
  - `Output/household_core_2025.parquet`: una fila por hogar-mes.
  - `Output/person_components_2025.parquet`: una fila por persona-mes.
- **Razón:** Unir los ingresos personales directamente con los pagos del hogar
  repetiría el mismo pago por cada integrante.
- **Implicación:** Primero se agrega el ingreso personal y solo después se une con
  la base de hogares.

### MD-08 — Tratamiento de los servicios públicos

- **Estado:** Confirmada bajo la regla de disponibilidad acordada.
- **Decisión:** No imputar ni inventar pagos de servicios públicos.
- **Evidencia:** Las preguntas seleccionadas de la GEIH no registran montos pagados
  por electricidad, agua, gas u otros servicios. Si no existe una pregunta que
  recoja la información necesaria, se considera que el dato no está disponible.
- **Implicación:** El gasto efectivo observado contiene arriendo o cuota de
  adquisición según la tenencia, pero excluye servicios públicos. Toda ficha que
  use la medida debe declarar esta limitación.

### MD-09 — Universo de tenencia de la pregunta 3

- **Estado:** Confirmada; reemplaza la exclusión inicial de las demás formas de
  tenencia.
- **Decisión:** Conservar como grupos principales las tres categorías mencionadas
  en la pregunta y añadir una cuarta categoría complementaria:
  - `P5090 = 1`: propietario con vivienda totalmente pagada.
  - `P5090 = 2`: propietario que está pagando su vivienda.
  - `P5090 = 3`: arrendatario.
  - `P5090 in {4, 5, 6, 7}`: otras formas de tenencia.
- **Razón:** Las categorías restantes tienen suficiente peso para que su exclusión
  limite la descripción de la población. La evaluación detallada se registra en
  MD-19.
- **Implicación:** La respuesta directa seguirá destacando las tres categorías
  exigidas. “Otras formas de tenencia” aparecerá como comparación complementaria
  y no como sustituto de ninguno de esos grupos.

### MD-10 — Pago efectivo de vivienda

- **Estado:** Confirmada.
- **Decisión:** Definir el desembolso monetario mensual como:

  $$
  G_h^{ef}=\begin{cases}
  0, & \text{si }P5090_h=1\text{, en las preguntas 1 y 3} \\
  P5100_h, & \text{si }P5090_h=2 \\
  P5140_h, & \text{si }P5090_h=3 \\
  \text{n. d.}, & \text{si }P5090_h\in\{4,5,6,7\}
  \end{cases}
  $$

  En la pregunta 2 no se estima la carga de los propietarios con vivienda
  pagada, porque el cero de arriendo o cuota no representa todos sus costos.
- **Razón:** `P5100` y `P5140` siguen los saltos del cuestionario y representan
  pagos observados. La ausencia de una pregunta para las otras formas no prueba
  que esos hogares no realicen ningún desembolso.
- **Implicación:** El cero de los propietarios con vivienda pagada significa que
  no pagan arriendo ni cuota de adquisición. No significa que el servicio de
  vivienda carezca de valor económico ni que no existan mantenimiento, impuestos
  o servicios públicos. Las otras formas se conservarán como “pago efectivo no
  observable”.

### MD-11 — Costo habitacional equivalente

- **Estado:** Confirmada como medición complementaria.
- **Decisión:** Definir el costo habitacional equivalente usado en la pregunta 3
  como:

  $$
  G_h^{eq}=\begin{cases}
  P5140_h, & \text{si }P5090_h=3 \\
  P5130_h, & \text{si }P5090_h\in\{1,2,4,5,6,7\}
  \end{cases}
  $$
- **Razón:** El arriendo estimado permite aproximar de manera más comparable el
  valor del servicio de vivienda en los cuatro grupos.
- **Implicación:** Nunca describir `P5130` como gasto efectivo ni restarlo del
  ingreso para afirmar cuánto dinero disponible conserva realmente el hogar.
  Presentar primero el pago efectivo observado y el costo equivalente como una
  comparación complementaria.

### MD-12 — Ingreso monetario mensual del hogar

- **Estado:** Confirmada.
- **Definición por persona:**

  $$
  Y_{ih}=INGLABO_i+P7422S1_i+
  \sum_{k\in M}P7500_{ik}+
  \frac{1}{12}\sum_{j\in A}P7510_{ij}
  $$

  donde $M$ contiene los componentes mensuales seleccionados y $A$ los
  componentes anuales seleccionados. Los símbolos representan montos depurados
  y condicionados a la recepción del ingreso: no se suman respuestas negativas
  ni códigos especiales como si fueran dinero. Una recepción desconocida o un
  monto faltante con recepción afirmativa marca el ingreso como incompleto.

- **Componentes incluidos:**
  - `INGLABO`: ingreso laboral mensual total construido por DANE.
  - `P7422S1`: ingreso laboral del mes anterior de personas no ocupadas durante
    la semana de referencia, condicionado a `P7422 = 1`.
  - `P7500S1A1`: arriendos recibidos por propiedades.
  - `P7500S2A1`: pensiones.
  - `P7500S3A1`: cuotas alimentarias.
  - $P7510S1A1 / 12$: transferencias de hogares en Colombia.
  - $P7510S2A1 / 12$: transferencias del exterior.
  - $P7510S3A1 / 12$: ayudas institucionales.
  - $P7510S5A1 / 12$: intereses, dividendos y rendimientos.
- **Regla contra doble contabilización:** No sumar `P7070` porque ya está
  incorporada en `INGLABO`.
- **Agregación:** Sumar los ingresos de todas las personas del hogar:

  $$
  Y_h=\sum_{i=1}^{n_h}Y_{ih}
  $$

- **Ingreso per cápita:**

  $$
  Y_h^{pc}=\frac{Y_h}{P6008_h}
  $$
- **Validación de `INGLABO`:** Entre 358.029 registros del módulo de ocupados,
  8.199 tienen `INGLABO` ausente. De ellos, 5.830 corresponden a trabajadores
  familiares sin remuneración (`P6430 = 6`) y reciben ingreso laboral cero; los
  2.369 restantes se marcan como ingreso incompleto. Ningún ocupado carece de
  `P6430`. Esta regla evita confundir sistemáticamente no remuneración con no
  respuesta.

### MD-13 — Ingreso faltante y validez del denominador

- **Estado:** Confirmada.
- **Decisión:**
  - `98`: la persona recibió o realiza el pago, pero **no sabe el monto**.
  - `99`: el monto **no fue informado**. En las preguntas de vivienda puede
    indicar que la persona paga, pero no quiere informar el valor.
  - `999999999`: no tiene una definición semántica en el diccionario de datos
    entregado ni una etiqueta en los archivos SAV. Aparece dos veces en los
    componentes monetarios seleccionados: una vez en `P7500S1A1` y una vez en
    `P7500S2A1`. Por su carácter extremo y su discontinuidad frente a los demás
    valores, se trata operacionalmente como faltante para evitar incorporarlo
    como ingreso mensual, pero no se afirma que signifique “no sabe” o “no
    informa”. Esta regla debe revisarse si el DANE publica una definición
    específica para esos registros.
  - Ninguno de estos valores se interpreta como un monto de 98, 99 o 999.999.999
    pesos. Se conserva su frecuencia en los controles de validación.
  - La regla se aplica tanto a los componentes de ingreso como a `P5100`,
    `P5130` y `P5140`; los registros afectados quedan fuera del cálculo que
    requiere ese monto, pero permanecen en los controles de cobertura.
  - Si una persona afirma recibir un componente, pero el monto está ausente,
    marcar como incompleto el ingreso del hogar.
  - Interpretar un indicador de aplicabilidad faltante como pregunta no aplicable,
    no como recepción afirmativa del ingreso.
  - Calcular la carga habitacional solo para hogares con ingreso completo y mayor
    que cero.
- **Carga efectiva:** El indicador se expresa como porcentaje numérico: 30
  representa 30% del ingreso.

  $$
  B_h^{ef}=\frac{G_h^{ef}}{Y_h}\times100
  $$

- **Implicación:** Los hogares con ingreso cero, negativo o incompleto permanecen
  en los diagnósticos de muestra, pero no entran en razones que usan ingreso como
  denominador.

### MD-14 — Resúmenes principales de la pregunta 3

- **Estado:** Confirmada e implementada.
- **Decisión:** Usar medianas ponderadas como resúmenes principales y acompañar
  cada mediana con el cuartil 1 (Q1) y el cuartil 3 (Q3).
- **Comparación de los tres grupos nombrados en la pregunta:**
  - Ingreso per cápita del hogar.
  - Pago efectivo de vivienda.
  - Carga habitacional efectiva.
  - Carga habitacional equivalente.
- **Comparación complementaria de las otras formas de tenencia:**
  - Ingreso per cápita del hogar.
  - Costo y carga habitacional equivalentes.
  - El pago y la carga efectivos se reportan como no observables.
- **Indicador adicional:** Proporción ponderada con carga efectiva superior al
  30% entre los hogares para los cuales puede calcularse válidamente.
- **Grupo de referencia:** Arrendatarios. Calcular el valor de los arrendatarios
  menos el valor de cada grupo únicamente cuando el indicador sea comparable.
- **Razón:** Las medianas son menos sensibles a la asimetría y a los valores
  extremos frecuentes en ingresos y cargas. Separar medidas efectivas y
  equivalentes evita presentar un arriendo imputado como desembolso real.

Para cada indicador se conservan únicamente sus observaciones válidas con peso
positivo. El cuantil ponderado se define sin interpolación:

$$
\widehat{Q}(p)=\inf\left\{x:\frac{\sum_h w_h\mathbf{1}(x_h\leq x)}{\sum_h w_h}\geq p\right\},
\quad p\in\{0.25,0.50,0.75\}
$$

$Q_1=\widehat{Q}(0.25)$, $Md=\widehat{Q}(0.50)$ y $Q_3=\widehat{Q}(0.75)$.
El intervalo Q1–Q3 describe dispersión, no un intervalo de confianza. Los tamaños
válidos pueden diferir entre ingreso, pago y carga dentro de una misma celda.

### MD-15 — Tratamiento de precios

- **Estado:** Provisional.
- **Decisión:** Agrupar las observaciones mensuales en pesos colombianos corrientes
  de 2025, sin ajustar por variaciones de precios entre enero y diciembre.
- **Razón:** La actividad describe un mismo año calendario y no exige actualmente
  comparaciones en precios constantes.
- **Implicación:** Presentar las cifras como pesos mensuales nominales de 2025.
  Reconsiderar solo si la variación mensual real se vuelve central.

### MD-16 — Interpretación de las brechas

- **Estado:** Confirmada.
- **Decisión:** Describir las diferencias con expresiones como “presenta”,
  “registra”, “es mayor o menor” o “se asocia”.
- **Restricción:** No afirmar que arrendar causa bajo ingreso ni que ser propietario
  causa menor carga.
- **Razón:** La tenencia no se asigna aleatoriamente y el análisis no controla por
  selección, composición del hogar u otros factores de confusión.

### MD-17 — Medición de la pregunta 1 con cuatro grupos de tenencia

- **Estado:** Confirmada e implementada en el script, los resultados, el gráfico
  y la ficha de la pregunta 1.
- **Decisión:** Conservar la redacción original de la pregunta, pero responderla
  operacionalmente con el pago efectivo de vivienda disponible en la GEIH e
  indicar expresamente que los montos de servicios públicos no están disponibles.
- **Universo de tenencia:**
  - Propietario con vivienda totalmente pagada (`P5090 = 1`).
  - Propietario que paga su vivienda (`P5090 = 2`).
  - Arrendatario (`P5090 = 3`).
  - Otras formas de tenencia (`P5090 in {4, 5, 6, 7}`).
- **Pago efectivo observado:**
  - Vivienda pagada: cero por arriendo o cuota de adquisición.
  - Vivienda que se está pagando: `P5100`.
  - Arrendatario: `P5140`.
  - Otras formas: no disponible. La encuesta no formula una pregunta de pago
    efectivo equivalente para estas categorías y no se les asignará cero.
- **Convención `n. d.`:** Significa **no disponible**. Indica que la encuesta no
  recoge la información o no permite estimarla. No significa cero, ausencia de
  gasto ni ausencia del fenómeno estudiado.
- **Información no disponible:** Aunque la GEIH pregunta por la disponibilidad
  de algunos servicios públicos básicos, no registra cuánto paga el hogar por
  electricidad, agua, gas u otros servicios. Disponibilidad del servicio no es
  equivalente a gasto monetario.
- **Comparabilidad:** La comparación directa de montos efectivos se realizará
  entre propietarios que pagan (`P5100`) y arrendatarios (`P5140`). Los
  propietarios con vivienda pagada se mostrarán con cero en arriendo o cuota,
  aclarando que no es gasto habitacional total. Las otras formas permanecerán
  en la misma estructura con `n. d.` para pago y carga efectivos.
- **Proporción de pagos en otras formas:** No es estimable. `P5130` pregunta un
  arriendo hipotético y no permite identificar si el hogar efectúa algún pago
  monetario. La ficha mostrará la proporción de hogares cuya medición es
  observable, no una proporción inventada de pagos efectivos en este grupo.
- **Razón:** La guía permite una medición parcial cuando la encuesta solo observa
  parte del concepto, siempre que se delimite con precisión. Bajo la regla
  acordada, la ausencia de una pregunta monetaria implica ausencia del dato; no
  se imputarán pagos efectivos sin respaldo.
- **Implicación para la ficha y el código:**
  - Conservar los cuatro grupos en la base, los tamaños de muestra y la
    descripción de cobertura.
  - Presentar el indicador monetario principal como **pago efectivo de vivienda
    observado** y señalar que no se estima para otras formas de tenencia.
  - Usar medianas ponderadas acompañadas por Q1 y Q3, igual que en la pregunta 3.
  - Reportar la cobertura de la medición y los códigos de no respuesta 98 y 99.
  - No rotular el pago observado como gasto total de vivienda y servicios.
  - Explicar que la ausencia de servicios subestima el compromiso monetario
    habitacional total de los hogares que sí realizan esos pagos.
- **Redacción acordada:** “La GEIH permite observar el arriendo o la cuota de
  adquisición para las formas de tenencia a las que estas preguntas aplican,
  pero no identifica un pago efectivo equivalente para las otras formas ni los
  montos de servicios públicos. Los resultados representan una medición parcial
  del gasto habitacional y deben interpretarse dentro de ese alcance”.

### MD-18 — Umbrales de carga e ingreso residual de la pregunta 2

- **Estado:** Confirmada e implementada en el script, los resultados, el gráfico,
  la auditoría y la ficha de la pregunta 2.
- **Universo:** Conservar en la base las cuatro categorías de MD-09: vivienda
  pagada, vivienda que se está pagando, arrendatarios y otras formas de tenencia.
- **Disponibilidad dentro del universo:**
  - La clasificación principal se calculará para propietarios que pagan su
    vivienda y arrendatarios con ingreso y pago válidos.
  - Los propietarios con vivienda pagada permanecen en el universo descriptivo,
    pero no reciben una estimación de carga ni aparecen en el gráfico de
    umbrales. El cero usado en las preguntas 1 y 3 solo representa ausencia de arriendo
    o cuota de adquisición y no una medición de su carga habitacional completa.
  - Las otras formas permanecen en el universo y se reportan como **carga efectiva
    no observable**. No se clasifican artificialmente como carga cero.
  - No se incorporará `P5130` en esta pregunta porque es un arriendo estimado y
    no un desembolso que reduzca el ingreso residual.
- **Denominador de los umbrales:** Propietarios que pagan y arrendatarios con
  ingreso mensual completo y positivo y pago efectivo informado. La ficha debe
  mostrar también el tamaño del universo total y la cobertura de este
  denominador.
- **Comparación principal:**
  - **Carga dentro del máximo recomendado:**

    $$
    B_h^{ef}\leq30
    $$

  - **Carga habitacional elevada:**

    $$
    B_h^{ef}>30
    $$

  - Los hogares con carga exactamente igual a 30% pertenecen al primer grupo,
    porque el criterio institucional define la carga elevada como superior al
    30%.
- **Umbral adicional exigido por la pregunta original:** Mantener como subgrupo
  de carga severa:

  $$
  B_h^{ef}>50
  $$

  Este grupo está contenido dentro de $B_h^{ef}>30$.
- **Sustento externo del umbral:**
  - Cromwell, M. (2022), *Renters More Likely Than Homeowners to Spend More Than
    30% of Income on Housing in Almost All Counties*, U.S. Census Bureau:
    https://www.census.gov/library/stories/2022/12/housing-costs-burden.html
  - U.S. Department of Housing and Urban Development, *CHAS: Background*:
    https://www.huduser.gov/portal/datasets/cp/CHAS/bg_chas.html
  Census sustenta la clasificación de carga superior al 30%; HUD documenta
  también la categoría severa superior al 50%.
- **Alcance de la referencia:** Las fuentes estadounidenses incluyen servicios y
  otros costos de vivienda en el numerador. La GEIH utilizada no observa todos
  esos componentes. El umbral se adopta como criterio de clasificación, pero las
  proporciones estimadas no deben presentarse como directamente equivalentes a
  las de Estados Unidos.
- **Ingreso residual per cápita:**

  $$
  R_h^{pc}=\frac{Y_h-G_h^{ef}}{P6008_h}
  $$

- **Tratamiento de valores negativos:** Conservarlos sin truncarlos a cero ni
  eliminarlos. Un valor negativo indica que el pago observado de vivienda supera
  el ingreso monetario construido para el hogar durante el periodo de referencia.
  No implica automáticamente un error: el hogar puede usar ahorro, crédito,
  transferencias no observadas o presentar diferencias temporales entre ingreso
  y gasto.
- **Regla editorial de materialidad:** Crear un subgrupo visual separado si los residuales
  negativos representan al menos 5% ponderado del universo con carga estimable
  en Cali A.M. o Colombia. Si quedan por debajo, mencionarlos en el texto y
  conservar su auditoría tabular, sin convertirlos en un tercer grupo principal.
  El 5% fue una elección de implementación propuesta por Codex para concretar
  “proporción considerable”; no es un estándar del DANE ni una prueba estadística,
  y no fue un umbral numérico indicado por el grupo. No elimina casos ni modifica
  los cálculos. Dentro del grupo con carga superior al 30%, los negativos son
  11,18% en Cali A.M. y 9,24% en Colombia, por lo que siguen siendo relevantes.
- **Auditoría obligatoria de residuales negativos:**
  1. Comprobar que `residual < 0` coincide con `pago efectivo > ingreso del hogar`.
  2. Reportar cantidad no ponderada, cantidad ponderada y proporción ponderada de
     residuales negativos para Cali A.M. y Colombia.
  3. Describirlos por forma de tenencia y mostrar mínimo, percentil 1, percentil 5
     y mediana, sin publicar identificadores de hogares.
  4. Conciliar todos los registros negativos, incluidos los extremos, con el
     ingreso reconstruido desde los componentes personales y con `P5100` o
     `P5140` de la base intermedia de hogares.
  5. Informar cuántos casos dependen de ingreso incompleto, pago faltante o códigos
     especiales; estos casos no entrarán en la clasificación de carga válida.
  6. Guardar `negative_residual_records_audit.csv`: una fila por residual
     negativo, sin llaves del hogar, con ingreso reconstruido, pago fuente,
     tamaño del hogar y comprobaciones del signo y la conciliación. Estos
     controles verifican el procesamiento; no certifican el reporte original.
- **Resultados producidos por la pregunta 2:**
  - Número y proporción de hogares con carga $B_h^{ef}\leq30$ y $B_h^{ef}>30$.
  - Número y proporción con carga $B_h^{ef}>50$.
  - Ingreso residual per cápita mediano en los grupos $B_h^{ef}\leq30$ y $B_h^{ef}>30$.
  - Diagnóstico específico de los valores residuales negativos.
  - Todos los resultados para Cali A.M. y Colombia, con `FEX_C18` y tamaño de
    muestra no ponderado.
- **Resultado de la regla de materialidad:** Los residuales negativos representan
  4,70% ponderado del universo estimable en Cali A.M. y 3,79% en Colombia. Como
  ninguno alcanza 5%, se mencionan y auditan, pero no forman un tercer grupo en
  el gráfico principal.
- **Resultados principales en Cali A.M.:** Aproximadamente 271.092 hogares
  mensuales promedio se encuentran hasta el 30% de carga y 196.157 superan el
  30%; dentro de estos últimos, 73.005 superan el 50%. El ingreso residual per
  cápita mediano es \$1.005.875 en el primer grupo y \$308.333 en el segundo.
  La asociación es parcialmente mecánica: el gasto y el ingreso se usan tanto
  para formar los grupos como para calcular el residual. No identifica un efecto
  causal de la carga sobre el bienestar ni mide consumo efectivo.

### MD-19 — Inclusión agrupada de otras formas de tenencia

- **Estado:** Confirmada e implementada en el script, los resultados, el
  gráfico y la ficha de la pregunta 3.
- **Decisión:** Agrupar `P5090 = 4, 5, 6 y 7` bajo el rótulo **“Otras formas de
  tenencia”** y compararlo con las tres categorías principales.
- **Composición del grupo:**
  - `P5090 = 4`: usufructo.
  - `P5090 = 5`: posesión sin título.
  - `P5090 = 6`: propiedad colectiva.
  - `P5090 = 7`: otra forma.
- **Evidencia cuantitativa:**
  - Cali A.M.: 1.605 observaciones hogar-mes y cerca de 127.988 hogares mensuales
    promedio, equivalentes al 15,32% ponderado de los hogares.
  - Colombia: 74.810 observaciones hogar-mes y cerca de 4.652.583 hogares mensuales
    promedio, equivalentes al 25,32% ponderado de los hogares.
  - Dentro de la categoría agrupada, el usufructo representa 91,31% en Cali A.M.
    y 73,26% en Colombia. La composición no es igual entre territorios.
- **Consecuencias favorables:**
  1. Se evita omitir una fracción relevante de hogares, especialmente en el total
     nacional.
  2. Se amplía la descripción del sistema de tenencia y se muestra que la
     oposición propietario-arrendatario no cubre todos los hogares.
  3. `P5130` permite comparar el costo habitacional equivalente cuando contiene
     un monto válido. Que el campo esté poblado no basta: los códigos de no
     respuesta se excluyen del indicador y reducen su cobertura.
- **Consecuencias y límites:**
  1. La categoría es heterogénea: usufructo, posesión sin título, propiedad
     colectiva y otras modalidades no implican los mismos derechos ni pagos.
  2. Su composición territorial difiere. Una brecha Cali-Colombia puede reflejar
     tanto diferencias económicas como distinta mezcla interna del grupo.
  3. La GEIH no recoge para estas categorías un pago efectivo equivalente a
     `P5100` o `P5140`. La ausencia de pregunta no demuestra que el pago sea cero.
  4. Por lo anterior, no se calculará una carga monetaria efectiva para el grupo
     asignándole cero. Sí se podrá comparar su ingreso per cápita y su carga
     equivalente mediante `P5130`.
  5. Añadir un cuarto grupo aumenta el contenido de la ficha. Los tres grupos
     nombrados en la pregunta deben conservar prioridad visual y narrativa.
- **Regla de presentación:** Incluir “Otras formas de tenencia” en tablas y, si el
  espacio lo permite, en el gráfico complementario. Separar claramente:
  - Comparaciones de **pago y carga efectiva**, disponibles para las categorías
    con desembolso observado.
  - Comparaciones de **ingreso y costo equivalente**, disponibles para los cuatro
    grupos.
- **Interpretación:** Los resultados del grupo agregado describen en conjunto a
  las formas restantes y no deben atribuirse individualmente a usufructuarios,
  ocupantes sin título o propietarios colectivos.

### MD-20 — Alcance de los controles contra doble contabilización

- **Estado:** Confirmada.
- **Decisión:** Afirmar únicamente que la construcción evita la duplicación
  producida por las uniones entre módulos y la suma repetida de componentes
  laborales conocidos. No afirmar que el código puede verificar si cada persona
  declaró correctamente sus ingresos.
- **Razón:** La doble contabilización puede surgir en dos niveles distintos:
  1. **Error de procesamiento:** una unión multiplica registros o el programa suma
     dos veces el mismo componente. Este riesgo sí puede controlarse con código.
  2. **Error de respuesta:** una persona informa mal un monto o dos integrantes
     atribuyen como propio el mismo ingreso familiar. Este riesgo pertenece a la
     calidad de la encuesta y no puede detectarse solamente con las variables
     utilizadas.
- **Controles implementados:**
  1. La llave de persona
     `(año, mes, DIRECTORIO, SECUENCIA_P, HOGAR, ORDEN)` debe ser única dentro de
     cada módulo. Si aparecen duplicados, la construcción se detiene.
  2. Las uniones entre módulos de personas usan `validate="one_to_one"`. Así, una
     fila no puede multiplicarse silenciosamente al cruzar las bases.
  3. Se verifica que una persona no aparezca simultáneamente en los módulos de
     ocupados y no ocupados (`labor_overlap = 0`). Esto evita asignarle a la misma
     persona `INGLABO` y `P7422S1` por una superposición de módulos.
  4. `INGLABO` se usa como ingreso laboral agregado construido por DANE. Sus
     componentes internos, incluido `P7070` asociado al segundo empleo, no se
     vuelven a sumar.
  5. Los valores `P7500` y `P7510` se suman porque representan fuentes distintas:
     arriendos recibidos, pensiones, cuotas alimentarias, transferencias, ayudas,
     intereses y dividendos. Recibir varias fuentes simultáneamente no constituye
     duplicación.
  6. Un monto condicionado se suma solamente cuando la pregunta indicadora señala
     que la persona recibió ese ingreso. Una respuesta negativa produce cero; una
     respuesta afirmativa sin monto marca el ingreso del hogar como incompleto.
  7. Después de calcular una vez el ingreso de cada persona, se agrega por hogar:

     $$
     Y_h=\sum_{i=1}^{n_h}Y_{ih}
     $$

     El número de integrantes agrupados debe coincidir con `P6008`. El ingreso
     agregado se une una sola vez con el registro de vivienda mediante una relación
     `one_to_one`.
- **Ejemplo:** Si una persona recibe \$2.000.000 de salario y otra recibe \$1.200.000
  de pensión más \$100.000 de transferencia, el ingreso del hogar es \$3.300.000.
  Se suman recursos de personas y fuentes diferentes; ninguna fila ni componente
  conocido se cuenta dos veces.
- **Limitaciones:**
  - La comprobación de `INGLABO` de MD-12 ya se implementó: entre ocupados con
    monto ausente, 5.830 familiares sin remuneración reciben cero y 2.369 casos
    restantes se marcan como incompletos. La clasificación no prueba que los
    montos declarados por los demás ocupados sean correctos.
  - Los controles no permiten saber si un encuestado informó un valor incorrecto
    ni si dos integrantes declararon por error el mismo ingreso familiar.
- **Redacción válida para la sustentación:** “El código no duplica registros ni
  suma deliberadamente dos veces un mismo componente conocido. Los errores de
  declaración de los encuestados permanecen como una limitación propia de la
  fuente”.

### MD-21 — Educación del jefe del hogar como criterio de segmentación

- **Estado:** Confirmada e implementada en el script, los resultados y la
  ficha de la pregunta 3.
- **Decisión:** Clasificar cada hogar mediante el máximo nivel educativo alcanzado
  por su jefe, identificado con `P6050 = 1`. No se usará el máximo nivel entre
  todos los integrantes ni la educación promedio del hogar.
- **Razón:** La educación es una variable personal y la unidad del estudio es el
  hogar. Usar el jefe proporciona una referencia única y reproducible para
  trasladar esa característica al nivel del hogar.
- **Variable educativa:** `P3042`, mayor nivel educativo alcanzado y último grado
  o semestre aprobado.
- **Agrupación:**
  - **Primaria o menos:** `P3042 in {1, 2, 3}` — ninguno, preescolar y básica
    primaria.
  - **Secundaria y media:** `P3042 in {4, 5, 6, 7}` — básica secundaria, media
    académica, media técnica y normalista.
  - **Técnico, tecnólogo o pregrado:** `P3042 in {8, 9, 10}` — técnica
    profesional, tecnológica y universitaria.
  - **Postgrado:** `P3042 in {11, 12, 13}` — especialización, maestría y
    doctorado.
  - `P3042 = 99` o ausente: educación no informada; conservar en los controles de
    cobertura y excluir de las comparaciones educativas.
- **Precisión del grupo:** El nombre “Secundaria y media” refleja que la categoría
  reúne básica secundaria, media académica, media técnica y normalista.
- **Validaciones realizadas:**
  - Los 292.942 hogares-mes de la base tienen exactamente un registro con
    `P6050 = 1`.
  - No se encontraron hogares sin jefe ni hogares con más de un jefe.
  - En Cali A.M. no hay jefes con educación no informada; en Colombia hay dos
    observaciones hogar-mes en esa condición.
- **Comparación:** Dentro de cada grupo educativo se contrastarán las cuatro formas
  de tenencia definidas en MD-09. Los resultados generales por tenencia se
  conservarán como referencia para evaluar cuánto cambia la brecha después de la
  segmentación.
- **Medidas principales:** Usar la mediana ponderada y acompañarla con Q1 y
  Q3. Mantener las restricciones de comparabilidad entre pago efectivo y costo
  equivalente establecidas en MD-14.
- **Precaución por tamaño de muestra:** Reportar el tamaño no ponderado de cada
  cruce educación–tenencia. Señalar las celdas con menos de 100 observaciones y
  advertir especialmente las menores de 50; no suprimirlas automáticamente sin
  una decisión posterior del grupo.
- **Alcance interpretativo:** La categoría representa la educación del jefe, no la
  de todos los integrantes. Las diferencias dentro de cada estrato continúan
  siendo descriptivas y no demuestran que la educación o la tenencia causen la
  carga observada.
## Estado de implementación

La bitácora distingue una decisión aprobada de su implementación material. Al
15 de septiembre de 2026, las tres preguntas están implementadas:

| Decisión | Limitación vigente |
|---|---|
| MD-13 | El tratamiento de 999999999 es operacional y revisable; su significado no está documentado. |
| MD-15 | Las cifras monetarias se presentan en pesos corrientes, sin deflactar entre meses. |
| MD-18 | El corte editorial de 5% no es un estándar estadístico. La auditoría verifica procesamiento, no veracidad del reporte. |

La pregunta 1 incorpora las cuatro formas de tenencia, la medición de cobertura,
los códigos de no respuesta y los cuartiles 1 y 3. La pregunta 2 incorpora los
umbrales, el ingreso residual per cápita y la auditoría de negativos. La pregunta
3 incorpora las cuatro formas de tenencia, la educación del jefe y los cuartiles
1 y 3; sus 40 filas de resumen se dividen en 8 resultados generales y 32 cruces
educación-tenencia.

## Diseño vigente de la pregunta 3

La tenencia forma los grupos y las condiciones económicas constituyen los
resultados. El ingreso es necesario porque el pago nominal por sí solo no mide
asequibilidad: dos hogares que pagan la misma cantidad pueden soportar cargas
distintas si sus recursos difieren.

La versión vigente conserva como comparación principal los tres grupos de la
pregunta e incorpora “Otras formas de tenencia” como grupo complementario.
Presenta un análisis general y otro dentro de los cuatro niveles educativos del
jefe, siguiendo las restricciones de comparabilidad de MD-14, MD-19 y MD-21.

El referente nacional incluye Cali A.M. Las tablas deben usar estos rótulos:

- **Cali A.M.**
- **Colombia (incluye Cali A.M.)**

## Protocolo de actualización

Cuando el grupo modifique una regla metodológica:

1. Agregar una decisión o actualizar el estado de la decisión existente.
2. Registrar la fecha y la razón en el historial de cambios.
3. Actualizar el script de Python correspondiente.
4. Regenerar tablas, gráficos y ficha.
5. Comprobar que la interpretación escrita coincida con los nuevos resultados.

## Historial de cambios

| Fecha | ID | Cambio | Responsable |
|---|---|---|---|
| 2026-09-15 | MD-01–MD-18 | Creación inicial a partir del flujo implementado y las decisiones pendientes | Grupo 4 |
| 2026-09-15 | MD-20 | Se delimitó qué doble contabilización controla el código y qué errores de respuesta quedan fuera de su alcance | Grupo 4 |
| 2026-09-15 | MD-09, MD-17 y MD-19 | Se decidió incluir otras formas de tenencia como categoría complementaria y responder la pregunta 1 con la información disponible, documentando la ausencia de servicios | Grupo 4 |
| 2026-09-15 | MD-17 y MD-18 | Se incorporó la cuarta categoría en la pregunta 1 y se cerraron el universo, los umbrales, el tratamiento de residuales negativos y el sustento institucional de la pregunta 2 | Grupo 4 |
| 2026-09-15 | MD-10, MD-11, MD-14 y orden general | Se alinearon las medidas con la cuarta categoría, se ordenaron MD-01–MD-20 y se añadió el estado de implementación | Grupo 4 |
| 2026-09-15 | MD-21 | Se definió la educación del jefe del hogar como criterio para comparar las formas de tenencia dentro de cuatro grupos educativos | Grupo 4 |
| 2026-09-15 | MD-12, MD-14, MD-19 y MD-21 | Se validó INGLABO y se implementaron cuatro tenencias, educación del jefe, mediana, Q1 y Q3 en el código, resultados, gráficos y ficha de la pregunta 3 | Grupo 4 |
| 2026-09-15 | MD-08, MD-10 y MD-17 | Se implementó la pregunta 1 con pagos efectivos, cobertura, `n. d.`, códigos 98 y 99, mediana, Q1, Q3, resultados, gráfico y ficha | Grupo 4 |
| 2026-09-15 | MD-13 y MD-18 | Se implementó la pregunta 2 con universo estimable de pagadores, umbrales de 30% y 50%, ingreso residual, regla de materialidad, auditoría de negativos, gráfico y ficha | Grupo 4 |
| 2026-09-15 | Auditoría global | Se corrigió la limpieza de 98 y 99 en pagos y arriendo estimado de la pregunta 3, se actualizaron cifras, se conciliaron los negativos, se añadieron los generadores PDF y se expresaron los indicadores como ecuaciones. Se corrigió el estado de la validación de INGLABO y se explicitó el origen editorial del corte de 5%. | Codex, por solicitud del grupo |

## Plantilla para una decisión nueva

```markdown
### MD-XX — Nombre breve de la decisión

- **Estado:** Pendiente / Provisional / Confirmada / Reemplazada.
- **Fecha:** AAAA-MM-DD.
- **Decisión:** Qué se decidió.
- **Razón:** Por qué se eligió esta alternativa.
- **Evidencia:** Guía, diccionario, cuestionario, validación o resultado que la respalda.
- **Implicación:** Qué cambia en el universo, indicador, código o interpretación.
- **Responsable:** Integrante que realizó la comprobación.
```
