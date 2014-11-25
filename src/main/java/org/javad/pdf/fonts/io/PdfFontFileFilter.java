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
package org.javad.pdf.fonts.io;

import java.io.File;
import java.io.FilenameFilter;

import javax.swing.JFileChooser;
import javax.swing.filechooser.FileFilter;

import org.javad.stamp.pdf.Resources;

public class PdfFontFileFilter extends FileFilter implements FilenameFilter {

	private FilterMode mode;

	public PdfFontFileFilter(FilterMode mode) {
		super();
		this.mode = mode;
	}
	
	@Override
	public boolean accept(File dir, String name) {
		return acceptFilename(name.toLowerCase());
	}

	
	@Override
	public boolean accept(File f) {
		boolean accept = f.isDirectory() && f.canRead();
		if( !accept ) {
			accept = f.isFile() && acceptFilename(f.getName().toLowerCase());
		}
		return accept;
	}

	private boolean acceptFilename(String name) {
		boolean accept = false;
		switch(mode) {
		case OTF:
			accept = name.endsWith(".otf");
			break;
		case TTF:
			accept = name.endsWith(".ttf") || name.endsWith(".ttc");
			break;
		case ALL:
			accept = name.endsWith(".ttf") || name.endsWith(".ttc") || name.endsWith(".otf");
		}
		return accept;
	}

	@Override
	public String getDescription() {
		switch(mode) {
		case OTF:
			return Resources.getString("filter.otf");
		case TTF:
			return Resources.getString("filter.ttf");
		default:
			return Resources.getString("filter.fonts");
		}
	}
	
	/**
	 * Will return a file chooser configured to not show the All files filter, but instead
	 * the supported file types and a "All supported images" filter which will be the default.
	 * 
	 * @return
	 */
	public static JFileChooser getFileChooser() {
		JFileChooser fileChooser = new JFileChooser();
		fileChooser.setAcceptAllFileFilterUsed(false);
		for(FilterMode mode: FilterMode.values()) {
			fileChooser.addChoosableFileFilter(new PdfFontFileFilter(mode));
		}
		return fileChooser;
	}
	
	public enum FilterMode {
		OTF,
		TTF,
		ALL;
	}

	
}
