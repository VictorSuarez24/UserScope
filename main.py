"""Interfaz de UserScope. Toda interacción con Tk ocurre en el hilo principal."""

from collections import Counter
from datetime import datetime
from queue import Empty, Queue
from threading import Event, Thread
import webbrowser

import customtkinter as ctk

import cerebro
import config


ESTADOS = {
    "encontrado": "Perfil existente",
    "no_encontrado": "No encontrado",
    "no_verificable": "No verificable",
}
IDENTIDADES = {
    "referencia_usuario": "Referencia indicada por ti",
    "enlazado": "Enlazado desde tu referencia",
    "referencia_publica": "Referencia pública · Wikidata",
    "sin_confirmar": "Identidad sin confirmar",
}


class UserScopeApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("UserScope · Perfiles y evidencias")
        self.geometry("900x720")
        self.minsize(780, 640)
        self.configure(fg_color=config.COLORES["fondo_main"])
        self.cola = Queue()
        self.cancelacion = Event()
        self.en_curso = False
        self.informe_actual = None
        self.datos_guardados = []
        self.protocol("WM_DELETE_WINDOW", self.cerrar)
        self.vista = ctk.CTkTabview(self)
        self.vista.pack(fill="both", expand=True, padx=18, pady=14)
        self.tab_scanner = self.vista.add("ESCÁNER")
        self.tab_historial = self.vista.add("HISTORIAL")
        self.setup_ui_scanner()
        self.frame_historial = ctk.CTkScrollableFrame(self.tab_historial)
        self.frame_historial.pack(fill="both", expand=True)
        self._poll_id = self.after(100, self.procesar_eventos)

    def setup_ui_scanner(self):
        ctk.CTkLabel(self.tab_scanner, text="USERSCOPE", font=("Segoe UI", 26, "bold")).pack(pady=(8, 2))
        ctk.CTkLabel(self.tab_scanner,
                     text="Encuentra perfiles y revisa qué los relaciona con tu búsqueda.",
                     text_color="#b0b9c6").pack(pady=(0, 10))
        formulario = ctk.CTkFrame(self.tab_scanner, fg_color="transparent")
        formulario.pack(fill="x", padx=10)
        self.entrada_usuario = self.campo(formulario, "Nombre o usuario", "Ej.: ibai o Ibai Llanos")
        self.entrada_referencia = self.campo(formulario, "Perfil de referencia (opcional)",
                                            "URL de una cuenta que ya sabes que pertenece a esa persona")
        self.entrada_aliases = self.campo(formulario, "Otros alias conocidos (opcional)",
                                         "Hasta cinco usuarios separados por comas")
        opciones = ctk.CTkFrame(formulario, fg_color="transparent")
        opciones.pack(fill="x", pady=(10, 4))
        self.descubrir = ctk.BooleanVar(value=True)
        self.variantes = ctk.BooleanVar(value=True)
        self.check_descubrir = ctk.CTkCheckBox(opciones, text="Descubrir alias públicos", variable=self.descubrir)
        self.check_descubrir.pack(side="left", padx=(0, 25))
        self.check_variantes = ctk.CTkCheckBox(opciones, text="Probar variantes de separadores", variable=self.variantes)
        self.check_variantes.pack(side="left")
        acciones = ctk.CTkFrame(formulario, fg_color="transparent")
        acciones.pack(fill="x", pady=10)
        self.boton = ctk.CTkButton(acciones, text="BUSCAR PERFILES", command=self.iniciar_busqueda, height=38)
        self.boton.pack(side="left")
        self.boton_cancelar = ctk.CTkButton(acciones, text="Cancelar", command=self.cancelar,
                                           state="disabled", fg_color="#414956", width=100, height=38)
        self.boton_cancelar.pack(side="left", padx=10)
        self.barra_progreso = ctk.CTkProgressBar(acciones, mode="indeterminate", width=180)
        self.barra_progreso.set(0)
        self.barra_progreso.pack(side="right")
        self.lbl_estado = ctk.CTkLabel(self.tab_scanner, text="Listo para buscar.", anchor="w", wraplength=700)
        self.lbl_estado.pack(fill="x", padx=12)
        filtros = ctk.CTkFrame(self.tab_scanner, fg_color="transparent")
        filtros.pack(fill="x", padx=12, pady=8)
        self.mostrar_candidatos = ctk.BooleanVar(value=False)
        self.mostrar_diagnostico = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(filtros, text="Ver coincidencias sin confirmar", variable=self.mostrar_candidatos,
                       command=self.renderizar_informe).pack(side="left", padx=(0, 22))
        ctk.CTkCheckBox(filtros, text="Ver comprobaciones fallidas", variable=self.mostrar_diagnostico,
                       command=self.renderizar_informe).pack(side="left")
        self.frame_resultados = ctk.CTkScrollableFrame(self.tab_scanner, fg_color="transparent")
        self.frame_resultados.pack(fill="both", expand=True, padx=6)
        self.etiqueta(self.frame_resultados,
                      "Compartir nombre no demuestra identidad. Las referencias públicas y los enlaces "
                      "se muestran con su origen para que puedas comprobarlos.", "#b0b9c6")
        self.entrada_usuario.bind("<Return>", lambda event: self.iniciar_busqueda())

    def campo(self, padre, titulo, ejemplo):
        ctk.CTkLabel(padre, text=titulo, anchor="w").pack(fill="x", pady=(5, 0))
        entrada = ctk.CTkEntry(padre, placeholder_text=ejemplo, height=34)
        entrada.pack(fill="x")
        return entrada

    def etiqueta(self, padre, texto, color="#d9dfe8", negrita=False):
        etiqueta = ctk.CTkLabel(padre, text=texto, anchor="w", justify="left", wraplength=690,
                               text_color=color, font=("Segoe UI", 13, "bold" if negrita else "normal"))
        etiqueta.pack(fill="x", padx=12, pady=3)
        if not getattr(padre, "_ajuste_texto", False):
            def ajustar(event):
                ancho = int(event.width / padre._get_widget_scaling())
                for hijo in padre.winfo_children():
                    if isinstance(hijo, ctk.CTkLabel):
                        hijo.configure(wraplength=max(220, ancho - 36))
            padre.bind("<Configure>", ajustar, add="+")
            padre._ajuste_texto = True
        return etiqueta

    def iniciar_busqueda(self):
        if self.en_curso:
            return
        argumentos = (self.entrada_usuario.get(), self.entrada_referencia.get(), self.entrada_aliases.get())
        try:
            cerebro.preparar_busqueda(*argumentos)
        except ValueError as exc:
            self.lbl_estado.configure(text=str(exc), text_color="#f0b769")
            return
        self.en_curso = True
        self.cancelacion = Event()
        self.informe_actual = None
        for widget in self.frame_resultados.winfo_children():
            widget.destroy()
        self.activar_controles(False)
        self.lbl_estado.configure(text="Buscando referencias y comprobando perfiles…", text_color="#d9dfe8")
        self.barra_progreso.start()
        opciones = {"descubrir": self.descubrir.get(), "variantes": self.variantes.get()}
        Thread(target=self.ejecutar_escaneo, args=(argumentos, opciones, self.cancelacion), daemon=True).start()

    def activar_controles(self, activos):
        for control in (self.boton, self.entrada_usuario, self.entrada_referencia, self.entrada_aliases,
                        self.check_descubrir, self.check_variantes):
            control.configure(state="normal" if activos else "disabled")
        self.boton_cancelar.configure(state="disabled" if activos else "normal")

    def ejecutar_escaneo(self, argumentos, opciones, cancelacion):
        try:
            informe = cerebro.buscar_perfiles(*argumentos, **opciones, cancelar=cancelacion,
                                              progreso=lambda texto: self.cola.put(("progreso", texto)))
            self.cola.put(("completado", informe))
        except Exception:
            # No volcar excepciones de red que puedan contener claves o tokens.
            self.cola.put(("error", "La búsqueda no pudo completarse. Puedes volver a intentarlo."))

    def procesar_eventos(self):
        try:
            while True:
                tipo, dato = self.cola.get_nowait()
                if tipo == "progreso":
                    if not self.cancelacion.is_set():
                        self.lbl_estado.configure(text=dato)
                else:
                    self.en_curso = False
                    self.barra_progreso.stop()
                    self.barra_progreso.set(0)
                    self.activar_controles(True)
                    if tipo == "completado":
                        self.informe_actual = dato
                        self.agregar_al_historial(dato)
                        self.renderizar_informe()
                    else:
                        self.lbl_estado.configure(text=dato, text_color="#f0b769")
        except Empty:
            pass
        self._poll_id = self.after(100, self.procesar_eventos)

    def cancelar(self):
        self.cancelacion.set()
        self.boton_cancelar.configure(state="disabled")
        self.lbl_estado.configure(text="Cancelando… esperando a que terminen las peticiones en curso.")

    def renderizar_informe(self):
        if self.informe_actual is None:
            return
        informe = self.informe_actual
        for widget in self.frame_resultados.winfo_children():
            widget.destroy()
        cuentas = Counter(r.estado for r in informe.resultados)
        sin_confirmar = sum(r.encontrado and r.identidad == "sin_confirmar" for r in informe.resultados)
        resumen = (f"{cuentas['encontrado']} perfiles existentes · {sin_confirmar} con identidad sin confirmar · "
                   f"{cuentas['no_verificable']} no verificables · {cuentas['no_encontrado']} no encontrados")
        self.lbl_estado.configure(text=resumen, text_color="#d9dfe8")
        for aviso in informe.avisos:
            self.etiqueta(self.frame_resultados, aviso, "#f0c785")
        visibles = 0
        for resultado in informe.resultados:
            con_origen = resultado.identidad != "sin_confirmar"
            if not self.mostrar_diagnostico.get() and resultado.estado == "no_encontrado":
                continue
            if not con_origen and not (
                self.mostrar_candidatos.get() if resultado.encontrado else self.mostrar_diagnostico.get()
            ):
                continue
            self.crear_ficha(resultado, self.frame_resultados)
            visibles += 1
        if not visibles:
            self.etiqueta(self.frame_resultados,
                          "No hay perfiles con una referencia que mostrar. Puedes indicar una cuenta conocida, "
                          "añadir alias o activar los filtros para revisar las coincidencias y comprobaciones.")

    def crear_ficha(self, resultado, contenedor):
        tarjeta = ctk.CTkFrame(contenedor, fg_color=config.COLORES["fondo_card"],
                               border_width=1, border_color=config.COLORES["borde"])
        tarjeta.pack(fill="x", padx=4, pady=6)
        objetivo = resultado.objetivo
        self.etiqueta(tarjeta, f"{objetivo.sitio} · {resultado.nombre or objetivo.usuario}", negrita=True)
        color = "#8cc8f8" if resultado.identidad != "sin_confirmar" else "#f0c785"
        self.etiqueta(tarjeta, f"{ESTADOS[resultado.estado]}  |  {IDENTIDADES[resultado.identidad]}", color)
        enlace = self.etiqueta(tarjeta, objetivo.url, "#81b9ed")
        enlace.configure(cursor="hand2")
        enlace.bind("<Button-1>", lambda event, url=objetivo.url: webbrowser.open(url))
        for evidencia in resultado.evidencias:
            self.etiqueta(tarjeta, evidencia, "#b0b9c6")
        for origen in resultado.origenes:
            etiqueta = self.etiqueta(tarjeta, origen.detalle + (f"\n{origen.url}" if origen.url else ""), "#b0b9c6")
            if origen.url:
                etiqueta.configure(cursor="hand2")
                etiqueta.bind("<Button-1>", lambda event, url=origen.url: webbrowser.open(url))

    def agregar_al_historial(self, informe):
        hora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        self.datos_guardados.append((hora, informe))
        ficha = ctk.CTkFrame(self.frame_historial)
        ficha.pack(fill="x", pady=5)
        ctk.CTkLabel(ficha, text=f"{hora} · {informe.consulta}").pack(side="left", padx=12, pady=10)
        ctk.CTkButton(ficha, text="Ver informe", width=110,
                      command=lambda: self.ver_detalles_guardados(informe)).pack(side="right", padx=12)

    def ver_detalles_guardados(self, informe):
        ventana = ctk.CTkToplevel(self)
        ventana.title(f"Informe: {informe.consulta}")
        ventana.geometry("800x650")
        contenido = ctk.CTkScrollableFrame(ventana)
        contenido.pack(fill="both", expand=True, padx=12, pady=12)
        for aviso in informe.avisos:
            self.etiqueta(contenido, aviso, "#f0c785")
        for resultado in informe.resultados:
            self.crear_ficha(resultado, contenido)
        if not informe.resultados:
            self.etiqueta(contenido, "No se completaron comprobaciones.")
        ventana.after(100, ventana.lift)

    def cerrar(self):
        self.cancelacion.set()
        self.after_cancel(self._poll_id)
        self.destroy()


if __name__ == "__main__":
    ctk.set_appearance_mode("Dark")
    ctk.set_default_color_theme("dark-blue")
    UserScopeApp().mainloop()
