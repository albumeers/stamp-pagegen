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

import java.util.Arrays;
import java.util.Set;
import org.javad.pdf.ISetContent;
import org.javad.pdf.Page;
import org.javad.pdf.PageTitle;
import org.javad.pdf.model.PageConfiguration;
import org.w3c.dom.Element;
import org.w3c.dom.NodeList;

public class PageParser extends AbstractXMLParser<Page> implements XMLDefinitions {

	@SuppressWarnings("unchecked")
	@Override
	public Page parse(Element element, PageConfiguration configuration) {
                Set<String> skipTerms = configuration.getSkipTerms();
                if( element.hasAttribute(SKIP) && !skipTerms.isEmpty()) {
                    for(String t : element.getAttribute(SKIP).split(" ")) {
                        if( skipTerms.contains(t)) {
                            return null;
                        }
                    }
                }
		Page p = new Page();
		
		PageTitle pt = new PageTitle(configuration);
                if( element.hasAttribute(TITLE)) {
                    pt.setTitle(element.getAttribute(TITLE).replace("\\n","\n"));
                }
		if( element.hasAttribute(SUBTITLE)) {
			pt.setSubTitle(element.getAttribute(SUBTITLE).replace("\\n","\n"));
		}
		if( element.hasAttribute(CLASSIFIER)) {
			pt.setClassifier(element.getAttribute(CLASSIFIER));
		}
		p.setTitle(pt);
		
		NodeList children = element.getChildNodes();
		if( children != null ) { 
			for( int i = 0; i < children.getLength(); i++ ) {
				Element elm = (Element)children.item(i);
				ISetContent content = null;
				if( elm.getTagName().equals(SET)) {
					content = getFactory().getParser(SET).parse(elm,configuration);
				} else if( elm.getTagName().equals(COLUMN_SET)) {
					content = getFactory().getParser(COLUMN_SET).parse(elm,configuration);
				}
				if( content != null ) {
					p.addContent(content);
				}
			}
		}
		
		return p;
	}

}
