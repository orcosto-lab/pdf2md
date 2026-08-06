# PDF2MD
`D:\Proyectos\Herramientas\PDF2MD\`

Convertidor de PDF a Markdown para manuales técnicos (uso personal, contexto para
conversaciones con Claude). **Completo.** Estado y decisiones en
[00_NOTAS_PROYECTO.md](00_NOTAS_PROYECTO.md). Spec original (ya borrada tras
completarse): `D:\pdf2md_spec.md`.

## Estructura
- `Datos\` — PDFs de prueba u origen (entrada del usuario)
- `Trabajo\` — código en desarrollo
  - [pdf2md.py](Trabajo/pdf2md.py) — script principal (UI customtkinter + conversión con pymupdf4llm)
  - `PDF a Markdown.spec` — spec de PyInstaller, para recompilar (ver notas)
- `Final\` — entregable: `PDF a Markdown.exe` (~100.7 MB, standalone, verificado)
