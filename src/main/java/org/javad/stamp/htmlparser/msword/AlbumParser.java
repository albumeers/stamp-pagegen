/*
   Copyright 2014 Jason Drake (jadrake75@gmail.com)
 
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
package org.javad.stamp.htmlparser.msword;

import java.io.FileOutputStream;
import java.io.FileWriter;
import java.io.IOException;
import java.io.OutputStreamWriter;
import java.io.StringReader;
import java.io.StringWriter;
import java.io.Writer;
import java.nio.charset.Charset;
import java.util.logging.Level;
import java.util.logging.Logger;
import javax.xml.stream.XMLOutputFactory;
import javax.xml.stream.XMLStreamException;
import javax.xml.stream.XMLStreamWriter;
import javax.xml.transform.OutputKeys;
import javax.xml.transform.Transformer;
import javax.xml.transform.TransformerException;
import javax.xml.transform.TransformerFactory;
import javax.xml.transform.stream.StreamResult;
import javax.xml.transform.stream.StreamSource;
import org.htmlparser.Node;
import org.htmlparser.NodeFilter;
import org.htmlparser.Parser;
import org.htmlparser.filters.AndFilter;
import org.htmlparser.filters.CssSelectorNodeFilter;
import org.htmlparser.filters.HasParentFilter;
import org.htmlparser.filters.NotFilter;
import org.htmlparser.filters.TagNameFilter;
import org.htmlparser.util.NodeIterator;
import org.htmlparser.util.ParserException;
import org.javad.pdf.Page;
import org.javad.stamp.htmlparser.msword.styles.LegacyPageStyle;
import org.javad.stamp.htmlparser.msword.styles.PageStyle;

/**
 *
 */
public class AlbumParser {
    
    public static void main(String[] args) {
        AlbumParser parser = new AlbumParser();
        parser.parse(new LegacyPageStyle(), "T:\\stamps\\Html Converted\\Iceland-1962.html", "c:\\temp\\output.xml");
    }
    
    public void parse(PageStyle style, String inputFile, String targetFile) {
        try {
            Parser parser = new Parser(inputFile);
            NodeFilter pageFilter = new AndFilter(
                    new CssSelectorNodeFilter(".TableGrid"),
                    new NotFilter(new HasParentFilter(new TagNameFilter("TD")))
            );
            StringWriter sw = new StringWriter();
            XMLStreamWriter xtw = startXMLDocument(sw);
            for (NodeIterator pages = parser.extractAllNodesThatMatch(pageFilter).elements(); pages.hasMoreNodes();) {
                Node pNode = pages.nextNode();
                PageProcessor processor = new PageProcessor(style);
                Page page = processor.process(pNode,null);
                if (page != null) {
                    page.writeToXml(xtw);
                }
            }
            endXMLDocument(sw, xtw, targetFile);
        } catch (ParserException | XMLStreamException ex) {
            Logger.getLogger(AlbumParser.class.getName()).log(Level.SEVERE, null, ex);
        }
    }

    private void endXMLDocument(Writer sw, XMLStreamWriter xtw, String targetFile) throws XMLStreamException {
        try {
            xtw.writeEndElement();
            xtw.writeEndDocument();
            xtw.flush();
            xtw.close();
            
            TransformerFactory factory = TransformerFactory.newInstance();
            
            Transformer transformer = factory.newTransformer();
            transformer.setOutputProperty(OutputKeys.INDENT, "yes");
            transformer.setOutputProperty(OutputKeys.ENCODING,"utf-8");
            transformer.setOutputProperty(OutputKeys.METHOD,"xml");
            transformer.setOutputProperty("{http://xml.apache.org/xslt}indent-amount", "4");
            // Need to ensure the output format is in utf-8 so we use an output stream writer
            // to set the output encoding on the writes
            Writer out = new OutputStreamWriter(new FileOutputStream(targetFile),Charset.forName("UTF-8"));
            transformer.transform(new StreamSource(new StringReader(sw.toString())), new StreamResult(out));
        } catch (TransformerException | IOException ex) {
            Logger.getLogger(AlbumParser.class.getName()).log(Level.SEVERE, null, ex);
        }
    }

    private XMLStreamWriter startXMLDocument(Writer writer) throws XMLStreamException {
        XMLOutputFactory xof = XMLOutputFactory.newInstance();
        XMLStreamWriter xtw = xof.createXMLStreamWriter(writer);
        xtw.writeStartDocument("utf-8", "1.0");
        xtw.writeDTD("<!DOCTYPE album SYSTEM \"http://www.drakeserver.com/dtds/pagegen.dtd\">");
        xtw.writeStartElement("album");
        return xtw;
    }
}
