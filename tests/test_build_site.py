import json

from src.build_site import configuracion, generar_sitio


def test_genera_sitio(tmp_path, ruta_datos):
    index = generar_sitio(ruta_datos, tmp_path)
    contenido = index.read_text(encoding="utf-8")
    assert "iPhone 18 Pro Max" in contenido
    assert "precios.png" in contenido
    assert contenido.count("<tr") >= 32
    assert (tmp_path / "precios.png").stat().st_size > 0


def test_tabla_interactiva_con_filtros(tmp_path, ruta_datos):
    contenido = generar_sitio(ruta_datos, tmp_path).read_text(encoding="utf-8")
    for filtro in ("f-modelo", "f-capacidad", "f-color", "f-disponibilidad", "f-texto"):
        assert f'id="{filtro}"' in contenido
    assert contenido.count('data-sku="') == 32
    assert "addEventListener" in contenido


def test_genera_json_de_datos(tmp_path, ruta_datos):
    generar_sitio(ruta_datos, tmp_path)
    datos = json.loads((tmp_path / "datos.json").read_text(encoding="utf-8"))
    assert len(datos) == 32
    assert {"Referencia (SKU)", "Precio_COP", "Disponibilidad"} <= set(datos[0])


def test_configuracion_por_defecto(monkeypatch):
    for var in ("APP_ENV", "APP_VERSION", "GITHUB_SHA"):
        monkeypatch.delenv(var, raising=False)
    assert configuracion() == {"entorno": "local", "version": "dev", "commit": "local"}


def test_variables_de_entorno_llegan_al_sitio(tmp_path, ruta_datos, monkeypatch):
    monkeypatch.setenv("APP_ENV", "produccion")
    monkeypatch.setenv("APP_VERSION", "1.1.0")
    monkeypatch.setenv("GITHUB_SHA", "abcdef1234567")
    contenido = generar_sitio(ruta_datos, tmp_path).read_text(encoding="utf-8")
    assert "produccion · v1.1.0" in contenido
    version = json.loads((tmp_path / "version.json").read_text(encoding="utf-8"))
    assert version["version"] == "1.1.0"
    assert version["entorno"] == "produccion"
    assert version["commit"] == "abcdef1"
    assert version["variantes"] == 32
