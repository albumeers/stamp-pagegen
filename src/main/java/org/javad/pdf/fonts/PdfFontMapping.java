package org.javad.pdf.fonts;

import java.text.MessageFormat;
import java.util.logging.Level;
import java.util.logging.Logger;

import org.javad.stamp.pdf.Resources;

import com.itextpdf.text.pdf.BaseFont;

public class PdfFontMapping {

	private String filePath;
	private String fontAlias;
	private boolean needsValidation = true;
	private boolean valid = false;
	private String validationMessage = null; 
	private static final Logger logger = Logger.getLogger(PdfFontMapping.class.getName());
	
	public PdfFontMapping() {
		super();
	}
	
	public String getFilePath() {
		return filePath;
	}

	public void setFilePath(String filePath) {
		this.filePath = filePath;
		needsValidation = true;
	}

	public String getFontAlias() {
		return fontAlias;
	}

	public void setFontAlias(String fontName) {
		this.fontAlias = fontName;
		needsValidation = true;
	}

	public boolean validate() {
		if( !needsValidation ) {
			return valid;
		}
		valid = false;
		if( filePath != null && fontAlias != null ) {
			try {
				BaseFont bf = BaseFont.createFont(getFilePath(), "UTF-8",true,false,null,null,false);
				if( bf != null ) {
					valid = true;
				}
			} catch( Exception e) {
				validationMessage = MessageFormat.format(Resources.getString("message.font.fontNotValid"),e.getMessage());
				logger.log(Level.FINE, "Issue registering the font \"" + fontAlias + "\" for path \"" + filePath + "\"", e);
			}
		} else {
			validationMessage = Resources.getString("message.font.invalidValue");
		}
		if( valid ) {
			validationMessage = null;
		}
		needsValidation = false;
		return valid;
	}
	
	public String getValidationMessage( ) {
		return validationMessage;
	}
	
	@Override
	public String toString() {
		return fontAlias + " - " + filePath;
	}
}
