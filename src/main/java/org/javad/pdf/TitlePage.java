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
package org.javad.pdf;

import javax.xml.stream.XMLStreamException;
import javax.xml.stream.XMLStreamWriter;
import org.javad.xml.XMLSerializable;

/**
 */
public class TitlePage implements XMLSerializable {

    private TitlePageContent content;
    
    @Override
    public void writeToXml(XMLStreamWriter writer) throws XMLStreamException {
        writer.writeStartElement("page");
        getTitlePageContent().writeToXml(writer);
        writer.writeEndElement();
        writer.flush();
    }
    
    public void setTitlePageContent(TitlePageContent c) {
        content = c;
    }
    
    public TitlePageContent getTitlePageContent() {
        return content;
    }
    
}
