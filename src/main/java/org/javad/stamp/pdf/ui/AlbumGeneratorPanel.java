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
package org.javad.stamp.pdf.ui;

import java.awt.Desktop;
import java.awt.Dimension;
import java.awt.event.ActionEvent;
import java.awt.event.ActionListener;
import java.io.File;
import java.io.IOException;
import java.text.MessageFormat;
import java.util.logging.Handler;
import java.util.logging.Level;
import java.util.logging.LogRecord;
import java.util.logging.Logger;
import java.util.prefs.BackingStoreException;
import java.util.prefs.Preferences;

import javax.swing.AbstractAction;
import javax.swing.DefaultComboBoxModel;
import javax.swing.JButton;
import javax.swing.JCheckBox;
import javax.swing.JFileChooser;
import javax.swing.JLabel;
import javax.swing.JOptionPane;
import javax.swing.JTextField;
import javax.swing.SwingConstants;
import javax.swing.event.DocumentEvent;
import javax.swing.event.DocumentListener;
import javax.swing.filechooser.FileFilter;

import org.bushe.swing.event.EventBus;
import org.bushe.swing.event.annotation.AnnotationProcessor;
import org.bushe.swing.event.annotation.EventSubscriber;
import org.javad.events.StatusEvent;
import org.javad.events.StatusEvent.StatusType;
import org.javad.pdf.model.PageConfiguration;
import org.javad.pdf.model.PageConfigurations;
import org.javad.pdf.model.PageConfigurations.PageConfigurationChangeHandler;
import org.javad.pdf.model.PageConfigurations.PageConfigurationChangeType;
import org.javad.stamp.pdf.Resources;
import org.javad.stamp.pdf.events.PdfAppEvent;
import org.javad.stamp.pdf.events.PdfAppEvent.EventType;
import org.javad.stamp.pdf.ui.model.GenerateBean;

import pub.domain.GradientPanel;

import com.jgoodies.forms.factories.FormFactory;
import com.jgoodies.forms.layout.ColumnSpec;
import com.jgoodies.forms.layout.FormLayout;
import com.jgoodies.forms.layout.RowSpec;
import com.jgoodies.forms.layout.Sizes;
import javax.swing.JPanel;
import javax.swing.JComboBox;
import javax.swing.JScrollPane;
import javax.swing.JTextArea;
import javax.swing.ScrollPaneConstants;
import java.awt.FlowLayout;
import java.awt.Color;

@SuppressWarnings("serial")
public class AlbumGeneratorPanel extends GradientPanel implements PageConfigurationChangeHandler {
	
	private String default_folder = null;
	private String default_output_folder = null;
	
	private JLabel inputFileLabel;
	private JTextField inputFileText;
	private JButton btnInputFile;
	private JLabel outputFolderLabel;
	private JTextField outputFolderText;
	private JButton btnOutputFolder;
	
	private JFileChooser fileChooser;
	private JFileChooser folderChooser;
	private JButton btnGenerate;
	private JButton btnOpenPdf;
	private JCheckBox checkRenderBorders;
	
	private GenerateBean modelBean = null;
	
	
	private static final Logger logger = Logger.getLogger(AlbumGeneratorPanel.class.getName());
	
	private JPanel panel;
	private JLabel configurationLabel;
	@SuppressWarnings("rawtypes")
	private JComboBox configurationComboBox;
	private JTextArea logText;
	private JLabel logLabel;
	private JScrollPane scrollPane;
	private JPanel configPanel;
	private JButton btnDeleteConfiguration;
	private JCheckBox checkRenderReverse;
	
	
	public AlbumGeneratorPanel() {
		initialize();
	}
	
	public GenerateBean getModelBean() {
		return modelBean;
	}
	
	public void setModelBean(GenerateBean modelBean) {
		this.modelBean = modelBean;
	}
	
	private void initialize() {
		AnnotationProcessor.process(this);
		setModelBean(new GenerateBean());
		setBackground(new Color(248, 248, 255));
		setForeground(new Color(211, 211, 211));
		setDirection(GradientPanel.HORIZONTAL);
		setLayout(new FormLayout(new ColumnSpec[] {
				FormFactory.UNRELATED_GAP_COLSPEC,
				ColumnSpec.decode("79px"),
				FormFactory.LABEL_COMPONENT_GAP_COLSPEC,
				new ColumnSpec(ColumnSpec.FILL, Sizes.bounded(Sizes.PREFERRED, Sizes.constant("250dlu", true), Sizes.constant("400dlu", true)), 1),
				ColumnSpec.decode("left:40px"),
				FormFactory.UNRELATED_GAP_COLSPEC,},
			new RowSpec[] {
				FormFactory.RELATED_GAP_ROWSPEC,
				RowSpec.decode("22dlu"),
				FormFactory.UNRELATED_GAP_ROWSPEC,
				RowSpec.decode("24px"),
				FormFactory.RELATED_GAP_ROWSPEC,
				RowSpec.decode("24px"),
				FormFactory.RELATED_GAP_ROWSPEC,
				FormFactory.DEFAULT_ROWSPEC,
				FormFactory.RELATED_GAP_ROWSPEC,
				FormFactory.DEFAULT_ROWSPEC,
				FormFactory.RELATED_GAP_ROWSPEC,
				FormFactory.DEFAULT_ROWSPEC,
				FormFactory.RELATED_GAP_ROWSPEC,
				RowSpec.decode("fill:60px:grow"),
				FormFactory.UNRELATED_GAP_ROWSPEC,}));
		add(getConfigurationLabel(), "2, 2, right, default");
		add(getConfigPanel(), "4, 2, 2, 1, left, fill");
		add(getInputFileLabel(), "2, 4, fill, center");
		add(getInputFileText(), "4, 4, fill, center");
		add(getBtnInputFile(), "5, 4, left, top");
		add(getOutputFolderLabel(), "2, 6, fill, fill");
		add(getOutputFolderText(), "4, 6, fill, center");
		add(getBtnOutputFolder(), "5, 6, left, top");
		add(getCheckRenderBorders(), "4, 8");
		add(getCheckRenderReverse(), "4, 10, left, default");
		add(getPanel(), "4, 12,fill, top");
		
		Preferences prefs = Resources.getPreferencesNode();
		String folderOutput = prefs.get(GeneratorConstants.DEFAULT_OUTPUT_FOLDER_KEY, null);
		String inputFile = prefs.get(GeneratorConstants.DEFAULT_INPUT_FILE_KEY, null);
		if( folderOutput != null ) {
			getOutputFolderText().setText(folderOutput);
		}
		if( inputFile != null ) {
			getInputFileText().setText(inputFile);
		}
		
		
		Logger.getLogger("org.javad").setLevel(Level.INFO);
		Logger.getLogger("org.javad").addHandler(new Handler() {

			@Override
			public void publish(LogRecord record) {
				getLogText().append(record.getMessage() + "\n");
			}

			@Override
			public void flush() { }

			@Override
			public void close() throws SecurityException {
				getLogText().setText(null);
			}
			
		});
		
		loadConfigurations();
		
		PageConfigurations configs = PageConfigurations.getInstance();
		configs.addPageConfigurationChangeHandler(this);
		add(getLogLabel(), "2, 14, right, top");
		add(getScrollPane(), "4, 14,2,1 fill, fill");
		
	}
	
	@EventSubscriber(eventClass=PdfAppEvent.class)
	public void handleAppEvent(PdfAppEvent evt) {
		if( evt.getType() == EventType.Generated) {
			getBtnOpenPdf().setEnabled(true);
		} else if ( evt.getType() == EventType.Generate_Error ) {
			if( evt.getData() instanceof IOException ) {
				IOException ioe = evt.getData();
				String msg = MessageFormat.format(Resources.getString("generate.error.msg"),ioe.getLocalizedMessage());
				JOptionPane.showMessageDialog(this, msg, Resources.getString("generate.error.title"), JOptionPane.ERROR_MESSAGE);
			}
			if( evt.getData() instanceof Throwable ) {
				((Throwable)evt.getData()).printStackTrace();
			}
			logger.log(Level.FINE, "Error generating the pages.", (Throwable)evt.getData());
		}
	}
	
	protected JLabel getInputFileLabel() {
		if (inputFileLabel == null) {
			inputFileLabel = new JLabel(Resources.getString("label.inputFile")); //$NON-NLS-1$
			inputFileLabel.setHorizontalAlignment(SwingConstants.RIGHT);
			inputFileLabel.setPreferredSize(new Dimension(100, 14));
		}
		return inputFileLabel;
	}
	
	protected JTextField getInputFileText() {
		if (inputFileText == null) {
			inputFileText = new JTextField();
			inputFileText.setMinimumSize(new Dimension(100, 20));
			inputFileText.setPreferredSize(new Dimension(250, 24));
			inputFileText.setColumns(10);
			inputFileText.getDocument().addDocumentListener(new FileDocumentUpdate());
		}
		return inputFileText;
	}
	protected JButton getBtnInputFile() {
		if (btnInputFile == null) {
			btnInputFile = new JButton();
			btnInputFile.setBorder(null);
			btnInputFile.setPreferredSize(new Dimension(40, 24));
			btnInputFile.setName("pagegen-inputFile");
			btnInputFile.setAction(new ChooseInputFile());
		}
		return btnInputFile;
	}
	protected JLabel getOutputFolderLabel() {
		if (outputFolderLabel == null) {
			outputFolderLabel = new JLabel(Resources.getString("label.outputFolder")); //$NON-NLS-1$
			outputFolderLabel.setHorizontalAlignment(SwingConstants.RIGHT);
			outputFolderLabel.setPreferredSize(new Dimension(100, 14));
		}
		return outputFolderLabel;
	}
	protected JTextField getOutputFolderText() {
		if (outputFolderText == null) {
			outputFolderText = new JTextField();
			outputFolderText.setPreferredSize(new Dimension(250, 24));
			outputFolderText.setMinimumSize(new Dimension(100, 20));
			outputFolderText.setColumns(10);
			outputFolderText.getDocument().addDocumentListener(new FileDocumentUpdate());
		}
		return outputFolderText;
	}
	protected JButton getBtnOutputFolder() {
		if (btnOutputFolder == null) {
			btnOutputFolder = new JButton();
			btnOutputFolder.setPreferredSize(new Dimension(40, 24));
			btnOutputFolder.setName("pagegen-outputFolder");
			btnOutputFolder.setAction(new ChooseOutputFolder());
		}
		return btnOutputFolder;
	}
	
	
	
	protected JButton getBtnGenerate() {
		if (btnGenerate == null) {
			btnGenerate = new JButton(Resources.getString("button.generate")); //$NON-NLS-1$
			btnGenerate.setEnabled(false);
			btnGenerate.setPreferredSize(new Dimension(110, 25));
			btnGenerate.setName("pagegen-generate");
			btnGenerate.setAction(new GenerateAction());
		}
		return btnGenerate;
	}
	
	protected JButton getBtnOpenPdf() {
		if (btnOpenPdf == null) {
			btnOpenPdf = new JButton(Resources.getString("button.open")); //$NON-NLS-1$
			btnOpenPdf.setPreferredSize(new Dimension(110, 25));
			btnOpenPdf.setName("pagegen-open");
			btnOpenPdf.setAction(new OpenPdfAction());
			btnOpenPdf.setEnabled(false);
		}
		return btnOpenPdf;
	}
	
	protected JCheckBox getCheckRenderBorders() {
		if (checkRenderBorders == null) {
			checkRenderBorders = new JCheckBox(Resources.getString("label.renderBorders")); //$NON-NLS-1$
			checkRenderBorders.setAction(new ToggleBordersAction());
			checkRenderBorders.setOpaque(false);
		}
		return checkRenderBorders;
	}
	
	protected JCheckBox getCheckRenderReverse() {
		if (checkRenderReverse == null) {
			checkRenderReverse = new JCheckBox(Resources.getString("label.renderReverse")); //$NON-NLS-1$
			checkRenderReverse.setAction(new ToggleReverseAction());
			checkRenderReverse.setOpaque(false);
		}
		return checkRenderReverse;
	}
	
	/**
	 * @wbp.nonvisual location=18,869
	 */
	protected JFileChooser getInputFileChooser() {
		if (fileChooser == null) {
			fileChooser = new JFileChooser();
			fileChooser.setName("pagegen-inputChooser");
			fileChooser.setAcceptAllFileFilterUsed(false);
			fileChooser.setFileFilter(new InputFileFilter());
			String folder = default_folder;
			if( default_folder == null ) {
				Preferences prefs = Resources.getPreferencesNode();
				folder = prefs.get(GeneratorConstants.DEFAULT_FOLDER_KEY, null);
			}
			if( folder != null ) {
				File f = new File(folder);
				if( f.exists()) {
					fileChooser.setCurrentDirectory(f);
				}
			}
		}
		return fileChooser;
	}
	
	private class InputFileFilter extends FileFilter {
		@Override
		public boolean accept(File f) {
			return (f.isDirectory() && f.canRead()) || (f.isFile() && f.canRead() && f.getName().toLowerCase().endsWith(".xml"));
		}

		@Override
		public String getDescription() {
			return Resources.getString("filter.xml"); //$NON-NLS-1$
		}
	}
	
	/**
	 * @wbp.nonvisual location=48,869
	 */
	protected JFileChooser getOutputFolderChooser() {
		if (folderChooser == null) {
			folderChooser = new JFileChooser();
			folderChooser.setName("pagegen-outputchooser");
			folderChooser.setAcceptAllFileFilterUsed(false);
			folderChooser.setFileSelectionMode(JFileChooser.DIRECTORIES_ONLY);
			folderChooser.setFileFilter(new OutputFileFilter());
			String folder = default_output_folder;
			if( default_output_folder == null ) {
				Preferences prefs = Resources.getPreferencesNode();
				folder = prefs.get(GeneratorConstants.DEFAULT_OUTPUT_FOLDER_KEY, null);
			}
			if( folder != null ) {
				File f = new File(folder);
				if( f.exists() && f.isDirectory()) {
					folderChooser.setCurrentDirectory(f);
				}
			}
		}
		return folderChooser;
	}
	
	private class OutputFileFilter extends FileFilter {
		@Override
		public boolean accept(File f) {
			return f.isDirectory() && f.canRead();
		}

		@Override
		public String getDescription() {
			return Resources.getString("filter.folder"); //$NON-NLS-1$
		}
	}
	
	private class ToggleBordersAction extends AbstractAction {
		
		public ToggleBordersAction() {
			putValue(NAME, Resources.getString("label.renderBorders")); //$NON-NLS-1$
		}
		
		@Override
		public void actionPerformed(ActionEvent e) {
			getModelBean().setDrawBorder(getCheckRenderBorders().isSelected());
		}
	}
	
	private class ToggleReverseAction extends AbstractAction {
		
		public ToggleReverseAction() {
			putValue(NAME, Resources.getString("label.renderReverse")); //$NON-NLS-1$
		}
		
		@Override
		public void actionPerformed(ActionEvent e) {
			getModelBean().setReversePages(getCheckRenderReverse().isSelected());
		}
	}
	
	private class OpenPdfAction extends AbstractAction {
		public OpenPdfAction() {
			putValue(NAME, Resources.getString("button.open")); //$NON-NLS-1$
			putValue(LARGE_ICON_KEY, Resources.getIcon("icon.open")); //$NON-NLS-1$
		}

		@Override
		public void actionPerformed(ActionEvent e) {
			try {
				Desktop.getDesktop().open(getModelBean().getOutputFile());
			} catch (IOException ex) {
				ex.printStackTrace();
			}
			
		}
	}
	
	
	private class ChooseOutputFolder extends AbstractAction {

		public ChooseOutputFolder() {
			putValue(SHORT_DESCRIPTION, Resources.getString("label.outputFolder.tooltip")); //$NON-NLS-1$
			putValue(LARGE_ICON_KEY, Resources.getIcon("icon.folderOutput")); //$NON-NLS-1$
		}
		
		@Override
		public void actionPerformed(ActionEvent e) {
			if( JFileChooser.APPROVE_OPTION == getOutputFolderChooser().showOpenDialog(getBtnOutputFolder()) ) {
				File f = getOutputFolderChooser().getSelectedFile();
				if (f != null ) {
						Preferences prefs = Resources.getPreferencesNode();
						prefs.put(GeneratorConstants.DEFAULT_OUTPUT_FOLDER_KEY, f.getPath());
						default_output_folder = f.getPath();
						try {
							prefs.flush();
						} catch (BackingStoreException e1) {
							logger.log(Level.SEVERE, "Unable to save default folder.", e1); //$NON-NLS-1$
						}
					getOutputFolderText().setText(f.getAbsolutePath());	
				}
			}
			
		}
		
	}
	
	
	private class GenerateAction extends AbstractAction {
		
		public GenerateAction() {
			putValue(NAME, Resources.getString("button.generate")); //$NON-NLS-1$
			putValue(LARGE_ICON_KEY, Resources.getIcon("icon.generate")); //$NON-NLS-1$
			setEnabled(false);
		}

		@Override
		public void actionPerformed(ActionEvent e) {
			Preferences prefs = Resources.getPreferencesNode();
			prefs.put(GeneratorConstants.DEFAULT_INPUT_FILE_KEY, getInputFileText().getText());
			EventBus.publish(new StatusEvent(StatusType.ShowBusy, Resources.getString("message.generating"))); //$NON-NLS-1$
			EventBus.publish(new PdfAppEvent(EventType.Generate,getModelBean()));
			getBtnOpenPdf().setEnabled(false);
		}
		
		
	}
	
	private class ChooseInputFile extends AbstractAction {

		public ChooseInputFile() {
			putValue(SHORT_DESCRIPTION, Resources.getString("label.inputFile.tooltip")); //$NON-NLS-1$
			putValue(LARGE_ICON_KEY, Resources.getIcon("icon.fileInput")); //$NON-NLS-1$
		}
		
		@Override
		public void actionPerformed(ActionEvent e) {
			if( JFileChooser.APPROVE_OPTION == getInputFileChooser().showOpenDialog(getBtnInputFile()) ) {
				File f = getInputFileChooser().getSelectedFile();
				if (f != null ) {
					if (f.getParent() != null) {
						Preferences prefs = Resources.getPreferencesNode();
						prefs.put(GeneratorConstants.DEFAULT_FOLDER_KEY, f.getParent());
						try {
							prefs.flush();
						} catch (BackingStoreException e1) {
							logger.log(Level.SEVERE,"Unable to save default folder.", e1); //$NON-NLS-1$
						}
					}
					getInputFileText().setText(f.getAbsolutePath());
				}
			}
			
		}
		
	}

	private class FileDocumentUpdate implements DocumentListener {
		
		public void insertUpdate(DocumentEvent e) {
			validateDocument(e);				}

		public void removeUpdate(DocumentEvent e) {
			validateDocument(e);				}

		public void changedUpdate(DocumentEvent e) {
			validateDocument(e);
		}
		
		private void validateDocument(DocumentEvent e ) {
			boolean valid = false;
			if( !getInputFileText().getText().isEmpty() && !getOutputFolderText().getText().isEmpty() ) {
				File input = new File(getInputFileText().getText());
				if( input.exists() && input.isFile()) {
					String filename = input.getName().substring(0, input.getName().lastIndexOf('.'));
					File output = new File(getOutputFolderText().getText());
					if( output.exists() && output.isDirectory()) {
						File out = new File(output, filename + ".pdf");
						getModelBean().setInputFile(input);
						getModelBean().setOutputFile(out);
					}
				}
				valid = getModelBean().isValid();
			}
			getBtnGenerate().getAction().setEnabled(valid);
		}
		
	}
	protected JPanel getPanel() {
		if (panel == null) {
			panel = new JPanel();
			panel.setPreferredSize(new Dimension(10, 40));
			panel.setMinimumSize(new Dimension(10, 50));
			panel.setOpaque(false);
			panel.add(getBtnGenerate());
			panel.add(getBtnOpenPdf());
		}
		return panel;
	}
	protected JLabel getConfigurationLabel() {
		if (configurationLabel == null) {
			configurationLabel = new JLabel(Resources.getString("label.configuration")); //$NON-NLS-1$
		}
		return configurationLabel;
	}
	@SuppressWarnings({ "rawtypes", "unchecked" })
	protected JComboBox getConfigurationComboBox() {
		if (configurationComboBox == null) {
			configurationComboBox = new JComboBox();
			configurationComboBox.setMinimumSize(new Dimension(23, 22));
			configurationComboBox.setPreferredSize(new Dimension(250, 22));
			configurationComboBox.setRenderer(new ConfigurationRenderer());
			ActionListener listener = new ActionListener() {
				@Override
				public void actionPerformed(ActionEvent e) {
					PageConfiguration configuration = (PageConfiguration) configurationComboBox.getSelectedItem();
					PageConfigurations.getInstance().setActiveConfiguration(configuration.getName());
					getBtnDeleteConfiguration().setEnabled(!configuration.isSystemConfiguration());
				}
				
			};
			configurationComboBox.addActionListener(listener);
		}
		return configurationComboBox;
	}
	
	@SuppressWarnings({ "rawtypes", "unchecked" })
	protected void loadConfigurations() {
		PageConfigurations configs = PageConfigurations.getInstance();
		DefaultComboBoxModel model = new DefaultComboBoxModel(configs.getConfigurations().toArray());
		getConfigurationComboBox().setModel(model);
		PageConfiguration active = configs.getActiveConfiguration();
		getBtnDeleteConfiguration().getAction().setEnabled(!active.isSystemConfiguration());
		getConfigurationComboBox().setSelectedItem(active);
	}
	
	protected JTextArea getLogText() {
		if (logText == null) {
			logText = new JTextArea();
			logText.setLineWrap(true);
			logText.setEditable(false);
			logText.setText("");
		}
		return logText;
	}
	protected JLabel getLogLabel() {
		if (logLabel == null) {
			logLabel = new JLabel(Resources.getString("label.log")); //$NON-NLS-1$
		}
		return logLabel;
	}
	protected JScrollPane getScrollPane() {
		if (scrollPane == null) {
			scrollPane = new JScrollPane();
			scrollPane.setVerticalScrollBarPolicy(ScrollPaneConstants.VERTICAL_SCROLLBAR_ALWAYS);
			scrollPane.setViewportView(getLogText());
		}
		return scrollPane;
	}

	@SuppressWarnings({ "rawtypes", "unchecked" })
	@Override
	public void onPageConfigurationChanged(PageConfigurationChangeType type, PageConfiguration config) {
		DefaultComboBoxModel model = (DefaultComboBoxModel) getConfigurationComboBox().getModel();
		if( type == PageConfigurationChangeType.CREATE ) {
			model.addElement(config);
		} else if ( type == PageConfigurationChangeType.SAVE ) {
			getConfigurationComboBox().repaint();
		} else if ( type == PageConfigurationChangeType.DELETE ) {
			model.removeElement(config);
		}
	}
	
	
	protected JPanel getConfigPanel() {
		if (configPanel == null) {
			configPanel = new JPanel();
			configPanel.setOpaque(false);
			configPanel.setLayout(new FlowLayout(FlowLayout.CENTER, 2, 4));
			configPanel.add(getConfigurationComboBox());
			configPanel.add(getBtnDeleteConfiguration());
		}
		return configPanel;
	}
	protected JButton getBtnDeleteConfiguration() {
		if (btnDeleteConfiguration == null) {
			btnDeleteConfiguration = new JButton(); //$NON-NLS-1$
			btnDeleteConfiguration.setName("btnDeleteConfiguration");
			btnDeleteConfiguration.setPreferredSize(new Dimension(40, 24));
			btnDeleteConfiguration.setAction(new DeleteAction());
			
		}
		return btnDeleteConfiguration;
	}
	
	private class DeleteAction extends AbstractAction {

		DeleteAction() {
			putValue(SHORT_DESCRIPTION, Resources.getString("button.deleteConfiguration")); //$NON-NLS-1$
			putValue(LARGE_ICON_KEY, Resources.getIcon("icon.remove")); //$NON-NLS-1$
			setEnabled(false);
		}
		
		@Override
		public void actionPerformed(ActionEvent e) {
			PageConfigurations.getInstance().delete((PageConfiguration) getConfigurationComboBox().getSelectedItem());
		}
		
	}

}
