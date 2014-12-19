/*
   Copyright 2014 Jason Drake (jadrake75@gmail.com)
 
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

import org.javad.pdf.ISetContent;
import org.javad.pdf.model.PageConfiguration;
import org.javad.stamp.pdf.StampSet;
import org.javad.xml.XML;
import org.w3c.dom.Element;
import org.w3c.dom.NodeList;

public class StampSetParser extends AbstractXMLParser<StampSet> implements XMLDefinitions {

	@SuppressWarnings("unchecked")
	@Override
	public StampSet parse(Element set, PageConfiguration configuration) {
		StampSet stampSet = new StampSet(configuration);
                if( set.hasAttribute(SKIP)) {
                    stampSet.parseSkipTerms(set.getAttribute(SKIP));
                }
                if( set.hasAttribute(ISSUE)) {
                    stampSet.setIssue(XML.normalize(set.getAttribute(ISSUE)));
                }
		stampSet.setDescription(XML.normalize(set.getAttribute(DESCRIPTION)));
		if( set.hasAttribute(DESCRIPTION_SECONDARY)) {
			stampSet.setDescriptionSecondary(XML.normalize(set.getAttribute(DESCRIPTION_SECONDARY)));
		}
		if( set.hasAttribute(COMMENT)) {
			stampSet.setComment(XML.normalize(set.getAttribute(COMMENT)));
		}
		NodeList rowSets = set.getChildNodes();
		if( rowSets != null ) {
			for(int i = 0; i < rowSets.getLength(); i++ ) {
				ISetContent content = null;
				Element rowSet = (Element)rowSets.item(i);
				if( rowSet.getTagName().equals(STAMP_ROW)) {
					content = getFactory().getParser(STAMP_ROW).parse(rowSet,configuration);
					
				} else if ( rowSet.getTagName().equals(COMPOSITE_SET)) {
					content = getFactory().getParser(COMPOSITE_SET).parse(rowSet, configuration);
				}
				if( content != null ) {
					stampSet.addContentRow(content);
				}
			}
		}
		return stampSet;
	}

}
