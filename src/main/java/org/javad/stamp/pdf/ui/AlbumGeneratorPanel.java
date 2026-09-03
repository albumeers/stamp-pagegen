/*
   Copyright 2023-2026 Jason Drake (jadrake75@gmail.com)
 
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

import java.awt.BorderLayout;
import java.awt.CardLayout;
import java.awt.Color;
import java.awt.Desktop;
import java.awt.Dimension;
import java.awt.FlowLayout;
import java.awt.event.ActionEvent;
import java.awt.event.ActionListener;
import java.io.BufferedReader;
import java.io.File;
import java.io.IOException;
import java.io.InputStreamReader;
import java.text.MessageFormat;
import java.util.ArrayList;
import java.util.List;
import java.util.logging.Handler;
import java.util.logging.Level;
import java.util.logging.LogRecord;
import java.util.logging.Logger;
import java.util.prefs.BackingStoreException;
import java.util.prefs.Preferences;

import javax.swing.AbstractAction;
import javax.swing.ButtonGroup;
import javax.swing.DefaultComboBoxModel;
import javax.swing.JButton;
import javax.swing.JCheckBox;
import javax.swing.JComboBox;
import javax.swing.JFileChooser;
import javax.swing.JLabel;
import javax.swing.JOptionPane;
import javax.swing.JPanel;
import javax.swing.JScrollPane;
import javax.swing.JTextArea;
import javax.swing.JTextField;
import javax.swing.JToggleButton;
import javax.swing.ScrollPaneConstants;
import javax.swing.SwingConstants;
import javax.swing.SwingUtilities;
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

import com.jgoodies.forms.factories.FormFactory;
import com.jgoodies.forms.layout.ColumnSpec;
import com.jgoodies.forms.layout.FormLayout;
import com.jgoodies.forms.layout.RowSpec;
import com.jgoodies.forms.layout.Sizes;

import pub.domain.GradientPanel;

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
	private JLabel tagLabel;
	private JTextField tagText;
	private JFileChooser fileChooser;
	private JFileChooser folderChooser;
	private JButton btnGenerate;
	private JButton btnOpenPdf;
	private JButton btnClearLog;
	private JCheckBox checkRenderBorders;
	private JCheckBox checkGeneratePictureBook;
	
	private GenerateBean modelBean = null;
	private File pfGeneratedPdfFile = null;
	
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

	// Segmented Mode Selector & Card Layout components
	private JPanel modePanel;
	private JToggleButton btnModeAlbum;
	private JToggleButton btnModePlateFlaws;
	private ButtonGroup modeGroup;
	private CardLayout cardLayout;
	private JPanel cardContainer;

	// Plate Flaws components
	private JLabel pfInputDirLabel;
	private JTextField pfInputDirText;
	private JButton btnPfInputDir;
	private JLabel pfSelectionLabel;
	private JTextField pfSelectionText;
	private JButton btnPfGenerate;
	private JButton btnPfOpen;
	private JButton btnPfClear;
	private JTextArea pfLogText;
	private JScrollPane pfScrollPane;
	private JPanel pfActionPanel;

	public AlbumGeneratorPanel() {
		initialize();
	}
	
	/*
	@Override
	public void paintComponent(java.awt.Graphics g) {
		super.paintComponent(g);
		java.awt.Graphics2D g2d = (java.awt.Graphics2D) g.create();
		g2d.setRenderingHint(java.awt.RenderingHints.KEY_ANTIALIASING, java.awt.RenderingHints.VALUE_ANTIALIAS_ON);

		int w = getWidth();
		int h = getHeight();

		// Balanced pale slate blue stroke for subtle yet visible globe circular arcs
		g2d.setColor(new Color(150, 175, 205, 90));
		g2d.setStroke(new java.awt.BasicStroke(1.35f));

		// Draw concentric circular globe arcs positioned towards the lower-right background
		int centerX = (int) (w * 0.75);
		int centerY = (int) (h * 0.70);

		for (int radius = 100; radius <= 700; radius += 90) {
			g2d.drawOval(centerX - radius, centerY - radius, radius * 2, radius * 2);
		}

		// Draw subtle elliptical latitude/longitude lines crossing the background
		for (int r = 120; r <= 600; r += 140) {
			g2d.drawOval(centerX - r, centerY - (int)(r * 0.4), r * 2, (int)(r * 0.8));
			g2d.drawOval(centerX - (int)(r * 0.4), centerY - r, (int)(r * 0.8), r * 2);
		}

		g2d.dispose();
	}
	*/
	
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
		setLayout(new BorderLayout(0, 0));

		// Top Shared Panel (Configuration, Output Folder, Render page borders, Mode Switcher)
		JPanel topSharedPanel = new JPanel();
		topSharedPanel.setOpaque(false);
		topSharedPanel.setLayout(new FormLayout(new ColumnSpec[] {
				FormFactory.UNRELATED_GAP_COLSPEC,
				ColumnSpec.decode("79px"),
				FormFactory.LABEL_COMPONENT_GAP_COLSPEC,
				new ColumnSpec(ColumnSpec.FILL, Sizes.bounded(Sizes.PREFERRED, Sizes.constant("280dlu", true), Sizes.constant("400dlu", true)), 1),
				ColumnSpec.decode("left:40px"),
				FormFactory.UNRELATED_GAP_COLSPEC,},
			new RowSpec[] {
				FormFactory.RELATED_GAP_ROWSPEC,
				RowSpec.decode("28px"),
				FormFactory.RELATED_GAP_ROWSPEC,
				RowSpec.decode("28px"),
				FormFactory.RELATED_GAP_ROWSPEC,
				FormFactory.DEFAULT_ROWSPEC,
				FormFactory.RELATED_GAP_ROWSPEC,
				FormFactory.DEFAULT_ROWSPEC,
				FormFactory.RELATED_GAP_ROWSPEC,}));

		topSharedPanel.add(getConfigurationLabel(), "2, 2, right, default");
		topSharedPanel.add(getConfigPanel(), "4, 2, 2, 1, left, fill");
		topSharedPanel.add(getOutputFolderLabel(), "2, 4, fill, fill");
		topSharedPanel.add(getOutputFolderText(), "4, 4, fill, center");
		topSharedPanel.add(getBtnOutputFolder(), "5, 4, left, top");
		topSharedPanel.add(getCheckRenderBorders(), "4, 6");
		topSharedPanel.add(getModePanel(), "4, 8, left, default");

		add(topSharedPanel, BorderLayout.NORTH);
		add(getCardContainer(), BorderLayout.CENTER);

		Preferences prefs = Resources.getPreferencesNode();
		String folderOutput = prefs.get(GeneratorConstants.DEFAULT_OUTPUT_FOLDER_KEY, null);
		String inputFile = prefs.get(GeneratorConstants.DEFAULT_INPUT_FILE_KEY, null);
		if (folderOutput != null) {
			getOutputFolderText().setText(folderOutput);
		}
		if (inputFile != null) {
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

		// Add document listeners to update Plate Flaws buttons state
		DocumentListener pfDocListener = new DocumentListener() {
			@Override
			public void insertUpdate(DocumentEvent e) { updatePfState(); }
			@Override
			public void removeUpdate(DocumentEvent e) { updatePfState(); }
			@Override
			public void changedUpdate(DocumentEvent e) { updatePfState(); }
		};
		getPfInputDirText().getDocument().addDocumentListener(pfDocListener);
		getOutputFolderText().getDocument().addDocumentListener(pfDocListener);
		getPfSelectionText().getDocument().addDocumentListener(pfDocListener);

		// Document listener on inputFileText to auto-default pfInputDirText
		getInputFileText().getDocument().addDocumentListener(new DocumentListener() {
			@Override
			public void insertUpdate(DocumentEvent e) { updatePfInputDirDefault(); }
			@Override
			public void removeUpdate(DocumentEvent e) { updatePfInputDirDefault(); }
			@Override
			public void changedUpdate(DocumentEvent e) { updatePfInputDirDefault(); }
		});

		updatePfInputDirDefault();
		updatePfState();
	}

	public JPanel getModePanel() {
		if (modePanel == null) {
			modePanel = new JPanel(new FlowLayout(FlowLayout.LEFT, 0, 0));
			modePanel.setOpaque(false);
			modePanel.add(getModeAlbumButton());
			modePanel.add(getModePlateFlawsButton());

			modeGroup = new ButtonGroup();
			modeGroup.add(getModeAlbumButton());
			modeGroup.add(getModePlateFlawsButton());
		}
		return modePanel;
	}

	public JToggleButton getModeAlbumButton() {
		if (btnModeAlbum == null) {
			btnModeAlbum = new JToggleButton(Resources.getString("tab.albumGenerator"));
			btnModeAlbum.setName("btnModeAlbum");
			btnModeAlbum.setIcon(Resources.getIcon("icon.documentPdf"));
			btnModeAlbum.setSelected(true);
			btnModeAlbum.setMargin(new java.awt.Insets(2, 4, 2, 4));
			btnModeAlbum.setPreferredSize(new Dimension(150, 26));
			btnModeAlbum.addActionListener(e -> getCardLayout().show(getCardContainer(), "AlbumGenerator"));
		}
		return btnModeAlbum;
	}

	public JToggleButton getModePlateFlawsButton() {
		if (btnModePlateFlaws == null) {
			btnModePlateFlaws = new JToggleButton(Resources.getString("tab.plateFlaws"));
			btnModePlateFlaws.setName("btnModePlateFlaws");
			btnModePlateFlaws.setIcon(Resources.getIcon("icon.generate.pf"));
			btnModePlateFlaws.setMargin(new java.awt.Insets(2, 4, 2, 4));
			btnModePlateFlaws.setPreferredSize(new Dimension(150, 26));
			btnModePlateFlaws.addActionListener(e -> getCardLayout().show(getCardContainer(), "PlateFlaws"));
		}
		return btnModePlateFlaws;
	}

	public CardLayout getCardLayout() {
		if (cardLayout == null) {
			cardLayout = new CardLayout();
		}
		return cardLayout;
	}

	public JPanel getCardContainer() {
		if (cardContainer == null) {
			cardContainer = new JPanel(getCardLayout());
			cardContainer.setOpaque(false);
			cardContainer.add(createAlbumGeneratorCard(), "AlbumGenerator");
			cardContainer.add(createPlateFlawsCard(), "PlateFlaws");
		}
		return cardContainer;
	}

	private JPanel createAlbumGeneratorCard() {
		JPanel panelCard = new JPanel();
		panelCard.setOpaque(false);
		panelCard.setLayout(new FormLayout(new ColumnSpec[] {
				FormFactory.UNRELATED_GAP_COLSPEC,
				ColumnSpec.decode("79px"),
				FormFactory.LABEL_COMPONENT_GAP_COLSPEC,
				new ColumnSpec(ColumnSpec.FILL, Sizes.bounded(Sizes.PREFERRED, Sizes.constant("280dlu", true), Sizes.constant("400dlu", true)), 1),
				ColumnSpec.decode("left:40px"),
				FormFactory.UNRELATED_GAP_COLSPEC,},
			new RowSpec[] {
				FormFactory.RELATED_GAP_ROWSPEC,
				RowSpec.decode("28px"),
				FormFactory.RELATED_GAP_ROWSPEC,
				RowSpec.decode("28px"),
				FormFactory.RELATED_GAP_ROWSPEC,
				FormFactory.DEFAULT_ROWSPEC,
				FormFactory.RELATED_GAP_ROWSPEC,
				FormFactory.DEFAULT_ROWSPEC,
				FormFactory.RELATED_GAP_ROWSPEC,
				FormFactory.DEFAULT_ROWSPEC,
				FormFactory.NARROW_LINE_GAP_ROWSPEC,
				RowSpec.decode("fill:60px:grow"),
				FormFactory.UNRELATED_GAP_ROWSPEC,}));

		panelCard.add(getInputFileLabel(), "2, 2, fill, center");
		panelCard.add(getInputFileText(), "4, 2, fill, center");
		panelCard.add(getBtnInputFile(), "5, 2, left, top");
		panelCard.add(getTagLabel(), "2, 4, fill, center");
		panelCard.add(getTagText(), "4, 4, left, center");
		panelCard.add(getCheckRenderReverse(), "4, 6, left, default");
		panelCard.add(getCheckGeneratePictureBook(), "4, 8, left, default");
		panelCard.add(getPanel(), "4, 10, 2, 1, fill, top");
		panelCard.add(getLogLabel(), "2, 12, right, top");
		panelCard.add(getScrollPane(), "4, 12, 2, 1, fill, fill");

		return panelCard;
	}

	private JPanel createPlateFlawsCard() {
		JPanel panelCard = new JPanel();
		panelCard.setOpaque(false);
		panelCard.setLayout(new FormLayout(new ColumnSpec[] {
				FormFactory.UNRELATED_GAP_COLSPEC,
				ColumnSpec.decode("79px"),
				FormFactory.LABEL_COMPONENT_GAP_COLSPEC,
				new ColumnSpec(ColumnSpec.FILL, Sizes.bounded(Sizes.PREFERRED, Sizes.constant("280dlu", true), Sizes.constant("400dlu", true)), 1),
				ColumnSpec.decode("left:40px"),
				FormFactory.UNRELATED_GAP_COLSPEC,},
			new RowSpec[] {
				FormFactory.RELATED_GAP_ROWSPEC,
				RowSpec.decode("28px"),
				FormFactory.RELATED_GAP_ROWSPEC,
				RowSpec.decode("28px"),
				FormFactory.RELATED_GAP_ROWSPEC,
				FormFactory.DEFAULT_ROWSPEC,
				FormFactory.RELATED_GAP_ROWSPEC,
				RowSpec.decode("fill:60px:grow"),
				FormFactory.UNRELATED_GAP_ROWSPEC,}));

		pfInputDirLabel = new JLabel(Resources.getString("label.inputDir"));
		pfInputDirLabel.setHorizontalAlignment(SwingConstants.RIGHT);
		panelCard.add(pfInputDirLabel, "2, 2, fill, center");
		panelCard.add(getPfInputDirText(), "4, 2, fill, center");
		panelCard.add(getBtnPfInputDir(), "5, 2, left, top");

		pfSelectionLabel = new JLabel(Resources.getString("label.selection"));
		pfSelectionLabel.setHorizontalAlignment(SwingConstants.RIGHT);
		panelCard.add(pfSelectionLabel, "2, 4, fill, center");
		panelCard.add(getPfSelectionText(), "4, 4, left, center");

		panelCard.add(getPfActionPanel(), "4, 6, 2, 1, fill, top");

		JLabel pfLogLabel = new JLabel(Resources.getString("label.log"));
		pfLogLabel.setHorizontalAlignment(SwingConstants.RIGHT);
		panelCard.add(pfLogLabel, "2, 8, right, top");
		panelCard.add(getPfScrollPane(), "4, 8, 2, 1, fill, fill");

		return panelCard;
	}

	public JTextField getPfInputDirText() {
		if (pfInputDirText == null) {
			pfInputDirText = new JTextField();
			pfInputDirText.setName("text.pfInputDir");
			pfInputDirText.setPreferredSize(new Dimension(250, 28));
		}
		return pfInputDirText;
	}

	public JButton getBtnPfInputDir() {
		if (btnPfInputDir == null) {
			btnPfInputDir = new JButton();
			btnPfInputDir.setName("btn.pfInputDir");
			btnPfInputDir.setPreferredSize(new Dimension(40, 28));
			btnPfInputDir.setIcon(Resources.getIcon("icon.folderOutput"));
			btnPfInputDir.addActionListener(e -> {
				JFileChooser chooser = new JFileChooser();
				chooser.setFileSelectionMode(JFileChooser.DIRECTORIES_ONLY);
				if (!getPfInputDirText().getText().trim().isEmpty()) {
					File f = new File(getPfInputDirText().getText().trim());
					if (f.exists()) {
						chooser.setCurrentDirectory(f);
					}
				}
				int option = chooser.showOpenDialog(AlbumGeneratorPanel.this);
				if (option == JFileChooser.APPROVE_OPTION) {
					getPfInputDirText().setText(chooser.getSelectedFile().getAbsolutePath());
				}
			});
		}
		return btnPfInputDir;
	}

	public JTextField getPfSelectionText() {
		if (pfSelectionText == null) {
			pfSelectionText = new JTextField(15);
			pfSelectionText.setName("text.pfSelection");
			pfSelectionText.setPreferredSize(new Dimension(150, 28));
		}
		return pfSelectionText;
	}

	public JButton getBtnPfGenerate() {
		if (btnPfGenerate == null) {
			btnPfGenerate = new JButton(Resources.getString("button.generate"));
			btnPfGenerate.setName("btnPfGenerate");
			btnPfGenerate.setIcon(Resources.getIcon("icon.generate"));
			btnPfGenerate.setPreferredSize(new Dimension(110, 24));
			btnPfGenerate.addActionListener(e -> executePlateFlawsGenerator());
		}
		return btnPfGenerate;
	}

	public JButton getBtnPfOpen() {
		if (btnPfOpen == null) {
			btnPfOpen = new JButton(Resources.getString("button.open"));
			btnPfOpen.setName("btnPfOpen");
			btnPfOpen.setIcon(Resources.getIcon("icon.open"));
			btnPfOpen.setPreferredSize(new Dimension(110, 24));
			btnPfOpen.setEnabled(false);
			btnPfOpen.addActionListener(e -> {
				if (pfGeneratedPdfFile != null && pfGeneratedPdfFile.exists()) {
					try {
						Desktop.getDesktop().open(pfGeneratedPdfFile);
					} catch (IOException ex) {
						logger.log(Level.WARNING, "Failed to open PDF file", ex);
					}
				}
			});
		}
		return btnPfOpen;
	}

	public JButton getBtnPfClear() {
		if (btnPfClear == null) {
			btnPfClear = new JButton();
			btnPfClear.setPreferredSize(new Dimension(80, 24));
			btnPfClear.setName("btnPfClear");
			btnPfClear.setAction(new ClearPfLogAction());
		}
		return btnPfClear;
	}

	private class ClearPfLogAction extends AbstractAction {
		public ClearPfLogAction() {
			putValue(NAME, Resources.getString("button.clearLog"));
			putValue(SMALL_ICON, Resources.getIcon("icon.remove"));
			putValue(SHORT_DESCRIPTION, Resources.getString("button.clearLog.tooltip"));
		}

		@Override
		public void actionPerformed(ActionEvent e) {
			getPfLogText().setText("");
		}
	}

	public JPanel getPfActionPanel() {
		if (pfActionPanel == null) {
			pfActionPanel = new JPanel(new BorderLayout());
			pfActionPanel.setPreferredSize(new Dimension(10, 28));
			pfActionPanel.setMinimumSize(new Dimension(10, 28));
			pfActionPanel.setOpaque(false);

			JPanel leftPanel = new JPanel(new FlowLayout(FlowLayout.LEFT, 5, 0));
			leftPanel.setOpaque(false);
			leftPanel.add(getBtnPfGenerate());
			leftPanel.add(getBtnPfOpen());
			pfActionPanel.add(leftPanel, BorderLayout.WEST);

			JPanel rightPanel = new JPanel(new FlowLayout(FlowLayout.RIGHT, 0, 0));
			rightPanel.setOpaque(false);
			rightPanel.add(getBtnPfClear());
			pfActionPanel.add(rightPanel, BorderLayout.EAST);
		}
		return pfActionPanel;
	}

	public JTextArea getPfLogText() {
		if (pfLogText == null) {
			pfLogText = new JTextArea();
			pfLogText.setName("text.pfLog");
		}
		return pfLogText;
	}

	public JScrollPane getPfScrollPane() {
		if (pfScrollPane == null) {
			pfScrollPane = new JScrollPane(getPfLogText());
		}
		return pfScrollPane;
	}

	private void updatePfInputDirDefault() {
		String inputFilePath = getInputFileText().getText().trim();
		if (!inputFilePath.isEmpty()) {
			File f = new File(inputFilePath);
			if (f.getParent() != null) {
				if (getPfInputDirText().getText().trim().isEmpty()) {
					getPfInputDirText().setText(f.getParent());
				}
			}
		}
	}

	private void updatePfState() {
		boolean inputDirValid = !getPfInputDirText().getText().trim().isEmpty();
		boolean outputDirValid = !getOutputFolderText().getText().trim().isEmpty();
		boolean selectionValid = !getPfSelectionText().getText().trim().isEmpty();

		getBtnPfGenerate().setEnabled(inputDirValid && outputDirValid && selectionValid);
	}

	private void executePlateFlawsGenerator() {
		getBtnPfGenerate().setEnabled(false);
		getBtnPfOpen().setEnabled(false);
		pfGeneratedPdfFile = null;
		getPfLogText().append("Starting Plate Flaws generator...\n");

		// Publish busy status to display intermediate progress bar in footer
		EventBus.publish(new StatusEvent(StatusType.ShowBusy, Resources.getString("message.generating")));

		Preferences genProps = Resources.getPreferencesNode().node("GeneratorProperties");
		String processor = genProps.get("processor", "reportlab");
		String imagesDir = genProps.get("images-dir", "");

		String pythonCmd = "python";
		String scriptPath = "src/main/python/generator/generate-plateflaws.py";
		File scriptFile = new File(scriptPath);
		if (!scriptFile.exists()) {
			scriptPath = "generator/generate-plateflaws.py";
		}

		List<String> command = new ArrayList<>();
		command.add(pythonCmd);
		command.add(scriptPath);
		command.add("--selection");
		command.add(getPfSelectionText().getText().trim());
		command.add("--input-dir");
		command.add(getPfInputDirText().getText().trim());
		command.add("--output-dir");
		command.add(getOutputFolderText().getText().trim());

		if (processor != null && !processor.trim().isEmpty()) {
			command.add("--processor");
			command.add(processor.trim());
		}
		if (imagesDir != null && !imagesDir.trim().isEmpty()) {
			command.add("--images-dir");
			command.add(imagesDir.trim());
		} else {
			String inputDir = getPfInputDirText().getText().trim();
			if (!inputDir.isEmpty()) {
				File defaultImagesDir = new File(inputDir, "images");
				command.add("--images-dir");
				command.add(defaultImagesDir.getAbsolutePath());
			}
		}

		new Thread(() -> {
			try {
				ProcessBuilder pb = new ProcessBuilder(command);
				pb.redirectErrorStream(true);
				Process proc = pb.start();

				try (BufferedReader reader = new BufferedReader(new InputStreamReader(proc.getInputStream()))) {
					String line;
					while ((line = reader.readLine()) != null) {
						final String l = line;
						if (l.startsWith("Generated PDF: ")) {
							String pdfPath = l.substring("Generated PDF: ".length()).trim();
							pfGeneratedPdfFile = new File(pdfPath);
						}
						SwingUtilities.invokeLater(() -> getPfLogText().append(l + "\n"));
					}
				}
				int exitCode = proc.waitFor();
				SwingUtilities.invokeLater(() -> {
					if (exitCode == 0) {
						getPfLogText().append("Pages generated successfully.\n\n");
						getBtnPfOpen().setEnabled(pfGeneratedPdfFile != null && pfGeneratedPdfFile.exists() && pfGeneratedPdfFile.isFile());
					} else {
						getPfLogText().append("Process completed with exit code: " + exitCode + "\n\n");
						getBtnPfOpen().setEnabled(false);
					}
					EventBus.publish(new StatusEvent(StatusType.Finished, ""));
					updatePfState();
				});
			} catch (Exception ex) {
				SwingUtilities.invokeLater(() -> {
					getPfLogText().append("Error executing process: " + ex.getMessage() + "\n");
					EventBus.publish(new StatusEvent(StatusType.Finished, ""));
					updatePfState();
					getBtnPfOpen().setEnabled(false);
				});
			}
		}).start();
	}

	@EventSubscriber(eventClass=PdfAppEvent.class)
	public void handleAppEvent(PdfAppEvent evt) {
		if (evt.getType() == EventType.Generated) {
			getBtnOpenPdf().setEnabled(true);
		} else if (evt.getType() == EventType.Generate_Error) {
			if (evt.getData() instanceof IOException) {
				IOException ioe = evt.getData();
				String msg = MessageFormat.format(Resources.getString("generate.error.msg"), ioe.getLocalizedMessage());
				JOptionPane.showMessageDialog(this, msg, Resources.getString("generate.error.title"), JOptionPane.ERROR_MESSAGE);
			}
			if (evt.getData() instanceof Throwable) {
				((Throwable) evt.getData()).printStackTrace();
			}
			logger.log(Level.FINE, "Error generating the pages.", (Throwable) evt.getData());
		}
	}

	protected JLabel getInputFileLabel() {
		if (inputFileLabel == null) {
			inputFileLabel = new JLabel(Resources.getString("label.inputFile"));
			inputFileLabel.setHorizontalAlignment(SwingConstants.RIGHT);
			inputFileLabel.setPreferredSize(new Dimension(100, 14));
		}
		return inputFileLabel;
	}

	protected JTextField getInputFileText() {
		if (inputFileText == null) {
			inputFileText = new JTextField();
			inputFileText.setMinimumSize(new Dimension(100, 20));
			inputFileText.setPreferredSize(new Dimension(250, 28));
			inputFileText.setColumns(10);
			inputFileText.getDocument().addDocumentListener(new FileDocumentUpdate());
		}
		return inputFileText;
	}

	protected JButton getBtnInputFile() {
		if (btnInputFile == null) {
			btnInputFile = new JButton();
			btnInputFile.setBorder(null);
			btnInputFile.setPreferredSize(new Dimension(40, 28));
			btnInputFile.setName("pagegen-inputFile");
			btnInputFile.setAction(new ChooseInputFile());
		}
		return btnInputFile;
	}

	protected JLabel getTagLabel() {
		if (tagLabel == null) {
			tagLabel = new JLabel(Resources.getString("label.tag"));
			tagLabel.setHorizontalAlignment(SwingConstants.RIGHT);
			tagLabel.setPreferredSize(new Dimension(100, 14));
		}
		return tagLabel;
	}

	protected JTextField getTagText() {
		if (tagText == null) {
			tagText = new JTextField(25);
			tagText.setPreferredSize(new Dimension(200, 28));
			tagText.setMinimumSize(new Dimension(100, 20));
		}
		return tagText;
	}

	protected JLabel getOutputFolderLabel() {
		if (outputFolderLabel == null) {
			outputFolderLabel = new JLabel(Resources.getString("label.outputFolder"));
			outputFolderLabel.setHorizontalAlignment(SwingConstants.RIGHT);
			outputFolderLabel.setPreferredSize(new Dimension(100, 14));
		}
		return outputFolderLabel;
	}

	protected JTextField getOutputFolderText() {
		if (outputFolderText == null) {
			outputFolderText = new JTextField();
			outputFolderText.setPreferredSize(new Dimension(250, 28));
			outputFolderText.setMinimumSize(new Dimension(100, 20));
			outputFolderText.setColumns(10);
			outputFolderText.getDocument().addDocumentListener(new FileDocumentUpdate());
		}
		return outputFolderText;
	}

	protected JButton getBtnOutputFolder() {
		if (btnOutputFolder == null) {
			btnOutputFolder = new JButton();
			btnOutputFolder.setPreferredSize(new Dimension(40, 28));
			btnOutputFolder.setName("pagegen-outputFolder");
			btnOutputFolder.setAction(new ChooseOutputFolder());
		}
		return btnOutputFolder;
	}

	protected JButton getBtnGenerate() {
		if (btnGenerate == null) {
			btnGenerate = new JButton(Resources.getString("button.generate"));
			btnGenerate.setEnabled(false);
			btnGenerate.setPreferredSize(new Dimension(110, 24));
			btnGenerate.setName("pagegen-generate");
			btnGenerate.setAction(new GenerateAction());
		}
		return btnGenerate;
	}

	protected JButton getBtnOpenPdf() {
		if (btnOpenPdf == null) {
			btnOpenPdf = new JButton(Resources.getString("button.open"));
			btnOpenPdf.setPreferredSize(new Dimension(110, 24));
			btnOpenPdf.setName("pagegen-open");
			btnOpenPdf.setAction(new OpenPdfAction());
			btnOpenPdf.setEnabled(false);
		}
		return btnOpenPdf;
	}

	protected JCheckBox getCheckRenderBorders() {
		if (checkRenderBorders == null) {
			checkRenderBorders = new JCheckBox(Resources.getString("label.renderBorders"));
			checkRenderBorders.setAction(new ToggleBordersAction());
			Preferences prefs = Resources.getPreferencesNode();
			boolean renderBorders = prefs.getBoolean(GeneratorConstants.RENDER_PAGE_BORDERS_KEY, true);
			checkRenderBorders.setSelected(renderBorders);
			checkRenderBorders.setOpaque(false);
			getModelBean().setDrawBorder(renderBorders);
		}
		return checkRenderBorders;
	}

	protected JCheckBox getCheckRenderReverse() {
		if (checkRenderReverse == null) {
			checkRenderReverse = new JCheckBox(Resources.getString("label.renderReverse"));
			checkRenderReverse.setAction(new ToggleReverseAction());
			checkRenderReverse.setOpaque(false);
		}
		return checkRenderReverse;
	}

	protected JCheckBox getCheckGeneratePictureBook() {
		if (checkGeneratePictureBook == null) {
			checkGeneratePictureBook = new JCheckBox(Resources.getString("label.generatePictureBook"));
			checkGeneratePictureBook.setAction(new ToggleGeneratePictureBookAction());
			checkGeneratePictureBook.setEnabled(false);
			checkGeneratePictureBook.setOpaque(false);
		}
		return checkGeneratePictureBook;
	}

	protected JFileChooser getInputFileChooser() {
		if (fileChooser == null) {
			fileChooser = new JFileChooser();
			fileChooser.setName("pagegen-inputChooser");
			fileChooser.setAcceptAllFileFilterUsed(false);
			fileChooser.setFileFilter(new InputFileFilter());
			String folder = default_folder;
			if (default_folder == null) {
				Preferences prefs = Resources.getPreferencesNode();
				folder = prefs.get(GeneratorConstants.DEFAULT_FOLDER_KEY, null);
			}
			if (folder != null) {
				File f = new File(folder);
				if (f.exists()) {
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
			return Resources.getString("filter.xml");
		}
	}

	protected JFileChooser getOutputFolderChooser() {
		if (folderChooser == null) {
			folderChooser = new JFileChooser();
			folderChooser.setName("pagegen-outputchooser");
			folderChooser.setAcceptAllFileFilterUsed(false);
			folderChooser.setFileSelectionMode(JFileChooser.DIRECTORIES_ONLY);
			folderChooser.setFileFilter(new OutputFileFilter());
			String folder = default_output_folder;
			if (default_output_folder == null) {
				Preferences prefs = Resources.getPreferencesNode();
				folder = prefs.get(GeneratorConstants.DEFAULT_OUTPUT_FOLDER_KEY, null);
			}
			if (folder != null) {
				File f = new File(folder);
				if (f.exists() && f.isDirectory()) {
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
			return Resources.getString("filter.folder");
		}
	}

	private class ToggleBordersAction extends AbstractAction {
		public ToggleBordersAction() {
			putValue(NAME, Resources.getString("label.renderBorders"));
		}

		@Override
		public void actionPerformed(ActionEvent e) {
			boolean selected = getCheckRenderBorders().isSelected();
			getModelBean().setDrawBorder(selected);
			Preferences prefs = Resources.getPreferencesNode();
			prefs.putBoolean(GeneratorConstants.RENDER_PAGE_BORDERS_KEY, selected);
		}
	}

	private class ToggleReverseAction extends AbstractAction {
		public ToggleReverseAction() {
			putValue(NAME, Resources.getString("label.renderReverse"));
		}

		@Override
		public void actionPerformed(ActionEvent e) {
			getModelBean().setReversePages(getCheckRenderReverse().isSelected());
		}
	}

	private class ToggleGeneratePictureBookAction extends AbstractAction {
		public ToggleGeneratePictureBookAction() {
			putValue(NAME, Resources.getString("label.generatePictureBook"));
		}

		@Override
		public void actionPerformed(ActionEvent e) {
			getModelBean().setGeneratePictureBook(getCheckGeneratePictureBook().isSelected());
		}
	}

	private class OpenPdfAction extends AbstractAction {
		public OpenPdfAction() {
			putValue(NAME, Resources.getString("button.open"));
			putValue(LARGE_ICON_KEY, Resources.getIcon("icon.open"));
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
			putValue(SHORT_DESCRIPTION, Resources.getString("label.outputFolder.tooltip"));
			putValue(LARGE_ICON_KEY, Resources.getIcon("icon.folderOutput"));
		}

		@Override
		public void actionPerformed(ActionEvent e) {
			if (JFileChooser.APPROVE_OPTION == getOutputFolderChooser().showOpenDialog(getBtnOutputFolder())) {
				File f = getOutputFolderChooser().getSelectedFile();
				if (f != null) {
					Preferences prefs = Resources.getPreferencesNode();
					prefs.put(GeneratorConstants.DEFAULT_OUTPUT_FOLDER_KEY, f.getPath());
					default_output_folder = f.getPath();
					try {
						prefs.flush();
					} catch (BackingStoreException e1) {
						logger.log(Level.SEVERE, "Unable to save default folder.", e1);
					}
					getOutputFolderText().setText(f.getAbsolutePath());
				}
			}
		}
	}

	private class GenerateAction extends AbstractAction {
		public GenerateAction() {
			putValue(NAME, Resources.getString("button.generate"));
			putValue(LARGE_ICON_KEY, Resources.getIcon("icon.generate"));
			setEnabled(false);
		}

		@Override
		public void actionPerformed(ActionEvent e) {
			Preferences prefs = Resources.getPreferencesNode();
			prefs.put(GeneratorConstants.DEFAULT_INPUT_FILE_KEY, getInputFileText().getText());
			EventBus.publish(new StatusEvent(StatusType.ShowBusy, Resources.getString("message.generating")));
			getModelBean().setTags(getTagText().getText());
			EventBus.publish(new PdfAppEvent(EventType.Generate, getModelBean()));
			getBtnOpenPdf().setEnabled(false);
		}
	}

	private class ChooseInputFile extends AbstractAction {
		public ChooseInputFile() {
			putValue(SHORT_DESCRIPTION, Resources.getString("label.inputFile.tooltip"));
			putValue(LARGE_ICON_KEY, Resources.getIcon("icon.fileInput"));
		}

		@Override
		public void actionPerformed(ActionEvent e) {
			if (JFileChooser.APPROVE_OPTION == getInputFileChooser().showOpenDialog(getBtnInputFile())) {
				File f = getInputFileChooser().getSelectedFile();
				if (f != null) {
					if (f.getParent() != null) {
						Preferences prefs = Resources.getPreferencesNode();
						prefs.put(GeneratorConstants.DEFAULT_FOLDER_KEY, f.getParent());
						try {
							prefs.flush();
						} catch (BackingStoreException e1) {
							logger.log(Level.SEVERE, "Unable to save default folder.", e1);
						}
					}
					getInputFileText().setText(f.getAbsolutePath());
				}
			}
		}
	}

	private class FileDocumentUpdate implements DocumentListener {
		@Override
		public void insertUpdate(DocumentEvent e) { validateDocument(e); }
		@Override
		public void removeUpdate(DocumentEvent e) { validateDocument(e); }
		@Override
		public void changedUpdate(DocumentEvent e) { validateDocument(e); }

		private void validateDocument(DocumentEvent e) {
			boolean valid = false;
			if (!getInputFileText().getText().isEmpty() && !getOutputFolderText().getText().isEmpty()) {
				File input = new File(getInputFileText().getText());
				if (input.exists() && input.isFile()) {
					String filename = input.getName().substring(0, input.getName().lastIndexOf('.'));
					File output = new File(getOutputFolderText().getText());
					if (output.exists() && output.isDirectory()) {
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
			panel = new JPanel(new BorderLayout());
			panel.setPreferredSize(new Dimension(10, 28));
			panel.setMinimumSize(new Dimension(10, 28));
			panel.setOpaque(false);

			JPanel leftPanel = new JPanel(new FlowLayout(FlowLayout.LEFT, 5, 0));
			leftPanel.setOpaque(false);
			leftPanel.add(getBtnGenerate());
			leftPanel.add(getBtnOpenPdf());
			panel.add(leftPanel, BorderLayout.WEST);

			JPanel rightPanel = new JPanel(new FlowLayout(FlowLayout.RIGHT, 0, 0));
			rightPanel.setOpaque(false);
			rightPanel.add(getBtnClearLog());
			panel.add(rightPanel, BorderLayout.EAST);
		}
		return panel;
	}

	protected JButton getBtnClearLog() {
		if (btnClearLog == null) {
			btnClearLog = new JButton();
			btnClearLog.setPreferredSize(new Dimension(80, 24));
			btnClearLog.setName("pagegen-clearLog");
			btnClearLog.setAction(new ClearLogAction());
		}
		return btnClearLog;
	}

	private class ClearLogAction extends AbstractAction {
		public ClearLogAction() {
			putValue(NAME, Resources.getString("button.clearLog"));
			putValue(SMALL_ICON, Resources.getIcon("icon.remove"));
			putValue(SHORT_DESCRIPTION, Resources.getString("button.clearLog.tooltip"));
		}

		@Override
		public void actionPerformed(ActionEvent e) {
			getLogText().setText(null);
		}
	}

	protected JLabel getConfigurationLabel() {
		if (configurationLabel == null) {
			configurationLabel = new JLabel(Resources.getString("label.configuration"));
			configurationLabel.setHorizontalAlignment(SwingConstants.RIGHT);
		}
		return configurationLabel;
	}

	@SuppressWarnings({ "rawtypes", "unchecked" })
	protected JComboBox getConfigurationComboBox() {
		if (configurationComboBox == null) {
			configurationComboBox = new JComboBox();
			configurationComboBox.setMinimumSize(new Dimension(23, 28));
			configurationComboBox.setPreferredSize(new Dimension(250, 28));
			configurationComboBox.setRenderer(new ConfigurationRenderer());
			ActionListener listener = new ActionListener() {
				@Override
				public void actionPerformed(ActionEvent e) {
					PageConfiguration configuration = (PageConfiguration) configurationComboBox.getSelectedItem();
					if (configuration != null) {
						PageConfigurations.getInstance().setActiveConfiguration(configuration.getName());
						getBtnDeleteConfiguration().setEnabled(!configuration.isSystemConfiguration());
					}
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
		if (active != null) {
			getBtnDeleteConfiguration().getAction().setEnabled(!active.isSystemConfiguration());
			getConfigurationComboBox().setSelectedItem(active);
		}
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
			logLabel = new JLabel(Resources.getString("label.log"));
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
		if (type == PageConfigurationChangeType.CREATE) {
			model.addElement(config);
		} else if (type == PageConfigurationChangeType.SAVE) {
			getConfigurationComboBox().repaint();
		} else if (type == PageConfigurationChangeType.DELETE) {
			model.removeElement(config);
		}
	}

	protected JPanel getConfigPanel() {
		if (configPanel == null) {
			configPanel = new JPanel();
			configPanel.setOpaque(false);
			configPanel.setLayout(new FlowLayout(FlowLayout.LEFT, 2, 0));
			configPanel.add(getConfigurationComboBox());
			configPanel.add(getBtnDeleteConfiguration());
		}
		return configPanel;
	}

	protected JButton getBtnDeleteConfiguration() {
		if (btnDeleteConfiguration == null) {
			btnDeleteConfiguration = new JButton();
			btnDeleteConfiguration.setName("btnDeleteConfiguration");
			btnDeleteConfiguration.setPreferredSize(new Dimension(40, 28));
			btnDeleteConfiguration.setAction(new DeleteAction());
		}
		return btnDeleteConfiguration;
	}

	private class DeleteAction extends AbstractAction {
		DeleteAction() {
			putValue(SHORT_DESCRIPTION, Resources.getString("button.deleteConfiguration"));
			putValue(LARGE_ICON_KEY, Resources.getIcon("icon.remove"));
			setEnabled(false);
		}

		@Override
		public void actionPerformed(ActionEvent e) {
			PageConfiguration selected = (PageConfiguration) getConfigurationComboBox().getSelectedItem();
			if (selected != null) {
				PageConfigurations.getInstance().delete(selected);
			}
		}
	}
}
