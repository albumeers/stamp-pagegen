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
package org.javad.stamp.pdf.ui;

import static org.junit.jupiter.api.Assertions.*;

import java.util.prefs.Preferences;

import org.javad.stamp.pdf.Resources;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

public class GeneratorPropertiesPanelTest {

	private GeneratorPropertiesPanel panel;
	private String initialType;
	private String initialProcessor;
	private String initialImagesDir;
	private Integer initialQuality;

	@BeforeEach
	public void setUp() {
		Preferences prefs = Resources.getPreferencesNode().node("GeneratorProperties");
		try {
			initialType = prefs.get("image-type", null);
			initialProcessor = prefs.get("processor", null);
			initialImagesDir = prefs.get("images-dir", null);
			if (prefs.get("image-quality", null) != null) {
				initialQuality = prefs.getInt("image-quality", 85);
			} else {
				initialQuality = null;
			}
			prefs.removeNode();
			prefs.flush();
		} catch (Exception e) {
			// ignore
		}
		panel = new GeneratorPropertiesPanel();
	}

	@AfterEach
	public void tearDown() {
		Preferences prefs = Resources.getPreferencesNode().node("GeneratorProperties");
		try {
			if (initialType != null) {
				prefs.put("image-type", initialType);
			} else {
				prefs.remove("image-type");
			}
			if (initialProcessor != null) {
				prefs.put("processor", initialProcessor);
			} else {
				prefs.remove("processor");
			}
			if (initialImagesDir != null) {
				prefs.put("images-dir", initialImagesDir);
			} else {
				prefs.remove("images-dir");
			}
			if (initialQuality != null) {
				prefs.putInt("image-quality", initialQuality);
			} else {
				prefs.remove("image-quality");
			}
			prefs.flush();
		} catch (Exception e) {
			// ignore
		}
	}

	@Test
	public void testDefaultLoadSettings() {
		panel.loadSettings();
		assertEquals("JPEG", panel.getImageTypeCombo().getSelectedItem());
		assertEquals("ReportLab", panel.getProcessorCombo().getSelectedItem());
		assertEquals("", panel.getImagesDirText().getText());
		assertEquals(85, ((Number) panel.getImageQualitySpinner().getValue()).intValue());
	}

	@Test
	public void testSaveAndLoadSettings() {
		panel.getImageTypeCombo().setSelectedItem("PNG");
		panel.getProcessorCombo().setSelectedItem("Word");
		panel.getImagesDirText().setText("C:/stamps/images");
		panel.getImageQualitySpinner().setValue(92);

		panel.saveSettings();

		Preferences prefs = Resources.getPreferencesNode().node("GeneratorProperties");
		assertEquals("png", prefs.get("image-type", "jpeg"));
		assertEquals("word", prefs.get("processor", "reportlab"));
		assertEquals("C:/stamps/images", prefs.get("images-dir", ""));
		assertEquals(92, prefs.getInt("image-quality", 85));

		// Verify reloading settings into a new panel instance
		GeneratorPropertiesPanel newPanel = new GeneratorPropertiesPanel();
		newPanel.loadSettings();
		assertEquals("PNG", newPanel.getImageTypeCombo().getSelectedItem());
		assertEquals("Word", newPanel.getProcessorCombo().getSelectedItem());
		assertEquals("C:/stamps/images", newPanel.getImagesDirText().getText());
		assertEquals(92, ((Number) newPanel.getImageQualitySpinner().getValue()).intValue());
	}

	@Test
	public void testInvalidQualityRangeHandling() {
		Preferences prefs = Resources.getPreferencesNode().node("GeneratorProperties");
		prefs.putInt("image-quality", 200);

		panel.loadSettings();
		assertEquals(85, ((Number) panel.getImageQualitySpinner().getValue()).intValue());
	}

	@Test
	public void testRevertToDefault() {
		panel.getImageTypeCombo().setSelectedItem("PNG");
		panel.getProcessorCombo().setSelectedItem("Word");
		panel.getImagesDirText().setText("C:/tmp/images");
		panel.getImageQualitySpinner().setValue(60);

		panel.getRevertDefault().doClick();

		assertEquals("JPEG", panel.getImageTypeCombo().getSelectedItem());
		assertEquals("ReportLab", panel.getProcessorCombo().getSelectedItem());
		assertEquals("", panel.getImagesDirText().getText());
		assertEquals(85, ((Number) panel.getImageQualitySpinner().getValue()).intValue());
	}
}
