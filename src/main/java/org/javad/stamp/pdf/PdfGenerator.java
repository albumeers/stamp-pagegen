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
package org.javad.stamp.pdf;

import com.itextpdf.text.Document;
import com.itextpdf.text.Rectangle;
import com.itextpdf.text.pdf.PdfContentByte;
import com.itextpdf.text.pdf.PdfWriter;
import java.io.BufferedOutputStream;
import java.io.File;
import java.io.FileOutputStream;
import java.text.MessageFormat;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.logging.Level;
import java.util.logging.Logger;
import org.bushe.swing.event.EventBus;
import org.javad.events.StatusEvent;
import org.javad.events.StatusEvent.StatusType;
import org.javad.pdf.ISetContent;
import org.javad.pdf.OutputBounds;
import org.javad.pdf.Page;
import org.javad.pdf.PageTitle;
import org.javad.pdf.TitlePage;
import org.javad.pdf.TitlePageContent;
import org.javad.pdf.model.PageConfiguration;
import org.javad.pdf.model.PageConfigurations;
import org.javad.pdf.util.ImageCache;
import org.javad.pdf.util.PdfUtil;
import org.javad.stamp.pdf.ui.model.GenerateBean;
import org.javad.stamp.xml.StampXMLParserFactory;
import org.javad.stamp.xml.XMLDefinitions;
import org.w3c.dom.Element;
import org.w3c.dom.Node;
import org.w3c.dom.NodeList;

public class PdfGenerator {

    StampXMLParserFactory factory = null;
    private boolean debug = false;
    private PageConfiguration config;
    private String generatingPageMsg = null;

    private static final Logger logger = Logger.getLogger(PdfGenerator.class.getName());

    public PdfGenerator() {
        try {
            PageConfigurations configs = PageConfigurations.getInstance();
            config = configs.getActiveConfiguration();
            factory = StampXMLParserFactory.getInstance();
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    public static void main(String[] args) {
        if (args == null || args.length < 2) {
            throw new IllegalArgumentException("The source and target files are required.");
        }
        PdfGenerator generator = new PdfGenerator();
        try {
            if (args.length >= 3 && args[2].equalsIgnoreCase("-debug")) {
                generator.setDebug(true);
            }
            generator.generate(new GenerateBean(new File(args[0]), new File(args[1])));
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    public void setDebug(boolean debug) {
        this.debug = debug;
    }

    public void createPage(PdfWriter writer, float center, PageTitle title, ISetContent... sets) {
        PdfContentByte handler = writer.getDirectContent();
        title.setX(center);
        title.setY((int) PdfUtil.convertFromMillimeters(config.getHeight() - config.getMarginTop() - 15.0f));
        OutputBounds rect = title.generate(handler);
        boolean previousTextOnly = false;
        for (ISetContent set : sets) {
            if (set instanceof ColumnSet) {
                float width = PdfUtil.findMaximumWidth(set, handler);
                set.setX(center - width / 2.0f);
            } else {
                set.setX(center);
            }
            set.setY(rect.y - rect.height - ((!previousTextOnly) ? PdfUtil.convertFromMillimeters(5.0f) : 0.0f));
            rect = set.generate(handler);
            previousTextOnly = set.isTextOnly();
        }
    }
    
    public void createTitlePage(PdfWriter writer, float center, TitlePageContent title) {
        PdfContentByte handler = writer.getDirectContent();
        title.setX(center);
        title.setY((int) PdfUtil.convertFromMillimeters(config.getHeight() - config.getMarginTop() - 15.0f));
        title.generate(handler);
    }

    public void generate(GenerateBean bean) throws Exception {
        long t = System.currentTimeMillis();
        config.parseSkipTerms(bean.getTags());
        Rectangle rect = new Rectangle(PdfUtil.convertFromMillimeters(config.getWidth()), PdfUtil.convertFromMillimeters(config.getHeight()));
        Document document = new Document(rect);
        PdfWriter writer = null;
        BufferedOutputStream bos = null;
        int pageCount = 0;
        try {
            boolean validName = bean.getInputFile().getName().toLowerCase().endsWith(".xml");
            if (validName) {
                bos = new BufferedOutputStream(new FileOutputStream(bean.getOutputFile()), 64 * 1024);
                writer = PdfWriter.getInstance(document, bos);
                setMargins(document);
                pageCount = parseXMLDocument(bean, document, writer);
                bos.flush();
            }

        } catch (Exception ex) {
            ex.printStackTrace();
        } finally {
            if (writer != null) {
                writer.close();
            }
            if (bos != null) {
                bos.close();
            }
        }
        long delta = System.currentTimeMillis() - t;
        logger.log(Level.INFO, "Successful album page generation. (execution time: " + delta + "ms, pages: " + pageCount + ")");
    }

    public void setMargins(Document document) {
        document.setMargins(PdfUtil.convertFromMillimeters(config.getMarginLeft()),
                PdfUtil.convertFromMillimeters(config.getMarginRight()),
                PdfUtil.convertFromMillimeters(config.getMarginTop()),
                PdfUtil.convertFromMillimeters(config.getMarginBottom()));
    }

    private static class ParsedPageHolder {
        final int pageIndex;
        final Element element;
        final Object parsedPage;

        ParsedPageHolder(int pageIndex, Element element, Object parsedPage) {
            this.pageIndex = pageIndex;
            this.element = element;
            this.parsedPage = parsedPage;
        }
    }

    private Set<File> collectImageFiles(org.w3c.dom.Document xmlDoc) {
        Set<File> files = new HashSet<>();
        if (xmlDoc == null) return files;
        File folder = factory.getWorkingFolder();
        NodeList allElements = xmlDoc.getElementsByTagName("*");
        for (int i = 0; i < allElements.getLength(); i++) {
            Node n = allElements.item(i);
            if (n instanceof Element) {
                Element elem = (Element) n;
                if (elem.hasAttribute(XMLDefinitions.IMAGE)) {
                    String imgPath = elem.getAttribute(XMLDefinitions.IMAGE);
                    if (imgPath != null && !imgPath.trim().isEmpty()) {
                        File f = new File(imgPath);
                        if (folder != null) {
                            f = new File(folder, imgPath);
                        }
                        if (f.exists()) {
                            files.add(f);
                        }
                    }
                }
            }
        }
        return files;
    }

    public int parseXMLDocument(GenerateBean bean, Document document, PdfWriter writer) throws Exception {
        document.open();
        int pageCount = 0;
        try {
            org.w3c.dom.Document xmlDoc = factory.getDocument(bean.getInputFile());
            if (xmlDoc != null) {
                Set<File> imageFiles = collectImageFiles(xmlDoc);
                if (!imageFiles.isEmpty()) {
                    imageFiles.parallelStream().forEach(file -> ImageCache.getInstance().getImage(file));
                }

                float boundsWidth = PdfUtil.convertFromMillimeters(config.getWidth() - config.getMarginLeft() - config.getMarginRight());
                float center = (boundsWidth / 2.0f + PdfUtil.convertFromMillimeters(config.getMarginLeft()));
                NodeList albums = xmlDoc.getElementsByTagName(XMLDefinitions.ALBUM);
                if (albums != null && albums.getLength() > 0) {
                    Element album = (Element) albums.item(0);
                    NodeList nodes = album.getChildNodes();
                    List<Element> pageElements = new ArrayList<>();
                    if (nodes != null) {
                        for (int i = 0; i < nodes.getLength(); i++) {
                            Node node = nodes.item(i);
                            if (node.getNodeType() == Node.ELEMENT_NODE) {
                                Element elm = (Element) node;
                                if (elm.getTagName().equals(XMLDefinitions.PAGE) || elm.getTagName().equals(XMLDefinitions.TITLE_PAGE)) {
                                    pageElements.add(elm);
                                }
                            }
                        }
                    }
                    pageCount = pageElements.size();
                    EventBus.publish(new StatusEvent(StatusType.MaximumProgress, pageCount));

                    List<ParsedPageHolder> parsedPages = new ArrayList<>(pageCount);
                    for (int i = 0; i < pageCount; i++) {
                        Element elm = pageElements.get(i);
                        Object parsedObj = factory.getParser(elm.getTagName()).parse(elm, config);
                        parsedPages.add(new ParsedPageHolder(i + 1, elm, parsedObj));
                    }

                    if (bean.isReversePages()) {
                        for (int p = pageCount - 1; p >= 0; p--) {
                            ParsedPageHolder holder = parsedPages.get(p);
                            renderParsedPage(bean, writer, center, holder.element, holder.parsedPage, holder.pageIndex);
                            if (p > 0) {
                                document.newPage();
                            }
                        }
                    } else {
                        for (int p = 0; p < pageCount; p++) {
                            ParsedPageHolder holder = parsedPages.get(p);
                            renderParsedPage(bean, writer, center, holder.element, holder.parsedPage, holder.pageIndex);
                            if (p < pageCount - 1) {
                                document.newPage();
                            }
                        }
                    }
                }
            }
        } catch (Exception t) {
            t.printStackTrace();
            throw new RuntimeException(t);
        } finally {
            document.close();
        }
        return pageCount;
    }

    protected void generatePage(GenerateBean bean, PdfWriter writer, float center, Element elm, int currentPage) {
        Object p = factory.getParser(elm.getTagName()).parse(elm, config);
        renderParsedPage(bean, writer, center, elm, p, currentPage);
    }

    protected void renderParsedPage(GenerateBean bean, PdfWriter writer, float center, Element elm, Object p, int currentPage) {
        EventBus.publish(new StatusEvent(StatusType.Progress, currentPage));
        if (generatingPageMsg == null) {
            generatingPageMsg = Resources.getString("message.generatingPage");
        }
        EventBus.publish(new StatusEvent(StatusType.Message, MessageFormat.format(generatingPageMsg, (currentPage))));
        if (p != null) {
            if (bean.isDrawBorder() || debug || (elm.hasAttribute("border") && Boolean.parseBoolean(elm.getAttribute("border")))) {
                PdfContentByte handler = writer.getDirectContent();
                float width = PdfUtil.convertFromMillimeters(config.getWidth() - config.getMarginLeft() - config.getMarginRight());
                float height = PdfUtil.convertFromMillimeters(config.getHeight() - config.getMarginTop() - config.getMarginBottom());
                handler.rectangle(PdfUtil.convertFromMillimeters(config.getMarginLeft()), PdfUtil.convertFromMillimeters(config.getMarginBottom()), width, height);
                handler.stroke();
            }
            if (p instanceof Page) {
                Page page = (Page) p;
                ISetContent[] content = new ISetContent[page.getContent().size()];
                content = page.getContent().toArray(content);
                createPage(writer, center, page.getTitle(), content);
            } else if (p instanceof TitlePage) {
                TitlePage page = (TitlePage) p;
                createTitlePage(writer, center, page.getTitlePageContent());
            }
        }
    }
}
