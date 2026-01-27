import customtkinter as ctk
import threading
import webbrowser
from datetime import datetime
import config
import cerebro

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")

class UserScopeApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.configure(fg_color=config.COLORES["fondo_main"])
        self.title("UserScope - Digital Identity Analyzer")
        self.geometry("700x650")

        self.datos_guardados = {}
        
        self.vista_pestañas = ctk.CTkTabview(self, 
                                             fg_color=config.COLORES["fondo_main"],
                                             segmented_button_fg_color=config.COLORES["fondo_card"],
                                             segmented_button_selected_color=config.COLORES["acento"],
                                             segmented_button_unselected_color=config.COLORES["fondo_main"],
                                             text_color=config.COLORES["texto_titulos"])
        self.vista_pestañas.pack(fill="both", expand=True, padx=20, pady=20)
        self.tab_scanner = self.vista_pestañas.add("🔍 ESCÁNER")
        self.tab_historial = self.vista_pestañas.add("📜 HISTORIAL")
        self.setup_ui_scanner()   
        self.setup_ui_historial() 

    def setup_ui_scanner(self):
        self.contenedor_scanner = ctk.CTkFrame(self.tab_scanner, fg_color="transparent")
        self.contenedor_scanner.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.titulo = ctk.CTkLabel(self.contenedor_scanner, 
                                   text="USERSCOPE", 
                                   font=("Roboto Medium", 24),
                                   text_color=config.COLORES["acento"])
        self.titulo.pack(pady=(10, 5))

        self.subtitulo = ctk.CTkLabel(self.contenedor_scanner, text="Intelligence & Analysis Tool", font=("Roboto", 12), text_color="gray")
        self.subtitulo.pack(pady=(0, 20))
        
        self.entrada_usuario = ctk.CTkEntry(self.contenedor_scanner, 
                                            placeholder_text="Identificador de objetivo...", 
                                            width=350, height=40, font=("Roboto", 14),
                                            fg_color=config.COLORES["fondo_card"],
                                            border_color=config.COLORES["borde"])
        self.entrada_usuario.pack(pady=5)
        
        self.boton = ctk.CTkButton(self.contenedor_scanner, 
                                   text="INICIAR RASTREO",
                                   font=("Roboto", 14, "bold"), height=45,
                                   fg_color=config.COLORES["acento"],
                                   hover_color=config.COLORES["acento_hover"],
                                   corner_radius=8,
                                   command=self.iniciar_busqueda)
        self.boton.pack(pady=15)

        self.barra_progreso = ctk.CTkProgressBar(self.contenedor_scanner, width=400, mode="indeterminate")
        self.barra_progreso.set(0)
        self.barra_progreso.pack_forget()

        self.lbl_estado = ctk.CTkLabel(self.contenedor_scanner, text="", font=("Consolas", 12), text_color="gray")
        self.lbl_estado.pack_forget()

        self.frame_resultados = ctk.CTkScrollableFrame(self.contenedor_scanner, 
                                                       width=500, height=300,
                                                       fg_color="transparent")
        self.frame_resultados.pack(pady=10, fill="both", expand=True)

    def setup_ui_historial(self):
        self.frame_historial = ctk.CTkScrollableFrame(self.tab_historial, 
                                                      fg_color="transparent")
        self.frame_historial.pack(fill="both", expand=True, padx=10, pady=10)

    def iniciar_busqueda(self):
        usuario = self.entrada_usuario.get()
        if usuario:
            for widget in self.frame_resultados.winfo_children():
                widget.destroy()
            
            hora = datetime.now().strftime("%H:%M")
            self.agregar_al_historial(usuario, hora)

            self.barra_progreso.pack(pady=5)
            self.barra_progreso.start()
            self.lbl_estado.pack(pady=2)
            self.lbl_estado.configure(text="Iniciando módulos...")

            threading.Thread(target=self.ejecutar_escaneo, args=(usuario,)).start()

    def ejecutar_escaneo(self, usuario):
        if usuario not in self.datos_guardados:
            self.datos_guardados[usuario] = []

        for nombre_sitio, url_base in config.SITIOS.items():
            self.lbl_estado.configure(text=f"Escaneando: {nombre_sitio}...")
            resultado = cerebro.escanear_sitio(nombre_sitio, url_base, usuario)

            if resultado: 
                self.datos_guardados[usuario].append(resultado)
                self.crear_ficha(resultado["sitio"], resultado["url"], resultado["imagen"])
        
        self.lbl_estado.configure(text="Análisis completado.", text_color=config.COLORES["acento"])
        self.barra_progreso.stop()
        self.barra_progreso.pack_forget()

    def crear_ficha(self, nombre_sitio, url, imagen=None, contenedor=None):
        if contenedor is None:
            contenedor = self.frame_resultados

        tarjeta = ctk.CTkFrame(contenedor, 
                               fg_color=config.COLORES["fondo_card"], 
                               corner_radius=10,
                               border_width=1,
                               border_color=config.COLORES["borde"])
        tarjeta.pack(fill="x", pady=6, padx=5)
        
        if imagen:
            frame_foto = ctk.CTkFrame(tarjeta, fg_color="transparent")
            frame_foto.pack(side="left", padx=10, pady=10)
            lbl_img = ctk.CTkLabel(frame_foto, image=imagen, text="")
            lbl_img.pack()
            lbl_img.image = imagen

        frame_texto = ctk.CTkFrame(tarjeta, fg_color="transparent")
        frame_texto.pack(side="left", fill="both", expand=True, padx=5)
        
        lbl_sitio = ctk.CTkLabel(frame_texto, text=f"{nombre_sitio}", 
                                 font=("Roboto", 16, "bold"), 
                                 text_color=config.COLORES["texto_titulos"], anchor="w")
        lbl_sitio.pack(fill="x", pady=(5, 0))
        
        lbl_url = ctk.CTkLabel(frame_texto, text=f"{url}", 
                               font=("Roboto", 12), 
                               text_color=config.COLORES["acento"], anchor="w",
                               cursor="hand2")
        lbl_url.pack(fill="x", pady=(0, 5))
        lbl_url.bind("<Button-1>", lambda event: webbrowser.open(url))

    def agregar_al_historial(self, usuario, hora):
        ficha = ctk.CTkFrame(self.frame_historial, 
                             fg_color=config.COLORES["fondo_card"], 
                             corner_radius=10,
                             border_color=config.COLORES["borde"], border_width=1)
        ficha.pack(fill="x", pady=5, padx=5)

        info = f"🕒 {hora}   |   👤 {usuario.upper()}"
        label = ctk.CTkLabel(ficha, text=info, font=("Consolas", 13), text_color=config.COLORES["texto_cuerpo"])
        label.pack(side="left", padx=15, pady=10)
        
        btn_accion = ctk.CTkButton(ficha, text="Ver Informe", width=90, height=28,
                                   fg_color="transparent", border_color=config.COLORES["acento"], 
                                   border_width=1, text_color=config.COLORES["acento"],
                                   hover_color=config.COLORES["fondo_main"],
                                   font=("Roboto", 11, "bold"),
                                   command=lambda: self.ver_detalles_guardados(usuario))
        btn_accion.pack(side="right", padx=15)

    def ver_detalles_guardados(self, usuario):
        if usuario not in self.datos_guardados or not self.datos_guardados[usuario]:
            return

        ventana_detalle = ctk.CTkToplevel(self)
        ventana_detalle.title(f"Informe Digital: {usuario}")
        ventana_detalle.geometry("500x500")
        ventana_detalle.configure(fg_color=config.COLORES["fondo_main"])
        ventana_detalle.attributes('-topmost', True)

        lbl_titulo = ctk.CTkLabel(ventana_detalle, text=f"RESULTADOS: {usuario.upper()}", 
                                  font=("Roboto", 18, "bold"), text_color=config.COLORES["texto_titulos"])
        lbl_titulo.pack(pady=15)

        frame_detalle = ctk.CTkScrollableFrame(ventana_detalle, fg_color="transparent")
        frame_detalle.pack(fill="both", expand=True, padx=15, pady=10)

        for dato in self.datos_guardados[usuario]:
            self.crear_ficha(dato["sitio"], dato["url"], dato["imagen"], contenedor=frame_detalle)

if __name__ == "__main__":
    app = UserScopeApp()
    app.mainloop()