# PDF a Markdown (PDF2MD)

Aplicación de escritorio para Windows que convierte documentos PDF (manuales
técnicos, artículos, etc.) a Markdown, con extracción opcional de imágenes.
Pensada para generar contenido en Markdown listo para usar como contexto en
conversaciones con LLMs.

## Características

- Interfaz gráfica sencilla (customtkinter): seleccionar PDF y guardar.
- Dos modos de exportación:
  - **Texto MD+Imágenes**: convierte el texto y extrae las imágenes del PDF a
    una carpeta junto al `.md`, con enlaces relativos.
  - **Texto MD**: solo texto, sin imágenes.
- Conversión página a página: si una página falla, se anota el error en el
  resultado y continúa con el resto del documento en vez de abortar.
- Jerarquía de encabezados por tamaño de fuente, tablas como Markdown y orden
  de lectura correcto en documentos a varias columnas (motor
  [`pymupdf4llm`](https://pypi.org/project/pymupdf4llm/)).

## Descarga

El ejecutable standalone para Windows (`PDF a Markdown.exe`) está disponible
en la sección [Releases](../../releases) de este repositorio. No requiere
Python ni ninguna instalación adicional.

## Compilar desde el código fuente

Requisitos: Python 3.11+ en Windows.

```powershell
# Crear y activar un entorno virtual
py -3 -m venv .venv
.venv\Scripts\activate

# Instalar dependencias
pip install customtkinter pymupdf pymupdf4llm pillow pyinstaller

# Compilar el ejecutable (desde Trabajo\)
cd Trabajo
pyinstaller "PDF a Markdown.spec"
```

El `.exe` resultante se genera en `Trabajo\dist\`.

Para ejecutar el script directamente sin compilar:

```powershell
python Trabajo\pdf2md.py
```

## Licencia

MIT. Ver [LICENSE](LICENSE).
