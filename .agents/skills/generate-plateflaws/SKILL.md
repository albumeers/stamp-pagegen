---
name: generate-plateflaws
description: >-
  Guidelines, CLI usage, dependency management, font mapping, and performance tuning for the Python Plate Flaw Generator (generate-plateflaws.py).
---

# Python Plate Flaw Generator Skill Guide

This skill provides operational guidelines and best practices for developing, running, testing, and maintaining the Python Plate Flaw Reference Generator in `stamp-pagegen`.

---

## 1. Directory & File Locations

- **Generator Script:** [`src/main/python/generator/generate-plateflaws.py`](src/main/python/generator/generate-plateflaws.py)
- **Font Mapping Config:** [`src/main/python/generator/mapping.json`](src/main/python/generator/mapping.json)
- **Dependencies List:** [`src/main/python/generator/requirements.txt`](src/main/python/generator/requirements.txt)
- **Dependency Installers:** [`install-dep.cmd`](src/main/python/generator/install-dep.cmd) and [`install-dep.sh`](src/main/python/generator/install-dep.sh)
- **Python Unit Tests:** [`src/test/python/test_generate_plateflaws.py`](src/test/python/test_generate_plateflaws.py)
- **Documentation:** [`src/main/python/generator/PlateFlawGenerator.md`](src/main/python/generator/PlateFlawGenerator.md)

---

## 2. Command Line Interface (CLI) Usage

### Execution Syntax

```bash
python src/main/python/generator/generate-plateflaws.py --selection ddr --pdf-backend reportlab --input-dir /path/to/xml --output-dir /path/to/output --images-dir /path/to/images
```

### CLI Parameters

| Option | Flag | Description | Default |
| :--- | :--- | :--- | :--- |
| `--selection` | `-s` | Album key (e.g. `ddr`, `es`, `bavaria`, `empire`, `saar`) | Interactive Prompt |
| `--pdf-backend` | `-b` | PDF generation engine (`reportlab` or `word`) | `reportlab` |
| `--input-dir` | `-i` | Base directory containing source XML files | Configured default |
| `--output-dir` | `-o` | Destination directory for PDFs and timing logs | Configured default |
| `--images-dir` | | Directory containing stamp image assets | `<input-dir>/images` |

---

## 3. Dependency Management Rule

**Strict Guardrail:**
Whenever a new third-party Python package is imported in `generate-plateflaws.py` (e.g., `pillow`, `python-docx`, `reportlab`, `pywin32`), you **MUST** immediately update [`src/main/python/generator/requirements.txt`](src/main/python/generator/requirements.txt) to declare the dependency:

```text
pillow
python-docx
pywin32; sys_platform == 'win32'
reportlab
```

---

## 4. Font Resolution & Path Expansion Rules

1. **Environment Variables:** Always expand `%USERPROFILE%` natively using `os.path.expandvars(os.path.expanduser(str(font_path)))`. Do not hardcode machine-specific dev paths.
2. **Casing Normalization:** ReportLab font registry names are case-sensitive. `_register_fonts_main()` must register both casing aliases (e.g. `CastleTLig` and `CastleTlig`) when processing font mappings.
3. **Windows System Font Fallback:** If a mapped font is not found at the user-specified path on Windows, check `C:\Windows\Fonts\<filename>` as a fallback and log a warning if missing.

---

## 5. Performance & Memory Management Rules

1. **Default Backend:** Always default `--pdf-backend` to `reportlab`. MS Word COM automation (`word`) is ~50x slower and should only be used as a manual fallback.
2. **Directory Creation Guard:** Ensure output directories exist via `os.makedirs(..., exist_ok=True)` prior to `canvas.Canvas()` initialization.
3. **Multithreaded Image Pre-processing:** Use `concurrent.futures.ThreadPoolExecutor` for parallel image pre-processing across all CPU cores.
4. **Memory Cleanup:** Clear `_IMAGE_CACHE` and execute `gc.collect()` at the end of PDF generation. Delete intermediate XML string buffers (`combined_xml`) and parsed line lists (`raw_xml_list`) as soon as they are consumed.
5. **Log Isolation Standard:** All timing and diagnostic log files (`baseline_timings.txt`, `detailed_timings.txt`) must be dumped into a dedicated `logs/` subfolder inside `output_directory` (`<output_dir>/logs/`).

---

## 6. Testing Instructions

Run the Python unit test suite:

```bash
rtk python -m unittest discover -s src/test/python -p "test_*.py"
```

Run Maven build & package verification:

```bash
rtk mvn clean package -DskipTests
```
