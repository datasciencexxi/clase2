---
description: Valida un archivo de gastos (CSV/Excel) contra el presupuesto y genera un reporte
argument-hint: <archivo_gastos> [archivo_presupuesto]
---

Usa el subagente **validador-costos** para validar los gastos contra el presupuesto.

- Archivo de gastos: `$1`
- Archivo de presupuesto: `$2` (si está vacío, el agente debe buscarlo junto al archivo de gastos)

Al terminar, muestra el estado del lote, el conteo de errores/advertencias, los hallazgos principales y la ruta del reporte generado en `reportes/`.
