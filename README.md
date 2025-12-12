# Practicas-1-

Introducción
La Cooperativa de Provisión de Obras y Servicios Públicos Limitada de Armstrong tiene a su cargo la distribución de energía eléctrica a usuarios residenciales, comerciales e industriales de la localidad.
Con el objetivo de mejorar la planificación energética, el control de pérdidas y la detección de posibles fraudes o fallas, se analizó el consumo mensual de energía desde 2022 en adelante, generando:
•	Un pronóstico de demanda para los próximos 12 meses.
•	La identificación de picos históricos y tendencias.
•	La detección de anomalías a nivel de medidor (variaciones bruscas o comportamientos atípicos).

Descripción de la base de datos
El dataset consumo_energia_2022_en_adelante.csv contiene registros de consumo eléctrico mensual por medidor.
Las columnas principales son:
•	numero_medidor: identificador único del medidor.
•	año y mes: periodo de registro.
•	consumo_kwh: consumo mensual de energía en kilovatios-hora.
A partir de esta información, el código procesa y consolida el consumo total mensual de toda la cooperativa.

Metodología aplicada
El análisis se desarrolló en Python, utilizando la siguiente estructura:
•	Modelado de tendencia y estacionalidad:
Método de Holt-Winters (suavizado exponencial triple) implementado en statsmodels.
Si hay más de 24 meses de datos, el modelo aprende la tendencia de crecimiento y la estacionalidad anual.
Si hay menos datos, se aplica un método estacional ingenuo (replica el consumo del mismo mes del año anterior).

•  Cálculo de indicadores (KPIs):
•	Consumo total histórico.
•	Consumo mensual promedio.
•	Pico histórico y fecha del pico.
•	Pronóstico máximo esperado y mes proyectado de mayor consumo.
•  Detección de anomalías:
1.	Cambios abruptos: variaciones mayores al +200% o menores al -50% respecto al mes anterior.
2.	Z-score robusto: diferencia extrema respecto a la mediana móvil de 12 meses (|Z| ≥ 4).
•  Visualización y salidas:
•	CSVs con indicadores (kpis_consumo.csv, pronostico_consumo_12m.csv, posibles_anomalias_recientes.csv).
•	Gráficos en PNG con evolución histórica, pronóstico. 

Resultados del análisis histórico
El consumo mensual total de la cooperativa mostró variaciones moderadas con clara estacionalidad bianual:
•	Picos de demanda en verano (diciembre–febrero) y julio,
•	Valles en abril–mayo y octubre–noviembre.

Promedios por año:
<img width="583" height="235" alt="image" src="https://github.com/user-attachments/assets/60a53245-37eb-486a-a612-42a6d449c5d8" />

⚡ En todo el periodo histórico (2022–2025) el consumo máximo se registró en diciembre de 2022 con 3.607.440 kWh, mientras que los valores mínimos se dieron en abril–mayo de 2023–2024 (≈2,65 MWh).

Pronóstico de demanda (septiembre 2025 – agosto 2026)
Según el modelo Holt-Winters, la demanda proyectada mantiene el patrón estacional histórico, con leve tendencia al crecimiento.

<img width="442" height="501" alt="image" src="https://github.com/user-attachments/assets/7f2c6c63-6758-4ce1-82d3-f12c57d68e92" />

Total energía proyectada 2025–2026: ≈ 39.85 millones de kWh
Promedio mensual proyectado: ≈ 3.32 millones de kWh/mes
Pico proyectado: marzo 2026 (3.96 MWh)
•	Se prevé un incremento promedio del 4% anual respecto al consumo de 2024.
 
•	La estacionalidad se conserva: los picos de verano e invierno son más marcados, con leve desplazamiento hacia marzo.
Detección de anomalías

<img width="567" height="390" alt="image" src="https://github.com/user-attachments/assets/52411230-24f3-466b-9da6-cb00a37d6224" />

Esto significa que, durante el período analizado en 2025, el sistema detectó un total de 4 986 eventos anómalos, de los cuales:
•	El 66 % (3 291) fueron cambios abruptos de consumo,
•	El 34 % (1 695) fueron desviaciones robustas (Z-score).
•	Cambio abrupto → lecturas con caídas > 50 % o subas > 200 % respecto al mes anterior.
Posibles causas: fallas en medición, reconexiones, errores de lectura o irregularidades. 
•	  Robust Z → valores fuera del patrón histórico de ese medidor (distancia ≥ 4 MAD de la mediana móvil 12 m).
Posibles causas: medidor alterado, consumos atípicos, instalaciones nuevas o manipulaciones.

<img width="567" height="248" alt="image" src="https://github.com/user-attachments/assets/06aee392-dbea-4545-9105-ec65092cd09b" />

<img width="567" height="423" alt="image" src="https://github.com/user-attachments/assets/88fe5f91-b917-4df1-850b-b9bf96b915f6" />

Visualización principal

<img width="563" height="451" alt="image" src="https://github.com/user-attachments/assets/c59566ba-cb32-4c36-ac59-8c9aed1420d6" />

•	Línea azul: consumo mensual total real (2022–2025).
•	Línea naranja: predicción para 2025–2026.
•	El modelo proyecta picos de hasta 3.96 millones kWh hacia marzo de 2026, superando levemente los máximos previos de 2022.


Conclusiones
El análisis integral de consumo eléctrico y detección de anomalías realizado para la Cooperativa de Provisión de Obras y Servicios Públicos Limitada de Armstrong, basado en los registros históricos del período 2022–2025 y las proyecciones hasta 2026, permitió obtener una visión clara del comportamiento energético de la red y de las posibles irregularidades de medición.
El estudio confirmó que el consumo total mensual de la cooperativa presenta una estacionalidad marcada, con picos de demanda en verano e invierno, alcanzando máximos históricos cercanos a los 3,6 millones de kWh y mínimos en los meses templados.
El modelo de pronóstico Holt-Winters proyecta una tendencia de crecimiento moderada (≈4 % anual) para 2025–2026, con un promedio estimado de 3,3 millones de kWh/mes, manteniendo la misma estructura estacional.
En materia de control y supervisión, el proceso de detección automática de anomalías identificó un total de 4 986 eventos atípicos durante 2025:
•	3 291 casos (66 %) corresponden a cambios abruptos en el consumo (caídas o incrementos bruscos intermensuales).
•	1 695 casos (34 %) fueron clasificados como anomalías robustas (Robust Z), es decir, desviaciones significativas respecto a la mediana móvil de 12 meses.
Los resultados obtenidos constituyen una base sólida para la planificación energética, la reducción de pérdidas no técnicas y la optimización operativa.











