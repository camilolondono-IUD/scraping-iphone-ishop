"""Verifica que la aplicación desplegada en la nube responde y es la versión esperada.

Es la "prueba de humo" (smoke test) que el pipeline ejecuta después de desplegar. Comprueba:
  1. que index.html responde con código 200 y contiene el título de la aplicación;
  2. que version.json corresponde al commit que se acaba de desplegar;
  3. que datos.json tiene las variantes esperadas.

GitHub Pages puede tardar unos segundos en servir la versión nueva (caché de la CDN), por eso
reintenta varias veces antes de fallar. Si falla, termina con código 1 y el job queda en rojo.

Uso:
  python scripts/verificar_despliegue.py --url https://usuario.github.io/repo/ \\
      --commit abc1234 --variantes 32
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.request

TITULO = "Precios del iPhone 18 Pro y 18 Pro Max"


def descargar(url, timeout=20):
    """Devuelve (status, texto). Agrega un parámetro para evitar respuestas en caché."""
    separador = "&" if "?" in url else "?"
    peticion = urllib.request.Request(f"{url}{separador}nocache={time.time_ns()}",
                                      headers={"User-Agent": "verificar-despliegue"})
    with urllib.request.urlopen(peticion, timeout=timeout) as resp:
        return resp.status, resp.read().decode("utf-8")


def verificar(url_base, commit=None, variantes=None, descargar=descargar):
    """Ejecuta las comprobaciones una vez. Devuelve la lista de errores (vacía si todo está bien)."""
    url_base = url_base.rstrip("/") + "/"
    errores = []

    status, html = descargar(url_base + "index.html")
    if status != 200:
        errores.append(f"index.html respondió {status}")
    elif TITULO not in html:
        errores.append("index.html no contiene el título de la aplicación")

    status, texto = descargar(url_base + "version.json")
    version = json.loads(texto) if status == 200 else {}
    if status != 200:
        errores.append(f"version.json respondió {status}")
    elif commit and version.get("commit") != commit[:7]:
        errores.append(f"commit desplegado {version.get('commit')} != esperado {commit[:7]}")

    status, texto = descargar(url_base + "datos.json")
    if status != 200:
        errores.append(f"datos.json respondió {status}")
    elif variantes is not None and len(json.loads(texto)) != variantes:
        errores.append(f"datos.json tiene {len(json.loads(texto))} variantes, se esperaban {variantes}")

    if not errores:
        print(f"OK: entorno={version.get('entorno')} versión={version.get('version')} "
              f"commit={version.get('commit')}")
    return errores


def main(argv=None):
    parser = argparse.ArgumentParser(description="Prueba de humo de la aplicación desplegada")
    parser.add_argument("--url", required=True, help="URL base del sitio publicado")
    parser.add_argument("--commit", help="SHA del commit que debería estar desplegado")
    parser.add_argument("--variantes", type=int, help="Número de variantes esperadas en datos.json")
    parser.add_argument("--intentos", type=int, default=10)
    parser.add_argument("--espera", type=float, default=15, help="Segundos entre intentos")
    args = parser.parse_args(argv)

    for intento in range(1, args.intentos + 1):
        try:
            errores = verificar(args.url, args.commit, args.variantes)
        except Exception as e:  # red caída, 404, JSON inválido...
            errores = [f"{type(e).__name__}: {e}"]
        if not errores:
            return 0
        print(f"Intento {intento}/{args.intentos} falló: {'; '.join(errores)}")
        if intento < args.intentos:
            time.sleep(args.espera)
    return 1


if __name__ == "__main__":
    sys.exit(main())
