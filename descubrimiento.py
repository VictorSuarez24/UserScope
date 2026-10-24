"""Descubre alias publicados en Wikidata sin convertir una búsqueda en prueba de identidad."""

import re

from perfiles import Origen, crear_objetivo, normalizar_nombre
from red import ErrorRed


PROPIEDADES = {
    "P2003": ("Instagram", "usuario"), "P2002": ("Twitter/X", "usuario"),
    "P5797": ("Twitch", "usuario"), "P2397": ("YouTube", "canal"),
    "P2013": ("Facebook", "usuario"), "P2037": ("GitHub", "usuario"),
}
API = "https://www.wikidata.org/w/api.php"


def _consultar(cliente, **params):
    respuesta = cliente.get(API, params={"format": "json", "maxlag": 10, **params})
    if respuesta.status_code != 200:
        raise ErrorRed(f"Wikidata no disponible (HTTP {respuesta.status_code}).")
    datos = respuesta.json()
    if isinstance(datos, dict) and datos.get("error", {}).get("code") == "maxlag":
        raise ErrorRed("Wikidata está temporalmente retrasado; prueba de nuevo más tarde.")
    if not isinstance(datos, dict) or "error" in datos:
        raise ErrorRed("Wikidata no pudo completar la consulta.")
    return datos


def _cuentas(entidad):
    cuentas = []
    for propiedad, (sitio, tipo) in PROPIEDADES.items():
        declaraciones = [c for c in entidad.get("claims", {}).get(propiedad, [])
                         if c.get("rank") != "deprecated" and "P582" not in c.get("qualifiers", {})]
        preferidas = [c for c in declaraciones if c.get("rank") == "preferred"]
        for declaracion in preferidas or declaraciones:
            snak = declaracion.get("mainsnak", {})
            if snak.get("snaktype") != "value":
                continue
            objetivo = crear_objetivo(sitio, snak.get("datavalue", {}).get("value"), tipo)
            if objetivo and objetivo not in cuentas:
                cuentas.append(objetivo)
    return cuentas


def descubrir_wikidata(consulta, cliente, referencias=()):
    """Devuelve candidatos y avisos. Una entidad ambigua nunca se elige por posición."""
    try:
        ids = []
        for idioma in ("es", "en"):
            datos = _consultar(cliente, action="wbsearchentities", search=consulta,
                               language=idioma, uselang="es", type="item", limit=5)
            for entidad in datos.get("search", []):
                identificador = entidad.get("id", "")
                if re.fullmatch(r"Q\d+", identificador) and identificador not in ids:
                    ids.append(identificador)
        if not ids:
            return [], ["Wikidata no encontró una referencia pública para esta búsqueda."]
        datos = _consultar(cliente, action="wbgetentities", ids="|".join(ids[:10]),
                           props="labels|aliases|descriptions|claims", languages="es|en")
        coincidencias = []
        for identificador in ids[:10]:
            entidad = datos.get("entities", {}).get(identificador, {})
            nombres = [v["value"] for v in entidad.get("labels", {}).values() if "value" in v]
            nombres += [v["value"] for grupo in entidad.get("aliases", {}).values()
                        for v in grupo if "value" in v]
            cuentas = _cuentas(entidad)
            exacto = normalizar_nombre(consulta) in {normalizar_nombre(n) for n in nombres}
            vinculado = bool({c.clave for c in cuentas} & set(referencias))
            if cuentas and (vinculado if referencias else exacto):
                etiqueta = entidad.get("labels", {}).get("es", {}).get("value") or (
                    entidad.get("labels", {}).get("en", {}).get("value", identificador))
                coincidencias.append((identificador, etiqueta, cuentas))
        if len(coincidencias) != 1:
            if coincidencias:
                opciones = ", ".join(f"{nombre} ({qid})" for qid, nombre, _ in coincidencias)
                return [], [f"Referencia ambigua: {opciones}. Usa un perfil de referencia para distinguirlas."]
            return [], ["No hay una referencia pública inequívoca que coincida con la búsqueda o el perfil indicado."]
        qid, nombre, cuentas = coincidencias[0]
        origen = Origen("wikidata", f"Wikidata: {nombre} ({qid}); dato público, revisable.",
                        f"https://www.wikidata.org/wiki/{qid}")
        return [(cuenta, origen) for cuenta in cuentas], [
            f"Alias publicados en Wikidata para {nombre} ({qid}). La atribución pública puede contener errores."]
    except ErrorRed as exc:
        return [], [f"{exc} Continúan las comprobaciones directas."]
    except (ValueError, TypeError, KeyError, AttributeError):
        return [], ["No se pudo consultar Wikidata; continúan las comprobaciones directas."]
