import os
import webbrowser
from datetime import datetime

def generar_html(usuario, resultados, tiempo_total="N/A"):
    """
    Genera un archivo HTML con los resultados del escaneo y lo abre en el navegador.
    """
    fecha = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    nombre_archivo = f"reporte_{usuario}.html"
    
    # CSS para Modo Oscuro y Estilo "Hacker"
    estilo_css = """
    <style>
        body { background-color: #050505; color: #e0e0e0; font-family: 'Consolas', 'Courier New', monospace; padding: 20px; }
        .container { max-width: 900px; margin: 0 auto; }
        h1 { color: #E2B714; text-align: center; border-bottom: 2px solid #333; padding-bottom: 10px; }
        .summary { background-color: #121212; padding: 15px; border-radius: 8px; margin-bottom: 20px; border: 1px solid #333; }
        .summary p { margin: 5px 0; font-size: 1.1em; }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #333; }
        th { background-color: #1e1e1e; color: #E2B714; }
        tr:hover { background-color: #1a1a1a; }
        a { color: #4facfe; text-decoration: none; }
        a:hover { text-decoration: underline; color: #E2B714; }
        .footer { margin-top: 40px; text-align: center; color: #666; font-size: 0.9em; }
        .icon { margin-right: 10px; }
    </style>
    """

    # Construcción de las filas de la tabla
    filas_html = ""
    for res in resultados:
        sitio = res.get("sitio", "Desconocido")
        url = res.get("url", "#")
        
        filas_html += f"""
        <tr>
            <td><strong>{sitio}</strong></td>
            <td><a href="{url}" target="_blank">{url}</a></td>
            <td style="color: #00ff00;">Encontrado</td>
        </tr>
        """

    # Plantilla HTML Completa
    contenido_html = f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Reporte OSINT - {usuario}</title>
        {estilo_css}
    </head>
    <body>
        <div class="container">
            <h1>👁️ UserScope Pro Report</h1>
            
            <div class="summary">
                <p><strong>👤 Objetivo:</strong> {usuario}</p>
                <p><strong>📅 Fecha:</strong> {fecha}</p>
                <p><strong>✅ Resultados:</strong> {len(resultados)} cuentas encontradas</p>
            </div>

            <table>
                <thead>
                    <tr>
                        <th>Plataforma</th>
                        <th>Enlace Detectado</th>
                        <th>Estado</th>
                    </tr>
                </thead>
                <tbody>
                    {filas_html}
                </tbody>
            </table>

            <div class="footer">
                Generado automáticamente por UserScope v1.1
            </div>
        </div>
    </body>
    </html>
    """

    # Escribir el archivo
    try:
        with open(nombre_archivo, "w", encoding="utf-8") as f:
            f.write(contenido_html)
        
        # Obtener ruta absoluta para abrirlo
        ruta_absoluta = os.path.abspath(nombre_archivo)
        print(f"Reporte generado: {ruta_absoluta}")
        
        # Abrir automáticamente en el navegador
        webbrowser.open(f"file://{ruta_absoluta}")
        return True, nombre_archivo
    except Exception as e:
        print(f"Error generando reporte: {e}")
        return False, str(e)