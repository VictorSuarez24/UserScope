# --- NOVEDADES v1.3 ---
# 1. Separación de errores FUERTES (ignoran longitud) y LEVES (miran longitud).
# 2. Chequeo específico del TÍTULO de la web (Steam suele poner "Error" en el título).
# 3. Headers más completos para simular un navegador real.
# ----------------------

import requests
from bs4 import BeautifulSoup
from PIL import Image
from io import BytesIO
import customtkinter as ctk
import random
import config 

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15"
]

def obtener_logo_plataforma(url_base):
    try:
        dominio = url_base.split("/")[2]
        api_url = f"https://www.google.com/s2/favicons?domain={dominio}&sz=64"
        resp = requests.get(api_url, timeout=2)
        if resp.status_code == 200:
            img_bytes = BytesIO(resp.content)
            pil_img = Image.open(img_bytes)
            return ctk.CTkImage(light_image=pil_img, size=(30, 30))
    except:
        return None
    return None

def escanear_sitio(nombre_sitio, url_base, usuario, idioma="es", callback=None):
    url_final = url_base.format(usuario)
    
    # Cargamos textos del idioma seleccionado
    try:
        txt = config.TEXTOS[idioma]
    except:
        txt = config.TEXTOS["es"]

    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
    }
    
    errores_fuertes = [
        "no se ha encontrado el perfil especificado", 
        "specified profile could not be found",
        "this page isn't available", 
        "esta página no está disponible",
        "content unavailable",
        "contenido no disponible",
        "user not found",
        "usuario no encontrado",
        "account suspended",
        "cuenta suspendida"
    ]
    errores_leves = [
        "page not found", "not found", "doesn't exist",
        "404", "error", "login", "sign up", "registrarse"
    ]
    
    try:
        if callback: callback(f"[INFO] {txt['log_conectando']} {nombre_sitio}...") 
        respuesta = requests.get(url_final, headers=headers, timeout=5)
        
        # Forzar UTF-8 para leer tildes
        respuesta.encoding = 'utf-8' 
        
        if respuesta.status_code == 200:
            contenido_texto = respuesta.text.lower()
            soup = BeautifulSoup(respuesta.text, "html.parser")
            
            if soup.title:
                titulo = soup.title.string.lower()
                if "error" in titulo or "not found" in titulo:
                     if callback: callback(f"[WARN] {nombre_sitio}: {txt['log_falso']} (Title Detect).")
                     return None
            for error in errores_fuertes:
                if error in contenido_texto:
                    if callback: callback(f"[WARN] {nombre_sitio}: {txt['log_falso']} ('{error}').")
                    return None
            for error in errores_leves:
                if error in contenido_texto:
                    if len(contenido_texto) < 150000: 
                        if callback: callback(f"[WARN] {nombre_sitio}: {txt['log_falso']} ('{error}' size check).")
                        return None

            imagen_usuario = None
            try:
                meta_foto = soup.find("meta", property="og:image")
                if meta_foto:
                    if callback: callback(f"[IMG] {nombre_sitio}: {txt['log_foto']}")
                    url_foto = meta_foto["content"]
                    resp_foto = requests.get(url_foto, headers=headers, timeout=3)
                    img_memoria = BytesIO(resp_foto.content)
                    pil_img = Image.open(img_memoria)
                    imagen_usuario = ctk.CTkImage(light_image=pil_img, size=(50, 50))
            except Exception as e:
                pass

            logo_plat = obtener_logo_plataforma(url_base)

            if callback: callback(f"[SUCCESS] {nombre_sitio}: {txt['log_encontrado']}")
            return {
                "sitio": nombre_sitio,
                "url": url_final,
                "imagen_usuario": imagen_usuario,
                "logo_plataforma": logo_plat,
                "encontrado": True
            }
        else:
            if callback: callback(f"[FAIL] {nombre_sitio}: Status {respuesta.status_code}")
            
    except Exception as e:
        if callback: callback(f"[ERR] {nombre_sitio}: {txt['log_error_red']} {e}")
    
    return None