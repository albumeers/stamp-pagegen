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
import org.javad.stamp.pdf.SetTenant;
import org.javad.stamp.pdf.SetTenant.Orientation;
import org.javad.stamp.pdf.StampBox;
import org.javad.stamp.pdf.StampBox.SetTenantPosition;
import org.w3c.dom.Element;
import org.w3c.dom.NodeList;

public class SetTenantParser extends AbstractXMLParser<SetTenant> implements XMLDefinitions {

	@SuppressWarnings("unchecked")
	@Override
	public SetTenant parse(Element set, PageConfiguration configuration) {
		SetTenant setTenant = new SetTenant(configuration);
		if( set.hasAttribute(ORIENTATION)) {
			setTenant.setOrientation(Orientation.valueOf(set.getAttribute(ORIENTATION).toUpperCase()));
		}
                if( set.hasAttribute(BORDER)) {
                    setTenant.setBorder(Boolean.valueOf(set.getAttribute(BORDER)));
                }
		NodeList stamps = set.getChildNodes();
		if( stamps != null ) {
			for(int i = 0; i < stamps.getLength(); i++ ) {
				Element rowSet = (Element)stamps.item(i);
				if( rowSet.getTagName().equals(STAMP)) {
					StampBox box = getFactory().getParser(STAMP).parse(rowSet,configuration);
					if( box != null ) {
						SetTenantPosition position = SetTenantPosition.middle;
						if( i == 0 ) {
							position = SetTenantPosition.first;
						} else if ( i == stamps.getLength()-1) {
							position = SetTenantPosition.last;
						}
						box.setSetTenantPosition(position);
						setTenant.addStamp(box);
					}
				}
			}
		}
		return setTenant;
	}

}
