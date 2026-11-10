"""Limpieza y estadísticas de los datos extraídos (sección 6 a 8 del notebook)."""

from __future__ import annotations

import re

import pandas as pd

COLUMNAS = [
    "Referencia (SKU)", "Nombre/Marca", "Valores", "Caracteristicas", "Modelo",
    "Capacidad", "Color", "Precio_COP", "Disponibilidad", "URL", "Fuente",
]


def orden_capacidad(cap):
    """'256 GB' -> 256, '1 TB' -> 1024. Sirve para ordenar capacidades."""
    m = re.match(r"(\d+)\s*(GB|TB)", str(cap))
    if not m:
        return 0
    return int(m.group(1)) * (1024 if m.group(2) == "TB" else 1)


def construir_dataframe(filas):
    """Arma el DataFrame final: sin duplicados y ordenado por modelo, capacidad y color."""
    df = pd.DataFrame(filas, columns=COLUMNAS)
    df = df.drop_duplicates(subset=["URL"])
    df["orden_cap"] = df["Capacidad"].map(orden_capacidad)
    df = df.sort_values(["Modelo", "orden_cap", "Color"]).drop(columns="orden_cap")
    return df.reset_index(drop=True)


def cargar_datos(ruta):
    df = pd.read_csv(ruta, encoding="utf-8-sig")
    df["Precio_COP"] = pd.to_numeric(df["Precio_COP"], errors="coerce")
    return df


def capacidades_ordenadas(df):
    return sorted(df["Capacidad"].unique(), key=orden_capacidad)


def tabla_precios(df):
    """Precio por capacidad (filas) y modelo (columnas)."""
    return (df.pivot_table(index="Capacidad", columns="Modelo", values="Precio_COP", aggfunc="mean")
              .reindex(capacidades_ordenadas(df)))


def diferencia_modelos(df):
    """Cuánto más cuesta el Pro Max que el Pro con la misma capacidad."""
    t = tabla_precios(df)
    return t["iPhone 18 Pro Max"] - t["iPhone 18 Pro"]


def incremento_capacidad(df):
    """Incremento de precio al pasar a la siguiente capacidad."""
    return tabla_precios(df).diff().dropna(how="all")


def precios_por_color(df):
    """Número de precios distintos por modelo y capacidad (1 = el color no cambia el precio)."""
    return df.groupby(["Modelo", "Capacidad"])["Precio_COP"].nunique()


def agotados(df):
    return df[df["Disponibilidad"] == "Agotado"].reset_index(drop=True)


def resumen(df):
    total = len(df)
    disponibles = int((df["Disponibilidad"] == "Disponible").sum())
    return {
        "variantes": total,
        "precio_min": float(df["Precio_COP"].min()),
        "precio_max": float(df["Precio_COP"].max()),
        "disponibles": disponibles,
        "agotados": int((df["Disponibilidad"] == "Agotado").sum()),
        "pct_disponible": round(disponibles / total * 100, 1) if total else 0.0,
        "completitud_pct": round(float(df[COLUMNAS].notna().mean().mean() * 100), 1),
    }
