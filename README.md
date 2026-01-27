# 🕵️ UserScope - Digital Identity Analyzer

**UserScope** es una herramienta de escritorio diseñada para facilitar la búsqueda de nombres de usuario (OSINT) en múltiples plataformas sociales. Desarrollada en Python con un enfoque en la experiencia de usuario (UX) y una arquitectura modular.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![GUI](https://img.shields.io/badge/GUI-CustomTkinter-green)
![Status](https://img.shields.io/badge/Status-Stable-brightgreen)
![License](https://img.shields.io/badge/License-MIT-yellow)

## 🚀 Características

* **Interfaz Moderna:** Diseño "Cyber-Professional" oscuro utilizando `CustomTkinter`.
* **Búsqueda Concurrente:** Uso de `threading` para evitar congelamientos durante el escaneo de red.
* **Arquitectura Modular:** Separación clara entre lógica (`cerebro.py`), configuración (`config.py`) e interfaz (`main.py`).
* **Historial de Sesión:** Registro temporal de búsquedas con acceso rápido a informes anteriores.
* **Extracción de Metadatos:** Intenta recuperar la foto de perfil del usuario si está disponible.

## 🛠️ Tecnologías Usadas

* **Python 3**
* **CustomTkinter** (UI moderna)
* **Requests** (Peticiones HTTP)
* **BeautifulSoup4** (Scraping de metadatos/fotos)
* **Pillow (PIL)** (Procesamiento de imágenes)

## 📦 Instalación y Uso

1. Clona el repositorio:
   ```bash
   git clone [https://github.com/VictorSuarez24/UserScope.git](https://github.com/VictorSuarez24/UserScope.git)
   cd UserScope
