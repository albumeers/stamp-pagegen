package org.javad.pdf.fonts;

import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.Collection;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

import com.itextpdf.text.Font;

public class FontRegistryTest {

	private FontRegistry fontRegistry;

	@BeforeEach
	public void setUp() {
		fontRegistry = FontRegistry.getInstance();
		fontRegistry.register();
	}

	@Test
	public void testGetInstance() {
		assertNotNull(FontRegistry.getInstance(), "FontRegistry instance should not be null");
	}

	@Test
	public void testGetFontBeans() {
		Collection<PdfFontBean> beans = fontRegistry.getFontBeans();
		assertNotNull(beans, "Font beans collection should not be null");
		assertTrue(beans.size() > 0, "Font beans collection should contain font definitions");
	}

	@Test
	public void testGetFontDefinitions() {
		for (PdfFontDefinition def : PdfFontDefinition.values()) {
			Font f = fontRegistry.getFont(def);
			assertNotNull(f, "Font for definition " + def + " should not be null");
			assertNotNull(f.getBaseFont(), "BaseFont for definition " + def + " should not be null");
		}
	}

	@Test
	public void testGetFontPath() {
		fontRegistry.setFontPath(null);
		String path = fontRegistry.getFontPath();
		assertNotNull(path, "Font path should be resolved");
	}
}
