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

import java.awt.Component;
import java.awt.Dimension;
import java.awt.FlowLayout;
import java.awt.GraphicsEnvironment;
import java.awt.event.ActionEvent;
import java.awt.event.MouseAdapter;
import java.awt.event.MouseEvent;
import java.text.MessageFormat;
import java.util.ArrayList;
import java.util.Collection;
import java.util.List;
import java.util.logging.Logger;

import javax.swing.AbstractAction;
import javax.swing.JButton;
import javax.swing.JLabel;
import javax.swing.JPanel;
import javax.swing.JScrollPane;
import javax.swing.JTable;
import javax.swing.event.ListSelectionEvent;
import javax.swing.event.ListSelectionListener;
import javax.swing.table.AbstractTableModel;
import javax.swing.table.DefaultTableCellRenderer;
import javax.swing.table.DefaultTableColumnModel;
import javax.swing.table.TableColumn;
import javax.swing.table.TableColumnModel;

import org.bushe.swing.event.annotation.AnnotationProcessor;
import org.bushe.swing.event.annotation.EventSubscriber;
import org.javad.components.ISettingsPanel;
import org.javad.components.MessagePanel;
import org.javad.components.UIHelper;
import org.javad.pdf.fonts.FontRegistry;
import org.javad.pdf.fonts.PdfFontMapping;
import org.javad.stamp.pdf.Resources;
import org.javad.stamp.pdf.events.PdfAppEvent;
import org.javad.stamp.pdf.events.PdfAppEvent.EventType;

import com.jgoodies.forms.factories.FormFactory;
import com.jgoodies.forms.layout.ColumnSpec;
import com.jgoodies.forms.layout.FormLayout;
import com.jgoodies.forms.layout.RowSpec;

@SuppressWarnings("serial")
public class FontMappingPanel extends JPanel implements ISettingsPanel {
		
	private JPanel panel;
	private JButton btnNewRefButton;
	private JScrollPane fontTableScrollPane;
	private JTable fontTable;
	private MessagePanel messagePanel;
	private JButton btnEditRefButton;
	private PdfFontMappingEditor editor;
	private FontReferenceTableModel tableRefModel;
	private JLabel fontPathLabel;
	private JLabel fontPathValueLabel;
	
	@SuppressWarnings("unused")
	private static final Logger logger = Logger.getLogger(FontMappingPanel.class.getName());
	private JButton btnDeleteRefButton;
	
	public FontMappingPanel() {
		super();
		AnnotationProcessor.process(this);
		setOpaque(false);
		setLayout(new FormLayout(new ColumnSpec[] {
				FormFactory.UNRELATED_GAP_COLSPEC,
				FormFactory.DEFAULT_COLSPEC,
				FormFactory.LABEL_COMPONENT_GAP_COLSPEC,
				ColumnSpec.decode("default:grow"),
				FormFactory.RELATED_GAP_COLSPEC,
				ColumnSpec.decode("40dlu"),
				FormFactory.UNRELATED_GAP_COLSPEC,},
			new RowSpec[] {
				FormFactory.UNRELATED_GAP_ROWSPEC,
				FormFactory.PREF_ROWSPEC,
				FormFactory.UNRELATED_GAP_ROWSPEC,
				FormFactory.DEFAULT_ROWSPEC,
				FormFactory.UNRELATED_GAP_ROWSPEC,
				FormFactory.DEFAULT_ROWSPEC,
				RowSpec.decode("85dlu:grow"),
				FormFactory.UNRELATED_GAP_ROWSPEC,}));
		add(getMessagePanel(), "2, 2, 5, 1, fill, fill");
		add(getFontPathLabel(), "2, 4, right, top");
		add(getFontPathValueLabel(), "4, 4, fill, default");
		add(getPanel(), "2, 6, 5, 1, fill, fill");
		add(getFontTableScrollPane(), "2, 7, 5, 1, fill, fill");
	}

	@EventSubscriber(eventClass=PdfAppEvent.class)
	public void handleAppEvent( PdfAppEvent event ) {
		if ( event.getType() == EventType.FontReferenceSave ) {
			FontReferenceTableModel tModel = getTableRefModel();
			tModel.addFontReference((PdfFontMapping)event.getData());
		} else if ( event.getType() == EventType.FontReferenceEdit ) {
			FontReferenceTableModel tModel = getTableRefModel(); 
			tModel.setFontReference((PdfFontMapping) event.getData());
		}
	}
	
	@Override
	public void loadSettings() {
		Collection<PdfFontMapping> mappings = FontRegistry.getInstance().getFontMappings();
		getTableRefModel().clear();
		for(PdfFontMapping mapping: mappings ) {
			getTableRefModel().addFontReference(mapping);
		}
	}

	@Override
	public void saveSettings() {
		List<PdfFontMapping> mappings = getTableRefModel().getFontReferences();
		FontRegistry.getInstance().setFontMappings(mappings);
	}
	
	
	protected JPanel getPanel() {
		if (panel == null) {
			panel = new JPanel();
			panel.setOpaque(false);
			FlowLayout flowLayout = (FlowLayout) panel.getLayout();
			flowLayout.setHgap(0);
			flowLayout.setAlignment(FlowLayout.LEFT);
			flowLayout.setVgap(0);
			panel.setPreferredSize(new Dimension(100, 26));
			panel.add(getBtnNewRefButton());
			panel.add(getBtnEditRefButton());
			panel.add(getBtnDeleteRefButton());
		}
		return panel;
	}
	protected JButton getBtnNewRefButton() {
		if (btnNewRefButton == null) {
			btnNewRefButton = new JButton();
			btnNewRefButton.setName("btn-fontMapping-new");
			btnNewRefButton.setAction(new CreateFontReferenceAction());
		}
		return btnNewRefButton;
	}
	
	protected JButton getBtnEditRefButton() {
		if (btnEditRefButton == null) {
			btnEditRefButton = new JButton();
			btnEditRefButton.setName("btn-fontMapping-edit");
			btnEditRefButton.setAction(new EditFontReferenceAction());
		}
		return btnEditRefButton;
	}
	
	protected JButton getBtnDeleteRefButton() {
		if (btnDeleteRefButton == null) {
			btnDeleteRefButton = new JButton();
			btnDeleteRefButton.setName("btn-fontMapping-delete"); //$NON-NLS-1$
			btnDeleteRefButton.setAction(new DeleteFontMappingAction());
		}
		return btnDeleteRefButton;
	}
	
	private class DeleteFontMappingAction extends AbstractAction {

		public DeleteFontMappingAction() {
			putValue(LARGE_ICON_KEY, Resources.getIcon("icon.deleteFont.small"));
			putValue(SHORT_DESCRIPTION, Resources.getString("label.fontDeleteMapping.tooltip"));
			setEnabled(false);
		}
		
		@Override
		public void actionPerformed(ActionEvent e) {
			PdfFontMapping ref = (PdfFontMapping) getTableRefModel().getFontReference(getFontReferenceTable().getSelectedRow());
			getTableRefModel().remove(ref);
		}
		
	}
	private class EditFontReferenceAction extends AbstractAction {

		public EditFontReferenceAction() {
			putValue(LARGE_ICON_KEY, Resources.getIcon("icon.editFont.small"));
			putValue(SHORT_DESCRIPTION, Resources.getString("label.fontEditReference.tooltip"));
			setEnabled(false);
		}
		
		@Override
		public void actionPerformed(ActionEvent e) {
			PdfFontMapping ref = (PdfFontMapping) getTableRefModel().getFontReference(getFontReferenceTable().getSelectedRow());
			getPdfFontReferenceEditor().setReferenceModel(ref);
			getPdfFontReferenceEditor().setVisible(true);
		}
		
	}
	
	private class CreateFontReferenceAction extends AbstractAction {
		public CreateFontReferenceAction() {
			putValue(LARGE_ICON_KEY, Resources.getIcon("icon.newFont.small"));
			putValue(SHORT_DESCRIPTION, Resources.getString("label.fontCreateReference.tooltip"));
		}
		public void actionPerformed(ActionEvent e) {
			getPdfFontReferenceEditor().setReferenceModel(null);
			getPdfFontReferenceEditor().setVisible(true);
		}
	}
	
	protected PdfFontMappingEditor getPdfFontReferenceEditor() {
		if( editor == null ) {
			editor = new PdfFontMappingEditor();
		}
		return editor;
	}
	
	protected JScrollPane getFontTableScrollPane() {
		if (fontTableScrollPane == null) {
			fontTableScrollPane = new JScrollPane();
			fontTableScrollPane.setViewportView(getFontReferenceTable());
		}
		return fontTableScrollPane;
	}
	protected JTable getFontReferenceTable() {
		if (fontTable == null) {
			fontTable = new JTable(getTableRefModel());
			fontTable.setColumnModel(getFontReferenceTableColumnModel());
			fontTable.setRowHeight(22);
			fontTable.getSelectionModel().addListSelectionListener(new ListSelectionListener() {
				@Override
				public void valueChanged(ListSelectionEvent e) {
					boolean enabled = getFontReferenceTable().getSelectedRow() > -1;
					getBtnEditRefButton().getAction().setEnabled(enabled);
					getBtnDeleteRefButton().getAction().setEnabled(enabled);
				}
			});
			fontTable.addMouseListener(new MouseAdapter() {
				@Override
				public void mouseClicked(MouseEvent e) {
					if (e.getClickCount() == 2) {
						getBtnEditRefButton().getAction().actionPerformed(new ActionEvent(getFontReferenceTable(),5,"edit"));
			        }
				}
			 });
		}
		return fontTable;
	}
	
	protected FontReferenceTableModel getTableRefModel() {
		if( tableRefModel == null ) {
			tableRefModel = new FontReferenceTableModel();
		}
		return tableRefModel;
	}
	
	protected TableColumnModel getFontReferenceTableColumnModel( ) {
		TableColumnModel tcm = new DefaultTableColumnModel();
		TableColumn validCol = new TableColumn(FontReferenceColumns.Valid.ordinal());
		validCol.setHeaderValue(FontReferenceColumns.Valid.getColumnHeader());
		validCol.setWidth(42);
		validCol.setMaxWidth(42);
		validCol.setCellRenderer(new ValidateColumnRenderer());
		TableColumn aliasCol = new TableColumn(FontReferenceColumns.Alias.ordinal());
		aliasCol.setPreferredWidth(70);
		aliasCol.setHeaderValue(FontReferenceColumns.Alias.getColumnHeader());
		TableColumn pathCol = new TableColumn(FontReferenceColumns.Path.ordinal());
		pathCol.setHeaderValue(FontReferenceColumns.Path.getColumnHeader());
		pathCol.setPreferredWidth(140);
		tcm.addColumn(validCol);
		tcm.addColumn(aliasCol);
		tcm.addColumn(pathCol);
		return tcm;
	}
	
	protected MessagePanel getMessagePanel() {
		if (messagePanel == null) {
			messagePanel = new MessagePanel(UIHelper.convertToMultiline(Resources.getString("message.fontMapping.helpText")));
			messagePanel.setPreferredSize(new Dimension(100, 70));
		}
		return messagePanel;
	}
	
	public class ValidateColumnRenderer extends DefaultTableCellRenderer {
		
		@Override
		public Component getTableCellRendererComponent(JTable table, Object value, boolean isSelected, boolean hasFocus, int row, int column) {
			Component comp = super.getTableCellRendererComponent(table, value, isSelected, hasFocus, row, column);
			if( comp instanceof JLabel && value instanceof PdfFontMapping) {
				JLabel label = (JLabel)comp;
				PdfFontMapping ref = (PdfFontMapping)value;
				boolean valid = ref.validate();
				label.setIcon(Resources.getIcon((valid) ? "icon.font.valid" : "icon.font.invalid"));
				label.setText("");
				label.setToolTipText(Resources.getString((valid) ? "message.valid" : ref.getValidationMessage()));
				comp = label;
			}
			return comp;
		}
	}
	
	enum FontReferenceColumns {
		Valid,
		Alias,
		Path;
		
		String getColumnHeader() {
			switch(this) {
			case Valid:
				return Resources.getString("table.header.fontReferenceValid");
			case Alias:
				return Resources.getString("table.header.fontReferenceAlias");
			case Path:
				return Resources.getString("table.header.fontReferencePath");
			}
			return "";
		}
	}
	
	protected class FontReferenceTableModel extends AbstractTableModel {
		List<PdfFontMapping> fontReferences = new ArrayList<PdfFontMapping>();

		
		public void clear() {
			fontReferences.clear();
			fireTableDataChanged();
		}
		
		public void remove(PdfFontMapping ref) {
			int index = -1;
			for(int i = 0; i < fontReferences.size(); i++ ) {
				if( fontReferences.get(i).equals(ref)) {
					index = i;
					break;
				}
			}
			if( index >= 0 ) {
				fontReferences.remove(index);
				fireTableRowsDeleted(index, index);
			}
		}
		
		@Override
		public int getRowCount() {
			return fontReferences.size();
		}

		public void addFontReference(PdfFontMapping ref ) {
			setFontReference(ref,getRowCount());
		}
		
		public void setFontReference(PdfFontMapping ref) {
			for(int i = 0; i < fontReferences.size(); i++ ) {
				if( fontReferences.get(i).equals(ref)) {
					setFontReference(ref,i);
					break;
				}
			}
		}
		
		public void setFontReference(PdfFontMapping ref, int row) {
			if( row < fontReferences.size()) {
				fontReferences.set(row,ref);
				fireTableRowsUpdated(row, row);
			} else {
				fontReferences.add(ref);
				fireTableRowsInserted(row, row);
			}
		}
		
		public List<PdfFontMapping> getFontReferences() {
			return fontReferences;
		}
		
		public PdfFontMapping getFontReference(int row) {
			return fontReferences.get(row);
		}
		
		@Override
		public int getColumnCount() {
			return 3;
		}

		@Override
		public Object getValueAt(int rowIndex, int columnIndex) {
			FontReferenceColumns col = FontReferenceColumns.values()[columnIndex];
			PdfFontMapping value = fontReferences.get(rowIndex);
			switch(col) {
			case Valid:
				return value;
			case Alias:
				return value.getFontAlias();
			case Path:
				return value.getFilePath();
			}
			return "";
		}
		
	}
	
	protected JLabel getFontPathLabel() {
		if (fontPathLabel == null) {
			fontPathLabel = new JLabel(Resources.getString("label.fontSystemPath")); //$NON-NLS-1$
		}
		return fontPathLabel;
	}
	
	protected JLabel getFontPathValueLabel() {
		if (fontPathValueLabel == null) {
			String nativePath = FontRegistry.getInstance().getFontPath();
			String path = (nativePath != null ) ? nativePath : "unknown";
			String msg = MessageFormat.format(Resources.getString("message.fontPath.value"), path, GraphicsEnvironment.getLocalGraphicsEnvironment().getAvailableFontFamilyNames().length );
			fontPathValueLabel = new JLabel(msg); //$NON-NLS-1$
		}
		return fontPathValueLabel;
	}
	
}
