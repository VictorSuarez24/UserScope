import customtkinter as ctk
import threading
import webbrowser
from datetime import datetime
import pyperclip
from PIL import Image

import config
import cerebro

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")

class UserScopeApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.configure(fg_color=config.COLORES["fondo_main"])
        self.title("UserScope Pro - Dashboard")
        self.geometry("1000x700")

        self.datos_guardados = {}
        self.frames = {}

        # Grid Layout Principal
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.crear_sidebar()
        self.crear_pantallas()
        
        # Mostrar Escáner por defecto
        self.mostrar_pantalla("scanner")

    def crear_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, width=90, corner_radius=0, fg_color=config.COLORES["fondo_sidebar"])
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        
        ctk.CTkLabel(self.sidebar, text="👁️", font=("Arial", 40)).pack(pady=(40, 30))

        # Botones de Navegación con Lógica
        self.btn_scanner = self.crear_boton_sidebar("Rastreador", "scanner")
        self.btn_historial = self.crear_boton_sidebar("Historial", "historial")

        ctk.CTkLabel(self.sidebar, text="v1.01", text_color="gray").pack(side="bottom", pady=20)

    def crear_boton_sidebar(self, texto, nombre_pantalla):
        btn = ctk.CTkButton(self.sidebar, text=texto, fg_color="transparent", 
                            text_color="gray", hover_color=config.COLORES["fondo_card"],
                            font=("Roboto Medium", 13), width=90, height=45, anchor="w",
                            command=lambda: self.mostrar_pantalla(nombre_pantalla))
        btn.pack(pady=5, padx=5)
        return btn

    def crear_pantallas(self):
        # Contenedor derecho
        self.contenedor_derecho = ctk.CTkFrame(self, fg_color="transparent")
        self.contenedor_derecho.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)

        # --- PANTALLA 1: ESCÁNER ---
        self.frame_scanner = ctk.CTkFrame(self.contenedor_derecho, fg_color="transparent")
        self.setup_scanner_ui(self.frame_scanner)
        self.frames["scanner"] = self.frame_scanner

        # --- PANTALLA 2: HISTORIAL ---
        self.frame_historial = ctk.CTkFrame(self.contenedor_derecho, fg_color="transparent")
        self.setup_historial_ui(self.frame_historial)
        self.frames["historial"] = self.frame_historial

    def mostrar_pantalla(self, nombre):
        for frame in self.frames.values():
            frame.pack_forget()
        
        if nombre == "scanner":
            self.btn_scanner.configure(text_color=config.COLORES["acento"])
            self.btn_historial.configure(text_color="gray")
        else:
            self.btn_scanner.configure(text_color="gray")
            self.btn_historial.configure(text_color=config.COLORES["acento"])

        # Mostrar la elegida
        self.frames[nombre].pack(fill="both", expand=True)

        if nombre == "historial":
            self.cargar_historial_visual()

    # ================= UI ESCÁNER =================
    def setup_scanner_ui(self, parent):
        ctk.CTkLabel(parent, text="Dashboard", font=("Roboto", 26, "bold"), text_color="white").pack(anchor="w", pady=(0, 20))

        # Buscador
        search_cont = ctk.CTkFrame(parent, fg_color="transparent")
        search_cont.pack(fill="x", pady=5)
        
        self.entrada_usuario = ctk.CTkEntry(search_cont, placeholder_text="Username...", height=50, font=("Roboto", 16),
                                            corner_radius=25, fg_color=config.COLORES["fondo_card"], 
                                            border_color=config.COLORES["borde"], text_color="white")
        self.entrada_usuario.pack(side="left", fill="x", expand=True, padx=(0, 15))
        
        ctk.CTkButton(search_cont, text="RASTREAR", font=("Roboto", 12, "bold"), height=50, width=140, corner_radius=25,
                      fg_color=config.COLORES["acento"], text_color="black", hover_color=config.COLORES["acento_hover"],
                      command=self.iniciar_busqueda).pack(side="right")

        self.barra = ctk.CTkProgressBar(parent, height=4, progress_color=config.COLORES["acento"])
        self.barra.set(0)
        self.barra.pack(fill="x", pady=(15, 5))
        self.barra.pack_forget()

        self.lbl_estado = ctk.CTkLabel(parent, text="", text_color="gray", font=("Roboto", 12))
        self.lbl_estado.pack(anchor="w")

        # Tabla Resultados
        self.scroll_resultados = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        self.scroll_resultados.pack(fill="both", expand=True, pady=10)

    # ================= UI HISTORIAL =================
    def setup_historial_ui(self, parent):
        ctk.CTkLabel(parent, text="Historial de Sesión", font=("Roboto", 26, "bold"), text_color="white").pack(anchor="w", pady=(0, 20))
        self.scroll_historial = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        self.scroll_historial.pack(fill="both", expand=True)

    # ================= LÓGICA =================
    def iniciar_busqueda(self):
        usuario = self.entrada_usuario.get()
        if not usuario: return
        
        for w in self.scroll_resultados.winfo_children(): w.destroy()
        
        self.barra.pack(fill="x", pady=(15, 5))
        self.barra.start()
        
        # Guardamos la fecha de la búsqueda
        if usuario not in self.datos_guardados:
            self.datos_guardados[usuario] = {"fecha": datetime.now().strftime("%H:%M"), "resultados": []}
            
        threading.Thread(target=self.ejecutar_escaneo, args=(usuario,)).start()

    def ejecutar_escaneo(self, usuario):
        count = 0
        total = len(config.SITIOS)
        self.datos_guardados[usuario]["resultados"] = []

        for nombre, url in config.SITIOS.items():
            self.lbl_estado.configure(text=f"Analizando: {nombre}...")
            res = cerebro.escanear_sitio(nombre, url, usuario)
            
            if res:
                self.datos_guardados[usuario]["resultados"].append(res)
                self.crear_fila_resultado(res, self.scroll_resultados)
            
            count += 1
            self.barra.set(count / total)

        self.lbl_estado.configure(text="Finalizado.", text_color=config.COLORES["acento"])
        self.barra.stop()

    def crear_fila_resultado(self, datos, contenedor):
        fila = ctk.CTkFrame(contenedor, fg_color=config.COLORES["fondo_card"], corner_radius=8, height=60)
        fila.pack(fill="x", pady=4)

        # 1. Logo Plataforma
        if datos.get("logo_plataforma"):
            lbl_logo = ctk.CTkLabel(fila, image=datos["logo_plataforma"], text="")
            lbl_logo.pack(side="left", padx=(15, 5))
            lbl_logo.image = datos["logo_plataforma"]
        else:
            ctk.CTkLabel(fila, text="🌐", font=("Arial", 20)).pack(side="left", padx=15)

        # 2. Nombre Sitio
        ctk.CTkLabel(fila, text=datos["sitio"], font=("Roboto", 14, "bold"), text_color="white", width=120, anchor="w").pack(side="left")

        # 3. Avatar Usuario
        if datos.get("imagen_usuario"):
             img_u = ctk.CTkLabel(fila, image=datos["imagen_usuario"], text="")
             img_u.pack(side="left", padx=10)
             img_u.image = datos["imagen_usuario"]

        url_c = (datos["url"][:40] + '...') if len(datos["url"]) > 40 else datos["url"]
        ctk.CTkLabel(fila, text=url_c, font=("Roboto", 12), text_color="gray").pack(side="left", padx=10)

        ctk.CTkButton(fila, text="📋", width=40, fg_color="#333", hover_color="#444", 
                      command=lambda: pyperclip.copy(datos["url"])).pack(side="right", padx=10)
        ctk.CTkButton(fila, text="↗", width=40, fg_color=config.COLORES["acento"], text_color="black", 
                      command=lambda: webbrowser.open(datos["url"])).pack(side="right", padx=5)

    def cargar_historial_visual(self):
        for w in self.scroll_historial.winfo_children(): w.destroy()
        
        if not self.datos_guardados:
            ctk.CTkLabel(self.scroll_historial, text="No hay búsquedas recientes.", text_color="gray").pack(pady=20)
            return

        for user, data in self.datos_guardados.items():
            card = ctk.CTkFrame(self.scroll_historial, fg_color=config.COLORES["fondo_card"])
            card.pack(fill="x", pady=5)
            
            ctk.CTkLabel(card, text=f"👤 {user.upper()}", font=("Roboto", 16, "bold"), text_color="white").pack(side="left", padx=15, pady=15)
            ctk.CTkLabel(card, text=f"Hora: {data['fecha']}", text_color="gray").pack(side="left", padx=10)
            ctk.CTkLabel(card, text=f"Encontrados: {len(data['resultados'])}", text_color=config.COLORES["acento"]).pack(side="left", padx=10)
            
if __name__ == "__main__":
    app = UserScopeApp()
    app.mainloop()