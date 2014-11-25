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
import java.awt.Component;
import java.awt.Dimension;
import java.awt.FlowLayout;
import java.awt.Frame;
import java.awt.GridLayout;
import java.awt.event.ActionEvent;
import java.io.IOException;
import java.util.logging.Level;
import java.util.logging.Logger;

import javax.imageio.ImageIO;
import javax.swing.AbstractAction;
import javax.swing.JButton;
import javax.swing.JDialog;
import javax.swing.JPanel;
import javax.swing.JTabbedPane;
import javax.swing.UIManager;
import javax.swing.border.EtchedBorder;
import javax.swing.border.TitledBorder;

import org.bushe.swing.event.EventBus;
import org.javad.components.ISettingsPanel;
import org.javad.components.IconLabel;
import org.javad.events.StatusEvent;
import org.javad.events.StatusEvent.StatusType;
import org.javad.pdf.fonts.ui.FontMappingPanel;
import org.javad.pdf.fonts.ui.FontSettingPanel;
import org.javad.pdf.model.PageConfiguration;
import org.javad.pdf.model.PageConfigurations;
import org.javad.stamp.pdf.Resources;

import pub.domain.GradientPanel;

@SuppressWarnings("serial")
public class SettingsDialog extends JDialog {
	private JPanel buttonPanel;
	private JTabbedPane tabbedPane;
	
	private JButton buttonOk;
	private JButton buttonCancel;
	private GradientPanel mainPanel;
	
	private PageLayoutSettingsPanel pageLayoutSettingsPanel;
	private FontMappingPanel fontMappingPanel;
	private FontSettingPanel fontSettingPanel;
	
	private Logger logger = Logger.getLogger(SettingsDialog.class.getName());
	
	
	public SettingsDialog(Frame frame)  {
		super(frame);
		initialize();
	}
	
	private void initialize() {
		setModal(true);
		try {
			setIconImage(ImageIO.read(getClass().getResource(Resources.getIconName("icon.settings")))); //$NON-NLS-1$
		} catch (IOException e) {
			logger.log(Level.WARNING, "Icon failed to load.", e);
		}
		getContentPane().setLayout(new GridLayout(0, 1, 0, 0));
		getContentPane().add(getMainPanel());
		setSize(700,500);
		setTitle(Resources.getString("title.settings")); //$NON-NLS-1$
		setName("settingsDialog"); //$NON-NLS-1$
	}
	
	@Override
	public void setVisible(boolean visible) {
		if( visible ) {
			PageConfiguration configuration = PageConfigurations.getInstance().getActiveConfiguration();
			for(int i = 0; i < getTabbedPane().getComponentCount(); i ++ ) {
				Component c = getTabbedPane().getComponent(i);
				if( c instanceof ISettingsPanel ) {
					ISettingsPanel panel = (ISettingsPanel)c;
					if( panel instanceof IPageConfigurationSettingsPanel) {
						((IPageConfigurationSettingsPanel)panel).setConfiguration(configuration);
					}
					panel.loadSettings();
				}
			}
		}
		super.setVisible(visible);
	}
	
	protected JPanel getButtonPanel() {
		if (buttonPanel == null) {
			buttonPanel = new JPanel();
			buttonPanel.setMinimumSize(new Dimension(100, 40));
			buttonPanel.setBorder(null);
			buttonPanel.setPreferredSize(new Dimension(100, 40));
			buttonPanel.setOpaque(false);
			buttonPanel.setLayout(new FlowLayout(FlowLayout.RIGHT, 5, 5));
			buttonPanel.add(getButtonOk());
			buttonPanel.add(getButtonCancel());
		}
		return buttonPanel;
	}
	protected JTabbedPane getTabbedPane() {
		if (tabbedPane == null) {
			tabbedPane = new JTabbedPane(JTabbedPane.LEFT);
			tabbedPane.setBorder(new EtchedBorder(EtchedBorder.LOWERED, null, null));
			tabbedPane.addTab("", null, getPageLayoutSettingsPanel(), null); //$NON-NLS-1$
			tabbedPane.addTab("",null, getFontSettingPanel(), null);
			tabbedPane.addTab("",null, getFontMappingPanel(), null);
			IconLabel pageSettingsLabel = new IconLabel(Resources.getString("settings.tab.margins"), Resources.getIcon("icon.margins.medium")); //$NON-NLS-1$ //$NON-NLS-2$
			pageSettingsLabel.setPreferredSize(new Dimension(100,65));
			pageSettingsLabel.setName("settingsDialog-pageSettings"); //$NON-NLS-1$
			
			IconLabel fontMappingLabel = new IconLabel(Resources.getString("settings.tab.fontMapping"), Resources.getIcon("icon.fontmapping.medium")); //$NON-NLS-1$ //$NON-NLS-2$
			fontMappingLabel.setPreferredSize(new Dimension(100,65));
			fontMappingLabel.setName("settingsDialog-fontMappingLabel"); //$NON-NLS-1$
			
			IconLabel fontLabel = new IconLabel(Resources.getString("settings.tab.fonts"), Resources.getIcon("icon.systemFont.medium")); //$NON-NLS-1$ //$NON-NLS-2$
			fontLabel.setPreferredSize(new Dimension(100,65));
			fontLabel.setName("settingsDialog-fontSettingLabel"); //$NON-NLS-1$
			
			tabbedPane.setTabComponentAt(0, pageSettingsLabel);
			tabbedPane.setTabComponentAt(1, fontLabel);
			tabbedPane.setTabComponentAt(2, fontMappingLabel);
			
		}
		return tabbedPane;
	}
	
	protected FontSettingPanel getFontSettingPanel() {
		if( fontSettingPanel == null ) {
			fontSettingPanel = new FontSettingPanel();
			fontSettingPanel.setBorder(new TitledBorder(UIManager.getBorder("TitledBorder.border"), Resources.getString("settings.tab.fonts.title"), TitledBorder.LEADING, TitledBorder.TOP, null, new Color(0, 0, 0)));
			fontSettingPanel.setOpaque(false);
		}
		return fontSettingPanel;
	}
	
	protected FontMappingPanel getFontMappingPanel() {
		if( fontMappingPanel == null ) {
			fontMappingPanel = new FontMappingPanel();
			fontMappingPanel.setBorder(new TitledBorder(UIManager.getBorder("TitledBorder.border"), Resources.getString("settings.tab.fontMapping.title"), TitledBorder.LEADING, TitledBorder.TOP, null, new Color(0, 0, 0)));
			fontMappingPanel.setOpaque(false);
		}
		return fontMappingPanel;
	}

	protected PageLayoutSettingsPanel getPageLayoutSettingsPanel() {
		if (pageLayoutSettingsPanel == null) {
			pageLayoutSettingsPanel = new PageLayoutSettingsPanel();
			pageLayoutSettingsPanel.setBorder(new TitledBorder(UIManager.getBorder("TitledBorder.border"), Resources.getString("settings.tab.margins.pageLayout"), TitledBorder.LEADING, TitledBorder.TOP, null, new Color(0, 0, 0)));
			pageLayoutSettingsPanel.setOpaque(false);
		}
		return pageLayoutSettingsPanel;
	}
	protected JButton getButtonOk() {
		if (buttonOk == null) {
			buttonOk = new JButton(""); //$NON-NLS-1$
			buttonOk.setPreferredSize(new Dimension(85, 27));
			buttonOk.setName("settingsDialog-ok");
			buttonOk.setAction(new SaveAction());
			buttonOk.setMinimumSize(new Dimension(85, 27));
		}
		return buttonOk;
	}
	protected JButton getButtonCancel() {
		if (buttonCancel == null) {
			buttonCancel = new JButton(""); //$NON-NLS-1$
			buttonCancel.setPreferredSize(new Dimension(85, 27));
			buttonCancel.setAction(new CancelAction());
			buttonCancel.setMinimumSize(new Dimension(85, 27));
			buttonCancel.setName("settingsDialog-cancel");
		}
		return buttonCancel;
	}
	protected GradientPanel getMainPanel() {
		if (mainPanel == null) {
			mainPanel = new GradientPanel();
			mainPanel.setDirection(GradientPanel.HORIZONTAL);
			mainPanel.setBackground(new Color(211, 211, 211));
			mainPanel.setForeground(new Color(248, 248, 255));
			((GradientPanel)mainPanel).setDirection(GradientPanel.VERTICAL);
			mainPanel.setLayout(new BorderLayout(0, 0));
			mainPanel.add(getButtonPanel(), BorderLayout.SOUTH);
			mainPanel.add(getTabbedPane(), BorderLayout.CENTER);
		}
		return mainPanel;
	}
	
	private class CancelAction extends AbstractAction {
		
		public CancelAction() {
			putValue(NAME, Resources.getString("button.cancel"));  //$NON-NLS-1$
		}
		
		public void actionPerformed(ActionEvent e) {
			setVisible(false);
		}
	}

	private class SaveAction extends AbstractAction {
		
		public SaveAction() {
			putValue(NAME, Resources.getString("button.ok"));  //$NON-NLS-1$
		}
		
		public void actionPerformed(ActionEvent e) {
			EventBus.publish(new StatusEvent(StatusType.ShowBusy, Resources.getString("message.savingSetting")));
			for(Component c: getTabbedPane().getComponents()) {
				if( c instanceof ISettingsPanel ) {
					ISettingsPanel panel = (ISettingsPanel)c;
					panel.saveSettings();
				}
			}
			EventBus.publish(new StatusEvent(StatusType.Finished,""));
			setVisible(false);
		}
	}
	
	
	
}
