/*
 Copyright 2012 Jason Drake (jadrake75@gmail.com)
 
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

import java.io.File;
import java.io.IOException;
import java.util.HashMap;
import java.util.Map;
import java.util.Map.Entry;
import java.util.Properties;
import java.util.logging.Level;
import java.util.logging.Logger;

import javax.xml.parsers.DocumentBuilder;
import javax.xml.parsers.DocumentBuilderFactory;

import org.javad.xml.IXMLContentParser;
import org.w3c.dom.Document;
import org.w3c.dom.Element;
import org.xml.sax.SAXParseException;

public class StampXMLParserFactory {

    private static StampXMLParserFactory instance = null;

    private File parseFile = null;

    private static final Logger logger = Logger.getLogger(StampXMLParserFactory.class.getName());
    private Map<String, IXMLContentParser<?>> parsers = new HashMap<String, IXMLContentParser<?>>();

    private void initialize() {
        Properties props = new Properties();
        try {
            props.loadFromXML(getClass().getResourceAsStream("/META-INF/xml-stampparsers.xml"));
            for (Entry<Object, Object> entry : props.entrySet()) {
                try {
                    Class<?> clazz = Class.forName(entry.getValue().toString());
                    if (clazz != null && IXMLContentParser.class.isAssignableFrom(clazz)) {
                        parsers.put(entry.getKey().toString(), (IXMLContentParser<?>) clazz.newInstance());
                    }
                } catch (Exception e) {
                    e.printStackTrace();
                }

            }
        } catch (IOException e) {
            logger.log(Level.SEVERE, "An error occured configuring the XML parsers", e);
        }
    }

    public static StampXMLParserFactory getInstance() {
        if (instance == null) {
            instance = new StampXMLParserFactory();
            instance.initialize();
        }
        return instance;
    }

    public Document getDocument(File inputFile) throws Exception {
        DocumentBuilderFactory docFactory = DocumentBuilderFactory.newInstance();
        docFactory.setIgnoringComments(true);
        docFactory.setIgnoringElementContentWhitespace(true);
        DocumentBuilder builder = docFactory.newDocumentBuilder();
        Document xmlDoc = null;
        try {
            xmlDoc = builder.parse(inputFile);
            setParseFile(inputFile);
        } catch (SAXParseException spe) {
            logger.log(Level.SEVERE, "Line " + (spe.getLineNumber() - 1) + ": Parsing Error - " + spe.getMessage(), spe);
            throw new Exception("Unable to continue parsing the document.");
        }

        return xmlDoc;
    }

    public File getWorkingFolder() throws IllegalStateException {
        if (parseFile == null) {
            throw new IllegalStateException("The parsing file is not set.");
        }
        if (parseFile.getParent() != null) {
            return new File(parseFile.getParent());
        }
        return null;
    }

    public File getParseFile() {
        return parseFile;
    }

    public void setParseFile(File parseFile) {
        this.parseFile = parseFile;
    }

    public IXMLContentParser<?> getParser(String tagName) {
        IXMLContentParser<?> parser = null;
        if (tagName != null && parsers.containsKey(tagName)) {
            parser = parsers.get(tagName);
        }
        return parser;
    }

    public IXMLContentParser<?> getParser(Element element) {
        IXMLContentParser<?> parser = null;
        if (element != null && parsers.containsKey(element.getTagName())) {
            parser = parsers.get(element.getTagName());
        }
        return parser;
    }
}
