**[Read this in English](README.md)**

[![Download latest release](https://img.shields.io/github/v/release/orcosto-lab/pdf2md?label=Download%20latest%20release)](https://github.com/orcosto-lab/pdf2md/releases/latest)

# PDF a Markdown (PDF2MD)

Aplicación de escritorio para Windows que convierte documentos PDF (manuales
técnicos, artículos, etc.) a Markdown, con extracción opcional de imágenes.
Pensada para generar contenido en Markdown listo para usar como contexto en
conversaciones con LLMs.

![Captura de la aplicación](docs/screenshot.png)

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
pip install -r Trabajo\requirements.txt

# Compilar el ejecutable (desde Trabajo\)
cd Trabajo
pyinstaller "PDF a Markdown.spec"
```

El `.exe` resultante se genera en `Trabajo\dist\`.

Para ejecutar el script directamente sin compilar:

```powershell
python Trabajo\pdf2md.py
```

## Limitaciones conocidas

- Layouts de PDF con columnas irregulares/complejas (revistas, capitulares,
  imágenes a doble columna) pueden mezclar el orden del texto — es una
  limitación del motor de layout de `pymupdf4llm`, no controlable desde esta
  herramienta.
- Algunos visores de Markdown estrictos con rutas relativas (MarkBin,
  MarkdownViewer++ de Notepad++) no muestran las imágenes extraídas aunque el
  archivo generado sea correcto — confirmado que es limitación del visor
  (MarkBin exige rutas absolutas), no un bug de esta herramienta. Visores
  confirmados que funcionan bien: Typora, "Another Markdown" de Notepad++
  ([ezyuzin/NppAnotherMarkdown](https://github.com/ezyuzin/NppAnotherMarkdown)).

## Licencia

MIT. Ver [LICENSE](LICENSE).
