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
package org.javad.stamp.pdf.events;

public class PdfAppEvent {

	private EventType type;
	private Object data;
	private Object source;
	
	public PdfAppEvent(EventType type) {
		super();
		this.type = type;
	}
	
	public PdfAppEvent(EventType type, Object data) {
		this(type);
		this.data = data;
	}
	
	public PdfAppEvent(EventType type, Object data, Object source) {
		this(type,data);
		setSource(source);
	}
	
	public void setSource(Object source) {
		this.source = source;
	}
	
	public EventType getType() {
		return type;
	}
	
	@SuppressWarnings("unchecked")
	public <X> X getSource() {
		return (X)source;
	}
	
	@SuppressWarnings("unchecked")
	public <X> X getData() {
		return (X)data;
	}
	
	
	public enum EventType {
		FontReferenceEdit,
		FontReferenceSave,
		FontBeanEdit,
		Generate,
                GenerateXml,
		Generate_Error,
		Generated;
	}
}
