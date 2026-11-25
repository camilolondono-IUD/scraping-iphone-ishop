"""Genera la aplicación web estática con los resultados del scraping.

Produce en la carpeta de salida:
  index.html    página con indicadores, gráfico, tablas y filtros interactivos
  precios.png   gráfico de precio por modelo y capacidad
  datos.json    las variantes en formato JSON (lo consume la tabla y cualquier cliente)
  version.json  versión, entorno y commit desplegados (lo usa la verificación del pipeline)

La configuración llega por variables de entorno, que en GitHub Actions se definen en
Settings > Secrets and variables > Actions > Variables:
  APP_ENV      nombre del entorno (por defecto "local")
  APP_VERSION  versión publicada (por defecto "dev")
  GITHUB_SHA   commit que generó el sitio (lo define GitHub Actions automáticamente)

Uso:  python -m src.build_site --datos data/iphone18pro_ishop.csv --salida site
"""

from __future__ import annotations

import argparse
import html
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from src import analisis  # noqa: E402

REPO_URL = "https://github.com/camilolondono-IUD/scraping-iphone-ishop"


def configuracion():
    """Lee la configuración de la app desde variables de entorno."""
    return {
        "entorno": os.environ.get("APP_ENV") or "local",
        "version": os.environ.get("APP_VERSION") or "dev",
        "commit": (os.environ.get("GITHUB_SHA") or "local")[:7],
    }


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


def opciones_html(valores):
    return "".join(f'<option value="{html.escape(str(v))}">{html.escape(str(v))}</option>' for v in valores)


def filtros_html(df):
    """Controles para filtrar la tabla de variantes en el navegador."""
    caps = analisis.capacidades_ordenadas(df)
    campos = [
        ("modelo", "Modelo", sorted(df["Modelo"].unique())),
        ("capacidad", "Capacidad", caps),
        ("color", "Color", sorted(df["Color"].unique())),
        ("disponibilidad", "Disponibilidad", sorted(df["Disponibilidad"].unique())),
    ]
    selects = "".join(
        f'<label>{titulo}<select id="f-{clave}" data-campo="{clave}"><option value="">Todos</option>'
        f"{opciones_html(valores)}</select></label>"
        for clave, titulo, valores in campos
    )
    return (f'<div class="filtros">{selects}'
            '<label>Buscar SKU<input id="f-texto" type="search" placeholder="Ej. MJRT4LZ"></label>'
            '<button id="f-limpiar" type="button">Limpiar</button></div>')


def tabla_variantes_html(df):
    """Tabla de todas las variantes; cada fila lleva sus atributos para poder filtrarla."""
    columnas = ["Referencia (SKU)", "Modelo", "Capacidad", "Color", "Precio", "Disponibilidad"]
    cab = "".join(f"<th>{html.escape(c)}</th>" for c in columnas)
    filas = []
    for _, r in df.iterrows():
        attrs = " ".join(
            f'data-{k}="{html.escape(str(r[c]))}"'
            for k, c in [("modelo", "Modelo"), ("capacidad", "Capacidad"), ("color", "Color"),
                         ("disponibilidad", "Disponibilidad"), ("sku", "Referencia (SKU)")]
        )
        celdas = "".join(f"<td>{html.escape(str(r[c]))}</td>" for c in columnas)
        filas.append(f"<tr {attrs}>{celdas}</tr>")
    return (f'<table id="tabla-variantes"><thead><tr>{cab}</tr></thead>'
            f'<tbody>{"".join(filas)}</tbody></table>')


# Filtro en el navegador (JavaScript sin dependencias): oculta las filas que no cumplen.
SCRIPT_FILTROS = """
<script>
(function () {
  var filas = Array.prototype.slice.call(document.querySelectorAll('#tabla-variantes tbody tr'));
  var selects = Array.prototype.slice.call(document.querySelectorAll('.filtros select'));
  var texto = document.getElementById('f-texto');
  var contador = document.getElementById('contador');
  function aplicar() {
    var buscado = texto.value.trim().toUpperCase();
    var visibles = 0;
    filas.forEach(function (fila) {
      var ok = selects.every(function (s) { return !s.value || fila.dataset[s.dataset.campo] === s.value; });
      if (buscado && fila.dataset.sku.toUpperCase().indexOf(buscado) === -1) { ok = false; }
      fila.hidden = !ok;
      if (ok) { visibles++; }
    });
    contador.textContent = 'Mostrando ' + visibles + ' de ' + filas.length + ' variantes';
  }
  selects.forEach(function (s) { s.addEventListener('change', aplicar); });
  texto.addEventListener('input', aplicar);
  document.getElementById('f-limpiar').addEventListener('click', function () {
    selects.forEach(function (s) { s.value = ''; });
    texto.value = '';
    aplicar();
  });
  aplicar();
})();
</script>
"""


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

    conf = configuracion()
    fecha = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    pagina = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="app-version" content="{html.escape(conf["version"])}">
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
  .filtros {{ display: flex; flex-wrap: wrap; gap: 10px; align-items: end; margin: 12px 0; }}
  .filtros label {{ display: flex; flex-direction: column; font-size: .8rem; color: #6e6e73; }}
  .filtros select, .filtros input, .filtros button {{ font: inherit; padding: 4px 6px; }}
  .entorno {{ display: inline-block; background: #2f6ea8; color: #fff; border-radius: 6px;
              padding: 0 8px; font-size: .8rem; }}
</style>
</head>
<body>
<h1>Precios del iPhone 18 Pro y 18 Pro Max en iShop Colombia</h1>
<p><span class="entorno">{html.escape(conf["entorno"])} · v{html.escape(conf["version"])}</span></p>
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
{filtros_html(df)}
<p id="contador"></p>
<div class="scroll">{tabla_variantes_html(variantes)}</div>
<p><a href="datos.json">Descargar los datos en JSON</a></p>

<footer>
  Fuente: co.tiendasishop.com · Generado automáticamente por GitHub Actions el {fecha}
  (commit {html.escape(conf["commit"])}) · Versión {html.escape(conf["version"])} ·
  Entorno {html.escape(conf["entorno"])} · <a href="{REPO_URL}">Repositorio</a>
</footer>
{SCRIPT_FILTROS}
</body>
</html>
"""
    (salida / "index.html").write_text(pagina, encoding="utf-8")

    # Datos y metadatos en JSON: los usan la tabla, otros clientes y la verificación del pipeline
    registros = df[["Referencia (SKU)", "Modelo", "Capacidad", "Color", "Precio_COP",
                    "Disponibilidad", "URL"]].to_dict(orient="records")
    (salida / "datos.json").write_text(json.dumps(registros, ensure_ascii=False, indent=1),
                                       encoding="utf-8")
    (salida / "version.json").write_text(
        json.dumps({**conf, "generado": fecha, "variantes": res["variantes"]}, ensure_ascii=False),
        encoding="utf-8")
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
