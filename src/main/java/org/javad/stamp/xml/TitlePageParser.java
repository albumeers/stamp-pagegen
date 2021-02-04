/*
 Copyright 2021 Jason Drake (jadrake75@gmail.com)
 
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

import java.awt.image.BufferedImage;
import java.io.File;
import java.io.IOException;
import java.util.Set;
import java.util.logging.Level;
import java.util.logging.Logger;
import javax.imageio.ImageIO;
import org.javad.pdf.TitlePage;
import org.javad.pdf.TitlePageContent;
import org.javad.pdf.model.PageConfiguration;
import org.w3c.dom.Element;
import org.w3c.dom.Node;
import org.w3c.dom.NodeList;

/**
 *
 */
public class TitlePageParser extends AbstractXMLParser<TitlePage> implements XMLDefinitions {

    private static final Logger logger = Logger.getLogger(TitlePageParser.class.getName());

    @SuppressWarnings("unchecked")
	@Override
    public TitlePage parse(Element element, PageConfiguration configuration) {
        Set<String> skipTerms = configuration.getSkipTerms();
        if (element.hasAttribute(SKIP) && !skipTerms.isEmpty()) {
            for (String t : element.getAttribute(SKIP).split(" ")) {
                if (skipTerms.contains(t)) {
                    return null;
                }
            }
        }
        TitlePage p = new TitlePage();
        TitlePageContent pt = new TitlePageContent(configuration);
        p.setTitlePageContent(pt);
        if (element.hasAttribute(TITLE)) {
        	pt.setTitle(element.getAttribute(TITLE).replace("\\n","\n"));
        }
        if (element.hasAttribute(SUBTITLE)) {
        	pt.setSubTitle(element.getAttribute(SUBTITLE).replace("\\n","\n"));
        }
        if (element.hasAttribute(DESCRIPTION)) {
        	pt.setDescription(element.getAttribute(DESCRIPTION).replace("\\n","\n"));
        }
        if (element.hasAttribute(IMAGE)) {
            String imagePath = element.getAttribute(IMAGE);
            try {
                File imageFile = new File(imagePath);
                File folder = getFactory().getWorkingFolder();
                if (folder != null) {
                    imageFile = new File(folder, imagePath);
                }
                if (imageFile.exists()) {
                    BufferedImage img = ImageIO.read(imageFile);
                    pt.setImage(img);
                } else {
                    logger.log(Level.WARNING, "The image file: {0} was not found relative to the album xml file.", imagePath);
                }
            } catch (IOException e) {
                logger.log(Level.WARNING, "Could not load the image " + imagePath, e);
            }
        }
        if (element.hasChildNodes()) {
            NodeList children = element.getChildNodes();
            if (children != null) {
                for (int i = 0; i < children.getLength(); i++) {
                    Node elm = (Node) children.item(i);
                    if (elm.getNodeName().equals(CONTENT_ITEMS)) {
                        NodeList contentChildren = elm.getChildNodes();
                        if (contentChildren != null) {
                            for (int j = 0; j < contentChildren.getLength(); j++) {
                                Node c_elm = (Node) contentChildren.item(j);
                                if (c_elm.getNodeName().equals(ITEM)) {
                                    String item = c_elm.getTextContent();
                                    pt.getItems().add(item);
                                }
                            }
                        }
                    }
                }
            }
        }
        return p;
    }

}
