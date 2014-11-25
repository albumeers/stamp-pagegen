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
