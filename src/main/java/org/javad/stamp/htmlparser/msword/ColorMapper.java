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

import java.io.IOException;
import java.util.Properties;
import java.util.logging.Level;
import java.util.logging.Logger;

/**
 *
 * @author Jason
 */
public class ColorMapper {

    private Properties properties = new Properties();
    private boolean loaded = false;
    private static ColorMapper factory;

    public static ColorMapper getInstance() {
        if (factory == null) {
            factory = new ColorMapper();
            factory.initialize();
        }
        return factory;
    }

    private void initialize() {
        if (!loaded) {
            try {
                properties.load(ColorMapper.class.getResourceAsStream("/META-INF/color-mappings.properties"));
                loaded = true;
            } catch (IOException ex) {
                Logger.getLogger(ColorMapper.class.getName()).log(Level.SEVERE, null, ex);
            }
        }
    }

    public String normalizeText(String text) {
        for(Object key: properties.keySet()) {
            text = text.replace(key.toString(), properties.getProperty(key.toString()));
        }
        return text;
    }
}
