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

import java.util.MissingResourceException;
import java.util.ResourceBundle;
import java.util.prefs.Preferences;

import javax.swing.Icon;
import javax.swing.ImageIcon;


public class Resources {
	private static final String BUNDLE_NAME = "org.javad.stamp.pdf.ui.messages"; //$NON-NLS-1$
	private static final String IMAGE_NAME = "org.javad.stamp.pdf.ui.icons"; //$NON-NLS-1$
	
	private static final ResourceBundle RESOURCE_BUNDLE = ResourceBundle.getBundle(BUNDLE_NAME);

	private Resources() {
	}

	
	
	private static final ResourceBundle IMAGE_BUNDLE = ResourceBundle.getBundle(IMAGE_NAME);
	
	public static String getIconName( String key ) {
		try {
			return IMAGE_BUNDLE.getString(key);
		} catch(MissingResourceException e ) {
			return '!' + key + '!';
		}
	}
	
	
	public static Icon getIcon(String key) {
		return new ImageIcon( Resources.class.getResource(getIconName(key)));
	}
	
	public static String getString(String key) {
		try {
			return RESOURCE_BUNDLE.getString(key);
		} catch (MissingResourceException e) {
			return '!' + key + '!';
		}
	}
	
	public static Preferences getPreferencesNode() {
		return Preferences.userNodeForPackage(Resources.class);
	}
}
