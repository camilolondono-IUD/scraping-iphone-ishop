from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"
RAIZ = Path(__file__).resolve().parents[1]


@pytest.fixture
def html_producto():
    return (FIXTURES / "producto_iphone18pro_mjrt4lz.html").read_text(encoding="utf-8")


@pytest.fixture
def html_coleccion():
    return (FIXTURES / "coleccion_iphone18pro.html").read_text(encoding="utf-8")


@pytest.fixture
def ruta_datos():
    return RAIZ / "data" / "iphone18pro_ishop.csv"


def html_con_producto(offers=None, nombre="iPhone 18 Pro Max 1 TB Plata"):
    """HTML mínimo con un bloque JSON-LD de tipo Product para casos borde."""
    import json

    producto = {"@context": "https://schema.org", "@type": "Product", "name": nombre,
                "sku": "MJXY4LZ/A", "brand": {"@type": "Brand", "name": "Apple"}}
    if offers is not None:
        producto["offers"] = offers
    return f'<html><head><script type="application/ld+json">{json.dumps(producto)}</script></head></html>'
