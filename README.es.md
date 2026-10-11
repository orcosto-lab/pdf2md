**[Read this in English](README.md)**

[![Download latest release](https://img.shields.io/github/v/release/orcosto-lab/pdf2md?label=Download%20latest%20release)](https://github.com/orcosto-lab/pdf2md/releases/latest)

# PDF a Markdown (PDF2MD)

Aplicación de escritorio para Windows que convierte documentos PDF (manuales
técnicos, artículos, etc.) a Markdown, con extracción opcional de imágenes.
Pensada para generar contenido en Markdown listo para usar como contexto en
conversaciones con LLMs.

![Captura de la aplicación](docs/screenshot.png)

## Características

- Cola por lotes: añade varios PDF a la vez (selector de archivos, selector
  de carpeta — solo sus PDFs directos, sin subcarpetas — o arrastrando y
  soltando archivos/carpetas sobre la ventana) y conviértelos de uno en uno
  en un hilo de trabajo aparte, sin bloquear la interfaz.
- Controles de cola: selección múltiple de archivos pendientes para
  reordenarlos (Subir/Bajar mueve el bloque seleccionado como unidad) o
  quitarlos; reintentar los fallidos; limpiar completados de la lista en
  cualquier momento, también con la cola en marcha (nunca afecta al archivo
  en curso, nunca borra nada del disco); reiniciar los archivos
  seleccionados en estado hecho/saltado/error para volver a convertirlos
  sobrescribiendo su salida de forma segura (aparece un único diálogo de
  confirmación solo si la salida actual de alguno ya existe; cada archivo se
  convierte primero a una ubicación temporal y solo sustituye la salida
  antigua si esa conversión termina bien — si falla, la salida anterior
  queda intacta); cancelar el lote (termina el archivo en curso — una
  llamada de `pymupdf4llm` no se puede interrumpir a mitad — y deja el resto
  como "pendiente"; pulsar Iniciar de nuevo simplemente continúa la cola
  donde se quedó); estado en vivo por archivo, barra de progreso global y
  resumen final (hechos/saltados/con error, más los pendientes que queden si
  se canceló el lote).
- Modo de exportación global para toda la cola:
  - **Texto MD+Imágenes**: convierte el texto y extrae las imágenes del PDF a
    una carpeta junto al `.md`, con enlaces relativos.
  - **Texto MD**: solo texto, sin imágenes.
- Destino de salida global para toda la cola: junto a cada PDF, o una única
  carpeta de salida.
- Seguro por defecto: si el `.md` de destino (o, en modo con imágenes, su
  carpeta `_images`) ya existe, ese archivo se salta y se informa — nunca se
  sobrescribe ni se borra nada tuyo.
- Conversión de documento completo en una sola llamada (más rápido), con
  fallback automático página a página (solo si la llamada completa falla)
  para aislar y reportar exactamente qué página está rota, sin abortar el
  resto.
- Jerarquía de encabezados por tamaño de fuente, tablas como Markdown y orden
  de lectura correcto en documentos a varias columnas (motor
  [`pymupdf4llm`](https://pypi.org/project/pymupdf4llm/)).

## Descarga

El ejecutable standalone para Windows (`PDF a Markdown.exe`) está disponible
en la sección [Releases](../../releases) de este repositorio. No requiere
Python ni ninguna instalación adicional.

## Compilar desde el código fuente

Requisitos: Python 3.11+ en Windows (el venv propio del proyecto usa 3.14).

```powershell
# Crear y activar un entorno virtual en la raíz del proyecto (no dentro de Trabajo\)
py -3 -m venv .venv
.venv\Scripts\activate

# Instalar dependencias
pip install -r Trabajo\requirements.txt

# Compilar el ejecutable (desde Trabajo\)
cd Trabajo
..\.venv\Scripts\python.exe -m PyInstaller "PDF a Markdown.spec"
```

El `.exe` resultante se genera en `Trabajo\dist\`. El `.spec` ya incluye los
datos de `pymupdf` (imprescindible, ver `00_NOTAS_PROYECTO.md`) y los
archivos nativos de arrastrar y soltar de `tkinterdnd2` vía `--collect-data`.

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
