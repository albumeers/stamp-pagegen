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
import org.htmlparser.tags.Span;
import org.javad.stamp.htmlparser.HtmlHelper;
import org.javad.stamp.htmlparser.msword.matchers.NodeMatcher;
import static org.javad.stamp.htmlparser.msword.styles.MatcherFactory.NUMBERS;

/**
 *
 * @author Jason
 */
public class TitleMatcher extends NodeMatcher {

    @Override
    public boolean matches(Node n) {
        if (n instanceof Span) {
            Span span = (Span) n;
            String style = span.getAttribute("style");
            if (style != null ) {
                String fontSize = HtmlHelper.extractValueFromStyle(style, "font-size");
                if( fontSize != null ) {
                    Matcher matcher = NUMBERS.matcher(fontSize.trim());
                    return ( matcher.find() && Float.valueOf(matcher.group(0)) > 11.0f );
                }
            }
        }
        return false;
    }
}
