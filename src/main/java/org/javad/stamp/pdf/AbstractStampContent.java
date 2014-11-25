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

import org.javad.pdf.PositionalContent;
import org.javad.pdf.model.PageConfiguration;

public abstract class AbstractStampContent extends PositionalContent implements IStampContent {

	protected int width = 0;
	protected int height = 0;
	private int padding;
	private int vertPadding;
	
	public AbstractStampContent(PageConfiguration configuration) {
		super(configuration);
		padding = Float.valueOf(configuration.getHorizontalSpacing()).intValue();
		vertPadding = Float.valueOf(configuration.getVerticalSpacing()).intValue();
	}


	@Override
	public int getWidth() {
		return width;
	}

	@Override
	public int getHeight() {
		return height;
	}
	
	public void setWidth(int width) {
		this.width = width;
	}
	
	public void setHeight(int height) {
		this.height = height;
	}
	
	@Override
	public int getPadding() {
		return padding;
	}

	@Override
	public int getVerticalPadding() {
		return vertPadding;
	}
	
	@Override
	public void setPadding(int padding) {
		this.padding = padding;
	}
	
	@Override
	public void setVerticalPadding(int padding) {
		vertPadding = padding;
	}

	
}
