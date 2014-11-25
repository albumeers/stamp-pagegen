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
package org.javad.pdf.fonts.ui;

import java.awt.BorderLayout;
import java.awt.Color;
import java.awt.Component;
import java.awt.Dimension;
import java.awt.FlowLayout;
import java.awt.GraphicsEnvironment;
import java.awt.GridLayout;
import java.awt.event.ActionEvent;
import java.awt.event.ItemEvent;
import java.awt.event.ItemListener;
import java.io.IOException;
import java.text.DecimalFormat;
import java.util.Collection;
import java.util.logging.Level;
import java.util.logging.Logger;

import javax.imageio.ImageIO;
import javax.swing.AbstractAction;
import javax.swing.ButtonGroup;
import javax.swing.DefaultComboBoxModel;
import javax.swing.JButton;
import javax.swing.JCheckBox;
import javax.swing.JComboBox;
import javax.swing.JDialog;
import javax.swing.JFormattedTextField;
import javax.swing.JLabel;
import javax.swing.JList;
import javax.swing.JPanel;
import javax.swing.JRadioButton;
import javax.swing.ListCellRenderer;
import javax.swing.event.DocumentEvent;
import javax.swing.event.DocumentListener;

import org.bushe.swing.event.EventBus;
import org.javad.components.MessagePanel;
import org.javad.components.UIHelper;
import org.javad.pdf.fonts.PdfFontBean;
import org.javad.pdf.fonts.PdfFontMapping;
import org.javad.stamp.pdf.Resources;
import org.javad.stamp.pdf.events.PdfAppEvent;
import org.javad.stamp.pdf.events.PdfAppEvent.EventType;

import pub.domain.GradientPanel;

import com.itextpdf.text.Font;
import com.jgoodies.forms.factories.FormFactory;
import com.jgoodies.forms.layout.ColumnSpec;
import com.jgoodies.forms.layout.FormLayout;
import com.jgoodies.forms.layout.RowSpec;

@SuppressWarnings("serial")
public class PdfFontEditor extends JDialog {
	
	private JPanel contentPanel;
	private JPanel buttonPanel;
	private GradientPanel mainPanel;
	private JButton btnOk;
	private JButton btnCancel;
	private JLabel usageLabel;
	private JLabel usageValueLabel;
	private MessagePanel messagePanel;
	private JLabel aliasLabel;
	private JRadioButton systemRadio;
	@SuppressWarnings("rawtypes")
	private JComboBox systemComboBox;
	private JRadioButton userRadio;
	@SuppressWarnings("rawtypes")
	private JComboBox userComboBox;
	private JLabel sizeLabel;
	private JFormattedTextField sizeText;
	private JLabel sizeLabelHelp;
	private JPanel panel;
	private JCheckBox checkboxBold;
	private JCheckBox checkboxItalic;
	private JCheckBox checkboxUnderline;
	private JLabel styleLabel;
	private ButtonGroup buttonGroup;
	
	private PdfFontBean fontBean;
	
	private static final Logger logger = Logger.getLogger(PdfFontEditor.class.getName());
	
	public PdfFontEditor() {
		setSize(475,420);
		setModal(true);
		setTitle(Resources.getString("title.editFont"));
		try {
			setIconImage(ImageIO.read(getClass().getResource(Resources.getIconName("icon.systemFont.small")))); //$NON-NLS-1$
		} catch (IOException e) {
			logger.log(Level.SEVERE,"There was an error setting the icon for the editor", e); //$NON-NLS-1$
		}
		getContentPane().setLayout(new GridLayout(0, 1, 0, 0));
		getContentPane().add(getMainPanel());
	}

	protected JPanel getContentPanel() {
		if (contentPanel == null) {
			contentPanel = new JPanel();
			contentPanel.setOpaque(false);
			contentPanel.setLayout(new FormLayout(new ColumnSpec[] {
					FormFactory.UNRELATED_GAP_COLSPEC,
					FormFactory.DEFAULT_COLSPEC,
					FormFactory.RELATED_GAP_COLSPEC,
					ColumnSpec.decode("left:15dlu"),
					ColumnSpec.decode("35dlu"),
					FormFactory.RELATED_GAP_COLSPEC,
					ColumnSpec.decode("default:grow"),
					FormFactory.UNRELATED_GAP_COLSPEC,},
				new RowSpec[] {
					FormFactory.UNRELATED_GAP_ROWSPEC,
					FormFactory.DEFAULT_ROWSPEC,
					RowSpec.decode("8dlu"),
					FormFactory.DEFAULT_ROWSPEC,
					FormFactory.RELATED_GAP_ROWSPEC,
					FormFactory.DEFAULT_ROWSPEC,
					FormFactory.NARROW_LINE_GAP_ROWSPEC,
					FormFactory.DEFAULT_ROWSPEC,
					FormFactory.RELATED_GAP_ROWSPEC,
					FormFactory.DEFAULT_ROWSPEC,
					FormFactory.NARROW_LINE_GAP_ROWSPEC,
					FormFactory.DEFAULT_ROWSPEC,
					FormFactory.UNRELATED_GAP_ROWSPEC,
					FormFactory.DEFAULT_ROWSPEC,
					FormFactory.RELATED_GAP_ROWSPEC,
					RowSpec.decode("35dlu"),
					FormFactory.UNRELATED_GAP_ROWSPEC,}));
			contentPanel.add(getMessagePanel(), "2, 2, 6, 1, fill, top");
			contentPanel.add(getUsageLabel(), "2, 4, right, default");
			contentPanel.add(getUsageValueLabel(), "4, 4, 5, 1");
			contentPanel.add(getAliasLabel(), "2, 6, right, default");
			contentPanel.add(getSystemRadio(), "4, 6, 4, 1");
			contentPanel.add(getSystemComboBox(), "5, 8, 3, 1, left, default");
			contentPanel.add(getUserRadio(), "4, 10, 4, 1");
			contentPanel.add(getUserComboBox(), "5, 12, 3, 1, left, default");
			contentPanel.add(getSizeLabel(), "2, 14, right, default");
			contentPanel.add(getSizeText(), "4, 14, 2, 1, left, default");
			contentPanel.add(getSizeLabelHelp(), "7, 14, left, default");
			contentPanel.add(getStyleLabel(), "2, 16, right, center");
			contentPanel.add(getPanel(), "4, 16, 4, 1, fill, center");
			
			getButtonGroup();
			
		}
		return contentPanel;
	}
	
	protected ButtonGroup getButtonGroup() {
		if( buttonGroup == null ) {
			buttonGroup = new ButtonGroup();
			buttonGroup.add(getSystemRadio());
			buttonGroup.add(getUserRadio());
		}
		return buttonGroup;
	}
	
	@SuppressWarnings({ "rawtypes", "unchecked" })
	public void initialize(PdfFontBean bean, Collection<PdfFontMapping> mappings) {
		if( bean == null ) {
			throw new IllegalArgumentException("The font bean can not be null.");
		}
		DefaultComboBoxModel cBox = new DefaultComboBoxModel();
		for(PdfFontMapping map: mappings ) {
			cBox.addElement(map);
		}
		getUserComboBox().setModel(cBox);
		getUsageValueLabel().setText(bean.getFontDefinition().toString());
		if( bean.isSystem()) {
			getSystemRadio().setSelected(true);
			getSystemComboBox().setSelectedItem(bean.getFontFamily());
		} else {
			getUserRadio().setSelected(true);
			getUserComboBox().setSelectedItem(bean.getFontMapping());
		}
		DecimalFormat df = new DecimalFormat("0.0#");
		getSizeText().setText(df.format(bean.getSize()));
		getCheckboxBold().setSelected(bean.isBold());
		getCheckboxItalic().setSelected(bean.isItalic());
		getCheckboxUnderline().setSelected(bean.isUnderline());
		
		this.fontBean = bean;
	}
	
	@SuppressWarnings("rawtypes")
	private class FontMappingRenderer extends JLabel implements ListCellRenderer {

		@Override
		public Component getListCellRendererComponent(JList list, Object value,	int index, boolean isSelected, boolean cellHasFocus) {
			if( value instanceof PdfFontMapping) {
				PdfFontMapping mapping = (PdfFontMapping)value;
				JLabel label = new JLabel(mapping.getFontAlias());
				return label;
			}
			return null;
		}
	}

	protected boolean isFormValid() {
		boolean valid = true;
		if( getSizeText().getText() == null || getSizeText().getText().isEmpty()) {
			valid = false;
		}
		if( getUserRadio().isSelected() && getUserComboBox().getSelectedItem() == null) {
			valid = false;
		}
		if( getSystemRadio().isSelected() && getSystemComboBox().getSelectedItem() == null ) {
			valid = false;
		}
		return valid;
	}
	
	protected class ValidatingDocumentListener implements DocumentListener {

		@Override
		public void insertUpdate(DocumentEvent e) {
			getBtnOk().getAction().setEnabled(isFormValid());
		}

		@Override
		public void removeUpdate(DocumentEvent e) {
			getBtnOk().getAction().setEnabled(isFormValid());
		}

		@Override
		public void changedUpdate(DocumentEvent e) {
			getBtnOk().getAction().setEnabled(isFormValid());
		}
		
	}
	
	
	protected JPanel getButtonPanel() {
		if (buttonPanel == null) {
			buttonPanel = new JPanel();
			FlowLayout flowLayout = (FlowLayout) buttonPanel.getLayout();
			flowLayout.setVgap(10);
			flowLayout.setAlignment(FlowLayout.RIGHT);
			buttonPanel.setOpaque(false);
			buttonPanel.setPreferredSize(new Dimension(100, 50));
			buttonPanel.add(getBtnOk());
			buttonPanel.add(getBtnCancel());
		}
		return buttonPanel;
	}
	protected GradientPanel getMainPanel() {
		if (mainPanel == null) {
			mainPanel = new GradientPanel();
			mainPanel.setDirection(GradientPanel.HORIZONTAL);
			mainPanel.setBackground(new Color(248, 248, 255));
			mainPanel.setForeground(Color.LIGHT_GRAY);
			mainPanel.setLayout(new BorderLayout(0, 0));
			mainPanel.add(getContentPanel(), BorderLayout.CENTER);
			mainPanel.add(getButtonPanel(), BorderLayout.SOUTH);
		}
		return mainPanel;
	}
	protected JButton getBtnOk() {
		if (btnOk == null) {
			btnOk = new JButton();
			btnOk.setPreferredSize(new Dimension(75, 28));
			btnOk.setAction(new SaveFontAction());
			btnOk.setName("btn-font-ok");
		}
		return btnOk;
	}
	protected JButton getBtnCancel() {
		if (btnCancel == null) {
			btnCancel = new JButton();
			btnCancel.setPreferredSize(new Dimension(75, 28));
			btnCancel.setAction(new CancelFontAction());
			btnCancel.setName("btn-font-cancel");
		}
		return btnCancel;
	}
	protected JLabel getUsageLabel() {
		if (usageLabel == null) {
			usageLabel = new JLabel(Resources.getString("label.fontUsage"));
		}
		return usageLabel;
	}
	protected JLabel getUsageValueLabel() {
		if (usageValueLabel == null) {
			usageValueLabel = new JLabel("");
			usageValueLabel.setName("label-usageValue");
		}
		return usageValueLabel;
	}
	protected MessagePanel getMessagePanel() {
		if (messagePanel == null) {
			messagePanel = new MessagePanel(UIHelper.convertToMultiline(Resources.getString("message.fontEditor.helpText")));
		}
		return messagePanel;
	}
	protected JLabel getAliasLabel() {
		if (aliasLabel == null) {
			aliasLabel = new JLabel(Resources.getString("label.fontAlias"));
		}
		return aliasLabel;
	}
	protected JRadioButton getSystemRadio() {
		if (systemRadio == null) {
			systemRadio = new JRadioButton(Resources.getString("label.fontSystem"));
			systemRadio.setOpaque(false);
			systemRadio.setSelected(true);
			systemRadio.addItemListener(new ItemListener() {

				@Override
				public void itemStateChanged(ItemEvent e) {
					getSystemComboBox().setEnabled( e.getStateChange() == ItemEvent.SELECTED);
				}
				
			});
		}
		return systemRadio;
	}
	@SuppressWarnings({ "rawtypes", "unchecked" })
	protected JComboBox getSystemComboBox() {
		if (systemComboBox == null) {
			GraphicsEnvironment gEnv = GraphicsEnvironment.getLocalGraphicsEnvironment();         
			systemComboBox = new JComboBox(gEnv.getAvailableFontFamilyNames()); 
			systemComboBox.setPreferredSize(new Dimension(250, 24));
			systemComboBox.addItemListener(new ItemListener() {
				@Override
				public void itemStateChanged(ItemEvent e) {
					getBtnOk().getAction().setEnabled(isFormValid());
				}
			});
		}
		return systemComboBox;
	}
	
	protected JRadioButton getUserRadio() {
		if (userRadio == null) {
			userRadio = new JRadioButton(Resources.getString("label.fontDefined"));
			userRadio.setOpaque(false);
			userRadio.addItemListener(new ItemListener() {

				@Override
				public void itemStateChanged(ItemEvent e) {
					getUserComboBox().setEnabled( e.getStateChange() == ItemEvent.SELECTED);
				}
				
			});
		}
		return userRadio;
	}
	@SuppressWarnings({ "rawtypes", "unchecked" })
	protected JComboBox getUserComboBox() {
		if (userComboBox == null) {
			userComboBox = new JComboBox();
			userComboBox.setPreferredSize(new Dimension(250, 24));
			userComboBox.setRenderer(new FontMappingRenderer());
			userComboBox.setEnabled(false);
			userComboBox.addItemListener(new ItemListener() {
				@Override
				public void itemStateChanged(ItemEvent e) {
					getBtnOk().getAction().setEnabled(isFormValid());
				}
			});
		}
		return userComboBox;
	}
	protected JLabel getSizeLabel() {
		if (sizeLabel == null) {
			sizeLabel = new JLabel(Resources.getString("label.size"));
		}
		return sizeLabel;
	}
	protected JFormattedTextField getSizeText() {
		if (sizeText == null) {
			DecimalFormat format = new DecimalFormat("0.0##");
			sizeText = new JFormattedTextField(format);
			sizeText.setPreferredSize(new Dimension(35, 22));
			sizeText.setColumns(8);
			sizeText.getDocument().addDocumentListener(new ValidatingDocumentListener());
		}
		return sizeText;
	}
	protected JLabel getSizeLabelHelp() {
		if (sizeLabelHelp == null) {
			sizeLabelHelp = new JLabel(Resources.getString("label.size.unit"));
		}
		return sizeLabelHelp;
	}
	protected JPanel getPanel() {
		if (panel == null) {
			panel = new JPanel();
			FlowLayout flowLayout = (FlowLayout) panel.getLayout();
			flowLayout.setAlignment(FlowLayout.LEFT);
			panel.setOpaque(false);
			panel.setPreferredSize(new Dimension(100, 35));
			panel.add(getCheckboxBold());
			panel.add(getCheckboxItalic());
			panel.add(getCheckboxUnderline());
		}
		return panel;
	}
	protected JCheckBox getCheckboxBold() {
		if (checkboxBold == null) {
			checkboxBold = new JCheckBox(Resources.getString("label.font.bold"));
			checkboxBold.setName("checkbox-bold");
			checkboxBold.setOpaque(false);
		}
		return checkboxBold;
	}
	protected JCheckBox getCheckboxItalic() {
		if (checkboxItalic == null) {
			checkboxItalic = new JCheckBox(Resources.getString("label.font.italic"));
			checkboxItalic.setName("checkbox-italic");
			checkboxItalic.setOpaque(false);
		}
		return checkboxItalic;
	}
	protected JCheckBox getCheckboxUnderline() {
		if (checkboxUnderline == null) {
			checkboxUnderline = new JCheckBox(Resources.getString("label.font.underline"));
			checkboxUnderline.setEnabled(false);
			checkboxUnderline.setName("checkbox-underline");
			checkboxUnderline.setOpaque(false);
		}
		return checkboxUnderline;
	}
	protected JLabel getStyleLabel() {
		if (styleLabel == null) {
			styleLabel = new JLabel(Resources.getString("label.style"));
		}
		return styleLabel;
	}
	
	
	private class CancelFontAction extends AbstractAction {
		public CancelFontAction() {
			putValue(NAME,Resources.getString("button.cancel")); //$NON-NLS-1$
		}
		
		@Override
		public void actionPerformed(ActionEvent e) {
			setVisible(false);
		}
	}
	
	private class SaveFontAction extends AbstractAction {
		public SaveFontAction() {
			putValue(NAME,Resources.getString("button.ok")); //$NON-NLS-1$
			setEnabled(false);
		}
		
		@Override
		public void actionPerformed(ActionEvent e) {
			if( isFormValid() ) {
				fontBean.setSize(Float.valueOf(getSizeText().getText()).floatValue());
				int style = Font.NORMAL;
				if( getCheckboxBold().isSelected()) {
					style = style | Font.BOLD;
				}
				if( getCheckboxItalic().isSelected()) {
					style = style | Font.ITALIC;
				}
				if ( getCheckboxUnderline().isSelected()) {
					style = style | Font.UNDERLINE;
				}
				fontBean.setStyle(style);
				fontBean.setSystem(getSystemRadio().isSelected());
				if( fontBean.isSystem()) {
					fontBean.setFontFamily(getSystemComboBox().getSelectedItem().toString());
				} else {
					fontBean.setFontMapping((PdfFontMapping) getUserComboBox().getSelectedItem());
				}
			}
			EventBus.publish(new PdfAppEvent(EventType.FontBeanEdit, fontBean));
			setVisible(false);
		}
		
	}
}
