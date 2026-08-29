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

import java.awt.Dimension;
import java.awt.event.ActionEvent;
import java.io.File;
import java.util.prefs.Preferences;

import javax.swing.AbstractAction;
import javax.swing.JButton;
import javax.swing.JComboBox;
import javax.swing.JFileChooser;
import javax.swing.JLabel;
import javax.swing.JPanel;
import javax.swing.JSpinner;
import javax.swing.JTextField;
import javax.swing.SpinnerNumberModel;

import org.javad.components.ISettingsPanel;
import org.javad.stamp.pdf.Resources;

import com.jgoodies.forms.factories.FormFactory;
import com.jgoodies.forms.layout.ColumnSpec;
import com.jgoodies.forms.layout.FormLayout;
import com.jgoodies.forms.layout.RowSpec;

@SuppressWarnings("serial")
public class GeneratorPropertiesPanel extends JPanel implements ISettingsPanel {

	private JComboBox<String> imageTypeCombo;
	private JComboBox<String> processorCombo;
	private JTextField imagesDirText;
	private JButton btnImagesDir;
	private JSpinner imageQualitySpinner;
	private JButton btnRevertDefault;

	public GeneratorPropertiesPanel() {
		setOpaque(false);
		setLayout(new FormLayout(new ColumnSpec[] {
				FormFactory.UNRELATED_GAP_COLSPEC,
				FormFactory.DEFAULT_COLSPEC,
				FormFactory.LABEL_COMPONENT_GAP_COLSPEC,
				FormFactory.DEFAULT_COLSPEC,
				ColumnSpec.decode("250px:grow"),
				FormFactory.LABEL_COMPONENT_GAP_COLSPEC,
				FormFactory.DEFAULT_COLSPEC,
				FormFactory.UNRELATED_GAP_COLSPEC,},
			new RowSpec[] {
				FormFactory.UNRELATED_GAP_ROWSPEC,
				FormFactory.DEFAULT_ROWSPEC,
				FormFactory.RELATED_GAP_ROWSPEC,
				FormFactory.DEFAULT_ROWSPEC,
				FormFactory.RELATED_GAP_ROWSPEC,
				FormFactory.DEFAULT_ROWSPEC,
				FormFactory.RELATED_GAP_ROWSPEC,
				FormFactory.DEFAULT_ROWSPEC,
				FormFactory.RELATED_GAP_ROWSPEC,
				FormFactory.DEFAULT_ROWSPEC,
				RowSpec.decode("default:grow"),
				FormFactory.UNRELATED_GAP_ROWSPEC,}));

		JLabel labelImageType = new JLabel(Resources.getString("label.imageType"));
		add(labelImageType, "2, 2, right, default");
		add(getImageTypeCombo(), "4, 2, left, default");

		JLabel labelImageQuality = new JLabel(Resources.getString("label.imageQuality"));
		add(labelImageQuality, "2, 4, right, default");
		add(getImageQualitySpinner(), "4, 4, left, default");

		JLabel labelProcessor = new JLabel(Resources.getString("label.processor"));
		add(labelProcessor, "2, 6, right, default");
		add(getProcessorCombo(), "4, 6, left, default");

		JLabel labelImagesDir = new JLabel(Resources.getString("label.imagesDir"));
		add(labelImagesDir, "2, 8, right, default");
		add(getImagesDirText(), "4, 8, 2, 1, fill, center");
		add(getBtnImagesDir(), "7, 8, left, default");

		add(getRevertDefault(), "4, 10, left, default");

		loadSettings();
	}

	public JButton getRevertDefault() {
		if (btnRevertDefault == null) {
			btnRevertDefault = new JButton();
			btnRevertDefault.setName("btnRevertDefault");
			btnRevertDefault.setAction(new RevertAction());
		}
		return btnRevertDefault;
	}

	private class RevertAction extends AbstractAction {
		public RevertAction() {
			putValue(NAME, Resources.getString("button.revert"));
		}

		@Override
		public void actionPerformed(ActionEvent e) {
			getImageTypeCombo().setSelectedItem("JPEG");
			getProcessorCombo().setSelectedItem("ReportLab");
			getImagesDirText().setText("");
			getImageQualitySpinner().setValue(85);
		}
	}

	public JComboBox<String> getImageTypeCombo() {
		if (imageTypeCombo == null) {
			imageTypeCombo = new JComboBox<>(new String[] { "JPEG", "PNG" });
			imageTypeCombo.setName("combo.imageType");
			imageTypeCombo.setSelectedItem("JPEG");
		}
		return imageTypeCombo;
	}

	public JComboBox<String> getProcessorCombo() {
		if (processorCombo == null) {
			processorCombo = new JComboBox<>(new String[] { "ReportLab", "Word" });
			processorCombo.setName("combo.processor");
			processorCombo.setSelectedItem("ReportLab");
		}
		return processorCombo;
	}

	public JTextField getImagesDirText() {
		if (imagesDirText == null) {
			imagesDirText = new JTextField();
			imagesDirText.setName("text.imagesDir");
			imagesDirText.setPreferredSize(new Dimension(250, 28));
		}
		return imagesDirText;
	}

	public JButton getBtnImagesDir() {
		if (btnImagesDir == null) {
			btnImagesDir = new JButton();
			btnImagesDir.setName("btn.imagesDir");
			btnImagesDir.setPreferredSize(new Dimension(40, 28));
			btnImagesDir.setIcon(Resources.getIcon("icon.folderOutput"));
			btnImagesDir.addActionListener(e -> {
				JFileChooser chooser = new JFileChooser();
				chooser.setFileSelectionMode(JFileChooser.DIRECTORIES_ONLY);
				if (!getImagesDirText().getText().trim().isEmpty()) {
					File f = new File(getImagesDirText().getText().trim());
					if (f.exists()) {
						chooser.setCurrentDirectory(f);
					}
				}
				int option = chooser.showOpenDialog(GeneratorPropertiesPanel.this);
				if (option == JFileChooser.APPROVE_OPTION) {
					getImagesDirText().setText(chooser.getSelectedFile().getAbsolutePath());
				}
			});
		}
		return btnImagesDir;
	}

	public JSpinner getImageQualitySpinner() {
		if (imageQualitySpinner == null) {
			imageQualitySpinner = new JSpinner(new SpinnerNumberModel(85, 1, 100, 1));
			imageQualitySpinner.setName("spinner.imageQuality");
		}
		return imageQualitySpinner;
	}

	@Override
	public void loadSettings() {
		Preferences prefs = Resources.getPreferencesNode().node("GeneratorProperties");
		String type = prefs.get("image-type", "jpeg");
		if (type != null && type.equalsIgnoreCase("png")) {
			getImageTypeCombo().setSelectedItem("PNG");
		} else {
			getImageTypeCombo().setSelectedItem("JPEG");
		}

		String processor = prefs.get("processor", "reportlab");
		if (processor != null && processor.equalsIgnoreCase("word")) {
			getProcessorCombo().setSelectedItem("Word");
		} else {
			getProcessorCombo().setSelectedItem("ReportLab");
		}

		String imagesDir = prefs.get("images-dir", "");
		getImagesDirText().setText(imagesDir);

		int quality = prefs.getInt("image-quality", 85);
		if (quality < 1 || quality > 100) {
			quality = 85;
		}
		getImageQualitySpinner().setValue(quality);
	}

	@Override
	public void saveSettings() {
		Preferences prefs = Resources.getPreferencesNode().node("GeneratorProperties");
		String selectedType = (String) getImageTypeCombo().getSelectedItem();
		String storedType = (selectedType != null && selectedType.equalsIgnoreCase("PNG")) ? "png" : "jpeg";
		prefs.put("image-type", storedType);

		String selectedProcessor = (String) getProcessorCombo().getSelectedItem();
		String storedProcessor = (selectedProcessor != null && selectedProcessor.equalsIgnoreCase("Word")) ? "word" : "reportlab";
		prefs.put("processor", storedProcessor);

		prefs.put("images-dir", getImagesDirText().getText().trim());

		int quality = 85;
		Object val = getImageQualitySpinner().getValue();
		if (val instanceof Number) {
			quality = ((Number) val).intValue();
		}
		if (quality < 1 || quality > 100) {
			quality = 85;
		}
		prefs.putInt("image-quality", quality);
	}
}
