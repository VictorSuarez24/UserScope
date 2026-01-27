import requests
from bs4 import BeautifulSoup
from PIL import Image
from io import BytesIO
import customtkinter as ctk

def escanear_sitio(nombre_sitio, url_base, usuario):

    url_final = url_base.format(usuario)
    
    try:
        respuesta = requests.get(url_final, timeout=5)
        
        if respuesta.status_code == 200:
            imagen_final = None
            try:
                soup = BeautifulSoup(respuesta.text, "html.parser")
                meta_foto = soup.find("meta", property="og:image")
                
                if meta_foto:
                    url_foto = meta_foto["content"]
                    resp_foto = requests.get(url_foto, timeout=5)
                    img_memoria = BytesIO(resp_foto.content)
                    pil_img = Image.open(img_memoria)
                    imagen_final = ctk.CTkImage(light_image=pil_img, size=(70, 70))
            except:
                pass
            return {
                "sitio": nombre_sitio,
                "url": url_final,
                "imagen": imagen_final,
                "encontrado": True
            }
            
    except Exception as e:
        print(f"Error conectando con {nombre_sitio}: {e}")
    
    return None