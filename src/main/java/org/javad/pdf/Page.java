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
