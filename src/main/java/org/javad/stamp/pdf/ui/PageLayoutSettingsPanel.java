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

import java.awt.event.ActionEvent;
import java.text.NumberFormat;

import javax.swing.AbstractAction;
import javax.swing.JButton;
import javax.swing.JFormattedTextField;
import javax.swing.JLabel;
import javax.swing.JPanel;

import org.javad.pdf.model.PageConfiguration;
import org.javad.pdf.model.PageConfigurations;
import org.javad.stamp.pdf.Resources;

import com.jgoodies.forms.factories.FormFactory;
import com.jgoodies.forms.layout.ColumnSpec;
import com.jgoodies.forms.layout.FormLayout;
import com.jgoodies.forms.layout.RowSpec;
import org.javad.components.MessagePanel;
import org.javad.components.UIHelper;

@SuppressWarnings("serial")
public class PageLayoutSettingsPanel extends JPanel implements IPageConfigurationSettingsPanel {
	
	private JFormattedTextField widthText;
	private JFormattedTextField heightText;
	private JFormattedTextField leftMarginText;
	private JFormattedTextField topMarginText;
	private JFormattedTextField rightMarginText;
	private JFormattedTextField bottomMarginText;
	private JFormattedTextField horizontalGapText;
	private JFormattedTextField verticalGapText;
	private JButton btnRevertDefault;
	private JLabel labelConfigurationValue;
	private PageConfiguration configuration;
	
	public PageLayoutSettingsPanel() {
		
		
		
		setLayout(new FormLayout(new ColumnSpec[] {
				FormFactory.UNRELATED_GAP_COLSPEC,
				ColumnSpec.decode("default:grow"),
				FormFactory.LABEL_COMPONENT_GAP_COLSPEC,
				FormFactory.DEFAULT_COLSPEC,
				FormFactory.RELATED_GAP_COLSPEC,
				FormFactory.BUTTON_COLSPEC,
				FormFactory.UNRELATED_GAP_COLSPEC,
				FormFactory.DEFAULT_COLSPEC,
				FormFactory.LABEL_COMPONENT_GAP_COLSPEC,
				FormFactory.DEFAULT_COLSPEC,
				FormFactory.RELATED_GAP_COLSPEC,
				FormFactory.DEFAULT_COLSPEC,
				FormFactory.UNRELATED_GAP_COLSPEC,},
			new RowSpec[] {
				FormFactory.UNRELATED_GAP_ROWSPEC,
				RowSpec.decode("default:grow"),
				FormFactory.UNRELATED_GAP_ROWSPEC,
				FormFactory.DEFAULT_ROWSPEC,
				FormFactory.RELATED_GAP_ROWSPEC,
				FormFactory.DEFAULT_ROWSPEC,
				FormFactory.RELATED_GAP_ROWSPEC,
				FormFactory.DEFAULT_ROWSPEC,
				RowSpec.decode("12dlu"),
				FormFactory.DEFAULT_ROWSPEC,
				FormFactory.RELATED_GAP_ROWSPEC,
				FormFactory.DEFAULT_ROWSPEC,
				FormFactory.RELATED_GAP_ROWSPEC,
				FormFactory.DEFAULT_ROWSPEC,
				FormFactory.RELATED_GAP_ROWSPEC,
				FormFactory.DEFAULT_ROWSPEC,
				RowSpec.decode("12dlu"),
				FormFactory.DEFAULT_ROWSPEC,
				FormFactory.UNRELATED_GAP_ROWSPEC,}));
		
		MessagePanel messagePanel = new MessagePanel(UIHelper.convertToMultiline(Resources.getString("message.pageLayout.helpText")));
		add(messagePanel, "2, 2, 11, 1, fill, fill");
		
		JLabel labelConfiguration = new JLabel(Resources.getString("label.configuration")); //$NON-NLS-1$
		add(labelConfiguration, "2, 4, right, default");
		
		
		add(getLabelConfigurationValue(), "4, 4, 9, 1");
		
		JLabel labelPageWidth = new JLabel("Paper Width:");
		add(labelPageWidth, "2, 6, right, center");
		add(getWidthText(), "4, 6, left, top");
		
		JLabel labelWidthDimension = new JLabel("(mm)");
		add(labelWidthDimension, "6, 6");
		
		JLabel labelHorizontalGap = new JLabel("Horizontal Box Spacing:");
		add(labelHorizontalGap, "8, 6, right, default");
		
		add(getHorizontalGapText(), "10, 6, left, default");
		
		JLabel labelHorizontalGapDimension = new JLabel("(mm)");
		add(labelHorizontalGapDimension, "12, 6");
		
		JLabel labelPageHeight = new JLabel("Paper Height:");
		add(labelPageHeight, "2, 8, right, center");
		add(getHeightText(), "4, 8, left, top");
		
		JLabel labelHeightDimension = new JLabel("(mm)");
		add(labelHeightDimension, "6, 8");
		
		JLabel labelVerticalGap = new JLabel("Vertical Row Spacing:");
		add(labelVerticalGap, "8, 8, right, default");
		
		add(getVerticalGapText(), "10, 8, left, default");
		
		JLabel labelVerticalGapDimension = new JLabel("(mm)");
		add(labelVerticalGapDimension, "12, 8");
		
		JLabel labelLeftMargin = new JLabel("Left Margin:");
		add(labelLeftMargin, "2, 10, right, default");
		add(getLeftMarginText(), "4, 10, left, default");
		
		JLabel labelLeftMarginDimension = new JLabel("(mm)");
		add(labelLeftMarginDimension, "6, 10");
		
		JLabel labelTopMargin = new JLabel("Top Margin:");
		add(labelTopMargin, "2, 12, right, default");
		add(getTopMarginText(), "4, 12, left, default");
		
		JLabel labelTopMarginDimension = new JLabel("(mm)");
		add(labelTopMarginDimension, "6, 12");
		
		JLabel labelRightMargin = new JLabel("Right Margin:");
		add(labelRightMargin, "2, 14, right, default");
		add(getRightMarginText(), "4, 14, left, default");
		
		JLabel labelRightMarginDimension = new JLabel("(mm)");
		add(labelRightMarginDimension, "6, 14");
		
		JLabel labelBottomMargin = new JLabel("Bottom Margin:");
		add(labelBottomMargin, "2, 16, right, default");
		add(getBottomMarginText(), "4, 16, left, default");
		
		JLabel labelBottomMarginDimension = new JLabel("(mm)");
		add(labelBottomMarginDimension, "6, 16");
		
		add(getRevertDefault(), "8, 18, left, default");
	}
	
	
	protected JLabel getLabelConfigurationValue() {
		if( labelConfigurationValue == null ) {
			labelConfigurationValue = new JLabel(""); //$NON-NLS-1$
			labelConfigurationValue.setName("label.configurationValue"); //$NON-NLS-1$
		}
		return labelConfigurationValue;
	}
	
	protected JButton getRevertDefault() {
		if( btnRevertDefault == null ) {
			btnRevertDefault = new JButton(Resources.getString("button.revert")); //$NON-NLS-1$
			btnRevertDefault.setName("btnRevertDefault");
			btnRevertDefault.setAction(new RevertAction());
		}
		return btnRevertDefault;
	}
	
	@Override
	public void setConfiguration(PageConfiguration configuration) {
		this.configuration = configuration;
	}
	
	private class RevertAction extends AbstractAction {

		public RevertAction() {
			putValue( NAME, Resources.getString("button.revert")); //$NON-NLS-1$
			setEnabled(false);
		}
		
		@Override
		public void actionPerformed(ActionEvent e) {
			if( configuration != null && configuration.isSystemConfiguration() ) {
				PageConfigurations.getInstance().revert(configuration);
				configureForPageConfiguration(configuration);
			}
		}
		
	}
	
	protected JFormattedTextField getHorizontalGapText() {
		if( horizontalGapText == null ) {
			horizontalGapText = new JFormattedTextField(NumberFormat.getInstance());
			horizontalGapText.setColumns(6);
		}
		return horizontalGapText;
	}
	
	protected JFormattedTextField getVerticalGapText() {
		if( verticalGapText == null ) {
			verticalGapText = new JFormattedTextField(NumberFormat.getInstance());
			verticalGapText.setColumns(6);
		}
		return verticalGapText;
	}
	
	protected JFormattedTextField getBottomMarginText() {
		if( bottomMarginText == null ) {
			bottomMarginText = new JFormattedTextField(NumberFormat.getInstance());
			bottomMarginText.setColumns(6);
		}
		return bottomMarginText;
	}
	
	protected JFormattedTextField getRightMarginText() {
		if( rightMarginText == null ) {
			rightMarginText = new JFormattedTextField(NumberFormat.getInstance());
			rightMarginText.setColumns(6);
		}
		return rightMarginText;
	}

	protected JFormattedTextField getTopMarginText() {
		if( topMarginText == null ) {
			topMarginText = new JFormattedTextField(NumberFormat.getInstance());
			topMarginText.setColumns(6);
		}
		return topMarginText;
	}

	private JFormattedTextField getLeftMarginText() {
		if( leftMarginText == null ) {
			leftMarginText = new JFormattedTextField(NumberFormat.getInstance());
			leftMarginText.setColumns(6);
		}
		return leftMarginText;
	}

	protected JFormattedTextField getHeightText() {
		if( heightText == null ) {
			heightText = new JFormattedTextField(NumberFormat.getInstance());
			heightText.setColumns(6);
		} 
		return heightText;
	}

	protected JFormattedTextField getWidthText() {
		if( widthText == null ) {
			widthText = new JFormattedTextField(NumberFormat.getInstance());
			widthText.setColumns(6);
		}
		return widthText;
	}

	
	public void configureForPageConfiguration(PageConfiguration config) {
		getLabelConfigurationValue().setText((config != null ) ? config.getDisplayName() : "unknown" );
		getWidthText().setValue(( config != null ) ? config.getWidth(): null);
		getHeightText().setValue((config != null ) ? config.getHeight(): null);
		getLeftMarginText().setValue((config != null) ? config.getMarginLeft(): null);
		getTopMarginText().setValue((config != null) ? config.getMarginTop(): null);
		getRightMarginText().setValue((config != null) ? config.getMarginRight(): null);
		getBottomMarginText().setValue((config != null) ? config.getMarginBottom(): null);
		getVerticalGapText().setValue((config != null) ? config.getVerticalSpacing(): null);
		getHorizontalGapText().setValue((config != null) ? config.getHorizontalSpacing(): null);
		getRevertDefault().getAction().setEnabled(config.isSystemConfiguration());
	}
	
	@Override
	public void loadSettings() {
		if( configuration != null ) {
			configureForPageConfiguration(configuration);
		}
	}

	@Override
	public void saveSettings() {
		if( configuration != null ) {
			configuration.setWidth(((Number)getWidthText().getValue()).floatValue());
			configuration.setHeight(((Number)getHeightText().getValue()).floatValue());
			configuration.setMarginLeft(((Number)getLeftMarginText().getValue()).floatValue());
			configuration.setMarginRight(((Number)getRightMarginText().getValue()).floatValue());
			configuration.setMarginTop(((Number)getTopMarginText().getValue()).floatValue());
			configuration.setMarginBottom(((Number)getBottomMarginText().getValue()).floatValue());
			configuration.setHorizontalSpacing(((Number)getHorizontalGapText().getValue()).floatValue());
			configuration.setVerticalSpacing(((Number)getVerticalGapText().getValue()).floatValue());
			PageConfigurations.getInstance().save(configuration);
		}
	}
}
