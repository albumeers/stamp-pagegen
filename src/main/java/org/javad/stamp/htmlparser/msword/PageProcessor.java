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

import java.util.logging.Level;
import java.util.logging.Logger;
import org.htmlparser.Node;
import org.htmlparser.util.NodeList;
import org.htmlparser.util.ParserException;
import org.javad.pdf.Page;
import org.javad.pdf.PageTitle;
import org.javad.pdf.util.PdfUtil;
import org.javad.stamp.htmlparser.HtmlHelper;
import org.javad.stamp.htmlparser.msword.matchers.TextNodeMatcher;
import org.javad.stamp.htmlparser.msword.styles.ComponentType;
import org.javad.stamp.htmlparser.msword.styles.MatcherFactory;
import org.javad.stamp.htmlparser.msword.styles.PageStyle;
import org.javad.stamp.pdf.StampSet;

/**
 *
 * @author Jason
 */
public class PageProcessor extends AbstractProcessor<Page> {
    
    private MatcherFactory factory;
    
    private static final Logger logger = Logger.getLogger(PageProcessor.class.getName());
    
    public PageProcessor(PageStyle style) {
        super(style);
        factory = MatcherFactory.getInstance(style);
    }
    
    @Override
    public Page process(Node pageNode, Node notUsed) {
        Page page = new Page();
        try {
            page.setTitle(processPageTitle(pageNode));
            NodeList stampSets = getNodeListProcessor().findChildren(pageNode.getChildren(), factory.getMatcher(ComponentType.StampSet));
            if( stampSets.size() > 0 ) {
                StampSetProcessor stampSetProcessor = new StampSetProcessor(getPageStyle());
                for(int i = 0; i < stampSets.size(); i++ ) {
                    StampSet set = stampSetProcessor.process(stampSets.elementAt(i), pageNode);
                    if( set != null ) {
                        page.addContent(set);
                    }
                }
            }
        } catch (Exception ex) {
            logger.log(Level.SEVERE, null, ex);
        }
        return page;
    }
    
    private PageTitle processPageTitle(Node pageNode) {
        PageTitle title = new PageTitle(null);
        try {
            TextNodeMatcher textMatcher = new TextNodeMatcher();
            NodeList titles = getNodeListProcessor().findChildren(pageNode.getChildren(), factory.getMatcher(ComponentType.Title));
            if( titles.size() > 0 ) {
                if( titles.size() > 1 ) {
                    for(int i = 0; i < titles.size(); i++) {
                        Node n = titles.elementAt(i);
                        NodeList textNodes = getNodeListProcessor().findChildren(titles, textMatcher);
                        String text = textNodes.elementAt(0).getText();
                        logger.warning("Unexpected title: " + text);
                    }
                    logger.warning("Was not expecting more than one title per page");
                }
                NodeList textNodes = getNodeListProcessor().findChildren(titles, textMatcher);
                String text = textNodes.elementAt(0).getText();
                text = PdfUtil.convertToProperCase(HtmlHelper.normalizeTitle(text));
                title.setTitle(text);
            }
            NodeList classifiers = getNodeListProcessor().findChildren(pageNode.getChildren(), factory.getMatcher(ComponentType.Classifier));
            if( classifiers.size() > 0 ) {
                NodeList textNodes = getNodeListProcessor().findChildren(classifiers, textMatcher);
                String text = textNodes.elementAt(0).getText();
                text = PdfUtil.convertToProperCase(HtmlHelper.normalizeTitle(text));
                title.setClassifier(text);
            }
            
            
        } catch (ParserException ex) {
            Logger.getLogger(PageProcessor.class.getName()).log(Level.SEVERE, null, ex);
        }
        return title;
    }

    
}
