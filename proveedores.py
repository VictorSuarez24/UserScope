"""Validación específica por plataforma. Un HTTP 200 nunca basta."""

import json
import os
import re

from bs4 import BeautifulSoup

from perfiles import Resultado, crear_objetivo, objetivo_desde_url
from red import ErrorRed


def enlaces_en_texto(texto):
    return list(dict.fromkeys(re.findall(r"https?://[^\s<>\"']+", texto or "")))[:20]


def _estado_http(respuesta, resultado):
    if respuesta.status_code in (404, 410):
        resultado.estado = "no_encontrado"
        resultado.evidencias.append(f"El proveedor devuelve HTTP {respuesta.status_code}.")
    elif respuesta.status_code in (401, 403, 429):
        resultado.evidencias.append(
            f"Acceso restringido o límite de peticiones (HTTP {respuesta.status_code}).")
    elif respuesta.status_code != 200:
        resultado.evidencias.append(f"Respuesta no concluyente (HTTP {respuesta.status_code}).")
    else:
        return False
    return True


def _confirmar(resultado, nombre, descripcion, identificador, prueba, enlaces=()):
    resultado.estado = "encontrado"
    resultado.nombre = str(nombre or resultado.objetivo.usuario)[:200]
    resultado.descripcion = str(descripcion or "")[:2000]
    resultado.identificador = str(identificador or "")
    resultado.evidencias.append(prueba)
    # Solo campos del perfil; nunca enlaces de publicaciones, navegación o recomendaciones.
    resultado.enlaces = list(dict.fromkeys(
        [e for e in enlaces if isinstance(e, str)] + enlaces_en_texto(resultado.descripcion)))[:20]
    return resultado


def _github(objetivo, cliente, resultado):
    headers = {"Accept": "application/vnd.github+json"}
    if os.getenv("USERSCOPE_GITHUB_TOKEN"):
        headers["Authorization"] = "Bearer " + os.environ["USERSCOPE_GITHUB_TOKEN"]
    respuesta = cliente.get(f"https://api.github.com/users/{objetivo.usuario}", headers=headers)
    if _estado_http(respuesta, resultado):
        return resultado
    datos = respuesta.json()
    if (not isinstance(datos, dict) or not datos.get("id")
            or str(datos.get("login", "")).casefold() != objetivo.usuario.casefold()
            or datos.get("type") not in ("User", "Organization")):
        resultado.evidencias.append("La API no confirma el identificador solicitado.")
        return resultado
    enlaces = [datos["blog"]] if isinstance(datos.get("blog"), str) else []
    twitter = crear_objetivo("Twitter/X", datos.get("twitter_username"))
    if twitter:
        enlaces.append(twitter.url)
    resultado.foto_url = datos.get("avatar_url", "")
    return _confirmar(resultado, datos.get("name"), datos.get("bio"), datos["id"],
                      "La API de GitHub devuelve un ID y el usuario exacto.", enlaces)


def _twitch(objetivo, cliente, resultado):
    respuesta = cliente.get("https://api.twitch.tv/helix/users",
                            params={"login": objetivo.usuario},
                            headers={"Client-Id": os.environ["TWITCH_CLIENT_ID"],
                                     "Authorization": "Bearer " + os.environ["TWITCH_ACCESS_TOKEN"]})
    if _estado_http(respuesta, resultado):
        return resultado
    datos = respuesta.json()
    usuarios = datos.get("data") if isinstance(datos, dict) else None
    if usuarios == []:
        resultado.estado = "no_encontrado"
        resultado.evidencias.append("La API de Twitch no devuelve ese usuario.")
        return resultado
    if isinstance(usuarios, list):
        for usuario in usuarios:
            if (isinstance(usuario, dict) and usuario.get("id")
                    and str(usuario.get("login", "")).casefold() == objetivo.usuario.casefold()):
                resultado.foto_url = usuario.get("profile_image_url", "")
                return _confirmar(resultado, usuario.get("display_name"), usuario.get("description"),
                                  usuario["id"], "La API de Twitch confirma el usuario y su ID.")
    resultado.evidencias.append("Respuesta de Twitch sin el usuario solicitado.")
    return resultado


def _youtube(objetivo, cliente, resultado):
    params = {"part": "snippet", "key": os.environ["YOUTUBE_API_KEY"]}
    params["id" if objetivo.tipo == "canal" else "forHandle"] = objetivo.usuario
    respuesta = cliente.get("https://www.googleapis.com/youtube/v3/channels", params=params)
    if _estado_http(respuesta, resultado):
        return resultado
    datos = respuesta.json()
    canales = datos.get("items") if isinstance(datos, dict) else None
    if canales == []:
        resultado.estado = "no_encontrado"
        resultado.evidencias.append("La API de YouTube no devuelve ese canal.")
        return resultado
    if isinstance(canales, list) and len(canales) == 1 and isinstance(canales[0], dict):
        canal = canales[0]
        detalle = canal.get("snippet", {})
        valido = (canal.get("id") == objetivo.usuario if objetivo.tipo == "canal" else
                  str(detalle.get("customUrl", "")).removeprefix("@").casefold()
                  == objetivo.usuario.casefold())
        if valido and crear_objetivo("YouTube", canal.get("id"), "canal"):
            return _confirmar(resultado, detalle.get("title"), detalle.get("description"),
                              canal["id"], "La API de YouTube confirma el identificador del canal.")
    resultado.evidencias.append("La API no confirma el canal solicitado.")
    return resultado


def _coincide_url(url, objetivo):
    otro = objetivo_desde_url(url)
    return otro is not None and otro.clave == objetivo.clave


def _json_script(script):
    try:
        return json.loads(script.string or script.get_text())
    except (ValueError, TypeError):
        return None


def _perfil_jsonld(soup, objetivo):
    """Solo Person/ProfilePage de la propia URL, no autores de posts o @graph arbitrarios."""
    for script in soup.find_all("script", type="application/ld+json"):
        datos = _json_script(script)
        for nodo in datos if isinstance(datos, list) else [datos]:
            if not isinstance(nodo, dict):
                continue
            if nodo.get("@type") == "ProfilePage" and _coincide_url(nodo.get("url"), objetivo):
                nodo = nodo.get("mainEntity", {})
            if not isinstance(nodo, dict) or nodo.get("@type") not in ("Person", "Organization"):
                continue
            alias = str(nodo.get("alternateName", "")).removeprefix("@").casefold()
            if _coincide_url(nodo.get("url"), objetivo) and alias == objetivo.usuario.casefold():
                return nodo
    return None


def _metadatos_youtube(soup, objetivo):
    for script in soup.find_all("script"):
        contenido = script.string or ""
        match = re.search(r'(?:var\s+ytInitialData|window\["ytInitialData"\]|ytInitialData)\s*=\s*', contenido)
        if not match:
            continue
        try:
            datos, _ = json.JSONDecoder().raw_decode(contenido[match.end():].lstrip())
        except ValueError:
            continue
        if not isinstance(datos, dict):
            continue
        canal = datos.get("metadata", {}).get("channelMetadataRenderer", {})
        if not isinstance(canal, dict) or not crear_objetivo("YouTube", canal.get("externalId"), "canal"):
            continue
        if ((objetivo.tipo == "canal" and canal["externalId"] == objetivo.usuario)
                or _coincide_url(canal.get("vanityChannelUrl"), objetivo)
                or _coincide_url(canal.get("channelUrl"), objetivo)):
            return canal
    return None


def _usuario_instagram(soup, objetivo):
    for script in soup.find_all("script", type="application/json"):
        datos = _json_script(script)
        if not isinstance(datos, dict):
            continue
        # Rutas concretas del objeto de perfil; no buscar cualquier username en toda la página.
        rutas = [("graphql", "user"), ("data", "user")]
        for ruta in rutas:
            usuario = datos
            for clave in ruta:
                usuario = usuario.get(clave, {}) if isinstance(usuario, dict) else {}
            if (isinstance(usuario, dict) and (usuario.get("id") or usuario.get("pk"))
                    and str(usuario.get("username", "")).casefold() == objetivo.usuario.casefold()):
                return usuario
    return None


def _html(objetivo, cliente, resultado):
    respuesta = cliente.get(objetivo.url)
    destino = objetivo_desde_url(respuesta.url)
    # Una redirección a login, portada u otro perfil no confirma el usuario solicitado.
    if not destino or (destino.clave != objetivo.clave and not (
            objetivo.sitio == "YouTube" and destino.sitio == "YouTube" and destino.tipo == "canal")):
        resultado.evidencias.append("La página redirige a un destino diferente del perfil solicitado.")
        return resultado
    if _estado_http(respuesta, resultado):
        return resultado
    soup = BeautifulSoup(respuesta.text, "html.parser")
    titulo = soup.title.get_text(" ", strip=True).casefold() if soup.title else ""
    if (any(s in titulo for s in ("log in", "login", "sign in", "iniciar sesión", "captcha",
                                  "just a moment", "access denied", "consent"))
            or soup.find("input", attrs={"type": "password"})):
        resultado.evidencias.append("Página de acceso, consentimiento o protección antibots.")
        return resultado
    if objetivo.sitio == "YouTube":
        canal = _metadatos_youtube(soup, objetivo)
        if canal:
            return _confirmar(resultado, canal.get("title"), canal.get("description"),
                              canal["externalId"], "Los metadatos del canal confirman su ID y URL.")
    if objetivo.sitio == "Instagram":
        usuario = _usuario_instagram(soup, objetivo)
        if usuario:
            return _confirmar(resultado, usuario.get("full_name"), usuario.get("biography"),
                              usuario.get("id") or usuario.get("pk"),
                              "El objeto de perfil contiene un ID y el usuario exacto.",
                              [usuario["external_url"]] if usuario.get("external_url") else [])
    persona = _perfil_jsonld(soup, objetivo)
    if persona:
        enlaces = persona.get("sameAs", [])
        if isinstance(enlaces, str):
            enlaces = [enlaces]
        if not isinstance(enlaces, list):
            enlaces = []
        return _confirmar(resultado, persona.get("name"), persona.get("description"), "",
                          "Datos estructurados de perfil con URL y usuario coincidentes.",
                          [e for e in enlaces if isinstance(e, str)])
    if any(s in titulo for s in ("page not found", "page isn't available", "page not available",
                                 "página no disponible", "página no encontrada")):
        resultado.estado = "no_encontrado"
        resultado.evidencias.append("La página indica que el perfil no existe (soft 404).")
        return resultado
    resultado.evidencias.append("HTTP 200 sin datos de perfil suficientes; no confirma existencia.")
    if objetivo.sitio == "Twitch":
        resultado.evidencias.append("La API oficial requiere TWITCH_CLIENT_ID y TWITCH_ACCESS_TOKEN.")
    return resultado


def validar_perfil(objetivo, cliente):
    resultado = Resultado(objetivo)
    try:
        if objetivo.sitio == "GitHub":
            return _github(objetivo, cliente, resultado)
        if objetivo.sitio == "Twitch" and all(os.getenv(k) for k in ("TWITCH_CLIENT_ID", "TWITCH_ACCESS_TOKEN")):
            return _twitch(objetivo, cliente, resultado)
        if objetivo.sitio == "YouTube" and os.getenv("YOUTUBE_API_KEY"):
            return _youtube(objetivo, cliente, resultado)
        return _html(objetivo, cliente, resultado)
    except ErrorRed as exc:
        resultado.evidencias.append(str(exc))
    except (ValueError, TypeError, KeyError, AttributeError):
        resultado.estado = "no_verificable"
        resultado.evidencias.append("El proveedor devolvió datos incompletos o con un formato no reconocido.")
    return resultado
