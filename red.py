"""HTTP limitado a los proveedores, con límites de tamaño, tiempo y redirecciones."""

from collections import defaultdict
from dataclasses import dataclass
import json
from threading import Event, Lock
from urllib.parse import urljoin, urlsplit

import requests

from config import TIMEOUT, USER_AGENT
from perfiles import DOMINIOS


class ErrorRed(Exception):
    pass


@dataclass
class Respuesta:
    status_code: int
    url: str
    text: str = ""

    def json(self):
        return json.loads(self.text)


class ClienteHTTP:
    def __init__(self, cancelar=None):
        self._locks = defaultdict(Lock)
        self._lock = Lock()
        self._bloqueados = {}
        self.cancelar = cancelar or Event()

    def get(self, url, *, params=None, headers=None):
        host = urlsplit(url).hostname
        permitidos = set(DOMINIOS) | {"www." + h for h in DOMINIOS} | {
            "api.github.com", "api.twitch.tv", "www.googleapis.com", "www.wikidata.org",
        }
        if host not in permitidos or urlsplit(url).scheme != "https":
            raise ErrorRed("Destino no admitido.")
        with self._lock:
            candado = self._locks[host]
        with candado:
            if self.cancelar.is_set():
                raise ErrorRed("Consulta cancelada.")
            if host in self._bloqueados:
                return Respuesta(self._bloqueados[host], url)
            cabeceras = {"User-Agent": USER_AGENT, **(headers or {})}
            try:
                for _ in range(4):
                    if self.cancelar.is_set():
                        raise ErrorRed("Consulta cancelada.")
                    with requests.get(url, params=params, headers=cabeceras, timeout=TIMEOUT,
                                      allow_redirects=False, stream=True) as respuesta:
                        if respuesta.status_code in (301, 302, 303, 307, 308):
                            destino = urljoin(url, respuesta.headers.get("Location", ""))
                            partes = urlsplit(destino)
                            # Las credenciales nunca se reenvían a otro host.
                            hosts = {host}
                            if host in {"twitter.com", "www.twitter.com", "x.com", "www.x.com"}:
                                hosts |= {"twitter.com", "www.twitter.com", "x.com", "www.x.com"}
                            if (partes.scheme != "https" or partes.hostname not in hosts
                                    or partes.username or partes.password or partes.port not in (None, 443)):
                                raise ErrorRed("Redirección externa o insegura; no se pudo validar.")
                            url, params = destino, None
                            continue
                        if respuesta.status_code in (401, 403, 429):
                            self._bloqueados[host] = respuesta.status_code
                        contenido = bytearray()
                        for bloque in respuesta.iter_content(65536):
                            contenido.extend(bloque)
                            if len(contenido) > 5_000_000:
                                raise ErrorRed("La respuesta supera el límite de tamaño.")
                        return Respuesta(respuesta.status_code, respuesta.url,
                                         contenido.decode("utf-8", errors="replace"))
                raise ErrorRed("Demasiadas redirecciones.")
            except requests.RequestException as exc:
                # No mostrar URLs de excepciones: pueden incluir claves de API.
                raise ErrorRed("Error de conexión o tiempo de espera agotado.") from exc
