/*
   Copyright 2023 Jason Drake (jadrake75@gmail.com)
 
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
package org.javad.stamp.xml;

import org.javad.pdf.VerticalAlignment;
import org.javad.pdf.model.PageConfiguration;
import org.javad.stamp.pdf.IStampContent;
import org.javad.stamp.pdf.StampRow;
import org.javad.xml.IXMLContentParser;
import org.w3c.dom.Element;
import org.w3c.dom.Node;
import org.w3c.dom.NodeList;

public class StampRowParser extends AbstractXMLParser<StampRow> implements XMLDefinitions {

	public StampRowParser() {
	}

	@SuppressWarnings("unchecked")
	@Override
	public StampRow parse(Element rowSet, PageConfiguration configuration) {
		StampRow row = new StampRow(configuration);
		if (rowSet.hasAttribute(SKIP)) {
			row.parseSkipTerms(rowSet.getAttribute(SKIP));
		}
		if (rowSet.hasAttribute(DESCRIPTION)) {
			row.setDescription(rowSet.getAttribute(DESCRIPTION).replace("\\n", "\n"));
		}
		if (rowSet.hasAttribute(VERTICAL_OFFSET)) {
			row.setVerticalOffset(Float.parseFloat(rowSet.getAttribute(VERTICAL_OFFSET)));
		}
		if (rowSet.hasAttribute(ALIGNMENT_VERTICAL)) {
			row.setValign(VerticalAlignment.valueOf(rowSet.getAttribute(ALIGNMENT_VERTICAL)));
		}
		if (rowSet.hasAttribute(SPACING_HORIZONTAL)) {
			row.setHorizontalPadding(Float.parseFloat(rowSet.getAttribute(SPACING_HORIZONTAL)));
		}
		NodeList children = rowSet.getChildNodes();
		if (children != null) {
			for (int j = 0; j < children.getLength(); j++) {
				Node node = (Node) children.item(j);
				if (node instanceof Element) {
					Element child = (Element) node;
					IXMLContentParser<IStampContent> parser = (IXMLContentParser<IStampContent>) getFactory()
							.getParser(child);
					if (parser != null) {
						IStampContent content = parser.parse(child, configuration);
						if (content != null) {
							row.addStampContent(content);
						}
					}
				}
			}
		}
		return row;
	}

}
