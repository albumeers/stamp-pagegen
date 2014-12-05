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

import java.awt.BorderLayout;
import java.awt.Color;
import java.awt.event.ActionEvent;
import java.awt.event.KeyEvent;
import java.awt.event.WindowAdapter;
import java.awt.event.WindowEvent;
import java.io.IOException;
import java.util.Map;
import java.util.logging.Level;
import java.util.logging.Logger;
import javax.imageio.ImageIO;
import javax.swing.AbstractAction;
import static javax.swing.Action.LARGE_ICON_KEY;
import static javax.swing.Action.NAME;
import static javax.swing.Action.SMALL_ICON;
import javax.swing.JCheckBoxMenuItem;
import javax.swing.JFrame;
import javax.swing.JLabel;
import javax.swing.JMenu;
import javax.swing.JMenuBar;
import javax.swing.JMenuItem;
import javax.swing.JOptionPane;
import javax.swing.SwingUtilities;
import javax.swing.UIManager;
import javax.swing.border.BevelBorder;
import javax.swing.border.SoftBevelBorder;
import org.bushe.swing.event.EventBus;
import org.bushe.swing.event.annotation.AnnotationProcessor;
import org.bushe.swing.event.annotation.EventSubscriber;
import org.javad.components.AboutDialog;
import org.javad.components.StatusPanel;
import org.javad.components.UIHelper;
import org.javad.components.model.AboutDialogBean;
import org.javad.pdf.fonts.FontRegistry;
import org.javad.pdf.model.PageConfiguration;
import org.javad.pdf.model.PageConfigurations;
import org.javad.stamp.htmlparser.ui.AlbumConversionPanel;
import org.javad.stamp.pdf.Resources;
import org.javad.stamp.pdf.events.PdfAppEvent;
import org.javad.stamp.pdf.events.PdfAppEvent.EventType;
import org.javad.stamp.pdf.ui.model.GenerateBean;
import org.javad.stamp.pdf.ui.tasks.GeneratePdfTask;
import org.javad.stamp.pdf.ui.tasks.GenerateXmlTask;

@SuppressWarnings("serial")
public class StampAlbumGenerator extends JFrame {
	private JMenuBar menuBar;
	
	private JMenuItem menuFileExit;
	private AlbumGeneratorPanel albumGeneratorPanel;
	private AlbumConversionPanel albumConversionPanel;
	private static final Logger logger = Logger.getLogger(StampAlbumGenerator.class.getName());
	private StatusPanel statusPanel;
	private JMenu menuFile;
	private JMenu menuConfiguration;
	private JMenu menuHelp;
	private JMenuItem menuHelpAbout;
	private JMenuItem menuOptionsSettings;
	private JCheckBoxMenuItem menuConvertAlbum;
        
	private SettingsDialog settingsDialog;
	private JMenuItem menuConfigureNew;
	private JMenuItem menuConfigureReset;
	private JMenu menuOptions;
	private JCheckBoxMenuItem menuHelpLogging;
	private JMenu menuHelpDebug;
	
	public StampAlbumGenerator() {
		initialize();
	}
	
	protected void initialize() {
		setName("stamp-pagegen");
		setDefaultCloseOperation(JFrame.DISPOSE_ON_CLOSE);
		AnnotationProcessor.process(this);
		setJMenuBar(getMenuBar_1());
		setTitle(Resources.getString("title.generator.application")); //$NON-NLS-1$
		try {
			setIconImage(ImageIO.read(getClass().getResource(Resources.getIconName("icon.application.generate")))); //$NON-NLS-1$
		} catch (IOException e) {
			logger.log(Level.SEVERE,"There was an error setting the icon for the application", e); //$NON-NLS-1$
		}
		FontRegistry.getInstance().initializeFontPath();
		getContentPane().add(getAlbumGeneratorPanel(), BorderLayout.CENTER);
		getContentPane().add(getStatusPanel(), BorderLayout.SOUTH);
	}

	protected JMenuBar getMenuBar_1() {
		if (menuBar == null) {
			menuBar = new JMenuBar();
			menuBar.add(getMenuFile());
			menuBar.add(getMenuOptions());
			menuBar.add(getMenuHelp());
		}
		return menuBar;
	}
	protected JMenu getMenuFile() {
		if (menuFile == null) {
			menuFile = new JMenu(Resources.getString("menu.file")); //$NON-NLS-1$
			menuFile.add(getMenuFileExit());
		}
		return menuFile;
	}
	protected JMenuItem getMenuFileExit() {
		if (menuFileExit == null) {
			menuFileExit = new JMenuItem(Resources.getString("menu.file.exit")); //$NON-NLS-1$
			menuFileExit.setMnemonic(KeyEvent.VK_X);
			menuFileExit.setAction(new ExitAction());
		}
		return menuFileExit;
	}
	
	protected JMenu getMenuHelp() {
		if (menuHelp == null) {
			menuHelp = new JMenu(Resources.getString("menu.help")); //$NON-NLS-1$
			menuHelp.add(getMenuHelpDebug());
			menuHelp.add(getMenuHelpAbout());
		}
		return menuHelp;
	}
	protected JMenuItem getMenuHelpAbout() {
		if (menuHelpAbout == null) {
			menuHelpAbout = new JMenuItem(Resources.getString("menu.help.about")); //$NON-NLS-1$
			menuHelpAbout.setName("menu.help.about");
			menuHelpAbout.setAction(new HelpAboutAction());
		}
		return menuHelpAbout;
	}
	
	private JMenu getMenuConfiguration() {
		if (menuConfiguration == null) {
			menuConfiguration = new JMenu(Resources.getString("menu.configure"));
			menuConfiguration.add(getMenuConfigureNew());
			menuConfiguration.add(getMenuConfigureReset());
		}
		return menuConfiguration;
	}
	private JMenuItem getMenuOptionsSettings() {
		if (menuOptionsSettings == null) {
			menuOptionsSettings = new JMenuItem(Resources.getString("menu.options.settings")); //$NON-NLS-1$
			menuOptionsSettings.setName("menu.options.settings");
			menuOptionsSettings.setAction(new OptionsAction());
		}
		return menuOptionsSettings;
	}
        
        private JCheckBoxMenuItem getMenuConvertAlbum() {
		if (menuConvertAlbum == null) {
			menuConvertAlbum = new  JCheckBoxMenuItem(Resources.getString("menu.options.convert")); //$NON-NLS-1$
			menuConvertAlbum.setName("menu.options.convert");
			menuConvertAlbum.setAction(new ConvertAction());
		}
		return menuConvertAlbum;
	}
        
        
	
	protected JMenuItem getMenuConfigureNew() {
		if (menuConfigureNew == null) {
			menuConfigureNew = new JMenuItem(Resources.getString("menu.configure.newConfig")); //$NON-NLS-1$
			menuConfigureNew.setName("menu.configure.new");
			menuConfigureNew.setAction(new NewConfigurationAction());
		}
		return menuConfigureNew;
	}
	
	protected JMenuItem getMenuConfigureReset() {
		if (menuConfigureReset == null) {
			menuConfigureReset = new JMenuItem(Resources.getString("menu.configure.resetAll")); //$NON-NLS-1$
			menuConfigureReset.setName("menu.configure.reset");
			menuConfigureReset.setAction(new ResetConfigurationAction());
		}
		return menuConfigureReset;
	}
	
	protected JMenu getMenuOptions() {
		if (menuOptions == null) {
			menuOptions = new JMenu(Resources.getString("menu.options")); //$NON-NLS-1$
			menuOptions.add(getMenuConfiguration());
			menuOptions.add(getMenuOptionsSettings());
                        menuOptions.add(getMenuConvertAlbum());
		}
		return menuOptions;
	}
	
	protected JCheckBoxMenuItem getMenuHelpLogging() {
		if (menuHelpLogging == null) {
			menuHelpLogging = new JCheckBoxMenuItem(new VerboseLoggingAction()); //$NON-NLS-1$
			menuHelpLogging.setName("menu.help.logging");
		}
		return menuHelpLogging;
	}
	
	protected JMenu getMenuHelpDebug() {
		if (menuHelpDebug == null) {
			menuHelpDebug = new JMenu(Resources.getString("menu.help.debug")); //$NON-NLS-1$
			menuHelpDebug.setIcon(Resources.getIcon("icon.support")); //$NON-NLS-1$
			menuHelpDebug.add(getMenuHelpLogging());
		}
		return menuHelpDebug;
	}
	
	private void disposeWindow() {
		processWindowEvent( new WindowEvent( this, WindowEvent.WINDOW_CLOSING)); 
	}
	
	
	private static void createAndShowGUI() {
		final StampAlbumGenerator creator = new StampAlbumGenerator();
		creator.addWindowListener(new WindowAdapter() {
			@Override
			public void windowClosed(WindowEvent e) {
				AnnotationProcessor.unprocess(creator);
				EventBus.clearAllSubscribers();
				System.exit(0);
			}
		});
		creator.setSize(630,500);
		creator.setVisible(true);
		
	}
	
	public static void main(String[] args) {
		try {
			UIManager.setLookAndFeel("com.sun.java.swing.plaf.nimbus.NimbusLookAndFeel");  //$NON-NLS-1$
		} catch (Exception e) {
			e.printStackTrace();
		}
		SwingUtilities.invokeLater(new Runnable() {
			public void run() {
				createAndShowGUI();
			}

			
		});
	}

	private class ExitAction extends AbstractAction {
		public ExitAction() {
			putValue(NAME, Resources.getString("menu.file.exit")); //$NON-NLS-1$
		}
		public void actionPerformed(ActionEvent e) {
			disposeWindow();
		}
	}
        
        protected AlbumConversionPanel getAlbumConversionPanel() {
		if (albumConversionPanel == null) {
			albumConversionPanel = new AlbumConversionPanel();
			albumConversionPanel.setBorder(new SoftBevelBorder(BevelBorder.RAISED, null, null, null, null));
		}
		return albumConversionPanel;
	}
        
	protected AlbumGeneratorPanel getAlbumGeneratorPanel() {
		if (albumGeneratorPanel == null) {
			albumGeneratorPanel = new AlbumGeneratorPanel();
			albumGeneratorPanel.getOutputFolderText().setEditable(false);
			albumGeneratorPanel.getInputFileText().setEditable(false);
			albumGeneratorPanel.setBorder(new SoftBevelBorder(BevelBorder.RAISED, null, null, null, null));
		}
		return albumGeneratorPanel;
	}
	protected StatusPanel getStatusPanel() {
		if (statusPanel == null) {
			statusPanel = new StatusPanel() {
				@Override
				protected JLabel getLblStatusLabel() {
					JLabel label = super.getLblStatusLabel();
					label.setForeground(Color.BLACK);
					return label;
				}
			};
			statusPanel.setForeground(new Color(211, 211, 211));
			statusPanel.setBackground(new Color(248, 248, 255));
			statusPanel.showPositionLabel(false);
			statusPanel.showZoomLabel(false);
		}
		return statusPanel;
	}
	
	@EventSubscriber(eventClass=PdfAppEvent.class)
	public void handleAppEvent( PdfAppEvent event ) {
		if ( event.getType() == EventType.Generate ) {
			GenerateBean bean = event.getData();
			GeneratePdfTask task = new GeneratePdfTask(bean);
			task.execute();
		} else if ( event.getType() == EventType.GenerateXml) {
                    Map<String,String> fileMap = event.getData();
                    GenerateXmlTask task = new GenerateXmlTask(fileMap);
                    task.execute();
                }
	}
	
	protected SettingsDialog getSettingsDialog() {
		if( settingsDialog == null ) {
			settingsDialog = new SettingsDialog(this);
		}
		return settingsDialog;
	}
	
	
	
	public class NewConfigurationAction extends AbstractAction {

		public NewConfigurationAction() {
			putValue(NAME, Resources.getString("menu.configure.newConfig")); //$NON-NLS-1$
		}
		
		@Override
		public void actionPerformed(ActionEvent e) {
			NewConfigurationPanel panel = new NewConfigurationPanel();
			panel.loadConfigurations();
			int result = JOptionPane.showOptionDialog(getAlbumGeneratorPanel(),panel, Resources.getString("title.newConfiguration"), JOptionPane.OK_CANCEL_OPTION, JOptionPane.PLAIN_MESSAGE, null,null,null);
			if( result == JOptionPane.OK_OPTION) {
				PageConfiguration config = panel.getConfiguration();
				PageConfigurations.getInstance().create(config);
			}
		}
	}
	
        
    public class ConvertAction extends AbstractAction {

        public ConvertAction() {
            putValue(NAME, Resources.getString("menu.options.convert")); //$NON-NLS-1$
            putValue(SMALL_ICON, Resources.getIcon("icon.convert")); //$NON-NLS-1$
            putValue(LARGE_ICON_KEY, Resources.getIcon("icon.convert.medium")); //$NON-NLS-1$
        }

        @Override
        public void actionPerformed(ActionEvent e) {
            if (getMenuConvertAlbum().isSelected()) {
                getContentPane().remove(getAlbumGeneratorPanel());
                getContentPane().add(getAlbumConversionPanel(), BorderLayout.CENTER);
            } else {
                getContentPane().remove(getAlbumConversionPanel());
                getContentPane().add(getAlbumGeneratorPanel(), BorderLayout.CENTER);
            }
            getContentPane().doLayout();
            getContentPane().paintAll(getContentPane().getGraphics());
        }

    }
                
                
	public class OptionsAction extends AbstractAction {
		
		public OptionsAction() {
			putValue(NAME, Resources.getString("menu.options.settings")); //$NON-NLS-1$
			putValue(SMALL_ICON, Resources.getIcon("icon.settings")); //$NON-NLS-1$
			putValue(LARGE_ICON_KEY, Resources.getIcon("icon.settings.medium")); //$NON-NLS-1$
		}

		@Override
		public void actionPerformed(ActionEvent e) {
			UIHelper.center(getRootPane(),getSettingsDialog());
			getSettingsDialog().setVisible(true);
		}
		
	}
	
	public class ResetConfigurationAction extends AbstractAction {

		public ResetConfigurationAction() {
			putValue(NAME, Resources.getString("menu.configure.resetAll")); //$NON-NLS-1$
		}
		
		@Override
		public void actionPerformed(ActionEvent e) {
			int result = JOptionPane.showConfirmDialog(getAlbumGeneratorPanel(), Resources.getString("message.resetAll"),Resources.getString("title.resetAll"), JOptionPane.YES_NO_OPTION); //$NON-NLS-1$
			if( result == JOptionPane.YES_OPTION) {
				PageConfigurations.getInstance().revertAll();
			}
		}
	}
	
	public class HelpAboutAction extends AbstractAction {

		public HelpAboutAction() {
			putValue(NAME, Resources.getString("menu.help.about")); //$NON-NLS-1$
			putValue(SMALL_ICON, Resources.getIcon("icon.help.about")); //$NON-NLS-1$
		}
		
		@Override
		public void actionPerformed(ActionEvent e) {
			AboutDialogBean bean = new AboutDialogBean();
			bean.setTitle(Resources.getString("title.helpAbout.application"));
			bean.setApplicationIcon(Resources.getIcon("icon.application.large"));
			bean.setApplicationInfo(Resources.getString("label.helpAbout.applicationInfo"));
			bean.setApplicationLink(Resources.getString("label.helpAbout.applicationLink"));
			AboutDialog dialog = new AboutDialog(bean);
			UIHelper.center(getRootPane(), dialog);
			dialog.setVisible(true);
		}
		
	}
	
	public class VerboseLoggingAction extends AbstractAction {

		public VerboseLoggingAction() {
			putValue(NAME, Resources.getString("menu.help.logging")); //$NON-NLS-1$
		}
		
		@Override
		public void actionPerformed(ActionEvent e) {
			Level level = ( getMenuHelpLogging().isSelected()) ? Level.FINEST : Level.INFO;
			Logger logger = Logger.getLogger("org.javad");
			logger.setLevel(level);
		}
		
	}
	

	
}
