import customtkinter as ctk
import threading
import webbrowser
from datetime import datetime
import pyperclip
from PIL import Image

import config
import cerebro
import reportes

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
        self.idioma = "es"
        self.usuario_actual = None

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.crear_sidebar()
        self.crear_pantallas()
        
        self.mostrar_pantalla("scanner")
        self.log_sistema("Sistema iniciado correctamente.")

    def crear_sidebar(self):
        self.sidebar = ctk.CTkFrame(self, width=90, corner_radius=0, fg_color=config.COLORES["fondo_sidebar"])
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        
        ctk.CTkLabel(self.sidebar, text="👁️", font=("Arial", 40)).pack(pady=(40, 30))

        self.btn_scanner = self.crear_boton_sidebar(config.TEXTOS[self.idioma]["nav_scanner"], "scanner")
        self.btn_historial = self.crear_boton_sidebar(config.TEXTOS[self.idioma]["nav_historial"], "historial")
        self.btn_logs = self.crear_boton_sidebar(config.TEXTOS[self.idioma]["nav_logs"], "logs")
        self.btn_ajustes = self.crear_boton_sidebar(config.TEXTOS[self.idioma]["nav_ajustes"], "ajustes")

        ctk.CTkLabel(self.sidebar, text="v1.1", text_color="gray").pack(side="bottom", pady=20)

    def crear_boton_sidebar(self, texto, nombre_pantalla):
        btn = ctk.CTkButton(self.sidebar, text=texto, fg_color="transparent", 
                            text_color="gray", hover_color=config.COLORES["fondo_card"],
                            font=("Roboto Medium", 13), width=90, height=45, anchor="w",
                            command=lambda: self.mostrar_pantalla(nombre_pantalla))
        btn.pack(pady=5, padx=5)
        return btn

    def crear_pantallas(self):
        self.contenedor_derecho = ctk.CTkFrame(self, fg_color="transparent")
        self.contenedor_derecho.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)

        # 1. ESCÁNER
        self.frame_scanner = ctk.CTkFrame(self.contenedor_derecho, fg_color="transparent")
        self.setup_scanner_ui(self.frame_scanner)
        self.frames["scanner"] = self.frame_scanner

        # 2. HISTORIAL
        self.frame_historial = ctk.CTkFrame(self.contenedor_derecho, fg_color="transparent")
        self.setup_historial_ui(self.frame_historial)
        self.frames["historial"] = self.frame_historial

        # 3. LOGS
        self.frame_logs = ctk.CTkFrame(self.contenedor_derecho, fg_color="transparent")
        self.setup_logs_ui(self.frame_logs)
        self.frames["logs"] = self.frame_logs
        
        # 4. AJUSTES
        self.frame_ajustes = ctk.CTkFrame(self.contenedor_derecho, fg_color="transparent")
        self.setup_ajustes_ui(self.frame_ajustes)
        self.frames["ajustes"] = self.frame_ajustes

    def mostrar_pantalla(self, nombre):
        for frame in self.frames.values(): frame.pack_forget()
        
        self.btn_scanner.configure(text_color="gray")
        self.btn_historial.configure(text_color="gray")
        self.btn_logs.configure(text_color="gray")
        self.btn_ajustes.configure(text_color="gray")

        if nombre == "scanner": self.btn_scanner.configure(text_color=config.COLORES["acento"])
        elif nombre == "historial": self.btn_historial.configure(text_color=config.COLORES["acento"])
        elif nombre == "logs": self.btn_logs.configure(text_color=config.COLORES["acento"])
        elif nombre == "ajustes": self.btn_ajustes.configure(text_color=config.COLORES["acento"])
        
        self.frames[nombre].pack(fill="both", expand=True)
        if nombre == "historial": self.cargar_historial_visual()

    def setup_ajustes_ui(self, parent):
        self.lbl_titulo_ajustes = ctk.CTkLabel(parent, text=config.TEXTOS[self.idioma]["titulo_ajustes"], font=("Roboto", 26, "bold"), text_color="white")
        self.lbl_titulo_ajustes.pack(anchor="w", pady=(0, 20))

        frame_idioma = ctk.CTkFrame(parent, fg_color=config.COLORES["fondo_card"], corner_radius=10)
        frame_idioma.pack(fill="x", pady=10, padx=5)

        self.lbl_sel_idioma = ctk.CTkLabel(frame_idioma, text=config.TEXTOS[self.idioma]["lbl_idioma"], font=("Roboto", 14), text_color="white")
        self.lbl_sel_idioma.pack(side="left", padx=20, pady=20)

        self.combo_idioma = ctk.CTkOptionMenu(frame_idioma, values=["Español", "English"],
                                              fg_color=config.COLORES["acento"], text_color="black",
                                              button_color=config.COLORES["acento_hover"],
                                              command=self.cambiar_idioma)
        self.combo_idioma.pack(side="right", padx=20, pady=20)
        self.combo_idioma.set("Español")

    def cambiar_idioma(self, seleccion):
        self.idioma = "es" if seleccion == "Español" else "en"
        txt = config.TEXTOS[self.idioma]

        # Actualizar Sidebar
        self.btn_scanner.configure(text=txt["nav_scanner"])
        self.btn_historial.configure(text=txt["nav_historial"])
        self.btn_logs.configure(text=txt["nav_logs"])
        self.btn_ajustes.configure(text=txt["nav_ajustes"])

        # Actualizar Títulos (incluyendo Logs)
        self.lbl_titulo_scan.configure(text=txt["titulo_dashboard"])
        self.lbl_titulo_hist.configure(text=txt["titulo_historial"])
        self.lbl_titulo_logs.configure(text=txt["titulo_logs"]) 
        self.lbl_titulo_ajustes.configure(text=txt["titulo_ajustes"])
        
        # Actualizar Resto
        self.entrada_usuario.configure(placeholder_text=txt["placeholder"])
        self.btn_main_scan.configure(text=txt["btn_rastrear"])
        self.btn_exportar.configure(text=txt["btn_exportar"])
        self.lbl_col_plat.configure(text=txt["col_plataforma"])
        self.lbl_col_link.configure(text=txt["col_enlace"])
        self.lbl_sel_idioma.configure(text=txt["lbl_idioma"])
        
        self.log_sistema(f"{txt['log_cambio']} {self.idioma.upper()}")

    def setup_logs_ui(self, parent):
        self.lbl_titulo_logs = ctk.CTkLabel(parent, text=config.TEXTOS[self.idioma]["titulo_logs"], font=("Roboto", 26, "bold"), text_color="white")
        self.lbl_titulo_logs.pack(anchor="w", pady=(0, 20))
        
        self.caja_logs = ctk.CTkTextbox(parent, font=("Consolas", 12), text_color="#00ff00", fg_color="black")
        self.caja_logs.pack(fill="both", expand=True)
        self.caja_logs.insert("0.0", "--- INICIANDO USERSCOPE KERNEL ---\n")
        self.caja_logs.configure(state="disabled")

    def log_sistema(self, mensaje):
        hora = datetime.now().strftime("%H:%M:%S")
        texto_final = f"[{hora}] > {mensaje}\n"
        
        self.caja_logs.configure(state="normal")
        self.caja_logs.insert("end", texto_final)
        self.caja_logs.see("end")
        self.caja_logs.configure(state="disabled")

    def setup_scanner_ui(self, parent):
        self.lbl_titulo_scan = ctk.CTkLabel(parent, text=config.TEXTOS[self.idioma]["titulo_dashboard"], font=("Roboto", 26, "bold"), text_color="white")
        self.lbl_titulo_scan.pack(anchor="w", pady=(0, 20))
        
        search_cont = ctk.CTkFrame(parent, fg_color="transparent")
        search_cont.pack(fill="x", pady=5)
        
        self.entrada_usuario = ctk.CTkEntry(search_cont, placeholder_text=config.TEXTOS[self.idioma]["placeholder"], height=50, font=("Roboto", 16),
                                            corner_radius=25, fg_color=config.COLORES["fondo_card"], 
                                            border_color=config.COLORES["borde"], text_color="white")
        self.entrada_usuario.pack(side="left", fill="x", expand=True, padx=(0, 15))
        
        self.btn_main_scan = ctk.CTkButton(search_cont, text=config.TEXTOS[self.idioma]["btn_rastrear"], font=("Roboto", 12, "bold"), height=50, width=140, corner_radius=25,
                    fg_color=config.COLORES["acento"], text_color="black", hover_color=config.COLORES["acento_hover"],
                    command=self.iniciar_busqueda)
        self.btn_main_scan.pack(side="right")

        self.btn_exportar = ctk.CTkButton(search_cont, text=config.TEXTOS[self.idioma]["btn_exportar"], font=("Roboto", 12, "bold"), height=50, width=120, corner_radius=25,
                    fg_color="transparent", border_width=2, border_color=config.COLORES["acento"], text_color=config.COLORES["acento"],
                    command=self.exportar_reporte)
        self.btn_exportar.pack(side="right", padx=(0, 10))
        self.btn_exportar.configure(state="disabled")

        self.barra = ctk.CTkProgressBar(parent, height=4, progress_color=config.COLORES["acento"])
        self.barra.set(0)
        self.barra.pack(fill="x", pady=(15, 5))
        self.barra.pack_forget()

        self.lbl_estado = ctk.CTkLabel(parent, text="", text_color="gray", font=("Roboto", 12))
        self.lbl_estado.pack(anchor="w")

        header_frame = ctk.CTkFrame(parent, fg_color="transparent")
        header_frame.pack(fill="x", pady=(10,0))
        self.lbl_col_plat = ctk.CTkLabel(header_frame, text=config.TEXTOS[self.idioma]["col_plataforma"], width=150, anchor="w", text_color="gray", font=("Roboto", 11, "bold"))
        self.lbl_col_plat.pack(side="left", padx=10)
        self.lbl_col_link = ctk.CTkLabel(header_frame, text=config.TEXTOS[self.idioma]["col_enlace"], anchor="w", text_color="gray", font=("Roboto", 11, "bold"))
        self.lbl_col_link.pack(side="left", padx=10)

        self.scroll_resultados = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        self.scroll_resultados.pack(fill="both", expand=True, pady=10)

    def setup_historial_ui(self, parent):
        self.lbl_titulo_hist = ctk.CTkLabel(parent, text=config.TEXTOS[self.idioma]["titulo_historial"], font=("Roboto", 26, "bold"), text_color="white")
        self.lbl_titulo_hist.pack(anchor="w", pady=(0, 20))
        self.scroll_historial = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        self.scroll_historial.pack(fill="both", expand=True)

    def iniciar_busqueda(self):
        usuario = self.entrada_usuario.get()
        if not usuario: return
        self.usuario_actual = usuario
        self.btn_exportar.configure(state="disabled")
        for w in self.scroll_resultados.winfo_children(): w.destroy()
        
        self.barra.pack(fill="x", pady=(15, 5))
        self.barra.start()
        
        # Logs traducidos
        txt_inicio = config.TEXTOS[self.idioma]["log_inicio"]
        self.log_sistema(f"{txt_inicio} {usuario}") 
        
        if usuario not in self.datos_guardados:
            self.datos_guardados[usuario] = {"fecha": datetime.now().strftime("%H:%M"), "resultados": []}
            
        threading.Thread(target=self.ejecutar_escaneo, args=(usuario,)).start()

    def ejecutar_escaneo(self, usuario):
        count = 0
        total = len(config.SITIOS)
        self.datos_guardados[usuario]["resultados"] = []

        for nombre, url in config.SITIOS.items():
            self.lbl_estado.configure(text=f"Analizando: {nombre}...")
            
            res = cerebro.escanear_sitio(nombre, url, usuario, idioma=self.idioma, callback=self.log_sistema)
            
            if res:
                self.datos_guardados[usuario]["resultados"].append(res)
                self.crear_fila_resultado(res, self.scroll_resultados)
            
            count += 1
            self.barra.set(count / total)

        txt_final = config.TEXTOS[self.idioma]["msg_finalizado"]
        txt_encontrados = config.TEXTOS[self.idioma]["msg_encontrados"]
        
        self.lbl_estado.configure(text=txt_final, text_color=config.COLORES["acento"])
        self.log_sistema(f"{txt_encontrados} {len(self.datos_guardados[usuario]['resultados'])}")
        self.barra.stop()
        self.btn_exportar.configure(state="normal")
                
    def exportar_reporte(self):
        if not self.usuario_actual or self.usuario_actual not in self.datos_guardados:
            return
        resultados = self.datos_guardados[self.usuario_actual]["resultados"]
        txt_ok = config.TEXTOS[self.idioma]["log_reporte_ok"]
        txt_err = config.TEXTOS[self.idioma]["log_reporte_err"]

        exito, ruta = reportes.generar_html(self.usuario_actual, resultados)
        
        if exito:
            self.log_sistema(f"{txt_ok} {ruta}")
        else:
            self.log_sistema(f"{txt_err} {ruta}")
            
    def crear_fila_resultado(self, datos, contenedor):
        fila = ctk.CTkFrame(contenedor, fg_color=config.COLORES["fondo_card"], corner_radius=8, height=60)
        fila.pack(fill="x", pady=4)

        if datos.get("logo_plataforma"):
            lbl_logo = ctk.CTkLabel(fila, image=datos["logo_plataforma"], text="")
            lbl_logo.pack(side="left", padx=(15, 5))
            lbl_logo.image = datos["logo_plataforma"]
        else:
            ctk.CTkLabel(fila, text="🌐", font=("Arial", 20)).pack(side="left", padx=15)

        ctk.CTkLabel(fila, text=datos["sitio"], font=("Roboto", 14, "bold"), text_color="white", width=120, anchor="w").pack(side="left")

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