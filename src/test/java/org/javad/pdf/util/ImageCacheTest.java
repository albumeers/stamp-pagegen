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

import static org.junit.jupiter.api.Assertions.*;

import java.io.File;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import com.itextpdf.text.Image;

public class ImageCacheTest {

    private ImageCache cache;

    @BeforeEach
    public void setUp() {
        cache = ImageCache.getInstance();
        cache.clear();
    }

    @Test
    public void testGetInstance() {
        assertNotNull(ImageCache.getInstance(), "ImageCache instance should not be null");
    }

    @Test
    public void testGetImageNullOrMissingFile() {
        assertNull(cache.getImage(null), "Null file should return null");
        assertNull(cache.getImage(new File("non_existent_file_12345.png")), "Non-existent file should return null");
    }

    @Test
    public void testGetImageCaching() {
        File sampleImage = new File("src/test/resources/images/symbol.png");
        if (sampleImage.exists()) {
            Image img1 = cache.getImage(sampleImage);
            assertNotNull(img1, "Cached image should not be null for existing file");
            assertEquals(1, cache.size(), "Cache size should be 1");

            Image img2 = cache.getImage(sampleImage);
            assertNotNull(img2, "Second retrieval should not be null");
            assertEquals(1, cache.size(), "Cache size should still be 1 after retrieving cached image");
            assertNotSame(img1, img2, "Each call should return a independent Image instance copy");
        }
    }
}
