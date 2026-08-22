# AGENTS.md: stamp-pagegen Project Context & Guidelines

This document serves as a comprehensive guide for AI coding agents and human developers working on the **`stamp-pagegen`** project. It outlines the architecture, build environment, coding standards, and specific constraints required to maintain project stability, particularly regarding legacy libraries (iText 5) and Java Swing applications.

---

## 1. Project Overview

- **Artifact ID:** `stamp-pagegen`
- **Language:** Java
- **Target JDK Version:** Java 21
- **Build Tool:** Maven
- **Domain:** Desktop Application for generating printable Stamp Albums in PDF format from HTML / MS Word templates.

The project provides a Swing desktop application that parses input documents, manages font assets (including iText font mapping), and generates structured PDF stamp pages based on defined layout rules (`StampBox`, `StampRow`, `StampSet`, `ColumnSet`, `CompositeRow`).

---

## 2. Environment & Tooling Rules


```bash
# Build and Compile
mvn clean compile

# Run Unit & Integration Tests
mvn test

# Package Application
mvn package

# Execute specific test class
mvn test -Dtest=StampBoxTest

# Git commands
git status
git diff
```

### 2.2. Dependencies & Framework Constraints
Adhere strictly to the declared versions for legacy and UI libraries defined in [pom.xml](file:///D:/src/stamp-pagegen/pom.xml):
- **PDF Engine:** `com.itextpdf:itextpdf:5.5.0` (iText 5 series; do not introduce iText 7/8 APIs).
- **UI Framework:** `com.jgoodies:forms:1.2.1` + Java Swing.
- **Testing:** `org.junit.jupiter:junit-jupiter-api:5.14.2`, `org.mockito:mockito-core:5.14.2`, `org.assertj:assertj-swing-junit:3.17.1`.
- **Parsing:** `org.htmlparser:htmlparser:2.1`, `org.codehaus.woodstox:wstx-asl:3.2.0`.

---

## 3. Package Architecture & Responsibilities

| Package | Responsibility | Key Classes / Interfaces | Notes |
| :--- | :--- | :--- | :--- |
| [`org.javad.pdf`](src/main/java/org/javad/pdf) | Core PDF layout abstractions, page definitions, bounds, and content interfaces. | [`Page`](src/main/java/org/javad/pdf/Page.java), [`PageTitle`](src/main/java/org/javad/pdf/PageTitle.java), [`OutputBounds`](src/main/java/org/javad/pdf/OutputBounds.java), [`IPositionalContent`](src/main/java/org/javad/pdf/IPositionalContent.java) | General page positioning & sizing engine. |
| [`org.javad.pdf.fonts`](src/main/java/org/javad/pdf/fonts) | iText 5 font registration & mapping, Windows font discovery, font bean definitions. | [`FontRegistry`](src/main/java/org/javad/pdf/fonts/FontRegistry.java), [`PdfFontBean`](src/main/java/org/javad/pdf/fonts/PdfFontBean.java), [`PdfFontDefinition`](src/main/java/org/javad/pdf/fonts/PdfFontDefinition.java), [`PdfFontMapping`](src/main/java/org/javad/pdf/fonts/PdfFontMapping.java) | **Critical:** Resolves system and user font directories. |
| [`org.javad.pdf.fonts.ui`](src/main/java/org/javad/pdf/fonts/ui) | Swing UI panels and dialogs for editing font usages and mapping aliases to TrueType files. | [`PdfFontEditor`](src/main/java/org/javad/pdf/fonts/ui/PdfFontEditor.java), [`FontSettingPanel`](src/main/java/org/javad/pdf/fonts/ui/FontSettingPanel.java), [`FontMappingPanel`](src/main/java/org/javad/pdf/fonts/ui/FontMappingPanel.java) | Swing dialogs interacting with `FontRegistry`. |
| [`org.javad.stamp.pdf`](src/main/java/org/javad/stamp/pdf) | Domain models for stamp album rendering. | [`StampBox`](src/main/java/org/javad/stamp/pdf/StampBox.java), [`StampRow`](src/main/java/org/javad/stamp/pdf/StampRow.java), [`StampSet`](src/main/java/org/javad/stamp/pdf/StampSet.java), [`ColumnSet`](src/main/java/org/javad/stamp/pdf/ColumnSet.java), [`CompositeRow`](src/main/java/org/javad/stamp/pdf/CompositeRow.java), [`PdfGenerator`](src/main/java/org/javad/stamp/pdf/PdfGenerator.java) | Domain objects representing album layout items. |
| [`org.javad.stamp.htmlparser`](src/main/java/org/javad/stamp/htmlparser) | HTML and MS Word document processing into stamp album domain models. | [`AlbumParser`](src/main/java/org/javad/stamp/htmlparser/msword/AlbumParser.java), [`PageProcessor`](src/main/java/org/javad/stamp/htmlparser/msword/PageProcessor.java), [`StampSetProcessor`](src/main/java/org/javad/stamp/htmlparser/msword/StampSetProcessor.java) | Document parsing & stylesheet extraction. |
| [`org.javad.stamp.pdf.ui`](src/main/java/org/javad/stamp/pdf/ui) | Swing Desktop Application entry points and event management. | [`StampAlbumGenerator`](src/main/java/org/javad/stamp/pdf/ui/StampAlbumGenerator.java), [`AlbumConversionPanel`](src/main/java/org/javad/stamp/htmlparser/ui/AlbumConversionPanel.java) | Application UI framework. |

---

## 4. Coding Standards & Guidelines

### 4.1. Font Handling Rules
- System and user fonts on Windows must be resolved through [FontRegistry.java](file:///D:/src/stamp-pagegen/src/main/java/org/javad/pdf/fonts/FontRegistry.java).
- Both system fonts (`C:\Windows\Fonts`) and Windows 10/11 user fonts (`%LOCALAPPDATA%\Microsoft\Windows\Fonts`) are scanned alongside user-configured preferences (`file.fontPath`).
- For font picker UIs (e.g. [PdfFontEditor.java](file:///D:/src/stamp-pagegen/src/main/java/org/javad/pdf/fonts/ui/PdfFontEditor.java)), **always use font family names from `FontRegistry.getInstance().getAvailableFontFamilyNames()`** rather than `java.awt.GraphicsEnvironment`. This ensures that only fonts successfully registered in iText's `FontFactory` are shown in the font selection dropdown.

### 4.2. Swing & UI Threading
- Ensure UI state modifications occur on the Event Dispatch Thread (EDT) via `SwingUtilities.invokeLater` when handling background events or long-running PDF compilation tasks.
- Keep UI components decoupled from PDF generation logic by using event publication (`EventBus.publish`).

### 4.3. iText 5 PDF Generation Constraints
- Always use `com.itextpdf.text.Font` for PDF styling. Do not introduce `java.awt.Font` into PDF rendering code paths.
- Handle fallback fonts gracefully: if a registered font cannot be loaded, fallback to default fonts like `FontFactory.HELVETICA` and log appropriate warnings.

---

## 5. Testing & Quality Assurance

- **Mandatory Test Creation:** AI agents **MUST ALWAYS** write or update unit tests in `src/test/java` for every code modification, bug fix, refactor, or default value change without waiting for explicit prompt from the user.
- **Compilation Verification:** Always verify code changes compile cleanly with `mvn clean compile`.
- **Test Suite Execution:** Run the full test suite with `mvn test` after making any change or adding new unit tests, ensuring 100% pass rate.
- **Mocking Standard:** Mock external dependencies and font mappings using Mockito 5 (`@ExtendWith(MockitoExtension.class)` or JUnit Jupiter assertions).
