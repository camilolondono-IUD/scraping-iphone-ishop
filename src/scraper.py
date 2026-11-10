"""Scraper del iPhone 18 Pro y 18 Pro Max en iShop Colombia.

Reorganiza la lógica del notebook de la Evidencia 1 (requests + BeautifulSoup):
la descarga HTTP está separada del parseo, de modo que las funciones que leen el
HTML son puras y se pueden probar con HTML guardado, sin hacer peticiones al sitio.
"""

from __future__ import annotations

import json
import re
import time

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://co.tiendasishop.com"
URL_COLECCION = BASE_URL + "/collections/iphone-18-pro-y-18-pro-max"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
    "Accept-Language": "es-CO,es;q=0.9",
}

PAUSA_SEGUNDOS = 1.5  # pausa entre peticiones (buenas prácticas)
VARIANTES_ESPERADAS = 32  # 2 modelos x 4 capacidades x 4 colores

# Handles de las variantes: empiezan por iphone-18-pro- y terminan en 4lz-a.
# El lookbehind descarta accesorios como "funda-...-para-el-iphone-18-pro-...4zm-a".
PATRON_HANDLE = re.compile(r"(?<![a-z0-9-])iphone-18-pro-m[a-z0-9]{3}4lz-a")

DISPONIBILIDAD = {
    "InStock": "Disponible",
    "OutOfStock": "Agotado",
    "PreOrder": "Preventa",
    "LimitedAvailability": "Pocas unidades",
}


# --------------------------------------------------------------------------- #
# Red (único lugar que hace peticiones HTTP)
# --------------------------------------------------------------------------- #
def crear_sesion() -> requests.Session:
    sesion = requests.Session()
    sesion.headers.update(HEADERS)
    return sesion


def obtener_html(url, sesion=None, intentos=3, pausa=PAUSA_SEGUNDOS):
    """Descarga una página y devuelve (html, status_code). Reintenta si falla."""
    sesion = sesion or crear_sesion()
    ultimo_status = None
    for intento in range(1, intentos + 1):
        try:
            response = sesion.get(url, timeout=30)
            ultimo_status = response.status_code
            if response.status_code == 200:
                return response.text, 200
            print(f"Petición fallida ({response.status_code}) intento {intento}: {url}")
        except requests.RequestException as e:
            print(f"Error de conexión intento {intento}: {e}")
        time.sleep(pausa * intento)
    return None, ultimo_status


# --------------------------------------------------------------------------- #
# Parseo (funciones puras sobre HTML)
# --------------------------------------------------------------------------- #
def extraer_enlaces_productos(html):
    """Enlaces a fichas del iPhone 18 Pro dentro del HTML de la colección."""
    soup = BeautifulSoup(html, "html.parser")
    enlaces = set()
    for a in soup.select('a[href*="/products/"]'):
        # Los href vienen con espacios y saltos de línea: se limpian con strip()
        href = a["href"].strip().split("?")[0].replace(BASE_URL, "")
        if href.startswith("/products/iphone-18-pro-") and not href.endswith(".oembed"):
            enlaces.add(href)
    return sorted(enlaces)


def extraer_handles(html):
    """Handles de todas las variantes (modelo x capacidad x color) en una ficha."""
    return sorted(set(PATRON_HANDLE.findall(html)))


def buscar_producto_jsonld(soup):
    """Devuelve el diccionario JSON-LD de tipo Product, o None."""
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            datos = json.loads(script.string or script.get_text())
        except (json.JSONDecodeError, TypeError):
            continue
        candidatos = datos if isinstance(datos, list) else datos.get("@graph", [datos])
        for item in candidatos:
            if isinstance(item, dict) and item.get("@type") == "Product":
                return item
    return None


def separar_caracteristicas(nombre):
    """'iPhone 18 Pro Max 256 GB Borgoña' -> ('iPhone 18 Pro Max', '256 GB', 'Borgoña')."""
    m = re.search(r"^(.*?)\s+(\d+\s*(?:GB|TB))\s*(.*)$", nombre, flags=re.I)
    if not m:
        return nombre, "No disponible", "No disponible"
    modelo, capacidad, color = m.groups()
    capacidad = re.sub(r"\s+", " ", capacidad.upper())
    return modelo.strip(), capacidad, color.strip() or "No disponible"


def convertir_precio(valor):
    """Convierte el precio del JSON-LD a número. Devuelve None si falta o no es válido."""
    if valor in (None, ""):
        return None
    try:
        return float(valor)
    except (TypeError, ValueError):
        return None


def formatear_precio(precio, moneda="COP"):
    if precio is None:
        return "No disponible"
    return f"${precio:,.0f} {moneda}".replace(",", ".")


def parsear_producto(html, url):
    """Extrae los datos de una ficha de producto a partir de su HTML."""
    soup = BeautifulSoup(html, "html.parser")
    producto = buscar_producto_jsonld(soup)
    if producto:
        nombre = producto.get("name", "No disponible")
        sku = producto.get("sku", "No disponible")
        marca = producto.get("brand", {})
        marca = marca.get("name", "Apple") if isinstance(marca, dict) else (marca or "Apple")
        ofertas = producto.get("offers", {})
        if isinstance(ofertas, list):
            ofertas = ofertas[0] if ofertas else {}
        precio = ofertas.get("price") or ofertas.get("lowPrice")
        moneda = ofertas.get("priceCurrency", "COP")
        disponibilidad = str(ofertas.get("availability", "")).split("/")[-1]
    else:
        # Respaldo: leer el título visible de la página
        h1 = soup.find("h1")
        nombre = h1.get_text(strip=True).split("|")[0].strip() if h1 else "No disponible"
        sku, marca, precio, moneda, disponibilidad = "No disponible", "Apple", None, "COP", ""

    modelo, capacidad, color = separar_caracteristicas(nombre)
    precio = convertir_precio(precio)

    return {
        "Referencia (SKU)": sku,
        "Nombre/Marca": f"[{marca}] {nombre}",
        "Valores": formatear_precio(precio, moneda),
        "Caracteristicas": f"{modelo} | {capacidad} | {color}",
        "Modelo": modelo,
        "Capacidad": capacidad,
        "Color": color,
        "Precio_COP": precio,
        "Disponibilidad": DISPONIBILIDAD.get(disponibilidad, disponibilidad or "No disponible"),
        "URL": url,
        "Fuente": "JSON-LD" if producto else "HTML",
    }


# --------------------------------------------------------------------------- #
# Orquestación
# --------------------------------------------------------------------------- #
def ejecutar_scraping(sesion=None, pausa=PAUSA_SEGUNDOS):
    """Recorre la colección, descubre las variantes y extrae cada una."""
    sesion = sesion or crear_sesion()
    inicio = time.time()

    html_coleccion, status = obtener_html(URL_COLECCION, sesion, pausa=pausa)
    if not html_coleccion:
        raise RuntimeError(f"No se pudo descargar la colección (status {status})")

    handles = set()
    for enlace in extraer_enlaces_productos(html_coleccion):
        html_ficha, _ = obtener_html(BASE_URL + enlace, sesion, pausa=pausa)
        if html_ficha:
            handles.update(extraer_handles(html_ficha))
        time.sleep(pausa)
        if len(handles) >= VARIANTES_ESPERADAS:
            break

    filas, errores = [], []
    for url in sorted(f"{BASE_URL}/products/{h}" for h in handles):
        html, status = obtener_html(url, sesion, pausa=pausa)
        if html:
            filas.append(parsear_producto(html, url))
        else:
            errores.append({"URL": url, "status": status})
        time.sleep(pausa)

    return filas, errores, time.time() - inicio


def main(salida="data/iphone18pro_ishop.csv"):
    from src.analisis import construir_dataframe

    filas, errores, duracion = ejecutar_scraping()
    df = construir_dataframe(filas)
    df.to_csv(salida, index=False, encoding="utf-8-sig")
    print(f"{len(df)} variantes guardadas en {salida} | errores: {len(errores)} | {duracion:.1f} s")


if __name__ == "__main__":
    main()
