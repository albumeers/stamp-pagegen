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
