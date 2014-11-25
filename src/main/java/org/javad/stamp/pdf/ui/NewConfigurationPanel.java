package org.javad.stamp.pdf.ui;

import javax.swing.DefaultComboBoxModel;
import javax.swing.JComboBox;
import javax.swing.JLabel;
import javax.swing.JPanel;
import javax.swing.JTextField;

import org.javad.pdf.model.PageConfiguration;
import org.javad.pdf.model.PageConfigurations;
import org.javad.stamp.pdf.Resources;

import com.jgoodies.forms.factories.FormFactory;
import com.jgoodies.forms.layout.ColumnSpec;
import com.jgoodies.forms.layout.FormLayout;
import com.jgoodies.forms.layout.RowSpec;

@SuppressWarnings("serial")
public class NewConfigurationPanel extends JPanel {
	private JLabel nameLabel;
	private JTextField nameText;
	private JLabel parentLabel;
	@SuppressWarnings("rawtypes")
	private JComboBox parentComboBox;
	
	public NewConfigurationPanel() {
		setLayout(new FormLayout(new ColumnSpec[] {
				FormFactory.UNRELATED_GAP_COLSPEC,
				FormFactory.DEFAULT_COLSPEC,
				FormFactory.RELATED_GAP_COLSPEC,
				ColumnSpec.decode("default:grow"),
				FormFactory.UNRELATED_GAP_COLSPEC,},
			new RowSpec[] {
				FormFactory.UNRELATED_GAP_ROWSPEC,
				FormFactory.DEFAULT_ROWSPEC,
				FormFactory.RELATED_GAP_ROWSPEC,
				FormFactory.DEFAULT_ROWSPEC,
				FormFactory.UNRELATED_GAP_ROWSPEC,}));
		add(getNameLabel(), "2, 2, right, default");
		add(getNameText(), "4, 2, fill, default");
		add(getParentLabel(), "2, 4, right, default");
		add(getParentComboBox(), "4, 4, fill, default");
		
	}

	@Override
	public void requestFocus() {
		getNameText().requestFocusInWindow();
	}
	
	protected JLabel getNameLabel() {
		if (nameLabel == null) {
			nameLabel = new JLabel(Resources.getString("label.name"));
		}
		return nameLabel;
	}
	protected JTextField getNameText() {
		if (nameText == null) {
			nameText = new JTextField();
			nameText.setColumns(10);
		}
		return nameText;
	}
	protected JLabel getParentLabel() {
		if (parentLabel == null) {
			parentLabel = new JLabel(Resources.getString("label.copyFrom"));
		}
		return parentLabel;
	}
	@SuppressWarnings({ "rawtypes", "unchecked" })
	protected JComboBox getParentComboBox() {
		if (parentComboBox == null) {
			parentComboBox = new JComboBox();
			parentComboBox.setRenderer(new ConfigurationRenderer());
		}
		return parentComboBox;
	}
	
	@SuppressWarnings({ "rawtypes", "unchecked" })
	protected void loadConfigurations() {
		PageConfigurations configs = PageConfigurations.getInstance();
		DefaultComboBoxModel model = new DefaultComboBoxModel(configs.getConfigurations().toArray());
		getParentComboBox().setModel(model);
		getParentComboBox().setSelectedItem(configs.getActiveConfiguration());
	}
	
	public PageConfiguration getConfiguration() {
		PageConfiguration config = (PageConfiguration) getParentComboBox().getSelectedItem();
		config = config.duplicate();
		config.setName(getNameText().getText());
		config.setDisplayName(config.getName());
		return config;
	}
}
