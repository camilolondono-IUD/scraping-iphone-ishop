from src import analisis


def test_orden_capacidad():
    caps = ["2 TB", "256 GB", "1 TB", "512 GB"]
    assert sorted(caps, key=analisis.orden_capacidad) == ["256 GB", "512 GB", "1 TB", "2 TB"]
    assert analisis.orden_capacidad("sin dato") == 0


def test_datos_completos(ruta_datos):
    df = analisis.cargar_datos(ruta_datos)
    assert len(df) == 32
    assert df["URL"].is_unique
    assert df["Precio_COP"].notna().all()
    assert set(df["Modelo"]) == {"iPhone 18 Pro", "iPhone 18 Pro Max"}


def test_tabla_de_precios(ruta_datos):
    t = analisis.tabla_precios(analisis.cargar_datos(ruta_datos))
    assert list(t.index) == ["256 GB", "512 GB", "1 TB", "2 TB"]
    assert t.loc["256 GB", "iPhone 18 Pro"] == 5_699_000
    assert t.loc["2 TB", "iPhone 18 Pro Max"] == 11_699_000


def test_el_color_no_cambia_el_precio(ruta_datos):
    assert (analisis.precios_por_color(analisis.cargar_datos(ruta_datos)) == 1).all()


def test_pro_max_siempre_cuesta_mas(ruta_datos):
    assert (analisis.diferencia_modelos(analisis.cargar_datos(ruta_datos)) > 0).all()


def test_construir_dataframe_quita_duplicados_y_ordena():
    fila = {"URL": "u1", "Modelo": "iPhone 18 Pro", "Capacidad": "1 TB", "Color": "Negro"}
    otra = {"URL": "u2", "Modelo": "iPhone 18 Pro", "Capacidad": "256 GB", "Color": "Negro"}
    df = analisis.construir_dataframe([fila, otra, fila])
    assert list(df["URL"]) == ["u2", "u1"]


def test_resumen(ruta_datos):
    r = analisis.resumen(analisis.cargar_datos(ruta_datos))
    assert r["variantes"] == 32
    assert r["disponibles"] + r["agotados"] == 32
    assert r["precio_min"] < r["precio_max"]
