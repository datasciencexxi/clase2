#!/usr/bin/env python3
"""Validación determinista de gastos contra presupuesto.

Lee un archivo de gastos y uno de presupuesto (CSV o Excel), aplica las reglas
definidas en reglas/reglas_validacion.yaml usando reglas/catalogo_categorias.yaml
y emite un JSON con el resumen, la ejecución presupuestaria y los hallazgos.

Uso:
    python3 validar.py --gastos G.csv --presupuesto P.csv \
        [--reglas reglas/reglas_validacion.yaml] \
        [--catalogo reglas/catalogo_categorias.yaml] \
        [--fecha-corte 2026-11-11] [--salida-dir reportes]

Códigos de salida:
    0  validación ejecutada (haya o no hallazgos)
    2  error de entrada (archivo inexistente, columnas faltantes, etc.)
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import yaml

COLUMNAS_GASTOS = [
    "id_gasto", "fecha", "proveedor", "rut_proveedor", "nro_factura", "categoria",
    "centro_costo", "descripcion", "monto", "moneda", "aprobado_por",
]
COLUMNAS_PRESUPUESTO = ["periodo", "categoria", "centro_costo", "monto_presupuestado", "moneda"]
LINEA = ["periodo", "categoria", "centro_costo"]


class ErrorEntrada(Exception):
    pass


# --------------------------------------------------------------------------- carga
def leer_tabla(ruta: str, columnas: list[str], nombre: str) -> pd.DataFrame:
    p = Path(ruta)
    if not p.exists():
        raise ErrorEntrada(f"No existe el archivo de {nombre}: {ruta}")
    if p.suffix.lower() in (".xlsx", ".xlsm", ".xls"):
        df = pd.read_excel(p, dtype=str)
    else:
        df = pd.read_csv(p, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]
    faltantes = [c for c in columnas if c not in df.columns]
    if faltantes:
        raise ErrorEntrada(f"Faltan columnas en {nombre} ({ruta}): {', '.join(faltantes)}")
    df = df[columnas].fillna("")
    for c in columnas:
        df[c] = df[c].astype(str).str.strip()
    return df


def cargar_yaml(ruta: str) -> dict:
    with open(ruta, encoding="utf-8") as f:
        return yaml.safe_load(f)


def a_numero(valor: str) -> float | None:
    try:
        return float(str(valor).replace(" ", ""))
    except ValueError:
        return None


# ----------------------------------------------------------------------- validador
class Validador:
    def __init__(self, gastos, presupuesto, reglas, catalogo, fecha_corte: date):
        self.g = gastos.copy()
        self.p = presupuesto.copy()
        self.reglas = {r["id"]: r for r in reglas["reglas"] if r.get("activa", True)}
        self.cat = catalogo
        self.fecha_corte = fecha_corte
        self.hallazgos: list[dict] = []
        self._preparar()

    def _preparar(self):
        fmt = self.reglas.get("R01", {}).get("parametros", {}).get("formato_fecha", "%Y-%m-%d")
        self.g["_fecha"] = pd.to_datetime(self.g["fecha"], format=fmt, errors="coerce")
        self.g["_monto"] = self.g["monto"].map(a_numero)
        self.g["periodo"] = self.g["_fecha"].dt.strftime("%Y-%m").fillna("")
        self.p["_monto"] = self.p["monto_presupuestado"].map(a_numero)

    def agregar(self, regla_id, id_gasto, detalle, severidad=None, linea=None):
        r = self.reglas[regla_id]
        self.hallazgos.append({
            "regla": regla_id,
            "nombre": r["nombre"],
            "severidad": severidad or r["severidad"],
            "id_gasto": id_gasto,
            "linea_presupuesto": linea,
            "detalle": detalle,
        })

    # R01
    def r01(self):
        campos = self.reglas["R01"]["parametros"]["campos_obligatorios"]
        for _, f in self.g.iterrows():
            vacios = [c for c in campos if f[c] == ""]
            if vacios:
                self.agregar("R01", f["id_gasto"], f"Campos vacíos: {', '.join(vacios)}")
            if f["fecha"] and pd.isna(f["_fecha"]):
                self.agregar("R01", f["id_gasto"], f"Fecha inválida: '{f['fecha']}'")
            if f["monto"] and (f["_monto"] is None or f["_monto"] <= 0):
                self.agregar("R01", f["id_gasto"], f"Monto no numérico o no positivo: '{f['monto']}'")
        dup_ids = self.g[self.g["id_gasto"].duplicated(keep=False) & (self.g["id_gasto"] != "")]
        for i in dup_ids["id_gasto"].unique():
            self.agregar("R01", i, "id_gasto repetido en el archivo")

    # R02
    def r02(self):
        cats, ccs = self.cat["categorias"], self.cat["centros_costo"]
        for _, f in self.g.iterrows():
            if f["categoria"] and f["categoria"] not in cats:
                self.agregar("R02", f["id_gasto"], f"Categoría '{f['categoria']}' no existe en el catálogo")
            if f["centro_costo"] and f["centro_costo"] not in ccs:
                self.agregar("R02", f["id_gasto"], f"Centro de costo '{f['centro_costo']}' no existe en el catálogo")

    def _gastos_computables(self) -> pd.DataFrame:
        """Gastos con monto válido, en moneda del presupuesto, para medir ejecución."""
        mon = self.p.set_index(LINEA)["moneda"].to_dict()
        g = self.g[self.g["_monto"].notna() & (self.g["_monto"] > 0) & (self.g["periodo"] != "")]
        moneda_linea = g.apply(lambda f: mon.get((f["periodo"], f["categoria"], f["centro_costo"])), axis=1)
        return g[(moneda_linea.isna()) | (g["moneda"] == moneda_linea)]

    def ejecucion(self) -> list[dict]:
        g = self._gastos_computables()
        ejec = g.groupby(LINEA)["_monto"].agg(["sum", "count"]).reset_index()
        ejec.columns = LINEA + ["ejecutado", "n_gastos"]
        tabla = self.p[LINEA + ["_monto", "moneda"]].rename(columns={"_monto": "presupuestado"})
        tabla = tabla.merge(ejec, on=LINEA, how="outer")
        tabla["ejecutado"] = tabla["ejecutado"].fillna(0)
        tabla["n_gastos"] = tabla["n_gastos"].fillna(0).astype(int)
        tabla["pct_ejecucion"] = (tabla["ejecutado"] / tabla["presupuestado"] * 100).round(1)
        tabla["saldo"] = tabla["presupuestado"] - tabla["ejecutado"]
        tabla = tabla.sort_values(LINEA)
        return json.loads(tabla.to_json(orient="records", force_ascii=False))

    # R03
    def r03(self):
        par = self.reglas["R03"]["parametros"]
        cats = self.cat["categorias"]
        for fila in self.ejecucion():
            linea = f"{fila['periodo']}/{fila['categoria']}/{fila['centro_costo']}"
            if fila["presupuestado"] is None:
                # Periodos sin presupuesto los reporta R07; categorías inválidas, R02.
                if fila["categoria"] in cats and fila["periodo"] in set(self.p["periodo"]):
                    self.agregar("R03", None, f"Gasto de {fila['ejecutado']:,.0f} sin presupuesto asignado", linea=linea)
                continue
            pct = fila["pct_ejecucion"]
            if pct > par["umbral_error_pct"]:
                self.agregar("R03", None,
                             f"Ejecución {pct}%: {fila['ejecutado']:,.0f} de {fila['presupuestado']:,.0f} "
                             f"(exceso {-fila['saldo']:,.0f})", "error", linea)
            elif pct >= par["umbral_advertencia_pct"]:
                self.agregar("R03", None,
                             f"Ejecución {pct}%: {fila['ejecutado']:,.0f} de {fila['presupuestado']:,.0f}",
                             "advertencia", linea)

    # R04
    def r04(self):
        ya = set()
        for clave in self.reglas["R04"]["parametros"]["claves"]:
            sub = self.g[(self.g[clave] != "").all(axis=1)]
            dups = sub[sub.duplicated(subset=clave, keep=False)]
            for _, grupo in dups.groupby(clave):
                ids = tuple(grupo["id_gasto"])
                if ids in ya:
                    continue
                ya.add(ids)
                valores = ", ".join(f"{c}={grupo.iloc[0][c]}" for c in clave)
                for i in ids[1:]:
                    self.agregar("R04", i, f"Posible duplicado de {ids[0]} ({valores})")

    # R05
    def r05(self):
        roles, aprob = self.cat["roles"], self.cat["aprobadores"]
        tramos = self.cat["tramos_aprobacion"]
        for _, f in self.g.iterrows():
            if f["_monto"] is None or f["_monto"] <= 0:
                continue
            requerido = next(t["rol_minimo"] for t in tramos if t["hasta"] is None or f["_monto"] <= t["hasta"])
            if not f["aprobado_por"]:
                self.agregar("R05", f["id_gasto"], f"Sin aprobación (requiere rol '{requerido}')")
                continue
            rol = aprob.get(f["aprobado_por"])
            if rol is None:
                self.agregar("R05", f["id_gasto"], f"'{f['aprobado_por']}' no es aprobador habilitado")
            elif roles[rol] < roles[requerido]:
                self.agregar("R05", f["id_gasto"],
                             f"Monto {f['_monto']:,.0f} requiere rol '{requerido}'; "
                             f"aprobado por {f['aprobado_por']} ({rol})")

    # R06
    def r06(self):
        par = self.reglas["R06"]["parametros"]
        g = self.g[self.g["_monto"].notna() & (self.g["_monto"] > 0)]
        for cat, grupo in g.groupby("categoria"):
            if len(grupo) < par["minimo_registros"]:
                continue
            mediana = grupo["_monto"].median()
            for _, f in grupo[grupo["_monto"] > par["factor_mediana"] * mediana].iterrows():
                self.agregar("R06", f["id_gasto"],
                             f"Monto {f['_monto']:,.0f} es {f['_monto'] / mediana:.1f}x la mediana de {cat} "
                             f"({mediana:,.0f})")

    # R07
    def r07(self):
        periodos = set(self.p["periodo"])
        for _, f in self.g[self.g["_fecha"].notna()].iterrows():
            if f["_fecha"].date() > self.fecha_corte:
                self.agregar("R07", f["id_gasto"], f"Fecha futura {f['fecha']} (corte {self.fecha_corte})")
            elif f["periodo"] not in periodos:
                self.agregar("R07", f["id_gasto"],
                             f"Periodo {f['periodo']} sin presupuesto (periodos válidos: {', '.join(sorted(periodos))})")

    # R08
    def r08(self):
        mon = self.p.set_index(LINEA)["moneda"].to_dict()
        base = self.cat.get("moneda_base")
        for _, f in self.g.iterrows():
            esperada = mon.get((f["periodo"], f["categoria"], f["centro_costo"]), base)
            if f["moneda"] and esperada and f["moneda"] != esperada:
                self.agregar("R08", f["id_gasto"], f"Moneda {f['moneda']} distinta a la del presupuesto ({esperada})")

    def ejecutar(self) -> dict:
        for rid in sorted(self.reglas):
            getattr(self, rid.lower())()
        orden = {"error": 0, "advertencia": 1}
        self.hallazgos.sort(key=lambda h: (orden.get(h["severidad"], 9), h["regla"], h["id_gasto"] or ""))
        ids_err = {h["id_gasto"] for h in self.hallazgos if h["severidad"] == "error" and h["id_gasto"]}
        n_err = sum(h["severidad"] == "error" for h in self.hallazgos)
        n_adv = sum(h["severidad"] == "advertencia" for h in self.hallazgos)
        return {
            "resumen": {
                "fecha_corte": str(self.fecha_corte),
                "total_gastos": len(self.g),
                "gastos_con_error": len(ids_err),
                "monto_total_computable": float(self._gastos_computables()["_monto"].sum()),
                "errores": n_err,
                "advertencias": n_adv,
                "reglas_aplicadas": sorted(self.reglas),
                "estado": "RECHAZADO" if n_err else ("OBSERVADO" if n_adv else "APROBADO"),
            },
            "ejecucion_presupuesto": self.ejecucion(),
            "hallazgos": self.hallazgos,
        }


# ---------------------------------------------------------------------------- main
def main() -> int:
    raiz = Path(__file__).resolve().parents[4]
    ap = argparse.ArgumentParser(description="Valida gastos contra presupuesto.")
    ap.add_argument("--gastos", required=True)
    ap.add_argument("--presupuesto", required=True)
    ap.add_argument("--reglas", default=str(raiz / "reglas/reglas_validacion.yaml"))
    ap.add_argument("--catalogo", default=str(raiz / "reglas/catalogo_categorias.yaml"))
    ap.add_argument("--fecha-corte", default=str(date.today()), help="YYYY-MM-DD; fechas posteriores son futuras")
    ap.add_argument("--salida-dir", help="Si se indica, guarda hallazgos_<ts>.csv y resultado_<ts>.json")
    a = ap.parse_args()

    try:
        gastos = leer_tabla(a.gastos, COLUMNAS_GASTOS, "gastos")
        presupuesto = leer_tabla(a.presupuesto, COLUMNAS_PRESUPUESTO, "presupuesto")
        corte = datetime.strptime(a.fecha_corte, "%Y-%m-%d").date()
        resultado = Validador(gastos, presupuesto, cargar_yaml(a.reglas), cargar_yaml(a.catalogo), corte).ejecutar()
    except ErrorEntrada as e:
        print(json.dumps({"error": str(e)}, ensure_ascii=False), file=sys.stderr)
        return 2

    if a.salida_dir:
        out = Path(a.salida_dir)
        out.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        pd.DataFrame(resultado["hallazgos"]).to_csv(out / f"hallazgos_{ts}.csv", index=False, encoding="utf-8-sig")
        (out / f"resultado_{ts}.json").write_text(json.dumps(resultado, ensure_ascii=False, indent=2), encoding="utf-8")
        resultado["archivos_generados"] = [str(out / f"hallazgos_{ts}.csv"), str(out / f"resultado_{ts}.json")]

    print(json.dumps(resultado, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
