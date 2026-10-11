# PDF2MD
`D:\Claude\Proyectos\Herramientas\PDF2MD\`

Convertidor de PDF a Markdown para manuales técnicos (uso personal, contexto para
conversaciones con Claude), con cola de conversión por lotes (v1.3) y, sobre
ella, "Limpiar completados" / "Reiniciar" con selección múltiple (v1.3b). Estado y
decisiones en [00_NOTAS_PROYECTO.md](00_NOTAS_PROYECTO.md) — ver sección
"Versión 1.3b — 'Limpiar completados' y 'Reiniciar'" para el cambio más reciente.
Spec original (ya borrada tras completar la v1.0): `D:\pdf2md_spec.md`.

## Estructura
- `Datos\` — PDFs de prueba u origen (entrada del usuario)
- `Trabajo\` — código en desarrollo
  - [pdf2md.py](Trabajo/pdf2md.py) — script principal: motor de conversión
    puro (`convertir_pdf`), modelo de cola (`ConversionQueue`) y UI
    (customtkinter + ttk.Treeview + tkinterdnd2 para arrastrar y soltar)
  - `requirements.txt` — dependencias del venv (incluye `tkinterdnd2`)
  - `PDF a Markdown.spec` — spec de PyInstaller, para recompilar (ver notas;
    incluye `--collect-data` de `pymupdf` y de `tkinterdnd2`)
- `Final\` — entregable: `PDF a Markdown.exe` (~107.4 MB, standalone, verificado)
  - `anterior\` — versiones anteriores conservadas al sustituir el entregable
    (p. ej. `PDF a Markdown (v1.0).exe`)
- `.venv\` — venv del proyecto (Python 3.14, no versionado); recreado en
  orcos el 11/10/2026, ver notas
