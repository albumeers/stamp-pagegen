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
package org.javad.stamp.pdf.ui.model;

import java.io.File;

public class GenerateBean {

	private File inputFile;
	private File outputFile;
	private boolean drawBorder;
	private boolean reversePages;
	
	public GenerateBean() {
		super();
	}
	
	public GenerateBean(File inputFile, File outputFile) {
		this();
		setInputFile(inputFile);
		setOutputFile(outputFile);
	}
	
	public void setDrawBorder(boolean drawBorder) {
		this.drawBorder = drawBorder;
	}
	
	public boolean isDrawBorder() {
		return drawBorder;
	}
	
	public boolean isReversePages() {
		return reversePages;
	}
	
	public void setReversePages(boolean reversePages) {
		this.reversePages = reversePages;
	}
	
	public File getInputFile() {
		return inputFile;
	}
	public void setInputFile(File inputFile) {
		this.inputFile = inputFile;
	}
	public File getOutputFile() {
		return outputFile;
	}
	public void setOutputFile(File outputFile) {
		this.outputFile = outputFile;
	}
	
	public boolean isValid( ) {
		return inputFile != null && outputFile != null;
	}
	
	
}
