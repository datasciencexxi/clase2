---
name: validacion-costos
description: Procedimiento para validar gastos (CSV/Excel) contra presupuesto aplicando reglas configurables (campos, catálogo, exceso de presupuesto, duplicados, aprobaciones, montos atípicos, periodo y moneda) y generar un reporte. Úsala cuando haya que revisar o auditar un archivo de gastos o facturas frente a un presupuesto.
---

# Validación de costos: gastos vs presupuesto

## Archivos de referencia
| Archivo | Uso |
|---|---|
| `reglas/reglas_validacion.yaml` | Reglas R01–R08, severidad, umbrales y activación |
| `reglas/catalogo_categorias.yaml` | Categorías, centros de costo, aprobadores y tramos de aprobación |
| `plantillas/gastos_plantilla.csv` | Columnas obligatorias del archivo de gastos |
| `plantillas/presupuesto_plantilla.csv` | Columnas obligatorias del presupuesto |
| `plantillas/reporte_validacion.md` | Estructura del reporte final |
| `scripts/validar.py` | Motor de validación determinista (pandas) |

## Pasos
1. **Verificar entradas.** Acepta `.csv`, `.xlsx`, `.xls`. Los nombres de columna se normalizan (minúsculas, espacios → `_`). Si faltan columnas, el script termina con código 2 y lista las faltantes: informa al usuario y no continúes.
2. **Ejecutar el script** desde la raíz del repo:
   ```bash
   python3 .claude/skills/validacion-costos/scripts/validar.py \
     --gastos <gastos> --presupuesto <presupuesto> --salida-dir reportes \
     [--fecha-corte YYYY-MM-DD]
   ```
   Devuelve JSON con `resumen`, `ejecucion_presupuesto` y `hallazgos` (y guarda CSV + JSON en `reportes/`).
3. **Analizar resultados**
   - Prioriza `error` sobre `advertencia`, y dentro de cada grupo por impacto en dinero.
   - Relaciona hallazgos: un R04 (duplicado) o R06 (atípico) puede explicar un R03 (exceso). Indica cuánto bajaría la ejecución si se corrige.
   - Líneas con `presupuestado = null` son gastos sin línea de presupuesto.
4. **Redactar el reporte** en `reportes/validacion_<YYYYMMDD>.md` siguiendo la plantilla. Cada hallazgo con una acción sugerida:
   | Regla | Acción típica |
   |---|---|
   | R01 | Solicitar al área el dato faltante o corregir el formato |
   | R02 | Reclasificar o solicitar alta de la categoría/centro en el catálogo |
   | R03 | Escalar al dueño del presupuesto; reasignar o pedir suplemento |
   | R04 | Confirmar con el proveedor y anular el registro duplicado |
   | R05 | Obtener aprobación del rol requerido antes de pagar |
   | R06 | Pedir respaldo (cotización/contrato) que justifique el monto |
   | R07 | Imputar al periodo correcto o rechazar si es fecha futura |
   | R08 | Convertir a moneda del presupuesto con tipo de cambio oficial |

## Extender
- **Nueva regla:** agrégala en `reglas_validacion.yaml` con un `id` nuevo (p. ej. `R09`) e implementa el método `r09()` en la clase `Validador` de `validar.py`; se ejecuta automáticamente si está `activa: true`.
- **Ajustar umbrales:** modifica `parametros` en el YAML; no hace falta tocar código.
- **Nuevos aprobadores o categorías:** edita `catalogo_categorias.yaml`.
