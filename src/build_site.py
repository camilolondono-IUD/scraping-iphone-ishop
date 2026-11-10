"""Genera un sitio estático (HTML + gráfico) con los resultados del scraping.

Uso:  python -m src.build_site --datos data/iphone18pro_ishop.csv --salida site
"""

from __future__ import annotations

import argparse
import html
import os
from datetime import datetime, timezone
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from src import analisis  # noqa: E402

REPO_URL = "https://github.com/camilolondono-IUD/scraping-iphone-ishop"


def cop(valor):
    return f"${valor:,.0f}".replace(",", ".")


def generar_grafico(df, ruta):
    tabla = analisis.tabla_precios(df) / 1e6
    ax = tabla.plot(kind="bar", figsize=(8, 4.5), rot=0, color=["#9ab8d8", "#2f6ea8"], width=0.75)
    for cont in ax.containers:
        ax.bar_label(cont, labels=[f"{v:.2f}".replace(".", ",") for v in cont.datavalues],
                     padding=2, fontsize=8)
    ax.set_xlabel("Capacidad")
    ax.set_ylabel("Precio (millones de COP)")
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(title=None, frameon=False)
    plt.tight_layout()
    plt.savefig(ruta, dpi=150)
    plt.close()


def tabla_html(df, columnas):
    cab = "".join(f"<th>{html.escape(c)}</th>" for c in columnas)
    filas = "".join(
        "<tr>" + "".join(f"<td>{html.escape(str(r[c]))}</td>" for c in columnas) + "</tr>"
        for _, r in df.iterrows()
    )
    return f"<table><thead><tr>{cab}</tr></thead><tbody>{filas}</tbody></table>"


def generar_sitio(ruta_datos, carpeta_salida):
    salida = Path(carpeta_salida)
    salida.mkdir(parents=True, exist_ok=True)
    df = analisis.cargar_datos(ruta_datos)
    res = analisis.resumen(df)
    generar_grafico(df, salida / "precios.png")

    precios = analisis.tabla_precios(df).reset_index()
    precios_fmt = precios.copy()
    for col in precios.columns[1:]:
        precios_fmt[col] = precios[col].map(cop)
    agot = analisis.agotados(df)
    variantes = df.copy()
    variantes["Precio"] = variantes["Precio_COP"].map(cop)

    sha = os.environ.get("GITHUB_SHA", "local")[:7]
    fecha = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    pagina = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Precios iPhone 18 Pro y 18 Pro Max – iShop Colombia</title>
<style>
  body {{ font-family: system-ui, sans-serif; max-width: 960px; margin: 0 auto; padding: 16px;
         color: #1d1d1f; line-height: 1.5; }}
  h1 {{ font-size: 1.6rem; }} h2 {{ margin-top: 2rem; border-bottom: 1px solid #ddd; }}
  .kpis {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 12px; }}
  .kpi {{ background: #f5f5f7; border-radius: 10px; padding: 12px; }}
  .kpi b {{ display: block; font-size: 1.4rem; }}
  table {{ border-collapse: collapse; width: 100%; font-size: .9rem; }}
  th, td {{ border-bottom: 1px solid #e5e5e5; padding: 6px 8px; text-align: left; }}
  th {{ background: #f5f5f7; }}
  img {{ max-width: 100%; }}
  .scroll {{ overflow-x: auto; }}
  footer {{ margin-top: 2rem; font-size: .8rem; color: #6e6e73; }}
</style>
</head>
<body>
<h1>Precios del iPhone 18 Pro y 18 Pro Max en iShop Colombia</h1>
<p>Resultados del web scraping con BeautifulSoup (Evidencia 1, Programación para Análisis de
Datos, IU Digital). Proyecto con fines educativos.</p>

<div class="kpis">
  <div class="kpi"><b>{res["variantes"]}</b>variantes extraídas</div>
  <div class="kpi"><b>{cop(res["precio_min"])}</b>precio mínimo</div>
  <div class="kpi"><b>{cop(res["precio_max"])}</b>precio máximo</div>
  <div class="kpi"><b>{res["disponibles"]} ({res["pct_disponible"]} %)</b>disponibles</div>
</div>

<h2>Precio por modelo y capacidad</h2>
<img src="precios.png" alt="Gráfico de barras del precio por capacidad del iPhone 18 Pro y Pro Max">
<div class="scroll">{tabla_html(precios_fmt, list(precios_fmt.columns))}</div>
<p>El color no cambia el precio: las cuatro variantes de color cuestan lo mismo en cada
combinación de modelo y capacidad.</p>

<h2>Variantes agotadas ({len(agot)})</h2>
<div class="scroll">{tabla_html(agot, ["Modelo", "Capacidad", "Color", "Referencia (SKU)"])}</div>

<h2>Todas las variantes</h2>
<div class="scroll">{tabla_html(variantes, ["Referencia (SKU)", "Modelo", "Capacidad", "Color",
                                             "Precio", "Disponibilidad"])}</div>

<footer>
  Fuente: co.tiendasishop.com · Generado automáticamente por GitHub Actions el {fecha}
  (commit {html.escape(sha)}) · <a href="{REPO_URL}">Repositorio</a>
</footer>
</body>
</html>
"""
    (salida / "index.html").write_text(pagina, encoding="utf-8")
    return salida / "index.html"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--datos", default="data/iphone18pro_ishop.csv")
    parser.add_argument("--salida", default="site")
    args = parser.parse_args()
    ruta = generar_sitio(args.datos, args.salida)
    print(f"Sitio generado en {ruta}")


if __name__ == "__main__":
    main()
