"""Regresiones offline: páginas falsas, identidad, alias y fallos de proveedores."""

import json
import unittest
from threading import Event
from unittest.mock import patch

from cerebro import buscar_perfiles, preparar_busqueda
from descubrimiento import API, descubrir_wikidata
from perfiles import Objetivo, Origen, Resultado, objetivo_desde_url
from proveedores import validar_perfil
from red import ClienteHTTP, ErrorRed, Respuesta


CANAL = "UC" + "A" * 22


class ClienteFalso:
    def __init__(self, respuesta):
        self.respuesta = respuesta
        self.llamadas = []

    def get(self, url, **kwargs):
        self.llamadas.append((url, kwargs))
        if isinstance(self.respuesta, Exception):
            raise self.respuesta
        if callable(self.respuesta):
            return self.respuesta(url, **kwargs)
        return self.respuesta


def json_respuesta(datos, url="https://api.github.com/users/ibai"):
    return Respuesta(200, url, json.dumps(datos))


def jsonld(objetivo, **kwargs):
    persona = {"@type": "Person", "name": "Ibai", "alternateName": "@" + objetivo.usuario,
               "url": objetivo.url, **kwargs}
    return '<script type="application/ld+json">' + json.dumps(persona) + '</script>'


class ValidacionTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict("os.environ", {}, clear=True)
        self.env.start()
        self.addCleanup(self.env.stop)
        self.instagram = Objetivo("Instagram", "ibai")

    def html(self, contenido, objetivo=None, status=200, url=None):
        objetivo = objetivo or self.instagram
        return validar_perfil(objetivo, ClienteFalso(Respuesta(status, url or objetivo.url, contenido)))

    def test_200_vacio_no_es_perfil(self):
        self.assertEqual(self.html("<title>Instagram</title>").estado, "no_verificable")

    def test_og_image_y_nombre_no_prueban_existencia(self):
        self.assertFalse(self.html('<title>ibai</title><meta property="og:image" content="foto.jpg">').encontrado)

    def test_login_200_incluso_con_metadata_no_confirma(self):
        resultado = self.html('<title>Log in</title>' + jsonld(self.instagram))
        self.assertEqual(resultado.estado, "no_verificable")

    def test_formulario_login_no_confirma(self):
        self.assertFalse(self.html('<input type="password">' + jsonld(self.instagram)).encontrado)

    def test_captcha_no_es_ausencia(self):
        self.assertEqual(self.html('<title>Just a moment...</title>').estado, "no_verificable")

    def test_soft_404(self):
        self.assertEqual(self.html('<title>Page Not Found</title>').estado, "no_encontrado")

    def test_estados_http(self):
        for estado in (401, 403, 429, 500):
            with self.subTest(estado=estado):
                self.assertEqual(self.html(jsonld(self.instagram), status=estado).estado, "no_verificable")
        for estado in (404, 410):
            self.assertEqual(self.html("", status=estado).estado, "no_encontrado")

    def test_redireccion_login_u_otro_usuario(self):
        for url in ("https://www.instagram.com/accounts/login/", "https://www.instagram.com/otro"):
            self.assertFalse(self.html(jsonld(self.instagram), url=url).encontrado)

    def test_404_de_login_no_significa_que_el_perfil_no_exista(self):
        resultado = self.html("", url="https://www.instagram.com/accounts/login/", status=404)
        self.assertEqual(resultado.estado, "no_verificable")

    def test_jsonld_valido_solo_confirma_existencia(self):
        resultado = self.html(jsonld(self.instagram))
        self.assertTrue(resultado.encontrado)
        self.assertEqual(resultado.identidad, "sin_confirmar")

    def test_metadatos_de_otro_usuario_no_confirman(self):
        self.assertFalse(self.html(jsonld(Objetivo("Instagram", "otra_persona"))).encontrado)

    def test_autor_de_post_no_confirma_perfil(self):
        contenido = '<script type="application/ld+json">' + json.dumps({
            "@type": "Article", "author": {"@type": "Person", "alternateName": "ibai", "url": self.instagram.url}
        }) + '</script>'
        self.assertFalse(self.html(contenido).encontrado)

    def test_solo_enlaces_de_perfil_no_navegacion(self):
        contenido = jsonld(self.instagram, sameAs=["https://www.twitch.tv/otro_alias"])
        contenido += '<a href="https://x.com/recomendado">Recomendado</a>'
        resultado = self.html(contenido)
        self.assertEqual(resultado.enlaces, ["https://www.twitch.tv/otro_alias"])

    def test_objeto_instagram_usuario_exacto(self):
        perfil = {"data": {"user": {"id": "123", "username": "ibai", "biography": "Hola"}}}
        contenido = '<script type="application/json">' + json.dumps(perfil) + '</script>'
        self.assertTrue(self.html(contenido).encontrado)
        self.assertFalse(self.html(contenido.replace('"ibai"', '"otro"')).encontrado)

    def test_youtube_metadata_del_canal(self):
        objetivo = Objetivo("YouTube", "ibai")
        datos = {"metadata": {"channelMetadataRenderer": {
            "externalId": CANAL, "vanityChannelUrl": objetivo.url, "title": "Ibai"}}}
        contenido = '<script>var ytInitialData = ' + json.dumps(datos) + ';</script>'
        self.assertTrue(self.html(contenido, objetivo).encontrado)
        otro = Objetivo("YouTube", "otro")
        self.assertFalse(self.html(contenido, otro).encontrado)

    def test_github_id_y_login_exacto(self):
        objetivo = Objetivo("GitHub", "ibai")
        for datos, esperado in (({"id": 1, "login": "ibai", "type": "User"}, True),
                                ({"id": 1, "login": "otro", "type": "User"}, False),
                                ({"login": "ibai", "type": "User"}, False),
                                ({"message": "API rate limit exceeded"}, False)):
            with self.subTest(datos=datos):
                self.assertEqual(validar_perfil(objetivo, ClienteFalso(json_respuesta(datos))).encontrado, esperado)

    def test_error_conexion_no_equivale_a_inexistencia(self):
        resultado = validar_perfil(self.instagram, ClienteFalso(ErrorRed("Tiempo agotado")))
        self.assertEqual(resultado.estado, "no_verificable")

    def test_json_invalido_o_formato_cambiado(self):
        for contenido in ('<html>Login</html>', '[]', '{"id":1,"login":null}', 'null'):
            resultado = validar_perfil(Objetivo("GitHub", "ibai"), ClienteFalso(Respuesta(200, "", contenido)))
            self.assertFalse(resultado.encontrado)

    def test_api_twitch(self):
        with patch.dict("os.environ", {"TWITCH_CLIENT_ID": "test", "TWITCH_ACCESS_TOKEN": "test"}):
            cliente = ClienteFalso(json_respuesta({"data": [{"id": "1", "login": "ibai"}]}))
            self.assertTrue(validar_perfil(Objetivo("Twitch", "ibai"), cliente).encontrado)
            cliente = ClienteFalso(json_respuesta({"data": []}))
            self.assertEqual(validar_perfil(Objetivo("Twitch", "ibai"), cliente).estado, "no_encontrado")

    def test_api_youtube_por_handle_y_canal(self):
        with patch.dict("os.environ", {"YOUTUBE_API_KEY": "test"}):
            for objetivo in (Objetivo("YouTube", "ibai"), Objetivo("YouTube", CANAL, "canal")):
                cliente = ClienteFalso(json_respuesta({"items": [{"id": CANAL, "snippet": {"customUrl": "@ibai"}}]}))
                self.assertTrue(validar_perfil(objetivo, cliente).encontrado)
                params = cliente.llamadas[0][1]["params"]
                self.assertIn("id" if objetivo.tipo == "canal" else "forHandle", params)


def declaracion(valor, **kwargs):
    return {"rank": "normal", "mainsnak": {"snaktype": "value", "datavalue": {"value": valor}}, **kwargs}


def entidad(nombre="Ibai Llanos", alias="ibai", cuenta="ibaillanos"):
    return {"labels": {"es": {"value": nombre}}, "aliases": {"es": [{"value": alias}]},
            "claims": {"P2003": [declaracion(cuenta)], "P5797": [declaracion("ibai")]}}


class DescubrimientoTests(unittest.TestCase):
    def cliente(self, entidades):
        def responder(url, **kwargs):
            self.assertEqual(url, API)
            datos = ({"search": [{"id": q} for q in entidades]} if kwargs["params"]["action"] == "wbsearchentities"
                     else {"entities": entidades})
            return json_respuesta(datos, API)
        return ClienteFalso(responder)

    def test_ibai_descubre_nombre_distinto_sin_hardcode(self):
        perfiles, avisos = descubrir_wikidata("ibai", self.cliente({"Q1": entidad()}))
        self.assertIn(Objetivo("Instagram", "ibaillanos"), [o for o, _ in perfiles])
        self.assertTrue(all(o.tipo == "wikidata" for _, o in perfiles))

    def test_reddit_no_se_interpreta_como_twitch(self):
        datos = entidad()
        datos["claims"]["P4265"] = [declaracion("usuario_reddit")]
        perfiles, _ = descubrir_wikidata("ibai", self.cliente({"Q1": datos}))
        self.assertEqual([o.usuario for o, _ in perfiles if o.sitio == "Twitch"], ["ibai"])

    def test_no_se_elige_la_primera_entidad_ambigua(self):
        perfiles, avisos = descubrir_wikidata("ibai", self.cliente({"Q1": entidad(), "Q2": entidad(cuenta="otra")}))
        self.assertEqual(perfiles, [])
        self.assertIn("ambigua", avisos[0])

    def test_coincidencia_parcial_no_atribuye_identidad(self):
        perfiles, _ = descubrir_wikidata("ibai", self.cliente({"Q1": entidad(alias="Ibai Llanos")}))
        self.assertEqual(perfiles, [])

    def test_referencia_distingue_homonimos(self):
        perfiles, _ = descubrir_wikidata("ibai", self.cliente({"Q1": entidad(), "Q2": entidad(cuenta="otra")}),
                                        {Objetivo("Instagram", "ibaillanos").clave})
        self.assertTrue(perfiles)
        self.assertTrue(all(o.url.endswith("Q1") for _, o in perfiles))

    def test_referencia_no_relacionada_no_mezcla_personas(self):
        perfiles, _ = descubrir_wikidata("ibai", self.cliente({"Q1": entidad()}),
                                        {Objetivo("GitHub", "ibai").clave})
        self.assertEqual(perfiles, [])

    def test_cuentas_antiguas_deprecated_y_sin_valor(self):
        datos = entidad()
        datos["claims"]["P2003"] = [declaracion("antigua", qualifiers={"P582": []}),
                                    declaracion("falsa", rank="deprecated"),
                                    {"mainsnak": {"snaktype": "novalue"}}]
        perfiles, _ = descubrir_wikidata("ibai", self.cliente({"Q1": datos}))
        self.assertFalse(any(o.sitio == "Instagram" for o, _ in perfiles))

    def test_error_200_de_api_no_es_lista_vacia_silenciosa(self):
        perfiles, avisos = descubrir_wikidata("ibai", ClienteFalso(json_respuesta({"error": {"code": "maxlag"}})))
        self.assertEqual(perfiles, [])
        self.assertIn("retrasado", avisos[0])


class MotorTests(unittest.TestCase):
    def validar(self, objetivo, cliente):
        return Resultado(objetivo, estado="encontrado")

    @patch("cerebro.validar_perfil")
    def test_coincidencias_exactas_nunca_se_atribuyen(self, validar):
        validar.side_effect = self.validar
        informe = buscar_perfiles("ibai", descubrir=False)
        self.assertEqual(len(informe.resultados), 6)
        self.assertTrue(all(r.identidad == "sin_confirmar" for r in informe.resultados))

    @patch("cerebro.validar_perfil")
    def test_enlace_fake_hacia_real_no_valida_fake(self, validar):
        def responder(objetivo, cliente):
            resultado = self.validar(objetivo, cliente)
            if objetivo.sitio == "GitHub":
                resultado.enlaces = ["https://www.twitch.tv/ibai"]
            return resultado
        validar.side_effect = responder
        informe = buscar_perfiles("ibai", referencia="https://www.twitch.tv/ibai", descubrir=False)
        github = next(r for r in informe.resultados if r.objetivo.sitio == "GitHub")
        self.assertEqual(github.identidad, "sin_confirmar")

    @patch("cerebro.validar_perfil")
    def test_enlaces_solo_un_salto_desde_referencia(self, validar):
        def responder(objetivo, cliente):
            resultado = self.validar(objetivo, cliente)
            if objetivo == Objetivo("GitHub", "ibai"):
                resultado.enlaces = ["https://www.instagram.com/ibaillanos", "https://evil.example/user"]
            if objetivo == Objetivo("Instagram", "ibaillanos"):
                resultado.enlaces = ["https://www.twitch.tv/cuenta_tercera"]
            return resultado
        validar.side_effect = responder
        informe = buscar_perfiles("ibai", referencia="https://github.com/ibai", descubrir=False)
        instagram = next(r for r in informe.resultados if r.objetivo.usuario == "ibaillanos")
        self.assertEqual(instagram.identidad, "enlazado")
        self.assertFalse(any(r.objetivo.usuario == "cuenta_tercera" for r in informe.resultados))

    @patch("cerebro.validar_perfil")
    def test_referencia_no_verificable_no_produce_enlaces(self, validar):
        validar.side_effect = lambda o, c: Resultado(o, enlaces=["https://x.com/otra"])
        informe = buscar_perfiles("ibai", referencia="https://github.com/ibai", descubrir=False)
        self.assertFalse(any(r.objetivo.usuario == "otra" for r in informe.resultados))

    @patch("cerebro.validar_perfil")
    def test_limite_deduplicacion_y_variantes(self, validar):
        validar.side_effect = self.validar
        informe = buscar_perfiles("ibai.llanos", aliases="ibai.llanos,ibai_llanos,ibai-llanos,ibai2,ibai3", descubrir=False)
        claves = [r.objetivo.clave for r in informe.resultados]
        self.assertEqual(len(claves), len(set(claves)))
        self.assertLessEqual(len(claves), 48)
        self.assertTrue(any(r.objetivo.usuario == "ibaillanos" for r in informe.resultados))

    @patch("cerebro.validar_perfil")
    def test_cancelacion_antes_de_empezar(self, validar):
        cancelar = Event()
        cancelar.set()
        informe = buscar_perfiles("ibai", cancelar=cancelar)
        validar.assert_not_called()
        self.assertEqual(informe.resultados, [])
        self.assertTrue(any("cancelada" in a for a in informe.avisos))

    @patch("cerebro.validar_perfil")
    def test_repetir_busqueda_no_acumula_resultados(self, validar):
        validar.side_effect = self.validar
        primero = buscar_perfiles("ibai", descubrir=False)
        segundo = buscar_perfiles("ibai", descubrir=False)
        self.assertEqual(len(primero.resultados), len(segundo.resultados))
        self.assertIsNot(primero.resultados, segundo.resultados)

    @patch("cerebro.descubrir_wikidata")
    @patch("cerebro.validar_perfil")
    def test_handle_y_channel_id_se_agrupan(self, validar, descubrir):
        descubrir.return_value = ([(Objetivo("YouTube", CANAL, "canal"), Origen("wikidata", "fuente"))], [])
        def responder(o, c):
            return Resultado(o, estado="encontrado", identificador=CANAL if o.sitio == "YouTube" else "")
        validar.side_effect = responder
        informe = buscar_perfiles("ibai")
        youtube = [r for r in informe.resultados if r.objetivo.sitio == "YouTube"]
        self.assertEqual(len(youtube), 1)
        self.assertEqual(youtube[0].identidad, "referencia_publica")


class EntradaTests(unittest.TestCase):
    def test_urls_con_dominios_parecidos_posts_y_rutas_no_perfil(self):
        for url in ("https://instagram.com.evil.test/ibai", "https://127.0.0.1/ibai",
                    "https://instagram.com@evil.test/ibai", "https://www.instagram.com/p/123",
                    "https://github.com/login", "https://youtube.com/watch?v=123",
                    "https://www.instagram.com/ibai%2Fotra", "https://www.instagram.com:999/ibai"):
            with self.subTest(url=url):
                self.assertIsNone(objetivo_desde_url(url))

    def test_url_de_perfil_se_usa_como_referencia(self):
        consulta, referencia, _ = preparar_busqueda("https://www.twitch.tv/ibai")
        self.assertEqual(consulta, "ibai")
        self.assertEqual(referencia, Objetivo("Twitch", "ibai"))

    def test_inyeccion_rutas_no_es_usuario(self):
        for usuario in ("../ibai", "ibai?admin=1", "", "@", "---"):
            with self.subTest(usuario=usuario), self.assertRaises(ValueError):
                preparar_busqueda(usuario)

    def test_youtube_ids_distinguen_mayusculas(self):
        self.assertNotEqual(Objetivo("YouTube", CANAL, "canal").clave,
                            Objetivo("YouTube", "UC" + "a" * 22, "canal").clave)

    def test_rechaza_destino_red_ajeno(self):
        with self.assertRaises(ErrorRed):
            ClienteHTTP().get("https://evil.test/ibai")


if __name__ == "__main__":
    unittest.main()
