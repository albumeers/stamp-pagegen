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
package org.javad.stamp.htmlparser.msword.styles;

import java.io.IOException;
import java.util.HashMap;
import java.util.Map;
import java.util.Properties;
import java.util.logging.Level;
import java.util.logging.Logger;
import java.util.regex.Pattern;
import org.javad.stamp.htmlparser.msword.matchers.NodeMatcher;
import org.javad.stamp.xml.StampXMLParserFactory;
import org.javad.xml.IXMLContentParser;

/**
 *
 * @author Jason
 */
public class MatcherFactory {
    
    private static Map<PageStyle,MatcherFactory> factories = new HashMap<>();
    private static final Logger logger = Logger.getLogger(MatcherFactory.class.getName());
    
    public static final Pattern NUMBERS = Pattern.compile("^([-+]?[0-9]*\\.?[0-9]*)+");
    
    private final Map<ComponentType, NodeMatcher> matchers = new HashMap<>();

    
    public static MatcherFactory getInstance(PageStyle style) {
        MatcherFactory factory = factories.get(style);
        if( factory == null ) {
            factory = new MatcherFactory();
            factory.initialize(style);
            factories.put(style, factory);
        }
        return factory;
    }
    
    
    @SuppressWarnings({"BroadCatchBlock", "TooBroadCatch", "UseSpecificCatch", "CallToPrintStackTrace"})
    private void initialize(PageStyle style) {
        Properties props = new Properties();
        try {
            props.loadFromXML(getClass().getResourceAsStream("/META-INF/html-legacy-parsers.xml"));
            for (Map.Entry<Object, Object> entry : props.entrySet()) {
                try {
                    Class<?> clazz = Class.forName(entry.getValue().toString());
                    if (clazz != null && NodeMatcher.class.isAssignableFrom(clazz)) {
                        matchers.put(ComponentType.valueOf(entry.getKey().toString()), (NodeMatcher) clazz.newInstance());
                    }
                } catch (Exception e) {
                    e.printStackTrace();
                }

            }
        } catch (IOException e) {
            logger.log(Level.SEVERE, "An error occured configuring the XML parsers", e);
        }
    }
    
    public NodeMatcher getMatcher(ComponentType style) {
        return matchers.get(style);
    }

    
}
