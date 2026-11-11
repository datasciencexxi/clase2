# clase2 — Agente de validación de costos

Agente de [Claude Code](https://claude.com/claude-code) que revisa un archivo de **gastos** (CSV o Excel) contra el **presupuesto** y genera un reporte con errores, advertencias y acciones sugeridas.

## Uso
Dentro de Claude Code, en la raíz del repo:

```
/validar-costos datos/ejemplo/gastos_ejemplo.csv datos/ejemplo/presupuesto_ejemplo.csv
```

O directamente: *"valida los gastos de octubre en datos/gastos_oct.xlsx"* — Claude delegará en el subagente `validador-costos`.

## Formato de entrada
**Gastos** (`plantillas/gastos_plantilla.csv`):
`id_gasto, fecha, proveedor, rut_proveedor, nro_factura, categoria, centro_costo, descripcion, monto, moneda, aprobado_por`

**Presupuesto** (`plantillas/presupuesto_plantilla.csv`):
`periodo, categoria, centro_costo, monto_presupuestado, moneda`

## Reglas
| ID | Regla | Severidad |
|---|---|---|
| R01 | Campos obligatorios, fecha válida, monto > 0, id único | error |
| R02 | Categoría y centro de costo existen en el catálogo | error |
| R03 | Ejecución ≤ 100 % del presupuesto (advertencia desde 90 %) | error / advertencia |
| R04 | Duplicados (proveedor + factura, o proveedor + fecha + monto) | error |
| R05 | Aprobado por un rol suficiente según tramo de monto | error |
| R06 | Monto atípico (> 4× la mediana de la categoría) | advertencia |
| R07 | Fecha en periodo con presupuesto y no futura | error |
| R08 | Moneda igual a la del presupuesto | error |

Umbrales, categorías, aprobadores y tramos se configuran en `reglas/`.

## Salida
- Resumen en el chat con el estado del lote: **APROBADO**, **OBSERVADO** o **RECHAZADO**.
- `reportes/validacion_<fecha>.md` — reporte completo.
- `reportes/hallazgos_<ts>.csv` y `reportes/resultado_<ts>.json` — detalle para Excel o integración.

## Requisitos
```bash
pip install pandas pyyaml openpyxl
```
