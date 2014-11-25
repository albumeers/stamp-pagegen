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

import java.lang.reflect.Method;
import java.util.ArrayList;
import java.util.Collection;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.logging.Level;
import java.util.logging.Logger;
import java.util.prefs.Preferences;

import com.itextpdf.text.Font;
import com.itextpdf.text.FontFactory;
import com.itextpdf.text.pdf.BaseFont;
import java.util.prefs.BackingStoreException;

public class FontRegistry {

	public static final String PREFERENCE_USAGE = "usage";
	public static final String PREFERENCE_MAPPING = "mapping";
	
	public static final String FILE_FONTPATH = "file.fontPath";
	private static final Logger logger = Logger.getLogger(FontRegistry.class.getName());
	
	private static FontRegistry factory = null;
	
	private Map<PdfFontDefinition,PdfFontBean> fontMap = null;
	private Collection<PdfFontMapping> fontMappings = null;
	private final Map<PdfFontBean,Font> calculatedFonts = new HashMap<>();
	
	private String fontPath;
	private boolean registered = false;
	
	protected FontRegistry() {
		super();
	}
	
	public static FontRegistry getInstance() {
		if( factory == null ) {
			factory = new FontRegistry();
		}
		return factory;
	}

	public static Preferences getPreferencesNode() {
		return Preferences.userNodeForPackage(FontRegistry.class);
	}
	
	public void register() {
		registered = false;
	}
	
	public void initializeFontPath( ) {
		Preferences prefs = getPreferencesNode();
		String path = prefs.get(FILE_FONTPATH,null);
		setFontPath(path);
	}
	
	public void initializeFonts() {
		if( !registered ) {
			String path = getFontPath();
			if( path != null ) {
				FontFactory.registerDirectory(path,true);
				if( logger.isLoggable(Level.FINEST)) {
					logger.finest(FontFactory.getRegisteredFonts().toString());
				}
			}
			registered = true;
		}
	}
	
	protected void initializeFontTable() {
		if( fontMap != null && !fontMap.isEmpty()) {
			return;
		}
		fontMap = new HashMap<>();
		calculatedFonts.clear();
		Preferences prefs = getPreferencesNode();
		try {
			Preferences bean = prefs.node(PREFERENCE_USAGE);
			for(PdfFontDefinition usage: PdfFontDefinition.values()) {
                            String value = bean.get(usage.toString(), null);
                            PdfFontBean b;
                            if (value != null) {
                                b = PdfFontBean.fromString(value);
                                b.setFontDefinition(usage);
                            } else {
                                b = new PdfFontBean();
                                b.setFontDefinition(usage);
                                b.setSize(usage.getDefaultSize());
                                b.setFontFamily(usage.getDefaultTypeFace());
                                b.setStyle(usage.getDefaultStyle());
                                b.setSystem(true);
                            }

                            if (usage == PdfFontDefinition.ExtendedCharacters) {
                                b.setI18N(true);
                            }
                            fontMap.put(b.getFontDefinition(), b);
			}
		} catch (Exception e) {
			logger.log(Level.FINE, "There was an issue reading the font usages:", e);
		}
		
	}
	
	/**
	 * Retrieves the font mappings from the preferences using the fully qualified preference
	 * node path
	 * 
	 *  <pre>/org/javad/pdf/fonts/mapping</pre>
	 * 
	 * @return  The collection of current font mappings.
	 */
	public Collection<PdfFontMapping> getFontMappings() {
		if( fontMappings != null ) {
			return fontMappings;
		}
		fontMappings = new ArrayList<>();
		Preferences prefs = getPreferencesNode();
		try {
			Preferences mapping = prefs.node(PREFERENCE_MAPPING);
			for(String alias: mapping.keys()) {
				PdfFontMapping ref = new PdfFontMapping();
				ref.setFontAlias(alias);
				ref.setFilePath(mapping.get(alias,null));
				fontMappings.add(ref);
			}
		} catch (BackingStoreException e) {
			logger.log(Level.FINE, "There was an issue reading the font mappings: ", e);
		}
		return fontMappings;
	}
	
	
	
	
	public Collection<PdfFontBean> getFontBeans() {
		initializeFontTable();
		List<PdfFontBean> beans = new ArrayList<>(fontMap.values());
		Collections.sort(beans);
		return beans;
	}
	
	public void setFontBeans(Collection<PdfFontBean> beans) {
		Preferences prefs = getPreferencesNode();
		try {
			if( prefs.nodeExists(PREFERENCE_USAGE)) {
				Preferences mapping = prefs.node(PREFERENCE_USAGE);
				mapping.removeNode();
				prefs.flush();
				mapping = prefs.node(PREFERENCE_USAGE);
				if( beans != null ) {
					for( PdfFontBean ref: beans ) {
						mapping.put(ref.getFontDefinition().toString(), ref.asString());
					}
				}
				prefs.flush();
				fontMap = null;
			}
		} catch( BackingStoreException e ) {
			logger.log(Level.FINE,"There is an issue saving the font bean: ", e);
		}
	}
	
	public void setFontMappings(Collection<PdfFontMapping> references) {
		Preferences prefs = getPreferencesNode();
		try {
			if( prefs.nodeExists(PREFERENCE_MAPPING)) {
				Preferences mapping = prefs.node(PREFERENCE_MAPPING);
				mapping.removeNode();
				prefs.flush();
				mapping = prefs.node(PREFERENCE_MAPPING);
				if( references != null ) {
					for( PdfFontMapping ref: references ) {
						mapping.put(ref.getFontAlias(), ref.getFilePath());
					}
				}
				prefs.flush();
				fontMappings = null;
			}
		} catch( BackingStoreException e ) {
			logger.log(Level.FINE,"There is an issue saving the font mappings: ", e);
		}
	}
	
	public void setFontPath(String fontPath) {
		this.fontPath = fontPath;
		registered = false;
	}
	
	public String getFontPath() {
		if( fontPath == null ) {
			logger.info("No font path is set.  Attempting to determine system font path.");
			fontPath = getNativeFontPath();
		}
		return fontPath;
	}
	
	protected String getNativeFontPath( ) {
		String path = null;
		String operating_system = System.getProperty("os.name");
		if( operating_system != null && operating_system.toLowerCase().contains("windows")) {
			path = "c:\\Windows\\Fonts";
		} else {
			path = System.getenv("JAVA_FONTS");
		}
		try {
			Class<?> clazz = Class.forName("sun.font.FontManager");
			if( clazz != null ) {
				Method m = clazz.getDeclaredMethod("getFontPath", boolean.class);
				if( m != null ) {
					path = m.invoke(null,true).toString();
				}
			}
		} catch( Exception t ) {
			logger.info("Non Oracle Java VM detected.  No font path is available.");
		}
		logger.log(Level.FINE, "Calculated system font path is \"{0}\"", path);
		return path;
	}
	
	public Font getFont(PdfFontDefinition name) {
		Font f = null;
		initializeFontTable();
		PdfFontBean bean = fontMap.get(name);
		if( bean == null ) {
			throw new IllegalArgumentException("The name \"" + name.toString() + "\" was not found in the mapping.");
		}
		if( calculatedFonts.containsKey(bean)) {
			return calculatedFonts.get(bean);
		}
		if( bean.isSystem()) {
			initializeFonts();
			f = findFont(bean.getFontFamily(), bean);
		} else if( bean.getFontMapping() != null ){
			logger.log(Level.FINE, "Using a mapped font for \"{0}\"", name);
			PdfFontMapping mapping = bean.getFontMapping();
			FontFactory.register(mapping.getFilePath(), mapping.getFontAlias());
			f = findFont(mapping.getFontAlias(), bean);
		}
		if( isFontInvalid(f) ) {
			logger.log(Level.INFO, "Unable to find a registered font for \"{0}\" using default of Helvetica", name);
			f = FontFactory.getFont(FontFactory.HELVETICA, name.getDefaultSize(), name.getDefaultStyle());
		}
		calculatedFonts.put(bean, f);
		return f;
	}

	/**
	 * This method will attempt to find the named font with the specified size and style
	 * using a naming roll-off technique based on some of the naming conventions observed.
	 * <ul><li>
	 * If the style is bold and italic, a font with the name <code>"[name]-bolditalic"</code>
	 * will attempted. </li>
	 * <li>If the style is both a name like <code>"[name] bold"</code> will be
	 * attempted.</li>
	 * <li>If the font is italic, the names <code>"[name] italic"</code> and then
	 * <code>"[name]-italic"</code> will be tried.</li>
	 * <li> Finally if none of these styled fonts can be located, the <code>"[name]"</code> will be tried.</li>
	 * </ul>
	 * 
	 * @param name
	 * @param bean
	 * @return
	 */
	Font findFont(String name, PdfFontBean bean) {
                String form = (bean.isI18N()) ? BaseFont.IDENTITY_H : BaseFont.CP1252;
		Font f = null;
		if( bean.isBold() && bean.isItalic()) {
			f = FontFactory.getFont(name + "-bolditalic", form, bean.getSize(), bean.getStyle());
		} 
		if( isFontInvalid(f)  && bean.isBold()) {
			f = FontFactory.getFont(name + " bold", form, bean.getSize(), bean.getStyle());
		}
		if( isFontInvalid(f) && bean.isItalic()) {
			f = FontFactory.getFont(name + " italic", form, bean.getSize(), bean.getStyle());
			if( isFontInvalid(f) )  {
				f = FontFactory.getFont(name + "-italic", form, bean.getSize(), bean.getStyle());
			}
		}
		if( isFontInvalid(f) ) {
                    f = FontFactory.getFont(name, form, bean.getSize(), bean.getStyle());
		}
		if( logger.isLoggable(Level.FINER)) {
                        @SuppressWarnings("null")
			BaseFont bf = f.getBaseFont();
			if( bf != null ) {
				String[][] fullName = bf.getFullFontName();
				if( fullName != null && fullName.length >= 1 && fullName[0].length >= 4 ) {
					logger.log(Level.FINER, "The calculated font name is \"{0}\"", fullName[0][3]);
				} else {
					logger.finer("The base font full name was not parseable.");
				}
			} else {
				logger.log(Level.FINER, "The base font was null for \"{0}\" with style {1}", new Object[]{name, bean.getStyle()});
			}
		}
		return f;
	}

        @SuppressWarnings("null")
	private boolean isFontInvalid(Font f ) {
		return (f == null || (f != null && f.getBaseFont() == null));
	}
}
