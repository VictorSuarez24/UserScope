"""Regresiones del transporte, sin conexiones reales."""

from threading import Event
import unittest
from unittest.mock import MagicMock, patch

import requests

from red import ClienteHTTP, ErrorRed


def respuesta(estado=200, headers=None, contenido=b'{}'):
    mock = MagicMock()
    mock.__enter__.return_value = mock
    mock.status_code = estado
    mock.headers = headers or {}
    mock.url = 'https://api.github.com/users/ibai'
    mock.iter_content.return_value = [contenido]
    return mock


class RedTests(unittest.TestCase):
    @patch('red.requests.get')
    def test_no_reenvia_credenciales_en_redireccion_externa(self, get):
        get.return_value = respuesta(302, {'Location': 'https://otro.example/perfil'})
        with self.assertRaises(ErrorRed):
            ClienteHTTP().get('https://api.github.com/users/ibai', headers={'Authorization': 'Bearer test'})
        self.assertEqual(get.call_count, 1)

    @patch('red.requests.get')
    def test_no_sigue_downgrade_http(self, get):
        get.return_value = respuesta(302, {'Location': 'http://api.github.com/users/ibai'})
        with self.assertRaises(ErrorRed):
            ClienteHTTP().get('https://api.github.com/users/ibai')
        self.assertEqual(get.call_count, 1)

    @patch('red.requests.get')
    def test_rate_limit_no_reintenta_por_cada_alias(self, get):
        get.return_value = respuesta(429)
        cliente = ClienteHTTP()
        self.assertEqual(cliente.get('https://api.github.com/users/ibai').status_code, 429)
        self.assertEqual(cliente.get('https://api.github.com/users/otro').status_code, 429)
        self.assertEqual(get.call_count, 1)

    @patch('red.requests.get')
    def test_respuesta_demasiado_grande(self, get):
        get.return_value = respuesta(contenido=b'x' * 5_000_001)
        with self.assertRaises(ErrorRed):
            ClienteHTTP().get('https://api.github.com/users/ibai')

    @patch('red.requests.get')
    def test_cancelacion_impide_empezar_otra_peticion(self, get):
        evento = Event()
        evento.set()
        with self.assertRaises(ErrorRed):
            ClienteHTTP(evento).get('https://api.github.com/users/ibai')
        get.assert_not_called()

    @patch('red.requests.get')
    def test_error_no_revela_clave_de_api(self, get):
        get.side_effect = requests.Timeout('https://www.googleapis.com/?key=secreto')
        with self.assertRaises(ErrorRed) as exc:
            ClienteHTTP().get('https://www.googleapis.com/youtube/v3/channels')
        self.assertNotIn('secreto', str(exc.exception))

    @patch('red.requests.get')
    def test_redirecciones_tienen_limite(self, get):
        get.return_value = respuesta(302, {'Location': '/users/ibai'})
        with self.assertRaises(ErrorRed):
            ClienteHTTP().get('https://api.github.com/users/ibai')
        self.assertEqual(get.call_count, 4)


if __name__ == '__main__':
    unittest.main()
