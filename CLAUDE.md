# clase2 — Agente de validación de costos

Proyecto de configuración de Claude Code para **validar gastos contra presupuesto** a partir de archivos CSV/Excel.

## Estructura
- `.claude/agents/validador-costos.md` — subagente que ejecuta la validación y redacta el reporte.
- `.claude/commands/validar-costos.md` — comando `/validar-costos <gastos> [presupuesto]`.
- `.claude/skills/validacion-costos/` — procedimiento (`SKILL.md`) y motor de reglas (`scripts/validar.py`).
- `reglas/` — reglas de validación (R01–R08) y catálogo de categorías, centros de costo y aprobadores.
- `plantillas/` — columnas esperadas de los archivos de entrada y plantilla del reporte.
- `datos/ejemplo/` — datos de prueba con un error sembrado por cada regla.
- `reportes/` — salida de las validaciones (no versionar reportes reales con datos sensibles).

## Convenciones
- Idioma: español. Montos en pesos chilenos (CLP) salvo que el presupuesto indique otra moneda.
- Fechas `YYYY-MM-DD`; periodos de presupuesto `YYYY-MM`.
- Los cálculos los hace siempre `validar.py`; el agente interpreta y explica.
- Nunca modificar archivos en `datos/` ni los archivos de entrada del usuario.
- Cambios de umbrales o catálogos se hacen en `reglas/*.yaml`, no en el código.

## Comando de prueba
```bash
python3 .claude/skills/validacion-costos/scripts/validar.py \
  --gastos datos/ejemplo/gastos_ejemplo.csv \
  --presupuesto datos/ejemplo/presupuesto_ejemplo.csv --fecha-corte 2026-11-11
```
Resultado esperado: estado `RECHAZADO`, 11 errores y 2 advertencias, con al menos un hallazgo de cada regla R01–R08.

Requisitos: Python 3.10+, `pandas`, `pyyaml` y `openpyxl` (para Excel).
