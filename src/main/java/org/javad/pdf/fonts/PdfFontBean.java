/*
   Copyright 2012 Jason Drake (jadrake75@gmail.com)
 
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

import java.util.logging.Level;
import java.util.logging.Logger;

import com.itextpdf.text.Font;

public class PdfFontBean implements Comparable<PdfFontBean> {
	private PdfFontMapping reference;
	private String fontFamily;
	private PdfFontDefinition definition;
	private float size;
	private int style;
        private boolean i18n = false;
	private boolean system = true;
	
	private static final Logger logger = Logger.getLogger(PdfFontBean.class.getName());
	
	public PdfFontBean(PdfFontDefinition definition, PdfFontMapping font) {
		this();
		this.definition = definition;
		this.reference = font;
	}
	
	public PdfFontBean() {
		super();
	}
	
        public boolean isI18N() {
            return i18n;
        }
        
        public void setI18N(boolean i18N) {
            i18n = i18N;
        }
        
	public boolean isSystem() {
		return system;
	}
	
	public void setSystem(boolean system) {
		this.system = system;
	}
	
	public String getFontFamily() {
		return fontFamily;
	}

	public void setFontFamily(String fontFamily) {
		this.fontFamily = fontFamily;
	}

	public PdfFontMapping getFontMapping() {
		return reference;
	}

	public void setFontMapping(PdfFontMapping font) {
		this.reference = font;
		setSystem(false);
	}

	public PdfFontDefinition getFontDefinition() {
		return definition;
	}

	public void setFontDefinition(PdfFontDefinition usage) {
		this.definition = usage;
	}

	public float getSize() {
		return size;
	}

	public void setSize(float size) {
		this.size = size;
	}

	public int getStyle() {
		return style;
	}

	public void setStyle(int style) {
		this.style = style;
	}

	public boolean isBold() {
		return (style & Font.BOLD) > 0;
	}
	
	public boolean isItalic() {
		return (style & Font.ITALIC) > 0;
	}
	
	public boolean isUnderline() {
		return (style & Font.UNDERLINE) > 0;
	}
	
	public String asString() {
		StringBuilder buf = new StringBuilder(128);
		buf.append(Boolean.valueOf(system).toString()).append("\uFFFF");
		buf.append((system) ? fontFamily : reference.getFontAlias()).append("\uFFFF");
		buf.append(size).append("\uFFFF");
		buf.append(style).append("\uFFFF");
		return buf.toString();
	}
	
	public static PdfFontBean fromString(String str) {
		PdfFontBean bean = new PdfFontBean();
		String[] values = str.split("\uFFFF");
		if( values.length < 4 ) {
			throw new IllegalArgumentException("The value \"" + str + "\" is not a valid serialized font bean.");
		}
		bean.setSystem(Boolean.valueOf(values[0]).booleanValue());
		String family = values[1];
		if( bean.isSystem()) {
			bean.setFontFamily(family);
		} else {
			for(PdfFontMapping mapping: FontRegistry.getInstance().getFontMappings()) {
				if( mapping.getFontAlias().equals(family)) {
					bean.setFontMapping(mapping);
					break;
				}
			}
			if( bean.getFontMapping() == null ) {
				logger.log(Level.WARNING, "The font mapped to alias \"" + family + "\" was not found in the registered font mappings.");
			}
		}
		bean.setSize(Float.valueOf(values[2]).floatValue());
		bean.setStyle(Integer.valueOf(values[3]).intValue());
		return bean;
	}

	@Override
	public int compareTo(PdfFontBean o) {
		return getFontDefinition().toString().compareTo(o.getFontDefinition().toString());
	}
	
}