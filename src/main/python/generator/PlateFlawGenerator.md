Generate PF Reference — README

Overview
--------
"generate-plateflaws.py" is a Windows-oriented Python utility that produces printable reference documents (PDFs) for Constant Plate Flaws and Constant Overprint Flaws from stamp album XML files.

It reads combined album XML files and associated stamp image files, extracts the relevant entries for plate/overprint flaws, and lays them out in a paginated grid with stamp images and captions. The program supports two PDF creation backends:

- reportlab: uses ReportLab to render PDF directly (faster, preferred when available).
- word: builds a python-docx document and uses Microsoft Word COM automation to convert it to PDF (fallback; works on Windows with Word installed).

Purpose and objectives
----------------------
- Produce human-readable PDF reference documents that display stamp images and plate/overprint-flaw descriptions arranged in consistent grid layouts.
- Support a fast ReportLab pipeline as well as a Word-based pipeline for compatibility with existing workflows.
- Log pipeline timings (baseline and per-page detailed timings) to help profile performance.

Important files and locations
-----------------------------
- Script: generate-plateflaws.py (this program)
- Default input_directory: c:/Y/mydocs/github/stamp-albums/xml — where XML files and the sibling images/ folder are expected.
- Default images directory (derived): input_directory + '/images' (script resolves image paths relative to the input folder parent).
- Default output_directory: c:/Y/Stamps/_PF References — PDFs and timing logs are written here.
- Logs created:
  - baseline_timings.txt (aggregate phase times)
  - detailed_timings.txt (per-page and per-image timings)

Platform and prerequisites
--------------------------
- Operating system: Windows (Word COM automation and pythoncom used). The ReportLab backend can work cross-platform but the DOCX->PDF path requires Windows + MS Word.
- Python: CPython (tested on Python 3.8+). The script imports modules that must be installed via pip.

Required Python packages
------------------------
- python-docx (package name: python-docx)
- pywin32 (for pythoncom and win32com.client)
- reportlab (optional but recommended for direct PDF generation)

Install (example):

    python -m pip install python-docx pywin32 reportlab

Note: If reportlab is not installed the script will fall back to the Word pipeline.

High-level flow
---------------
1. User chooses a selection key (see selection_map in the script) either via CLI (--selection/-s) or interactively.
2. Script builds a list of XML input files for that selection and computes output paths.
3. For each of two section types ("Constant Plate Flaws" and "Constant Overprint Flaws") the program runs createPFRefAlbumPages():
   a. combine_input_xml_files() reads and concatenates the selected XML files into a single string.
   b. splitCombinedXML() splits the XML into element lines for tokenized processing.
   c. capture_raw_constant_plate_flaw_data() filters the tokenized XML to the XML fragments belonging to the active section (based on global constant_title).
   d. create_data_list() parses the filtered XML tokens and builds a data_list containing entries of types 'set', 'row_set_description', and 'data'.
   e. extract_selectively(), append_row_set_description(), and removeDenominationColor() filter and augment the data list to the rows intended for the PF reference PDF.
   f. remove_duplicates_from_data_list() removes duplicate (image, description) pairs.
   g. If the ReportLab backend is selected and available, generate_pdf_main() renders the PDF directly. If ReportLab is unavailable or fails, the program builds a python-docx Document (createPFDocx()), saves it (writeDocxPfRefDoc()), and converts it to PDF using Word COM (writePdfPfRefDoc()).
4. Timing hooks record phase durations and write both baseline and detailed timing logs.

Key modules and functions (quick reference)
-------------------------------------------
- main(): program entrypoint. Resolves selection, sets global variables and runs createPFRefAlbumPages() for plate flaws and overprint flaws.
- get_selection(): parse args (--selection/-s, --pdf-backend/-b) or prompt interactively.
- createPFRefAlbumPages(input_file_list, output_file, image_directory_location, pdf_backend='word'):
  Orchestrates the pipeline for a section type; records timings and chooses PDF backend.
- combine_input_xml_files(input_file_list): concatenates XML files into a single string.
- splitCombinedXML(combined_xml): splits combined XML into element lines for parsing.
- capture_raw_constant_plate_flaw_data(raw_xml_list): filters element list to the active constant_title block.
- create_data_list(raw_xml_list): parses XML element lines into a structured data_list (items like ['data', image, ...], ['row_set_description', text], ['set', issue]).
- append_row_set_description(data_list): pairs the most recent row-set description and issue year with following 'data' rows.
- removeDenominationColor(data_list): keep rows whose denomination, color, and cell description are empty (identifies plate flaw rows appropriate for PF reference).
- remove_duplicates_from_data_list(data_list, i_image, i_rdesc): de-duplicate by (image, description).
- generate_pdf_main(data_list, output_pdf_path, images_directory, label_print=False, page_title='', page_description=''):
  ReportLab-based PDF rendering (grid layout, image caching, caption wrapping, and font registration).
- createPFDocx(data_list) and printDocxPages(doc, ...): build the python-docx document used by the Word-based backend.
- writeDocxPfRefDoc(doc) and writePdfPfRefDoc(): save .docx and convert to PDF via Word COM.
- _write_timings_log(timings, note=None) and _write_detailed_timings(...): write timing logs.

Data layout: structure of a 'data' row
-------------------------------------
The script stores parsed rows in lists where each position has meaning. Key indices (module globals):
- i_image = 1 (image path relative to album images folder)
- i_denomination = 3
- i_color = 4
- i_cell_desc = 5
- i_cat2 = 8 (Michel catalog number)
- i_rdesc = 9 (row-set description appended later)
- i_date = 10 (issue year appended later)
- i_sort = 11
- i_sort_year = 1 (sorting position in special sort string)
- i_sort_field = 15 (Roman plate fault number or other sort field)

Example parsed row after append_row_set_description():
['data', 'images/Germany - DDR/OD1 II.png', '18x18', '', '', '', '', '', '', 'Large Blank Area in\nEmblem at Right', '1965']

Configuration and editing points
--------------------------------
- input_directory, images_directory, and output_directory are module-level variables set near the top of the file. Update these if your XML/images are in a different location.
- selection_map lists available album selections and maps selection keys (CLI inputs) to (file_list, output_filename). Add new keys, or change file lists here.
- label_print global flag: when True, layout switches to a label-oriented grid (4x10) and modifies table sizing. Default is False.
- Fonts: ReportLab font registration is performed by _register_fonts_main(). If the script cannot find CastleTlig or Verdana, it falls back to built-in fonts.

Running the program
-------------------
Command-line (preferred if you know the selection key):

    python generate-plateflaws.py --selection ddr --pdf-backend reportlab --input-dir /path/to/xml --output-dir /path/to/output --images-dir /path/to/images

Command-line parameters:
- `--selection` / `-s`: Album selection key (e.g. `ddr`, `bavaria`, `empire`, `saar`).
- `--pdf-backend` / `-b`: PDF engine (`reportlab` or `word`).
- `--input-dir` / `-i`: Path to directory containing source album XML files.
- `--output-dir` / `-o`: Destination directory for generated PDF files and timing logs.
- `--images-dir`: Directory containing stamp image assets (defaults to `<input-dir>/images`).

Interactive mode (no --selection):

    python generate-plateflaws.py

The script will prompt for a selection from the keys in selection_map.

Selecting the PDF backend
-------------------------
- Use --pdf-backend reportlab to attempt direct PDF generation via ReportLab.
  If ReportLab is not installed or if the ReportLab generation fails, the script will fall back to python-docx + Word COM.
- Use --pdf-backend word to force the python-docx + Word COM path.

Output
------
- PDF: written to output_directory with a filename taken from selection_map for the chosen selection.
- baseline_timings.txt and detailed_timings.txt: appended in output_directory. These contain phase timings and per-page/per-image timing details to help profile the run.

Logging and diagnostics
-----------------------
- The script prints diagnostic messages and some debug prints to the console (e.g., parsed args, error fallbacks, image missing warnings).
- Timing functions write to baseline_timings.txt and detailed_timings.txt in the configured output_directory.
- ReportLab prints a message if the target image size exceeds the cell box size.

Troubleshooting and common issues
---------------------------------
- Missing images: The script prints "(Image Missing)" in the DOCX document; ReportLab simply omits the image if it cannot load it. Confirm that images_directory is correct and that the image path found in the XML exists under the images folder.
- Word COM errors: DOCX -> PDF conversion requires Microsoft Word installed and accessible via win32com. If Word cannot open or save files (locked files, permission errors), the script attempts alternate "(1)" suffixed filenames. Close any open copies of the DOCX before retrying.
- ReportLab not installed: The script detects absent ReportLab imports and will fall back to a Word-based pipeline. Install reportlab to use the direct PDF path.
- Encoding: XML files are opened with UTF-8. If your XML uses another encoding, adjust combine_input_xml_files() accordingly.
- Hardcoded Windows paths: Many defaults are Windows-specific. If moving to a different machine, update input_directory and output_directory variables.

Development notes and extension points
-------------------------------------
- XML parsing is line-oriented and ad-hoc (split on '<' then inspect prefixes). If album XML formats change or become more complex, consider replacing this with a robust parser (e.g., lxml or ElementTree) for maintainability and correctness.
- The pipeline appends descriptions and years using append_row_set_description(). The code assumes a certain ordering of <set>, <row-set>, and <s> tokens; careful testing needed when XML structure varies.
- To add a new album selection: create a file list similar to the existing ones and add a new key/value pair in selection_map.
- To change layout sizes, adjust constants inside generate_pdf_main() for ReportLab and the sizing code in printDocxPages() for DOCX.

Code style, safety, and maintenance
----------------------------------
- The script uses many module-level global variables (e.g., constant_title, output_file_wo_extension) for legacy convenience. Consider refactoring to pass these values explicitly for easier unit testing and modularity.
- Several "placeholder" XML handlers exist (processAlbum, processItem, etc.) to keep the line-dispatch approach intact; they can be removed or consolidated if a structured parser is introduced.
- Extensive try/except blocks exist to make the script resilient during rendering; however, they sometimes hide root causes. When developing, temporarily surface exceptions to troubleshoot.

Quick developer checklist
------------------------
- Ensure python-docx and pywin32 are installed. Install reportlab for better performance.
- Confirm input_directory contains the expected XML files and a sibling images/ folder.
- Run with --pdf-backend reportlab first. If it fails, run with --pdf-backend word and check Word conversion.
- Inspect baseline_timings.txt and detailed_timings.txt for slow phases and per-image timings.

Changelog summary (from script comments)
---------------------------------------
- v00 to v11: evolved from a Node.js-based parser, added label-print mode, CLI selection, ReportLab backend, timing hooks, and Google-style docstrings.


