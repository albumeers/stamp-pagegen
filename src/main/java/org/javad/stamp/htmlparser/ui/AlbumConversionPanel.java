/*
 Copyright 2014 Jason Drake (jadrake75@gmail.com)
 
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
package org.javad.stamp.htmlparser.ui;

import java.awt.Color;
import java.awt.event.ActionEvent;
import java.io.File;
import java.io.IOException;
import java.text.MessageFormat;
import java.util.HashMap;
import java.util.Map;
import java.util.logging.Handler;
import java.util.logging.Level;
import java.util.logging.LogRecord;
import java.util.logging.Logger;
import java.util.prefs.BackingStoreException;
import java.util.prefs.Preferences;
import javax.swing.AbstractAction;
import static javax.swing.Action.LARGE_ICON_KEY;
import static javax.swing.Action.NAME;
import static javax.swing.Action.SHORT_DESCRIPTION;
import javax.swing.JFileChooser;
import javax.swing.JOptionPane;
import javax.swing.filechooser.FileFilter;
import org.bushe.swing.event.EventBus;
import org.bushe.swing.event.annotation.AnnotationProcessor;
import org.bushe.swing.event.annotation.EventSubscriber;
import org.javad.events.StatusEvent;
import org.javad.stamp.htmlparser.msword.styles.PageStyle;
import org.javad.stamp.pdf.Resources;
import org.javad.stamp.pdf.events.PdfAppEvent;
import org.javad.stamp.pdf.ui.GeneratorConstants;
import pub.domain.GradientPanel;

/**
 *
 * @author Jason
 */
public class AlbumConversionPanel extends GradientPanel {

    private JFileChooser htmlChooser;
    private JFileChooser dirChooser;
    private String default_folder = null;
    private String default_output_folder = null;
        
    private static final Logger logger = Logger.getLogger(AlbumConversionPanel.class.getName());
    
    /**
     * Creates new form AlbumConversionPanel
     */
    public AlbumConversionPanel() {
        setBackground(new Color(248, 248, 255));
        setForeground(new Color(211, 211, 211));
        AnnotationProcessor.process(this);
        initComponents();
        
        Logger.getLogger("org.javad").setLevel(Level.INFO);
        Logger.getLogger("org.javad").addHandler(new Handler() {
            
            @Override
            public void publish(LogRecord record) {
                textMessage.append(record.getMessage() + "\n");
            }
            
            @Override
            public void flush() {
            }
            
            @Override
            public void close() throws SecurityException {
                textMessage.setText(null);
            }
            
        });
        
        String folder = default_output_folder;
        if (default_output_folder == null) {
            Preferences prefs = Resources.getPreferencesNode();
            folder = prefs.get(GeneratorConstants.DEFAULT_XML_OUTPUT_FOLDER_KEY, null);
        }
        if (folder != null) {
            textDirectory.setText(folder);
        }
        
    }
    
    protected JFileChooser getDirectoryChooser() {
		if (dirChooser == null) {
			dirChooser = new JFileChooser();
			dirChooser.setName("pagegen-dirchooser");
			dirChooser.setAcceptAllFileFilterUsed(false);
			dirChooser.setFileSelectionMode(JFileChooser.DIRECTORIES_ONLY);
			dirChooser.setFileFilter(new OutputFileFilter());
			String folder = default_output_folder;
			if( default_output_folder == null ) {
				Preferences prefs = Resources.getPreferencesNode();
				folder = prefs.get(GeneratorConstants.DEFAULT_XML_OUTPUT_FOLDER_KEY, null);
			}
			if( folder != null ) {
				File f = new File(folder);
				if( f.exists() && f.isDirectory()) {
					dirChooser.setCurrentDirectory(f);
				}
			}
		}
		return dirChooser;
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

    private JFileChooser getHtmlChooser() {
        if (htmlChooser == null) {
            htmlChooser = new JFileChooser();
            htmlChooser.setName("pagegen-htmlChooser");
            htmlChooser.setAcceptAllFileFilterUsed(false);
            htmlChooser.setFileFilter(new InputFileFilter());
            String folder = default_folder;
            if (default_folder == null) {
                Preferences prefs = Resources.getPreferencesNode();
                folder = prefs.get(GeneratorConstants.DEFAULT_HTML_FOLDER_KEY, null);
            }
            if (folder != null) {
                File f = new File(folder);
                if (f.exists()) {
                    htmlChooser.setCurrentDirectory(f);
                }
            }
        }
        return htmlChooser;
    }
    
    private class ChooseOutputFolder extends AbstractAction {

        public ChooseOutputFolder() {
            putValue(SHORT_DESCRIPTION, Resources.getString("label.outputFolder.tooltip")); //$NON-NLS-1$
            putValue(LARGE_ICON_KEY, Resources.getIcon("icon.folderOutput")); //$NON-NLS-1$
        }

        @Override
        public void actionPerformed(ActionEvent e) {
            if (JFileChooser.APPROVE_OPTION == getDirectoryChooser().showOpenDialog(buttonDirectory)) {
                File f = getDirectoryChooser().getSelectedFile();
                if (f != null) {
                    Preferences prefs = Resources.getPreferencesNode();
                    prefs.put(GeneratorConstants.DEFAULT_XML_OUTPUT_FOLDER_KEY, f.getPath());
                    default_output_folder = f.getPath();
                    try {
                        prefs.flush();
                    } catch (BackingStoreException e1) {
                        logger.log(Level.SEVERE, "Unable to save default folder.", e1); //$NON-NLS-1$
                    }
                    textDirectory.setText(f.getAbsolutePath());
                    buttonGenerate.setEnabled(!textFile.getText().isEmpty());
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
            prefs.put(GeneratorConstants.DEFAULT_INPUT_HTML_FILE_KEY, textFile.getText());
            EventBus.publish(new StatusEvent(StatusEvent.StatusType.ShowBusy, Resources.getString("message.generating"))); //$NON-NLS-1$
            Map<String,String> map = new HashMap<>();
            map.put("input", textFile.getText());
            map.put("output", textDirectory.getText());
            map.put("pageType", PageStyle.StyleType.Legacy.toString());
            EventBus.publish(new PdfAppEvent(PdfAppEvent.EventType.GenerateXml, map));
        }

    }

    @EventSubscriber(eventClass = PdfAppEvent.class)
    public void handleAppEvent(PdfAppEvent evt) {
        if (evt.getType() == PdfAppEvent.EventType.Generate_Error) {
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
    
    private class ChooseInputFile extends AbstractAction {

        public ChooseInputFile() {
            putValue(SHORT_DESCRIPTION, Resources.getString("label.inputFile.tooltip")); //$NON-NLS-1$
            putValue(LARGE_ICON_KEY, Resources.getIcon("icon.fileInput")); //$NON-NLS-1$
        }

        @Override
        public void actionPerformed(ActionEvent e) {
            if (JFileChooser.APPROVE_OPTION == getHtmlChooser().showOpenDialog(buttonFile)) {
                File f = getHtmlChooser().getSelectedFile();
                if (f != null) {
                    if (f.getParent() != null) {
                        Preferences prefs = Resources.getPreferencesNode();
                        prefs.put(GeneratorConstants.DEFAULT_HTML_FOLDER_KEY, f.getParent());
                        try {
                            prefs.flush();
                        } catch (BackingStoreException e1) {
                            logger.log(Level.SEVERE, "Unable to save default folder.", e1); //$NON-NLS-1$
                        }
                    }
                    textFile.setText(f.getAbsolutePath());
                    buttonGenerate.setEnabled(!textDirectory.getText().isEmpty());
                }
            }

        }

    }
    
    private class InputFileFilter extends FileFilter {

        @Override
        public boolean accept(File f) {
            return (f.isDirectory() && f.canRead()) || (f.isFile() && f.canRead() && f.getName().toLowerCase().endsWith(".html"));
        }

        @Override
        public String getDescription() {
            return Resources.getString("filter.html"); //$NON-NLS-1$
        }
    }
                        
                        
    /**
     * This method is called from within the constructor to initialize the form.
     * WARNING: Do NOT modify this code. The content of this method is always
     * regenerated by the Form Editor.
     */
    @SuppressWarnings("unchecked")
    // <editor-fold defaultstate="collapsed" desc="Generated Code">//GEN-BEGIN:initComponents
    private void initComponents() {

        labelFile = new javax.swing.JLabel();
        textFile = new javax.swing.JTextField();
        buttonFile = new javax.swing.JButton();
        labelDirectory = new javax.swing.JLabel();
        textDirectory = new javax.swing.JTextField();
        buttonDirectory = new javax.swing.JButton();
        buttonGenerate = new javax.swing.JButton();
        scrollPane = new javax.swing.JScrollPane();
        textMessage = new javax.swing.JTextArea();
        labelMessage = new javax.swing.JLabel();

        labelFile.setText("Input File:");

        textFile.setEditable(false);

        buttonFile.setAction(new ChooseInputFile());
        buttonFile.setIcon(new javax.swing.ImageIcon("C:\\dev\\netbeans_projects\\stamp-pagegen\\src\\main\\resources\\images\\html-document-16x16.png")); // NOI18N

        labelDirectory.setText("Output Directory:");

        textDirectory.setEditable(false);

        buttonDirectory.setAction(new ChooseOutputFolder());
        buttonDirectory.setIcon(new javax.swing.ImageIcon("C:\\dev\\netbeans_projects\\stamp-pagegen\\src\\main\\resources\\images\\folder-icon-16x16.png")); // NOI18N

        buttonGenerate.setAction(new GenerateAction());
        buttonGenerate.setText("Generate...");
        buttonGenerate.setName("geneateButton"); // NOI18N

        textMessage.setEditable(false);
        textMessage.setColumns(20);
        textMessage.setRows(5);
        scrollPane.setViewportView(textMessage);

        labelMessage.setText("Messages:");

        javax.swing.GroupLayout layout = new javax.swing.GroupLayout(this);
        this.setLayout(layout);
        layout.setHorizontalGroup(
            layout.createParallelGroup(javax.swing.GroupLayout.Alignment.LEADING)
            .addGroup(layout.createSequentialGroup()
                .addContainerGap()
                .addGroup(layout.createParallelGroup(javax.swing.GroupLayout.Alignment.LEADING)
                    .addGroup(layout.createSequentialGroup()
                        .addComponent(buttonGenerate)
                        .addContainerGap(javax.swing.GroupLayout.DEFAULT_SIZE, Short.MAX_VALUE))
                    .addGroup(layout.createSequentialGroup()
                        .addGroup(layout.createParallelGroup(javax.swing.GroupLayout.Alignment.LEADING, false)
                            .addComponent(labelDirectory)
                            .addComponent(labelFile, javax.swing.GroupLayout.DEFAULT_SIZE, javax.swing.GroupLayout.DEFAULT_SIZE, Short.MAX_VALUE)
                            .addComponent(labelMessage, javax.swing.GroupLayout.DEFAULT_SIZE, 92, Short.MAX_VALUE))
                        .addPreferredGap(javax.swing.LayoutStyle.ComponentPlacement.RELATED)
                        .addGroup(layout.createParallelGroup(javax.swing.GroupLayout.Alignment.LEADING)
                            .addGroup(layout.createSequentialGroup()
                                .addGroup(layout.createParallelGroup(javax.swing.GroupLayout.Alignment.LEADING, false)
                                    .addComponent(textFile)
                                    .addComponent(textDirectory, javax.swing.GroupLayout.DEFAULT_SIZE, 243, Short.MAX_VALUE))
                                .addPreferredGap(javax.swing.LayoutStyle.ComponentPlacement.RELATED)
                                .addGroup(layout.createParallelGroup(javax.swing.GroupLayout.Alignment.LEADING, false)
                                    .addComponent(buttonDirectory, javax.swing.GroupLayout.DEFAULT_SIZE, javax.swing.GroupLayout.DEFAULT_SIZE, Short.MAX_VALUE)
                                    .addComponent(buttonFile, javax.swing.GroupLayout.DEFAULT_SIZE, javax.swing.GroupLayout.DEFAULT_SIZE, Short.MAX_VALUE)))
                            .addGroup(layout.createSequentialGroup()
                                .addComponent(scrollPane, javax.swing.GroupLayout.DEFAULT_SIZE, 325, Short.MAX_VALUE)
                                .addContainerGap())))))
        );
        layout.setVerticalGroup(
            layout.createParallelGroup(javax.swing.GroupLayout.Alignment.LEADING)
            .addGroup(layout.createSequentialGroup()
                .addContainerGap()
                .addGroup(layout.createParallelGroup(javax.swing.GroupLayout.Alignment.BASELINE)
                    .addComponent(labelFile)
                    .addComponent(textFile, javax.swing.GroupLayout.PREFERRED_SIZE, javax.swing.GroupLayout.DEFAULT_SIZE, javax.swing.GroupLayout.PREFERRED_SIZE)
                    .addComponent(buttonFile))
                .addPreferredGap(javax.swing.LayoutStyle.ComponentPlacement.UNRELATED)
                .addGroup(layout.createParallelGroup(javax.swing.GroupLayout.Alignment.BASELINE)
                    .addComponent(labelDirectory)
                    .addComponent(textDirectory, javax.swing.GroupLayout.PREFERRED_SIZE, javax.swing.GroupLayout.DEFAULT_SIZE, javax.swing.GroupLayout.PREFERRED_SIZE)
                    .addComponent(buttonDirectory))
                .addPreferredGap(javax.swing.LayoutStyle.ComponentPlacement.UNRELATED)
                .addComponent(buttonGenerate)
                .addGap(18, 18, 18)
                .addGroup(layout.createParallelGroup(javax.swing.GroupLayout.Alignment.LEADING)
                    .addGroup(layout.createSequentialGroup()
                        .addComponent(labelMessage)
                        .addGap(0, 0, Short.MAX_VALUE))
                    .addComponent(scrollPane))
                .addContainerGap())
        );
    }// </editor-fold>//GEN-END:initComponents


    // Variables declaration - do not modify//GEN-BEGIN:variables
    private javax.swing.JButton buttonDirectory;
    private javax.swing.JButton buttonFile;
    private javax.swing.JButton buttonGenerate;
    private javax.swing.JLabel labelDirectory;
    private javax.swing.JLabel labelFile;
    private javax.swing.JLabel labelMessage;
    private javax.swing.JScrollPane scrollPane;
    private javax.swing.JTextField textDirectory;
    private javax.swing.JTextField textFile;
    private javax.swing.JTextArea textMessage;
    // End of variables declaration//GEN-END:variables
}
