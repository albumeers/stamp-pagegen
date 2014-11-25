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
package org.javad.stamp.pdf;

import org.javad.pdf.IContentGenerator;
import org.javad.pdf.IPositionalContent;
import org.javad.xml.XMLSerializable;

public interface IStampContent extends IContentGenerator, IPositionalContent, XMLSerializable {

	public int getWidth();
	
	public int getHeight();
	
	public void setWidth(int width);
	
	public void setHeight(int height);
	
	public int getPadding();
	
	public int getVerticalPadding();
	
	public void setPadding(int padding);
	
	public void setVerticalPadding(int padding);
}
