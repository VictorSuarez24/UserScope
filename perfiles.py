"""Identificadores, procedencia y resultados. Sin dependencias de la interfaz."""

from dataclasses import dataclass, field
import re
import unicodedata
from urllib.parse import quote, unquote, urlsplit

from config import SITIOS


DOMINIOS = {
    "github.com": "GitHub",
    "instagram.com": "Instagram",
    "twitter.com": "Twitter/X",
    "x.com": "Twitter/X",
    "facebook.com": "Facebook",
    "youtube.com": "YouTube",
    "twitch.tv": "Twitch",
}
RESERVADOS = {
    "login", "signin", "signup", "accounts", "explore", "search", "home",
    "intent", "share", "sharer.php", "watch", "feed", "results", "privacy",
    "help", "about", "settings", "i", "p", "reel", "reels", "stories",
    "directory", "downloads", "features", "marketplace", "topics", "orgs",
}


@dataclass(frozen=True)
class Objetivo:
    sitio: str
    usuario: str
    tipo: str = "usuario"

    @property
    def url(self):
        usuario = quote(self.usuario, safe="._-")
        if self.sitio == "YouTube" and self.tipo == "canal":
            return f"https://www.youtube.com/channel/{usuario}"
        return SITIOS[self.sitio].format(usuario)

    @property
    def clave(self):
        # Los IDs de canal de YouTube distinguen mayúsculas.
        usuario = self.usuario if self.tipo == "canal" else self.usuario.casefold()
        return self.sitio, self.tipo, usuario


def crear_objetivo(sitio, usuario, tipo="usuario"):
    if not isinstance(usuario, str) or sitio not in SITIOS:
        return None
    usuario = usuario.strip().removeprefix("@")
    if not usuario or usuario.casefold() in RESERVADOS:
        return None
    patrones = {
        "GitHub": r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?",
        "Instagram": r"[A-Za-z0-9._]{1,30}",
        "Twitter/X": r"[A-Za-z0-9_]{1,15}",
        "Facebook": r"[A-Za-z0-9.]{1,50}",
        "Twitch": r"[A-Za-z0-9_]{1,25}",
        "YouTube": r"[\w.\-·]{3,30}",
    }
    if tipo == "canal":
        valido = sitio == "YouTube" and re.fullmatch(r"UC[A-Za-z0-9_-]{22}", usuario)
    else:
        valido = tipo == "usuario" and re.fullmatch(patrones[sitio], usuario)
    return Objetivo(sitio, usuario, tipo) if valido else None


def objetivo_desde_url(url):
    """Solo URLs de perfiles en plataformas admitidas; nunca posts ni dominios parecidos."""
    if not isinstance(url, str) or len(url) > 2048:
        return None
    try:
        partes = urlsplit(url.strip())
        if partes.scheme not in ("http", "https") or partes.username or partes.password:
            return None
        if partes.port not in (None, 80, 443):
            return None
        host = (partes.hostname or "").removeprefix("www.")
        sitio = DOMINIOS.get(host)
        if not sitio:
            return None
        ruta = unquote(partes.path).strip("/").split("/")
        if sitio == "YouTube":
            if len(ruta) == 2 and ruta[0] == "channel":
                return crear_objetivo(sitio, ruta[1], "canal")
            if len(ruta) != 1 or not ruta[0].startswith("@"):
                return None
        elif len(ruta) != 1:
            return None
        return crear_objetivo(sitio, ruta[0])
    except ValueError:
        return None


def normalizar_nombre(texto):
    texto = unicodedata.normalize("NFKD", texto.casefold().strip().removeprefix("@"))
    return " ".join("".join(c for c in texto if not unicodedata.combining(c)).split())


def variantes_usuario(usuario):
    """Variaciones acotadas de separadores; sin inventar sufijos como 'official'."""
    partes = [p for p in re.split(r"[\s._-]+", usuario.strip().removeprefix("@")) if p]
    if len(partes) < 2:
        return []
    return list(dict.fromkeys("".join(partes) if not sep else sep.join(partes)
                              for sep in ("", "_", ".")))[:3]


@dataclass(frozen=True)
class Origen:
    tipo: str
    detalle: str
    url: str = ""


@dataclass
class Resultado:
    objetivo: Objetivo
    estado: str = "no_verificable"
    nombre: str = ""
    descripcion: str = ""
    foto_url: str = ""
    identificador: str = ""
    evidencias: list[str] = field(default_factory=list)
    origenes: list[Origen] = field(default_factory=list)
    enlaces: list[str] = field(default_factory=list)
    identidad: str = "sin_confirmar"

    @property
    def encontrado(self):
        return self.estado == "encontrado"


@dataclass
class Informe:
    consulta: str
    resultados: list[Resultado] = field(default_factory=list)
    avisos: list[str] = field(default_factory=list)
