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
		if (System.getProperty("os.name", "").toLowerCase().contains("windows") ||
		    new java.io.File("/usr/share/fonts").exists() ||
		    new java.io.File("/usr/local/share/fonts").exists() ||
		    System.getenv("JAVA_FONTS") != null) {
			assertNotNull(path, "Font path should be resolved on systems with available font directories");
		}
	}
}
