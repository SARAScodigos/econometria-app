# Especificación de variables en un modelo VARX con intervención estatal y choque COVID-19

## 1. Estructura general del modelo

El estudio empleará un modelo de Vectores Autorregresivos con variables exógenas (VARX), debido a que el volumen de créditos y la morosidad pueden influirse mutuamente a lo largo del tiempo, pero también responden a condiciones macroeconómicas y a intervenciones externas, como la pandemia de COVID-19 y las medidas estatales de apoyo financiero.

La formulación general del modelo es:

$$
Y_t = c + A_1Y_{t-1} + A_2Y_{t-2} + \cdots + A_pY_{t-p} + BX_t + \varepsilon_t
$$

Donde:

- $Y_t$ representa el vector de variables endógenas.
- $A_1, A_2, \ldots, A_p$ son las matrices de coeficientes asociadas a los rezagos de las variables endógenas.
- $X_t$ contiene las variables exógenas.
- $B$ representa la matriz de coeficientes de las variables exógenas.
- $\varepsilon_t$ corresponde al vector de errores o innovaciones no explicadas por el modelo.

El periodo de análisis comprende observaciones mensuales desde enero de 2002 hasta diciembre de 2022, lo que proporciona aproximadamente 252 observaciones para la estimación econométrica.

---

## 2. Vector de variables endógenas

Las variables endógenas son aquellas cuyo comportamiento se explica, en parte, por sus propios valores pasados y por la interacción dinámica entre ellas.

En este estudio, el vector endógeno será:

$$
Y_t =
\begin{bmatrix}
Volumen_t \\
Morosidad_t
\end{bmatrix}
$$

Donde:

- $Volumen_t$: representa el nivel mensual del volumen de créditos, colocaciones u otra medida de financiamiento utilizada en la investigación.
- $Morosidad_t$: representa el indicador mensual de deterioro de cartera, como cartera atrasada, ratio de morosidad o crédito vencido, según la definición operacional seleccionada.

La inclusión conjunta de ambas variables permite analizar relaciones dinámicas relevantes. Por ejemplo, un incremento del volumen de créditos puede generar inicialmente una expansión de la cartera, pero posteriormente podría incidir en la morosidad. Del mismo modo, un aumento sostenido de la morosidad puede reducir la disposición de las entidades financieras a otorgar nuevos créditos.

---

## 3. Vector de variables exógenas

Las variables exógenas son factores que influyen en el sistema, pero que no son explicados internamente por el comportamiento del volumen de créditos y la morosidad.

El vector exógeno propuesto será:

$$
X_t =
\begin{bmatrix}
PBI_t \\
TasaRef_t \\
D_{COVID,t} \\
D_{Ayuda,t}
\end{bmatrix}
$$

Donde:

- $PBI_t$: indicador mensual de actividad económica. Puede emplearse la variación porcentual interanual, la variación mensual desestacionalizada o un indicador mensual proxy de actividad económica.
- $TasaRef_t$: tasa de interés de referencia del Banco Central de Reserva del Perú, expresada como promedio mensual o valor de cierre de cada mes.
- $D_{COVID,t}$: variable de intervención que representa el choque extraordinario asociado al inicio de la pandemia y las restricciones de movilidad.
- $D_{Ayuda,t}$: variable de intervención que representa el periodo de aplicación efectiva de medidas estatales de apoyo crediticio y alivio financiero.

Así, el modelo puede expresarse de manera ampliada como:

$$
\begin{bmatrix}
Volumen_t \\
Morosidad_t
\end{bmatrix}
=
c
+ A_1
\begin{bmatrix}
Volumen_{t-1} \\
Morosidad_{t-1}
\end{bmatrix}
+ \cdots
+ A_p
\begin{bmatrix}
Volumen_{t-p} \\
Morosidad_{t-p}
\end{bmatrix}
+ B
\begin{bmatrix}
PBI_t \\
TasaRef_t \\
D_{COVID,t} \\
D_{Ayuda,t}
\end{bmatrix}
+
\begin{bmatrix}
\varepsilon_{1t} \\
\varepsilon_{2t}
\end{bmatrix}
$$

---

## 4. Variable agregada de ayuda estatal

La variable $D_{Ayuda,t}$ representa la existencia de un régimen extraordinario de apoyo estatal al sistema financiero y a los agentes económicos afectados por la pandemia.

Esta variable integra, en una sola intervención, los principales mecanismos de apoyo implementados durante el periodo de emergencia, tales como:

- Reactiva Perú.
- Fondo de Apoyo Empresarial para las MYPE, denominado FAE-MYPE.
- Reprogramaciones crediticias y medidas de flexibilización o alivio financiero.

Su codificación puede definirse de la siguiente manera:

$$
D_{Ayuda,t} =
\begin{cases}
1, & \text{si durante el mes } t \text{ estuvo vigente al menos una medida de apoyo estatal} \\
0, & \text{si durante el mes } t \text{ no estuvo vigente ninguna medida de apoyo}
\end{cases}
$$

En términos lógicos:

$$
D_{Ayuda,t} =
\max \left(
D_{Reactiva,t},
D_{FAE\text{-}MYPE,t},
D_{Reprogramacion,t}
\right)
$$

Por tanto, la variable toma el valor de 1 cuando al menos uno de los programas o mecanismos de apoyo se encontraba operativo en el mes analizado.

| Mes            | Reactiva Perú | FAE-MYPE | Reprogramaciones | $D_{Ayuda,t}$ |
| -------------- | -------------: | -------: | ---------------: | --------------: |
| Marzo 2020     |              0 |        0 |                0 |               0 |
| Abril 2020     |              0 |        0 |                0 |               0 |
| Mayo 2020      |              1 |        0 |                0 |               1 |
| Junio 2020     |              1 |        1 |                1 |               1 |
| Diciembre 2020 |              1 |        1 |                1 |               1 |
| Julio 2021     |              0 |        1 |                1 |               1 |
| Enero 2022     |              0 |        0 |                1 |               1 |
| Diciembre 2022 |              0 |        0 |                0 |               0 |

---

## 5. Justificación del uso de una sola variable de ayuda estatal

Se empleará una sola variable agregada de ayuda estatal porque Reactiva Perú, FAE-MYPE y las reprogramaciones crediticias fueron medidas aplicadas en un contexto común: reducir los efectos económicos y financieros de la pandemia sobre empresas, hogares y entidades financieras.

Aunque cada instrumento tuvo mecanismos específicos, los tres compartieron una finalidad general: preservar liquidez, evitar el cierre de empresas, sostener la capacidad de pago de los deudores y reducir el riesgo de deterioro acelerado de la cartera crediticia.

El uso de una sola variable presenta tres ventajas metodológicas:

1. **Evita la multicolinealidad.** Las medidas fueron aplicadas en periodos cercanos y, en varios meses, coexistieron. Si se incorporan dummies separadas para Reactiva, FAE-MYPE y reprogramaciones, el modelo podría tener dificultades para distinguir con precisión el efecto individual de cada intervención, debido a la alta superposición temporal entre ellas.
2. **Preserva grados de libertad.** Aunque la serie contiene aproximadamente 252 observaciones, solo alrededor de 34 corresponden al periodo comprendido entre marzo de 2020 y diciembre de 2022. Introducir numerosas variables de intervención para un periodo relativamente breve puede sobrecargar la especificación y reducir la estabilidad de las estimaciones.
3. **Permite una interpretación coherente con el objetivo general del estudio.** La variable no pretende identificar cuánto efecto corresponde exclusivamente a Reactiva Perú, FAE-MYPE o reprogramaciones. Su finalidad es estimar si, durante el periodo de apoyo estatal extraordinario, el comportamiento del volumen y la morosidad fue distinto al esperado según sus propios rezagos, la actividad económica y la tasa de referencia.

En consecuencia, el coeficiente de $D_{Ayuda,t}$ debe interpretarse como un efecto conjunto o promedio asociado al régimen de intervención estatal, no como un efecto causal individual atribuible a un programa específico.

---

## 6. Tratamiento del choque COVID-19

El choque inicial de la pandemia puede representarse mediante una variable de intervención temporal, especialmente para los meses de marzo y abril de 2020, cuando se produjo la paralización abrupta de actividades económicas y restricciones intensas de movilidad.

Una forma simple de codificarla sería mediante una dummy pulso:

$$
D_{COVID,t} =
\begin{cases}
1, & \text{si } t = \text{marzo de 2020 o abril de 2020} \\
0, & \text{en los demás meses}
\end{cases}
$$

Sin embargo, el valor 1 no significa que el impacto económico haya tenido la misma magnitud en marzo y abril. El valor 1 solo identifica la ocurrencia del choque. La magnitud efectiva del impacto sobre el volumen de créditos y la morosidad es estimada por el modelo mediante los coeficientes asociados a dicha variable.

Por ejemplo, si el coeficiente de $D_{COVID,t}$ en la ecuación de volumen es negativo y estadísticamente significativo, ello indicará que, durante marzo y abril de 2020, el volumen de créditos fue menor al esperado según la dinámica previa de las variables endógenas, el PBI, la tasa de referencia y las demás variables incluidas.

---

## 7. Uso de diferencias de escenarios para estimar el efecto COVID-19

El efecto de la pandemia también puede analizarse mediante una comparación de escenarios. No obstante, esta comparación no debe utilizarse para asignar directamente valores distintos a la dummy antes de estimar el modelo.

La lógica correcta consiste en estimar primero el VARX con la variable de intervención COVID-19 y, posteriormente, construir dos trayectorias:

$$
\text{Escenario observado: } D_{COVID,t}=1
$$

$$
\text{Escenario contrafactual: } D_{COVID,t}=0
$$

La diferencia entre ambas trayectorias estimadas representa el efecto atribuido al choque COVID-19 dentro de la estructura del modelo:

$$
Impacto_t = \widehat{Y}_{t}^{observado} - \widehat{Y}_{t}^{contrafactual}
$$

De esta manera, el modelo permite estimar cuánto habría sido el volumen o la morosidad en ausencia del choque inicial de la pandemia, manteniendo constantes las demás condiciones incluidas en la especificación.

Por tanto, no es necesario que marzo y abril tengan necesariamente valores idénticos de impacto. La dummy puede codificarse como 1 en ambos meses, pero los efectos estimados pueden diferir por la dinámica autorregresiva, los rezagos y la interacción con las demás variables exógenas.

---

## 8. Alternativa: variable de intensidad del choque COVID-19

Si se dispone de una medida objetiva y externa que refleje la intensidad mensual del choque, la dummy simple puede complementarse o sustituirse por una variable continua.

Por ejemplo, podrían emplearse indicadores como:

- Variación interanual del PBI mensual.
- Índice de movilidad.
- Índice de severidad de restricciones.
- Caída sectorial de ventas, producción o empleo.
- Número de días de inmovilización obligatoria por mes.

En ese caso, la variable podría tomar valores diferentes entre marzo y abril de 2020, reflejando que el impacto no fue necesariamente homogéneo.

No obstante, debe evitarse construir la intensidad del choque usando directamente el volumen o la morosidad observada, porque ello generaría problemas de endogeneidad. La variable de intensidad debe provenir de una fuente externa e independiente del sistema financiero analizado.

Una alternativa técnica sería:

$$
COVIDIntensidad_t =
\frac{\text{Días de restricción en el mes } t}{\text{Días totales del mes } t}
$$

Por ejemplo:

| Mes        | Días con restricción intensa | Días del mes | Intensidad COVID |
| ---------- | -----------------------------: | ------------: | ---------------: |
| Marzo 2020 |                             16 |            31 |            0.516 |
| Abril 2020 |                             30 |            30 |            1.000 |
| Mayo 2020  |                             31 |            31 |            1.000 |
| Junio 2020 |                             30 |            30 |            1.000 |

Esta alternativa sería útil si el objetivo es capturar diferencias en la intensidad de las restricciones. Sin embargo, para una especificación principal más parsimoniosa, la dummy pulso para marzo y abril de 2020 suele ser suficiente, mientras que la diferencia entre escenarios permite cuantificar posteriormente la magnitud estimada del choque.

---

## 9. Especificación recomendada

Una especificación inicial parsimoniosa puede ser:

$$
Y_t =
\begin{bmatrix}
\Delta \ln(Volumen_t) \\
Morosidad_t
\end{bmatrix}
$$

$$
X_t =
\begin{bmatrix}
\Delta PBI_t \\
TasaRef_t \\
D_{COVID,t} \\
D_{Ayuda,t}
\end{bmatrix}
$$

Donde:

- $\Delta \ln(Volumen_t)$ representa la variación logarítmica del volumen de créditos.
- $Morosidad_t$ representa el nivel o ratio de morosidad.
- $\Delta PBI_t$ representa la variación del indicador mensual de actividad económica.
- $TasaRef_t$ representa la tasa de referencia monetaria.
- $D_{COVID,t}$ identifica el choque inicial de marzo y abril de 2020.
- $D_{Ayuda,t}$ identifica el periodo de intervención estatal agregada.

Finalmente, como análisis de robustez, la dummy agregada de ayuda estatal puede sustituirse por dummies separadas de Reactiva Perú, FAE-MYPE y reprogramaciones, siempre que se evalúe previamente la correlación entre ellas y se justifique su capacidad de identificación dentro de la muestra.
