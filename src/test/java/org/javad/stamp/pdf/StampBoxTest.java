/*
	Copyright 2014-2026 Jason Drake (jadrake75@gmail.com)
	
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
package org.javad.stamp.pdf;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.mockito.Mockito.mock;

import org.javad.pdf.OutputBounds;
import org.javad.pdf.model.PageConfiguration;
import org.javad.pdf.model.PageConfigurations;
import org.javad.stamp.pdf.StampBox.Bisect;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.junit.jupiter.MockitoExtension;
import org.mockito.Mock;

import com.itextpdf.text.pdf.PdfContentByte;

@ExtendWith(MockitoExtension.class)
public class StampBoxTest {

	float TOLERANCE = 0.01f;
	private PageConfiguration configuration;
	
	@Mock
	PdfContentByte cByte;
	
	@BeforeEach
	public void setup() {
		PageConfigurations configs = PageConfigurations.getInstance();
		configuration = configs.getActiveConfiguration();
	}
	@Test
	public void drawBisect_TopLeft() {
		
		StampBox stamp = new StampBox(configuration);
		stamp.setBisect(Bisect.top_left);
		//PdfContentByte cByte = mock(PdfContentByte.class);
		OutputBounds rect = new OutputBounds(50,50,20,100);
		stamp.drawBisect(cByte, rect);
	}
	
	@Test
	public void drawBisect_TopRight() {
		
		StampBox stamp = new StampBox(configuration);
		stamp.setBisect(Bisect.top_right);
		//PdfContentByte cByte = mock(PdfContentByte.class);
		OutputBounds rect = new OutputBounds(50,50,20,100);
		stamp.drawBisect(cByte, rect);
	}
	
	@Test
	public void drawBisect_Vertical() {
		
		StampBox stamp = new StampBox(configuration);
		stamp.setBisect(Bisect.vertical);
		//PdfContentByte cByte = mock(PdfContentByte.class);
		OutputBounds rect = new OutputBounds(50,50,20,100);
		stamp.drawBisect(cByte, rect);
	}
	
	@Test
	public void testSetAndGetPdfImage() throws Exception {
		StampBox stamp = new StampBox(configuration);
		assertNull(stamp.getPdfImage(), "Default pdfImage should be null");
		com.itextpdf.text.Image sampleImg = com.itextpdf.text.Image.getInstance("src/test/resources/images/symbol.png");
		stamp.setPdfImage(sampleImg);
		assertEquals(sampleImg, stamp.getPdfImage(), "pdfImage getter should return set image");
	}
}
