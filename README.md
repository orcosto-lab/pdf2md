**[Leer en español](README.es.md)**

[![Download latest release](https://img.shields.io/github/v/release/orcosto-lab/pdf2md?label=Download%20latest%20release)](https://github.com/orcosto-lab/pdf2md/releases/latest)

# PDF to Markdown (PDF2MD)

Windows desktop app that converts PDF documents (technical manuals, articles,
etc.) to Markdown, with optional image extraction. Built to produce Markdown
content ready to use as context in conversations with LLMs.

![App screenshot](docs/screenshot.png)

## Features

- Batch queue: add several PDFs at once (file picker, folder picker — only
  that folder's own PDFs, no subfolders — or drag & drop files/folders onto
  the window) and convert them one by one in a background thread, without
  freezing the UI.
- Queue controls: multi-select pending files to reorder (Up/Down moves the
  whole selected block as a unit) or remove them; retry failed files; clear
  completed files from the list at any time, even while the queue is
  running (never touches the file currently in progress, never deletes
  anything from disk); restart selected done/skipped/error files to
  re-convert and safely overwrite their existing output (a single
  confirmation dialog appears only if any selected file's current output
  already exists; the file converts to a temporary location first and only
  replaces the old output if that conversion succeeds — if it fails, the
  previous output is left untouched); cancel the batch (finishes the file
  currently in progress — a single `pymupdf4llm` call can't be interrupted
  mid-way — and leaves the rest untouched as "pending"; pressing Start again
  simply resumes the queue where it left off); live per-file status and an
  overall progress bar plus a final summary (done/skipped/error, plus any
  files still pending if the batch was cancelled).
- Global export mode for the whole queue:
  - **MD text + images**: converts the text and extracts the PDF's images to
    a folder next to the `.md` file, with relative links.
  - **MD text only**: text only, no images.
- Global output destination for the whole queue: next to each PDF, or a
  single output folder.
- Safe by default: if the destination `.md` (or, in image mode, its
  `_images` folder) already exists, that file is skipped and reported —
  nothing of yours is ever overwritten or deleted.
- Whole-document conversion in a single call for speed, with automatic
  page-by-page fallback (only if the full-document call fails) to isolate
  and report exactly which page is broken, without aborting the rest.
- Heading hierarchy based on font size, tables rendered as Markdown, and
  correct reading order in multi-column documents (powered by
  [`pymupdf4llm`](https://pypi.org/project/pymupdf4llm/)).

## Download

The standalone Windows executable (`PDF a Markdown.exe`) is available in this
repository's [Releases](../../releases) section. No Python or additional
installation required.

## Build from source

Requirements: Python 3.11+ on Windows (this project's own venv uses 3.14).

```powershell
# Create and activate a virtual environment at the project root (not inside Trabajo\)
py -3 -m venv .venv
.venv\Scripts\activate

# Install dependencies
pip install -r Trabajo\requirements.txt

# Build the executable (from Trabajo\)
cd Trabajo
..\.venv\Scripts\python.exe -m PyInstaller "PDF a Markdown.spec"
```

The resulting `.exe` is generated in `Trabajo\dist\`. The `.spec` already
bundles `pymupdf`'s data files (required, see `00_NOTAS_PROYECTO.md`) and
`tkinterdnd2`'s native drag & drop files via `--collect-data`.

To run the script directly without building:

```powershell
python Trabajo\pdf2md.py
```

## Known limitations

- PDFs with irregular or complex column layouts (magazines, drop caps,
  double-column images) may end up with mixed-up text order — this is a
  limitation of `pymupdf4llm`'s layout engine, not something this tool
  controls.
- Some strict Markdown viewers that rely on relative paths (MarkBin,
  Notepad++'s MarkdownViewer++) don't display the extracted images even
  though the generated file is correct — confirmed to be a viewer limitation
  (MarkBin requires absolute paths), not a bug in this tool. Viewers
  confirmed to work well: Typora, Notepad++'s "Another Markdown"
  ([ezyuzin/NppAnotherMarkdown](https://github.com/ezyuzin/NppAnotherMarkdown)).

## License

MIT. See [LICENSE](LICENSE).
