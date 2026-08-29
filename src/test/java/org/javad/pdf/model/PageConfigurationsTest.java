/*
   Copyright 2026 Jason Drake (jadrake75@gmail.com)
 
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

import static org.junit.jupiter.api.Assertions.*;

import java.util.Collection;
import java.util.prefs.Preferences;

import org.javad.stamp.pdf.Resources;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

public class PageConfigurationsTest {

	@BeforeEach
	public void setUp() {
		Preferences root = Resources.getPreferencesNode();
		Preferences genPropsNode = root.node("GeneratorProperties");
		genPropsNode.put("image-type", "jpeg");
		genPropsNode.putInt("image-quality", 85);
	}

	@AfterEach
	public void tearDown() {
		try {
			Preferences root = Resources.getPreferencesNode();
			root.node("GeneratorProperties").removeNode();
			root.flush();
		} catch (Exception e) {
			// ignore
		}
	}

	@Test
	public void testNonPageConfigurationSubnodesExcluded() {
		PageConfigurations configs = PageConfigurations.getInstance();
		configs.load();
		Collection<PageConfiguration> allConfigs = configs.getConfigurations();

		for (PageConfiguration config : allConfigs) {
			assertNotEquals("GeneratorProperties", config.getName(), "GeneratorProperties should not be listed as a page configuration");
		}
	}
}
