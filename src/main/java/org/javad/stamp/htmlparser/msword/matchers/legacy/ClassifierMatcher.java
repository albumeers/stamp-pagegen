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
package org.javad.stamp.htmlparser.msword.matchers.legacy;

import java.util.logging.Level;
import java.util.logging.Logger;
import java.util.regex.Matcher;
import org.htmlparser.Node;
import org.htmlparser.tags.ParagraphTag;
import org.htmlparser.tags.Span;
import org.htmlparser.util.ParserException;
import org.javad.stamp.htmlparser.HtmlHelper;
import org.javad.stamp.htmlparser.msword.NodeListProcessor;
import org.javad.stamp.htmlparser.msword.matchers.NodeMatcher;
import org.javad.stamp.htmlparser.msword.styles.ComponentType;
import org.javad.stamp.htmlparser.msword.styles.LegacyPageStyle;
import org.javad.stamp.htmlparser.msword.styles.MatcherFactory;
import static org.javad.stamp.htmlparser.msword.styles.MatcherFactory.NUMBERS;
import org.javad.stamp.htmlparser.msword.styles.PageStyle;

/**
 *
 * @author Jason
 */
public class ClassifierMatcher extends NodeMatcher {

    private final NodeListProcessor processor = new NodeListProcessor();

    private boolean checkSize(String fontSize) {
        if (fontSize != null) {
            Matcher matcher = NUMBERS.matcher(fontSize.trim());
            if (matcher.find()) {
                float size = Float.valueOf(matcher.group(0));
                return (size > 8.5f && size < 12.0f);
            }
        }
        return false;
    }
    
    private boolean checkBottomMargin(Node n) {
        Node parent = n.getParent();
        if (parent instanceof ParagraphTag) {
            ParagraphTag pTag = (ParagraphTag) parent;
            String style = pTag.getAttribute("style");
            if (style != null) {
                String marginBottom = HtmlHelper.extractValueFromStyle(style, "margin-bottom");
                if (marginBottom != null) {
                    Matcher matcher = NUMBERS.matcher(marginBottom.trim());
                    if (matcher.find()) {
                        float mb = Float.valueOf(matcher.group(0));
                        return ( mb > 5.09f );
                    }
                }
            }
        }
        return false;
    }
    
    private boolean checkForTitleAsPeer(Node n) {
        Node parent = processor.findParentByTagName(n, "P");
        Node sibling = processor.findPredecessorSibling(parent);
        if( sibling != null ) {
            Node td = processor.findParentByTagName(sibling, "TD");
            if( td != null && td.getChildren().indexOf(sibling) > 10) {
                return false;
            }
            try {
                PageStyle style = new LegacyPageStyle();
                return processor.findChildren(sibling.getChildren(), MatcherFactory.getInstance(style).getMatcher(ComponentType.Title)).size() > 0;
            } catch (ParserException ex) {
                Logger.getLogger(ClassifierMatcher.class.getName()).log(Level.SEVERE, null, ex);
            }
        }
        return false;
    }

    @Override
    public boolean matches(Node n) {
        if (n instanceof Span) {
            Span span = (Span) n;
            String style = span.getAttribute("style");
            if (style != null) {
                String fontSize = HtmlHelper.extractValueFromStyle(style, "font-size");
                return checkSize(fontSize) && checkBottomMargin(n) && checkForTitleAsPeer(n);
            }
        }
        return false;
    }
}
