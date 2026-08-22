package org.javad.stamp.pdf.ui.model;

import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.junit.jupiter.api.Assertions.assertFalse;

import org.junit.jupiter.api.Test;

public class GenerateBeanTest {

	@Test
	public void testDefaultDrawBorderIsTrue() {
		GenerateBean bean = new GenerateBean();
		assertTrue(bean.isDrawBorder(), "Draw border should default to true in GenerateBean");
	}

	@Test
	public void testSetDrawBorder() {
		GenerateBean bean = new GenerateBean();
		bean.setDrawBorder(false);
		assertFalse(bean.isDrawBorder(), "Draw border should be false after setting to false");
	}
}
