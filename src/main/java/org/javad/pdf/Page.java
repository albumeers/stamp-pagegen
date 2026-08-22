/*
	Copyright 2014-2026 Jason Drake (jadrake75@gmail.com)
	
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
package org.javad.pdf;

import java.util.ArrayList;
import java.util.List;
import javax.xml.stream.XMLStreamException;
import javax.xml.stream.XMLStreamWriter;
import org.javad.xml.XMLSerializable;

public class Page implements XMLSerializable {

	PageTitle title;
        String pageNum;
        
	List<ISetContent> content = new ArrayList<>();
	
	public PageTitle getTitle() {
		return title;
	}
	public void setTitle(PageTitle title) {
		this.title = title;
	}
        
        public void setPageNum(String num) {
            pageNum = num;
        }
        
        public String getPageNum() {
            return pageNum;
        }
        
	public List<ISetContent> getContent() {
		return content;
	}
	public void setContent(List<ISetContent> content) {
		this.content = content;
	}
	
	public void addContent(ISetContent item) {
		content.add(item);
	}
        
        @Override
        public void writeToXml(XMLStreamWriter writer) throws XMLStreamException {
            writer.writeStartElement("page");
            getTitle().writeToXml(writer);
            if( getPageNum() != null ) {
                writer.writeAttribute("pagenum", getPageNum());
            }
            for( ISetContent c: getContent()) {
                c.writeToXml(writer);
            }
            writer.writeEndElement();
            writer.flush();
        };

}
