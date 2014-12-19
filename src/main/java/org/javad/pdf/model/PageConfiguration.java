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
package org.javad.pdf.model;

import java.io.IOException;
import java.io.InputStream;
import java.util.Arrays;
import java.util.HashSet;
import java.util.Properties;
import java.util.Set;
import java.util.logging.Level;
import java.util.logging.Logger;
import java.util.prefs.BackingStoreException;
import java.util.prefs.Preferences;
import org.javad.stamp.pdf.Resources;

public class PageConfiguration {

	private static final Logger logger = Logger.getLogger(PageConfiguration.class.getName());
	
	private String name;
	private String displayName;
	
	private boolean systemConfiguration = false;
	
	private float width;
	private float height;
	private float marginLeft;
	private float marginTop;
	private float marginBottom;
	private float marginRight;
	private float verticalSpacing;
	private float horizontalSpacing;
        
        private Set<String> skipTerms = new HashSet<>();
	
	public static String DISPLAY_NAME = "displayName";
	public static String WIDTH = "page.width";
	public static String HEIGHT = "page.height";
	public static String MARGIN_LEFT = "margin.left";
	public static String MARGIN_TOP = "margin.top";
	public static String MARGIN_RIGHT = "margin.right";
	public static String MARGIN_BOTTOM = "margin.bottom";
	public static String HORIZONTAL_SPACING = "spacing.box.horizontal";
	public static String VERTICAL_SPACING = "spacing.box.vertical";
	
	void load() {
		Preferences prefs = Resources.getPreferencesNode().node(name);
		Properties defaults = new Properties();
		try {
			if( name == null ) {
				throw new IllegalStateException("The name is not set for the configuration");
			}
			InputStream in = getClass().getResourceAsStream("/META-INF/" + name + "-settings.xml");
			if( in != null ) {
				defaults.loadFromXML(in);
				systemConfiguration = true;
			}
		} catch( IOException ie ) {
			logger.log(Level.WARNING,"The settings file was not found.", ie);
		}
		setDisplayName(defaults.getProperty(DISPLAY_NAME, null));
		setWidth(prefs.getFloat(WIDTH, Float.valueOf((defaults.containsKey(WIDTH)) ? defaults.getProperty(WIDTH) : "0")));
		setHeight(prefs.getFloat(HEIGHT, Float.valueOf((defaults.containsKey(HEIGHT)) ? defaults.getProperty(HEIGHT) : "0")));
		setMarginLeft(prefs.getFloat(MARGIN_LEFT, Float.valueOf((defaults.containsKey(MARGIN_LEFT)) ? defaults.getProperty(MARGIN_LEFT) : "0")));
		setMarginTop(prefs.getFloat(MARGIN_TOP, Float.valueOf((defaults.containsKey(MARGIN_TOP)) ? defaults.getProperty(MARGIN_TOP) : "0")));
		setMarginRight(prefs.getFloat(MARGIN_RIGHT, Float.valueOf((defaults.containsKey(MARGIN_RIGHT)) ? defaults.getProperty(MARGIN_RIGHT) : "0")));
		setMarginBottom(prefs.getFloat(MARGIN_BOTTOM, Float.valueOf((defaults.containsKey(MARGIN_BOTTOM)) ? defaults.getProperty(MARGIN_BOTTOM) : "0")));
		setHorizontalSpacing(prefs.getFloat(HORIZONTAL_SPACING, Float.valueOf((defaults.containsKey(HORIZONTAL_SPACING)) ? defaults.getProperty(HORIZONTAL_SPACING) : "0")));
		setVerticalSpacing(prefs.getFloat(VERTICAL_SPACING, Float.valueOf((defaults.containsKey(VERTICAL_SPACING)) ? defaults.getProperty(VERTICAL_SPACING) : "0")));
	}
	
	public boolean isSystemConfiguration( ) {
		return systemConfiguration;
	}
	
	void revert() {
		Preferences prefs = Resources.getPreferencesNode().node(name);
		try {
			prefs.removeNode();
			Resources.getPreferencesNode().remove(name);
		} catch (BackingStoreException e) {
			logger.log(Level.WARNING, "The preference for " + name + " was unable to be reverted.", e);
		}
		load();
	}
	
	void save() {
		Preferences prefs = Resources.getPreferencesNode().node(name);
		prefs.putFloat(WIDTH, getWidth());
		prefs.putFloat(HEIGHT, getHeight());
		prefs.putFloat(MARGIN_LEFT, getMarginLeft());
		prefs.putFloat(MARGIN_TOP,getMarginTop());
		prefs.putFloat(MARGIN_RIGHT, getMarginRight());
		prefs.putFloat(MARGIN_BOTTOM, getMarginBottom());
		prefs.putFloat(HORIZONTAL_SPACING, getHorizontalSpacing());
		prefs.putFloat(VERTICAL_SPACING, getVerticalSpacing());
		logger.info("Saved configuration for \"" + ((displayName != null ) ? displayName : name) + "\"");
	}
	
	public PageConfiguration duplicate() {
		PageConfiguration config = new PageConfiguration(getName());
		config.setDisplayName(getDisplayName());
		config.setHeight(getHeight());
		config.setWidth(getWidth());
		config.setHorizontalSpacing(getHorizontalSpacing());
		config.setVerticalSpacing(getVerticalSpacing());
		config.setMarginBottom(getMarginBottom());
		config.setMarginLeft(getMarginLeft());
		config.setMarginRight(getMarginRight());
		config.setMarginTop(getMarginTop());
		return config;
	}
	
	public PageConfiguration(String name) {
		this.name = name;
	}
	
	public String getName() {
		return name;
	}

	public void setName(String name) {
		this.name = name;
	}

	public String getDisplayName() {
		return displayName == null ? name : displayName;
	}

	public void setDisplayName(String displayName) {
		this.displayName = displayName;
	}	
	
	public float getWidth() {
		return width;
	}
        public float getUsableWidth() {
            return width - marginLeft - marginRight;
        }
	public void setWidth(float width) {
		this.width = width;
	}
	public float getHeight() {
		return height;
	}
	public void setHeight(float height) {
		this.height = height;
	}
	public float getMarginLeft() {
		return marginLeft;
	}
	public void setMarginLeft(float marginLeft) {
		this.marginLeft = marginLeft;
	}
        
        public Set<String> getSkipTerms() {
            return skipTerms;
        }
        
        public void parseSkipTerms( String text ) {
            skipTerms.clear();
            if( text != null && !text.isEmpty()) {
                skipTerms.addAll(Arrays.asList(text.split(" ")));
            }
        }
        
	public float getMarginTop() {
		return marginTop;
	}
	public void setMarginTop(float marginTop) {
		this.marginTop = marginTop;
	}
	public float getMarginBottom() {
		return marginBottom;
	}
	public void setMarginBottom(float marginBottom) {
		this.marginBottom = marginBottom;
	}
	public float getMarginRight() {
		return marginRight;
	}
	public void setMarginRight(float marginRight) {
		this.marginRight = marginRight;
	}
	public float getVerticalSpacing() {
		return verticalSpacing;
	}
	public void setVerticalSpacing(float verticalSpacing) {
		this.verticalSpacing = verticalSpacing;
	}
	public float getHorizontalSpacing() {
		return horizontalSpacing;
	}
	public void setHorizontalSpacing(float horizontalSpacing) {
		this.horizontalSpacing = horizontalSpacing;
	}
	
	
}
