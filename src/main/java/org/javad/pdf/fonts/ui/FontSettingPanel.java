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

import java.awt.Dimension;
import java.awt.FlowLayout;
import java.awt.event.ActionEvent;
import java.awt.event.MouseEvent;
import java.text.DecimalFormat;
import java.util.ArrayList;
import java.util.Collection;
import java.util.List;
import java.util.logging.Logger;

import javax.swing.AbstractAction;
import javax.swing.JButton;
import javax.swing.JPanel;
import javax.swing.JScrollPane;
import javax.swing.JTable;
import javax.swing.event.ListSelectionEvent;
import javax.swing.event.ListSelectionListener;
import javax.swing.table.AbstractTableModel;
import javax.swing.table.DefaultTableColumnModel;
import javax.swing.table.TableColumn;
import javax.swing.table.TableColumnModel;

import org.bushe.swing.event.annotation.AnnotationProcessor;
import org.bushe.swing.event.annotation.EventSubscriber;
import org.javad.components.ISettingsPanel;
import org.javad.components.MessagePanel;
import org.javad.components.UIHelper;
import org.javad.pdf.fonts.FontRegistry;
import org.javad.pdf.fonts.PdfFontBean;
import org.javad.stamp.pdf.Resources;
import org.javad.stamp.pdf.events.PdfAppEvent;
import org.javad.stamp.pdf.events.PdfAppEvent.EventType;

import com.itextpdf.text.Font;
import com.jgoodies.forms.factories.FormFactory;
import com.jgoodies.forms.layout.ColumnSpec;
import com.jgoodies.forms.layout.FormLayout;
import com.jgoodies.forms.layout.RowSpec;

@SuppressWarnings("serial")
public class FontSettingPanel extends JPanel implements ISettingsPanel {
	
	private JPanel panel;
	private JButton editFontUsageButton;
	private MessagePanel messagePanel;
	private JScrollPane scrollPane;
	private JTable table;
	private FontTableModel tableModel;
	private PdfFontEditor editor;
	
	private static final Logger logger = Logger.getLogger(FontSettingPanel.class.getName());
	
	public FontSettingPanel() {
		super();
		AnnotationProcessor.process(this);
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
				RowSpec.decode("default:grow"),
				FormFactory.UNRELATED_GAP_ROWSPEC,}));
		add(getMessagePanel(), "2, 2, 3, 1, fill, fill");
		add(getPanel(), "2, 4, 3, 1, fill, fill");
		add(getScrollPane(), "2, 5, 3, 1, fill, fill");
	}
	
	
	protected TableColumnModel getFontTableColumnModel( ) {
		TableColumnModel tcm = new DefaultTableColumnModel();
		TableColumn usageCol = new TableColumn(FontColumns.Usage.ordinal());
		usageCol.setHeaderValue(FontColumns.Usage.getColumnHeader());
		usageCol.setPreferredWidth(125);
		TableColumn aliasCol = new TableColumn(FontColumns.Alias.ordinal());
		aliasCol.setPreferredWidth(70);
		aliasCol.setHeaderValue(FontColumns.Alias.getColumnHeader());
		TableColumn styleCol = new TableColumn(FontColumns.Style.ordinal());
		styleCol.setHeaderValue(FontColumns.Style.getColumnHeader());
		styleCol.setPreferredWidth(70);
		TableColumn sizeCol = new TableColumn(FontColumns.Size.ordinal());
		sizeCol.setHeaderValue(FontColumns.Size.getColumnHeader());
		sizeCol.setPreferredWidth(25);
		tcm.addColumn(usageCol);
		tcm.addColumn(aliasCol);
		tcm.addColumn(styleCol);
		tcm.addColumn(sizeCol);
		return tcm;
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
			panel.add(getEditFontUsageButton());
		}
		return panel;
	}
	protected JButton getEditFontUsageButton() {
		if (editFontUsageButton == null) {
			editFontUsageButton = new JButton();
			editFontUsageButton.setName("btn-fontReference-edit");
			editFontUsageButton.setAction(new EditFontUsage());
		}
		return editFontUsageButton;
	}
	protected MessagePanel getMessagePanel() {
		if (messagePanel == null) {
			messagePanel = new MessagePanel(UIHelper.convertToMultiline(Resources.getString("message.font.helpText")));
		}
		return messagePanel;
	}
	protected JScrollPane getScrollPane() {
		if (scrollPane == null) {
			scrollPane = new JScrollPane();
			scrollPane.setViewportView(getTable());
		}
		return scrollPane;
	}
	protected JTable getTable() {
		if (table == null) {
			table = new JTable(getTableModel());
			table.setColumnModel(getFontTableColumnModel());
			table.getSelectionModel().addListSelectionListener(new ListSelectionListener() {
				@Override
				public void valueChanged(ListSelectionEvent e) {
					getEditFontUsageButton().getAction().setEnabled(e.getFirstIndex() >= 0);
				}
			});
			table.addMouseListener(new java.awt.event.MouseAdapter() {
				@Override
				public void mouseClicked(MouseEvent e) {
					if (e.getClickCount() == 2) {
						getEditFontUsageButton().getAction().actionPerformed(new ActionEvent(getTable(),5,"edit"));
			        }
				}
			 });
		}
		return table;
	}
	
	protected FontTableModel getTableModel() {
		if( tableModel == null)  {
			tableModel = new FontTableModel();
		}
		return tableModel;
	}
	
	private PdfFontEditor getEditor() {
		if( editor == null ) {
			editor = new PdfFontEditor();
		}
		return editor;
	}
	

	class EditFontUsage extends AbstractAction {

		EditFontUsage() {
			putValue(LARGE_ICON_KEY, Resources.getIcon("icon.editFont.small"));
			putValue(SHORT_DESCRIPTION, Resources.getString("label.fontEdit.tooltip"));
			setEnabled(false);
		}
		
		@Override
		public void actionPerformed(ActionEvent e) {
			int row = getTable().getSelectedRow();
			if( row >= 0 ) {
				PdfFontBean bean = getTableModel().getFontBean(row);
				getEditor().initialize(bean, FontRegistry.getInstance().getFontMappings());
				getEditor().setVisible(true);
			}
			else {
				logger.warning("The edit action was performed on a non-selected row.");
			}
		}
	}
	@Override
	public void loadSettings() {
		
		Collection<PdfFontBean> beans = FontRegistry.getInstance().getFontBeans();
		getTableModel().clear();
		for( PdfFontBean bean: beans ) {
			getTableModel().addFontBean(bean);
		}
	}
	@Override
	public void saveSettings() {
		FontRegistry.getInstance().setFontBeans(getTableModel().getFontBeans());
	}
	
	@EventSubscriber(eventClass=PdfAppEvent.class)
	public void handleAppEvent( PdfAppEvent event ) {
		if ( event.getType() == EventType.FontBeanEdit ) {
			PdfFontBean bean = event.getData();
			getTableModel().update(bean);
		}
	}
	
	enum FontColumns {
		Usage,
		Alias,
		Style,
		Size;
		
		String getColumnHeader( ) {
			switch(this) {
			case Usage:
				return Resources.getString("table.header.fontUsage");
			case Alias:
				return Resources.getString("table.header.fontAlias");
			case Style:
				return Resources.getString("table.header.fontStyle");
			case Size:
				return Resources.getString("table.header.fontSize");
			}
			return "";
		}
	}
	
	
	protected class FontTableModel extends AbstractTableModel {

		List<PdfFontBean> fonts = new ArrayList<PdfFontBean>();
		
		@Override
		public int getRowCount() {
			return fonts.size();
		}

		public void clear() {
			fonts.clear();
			fireTableDataChanged();
		}

		public void addFontBean(PdfFontBean bean) {
			setFontBean(getRowCount(), bean);
			fireTableRowsInserted(getRowCount()-1, getRowCount()-1);
		}
		
		public PdfFontBean getFontBean(int row) {
			return fonts.get(row);
		}
		
		public void update(PdfFontBean bean) {
			int row = 0;
			for( PdfFontBean b: fonts) {
				if( b.equals(bean)) {
					fireTableRowsUpdated(row,row);
					break;
				}
				row++;
			}
		}
		
		public void setFontBean(int row, PdfFontBean bean) {
			if( row < fonts.size()) {
				fonts.set(row,bean);
			} else {
				fonts.add(bean);
			}
			fireTableRowsInserted(row, row);
		}
		
		public List<PdfFontBean> getFontBeans() {
			return fonts;
		}
		
		@Override
		public int getColumnCount() {
			return FontColumns.values().length;
		}

		@Override
		public Object getValueAt(int rowIndex, int columnIndex) {
			FontColumns col = FontColumns.values()[columnIndex];
			PdfFontBean bean = fonts.get(rowIndex);
			switch(col) {
				case Usage:
					return bean.getFontDefinition().toString();
				case Alias:
					if( bean.isSystem()) {
						return bean.getFontFamily();
					} else if( bean.getFontMapping() != null ) {
						return bean.getFontMapping().getFontAlias();
					}
				case Style:
					return getStyle(bean);
				case Size:
					DecimalFormat format = new DecimalFormat("0.0##");
					return format.format(bean.getSize());
			}
			return "";
		}
		
		private String getStyle(PdfFontBean bean) {
			 StringBuilder str = new StringBuilder("");
			 if( bean.getStyle() < 0 || bean.getStyle() == Font.NORMAL ) {
				 str.append(Resources.getString("table.style.normal"));
			}
			 else {
				 if ( bean.isBold() ) {
					 str.append(Resources.getString("table.style.bold"));
				 }
				 if (bean.isItalic()) {
					 if( str.length() >  0 ) {
						 str.append(", ");
					 }
					 str.append(Resources.getString("table.style.italic"));
				 }
				 if( bean.isUnderline()) {
					 if( str.length() > 0 ) {
						 str.append(", ");
					 }
					 str.append(Resources.getString("table.style.underline"));
				 }
			 }			 
			 return str.toString();
		}

	}
}
