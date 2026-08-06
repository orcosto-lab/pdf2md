# PDF2MD — Notas de proyecto
`D:\Proyectos\Herramientas\PDF2MD\`

## Objetivo
Herramienta de escritorio para Pedro: convierte manuales técnicos PDF a Markdown,
para usarlos como contexto/información en conversaciones con Claude. Entregable
final: un .exe standalone (Windows), sin necesidad de terminal.

Spec completa: `D:\pdf2md_spec.md`.

## Estado
- Paso 0 (leer CLAUDE.md raíz): hecho.
- Paso 1 (estructura de proyecto): hecho.
- Paso 2 (script Python mejorado en `Trabajo\pdf2md.py`): hecho.
- Paso 3 (entorno / dependencias): hecho.
- Paso 4 (prueba en Python): hecho, sin errores.
- Paso 5 (compilación a .exe): hecho y verificado (prueba funcional automatizada, ver abajo).
- Paso 6 (entrega en `Final\`): hecho — `Final\PDF a Markdown.exe` (~100.7 MB).

**Proyecto completo.** Spec original (`D:\pdf2md_spec.md`) borrada tras completar todos los pasos.

## Decisiones tomadas (Paso 2)

**Motor de conversión**: `pymupdf4llm.to_markdown()` en vez de la extracción manual
bloque a bloque con `fitz` del script de partida. Resuelve de forma nativa jerarquía
de encabezados por tamaño de fuente, tablas como Markdown y orden de lectura correcto
en layouts multi-columna — sustituye la heurística de mayúsculas (poco fiable) y el
bug de orden de lectura en PDFs a varias columnas del script original.

**Conversión página a página**: en vez de una única llamada a `to_markdown()` para
todo el documento, se llama una vez por página (`pages=[i]`) dentro de un bucle. Así
se pueden capturar errores por página sin abortar la conversión completa — si una
página falla se inserta un comentario HTML con el motivo en su lugar y se continúa
con el resto (evita el todo-o-nada).

**Imágenes**: se usa `write_images=True` de `pymupdf4llm` (`image_path`,
`image_format="png"`, `dpi=150`), que cubre bien el caso pedido — guarda las
imágenes en carpeta separada y genera enlaces relativos en el .md, sin reencode
manual con PIL (evita la pérdida de calidad y el trabajo extra del script de
partida). Flujo en dos fases porque al pulsar "Convertir" todavía no se conoce la
ruta final de guardado: las imágenes se escriben primero en una carpeta temporal
(`tempfile.mkdtemp`); al guardar, se copian a `<nombre-md>_images\` junto al .md
elegido y se reescriben los enlaces en el texto Markdown para apuntar a la ruta
relativa final. La carpeta temporal se borra tras guardar.

**UI**: `customtkinter`, sin threading (uso personal, PDFs de manuales técnicos de
tamaño razonable) — los botones bloquean la UI brevemente durante la conversión,
aceptable en este contexto.

**Manejo de errores**: por página (ver arriba), más try/except global al abrir el
PDF (documento corrupto o ilegible) y al guardar/copiar imágenes. Al final de la
conversión el label de estado resume las páginas con problemas; el resumen también
aparece en el diálogo de guardado.

## Paso 3 — Entorno

CLAUDE.md raíz no especifica una convención propia de entornos Python para
herramientas, así que se usó venv (opción por defecto de la spec). Creado en
`PDF2MD\.venv` con `py -3.14` (Python 3.14.4, `C:\Python314\`, documentado como
el Python de esta máquina en `00_NOTAS_PROYECTO.md` raíz) — no con el 3.11.9 que
resuelve `python`/`where.exe python` por PATH en P101, que es otra instalación
sin relación con este proyecto.

Dependencias instaladas en el venv: `customtkinter`, `pymupdf`, `pymupdf4llm`,
`pillow`. Todas con wheels precompiladas para cp314 en Windows, sin problemas de
compilación. `pymupdf4llm` arrastra como dependencias transitivas `pymupdf_layout`,
`onnxruntime`, `numpy`, `networkx`, `pyyaml`, `tabulate` — más pesado de lo que
sugiere la spec, pero es el paquete oficial y no hay forma de evitarlo.

## Paso 4 — Prueba en Python

No había ningún PDF de prueba dedicado en el sistema, pero sí PDFs reales
disponibles en `Downloads` de Pedro. Se usó
`Riego deficitario Olivo y ppistacho Fases del fruto_0.pdf` (artículo técnico
agrícola, texto + varias imágenes), copiado a `Datos\` como PDF de referencia del
proyecto.

Al ser una app de UI (`customtkinter`), la prueba se hizo con un script ad-hoc
que invoca los mismos métodos que pulsaría Pedro (`select_pdf` → `convert_pdf` →
`save_markdown`), sustituyendo los diálogos de archivo de tkinter por rutas fijas
(`unittest.mock.patch`) para poder ejecutarlo sin intervención manual de ratón.
El script de prueba era solo para esta validación puntual — no se conserva en
`Trabajo\`.

**Resultado: sin errores de página.** El PDF de 8 páginas se convirtió completo,
con jerarquía de encabezados correcta (`#`/`##` por tamaño de fuente), y las 8
imágenes del documento se extrajeron y quedaron enlazadas con rutas relativas
correctas (`_images/...`) en el .md final tras el paso de guardado (que copia
desde la carpeta temporal y reescribe los enlaces). Verificado leyendo el
contenido del .md generado y comprobando que las imágenes referenciadas existen
en la carpeta de destino.

## Paso 5 — Compilación a .exe (PyInstaller)

**Entorno**: `PyInstaller` no estaba instalado — se añadió al venv del proyecto
(`.venv`), no al Python 3.14 global, para no mezclar dependencias de build con
otros proyectos. Versión instalada: PyInstaller 6.21.0 (con
`pyinstaller-hooks-contrib` 2026.6, que trae un hook propio para
`customtkinter` y para `onnxruntime`).

**Comando de compilación** (ejecutado desde `Trabajo\`):

```
.venv\Scripts\python.exe -m PyInstaller --onefile --windowed --name "PDF a Markdown" `
  --add-data ".venv\Lib\site-packages\customtkinter;customtkinter" `
  --collect-data=pymupdf `
  --hidden-import=fitz --hidden-import=pymupdf4llm `
  --distpath ".\dist" --workpath ".\build" --specpath "." pdf2md.py
```

- `--onefile`: un solo .exe, sin carpeta de dependencias sueltas.
- `--windowed`: sin consola detrás de la ventana (app de escritorio, no CLI).
- `--add-data ...customtkinter;customtkinter`: aunque el hook de
  `pyinstaller-hooks-contrib` ya cubre customtkinter, se mantiene explícito por
  claridad y como red de seguridad si el hook cambia de versión.
- `--hidden-import=fitz` / `--hidden-import=pymupdf4llm`: PyInstaller no siempre
  detecta estos imports por análisis estático (uso vía nombre de paquete C
  extension / imports diferidos); se fuerzan explícitamente.
- `--collect-data=pymupdf`: **imprescindible**, ver problema encontrado abajo.

**Problema encontrado y cómo se resolvió — recursos de `pymupdf.layout`**:
la primera compilación (sin `--collect-data=pymupdf`) generaba un .exe que
abría la ventana pero crasheaba justo al hacer clic en cualquier acción, con
`FileNotFoundError` sobre
`...\_MEI*\pymupdf\layout\resources\onnx\layout_rf2.4.1+imf1.yaml`. Causa:
`pymupdf4llm` importa internamente `pymupdf.layout`, que en el **import**
(no en el uso) activa un analizador de layout que carga un modelo ONNX (~47 MB
de recursos en `pymupdf\layout\resources\` y `pymupdf\layout\onnx\*.yaml`).
PyInstaller empaqueta el código `.py` de un paquete automáticamente, pero no
sus archivos de datos no-Python a menos que se le indique. Se diagnosticó
compilando una build temporal con `--console` en vez de `--windowed` (para ver
el traceback real, invisible en modo windowed) y ejecutándola directamente.
Solución: añadir `--collect-data=pymupdf`, que le dice a PyInstaller que
incluya todos los archivos de datos del paquete `pymupdf` (incluye el árbol
`layout/`). Esto explica buena parte del tamaño final del .exe.

**Tamaño final**: ~100.7 MB (single-file). La mayor parte corresponde a los
recursos de `pymupdf.layout` (modelo ONNX, ~47 MB) más `onnxruntime`, `numpy` y
el intérprete de Python embebido — coherente con lo ya anotado en el Paso 3
sobre el peso de las dependencias transitivas de `pymupdf4llm`.

**Prueba de apertura y funcionamiento**: verificada de dos formas:
1. Apertura simple: lanzado el .exe y confirmado que el proceso permanece
   vivo y la ventana "PDF a Markdown" aparece (el proceso visible con la
   ventana es el hijo real; el .exe `--onefile` actúa como lanzador/bootloader
   de ese hijo — comportamiento normal de PyInstaller, no un fallo).
2. Prueba funcional de extremo a extremo: automatizada con `pywinauto`
   (instalado temporalmente en el venv, no es dependencia de la app) simulando
   los clics de Pedro — seleccionar PDF (`Datos\Riego deficitario...pdf`, el
   mismo usado en el Paso 4) → Convertir → Guardar como .md. Resultado: .md
   generado con el contenido correcto (encabezados, texto) y las 8 imágenes
   del PDF extraídas y enlazadas correctamente, igual que en la prueba en
   Python del Paso 4. Sin necesidad de conservar `pywinauto` en el proyecto —
   fue solo herramienta de verificación puntual.

## Paso 6 — Entrega

`Final\PDF a Markdown.exe` (~100.7 MB) es el entregable. Pedro puede
ejecutarlo directamente por doble clic, sin Python ni terminal.

### Cómo recompilar si Pedro cambia el script

1. Editar `Trabajo\pdf2md.py`.
2. Activar el venv del proyecto (`Trabajo\..\.venv\Scripts\activate` o
   invocar directamente `.venv\Scripts\python.exe`).
3. Desde `Trabajo\`, volver a ejecutar el comando de compilación de arriba
   (el `.spec` generado en `Trabajo\PDF a Markdown.spec` ya recoge estas
   opciones — con `pyinstaller "PDF a Markdown.spec"` basta si no cambian las
   dependencias).
4. Copiar el nuevo `dist\PDF a Markdown.exe` a `Final\`, sobrescribiendo el
   anterior.
5. Si se añaden dependencias nuevas con datos empaquetados (fuentes, modelos,
   assets), comprobar si necesitan su propio `--collect-data=<paquete>` o
   `--add-data`, siguiendo el mismo patrón que con `pymupdf`.

`Trabajo\build\` es la carpeta intermedia de PyInstaller (cache de análisis);
se puede borrar sin pérdida — se regenera en cada compilación.

## Cambio posterior (03/08/2026): UI de 3 botones → 2 botones

A petición de Pedro tras la primera entrega: el botón "Convertir" era un paso
manual redundante, ya que convertir y guardar siempre se hacen juntos, nunca
por separado. Eliminado; su lógica (llamada a `pymupdf4llm` página a página +
manejo de imágenes) pasó a ejecutarse dentro del propio `save_markdown()`,
justo antes de escribir el archivo. UI resultante: "Seleccionar PDF" +
"Guardar como Markdown" (deshabilitado hasta seleccionar PDF, igual que antes
lo estaba "Convertir"). Resto del diseño sin cambios (motor, imágenes en dos
fases, manejo de errores por página, sin threading).

Probado con el mismo flujo de mocks del Paso 4 (sin dejar artefactos), y
recompilado con el mismo comando de PyInstaller ya documentado arriba — mismo
problema de `--collect-data=pymupdf` ya resuelto, no reapareció. Nuevo .exe
copiado a `Final\` (~100.7 MB, prácticamente igual de tamaño).

## Compatibilidad de visor: MarkdownViewer++ y MarkBin no muestran las imágenes (03/08/2026)

Pedro detectó que las imágenes generadas no se visualizan en dos visores de
Markdown concretos: **MarkdownViewer++** (plugin de Notepad++) y **MarkBin**
(app de Microsoft Store) — en ambos, el enlace de imagen aparece roto pese a
que el archivo `.md` y las imágenes son correctos (verificado exhaustivamente:
carpeta y nombre de archivo coinciden carácter a carácter, PNG válidos sin
corrupción). Confirmado con **Typora** y **Another Markdown**
(`ezyuzin/NppAnotherMarkdown`, plugin gratuito de Notepad++) que las imágenes
Confirmado por Pedro (03/08/2026): **MarkBin exige rutas absolutas para
cargar imágenes, no soporta rutas relativas en absoluto** — causa raíz exacta
de por qué nunca iba a funcionar ahí con el enfoque estándar de carpeta de
imágenes junto al `.md` (rutas relativas), que es el que usa esta herramienta
y prácticamente cualquier generador de Markdown. No es un bug de
`pdf2md.py` en ningún sentido — es una limitación de diseño de MarkBin en
concreto. MarkdownViewer++ probablemente comparte la misma limitación
(sin confirmar el motivo exacto ahí, pero el síntoma es idéntico).

Se probó también eliminar el `.pdf` incrustado en medio del nombre de archivo
que genera `pymupdf4llm` (ej. `...olivo.pdf-0001-06.png` →
`...olivo-0001-06.png`), por sospecha de que algunos parsers determinan el
tipo de archivo por el primer punto en vez del último. El cambio se mantiene
(nombres más limpios, mejor compatibilidad general), pero **no fue la causa**
del problema con MarkdownViewer++/MarkBin — confirmado que siguen sin
mostrar las imágenes incluso con el nombre ya corregido.

**Recomendación si el .md generado no muestra imágenes en algún visor**: no es
necesariamente un bug de `pdf2md.py` — probar primero con Another Markdown
(Notepad++) o Typora antes de asumir que el archivo está mal generado.

## Fix (03/08/2026): espacios sin codificar en la ruta de imágenes del .md

Bug encontrado por Pedro: el nombre de la carpeta de imágenes se derivaba
directamente de `out_path.stem` (nombre de archivo elegido por el usuario al
guardar), que puede contener espacios — ej.
`Riego deficitario Olivo y ppistacho Fases del fruto_0_images`. Los enlaces de
imagen en el .md quedaban con esa ruta sin escapar, y muchos visores Markdown
(CommonMark estricto) no la resuelven sin `%20` o `<...>`, así que la imagen
no se veía.

Solución en `Trabajo\pdf2md.py` (`save_markdown`): antes de construir
`images_folder_name`, se sanitiza `out_path.stem` con
`re.sub(r"[^A-Za-z0-9_-]", "_", ...)` — cualquier carácter que no sea
alfanumérico, guión o guión bajo se reemplaza por `_`. Solo afecta al nombre
de la carpeta de imágenes y a la ruta escrita en los enlaces; el nombre del
propio .md no se toca. Ejemplo: `Riego deficitario Olivo y ppistacho Fases
del fruto_0` → carpeta `Riego_deficitario_Olivo_y_ppistacho_Fases_del_fruto_0_images`.

Probado con el mismo flujo de mocks de los pasos anteriores (PDF de `Datos\`,
sin dejar artefactos), verificando explícitamente que ninguna ruta de imagen
en el .md generado contiene espacios (8 imágenes, 8 rutas comprobadas).
Recompilado con el `.spec` ya existente en `Trabajo\` (mismo resultado que el
comando documentado en el Paso 5) y el nuevo .exe (~100.7 MB) sustituye al
anterior en `Final\`.

## Fix (03/08/2026): ".pdf" incrustado en medio del nombre de las imágenes

Bug encontrado por Pedro tras varias pruebas con distintos visores Markdown:
`pymupdf4llm` nombra las imágenes como
`<nombre_pdf_origen>.pdf-XXXX-YY.png` (ej.
`Riego_deficitario_olivo.pdf-0001-06.png`) — el `.pdf` queda en medio del
nombre, antes de la extensión real `.png`. Algunos visores/parsers determinan
el tipo de archivo por el primer punto en vez del último y tratan la imagen
como si fuera un PDF.

Solución en `Trabajo\pdf2md.py` (`save_markdown`): tras copiar las imágenes de
la carpeta temporal a `<nombre-md>_images\`, se recorren los archivos
copiados y, para cada uno cuyo *stem* (nombre sin la extensión final, vía
`Path.stem`/`Path.suffix`) contenga `.pdf`, se elimina esa subcadena y se
renombra el archivo — `Path.stem`/`suffix` separan siempre por el *último*
punto, así que la extensión real (`.png`) nunca se toca aunque `.pdf`
aparezca en cualquier posición del nombre generado. Cada enlace
correspondiente en el texto Markdown se reescribe igual (nombre antiguo →
nombre nuevo). Ejemplo:
`Riego_deficitario_olivo.pdf-0001-06.png` →
`Riego_deficitario_olivo-0001-06.png`.

Probado con el mismo flujo de mocks de los pasos anteriores (PDF de `Datos\`,
sin dejar artefactos), verificando explícitamente que ningún nombre de
archivo de imagen ni ningún enlace del .md contiene ya `.pdf` incrustado (8
imágenes, 8 enlaces comprobados). Recompilado con el `.spec` existente en
`Trabajo\` y el nuevo .exe (~100.7 MB) sustituye al anterior en `Final\`.

## Cambio (03/08/2026): UI de 2 botones → 3 botones ("Texto MD" sin imágenes)

A petición de Pedro: además de "Texto MD+Imágenes" (renombrado desde "Guardar
como Markdown", misma lógica de siempre — imágenes en dos fases con carpeta
temporal, enlaces relativos), se añadió un tercer botón "Texto MD" que extrae
solo el texto, sin tocar imágenes en absoluto.

**Cómo se desactivan las imágenes**: se revisó la firma de
`pymupdf4llm.to_markdown()` instalada en el venv del proyecto
(`pymupdf4llm` 1.x). El parámetro relevante es `write_images` (junto a
`embed_images`, no usado aquí); ambos ya son `False` por defecto. Con
`write_images=False` y sin pasar `image_path`, la función interna
`save_image()` devuelve cadena vacía y el código que emite el marcador
`![](...)` está condicionado a que esa cadena no esté vacía (`if pathname:`)
— confirmado leyendo el código fuente de la librería, no por suposición. Así
que el modo "Texto MD" simplemente omite `write_images`/`image_path` en la
llamada por página; no se genera ninguna carpeta de imágenes ni ningún
enlace `![]` en el resultado.

**Factorización**: ambos botones de guardado comparten ahora un único método
`_convert(with_images: bool)` (bucle página a página, manejo de errores,
diálogo de guardado, escritura del archivo final); solo difieren en si se
crea la carpeta temporal de imágenes y se pasan los parámetros de imagen a
`pymupdf4llm.to_markdown()`, y en el bloque posterior que copia imágenes
junto al .md y reescribe enlaces (se salta por completo en modo solo texto).
Los dos botones de guardado permanecen deshabilitados hasta seleccionar un
PDF, igual que antes.

Probado con el mismo flujo de mocks de siempre (PDF de `Datos\`, sin dejar
artefactos): modo "Texto MD+Imágenes" generó las mismas 8 imágenes con
enlaces correctos de las pruebas anteriores; modo "Texto MD" generó un .md de
solo texto sin ninguna carpeta `_images` y sin ningún enlace `![]` (0
encontrados). Recompilado con el `.spec` existente en `Trabajo\` (~105.6 MB,
ligero aumento respecto a los ~100.7 MB previos) y el nuevo .exe sustituye al
anterior en `Final\`.

## Cambio (03/08/2026): icono de la app (`icon.ico`)

Añadido `--icon=icon.ico` (ya generado por Pedro en `Trabajo\icon.ico`) al
comando de PyInstaller documentado en el Paso 5. Nota: el `.venv` del
proyecto está en `PDF2MD\.venv`, no en `Trabajo\.venv` — al ejecutar desde
`Trabajo\` hay que referenciarlo como `..\.venv\Scripts\python.exe` (y el
`--add-data` de customtkinter igual, `..\.venv\...`), no `.venv\...` como
decía literalmente el comando documentado. Verificado que el icono queda
incrustado extrayéndolo del .exe generado (`System.Drawing.Icon.
ExtractAssociatedIcon`, 32x32 encontrado), no solo que el comando no dio
error. Nuevo .exe (~105.9 MB) sustituye al anterior en `Final\`.
