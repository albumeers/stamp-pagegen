package org.javad.stamp.pdf;

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
	
	
}
