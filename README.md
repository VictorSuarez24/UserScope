# UserScope · Perfiles y evidencias

Aplicación de escritorio en Python para buscar cuentas públicas en GitHub, Instagram, X, Facebook, YouTube y Twitch. **Encontrar un perfil no demuestra que pertenezca a la persona buscada.** UserScope muestra por separado la existencia del perfil y la procedencia de su asociación.

## Qué cambia en esta versión

- HTTP 200 ya no equivale a perfil encontrado. Se requieren datos específicos del perfil y coincidencia del identificador.
- Las páginas de login, captchas, restricciones y errores quedan como **no verificables**. Los 404/410 y las respuestas explícitas de ausencia quedan como **no encontrados**.
- Wikidata permite descubrir nombres distintos entre redes a partir de una coincidencia exacta de nombre o alias. Si hay varias entidades compatibles, no se elige automáticamente la primera.
- Puedes indicar una cuenta de referencia y hasta cinco alias conocidos. Se revisan los enlaces públicos publicados en los campos de perfil de esa cuenta.
- Variantes acotadas de separadores: `nombre.apellido` puede buscarse también como `nombreapellido` o `nombre_apellido`. No se inventan sufijos como `official` ni se atribuye identidad por semejanza.
- Las coincidencias sin confirmar están ocultas inicialmente. Los filtros permiten inspeccionarlas junto con las comprobaciones fallidas.
- Interfaz actualizada desde el hilo principal, cancelación y un informe independiente por búsqueda en el historial de sesión.

## Instalación

Requiere Python 3.10 o posterior y Tkinter. En Windows suele venir con Python; en Linux puede requerir el paquete `python3-tk` de tu distribución.

```bash
git clone https://github.com/VictorSuarez24/UserScope.git
cd UserScope
python -m venv .venv
```

Activa el entorno:

```powershell
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
```

```bash
# Linux / macOS
source .venv/bin/activate
```

Instala y ejecuta:

```bash
python -m pip install -r requirements.txt
python main.py
```

## Cómo buscar

1. Escribe un usuario (`ibai`), un nombre (`Ibai Llanos`) o una URL de perfil admitida.
2. Si ya conoces una cuenta de esa persona, añade su URL en **Perfil de referencia**. Una URL introducida en el primer campo se usa como referencia automáticamente.
3. Deja activado **Descubrir alias públicos** para consultar Wikidata. Puedes desactivarlo si prefieres comprobar únicamente los usuarios indicados y los enlaces encontrados en sus perfiles.
4. Abre **BUSCAR PERFILES** y revisa los motivos y las fuentes de cada tarjeta.

Por ejemplo, la entidad pública [Ibai Llanos en Wikidata](https://www.wikidata.org/wiki/Q83566876) permite recuperar identificadores diferentes entre Instagram, X, Twitch y YouTube. No hay una lista de celebridades ni excepciones para `ibai` en el código. La disponibilidad y la atribución de cada cuenta se comprueban por separado; pueden cambiar con el tiempo.

### Cómo interpretar las tarjetas

| Existencia | Significado |
| --- | --- |
| Perfil existente | API o datos estructurados del perfil coinciden con el identificador solicitado. Puede ser un homónimo o un imitador. |
| No verificable | Faltan datos suficientes, hay un bloqueo, login, error de red o límite de peticiones. No significa que la cuenta no exista. |
| No encontrado | El proveedor comunica ausencia mediante HTTP 404/410, una página explícita de error o una API sin resultados. |

| Relación con la búsqueda | Significado |
| --- | --- |
| Referencia indicada por ti | Cuenta que tú has aportado como punto de partida. |
| Enlazado desde tu referencia | La referencia publica un enlace a ese perfil. Hay que revisar su contexto: también puede enlazar a colaboradores. |
| Referencia pública · Wikidata | Una entidad compatible publica ese identificador. Wikidata es editable y puede contener errores o datos antiguos. |
| Identidad sin confirmar | Solo coincide el usuario, una variante o un enlace procedente de otro candidato. |

Ninguna etiqueta certifica que una cuenta sea oficial. Un fake que enlace a una cuenta auténtica **no** se convierte por ello en una cuenta relacionada. La expansión de enlaces se limita a un salto y no usa publicaciones ni recomendaciones. No se extraen ni comparan rostros.

## APIs opcionales

Funciona sin claves, con las limitaciones de las páginas públicas. No se eluden logins ni captchas. Las APIs mejoran la comprobación de existencia, pero no certifican identidad entre plataformas.

| Plataforma | Método | Variables de entorno opcionales |
| --- | --- | --- |
| GitHub | API pública `/users/{login}`; exige ID y login coincidente | `USERSCOPE_GITHUB_TOKEN` para aumentar el límite disponible |
| Twitch | API oficial Helix `/users?login=...`; sin credenciales intenta datos estructurados públicos | `TWITCH_CLIENT_ID` y `TWITCH_ACCESS_TOKEN` (ambas) |
| YouTube | API oficial `channels.list` con `forHandle` o `id`; sin clave intenta metadatos públicos del canal | `YOUTUBE_API_KEY` |
| Instagram, X y Facebook | Objeto de perfil o JSON-LD con URL e identificador coincidentes | Ninguna; si la página exige acceso queda no verificable |
| Wikidata | API pública para descubrir identificadores de una entidad compatible | Ninguna |

Configura las variables **en el entorno desde el que arrancas la aplicación**. No se carga `.env` automáticamente. No pongas tokens en el código, informes o commits. No se guardan credenciales ni se muestran URLs de errores que puedan contenerlas.

Documentación de proveedores: [GitHub](https://docs.github.com/en/rest/users/users#get-a-user), [Twitch](https://dev.twitch.tv/docs/api/reference/#get-users), [YouTube](https://developers.google.com/youtube/v3/docs/channels/list) y [Wikidata](https://www.wikidata.org/wiki/Wikidata:Data_access).

Se revisó [API Mega List](https://github.com/cporter202/API-mega-list) como catálogo. No es un servicio de verificación de identidad. Esta versión usa proveedores oficiales y referencias públicas; no requiere contratar un scraper de terceros.

## Límites y decisiones

- Hasta 48 candidatos por búsqueda, 4 trabajadores y una petición simultánea por host. Tras HTTP 401/403/429, no se insiste contra ese host durante la búsqueda.
- Timeout de conexión/lectura de 4/10 segundos, hasta 3 redirecciones y 5 MB por respuesta. Solo se consultan dominios admitidos; no se siguen enlaces hacia servidores arbitrarios.
- Wikidata busca en español e inglés entre hasta 10 entidades. Solo toma declaraciones vigentes no obsoletas, priorizando las de rango preferido. Un nombre que no aparece en Wikidata necesitará alias conocidos o un perfil de referencia.
- Si indicas una referencia, Wikidata debe incluir esa misma cuenta (o el ID de canal resuelto por YouTube); de lo contrario no se mezclan identidades.
- Las APIs o el HTML pueden cambiar. Ante datos insuficientes se conserva la incertidumbre. Instagram, X, Facebook, YouTube y Twitch pueden bloquear peticiones públicas sin credenciales.
- Cancelar detiene nuevas comprobaciones y descarta tareas pendientes; las peticiones ya iniciadas terminan al responder o agotar su timeout. El informe cancelado es parcial.
- Se ha retirado la búsqueda de `Wikipedia/User:usuario`: identifica una cuenta de editor, no la biografía de una persona. La fuente pública de alias es Wikidata.
- Las tarjetas priorizan evidencias; no descargan automáticamente imágenes arbitrarias de `og:image`. Los adaptadores pueden conservar la URL pública del avatar como metadato.
- El historial permanece en memoria durante la sesión. Solo se consultan datos públicos.

## Desarrollo y pruebas

```bash
python -m unittest discover -v
python -m compileall -q cerebro.py config.py descubrimiento.py main.py perfiles.py proveedores.py red.py
```

Las pruebas automatizadas usan respuestas simuladas y no necesitan red ni claves. Cubren falsos positivos, ambigüedad de identidad, enlaces en la dirección incorrecta, alias, APIs, límites y cancelación. Para comprobar también la interfaz en un equipo con Tk y escritorio:

```powershell
$env:USERSCOPE_GUI_TESTS = "1"
python -m unittest tests.test_gui -v
```

Archivos principales:

- `cerebro.py`: orquestación, límites y clasificación por procedencia.
- `perfiles.py`: modelos y normalización de URLs e identificadores.
- `proveedores.py`: validación de cada plataforma y extracción acotada de enlaces.
- `descubrimiento.py`: descubrimiento de alias mediante Wikidata.
- `red.py`: transporte HTTP, redirecciones, tamaño máximo y límites por host.
- `main.py`: interfaz, filtros, cancelación e historial.
- `config.py`: sitios, colores y límites.
