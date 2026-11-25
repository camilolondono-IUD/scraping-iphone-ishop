"""Pruebas de la verificación del despliegue, con un servidor simulado (sin internet)."""

import json

from scripts import verificar_despliegue as vd


def servidor(paginas):
    def descargar(url, timeout=20):
        for ruta, (status, texto) in paginas.items():
            if url.endswith(ruta):
                return status, texto
        return 404, ""
    return descargar


SITIO_OK = {
    "index.html": (200, f"<h1>{vd.TITULO} en iShop Colombia</h1>"),
    "version.json": (200, json.dumps({"entorno": "produccion", "version": "1.1.0", "commit": "abc1234"})),
    "datos.json": (200, json.dumps([{}] * 32)),
}


def test_despliegue_correcto():
    assert vd.verificar("https://x.github.io/app", "abc1234ffff", 32, descargar=servidor(SITIO_OK)) == []


def test_detecta_commit_desactualizado():
    errores = vd.verificar("https://x.github.io/app/", "9999999", 32, descargar=servidor(SITIO_OK))
    assert any("commit desplegado" in e for e in errores)


def test_detecta_pagina_caida_y_datos_incompletos():
    paginas = {**SITIO_OK, "index.html": (404, ""), "datos.json": (200, "[]")}
    errores = vd.verificar("https://x.github.io/app", None, 32, descargar=servidor(paginas))
    assert "index.html respondió 404" in errores
    assert any("0 variantes" in e for e in errores)


def test_main_reintenta_y_falla(monkeypatch):
    monkeypatch.setattr(vd, "verificar", lambda *a, **k: ["caído"])
    monkeypatch.setattr(vd.time, "sleep", lambda s: None)
    assert vd.main(["--url", "https://x", "--intentos", "2"]) == 1


def test_main_exito(monkeypatch):
    monkeypatch.setattr(vd, "verificar", lambda *a, **k: [])
    assert vd.main(["--url", "https://x"]) == 0
