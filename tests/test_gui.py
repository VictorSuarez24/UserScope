"""Pruebas de integración Tk opcionales: USERSCOPE_GUI_TESTS=1."""

import os
import unittest
from unittest.mock import patch

from perfiles import Informe, Objetivo, Origen, Resultado


@unittest.skipUnless(os.getenv("USERSCOPE_GUI_TESTS") == "1", "Requiere escritorio: USERSCOPE_GUI_TESTS=1")
class InterfazTests(unittest.TestCase):
    def setUp(self):
        from main import UserScopeApp
        self.app = UserScopeApp()
        self.app.withdraw()
        self.errores = []
        self.app.report_callback_exception = lambda *error: self.errores.append(error)
        self.publico = Resultado(Objetivo("Instagram", "ibaillanos"), identidad="referencia_publica",
                                origenes=[Origen("wikidata", "Referencia pública")])
        self.candidato = Resultado(Objetivo("GitHub", "ibai"), estado="encontrado")
        self.informe = Informe("ibai", [self.publico, self.candidato])

    def tearDown(self):
        # CustomTkinter registra temporizadores propios; limpiar el intérprete entre instancias.
        for identificador in self.app.tk.call("after", "info"):
            self.app.after_cancel(identificador)
        self.app.cerrar()
        self.assertEqual(self.errores, [])

    def test_renderizar_repetidamente_no_usa_etiquetas_destruidas(self):
        self.app.informe_actual = self.informe
        for _ in range(3):
            self.app.renderizar_informe()
            self.app.update()

    def test_textos_se_ajustan_al_ancho_con_escalado_dpi(self):
        self.app.deiconify()
        self.app.informe_actual = Informe("ibai")
        self.app.renderizar_informe()
        self.app.update()
        etiqueta = self.app.frame_resultados.winfo_children()[0]
        ancho_texto = etiqueta.cget("wraplength") * etiqueta._get_widget_scaling()
        self.assertLess(ancho_texto, self.app.frame_resultados.winfo_width())

    def test_candidatos_ocultos_hasta_activar_filtro(self):
        self.app.informe_actual = self.informe
        self.app.renderizar_informe()
        self.assertEqual(len(self.app.frame_resultados.winfo_children()), 1)
        self.app.mostrar_candidatos.set(True)
        self.app.renderizar_informe()
        self.assertEqual(len(self.app.frame_resultados.winfo_children()), 2)
        self.app.update()

    def test_historial_conserva_informes_independientes(self):
        segundo = Informe("ibai", [])
        self.app.agregar_al_historial(self.informe)
        self.app.agregar_al_historial(segundo)
        self.assertIs(self.app.datos_guardados[0][1], self.informe)
        self.assertIs(self.app.datos_guardados[1][1], segundo)
        self.app.update()

    def test_worker_publica_eventos_y_no_toca_tk(self):
        with patch("cerebro.buscar_perfiles", return_value=self.informe):
            self.app.ejecutar_escaneo(("ibai", "", ""), {}, self.app.cancelacion)
        self.assertIsNone(self.app.informe_actual)
        tipo, informe = self.app.cola.get_nowait()
        self.assertEqual(tipo, "completado")
        self.assertIs(informe, self.informe)


if __name__ == "__main__":
    unittest.main()
