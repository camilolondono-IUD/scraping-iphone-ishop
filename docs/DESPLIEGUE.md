# Despliegue de la aplicación

La aplicación es un sitio estático (HTML, JavaScript, JSON e imagen) que se aloja en
**GitHub Pages**, el servicio de alojamiento en la nube de GitHub, y se publica con el
pipeline de GitHub Actions. No requiere servidor propio ni base de datos.

- **URL pública:** <https://camilolondono-iud.github.io/scraping-iphone-ishop/>
- **Versión publicada:** <https://camilolondono-iud.github.io/scraping-iphone-ishop/version.json>
- **Datos:** <https://camilolondono-iud.github.io/scraping-iphone-ishop/datos.json>

## 1. Configuración del servicio (GitHub Pages)

**Settings > Pages > Build and deployment > Source: _GitHub Actions_**

Con esta opción GitHub no publica una rama, sino el artefacto que sube el job `build`. Así lo
que se despliega es siempre lo que pasó las pruebas.

## 2. Entorno `github-pages`

GitHub crea el entorno automáticamente con el primer despliegue (**Settings > Environments**).

| Configuración | Valor |
| --- | --- |
| Nombre | `github-pages` |
| Ramas que pueden desplegar | Solo `main` (regla por defecto del entorno) |
| URL | La que devuelve `actions/deploy-pages` |
| Historial | **Code > Deployments** muestra cada despliegue con su commit |

## 3. Variables de entorno

La aplicación lee su configuración de variables de entorno (`src/build_site.py`, función
`configuracion()`):

| Variable | Dónde se define | Valor en producción | Por defecto | Uso |
| --- | --- | --- | --- | --- |
| `APP_ENV` | Variable del repositorio | `produccion` | `local` | Etiqueta del entorno en la app y en `version.json` |
| `APP_VERSION` | Variable del repositorio | `1.1.0` | `dev` | Versión mostrada en la app y en `version.json` |
| `GITHUB_SHA` | GitHub Actions (automática) | SHA del commit | `local` | Commit desplegado; lo usa la prueba de humo |

### Cómo crear las variables

1. **Settings > Secrets and variables > Actions > pestaña _Variables_ > New repository variable**.
2. Crear `APP_ENV` = `produccion`.
3. Crear `APP_VERSION` = `1.1.0`.

Son **variables** y no *secrets* porque no contienen información sensible; aparecen en los logs
y en la propia aplicación. El proyecto no necesita secretos: el despliegue se autentica con el
token OIDC que GitHub genera en cada ejecución (`id-token: write`).

### Cómo cambiar la versión publicada

Cambiar `APP_VERSION` en las variables del repositorio y volver a ejecutar el workflow
(**Actions > CI/CD > Run workflow** sobre `main`) o fusionar un nuevo PR.

## 4. Permisos

| Job | Permisos | Motivo |
| --- | --- | --- |
| Todos (por defecto) | `contents: read` | Leer el código |
| `deploy` | `pages: write`, `id-token: write` | Publicar en Pages autenticándose con OIDC |

## 5. Proceso de despliegue

1. Se fusiona un PR en `main` (con el check **Pruebas y linting** en verde, exigido por la
   protección de la rama).
2. El push a `main` dispara el workflow: `test` → `build` → `deploy` → `verificar`.
3. `deploy` publica el artefacto en el entorno `github-pages`.
4. `verificar` comprueba la URL pública, el commit en `version.json` y las 32 variantes.
5. El pie de página y la etiqueta superior de la app muestran versión, entorno y commit.

## 6. Comprobar un despliegue a mano

```bash
curl -s https://camilolondono-iud.github.io/scraping-iphone-ishop/version.json
# {"entorno": "produccion", "version": "1.1.0", "commit": "abc1234", ...}

python scripts/verificar_despliegue.py --url https://camilolondono-iud.github.io/scraping-iphone-ishop/ --variantes 32
```

## 7. Revertir un despliegue

1. **Revert del PR** (recomendado): en el PR fusionado, botón **Revert** → fusionar el PR que
   GitHub crea. El pipeline vuelve a desplegar la versión anterior.
   Por consola: `git revert -m 1 <sha-del-merge> && git push`.
2. **Re-ejecutar** un despliegue anterior: Actions > ejecución buena > **Re-run all jobs**.
3. **Versiones etiquetadas:** `v1.0.0` (EA2) y `v1.1.0` (EA3) marcan puntos estables.

## 8. Problemas frecuentes

| Síntoma | Causa | Solución |
| --- | --- | --- |
| `deploy` falla con *Pages not enabled* | Pages no está configurado con *GitHub Actions* | Settings > Pages > Source: GitHub Actions |
| `verificar` falla por commit distinto | La CDN aún sirve la versión anterior | Esperar y re-ejecutar el job; ya reintenta 10 veces |
| La app muestra `dev` | No existe la variable `APP_VERSION` | Crearla en Settings > Variables |
| `deploy` no corre en un PR | Es lo esperado | Solo despliega en push a `main` |
