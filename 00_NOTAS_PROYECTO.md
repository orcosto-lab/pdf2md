# PDF2MD — Notas de proyecto
`D:\Claude\Proyectos\Herramientas\PDF2MD\`

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

**v1.0 completa** (pasos arriba). Spec original (`D:\pdf2md_spec.md`) borrada tras
completar todos los pasos. Evolución posterior documentada en secciones propias más
abajo, la más reciente: "Versión 1.3b (11/10/2026) — 'Limpiar completados' y
'Reiniciar'" (incluye un fix de un bug real de la v1.3 — el evento "finished" no
llegaba nunca a la UI, así que "Iniciar" no terminaba visualmente).

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

## Idea pendiente (08/09/2026): OCR local embebido (PaddleOCR-VL) como fallback

Surgió al revisar el repo [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR)
(no motivada por un caso real todavía). `pymupdf4llm` extrae texto de la capa de
texto del PDF — no hace OCR. Si algún manual llega escaneado (solo imagen, sin
capa de texto), hoy sale vacío o con basura.

**Enfoque decidido si se implementa**: PaddleOCR-VL (~0.9B) como fallback local
embebido, activado solo por página cuando `pymupdf4llm` no extrae texto de esa
página — no sustituye el flujo actual. Descartada la alternativa de mandar esas
páginas a una API en la nube (Claude/GPT-4o vision): los manuales pueden
contener datos de proyecto/cliente y no deben salir de la máquina.

**Coste estimado** (sin medir, solo por tamaños publicados de los componentes):
- Framework `paddlepaddle` (CPU, Windows): ~150-250 MB instalado.
- Pesos de PaddleOCR-VL-0.9B: ~1.8-2 GB (fp16).
- Resto de dependencias de `paddleocr` (opencv, shapely, pyclipper...): ~100-250 MB.
- Total estimado añadido al .exe: **~2-2.5 GB** (vs ~106 MB actuales) — pero
  comparado con una suite comercial tipo ABBYY (que también ronda los 2 GB
  instalada), no es un salto descabellado en términos absolutos.
- Inferencia en CPU sin GPU dedicada: previsiblemente varios segundos/página —
  a validar si se implementa, puede notarse en manuales de 100+ páginas.

**Riesgos a vigilar si se implementa**:
- No versionar los pesos del modelo ni el `.venv` en el repo git de PDF2MD
  (`.gitignore`) — si se cuela una vez, el historial queda hinchado para siempre.
- Fricción adicional en el despliegue a orcos de `pdf2md-mcp` (ya pendiente y
  con fricción por el `.venv` no portable, según sus propias notas) si el
  fallback se lleva también ahí.

**Prioridad: baja.** No es un problema real con los manuales técnicos de Pedro
a fecha de hoy; se retoma si aparece un caso concreto de PDF escaneado.

## Versión 1.3 (11/10/2026) — cola por lotes

> **Numeración:** "1.3" y "1.3b" son la numeración interna de trabajo. Ambas
> se publicaron juntas en GitHub como **release v1.1** (11/10/2026), siguiente
> a la v1.0. Publicación: clon temporal de `orcosto-lab/pdf2md` (no hay clon
> local permanente; esta carpeta no es un repo git), copia de los archivos
> rastreados, commit + push, `gh release create` con el `.exe` como asset.

Encargo de Pedro: convertir varios PDF en una sola tanda (añadir archivos o
carpetas, arrastrar y soltar, reordenar, cancelar, reintentar), con modo
global (con/sin imágenes) y destino global (junto al PDF / carpeta de
salida) para toda la cola. Reescritura sustancial de `Trabajo\pdf2md.py`
sobre la base de la v1.0 (3 botones: Seleccionar PDF / Texto MD+Imágenes /
Texto MD).

### Entorno (orcos) — venv recreado

Al empezar esta tarea, `PDF2MD\.venv` **no existía en esta máquina** (orcos)
pese a estar documentado como ubicación fija del venv — probablemente nunca
se replicó desde P101, a diferencia de `pdf2md-mcp`, que sí tiene su propio
`.venv` en orcos (creado 2026-09-15). Se recreó con
`py -3.14 -m venv .venv` (mismo intérprete que usa `pdf2md-mcp` en esta
máquina, `C:\Users\orcos\AppData\Local\Python\pythoncore-3.14-64`) y se
reinstalaron las dependencias de `Trabajo\requirements.txt` (mismas
versiones ya fijadas, wheels precompiladas sin problemas) más `tkinterdnd2`
(nuevo, ver abajo). Pendiente: confirmar en P101, la próxima vez que se
trabaje allí, si su `.venv` sigue existiendo y en qué estado — no asumir
paridad entre máquinas sin comprobar (norma del `CLAUDE.md` raíz).

### Motor: documento completo + fallback (antes: siempre página a página)

Cambio equivalente al ya aplicado en `pdf2md-mcp` (2026-09-05, ver sus
notas): la llamada por página en bucle hacía que `pymupdf4llm` reanalizara
el documento completo (layout, fuentes, tablas) una vez por página, muy
caro para documentos de varias páginas. Ahora: una sola llamada
`pymupdf4llm.to_markdown(doc, ...)` sobre el documento completo; si esa
llamada lanza una excepción, cae al bucle página a página original (ahora
`_convertir_pagina_a_pagina()`) para aislar y reportar qué página concreta
falla — mismo formato de salida de siempre (comentario HTML + resumen).

**Colisión de nombres de imagen entre páginas** (motivo original del bucle
por página, según la spec de esta tarea): verificado que no ocurre.
`pymupdf4llm` nombra cada imagen como `<origen>.pdf-NNNN-MM.png`, donde
`NNNN` es el número de página — ya incluye la página en el nombre tanto si
se llama una vez por documento completo como una vez por página, así que
no hay colisión en ningún caso. Confirmado en la prueba 1 (8 imágenes
generadas con la llamada de documento completo, 8 enlaces correctos, sin
sobrescrituras) y en la prueba 6 (fallback forzado, mismo resultado).

### Threading: se revierte la decisión "sin threading" de la v1.0

La v1.0 documentaba explícitamente "sin threading (uso personal, PDFs de
tamaño razonable) — los botones bloquean la UI brevemente, aceptable en
este contexto". Con una cola de varios archivos esa premisa deja de
sostenerse: convertir una tanda puede tardar minutos y bloquear tkinter ese
tiempo sería mala experiencia (ventana "no responde", sin poder cancelar).
Se añade un hilo de trabajo (`threading.Thread`) que procesa la cola de uno
en uno; la UI nunca se toca desde ese hilo — el hilo solo muta
`ConversionQueue.items` (protegido con `threading.Lock` para las
operaciones de lista: añadir/quitar/mover/leer-siguiente-pendiente) y
notifica eventos ligeros a una `queue.Queue()`; el hilo principal hace
polling con `self.after(150, ...)` y es el único que toca Treeview/labels/
botones. `ConversionQueue` en sí (añadir, quitar, mover, reintentar,
`run()`) no depende de tkinter y se probó de forma aislada (ver Pruebas).

### Reglas de conflicto: nunca sobrescribir ni borrar nada del usuario

Cambio deliberado respecto a la v1.0, que hacía `shutil.rmtree()` de la
carpeta de imágenes si ya existía antes de regenerarla. Ahora: si el `.md`
de destino ya existe, o si existe ya su carpeta `<stem>_images` (en modo
con imágenes) — **aunque el `.md` no exista** —, el archivo se salta
(`status="saltado"`) sin tocar nada, antes de abrir siquiera el PDF. Esto
también resuelve de forma natural el caso "dos PDF de la cola generarían el
mismo `.md` en la carpeta de salida común": el segundo encuentra el `.md`
del primero ya escrito y se salta.

### Estados de la cola: no existe un estado "cancelado" (decisión de Pedro, 11/10/2026)

El encargo original listaba seis estados (`pendiente, convirtiendo, hecho,
saltado, error, cancelado`) y dos reglas que, leídas juntas, no eran
consistentes al 100%: "Reintentar fallidos (error/cancelado → pendiente)"
trataba `cancelado` como estado propio recuperable igual que `error`, pero
la regla de Cancelar decía "los restantes quedan pendientes". Se implementó
primero una lectura (marcar `cancelado` a los pendientes sin tocar) y se
planteó a Pedro como desviación a confirmar.

**Resolución de Pedro**: se aplica la lectura literal del plan original. Al
pulsar Cancelar, el archivo en curso termina con normalidad (no se puede
interrumpir la llamada única de `pymupdf4llm`) y obtiene su estado real
(`hecho`/`saltado`/`error`); los archivos que todavía estaban `pendiente`
se quedan en `pendiente`, sin tocar — pulsar Iniciar de nuevo continúa la
cola exactamente donde se quedó, en el mismo orden. "Reintentar fallidos"
pasa solo los `error` a `pendiente` (los `pendiente` ya están donde tienen
que estar, no necesitan "reintentarse").

Con esto, el estado `cancelado` quedaba sin ningún caso real que lo
produjera — **se eliminó por completo**: ya no aparece en
`QueueItem.status`, `ConversionQueue.counts()`, `ConversionQueue.
retry_failed()` ni en `ConversionQueue.run()` (que ya no tiene ningún
bloque de "asentamiento" tras cancelar, solo deja de arrancar items
nuevos). Los cinco estados reales son: `pendiente, convirtiendo, hecho,
saltado, error`. El resumen final de la UI (`_on_run_finished`), en vez de
un contador "cancelado(s)" muerto, añade una frase si quedan `pendiente`
tras terminar (señal de que el lote se canceló antes de llegar a ellos),
sin inventar un estado nuevo para explicarlo.

No se encontró ningún caso legítimo en el que `cancelado` siguiera
haciendo falta como estado distinto de `pendiente` — se revisó
explícitamente y no lo hay con las reglas actuales (un único hilo,
cancelación solo entre archivos, nunca a mitad de uno).

Pruebas ajustadas y repetidas íntegras tras el cambio (ver "Pruebas" más
abajo): cancelar tras arrancar el primer archivo deja el resto en
`pendiente`; una segunda llamada a `run()` (equivalente a pulsar Iniciar
otra vez) continúa la cola y la termina; `retry_failed()` solo toca
`error`. `.exe` recompilado (~107.4 MB) y verificado (abre, ventana real),
sustituyendo solo `Final\PDF a Markdown.exe` — `Final\anterior\PDF a
Markdown (v1.0).exe` no se tocó.

### UI

Ventana redimensionable (920×640 inicial, mínimo 760×520) con:
`ttk.Treeview` (archivo/estado/detalle) en vez de un solo label de estado;
botones Añadir archivos / Añadir carpeta / Quitar / Subir / Bajar /
Reintentar fallidos / Iniciar / Cancelar; segmented buttons de
`customtkinter` para el modo global (Texto MD+Imágenes / Solo texto MD) y
el destino global (Junto a cada PDF / Carpeta de salida, con botón "Elegir
carpeta..."); barra de progreso (`CTkProgressBar`) + etiqueta `n/total`;
label de resumen final. Quitar/Subir/Bajar solo actúan sobre elementos
`pendiente` (nunca sobre el que está `convirtiendo` ni sobre los ya
terminados), tanto en reposo como durante la ejecución. Añadir
archivos/carpeta y arrastrar y soltar se deshabilitan mientras la cola está
corriendo (para no mover el denominador del progreso a mitad de tanda).
**Sin número de versión visible en la UI** (pedido explícito). **Sin
persistencia de la cola entre sesiones** (decidido por Pedro) — la lista
se pierde al cerrar la app, como estaba previsto.

Arrastrar y soltar: `tkinterdnd2` (nuevo, `pip install tkinterdnd2` en el
venv del proyecto). La ventana principal usa una clase combinada
`ctk.CTk` + `TkinterDnD.DnDWrapper` (patrón habitual para mezclar
`customtkinter` con `tkinterdnd2`, ya que `customtkinter.CTk` no hereda de
`TkinterDnD.Tk`); si la importación de `tkinterdnd2` falla por cualquier
motivo, la app sigue funcionando sin esa función (degradación explícita,
`DND_AVAILABLE = False`, con un aviso textual en la UI en vez de crashear).

### Empaquetado del .exe: tkinterdnd2

Se añadió `datas += collect_data_files('tkinterdnd2')` y
`tkinterdnd2` a `hiddenimports` en `PDF a Markdown.spec`, replicando el
patrón ya usado con `pymupdf` (red de seguridad explícita). En la práctica,
`pyinstaller-hooks-contrib` 2026.6 ya trae su propio hook
(`hook-tkinterdnd2.py`) que lo detecta y empaqueta solo — confirmado en el
log de compilación ("Processing standard module hook 'hook-tkinterdnd2.py'
from ... _pyinstaller_hooks_contrib\stdhooks") — así que la entrada
explícita es redundante pero inofensiva, igual que ya se documentó para
`customtkinter` en el Paso 5 original. El `--collect-data=pymupdf` sigue
siendo imprescindible (sin cambios, ver Paso 5).

### Pruebas

**Motor y conflictos** (`convertir_pdf`, script ad-hoc en una carpeta
temporal fuera del proyecto, limpiada al terminar, sin tocar
`Datos\Riego deficitario olivo.pdf` ni sus `.md` existentes):
1. Documento completo con imágenes: 8 imágenes generadas, sin `.pdf`
   incrustado en el nombre, todos los enlaces presentes en el `.md`.
2. Solo texto: sin carpeta `_images`, sin ningún `![...]` en el resultado.
3. Conflicto por `.md` existente: `status="saltado"`, contenido previo del
   `.md` verificado byte a byte sin cambios.
4. Conflicto por carpeta `_images` existente aunque el `.md` no exista:
   `status="saltado"`, ni se crea el `.md` ni se toca el archivo centinela
   dejado dentro de la carpeta de imágenes.
5. PDF corrupto (texto plano renombrado a `.pdf`): `status="error"`, sin
   excepción sin capturar.
6. Fallback forzado (monkeypatch de `pymupdf4llm.to_markdown` para que la
   llamada de documento completo falle): cae al bucle página a página,
   `status="hecho"`, mismo `.md` resultante.

**Cola** (`ConversionQueue`, sin tkinter):
7. Añadir desde carpeta sin recursión (ignora subcarpeta y archivo `.txt`),
   deduplicación al añadir la misma ruta dos veces.
8. Quitar y mover elementos `pendiente`, orden resultante correcto,
   ejecución completa (`run()`) con los dos archivos restantes converti-
   dos (`hecho`) y el `.md` del tercero (quitado antes de arrancar)
   ausente.
9. Lote con un conflicto (`.md` preexistente), un PDF corrupto y
   cancelación disparada justo al arrancar el primer elemento: el elemento
   en curso termina con normalidad (`saltado` por el conflicto); los tres
   restantes se quedan en `pendiente` (no `cancelado`, ya no existe ese
   estado); el `.md` del conflicto se verifica intacto. Una segunda llamada
   a `run()` (equivalente a pulsar Iniciar otra vez) continúa la cola desde
   donde se quedó: el siguiente válido queda `hecho`, el corrupto `error`,
   el último válido `hecho`. `retry_failed()` devuelve exactamente 1 (el
   `error`) y lo pasa a `pendiente`, sin tocar `saltado`/`hecho`.

**Integración UI real** (clase `PDF2MDApp` completa, sin clics de ratón:
se invocan sus métodos directamente, igual que en el Paso 4 original):
instancia de la app, `_add_paths()` con 2 PDF válidos + 1 corrupto,
`on_start()` real (hilo + `queue.Queue` + `self.after()` real, no
simulado), espera a que `self._running` vuelva a `False` por el propio
bucle de eventos de tkinter, comprobación final: 2 `hecho`, 1 `error`, los
`.md` correctos en disco y ausente el del corrupto. Sin excepciones en
ningún punto.

Todos los artefactos de prueba (carpetas temporales, PDF de prueba, script
de prueba) se borraron al terminar; no se deja ningún script de test en el
repositorio (mismo criterio que el Paso 4 original).

### Compilación y verificación del .exe

Mismo comando documentado en el Paso 5 (vía el `.spec` ya actualizado),
ejecutado desde `Trabajo\` con `..\.venv\Scripts\python.exe -m PyInstaller
"PDF a Markdown.spec" --noconfirm`. Sin warnings relacionados con
`tkinterdnd2` ni con `pymupdf` en el log de compilación.

**Tamaño**: ~107.4 MB (antes ~105.9 MB; el aumento es `tkinterdnd2` y sus
binarios nativos por plataforma, aunque solo se usa el de Windows).

**Verificado**: el `.exe` se lanzó (proceso hijo real, patrón
bootloader+hijo ya documentado en el Paso 5) y permaneció vivo y estable
varios segundos sin crashear — el riesgo histórico conocido era justo este
(recursos de `pymupdf.layout` sin empaquetar, Paso 5), y no reapareció.
Inspeccionado con `pywinauto` (instalado temporalmente en el venv, no es
dependencia de la app, desinstalado al terminar): ventana real "PDF a
Markdown" visible, habilitada, no minimizada, con rectángulo de pantalla
coherente (no en el estado "icónico" (-32000,-32000) de Windows); árbol de
controles con decenas de `TkChild`/`Static`/`Treeview` anidados, sin
señales de fallo de carga.

**Pendiente de prueba (por Pedro)**: no se completó una prueba funcional
de clic-a-clic con `pywinauto` dentro del `.exe` (a diferencia del Paso 5
original, que sí probó el flujo de 2-3 botones). Motivo: los widgets de
`customtkinter` (`CTkButton`, `CTkSegmentedButton`, `CTkLabel`) se dibujan
sobre un `Canvas` sin exponer un nombre accesible individual vía el
backend `win32` de `pywinauto` (confirmado con
`print_control_identifiers()`: solo aparecen `TkChild`/`Static` genéricos,
sin texto) — un clic fiable habría requerido coordenadas de pantalla fijas,
frágiles y no reproducibles de forma robusta sin iterar a ciegas. La lógica
real (cola, hilo, conversión, reglas de conflicto) ya se verificó de forma
más rigurosa ejecutando la clase `PDF2MDApp` completa directamente en
Python (ver "Integración UI real" arriba) — ese camino cubre todo el
comportamiento salvo la interacción física de ratón/teclado en el binario
compilado. Pedro debe probar a mano, con el `.exe` de `Final\`: abrir la
app, arrastrar y soltar un PDF real sobre la ventana, y ejecutar una tanda
completa con imágenes.

### Entrega

`Final\PDF a Markdown.exe` (~107.4 MB) sustituye al entregable anterior,
que se conserva en `Final\anterior\PDF a Markdown (v1.0).exe` (no se borró,
por norma del `CLAUDE.md` raíz de no eliminar entregables existentes sin
pedirlo).

## Versión 1.3b (11/10/2026) — "Limpiar completados" y "Reiniciar"

Encargo de Pedro, continuación directa de la v1.3 (cola por lotes) de la
misma fecha: dos botones nuevos, "Limpiar completados" y "Reiniciar", más
selección múltiple coherente en Quitar/Subir/Bajar. Solo afecta a la app
de escritorio (`Trabajo\pdf2md.py`); `pdf2md-mcp` no se toca (ver relación
entre ambos en `CLAUDE.md` de este proyecto); `V02\` no se tocó.

### Bug encontrado y corregido: el evento "finished" nunca llegaba a la UI

Antes de implementar lo nuevo, la batería de pruebas de integración (ver
abajo) reveló un bug real ya presente en el código de la v1.3 de anoche,
no introducido en esta tarea: `PDF2MDApp._worker_run()` envolvía los
eventos de `ConversionQueue.run()` en un `on_event` que **siempre**
traducía el evento a `("refresh", None)` en la cola de mensajes (más
`("tick", None)` si era `"item_done"`), pero nunca reenviaba el evento
`"finished"` tal cual. Como `_poll_queue()` solo deja de seguir haciendo
`self.after(150, ...)` cuando recibe el mensaje `"finished"`, ese evento
jamás llegaba: tras pulsar "Iniciar", la cola terminaba de verdad en el
hilo de trabajo (todos los archivos quedaban en su estado final), pero la
UI se quedaba para siempre mostrando "Convirtiendo...", con `self._running`
en `True` indefinidamente — Añadir archivos/carpeta, Modo y Destino
seguían deshabilitados sin motivo, y el resumen final nunca aparecía.

Esto coincide con el apartado "Pendiente de prueba (por Pedro)" de la
sección anterior: la prueba de clic-a-clic con `pywinauto` no se completó
la noche que se implementó la v1.3, así que este bug no se había detectado
todavía. Se encontró aquí porque la prueba de integración de la UI real
para "Reiniciar"/"Limpiar completados" sí ejecuta `on_start()` real y
espera a que `self._running` vuelva a `False` por el bucle de eventos de
tkinter — exactamente el camino que estaba roto.

**Corrección** en `_worker_run()`: el `on_event` interno ahora reenvía
explícitamente `("finished", None)` cuando el evento es `"finished"`,
además de seguir mandando `("tick", None)` en `"item_done"` y el
`("refresh", None)` de siempre en todos los casos. Una vez corregido, el
resumen final aparece y los controles se reactivan con normalidad. Pedro
debería notar la diferencia de inmediato al probar el `.exe` a mano: con
la v1.3 de anoche, "Iniciar" nunca "termina" visualmente aunque los
archivos sí se conviertan.

### "Limpiar completados"

`ConversionQueue.clear_done()`: quita de la lista los elementos en estado
"hecho" (y solo esos) sin tocar nada en disco. Utilizable en cualquier
momento, también con la cola corriendo en otro hilo — nunca puede afectar
al elemento en curso porque ese nunca está en "hecho" mientras se procesa
(el propio modelo de estados lo garantiza, no hace falta ningún bloqueo
especial más allá del `Lock` que ya protege la lista). Botón "Limpiar
completados" en la UI (`on_clear_done`), habilitado solo si hay al menos
un elemento "hecho".

### "Reiniciar" y selección múltiple

**Selección múltiple en Quitar/Subir/Bajar**: el `ttk.Treeview` ya usaba
`selectmode="extended"` desde la v1.3 (la selección múltiple en sí ya
funcionaba a nivel de widget), pero "Subir"/"Bajar" solo aceptaban
exactamente un elemento seleccionado. Nuevo método `ConversionQueue.
move_many(ids, delta)`: mueve el bloque de elementos "pendiente"
seleccionados una posición arriba/abajo como unidad, conservando su orden
relativo (como "mover selección" en cualquier lista reordenable — los
elementos adyacentes seleccionados se desplazan juntos en vez de
intercambiarse entre ellos). Algoritmo: procesar los ids seleccionados en
orden ascendente de posición para subir (descendente para bajar),
recalculando el índice *actual* de cada uno en cada paso (ya reflejando
los intercambios anteriores de la misma llamada) antes de intercambiarlo
con su vecino. Ids no "pendiente" en la selección se ignoran sin error; un
elemento ya en el límite de la lista simplemente no se mueve, sin impedir
que el resto de la selección sí lo haga. "Quitar" (`ConversionQueue.
remove`) ya aceptaba una lista de ids desde la v1.3, así que no necesitó
cambios — solo se verificó que el comportamiento con selección múltiple ya
era coherente.

**"Reiniciar"**: vuelve a procesar los elementos seleccionados en estado
"hecho", "saltado" o "error" (`RESTARTABLE_STATUSES`), sobrescribiendo su
salida existente; los pendientes seleccionados se ignoran (no es un
error) y el elemento en curso nunca se toca (ni siquiera si estuviera
seleccionado). `ConversionQueue.restart_items(ids)` los pasa a
"pendiente" con `QueueItem.allow_overwrite=True` y
`detail=OVERWRITE_MARK_DETAIL` ("Se sobrescribirá al convertir.", visible
en la columna de detalle). Antes de aplicar la marca, la UI
(`on_restart_selected`) usa `ConversionQueue.restartable_snapshot(ids)` +
`ConversionQueue.resolve_out_path(...)` con el destino/modo **vigentes en
ese momento** (no los que tenía el elemento la vez anterior) para contar
cuántos de los seleccionados ya tienen su `.md` (o su carpeta `_images` en
modo con imágenes) escritos en el destino actual; si hay alguno, se
muestra un único `messagebox.askyesno` con el recuento — cancelarlo no
cambia nada. La marca se evalúa de nuevo en tiempo de ejecución porque
`ConversionQueue.run()` ya resolvía el destino en cada iteración a partir
de los parámetros vigentes al pulsar "Iniciar" (sin cambios necesarios
ahí).

**Sobrescritura segura** en `convertir_pdf()`: nuevo parámetro
`allow_overwrite` (por defecto `False`, sin cambio de comportamiento para
nadie que no lo pase). Con `allow_overwrite=True` se omiten las dos
comprobaciones de conflicto (`.md` existente / carpeta `_images`
existente) y se convierte igual que siempre, pero el resultado se escribe
primero en un `.md` temporal junto al destino (`<nombre>.pdf2md_tmp.md`) y
las imágenes se preparan en la carpeta temporal habitual
(`tempfile.mkdtemp`); solo si la conversión completa termina bien se hace
la sustitución: si hay imágenes nuevas, se borra la carpeta `<stem>_images`
antigua (si existía) y se mueve la nueva en su lugar (`shutil.move`,
soporta cambiar de volumen); después se reemplaza el `.md` con
`os.replace()` (atómico en el mismo volumen). Si la conversión falla en
cualquier punto anterior a esa sustitución (PDF corrupto, fallo de
`pymupdf4llm` incluso con el fallback página a página, error al escribir
el temporal), no se toca nada de la salida existente y el elemento queda
en "error" — igual que sin `allow_overwrite`. Este mismo camino
(temporal → sustitución) se reutilizó también para el caso sin
`allow_overwrite` y sin conflicto previo (creación normal): no hay dos
rutas de código distintas para "con conflicto" y "sin conflicto", solo
cambia si se comprueba el conflicto por delante o no — menos duplicación
y más cobertura de pruebas del mismo camino.

**Limitación conocida, no cubierta por las pruebas**: la sustitución final
(mover la carpeta de imágenes + reemplazar el `.md`) no es una transacción
completa a nivel de sistema de archivos. Si la conversión termina bien
pero el propio paso de sustitución falla a mitad (p. ej. `shutil.move`
sin permisos de escritura, disco lleno) después de haber borrado ya la
carpeta `_images` antigua pero antes de reemplazar el `.md`, podría
quedar una salida antigua con un `.md` que referencia una carpeta de
imágenes que ya no existe. Es un caso de fallo de sistema de archivos a
mitad de una operación de pocos milisegundos (no un fallo de conversión,
que es el caso real que pidió Pedro y que sí está cubierto), se considera
un riesgo residual aceptable para esta herramienta de uso personal y no
se ha implementado un commit en dos fases con copias de seguridad para
cubrirlo.

Tras procesarse un elemento marcado (hecho o error, nunca queda
"saltado" porque `allow_overwrite=True` se salta esa comprobación), la
marca `allow_overwrite` se limpia siempre (`ConversionQueue.run()`, bloque
`finally`), igual si terminó bien que si terminó mal.

### Pruebas (v1.3b)

Script ad-hoc temporal (`Trabajo\_test_v13b.py`, no se conserva — borrado
al terminar, igual que en la v1.3 y el Paso 4 original), con copias de
`Datos\Riego deficitario olivo.pdf` en carpetas temporales fuera del
proyecto, limpiadas al final de cada prueba:

- Repetida íntegra la batería original de la v1.3 (9 pruebas: documento
  completo con imágenes, solo texto, conflicto por `.md`, conflicto por
  carpeta `_images` sin `.md`, PDF corrupto, fallback forzado, añadir
  desde carpeta sin recursión + dedup, quitar/mover pendientes + ejecutar
  el resto, lote con conflicto+corrupto+cancelación+reintentar) — sin
  regresiones.
- `clear_done`: quita solo los "hecho" (con "pendiente", "convirtiendo",
  "saltado" y "error" presentes a la vez, para comprobar que ninguno de
  esos se toca); y a mitad de una tanda real en marcha (vía
  `ConversionQueue.run()` con un hilo real), confirmando que el elemento
  recién limpiado desaparece y el resto de la cola sigue y termina con
  normalidad.
- `move_many`: bloque de dos seleccionados subiendo y bajando (orden
  relativo conservado), límite superior de la lista (el de abajo se mueve,
  el de arriba no, sin error), e ids no "pendiente" en la selección
  (se ignoran).
- `remove` con selección múltiple de pendientes mezclados con un "hecho"
  (solo se quitan los pendientes).
- `restart_items`: marca solo hecho/saltado/error de la selección, ignora
  pendiente/convirtiendo.
- Sobrescritura (`convertir_pdf(..., allow_overwrite=True)`): sobrescribe
  `.md` + carpeta `_images` (con un archivo centinela en la carpeta antigua
  para probar que se borra entera, no se fusiona); sin salida previa
  funciona igual que una conversión normal; fallo durante la conversión
  (PDF corrupto) deja la salida antigua completamente intacta y sin
  artefactos temporales; `allow_overwrite=False` (valor por defecto) sigue
  saltando sin regresión.
- Reinicio de un "error" con éxito (condición transitoria simulada con
  `fitz.open` que falla solo la primera vez).
- `ConversionQueue.run()` de extremo a extremo: fallo durante un reinicio
  deja el `.md` antiguo intacto y limpia la marca igualmente; lote mixto
  con un elemento marcado (se sobrescribe) y otro sin marcar con conflicto
  real (sigue saltándose) procesados en la misma tanda.
- **Integración UI real** (`PDF2MDApp` completa, sin clics de ratón, igual
  que la v1.3): arranque real con hilo + `queue.Queue` + `self.after()`,
  esperando a `self._running` vía el bucle de eventos de tkinter (el
  camino que reveló el bug del evento "finished", ver arriba); "Limpiar
  completados" tras una tanda real; "Reiniciar" con selección múltiple
  mostrando el diálogo de confirmación (`unittest.mock.patch` sobre
  `pdf2md.messagebox.askyesno`) exactamente una vez cuando hay conflictos
  reales en disco, cero veces cuando no hay ninguno, y verificando que
  cancelar el diálogo no cambia nada; "Subir" con selección múltiple vía
  `on_move`.

Todos los artefactos de prueba (carpetas temporales, PDFs y `.md`/
`_images` generados, el propio script) se borraron al terminar — no se
deja ningún script de test en el repositorio ni se tocó `Datos\Riego
deficitario olivo.pdf` ni ninguno de sus `.md`/`_images` existentes.

**Nota al margen, no de esta tarea**: en `Datos\` ya había de antes
`Riego deficitario olivo.md`, `Riego deficitario olivo2.md` y la carpeta
`Riego_deficitario_olivo_images`, y en `Trabajo\` ya había `_diagnostico.md`
y `_diagnostico_images\` (fechados 03/08/2026, de una investigación previa
ya cerrada según el `CLAUDE.md` de este proyecto). No son artefactos de
esta sesión ni de la v1.3 de anoche; no se han tocado ni borrado, por
norma de no eliminar nada del usuario sin pedirlo, pero quedan anotados
aquí por si Pedro quiere limpiarlos él mismo en algún momento.

### Compilación y verificación del .exe (v1.3b)

Mismo procedimiento documentado en el Paso 5 / v1.3: desde `Trabajo\`,
`..\.venv\Scripts\python.exe -m PyInstaller "PDF a Markdown.spec"
--noconfirm`. Sin warnings relacionados con `pymupdf` ni `tkinterdnd2`.

**Tamaño**: ~107.4 MB (prácticamente igual que la v1.3 de anoche; no se
añadió ninguna dependencia nueva).

**Verificado**: el `.exe` de `Final\` se lanzó y, a diferencia de la
simple comprobación de apertura de sesiones anteriores, aquí se confirmó
explícitamente el patrón lanzador+hijo con `Get-Process`/`tasklist`: el
proceso lanzador (~8 MB) y el proceso hijo real con
`MainWindowTitle = "PDF a Markdown"` y ~132 MB en memoria (coherente con
`pymupdf.layout`/`onnxruntime` cargados) — ventana real visible, sin
crashear. Cerrado con `taskkill` tras la comprobación. La lógica completa
(cola, hilo, "Limpiar completados", "Reiniciar", selección múltiple,
sobrescritura segura, y el fix del evento "finished") ya se verificó de
forma más rigurosa con la integración UI real de las pruebas de arriba.

**Pendiente de prueba (por Pedro)**: igual que en la v1.3 original, no se
hizo una prueba de clic-a-clic físico con `pywinauto` dentro del `.exe`
compilado (misma limitación de `customtkinter`/backend `win32` ya
documentada). Pedro debe probar a mano con el `.exe` de `Final\`: una
tanda con varios PDF, comprobar que "Iniciar" ahora sí termina
visualmente (el bug del evento "finished" ya no debería reproducirse),
"Limpiar completados" con la cola en marcha, y "Reiniciar" sobre archivos
ya convertidos (debe aparecer el diálogo de confirmación si ya existe su
salida).

### Entrega (v1.3b)

`Final\PDF a Markdown.exe` (~107.4 MB) sustituye al entregable anterior de
esta misma carpeta (la v1.3 de anoche, que no se conservó aparte — solo
`Final\anterior\PDF a Markdown (v1.0).exe`, el respaldo original, se deja
sin tocar, por norma del `CLAUDE.md` raíz).
