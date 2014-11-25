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
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Properties;
import java.util.Set;
import java.util.logging.Level;
import java.util.logging.Logger;
import java.util.prefs.BackingStoreException;
import java.util.prefs.Preferences;

import org.javad.stamp.pdf.Resources;


public class PageConfigurations {

	private Map<String,PageConfiguration> configurations = new HashMap<String,PageConfiguration>();
	private String defaultConfiguration;
	private String activeConfiguration;
	private boolean loaded = false;

	private static final Logger logger = Logger.getLogger(PageConfigurations.class.getName());
	private static PageConfigurations instance = null;
	public static final String PAGE_CONFIGURATION = "page.configuration";
	public static final String DEFAULT_CONFIGURATION = "page.configuration.default";
	
	private List<PageConfigurationChangeHandler> handlers = new ArrayList<PageConfigurationChangeHandler>();
	
	public enum PageConfigurationChangeType {
		SAVE,
		CREATE,
		LOAD,
		DELETE,
		REVERT;
	}
	
	public interface PageConfigurationChangeHandler {
		public void onPageConfigurationChanged(PageConfigurationChangeType type, PageConfiguration config);
	}
	
	protected PageConfigurations() {
		super();
	}
	
	public void addPageConfigurationChangeHandler(PageConfigurationChangeHandler handler) {
		handlers.add(handler);
	}
	
	public static PageConfigurations getInstance() {
		if( instance == null ) {
			instance = new PageConfigurations();
		}
		return instance;
	}
	
	public void load() {
		if (!loaded) {
			try {
				Properties properties = new Properties();
				InputStream in = getClass().getResourceAsStream("/META-INF/settings.xml");
				properties.loadFromXML(in);
				Set<String> configKeys = new HashSet<String>();
				String keys = properties.getProperty(PAGE_CONFIGURATION, "lighthouse");
				for (String k : keys.split(",")) {
					configKeys.add(k);
				}
				Preferences root = Resources.getPreferencesNode();
				try {
					for(String k : root.childrenNames()) {
						configKeys.add(k);
					}
				} catch (BackingStoreException e) {
					// TODO Auto-generated catch block
					e.printStackTrace();
				}
				for(String k : configKeys) {
					PageConfiguration configuration = new PageConfiguration(k);
					configuration.load();
					logger.info("Reading configuration for \"" + configuration.getDisplayName() + "\"...");
					configurations.put(k, configuration);
				}
				defaultConfiguration = properties.getProperty(DEFAULT_CONFIGURATION);
				loaded = true;
			} catch (IOException ie) {
				logger.log(Level.SEVERE, "Unable to load the master configuration", ie);
			}
		}
	}
	
	public void load(PageConfiguration config) {
		config.load();
		for(PageConfigurationChangeHandler handler: handlers ) {
			handler.onPageConfigurationChanged(PageConfigurationChangeType.LOAD, config);
		}
	}
	
	public void delete(PageConfiguration config) {
		if( config.isSystemConfiguration()) {
			logger.warning("Deletion of system configuration \"" + config.getDisplayName() + "\" is not supported.");
		} else {
			Preferences prefs = Resources.getPreferencesNode();
			try {
				prefs.node(config.getName()).removeNode();
				Resources.getPreferencesNode().remove(config.getName());
				logger.info("Removed configuration \"" + config.getDisplayName() + "\"");
			} catch (BackingStoreException e) {
				logger.log(Level.SEVERE,"Unable to remove configuration with name \"" + config.getName() + "\"");
			}
		}
		for(PageConfigurationChangeHandler handler: handlers ) {
			handler.onPageConfigurationChanged(PageConfigurationChangeType.DELETE, config);
		}
	}
	
	public void save(PageConfiguration config) {
		config.save();
		for(PageConfigurationChangeHandler handler: handlers ) {
			handler.onPageConfigurationChanged(PageConfigurationChangeType.SAVE, config);
		}
	}
	
	public void create(PageConfiguration config) {
		config.save();
		configurations.put(config.getName(),config);
		for(PageConfigurationChangeHandler handler: handlers ) {
			handler.onPageConfigurationChanged(PageConfigurationChangeType.CREATE, config);
		}
	}
	
	public void revertAll() {
		for(PageConfiguration config: configurations.values()) {
			if( config.isSystemConfiguration()) {
				config.revert();
			} else {
				delete(config);
			}
		}
	}

	public void revert(PageConfiguration config) {
		config.revert();
		for(PageConfigurationChangeHandler handler: handlers ) {
			handler.onPageConfigurationChanged(PageConfigurationChangeType.REVERT, config);
		}
	}
	
	public void setActiveConfiguration(String activeConfiguration) {
		if( !configurations.containsKey(activeConfiguration)) {
			throw new IllegalArgumentException("The active configuration was not valid.");
		}
		this.activeConfiguration = activeConfiguration;
	}
	
	public PageConfiguration getActiveConfiguration() {
		if( !loaded ) {
			load();
		}
		String name = (activeConfiguration != null ) ? activeConfiguration : defaultConfiguration;
		return getConfiguration(name);
	}
	
	public PageConfiguration getConfiguration(String configuration) {
		if( !loaded ) {
			load();
		}
		if( configuration != null ) {
			return configurations.get(configuration);
		}
		logger.fine("No configuration was found.");
		return null;
	}
	
	public List<PageConfiguration> getConfigurations() {
		if( !loaded ) {
			load();
		}
		List<PageConfiguration> configs = new ArrayList<PageConfiguration>();
		for( PageConfiguration config: configurations.values()) {
			configs.add(config);
		}
		return configs;
	}
	
}
