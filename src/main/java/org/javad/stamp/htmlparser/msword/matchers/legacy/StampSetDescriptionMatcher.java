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

import java.util.regex.Matcher;
import org.htmlparser.Node;
import org.htmlparser.tags.ParagraphTag;
import org.htmlparser.tags.Span;
import org.htmlparser.util.NodeList;
import org.javad.stamp.htmlparser.HtmlHelper;
import org.javad.stamp.htmlparser.msword.NodeListProcessor;
import org.javad.stamp.htmlparser.msword.matchers.NodeMatcher;
import static org.javad.stamp.htmlparser.msword.styles.MatcherFactory.NUMBERS;

/**
 *
 * @author Jason
 */
public class StampSetDescriptionMatcher extends NodeMatcher {

    private final NodeListProcessor processor = new NodeListProcessor();

    private boolean checkFontSize(Span span) {
        String style = span.getAttribute("style");
        if (style != null) {
            String fontSize = HtmlHelper.extractValueFromStyle(style, "font-size");
            if (fontSize != null) {
                Matcher matcher = NUMBERS.matcher(fontSize.trim());
                if (matcher.find()) {
                    float size = Float.valueOf(matcher.group(0));
                    return (size > 6.5f && size < 9.25f);
                }
            }
        }
        return false;
    }

    private boolean checkBottomMargin(ParagraphTag pTag) {
        String style = pTag.getAttribute("style");
        if (style != null) {
            String marginBottom = HtmlHelper.extractValueFromStyle(style, "margin-bottom");
            if (marginBottom != null) {
                Matcher matcher = NUMBERS.matcher(marginBottom.trim());
                if (matcher.find()) {
                    float mb = Float.valueOf(matcher.group(0));
                    return (mb >= 0.0f && mb < 5.5f);
                }
            }
        }
        return false;
    }

    @Override
    public boolean matches(Node node) {
        if (node instanceof ParagraphTag) {
            ParagraphTag pTag = (ParagraphTag) node;
            NodeList list = processor.findChildrenByTagName(pTag, "SPAN");
            if (list != null && list.size() > 0) {
                Node first = list.elementAt(0);
                if (new TitleMatcher().matches(first) || new ClassifierMatcher().matches(first)) {
                    return false;
                } else if (checkBottomMargin(pTag) && checkFontSize((Span) first)) {
                    return true;
                }

            }

        }
        return false;
    }

}
