"""Pruebas del parseo. No hacen peticiones al sitio real: usan HTML guardado de iShop."""

import pytest
import requests

from src import scraper
from tests.conftest import html_con_producto

URL = "https://co.tiendasishop.com/products/iphone-18-pro-mjrt4lz-a"


# --- Colección ---------------------------------------------------------------
def test_enlaces_de_la_coleccion(html_coleccion):
    enlaces = scraper.extraer_enlaces_productos(html_coleccion)
    assert enlaces == ["/products/iphone-18-pro-mjrr4lz-a", "/products/iphone-18-pro-mjxq4lz-a"]


def test_enlaces_limpia_espacios_y_parametros():
    html = '<a href="\n  /products/iphone-18-pro-mjxq4lz-a?variant=1  ">x</a>'
    assert scraper.extraer_enlaces_productos(html) == ["/products/iphone-18-pro-mjxq4lz-a"]


# --- Variantes ---------------------------------------------------------------
def test_ficha_contiene_las_32_variantes(html_producto):
    handles = scraper.extraer_handles(html_producto)
    assert len(handles) == scraper.VARIANTES_ESPERADAS
    assert all(h.startswith("iphone-18-pro-") and h.endswith("4lz-a") for h in handles)


def test_handles_descartan_accesorios():
    html = ('"funda-de-techwoven-con-magsafe-para-el-iphone-18-pro-mkdu4zm-a" '
            '"iphone-18-pro-mjrt4lz-a"')
    assert scraper.extraer_handles(html) == ["iphone-18-pro-mjrt4lz-a"]


# --- Ficha de producto ---------------------------------------------------------
def test_parsea_ficha_real(html_producto):
    fila = scraper.parsear_producto(html_producto, URL)
    assert fila["Referencia (SKU)"] == "MJRT4LZ/A"
    assert fila["Nombre/Marca"] == "[Apple] iPhone 18 Pro 256 GB Glaciar"
    assert (fila["Modelo"], fila["Capacidad"], fila["Color"]) == ("iPhone 18 Pro", "256 GB", "Glaciar")
    assert fila["Precio_COP"] == 5_699_000
    assert fila["Valores"] == "$5.699.000 COP"
    assert fila["Disponibilidad"] == "Disponible"
    assert fila["Fuente"] == "JSON-LD"


@pytest.mark.parametrize("nombre, esperado", [
    ("iPhone 18 Pro Max 256 GB Borgoña", ("iPhone 18 Pro Max", "256 GB", "Borgoña")),
    ("iPhone 18 Pro 1 TB Plata", ("iPhone 18 Pro", "1 TB", "Plata")),
    ("iPhone 18 Pro 2tb Negro", ("iPhone 18 Pro", "2TB", "Negro")),
    ("iPhone 18 Pro", ("iPhone 18 Pro", "No disponible", "No disponible")),
])
def test_separar_caracteristicas(nombre, esperado):
    assert scraper.separar_caracteristicas(nombre) == esperado


def test_precio_ausente():
    fila = scraper.parsear_producto(html_con_producto(offers=None), URL)
    assert fila["Precio_COP"] is None
    assert fila["Valores"] == "No disponible"
    assert fila["Disponibilidad"] == "No disponible"


def test_precio_mal_formateado():
    offers = {"@type": "Offer", "price": "consultar", "priceCurrency": "COP"}
    fila = scraper.parsear_producto(html_con_producto(offers=offers), URL)
    assert fila["Precio_COP"] is None


def test_precio_como_texto_numerico():
    offers = [{"@type": "Offer", "price": "8949000.00", "priceCurrency": "COP",
               "availability": "http://schema.org/OutOfStock"}]
    fila = scraper.parsear_producto(html_con_producto(offers=offers), URL)
    assert fila["Precio_COP"] == 8_949_000
    assert fila["Disponibilidad"] == "Agotado"


def test_sin_jsonld_usa_el_h1():
    html = "<html><body><h1>iPhone 18 Pro Max 512 GB Negro | iShop Colombia</h1></body></html>"
    fila = scraper.parsear_producto(html, URL)
    assert fila["Fuente"] == "HTML"
    assert fila["Capacidad"] == "512 GB"
    assert fila["Color"] == "Negro"


def test_jsonld_invalido_se_ignora():
    html = ('<script type="application/ld+json">{no es json</script>'
            "<h1>iPhone 18 Pro 256 GB Plata</h1>")
    assert scraper.parsear_producto(html, URL)["Fuente"] == "HTML"


# --- Capa de red (con una sesión falsa, sin internet) ---------------------------
class RespuestaFalsa:
    def __init__(self, status, text=""):
        self.status_code, self.text = status, text


class SesionFalsa:
    def __init__(self, respuestas):
        self.respuestas, self.llamadas = list(respuestas), 0

    def get(self, url, timeout=None):
        self.llamadas += 1
        r = self.respuestas.pop(0)
        if isinstance(r, Exception):
            raise r
        return r


def test_obtener_html_reintenta_y_luego_responde():
    sesion = SesionFalsa([RespuestaFalsa(500), requests.ConnectionError("caída"),
                          RespuestaFalsa(200, "<html>ok</html>")])
    html, status = scraper.obtener_html(URL, sesion, pausa=0)
    assert (html, status, sesion.llamadas) == ("<html>ok</html>", 200, 3)


def test_obtener_html_devuelve_none_si_todo_falla():
    sesion = SesionFalsa([RespuestaFalsa(503)] * 3)
    assert scraper.obtener_html(URL, sesion, pausa=0) == (None, 503)


class SesionPorUrl:
    """Responde con la colección o con la ficha guardada según la URL pedida."""

    def __init__(self, coleccion, ficha):
        self.coleccion, self.ficha, self.urls = coleccion, ficha, []

    def get(self, url, timeout=None):
        self.urls.append(url)
        return RespuestaFalsa(200, self.coleccion if "/collections/" in url else self.ficha)


def test_ejecutar_scraping_completo_sin_internet(html_coleccion, html_producto):
    sesion = SesionPorUrl(html_coleccion, html_producto)
    filas, errores, _ = scraper.ejecutar_scraping(sesion, pausa=0)
    assert len(filas) == scraper.VARIANTES_ESPERADAS
    assert errores == []
    assert sesion.urls[0] == scraper.URL_COLECCION


# --- Formato colombiano (fix/precio-formato-colombiano) -------------------------
@pytest.mark.parametrize("valor, esperado", [
    ("$5.699.000 COP", 5_699_000),
    ("5.699.000", 5_699_000),
    ("$ 11.149.000", 11_149_000),
    ("6199000.00", 6_199_000),
    (7149000, 7_149_000),
])
def test_precio_formato_colombiano(valor, esperado):
    offers = {"@type": "Offer", "price": valor, "priceCurrency": "COP"}
    assert scraper.parsear_producto(html_con_producto(offers=offers), URL)["Precio_COP"] == esperado
