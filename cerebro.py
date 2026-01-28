import requests
from bs4 import BeautifulSoup
from PIL import Image
from io import BytesIO
import customtkinter as ctk
import random

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15"
]

def obtener_logo_plataforma(url_base):
    try:
        # Extraer el dominio
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

def escanear_sitio(nombre_sitio, url_base, usuario):
    url_final = url_base.format(usuario)
    
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept-Language": "en-US,en;q=0.9"
    }
    
    # --- PALABRAS CLAVE DE ERROR ---
    errores_comunes = [
        "page not found", "not found", "doesn't exist", "no existe", 
        "página no encontrada", "user not found", "login", "sign up"
    ]
    
    try:
        respuesta = requests.get(url_final, headers=headers, timeout=5)
        
        if respuesta.status_code == 200:
            
            contenido_texto = respuesta.text.lower()
            for error in errores_comunes:
                if error in contenido_texto and len(contenido_texto) < 5000: 
                    return None

            imagen_usuario = None
            try:
                soup = BeautifulSoup(respuesta.text, "html.parser")
                meta_foto = soup.find("meta", property="og:image")
                if meta_foto:
                    url_foto = meta_foto["content"]
                    resp_foto = requests.get(url_foto, headers=headers, timeout=3)
                    img_memoria = BytesIO(resp_foto.content)
                    pil_img = Image.open(img_memoria)
                    imagen_usuario = ctk.CTkImage(light_image=pil_img, size=(50, 50))
            except:
                pass

            logo_plat = obtener_logo_plataforma(url_base)

            return {
                "sitio": nombre_sitio,
                "url": url_final,
                "imagen_usuario": imagen_usuario,
                "logo_plataforma": logo_plat,
                "encontrado": True
            }
            
    except:
        pass
    
    return None