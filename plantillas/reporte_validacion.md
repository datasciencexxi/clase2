# Reporte de validación de costos

**Fecha de corte:** {{fecha_corte}}
**Archivo de gastos:** `{{archivo_gastos}}`
**Archivo de presupuesto:** `{{archivo_presupuesto}}`
**Estado del lote:** {{estado}}  <!-- APROBADO | OBSERVADO | RECHAZADO -->

## 1. Resumen ejecutivo
<!-- 3 a 5 líneas: qué se revisó, resultado general, los 2-3 problemas más relevantes y su impacto en $. -->

| Indicador | Valor |
|---|---|
| Gastos revisados | {{total_gastos}} |
| Gastos con error | {{gastos_con_error}} |
| Errores | {{errores}} |
| Advertencias | {{advertencias}} |
| Monto total computable | {{monto_total_computable}} |

## 2. Ejecución vs presupuesto
| Periodo | Categoría | Centro | Presupuestado | Ejecutado | % | Saldo | Estado |
|---|---|---|---:|---:|---:|---:|---|
<!-- Una fila por línea de presupuesto. Estado: OK (<90%), ⚠️ (90-100%), ❌ (>100% o sin presupuesto). -->

## 3. Hallazgos
### 3.1 Errores (bloquean la aprobación)
| Regla | Gasto / Línea | Detalle | Acción sugerida |
|---|---|---|---|

### 3.2 Advertencias (requieren revisión)
| Regla | Gasto / Línea | Detalle | Acción sugerida |
|---|---|---|---|

## 4. Recomendaciones
<!-- Acciones concretas priorizadas: a quién escalar, qué corregir en el archivo, qué reasignar en el presupuesto. -->

## 5. Supuestos y alcance
- Reglas aplicadas: {{reglas_aplicadas}} (ver `reglas/reglas_validacion.yaml`).
- Los gastos en moneda distinta al presupuesto no se suman a la ejecución.
- Los posibles duplicados sí se suman a la ejecución hasta que se confirme su anulación.
