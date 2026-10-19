# Fab Discovery Loop

[Français](README.md) · [English](README.en.md)

**¿Qué ensayo de fabricación merece realizarse después?**

Un laboratorio local elige el experimento que mejor distingue hipótesis explícitas del proceso por unidad de coste. Tras una observación, actualiza sus probabilidades y calcula el siguiente ensayo. Muestra límites de máquina, capacidades ausentes, ensayos pendientes, presupuesto y riesgo condicional.

![Demostración sintética: elegir el siguiente experimento](docs/preview-fr.png)

## Probar

Python 3.11 o posterior, solo biblioteca estándar. Sin clave ni hardware conectado.

```sh
python3 -m fab_discovery serve --lang es
```

Abrir `http://127.0.0.1:8765/?lang=es`. Elegir la hipótesis verdadera del **simulador sintético**, simular un ensayo, observar la evolución y exportar hipótesis y observaciones. El panel permite registrar una observación proporcionada; introducirla no demuestra su procedencia instrumental.

```sh
python3 -m fab_discovery demo --lang es
python3 -m fab_discovery analyze fab_discovery/examples/process-window.json
python3 -m fab_discovery observe caso.json p1-d5 underfused medida-001 > siguiente.json
python3 -m fab_discovery benchmark > benchmark.json
```

`pip install .` ofrece también `fab-discovery`. Interfaz y mensajes CLI disponibles en FR/EN/ES.

## Bucle de aprendizaje comprobable

1. Describir hipótesis finitas: umbrales de formación y daño, anchuras de transición y peso inicial.
2. Proporcionar ensayos candidatos: potencia, duración, coste y capacidades necesarias.
3. Calcular exactamente la reducción **esperada** de entropía con resultados `underfused`, `good` y `damaged`.
4. Excluir ensayos fuera de presupuesto, límites de máquina o riesgo condicional, sin capacidades o pendientes; ordenar por información esperada/coste.
5. Registrar el resultado y actualizar los pesos bayesianos en espacio logarítmico.

Repetir el mismo `evidence_id` con el mismo resultado no consume presupuesto adicional ni duplica la observación. Un resultado diferente con ese identificador se rechaza. Sin identificador, cada observación se considera una repetición independiente. Puede registrarse un ensayo completado aunque las reglas lo hubieran excluido: también se conservan los fallos.

La recomendación no ejecuta ni reserva equipos. El coste se descuenta al registrar una observación completada; comandos, reservas y compromisos financieros se gestionan por separado. La huella del caso vincula la recomendación a sus hipótesis y medidas.

## Comparación reproducible y compromisos

`benchmark` compara tres estrategias miopes para las tres hipótesis verdaderas posibles, 20 semillas y hasta ocho ensayos por campaña. Presupuesto inicial: 24 unidades. Los sorteos se comparten por semilla, ensayo y número de repetición.

| Estrategia                 | Coste medio | Entropía final media, bits | Peso final medio de la hipótesis verdadera | Ensayos dañados medios |
| -------------------------- | ----------: | -------------------------: | -----------------------------------------: | ---------------------: |
| Información/coste          |       23,14 |                      0,095 |                                      0,973 |                  0,567 |
| Rendimiento previsto/coste |       23,37 |                      0,203 |                                      0,930 |                  0,417 |
| Más barato                 |       16,00 |                      1,414 |                                      0,399 |                  0,000 |

Aprender más produce más daños simulados en este caso; la estrategia más barata gasta menos. El peso de la hipótesis verdadera **no es precisión industrial**. Los resultados dependen de estos modelos de juguete, parámetros y semillas. No se ha medido ventaja sobre BayBE ni sobre un proceso real.

## Herramientas existentes y límites

[BayBE](https://github.com/emdgroup/baybe) ya ofrece optimización bayesiana y diseño experimental generales. Este repositorio no reinventa sus métodos: ofrece un bucle pequeño y autónomo centrado en distinguir hipótesis, exclusiones explícitas y una demostración sin dependencias.

[Atomic Machines](https://www.atomicmachines.com/matter-compiler) describe un ciclo de diseño, fabricación y medida. Ese ciclo inspira el proyecto; **no integra API, hardware, licencia ni afiliación con Atomic Machines**. Frente a [MeasurePlan](https://github.com/gbesse/measureplan), que asigna inspecciones, este bucle cambia el siguiente ensayo según lo aprendido.

El modelo usa dos umbrales de dosis y tres resultados categóricos. Supone observaciones condicionalmente independientes. Una hipótesis ausente nunca se descubre; un posterior muy seguro puede ser falso. El riesgo previsto no certifica seguridad ni valida física. No incluye optimización de lotes paralelos, modelo continuo ni conector industrial. Los datos simulados son sintéticos y se identifican en el registro.

## Validación

```sh
python3 -m unittest discover -s tests -v
npm ci
npx playwright install chromium
npm run test:browser
npm run format:check
```

Catorce pruebas contrastan información con una formulación KL independiente, exclusiones, repeticiones, presupuesto y estabilidad numérica. El navegador verifica FR/EN/ES, simulación, observación introducida, riesgo, exportación y móvil. CI verifica Python 3.11/3.12 y la instalación de la rueda fuera de las fuentes. Licencia MIT; alfa de investigación.
