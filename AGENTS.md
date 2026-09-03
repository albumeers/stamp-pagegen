# AGENTS.md: stamp-pagegen Project Context & Guidelines

This document serves as a comprehensive guide for AI coding agents and human developers working on the **`stamp-pagegen`** project. It outlines the architecture, build environment, coding standards, and specific constraints required to maintain project stability, regarding legacy Java libraries (iText 5), Swing applications, and the Python Plate Flaw Generator workflow.

---

## 1. Project Overview

- **Artifact ID:** `stamp-pagegen`
- **Language:** Java (JDK 21) & Python 3
- **Build Tool:** Maven
- **Issue Tracker:** [GitHub Issues](https://github.com/albumeers/stamp-pagegen/issues)
- **Domain:** Desktop Application and Python tooling for generating printable Stamp Albums and Plate Flaw Reference PDFs from HTML, MS Word, and XML templates.

The project provides:
1. A Swing desktop application that parses input documents and generates structured PDF stamp pages.
2. A Python reference generator ([`generate-plateflaws.py`](src/main/python/generator/generate-plateflaws.py)) that parses stamp album XML datasets and renders plate flaw & overprint reference PDFs using ReportLab.

---

## 2. Environment & Tooling Rules

- **Issue Tracker Rule:** **NEVER** automatically close GitHub issues, tracker bugs, or tickets upon resolution unless explicitly directed by the user to close them.

```bash
# Build and Compile Java
mvn clean compile

# Run Unit & Integration Tests (Java)
mvn test

# Run Python Unit Tests
python -m unittest discover -s src/test/python -p "test_*.py"

# Package Application (Includes staging generator/ into ZIP artifact)
mvn package -DskipTests

# Execute specific test class
mvn test -Dtest=StampBoxTest

# Git commands
git status
git diff
```

### 2.2. Dependencies & Framework Constraints

#### Java Dependencies ([pom.xml](pom.xml))
- **PDF Engine:** `com.itextpdf:itextpdf:5.5.0` (iText 5 series; do not introduce iText 7/8 APIs).
- **UI Framework:** `com.jgoodies:forms:1.2.1` + Java Swing.
- **Testing:** `org.junit.jupiter:junit-jupiter-api:5.14.2`, `org.mockito:mockito-core:5.14.2`, `org.assertj:assertj-swing-junit:3.17.1`.
- **Parsing:** `org.htmlparser:htmlparser:2.1`, `org.codehaus.woodstox:wstx-asl:3.2.0`.

#### Python Dependencies ([requirements.txt](src/main/python/generator/requirements.txt))
- **Mandatory Requirement:** **ANY** time a new third-party Python package is imported in [`generate-plateflaws.py`](src/main/python/generator/generate-plateflaws.py) or related scripts (e.g. `pillow`, `python-docx`, `pywin32`, `reportlab`), it **MUST IMMEDIATELY** be added to [`src/main/python/generator/requirements.txt`](src/main/python/generator/requirements.txt).
- Declare platform-specific markers when appropriate (e.g. `pywin32; sys_platform == 'win32'`).

---

## 3. Package & Directory Architecture

| Package / Directory | Responsibility | Key Classes / Files | Notes |
| :--- | :--- | :--- | :--- |
| [`org.javad.pdf`](src/main/java/org/javad/pdf) | Core PDF layout abstractions, page definitions, bounds, and content interfaces. | [`Page`](src/main/java/org/javad/pdf/Page.java), [`PageTitle`](src/main/java/org/javad/pdf/PageTitle.java), [`OutputBounds`](src/main/java/org/javad/pdf/OutputBounds.java) | General page positioning & sizing engine. |
| [`org.javad.pdf.fonts`](src/main/java/org/javad/pdf/fonts) | iText 5 font registration & mapping, Windows font discovery. | [`FontRegistry`](src/main/java/org/javad/pdf/fonts/FontRegistry.java), [`PdfFontBean`](src/main/java/org/javad/pdf/fonts/PdfFontBean.java) | Resolves system and user font directories. |
| [`org.javad.stamp.pdf`](src/main/java/org/javad/stamp/pdf) | Domain models for stamp album rendering. | [`StampBox`](src/main/java/org/javad/stamp/pdf/StampBox.java), [`PdfGenerator`](src/main/java/org/javad/stamp/pdf/PdfGenerator.java) | Domain objects representing album layout items. |
| [`src/main/python/generator`](src/main/python/generator) | Python Plate Flaw Generator workflow and assets. | [`generate-plateflaws.py`](src/main/python/generator/generate-plateflaws.py), [`mapping.json`](src/main/python/generator/mapping.json), [`requirements.txt`](src/main/python/generator/requirements.txt) | Staged into output ZIP under `generator/` during `mvn package`. |
| [`src/test/python`](src/test/python) | Python unit tests suite. | [`test_generate_plateflaws.py`](src/test/python/test_generate_plateflaws.py) | Unit tests verifying utility functions, CLI parsing, and memory management. |

---

## 4. Coding Standards & Guidelines

### 4.1. Java Font Handling Rules
- System and user fonts on Windows must be resolved through [`FontRegistry.java`](src/main/java/org/javad/pdf/fonts/FontRegistry.java).
- Always use font family names from `FontRegistry.getInstance().getAvailableFontFamilyNames()`.

### 4.2. Python Plate Flaw Generator Rules
- **Environment Variable Expansion:** Always expand `%USERPROFILE%` natively using `os.path.expandvars(os.path.expanduser(str(font_path)))`. Do not hardcode machine-specific user home paths or dev workspace directories.
- **Font Alias Normalization:** Registered fonts in ReportLab are case-sensitive. Ensure alias lookups handle casing variations (e.g. `CastleTLig` vs `CastleTlig`) in `_register_fonts_main()`.
- **System Font Fallback:** If a mapped font file is not found at the user-specified path on Windows, fall back to checking `C:\Windows\Fonts\<filename>` and emit a warning log if missing.
- **PDF Backend Default:** Default `--pdf-backend` to `reportlab` to prevent unnecessary fallback to MS Word COM automation (which is ~50x slower).
- **Directory Creation Guard:** Always call `os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)` prior to ReportLab `canvas.Canvas` initialization.
- **Log Isolation Standard:** All timing, profiling, and diagnostic log files (e.g. `baseline_timings.txt`, `detailed_timings.txt`) must be written to a dedicated `logs/` subfolder inside `output_directory` (`<output_dir>/logs/`).
- **Memory & Resource Management:** 
  - Downsample high-resolution images to cell resolution before rendering.
  - Clear `_IMAGE_CACHE` and execute `gc.collect()` at the end of PDF generation.
  - Delete intermediate XML strings (`combined_xml`) and parsed line lists (`raw_xml_list`) as soon as they are consumed.

---

## 5. Testing & Quality Assurance

- **Mandatory Test Creation (Strict Guardrail):** AI agents **MUST ALWAYS** write or update unit tests in `src/test/java` AND `src/test/python` for **EVERY** code modification, bug fix, refactor, performance tuning, or default value change without waiting for explicit user prompt.
  - *Exception:* Minor UI component dimension and sizing tweaks (such as preferred height/width adjustments or pixel padding) do not require dedicated unit test assertions.
- **Pre-Completion Requirement:** No task or feature turn may be declared complete until corresponding unit test files under `src/test/java` and `src/test/python` have been updated or added, verified passing, and confirmed.
- **Test Suite Execution:**
  - Run Java test suite: `rtk mvn test`
  - Run Python test suite: `rtk python -m unittest discover -s src/test/python -p "test_*.py"`
