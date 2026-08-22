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
