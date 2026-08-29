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

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.prefs.Preferences;
import org.assertj.swing.edt.GuiActionRunner;
import org.javad.stamp.pdf.Resources;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

public class AlbumGeneratorPanelTest {

    private String originalRenderBorders;

    @BeforeEach
    public void setUp() {
        Preferences prefs = Resources.getPreferencesNode();
        originalRenderBorders = prefs.get(GeneratorConstants.RENDER_PAGE_BORDERS_KEY, null);
    }

    @AfterEach
    public void tearDown() {
        Preferences prefs = Resources.getPreferencesNode();
        if (originalRenderBorders != null) {
            prefs.put(GeneratorConstants.RENDER_PAGE_BORDERS_KEY, originalRenderBorders);
        } else {
            prefs.remove(GeneratorConstants.RENDER_PAGE_BORDERS_KEY);
        }
    }

    @Test
    public void testRenderBordersPreferenceDefault() {
        Preferences prefs = Resources.getPreferencesNode();
        prefs.remove(GeneratorConstants.RENDER_PAGE_BORDERS_KEY);
        AlbumGeneratorPanel panel = GuiActionRunner.execute(() -> new AlbumGeneratorPanel());
        assertTrue(panel.getCheckRenderBorders().isSelected(), "Default value for render borders should be true");
        assertTrue(panel.getModelBean().isDrawBorder(), "Model bean drawBorder should default to true");
    }

    @Test
    public void testRenderBordersPreferencePersistence() {
        AlbumGeneratorPanel panel = GuiActionRunner.execute(() -> new AlbumGeneratorPanel());
        GuiActionRunner.execute(() -> {
            panel.getCheckRenderBorders().setSelected(false);
            panel.getCheckRenderBorders().getAction().actionPerformed(null);
        });

        assertFalse(panel.getModelBean().isDrawBorder(), "Model bean drawBorder should be false");
        Preferences prefs = Resources.getPreferencesNode();
        assertFalse(prefs.getBoolean(GeneratorConstants.RENDER_PAGE_BORDERS_KEY, true), "Preference should be saved as false");

        // Verify a new instance reads false from preferences
        AlbumGeneratorPanel newPanel = GuiActionRunner.execute(() -> new AlbumGeneratorPanel());
        assertFalse(newPanel.getCheckRenderBorders().isSelected(), "New panel should load false from preference");
        assertFalse(newPanel.getModelBean().isDrawBorder(), "New panel model bean should load false from preference");
    }

    @Test
    public void testClearLogButton() {
        AlbumGeneratorPanel panel = GuiActionRunner.execute(() -> new AlbumGeneratorPanel());
        GuiActionRunner.execute(() -> {
            panel.getLogText().setText("Sample log message");
            panel.getBtnClearLog().getAction().actionPerformed(null);
        });
        assertEquals("", panel.getLogText().getText(), "Log text area should be empty after clear button action");
    }

    @Test
    public void testPlateFlawsGenerateEnableState() {
        AlbumGeneratorPanel panel = GuiActionRunner.execute(() -> new AlbumGeneratorPanel());
        GuiActionRunner.execute(() -> {
            panel.getPfInputDirText().setText("");
            panel.getOutputFolderText().setText("");
            panel.getPfSelectionText().setText("");
        });
        assertFalse(panel.getBtnPfGenerate().isEnabled(), "Generate button should be disabled when fields are empty");

        GuiActionRunner.execute(() -> {
            panel.getPfInputDirText().setText("C:/tmp/input");
            panel.getOutputFolderText().setText("C:/tmp/output");
            panel.getPfSelectionText().setText("ddr");
        });
        assertTrue(panel.getBtnPfGenerate().isEnabled(), "Generate button should be enabled when required fields are populated");
    }

    @Test
    public void testPlateFlawsClearButton() {
        AlbumGeneratorPanel panel = GuiActionRunner.execute(() -> new AlbumGeneratorPanel());
        GuiActionRunner.execute(() -> {
            panel.getPfLogText().setText("Sample Plate Flaw log");
            panel.getBtnPfClear().doClick();
        });
        assertEquals("", panel.getPfLogText().getText(), "Plate Flaws log text should be empty after clear button action");
    }

    @Test
    public void testModeToggleButtons() {
        AlbumGeneratorPanel panel = GuiActionRunner.execute(() -> new AlbumGeneratorPanel());
        assertTrue(panel.getModeAlbumButton().isSelected(), "Album mode button should be selected by default");
        assertFalse(panel.getModePlateFlawsButton().isSelected(), "Plate flaws mode button should not be selected by default");

        GuiActionRunner.execute(() -> panel.getModePlateFlawsButton().doClick());
        assertTrue(panel.getModePlateFlawsButton().isSelected(), "Plate flaws mode button should be selected after click");
        assertFalse(panel.getModeAlbumButton().isSelected(), "Album mode button should not be selected after clicking Plate flaws");
    }

    @Test
    public void testTagTextColumnWidth() {
        AlbumGeneratorPanel panel = GuiActionRunner.execute(() -> new AlbumGeneratorPanel());
        assertEquals(25, panel.getTagText().getColumns(), "Tag text field should be configured for 25 columns visually");
    }

    @Test
    public void testPlateFlawsSelectionTextColumnWidth() {
        AlbumGeneratorPanel panel = GuiActionRunner.execute(() -> new AlbumGeneratorPanel());
        assertEquals(15, panel.getPfSelectionText().getColumns(), "Plate Flaws selection field should be configured for 15 columns visually");
    }

    @Test
    public void testPlateFlawsOpenButtonInitialDisabledState() {
        AlbumGeneratorPanel panel = GuiActionRunner.execute(() -> new AlbumGeneratorPanel());
        assertFalse(panel.getBtnPfOpen().isEnabled(), "Plate Flaws Open button should be disabled initially when no PDF generated");
    }
}
