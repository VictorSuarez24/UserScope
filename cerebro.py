"""Búsqueda acotada, validación de existencia y procedencia de las coincidencias."""

from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Event

import config
from descubrimiento import descubrir_wikidata
from perfiles import Informe, Origen, crear_objetivo, objetivo_desde_url, variantes_usuario
from proveedores import validar_perfil
from red import ClienteHTTP


def preparar_busqueda(consulta, referencia="", aliases=""):
    consulta = consulta.strip()
    if not consulta or len(consulta) > 100:
        raise ValueError("Escribe un nombre o usuario de entre 1 y 100 caracteres.")
    desde_url = objetivo_desde_url(consulta)
    if desde_url:
        referencia = referencia.strip() or desde_url.url
        consulta = desde_url.usuario
    elif any(c in consulta for c in ("/", "\\", "?", "#", ":")):
        raise ValueError("Usa un nombre, un usuario o una URL de perfil de las plataformas admitidas.")
    objetivo_ref = objetivo_desde_url(referencia) if referencia.strip() else None
    if referencia.strip() and objetivo_ref is None:
        raise ValueError("La referencia debe ser una URL de perfil de GitHub, Instagram, X, Facebook, YouTube o Twitch.")
    consulta = consulta.removeprefix("@").strip()
    if not consulta or not any(c.isalnum() for c in consulta):
        raise ValueError("El nombre debe contener letras o números.")
    extras = list(dict.fromkeys(a.strip().removeprefix("@") for a in aliases.split(",") if a.strip()))
    if len(extras) > 5 or any(not any(crear_objetivo(s, a) for s in config.SITIOS) for a in extras):
        raise ValueError("Introduce hasta cinco alias válidos, separados por comas.")
    return consulta, objetivo_ref, extras


def _clasificar(resultado):
    tipos = {o.tipo for o in resultado.origenes}
    if "referencia" in tipos:
        resultado.identidad = "referencia_usuario"
    elif "enlace_referencia" in tipos:
        resultado.identidad = "enlazado"
    elif "wikidata" in tipos:
        resultado.identidad = "referencia_publica"
    else:
        resultado.identidad = "sin_confirmar"


def buscar_perfiles(consulta, referencia="", aliases="", *, descubrir=True, variantes=True,
                    progreso=None, cancelar=None, cliente=None):
    consulta, objetivo_ref, extras = preparar_busqueda(consulta, referencia, aliases)
    cancelar = cancelar or Event()
    cliente = cliente or ClienteHTTP(cancelar)
    progreso = progreso or (lambda mensaje: None)
    informe = Informe(consulta)
    candidatos = {}
    resultados = {}

    def agregar(objetivo, origen):
        if objetivo is None:
            return
        if objetivo.clave not in candidatos:
            if len(candidatos) >= config.MAX_CANDIDATOS:
                aviso = f"Se alcanzó el límite de {config.MAX_CANDIDATOS} perfiles; acota los alias o la referencia."
                if aviso not in informe.avisos:
                    informe.avisos.append(aviso)
                return
            candidatos[objetivo.clave] = (objetivo, [])
        origenes = candidatos[objetivo.clave][1]
        if origen not in origenes:
            origenes.append(origen)

    referencias = set()
    if objetivo_ref and not cancelar.is_set():
        agregar(objetivo_ref, Origen("referencia", "Perfil de referencia indicado por ti.", objetivo_ref.url))
        progreso("Validando el perfil de referencia…")
        resultado = validar_perfil(objetivo_ref, cliente)
        resultados[objetivo_ref.clave] = resultado
        referencias.add(objetivo_ref.clave)
        if resultado.encontrado and objetivo_ref.sitio == "YouTube":
            canal = crear_objetivo("YouTube", resultado.identificador, "canal")
            if canal:
                referencias.add(canal.clave)
        if not resultado.encontrado:
            informe.avisos.append("No se pudo validar la existencia del perfil de referencia; no se extraerán sus enlaces.")

    if descubrir and not cancelar.is_set():
        progreso("Buscando alias en referencias públicas…")
        descubiertos, avisos = descubrir_wikidata(consulta, cliente, referencias)
        informe.avisos.extend(avisos)
        for objetivo, origen in descubiertos:
            agregar(objetivo, origen)

    for usuario in [consulta, *extras]:
        for sitio in config.SITIOS:
            agregar(crear_objetivo(sitio, usuario), Origen(
                "consulta" if usuario == consulta else "alias",
                "Coincidencia de usuario; no demuestra que sea la misma persona."
                if usuario == consulta else f"Alias indicado por ti: {usuario}; identidad pendiente."))
        if variantes:
            for variante in variantes_usuario(usuario):
                if variante == usuario:
                    continue
                for sitio in config.SITIOS:
                    agregar(crear_objetivo(sitio, variante), Origen(
                        "variante", f"Variante de separadores de {usuario}; identidad pendiente."))

    def validar_pendientes():
        pendientes = [o for clave, (o, _) in candidatos.items() if clave not in resultados]
        with ThreadPoolExecutor(max_workers=config.MAX_WORKERS) as executor:
            futuros = {}
            for objetivo in pendientes:
                if cancelar.is_set():
                    break
                futuros[executor.submit(validar_perfil, objetivo, cliente)] = objetivo
            for futuro in as_completed(futuros):
                if cancelar.is_set():
                    for pendiente in futuros:
                        pendiente.cancel()
                    break
                objetivo = futuros[futuro]
                resultados[objetivo.clave] = futuro.result()
                progreso(f"Comprobados {len(resultados)} de {len(candidatos)} perfiles · {objetivo.sitio}")

    if not cancelar.is_set():
        validar_pendientes()

    # Una única expansión. Un fake que enlaza a la cuenta real no se convierte en referencia.
    for clave, resultado in list(resultados.items()):
        if cancelar.is_set() or not resultado.encontrado:
            continue
        canal = crear_objetivo("YouTube", resultado.identificador, "canal") if resultado.objetivo.sitio == "YouTube" else None
        es_referencia = objetivo_ref is not None and (
            clave == objetivo_ref.clave or (canal is not None and canal.clave in referencias))
        tipo = "enlace_referencia" if es_referencia else "enlace_candidato"
        detalle = ("Enlace publicado en tu perfil de referencia; revisa su contexto." if es_referencia else
                   "Enlace publicado en otro candidato; no confirma identidad.")
        objetivos = [objetivo_desde_url(e.rstrip(".,);]")) for e in resultado.enlaces]
        objetivos = list(dict.fromkeys(o for o in objetivos if o and o.clave != clave))
        for objetivo in objetivos[:config.MAX_ENLACES_POR_PERFIL]:
            agregar(objetivo, Origen(tipo, detalle, resultado.objetivo.url))

    if not cancelar.is_set():
        validar_pendientes()
    else:
        informe.avisos.append("Búsqueda cancelada. Se muestran solo las comprobaciones terminadas.")

    # Agrupar las URLs handle/channel que un proveedor identifica como el mismo perfil.
    unicos = {}
    for clave, resultado in resultados.items():
        resultado.origenes = candidatos[clave][1].copy()
        id_perfil = ((resultado.objetivo.sitio, resultado.identificador) if
                     resultado.encontrado and resultado.identificador else clave)
        if id_perfil in unicos:
            anterior = unicos[id_perfil]
            anterior.origenes = list(dict.fromkeys(anterior.origenes + resultado.origenes))
            anterior.evidencias = list(dict.fromkeys(anterior.evidencias + resultado.evidencias))
        else:
            unicos[id_perfil] = resultado
    for resultado in unicos.values():
        _clasificar(resultado)
    prioridad = {"referencia_usuario": 0, "enlazado": 1, "referencia_publica": 2, "sin_confirmar": 3}
    informe.resultados = sorted(unicos.values(), key=lambda r: (
        prioridad[r.identidad], not r.encontrado, r.objetivo.sitio, r.objetivo.usuario.casefold()))
    return informe


def escanear_sitio(nombre_sitio, url_base, usuario):
    """Compatibilidad con v1: encontrado expresa existencia, nunca propiedad de la cuenta."""
    objetivo = crear_objetivo(nombre_sitio, usuario)
    if objetivo is None:
        return None
    resultado = validar_perfil(objetivo, ClienteHTTP())
    if not resultado.encontrado:
        return None
    return {"sitio": nombre_sitio, "url": objetivo.url, "imagen": None,
            "encontrado": resultado.encontrado, "estado": resultado.estado,
            "identidad": "sin_confirmar", "evidencias": resultado.evidencias}
