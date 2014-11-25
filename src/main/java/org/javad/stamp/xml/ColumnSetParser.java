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
package org.javad.stamp.xml;

import org.javad.pdf.model.PageConfiguration;
import org.javad.stamp.pdf.ColumnSet;
import org.javad.pdf.SpacingMode;
import org.javad.stamp.pdf.StampSet;
import static org.javad.stamp.xml.XMLDefinitions.ISSUE;
import org.javad.xml.XML;
import org.w3c.dom.Element;
import org.w3c.dom.NodeList;

public class ColumnSetParser extends AbstractXMLParser<ColumnSet> implements XMLDefinitions {

	@SuppressWarnings("unchecked")
	@Override
	public ColumnSet parse(Element element, PageConfiguration configuration) {
		ColumnSet cols = new ColumnSet(configuration);
                if( element.hasAttribute(SPACING)) {
                    cols.setSpacingMode(SpacingMode.valueOf(element.getAttribute(SPACING).toLowerCase()));
		}
                if( element.hasAttribute(ISSUE)) {
                    cols.setIssue(XML.normalize(element.getAttribute(ISSUE)));
                }
		NodeList sets = element.getElementsByTagName(SET);
		if( sets != null ) {
			for(int i = 0; i < sets.getLength(); i++ ) {
				Element s = (Element)sets.item(i);
				StampSet sc = getFactory().getParser(SET).parse(s,configuration);
				if( sc != null ) {
					cols.addStampSet(sc);
				}
			}
		}
		return cols;
	}

}
