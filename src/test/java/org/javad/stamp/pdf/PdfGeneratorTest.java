/*
	Copyright 2026 Jason Drake (jadrake75@gmail.com)
	
	Licensed under the Apache License, Version 2.0 (the "License");
	you may not use this file except in compliance with the License.
	You may obtain a copy of the License at
	
	    http://www.apache.org/licenses/LICENSE-2.0
	
	Unless required by applicable law or agreed to in writing, software
	distributed under the License is distributed on an "AS IS" BASIS,
	WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
	See the License for the specific language governing permissions and
	limitations under the License.
 */
package org.javad.stamp.pdf;

import static org.junit.jupiter.api.Assertions.*;

import java.io.File;
import java.io.PrintWriter;
import java.nio.file.Path;

import org.javad.stamp.pdf.ui.model.GenerateBean;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

/**
 * Unit tests for {@link PdfGenerator}.
 *
 */
public class PdfGeneratorTest {

    private PdfGenerator generator;

    @BeforeEach
    public void setUp() {
        generator = new PdfGenerator();
    }

    @Test
    public void testGeneratePdfOutput(@TempDir Path tempDir) throws Exception {
        File xmlFile = tempDir.resolve("album.xml").toFile();
        try (PrintWriter writer = new PrintWriter(xmlFile, "UTF-8")) {
            writer.println("<album>");
            writer.println("  <title-page title=\"Germany\" subtitle=\"German Empire\" />");
            writer.println("  <!-- whitespace text nodes -->");
            writer.println("  <page title=\"Germany\" subtitle=\"German Empire\">");
            writer.println("    <set issue=\"1900\" description=\"Reichspost\">");
            writer.println("      <row-set>");
            writer.println("        <s>\"21 25\" \"3pf\" \"Brown\" \"\" \"1\"</s>");
            writer.println("      </row-set>");
            writer.println("    </set>");
            writer.println("  </page>");
            writer.println("</album>");
        }

        File pdfFile = tempDir.resolve("album.pdf").toFile();
        GenerateBean bean = new GenerateBean(xmlFile, pdfFile);

        generator.generate(bean);

        assertTrue(pdfFile.exists(), "PDF file should be created on disk");
        assertTrue(pdfFile.length() > 0, "PDF file should not be empty");
    }

    @Test
    public void testReversePageGeneration(@TempDir Path tempDir) throws Exception {
        File xmlFile = tempDir.resolve("reverse_album.xml").toFile();
        try (PrintWriter writer = new PrintWriter(xmlFile, "UTF-8")) {
            writer.println("<album>");
            writer.println("  <page title=\"Page 1\"><set issue=\"1901\"><row-set><s>\"21 25\" \"5pf\" \"Green\" \"\" \"2\"</s></row-set></set></page>");
            writer.println("  <page title=\"Page 2\"><set issue=\"1902\"><row-set><s>\"21 25\" \"10pf\" \"Red\" \"\" \"3\"</s></row-set></set></page>");
            writer.println("</album>");
        }

        File pdfFile = tempDir.resolve("reverse_album.pdf").toFile();
        GenerateBean bean = new GenerateBean(xmlFile, pdfFile);
        bean.setReversePages(true);

        generator.generate(bean);

        assertTrue(pdfFile.exists(), "Reversed page PDF file should be created on disk");
        assertTrue(pdfFile.length() > 0, "Reversed page PDF file should not be empty");
    }

    @Test
    public void testParallelImageLoading(@TempDir Path tempDir) throws Exception {
        File xmlFile = tempDir.resolve("image_album.xml").toFile();
        try (PrintWriter writer = new PrintWriter(xmlFile, "UTF-8")) {
            writer.println("<album>");
            writer.println("  <page title=\"Images\">");
            writer.println("    <set issue=\"1900\"><row-set>");
            writer.println("      <s image=\"src/test/resources/images/symbol.png\">\"21 25\" \"5pf\" \"Green\" \"\" \"1\"</s>");
            writer.println("      <s image=\"src/test/resources/images/symbol2.png\">\"21 25\" \"10pf\" \"Blue\" \"\" \"2\"</s>");
            writer.println("      <s image=\"src/test/resources/images/symbol2.png\">\"21 25\" \"15pf\" \"Red\" \"\" \"3a\"</s>");
            writer.println("    </row-set></set>");
            writer.println("  </page>");
            writer.println("</album>");
        }

        File pdfFile = tempDir.resolve("image_album.pdf").toFile();
        GenerateBean bean = new GenerateBean(xmlFile, pdfFile);

        assertDoesNotThrow(() -> generator.generate(bean), "Parallel image pre-loading should execute without error");
        assertTrue(pdfFile.exists(), "PDF output should be generated");
    }
}
