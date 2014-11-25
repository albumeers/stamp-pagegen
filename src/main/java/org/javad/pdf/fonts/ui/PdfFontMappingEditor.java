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
import java.awt.Dimension;
import java.awt.FlowLayout;
import java.awt.GridLayout;
import java.awt.event.ActionEvent;
import java.io.File;
import java.io.IOException;
import java.util.logging.Level;
import java.util.logging.Logger;

import javax.imageio.ImageIO;
import javax.swing.AbstractAction;
import javax.swing.JButton;
import javax.swing.JDialog;
import javax.swing.JFileChooser;
import javax.swing.JLabel;
import javax.swing.JPanel;
import javax.swing.JTextField;
import javax.swing.event.DocumentEvent;
import javax.swing.event.DocumentListener;

import org.bushe.swing.event.EventBus;
import org.javad.components.MessagePanel;
import org.javad.components.UIHelper;
import org.javad.pdf.fonts.PdfFontMapping;
import org.javad.pdf.fonts.io.PdfFontFileFilter;
import org.javad.stamp.pdf.Resources;
import org.javad.stamp.pdf.events.PdfAppEvent;
import org.javad.stamp.pdf.events.PdfAppEvent.EventType;

import pub.domain.GradientPanel;

import com.jgoodies.forms.factories.FormFactory;
import com.jgoodies.forms.layout.ColumnSpec;
import com.jgoodies.forms.layout.FormLayout;
import com.jgoodies.forms.layout.RowSpec;

@SuppressWarnings("serial")
public class PdfFontMappingEditor extends JDialog {
	
	private JPanel contentPanel;
	private JPanel buttonPanel;
	private JButton btnOk;
	private JButton btnCancel;
	private JLabel aliasLabel;
	private JTextField aliasText;
	private JLabel fontLabel;
	private JTextField fontText;
	private JButton btnFontPicker;
	private MessagePanel messagePanel;
	private GradientPanel dialogPanel;
	
	private PdfFontMapping model;
	
	private boolean edit = false;
	
	private static final Logger logger = Logger.getLogger(PdfFontMappingEditor.class.getName());
	
	public PdfFontMappingEditor() {
		super();
		try {
			setIconImage(ImageIO.read(getClass().getResource(Resources.getIconName("icon.font.small")))); //$NON-NLS-1$
		} catch (IOException e) {
			logger.log(Level.SEVERE,"There was an error setting the icon for the editor", e); //$NON-NLS-1$
		}
		setSize(new Dimension(450, 270));
		setModal(true);
		setBackground(UIHelper.Medium_Grey);
		setForeground(UIHelper.Dark_Grey);
		setTitle(Resources.getString("title.fontReference")); //$NON-NLS-1$
		dialogPanel = new GradientPanel();
		dialogPanel.setDirection(GradientPanel.HORIZONTAL);
		dialogPanel.setBackground(new Color(248, 248, 255));
		dialogPanel.setForeground(Color.LIGHT_GRAY);
		dialogPanel.setLayout(new BorderLayout(0,0));
		dialogPanel.add(getContentPanel(), BorderLayout.CENTER);
		dialogPanel.add(getButtonPanel(), BorderLayout.SOUTH);
		getContentPane().setLayout(new GridLayout(1, 1));
		getContentPane().add(dialogPanel);
		
	}
	
	public void setReferenceModel(PdfFontMapping reference) {
		if( reference == null ) {
			reference = new PdfFontMapping();
			edit = false;
		} else {
			edit = true;
		}
		model = reference;
		getAliasText().setText((edit) ? reference.getFontAlias() : "");
		getFontText().setText((edit) ? reference.getFilePath() : "");
		
		validateReference();
	}
	
	public PdfFontMapping getReferenceModel() {
		return model;
	}

	protected JPanel getContentPanel() {
		if (contentPanel == null) {
			contentPanel = new JPanel();
			contentPanel.setOpaque(false);
			contentPanel.setLayout(new FormLayout(new ColumnSpec[] {
					FormFactory.UNRELATED_GAP_COLSPEC,
					FormFactory.DEFAULT_COLSPEC,
					FormFactory.RELATED_GAP_COLSPEC,
					ColumnSpec.decode("default:grow"),
					FormFactory.RELATED_GAP_COLSPEC,
					ColumnSpec.decode("32dlu"),
					FormFactory.UNRELATED_GAP_COLSPEC,},
				new RowSpec[] {
					FormFactory.UNRELATED_GAP_ROWSPEC,
					FormFactory.PREF_ROWSPEC,
					FormFactory.RELATED_GAP_ROWSPEC,
					RowSpec.decode("24dlu"),
					RowSpec.decode("1dlu"),
					RowSpec.decode("24dlu"),
					FormFactory.UNRELATED_GAP_ROWSPEC,}));
			contentPanel.add(getMessagePanel(), "2, 2, 5, 1, fill, fill"); //$NON-NLS-1$
			contentPanel.add(getAliasLabel(), "2, 4, right, default"); //$NON-NLS-1$
			contentPanel.add(getAliasText(), "4, 4, left, default"); //$NON-NLS-1$
			contentPanel.add(getFontLabel(), "2, 6, right, default"); //$NON-NLS-1$
			contentPanel.add(getFontText(), "4, 6, fill, default"); //$NON-NLS-1$
			contentPanel.add(getBtnFontPicker(), "6, 6"); //$NON-NLS-1$
		}
		return contentPanel;
	}
	protected JPanel getButtonPanel() {
		if (buttonPanel == null) {
			buttonPanel = new JPanel();
			buttonPanel.setRequestFocusEnabled(false);
			buttonPanel.setOpaque(false);
			FlowLayout fl_buttonPanel = (FlowLayout) buttonPanel.getLayout();
			fl_buttonPanel.setVgap(15);
			fl_buttonPanel.setAlignment(FlowLayout.RIGHT);
			buttonPanel.setPreferredSize(new Dimension(100, 50));
			buttonPanel.add(getBtnOk());
			buttonPanel.add(getBtnCancel());
		}
		return buttonPanel;
	}
	protected JButton getBtnOk() {
		if (btnOk == null) {
			btnOk = new JButton(Resources.getString("button.ok")); //$NON-NLS-1$
			btnOk.setPreferredSize(new Dimension(75, 24));
			btnOk.setName("btn-fontReferenceEditor-ok"); //$NON-NLS-1$
			btnOk.setAction(new SaveReferenceAction());
		}
		return btnOk;
	}
	protected JButton getBtnCancel() {
		if (btnCancel == null) {
			btnCancel = new JButton(Resources.getString("button.cancel")); //$NON-NLS-1$
			btnCancel.setPreferredSize(new Dimension(75, 24));
			btnCancel.setName("btn-fontReferenceEditor-cancel"); //$NON-NLS-1$
			btnCancel.setAction(new CancelReferenceAction());
		}
		return btnCancel;
	}
	protected JLabel getAliasLabel() {
		if (aliasLabel == null) {
			aliasLabel = new JLabel(Resources.getString("label.fontAlias")); //$NON-NLS-1$
		}
		return aliasLabel;
	}
	protected JTextField getAliasText() {
		if (aliasText == null) {
			aliasText = new JTextField();
			aliasText.setMinimumSize(new Dimension(150, 24));
			aliasText.setPreferredSize(new Dimension(250, 24));
			aliasText.setText(""); //$NON-NLS-1$
			aliasText.setColumns(20);
			aliasText.getDocument().addDocumentListener(new ValidatingDocumentListener());
		}
		return aliasText;
	}
	protected JLabel getFontLabel() {
		if (fontLabel == null) {
			fontLabel = new JLabel(Resources.getString("label.fontPath")); //$NON-NLS-1$
		}
		return fontLabel;
	}
	protected JTextField getFontText() {
		if (fontText == null) {
			fontText = new JTextField();
			fontText.setBackground(new Color(240, 240, 240));
			fontText.setEditable(false);
			fontText.setPreferredSize(new Dimension(100, 24));
			fontText.setText(""); //$NON-NLS-1$
			fontText.setColumns(10);
			fontText.getDocument().addDocumentListener(new ValidatingDocumentListener());
		}
		return fontText;
	}
	
	protected class ValidatingDocumentListener implements DocumentListener {

		private void updateField(DocumentEvent e) {
			if( getAliasText().getDocument().equals(e.getDocument())) {
				getReferenceModel().setFontAlias(getAliasText().getText());
			} else if ( getFontText().getDocument().equals(e.getDocument())) {
				getReferenceModel().setFilePath(getFontText().getText());
			}
		}
		
		@Override
		public void insertUpdate(DocumentEvent e) {
			updateField(e);
			getBtnOk().getAction().setEnabled(validateReference());
		}

		@Override
		public void removeUpdate(DocumentEvent e) {
			updateField(e);
			getBtnOk().getAction().setEnabled(validateReference());
		}

		@Override
		public void changedUpdate(DocumentEvent e) {
			updateField(e);
			getBtnOk().getAction().setEnabled(validateReference());
		}
		
	}
	
	public boolean validateReference() {
		return !getFontText().getText().isEmpty() && !getAliasText().getText().isEmpty();
	}
	
	protected JButton getBtnFontPicker() {
		if (btnFontPicker == null) {
			btnFontPicker = new JButton();
			btnFontPicker.setPreferredSize(new Dimension(32, 26));
			btnFontPicker.setName("btn-fontReference-fontPicker"); //$NON-NLS-1$
			btnFontPicker.setAction(new FontPickerAction());
		}
		return btnFontPicker;
	}
	
	private class CancelReferenceAction extends AbstractAction {
		public CancelReferenceAction() {
			putValue(NAME,Resources.getString("button.cancel")); //$NON-NLS-1$
		}
		
		@Override
		public void actionPerformed(ActionEvent e) {
			setVisible(false);
		}
	}
	
	private class SaveReferenceAction extends AbstractAction {
		public SaveReferenceAction() {
			putValue(NAME,Resources.getString("button.ok")); //$NON-NLS-1$
			setEnabled(false);
		}
		
		@Override
		public void actionPerformed(ActionEvent e) {
			logger.finer("Saving reference: " + getReferenceModel().toString());
			EventBus.publish(new PdfAppEvent((edit) ? EventType.FontReferenceEdit : EventType.FontReferenceSave, getReferenceModel()));
			setVisible(false);
		}
		
	}
	
	private class FontPickerAction extends AbstractAction {
		public FontPickerAction() {
			putValue(LARGE_ICON_KEY, Resources.getIcon("icon.font.picker")); //$NON-NLS-1$
			putValue(SHORT_DESCRIPTION, Resources.getString("label.font.picker")); //$NON-NLS-1$
		}
		public void actionPerformed(ActionEvent e) {
			JFileChooser chooser = PdfFontFileFilter.getFileChooser();
			if( JFileChooser.APPROVE_OPTION == chooser.showOpenDialog(getBtnFontPicker()) ) {
				File f = chooser.getSelectedFile();
				if( f != null ) {
					getFontText().setText(f.getAbsolutePath());
				}
			}
		}
	}
	
	protected MessagePanel getMessagePanel() {
		if (messagePanel == null) {
			messagePanel = new MessagePanel(UIHelper.convertToMultiline(Resources.getString("message.fontReference.helpText"))); //$NON-NLS-1$
		}
		return messagePanel;
	}
}