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
package org.javad.stamp.xml;

import static org.junit.jupiter.api.Assertions.*;

import java.io.ByteArrayInputStream;
import java.nio.charset.StandardCharsets;

import javax.xml.parsers.DocumentBuilder;
import javax.xml.parsers.DocumentBuilderFactory;

import org.javad.pdf.model.PageConfiguration;
import org.javad.pdf.model.PageConfigurations;
import org.javad.stamp.pdf.CompositeRow;
import org.javad.stamp.pdf.IStampContent;
import org.javad.stamp.pdf.StampRow;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.w3c.dom.Document;
import org.w3c.dom.Element;

/**
 * Unit tests for StampRowParser and CompositeRowParser.
 *
 * Mandatory Test Creation (AGENTS.md):
 * AI agents MUST ALWAYS write or update unit tests in src/test/java for every
 * code modification, bug fix, refactor, or default value change without waiting
 * for explicit prompt from the user.
 */
public class StampRowParserTest {

    private StampRowParser stampRowParser;
    private CompositeRowParser compositeRowParser;
    private PageConfiguration configuration;
    private DocumentBuilder documentBuilder;

    @BeforeEach
    public void setUp() throws Exception {
        stampRowParser = new StampRowParser();
        compositeRowParser = new CompositeRowParser();
        configuration = PageConfigurations.getInstance().getActiveConfiguration();

        DocumentBuilderFactory factory = DocumentBuilderFactory.newInstance();
        factory.setNamespaceAware(true);
        documentBuilder = factory.newDocumentBuilder();
    }

    private Element parseXmlElement(String xmlString) throws Exception {
        ByteArrayInputStream is = new ByteArrayInputStream(xmlString.getBytes(StandardCharsets.UTF_8));
        Document doc = documentBuilder.parse(is);
        return doc.getDocumentElement();
    }

    @Test
    public void testParseStampRowWithStampBox() throws Exception {
        String xml = "<row-set><s>\"21 25\" \"5pf\" \"Green\" \"\" \"1\"</s></row-set>";
        Element element = parseXmlElement(xml);

        StampRow row = stampRowParser.parse(element, configuration);
        assertNotNull(row, "Parsed StampRow should not be null");
        assertFalse(row.getStampContent().isEmpty(), "StampRow should contain parsed stamp content");
        assertTrue(row.getStampContent().get(0) instanceof IStampContent, "Child content must implement IStampContent");
    }

    @Test
    public void testParseStampRowWithUnexpectedChildElement() throws Exception {
        String xml = "<row-set><row-set><s>\"21 25\" \"5pf\" \"Green\" \"\" \"1\"</s></row-set></row-set>";
        Element element = parseXmlElement(xml);

        assertDoesNotThrow(() -> {
            StampRow row = stampRowParser.parse(element, configuration);
            assertNotNull(row, "Parsed StampRow should not be null");
        }, "Parsing a row-set containing an unexpected child element should not throw ClassCastException");
    }

    @Test
    public void testParseCompositeRowWithNonRowChild() throws Exception {
        String xml = "<comp-set><s>\"21 25\" \"5pf\" \"Green\" \"\" \"1\"</s></comp-set>";
        Element element = parseXmlElement(xml);

        assertDoesNotThrow(() -> {
            CompositeRow compRow = compositeRowParser.parse(element, configuration);
            assertNotNull(compRow, "Parsed CompositeRow should not be null");
        }, "Parsing a comp-set containing non-row child elements should safely skip them without throwing ClassCastException");
    }
}
