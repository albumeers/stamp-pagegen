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
