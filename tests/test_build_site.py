from src.build_site import generar_sitio


def test_genera_sitio(tmp_path, ruta_datos):
    index = generar_sitio(ruta_datos, tmp_path)
    contenido = index.read_text(encoding="utf-8")
    assert "iPhone 18 Pro Max" in contenido
    assert "precios.png" in contenido
    assert contenido.count("<tr>") >= 32
    assert (tmp_path / "precios.png").stat().st_size > 0
