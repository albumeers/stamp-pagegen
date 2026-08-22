/*
 Copyright 2026 Jason Drake (jadrake75@gmail.com)
 
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
package org.javad.pdf.util;

import com.itextpdf.text.Image;
import java.io.File;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.logging.Level;
import java.util.logging.Logger;

public class ImageCache {

    private static final Logger logger = Logger.getLogger(ImageCache.class.getName());
    private static final ImageCache INSTANCE = new ImageCache();

    private final Map<String, Image> cache = new ConcurrentHashMap<>();

    private ImageCache() {
    }

    public static ImageCache getInstance() {
        return INSTANCE;
    }

    public Image getImage(File file) {
        if (file == null || !file.exists()) {
            return null;
        }
        try {
            String key = file.getCanonicalPath();
            Image template = cache.get(key);
            if (template == null) {
                template = Image.getInstance(key);
                if (template != null) {
                    cache.put(key, template);
                }
            }
            if (template != null) {
                return Image.getInstance(template);
            }
        } catch (Exception e) {
            logger.log(Level.WARNING, "Could not load image from file: " + file.getPath(), e);
        }
        return null;
    }

    public void clear() {
        cache.clear();
    }

    public int size() {
        return cache.size();
    }
}
