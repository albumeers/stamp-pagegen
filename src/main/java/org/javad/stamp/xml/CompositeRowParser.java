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

import org.javad.pdf.SpacingMode;
import org.javad.pdf.model.PageConfiguration;
import org.javad.stamp.pdf.CompositeRow;
import org.javad.stamp.pdf.StampRow;
import org.w3c.dom.Element;
import org.w3c.dom.NodeList;

public class CompositeRowParser extends AbstractXMLParser<CompositeRow> implements XMLDefinitions {

	@SuppressWarnings("unchecked")
	@Override
	public CompositeRow parse(Element element, PageConfiguration configuration) {
		CompositeRow compRow = new CompositeRow(configuration);
		if (element.hasAttribute(SKIP)) {
			compRow.parseSkipTerms(element.getAttribute(SKIP));
		}
		if (element.getAttribute(DESCRIPTION) != null) {
			compRow.setDescription(element.getAttribute(DESCRIPTION));
		}
		if (element.hasAttribute(SPACING)) {
			compRow.setSpacingMode(SpacingMode.valueOf(element.getAttribute(SPACING).toLowerCase()));
		}
		if (element.hasAttribute(VERTICAL_OFFSET)) {
			compRow.setVerticalOffset(Float.parseFloat(element.getAttribute(VERTICAL_OFFSET)));
		}
		NodeList compSets = element.getChildNodes();
		if (compSets != null) {
			for (int j = 0; j < compSets.getLength(); j++) {
				Element rowSet2 = (Element) compSets.item(j);
				StampRow row2 = getFactory().getParser(STAMP_ROW).parse(rowSet2, configuration);
				if (row2 != null) {
					compRow.addStampRow(row2);
				}
			}
		}
		return compRow;
	}

}
