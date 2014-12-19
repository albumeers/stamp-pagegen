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
package org.javad.stamp.xml;

import java.awt.image.BufferedImage;
import java.io.File;
import java.io.IOException;
import java.util.logging.Level;
import java.util.logging.Logger;

import javax.imageio.ImageIO;

import org.javad.pdf.model.PageConfiguration;
import org.javad.stamp.pdf.StampBox;
import org.javad.stamp.pdf.StampBox.Bisect;
import org.javad.stamp.pdf.StampBox.Shape;
import org.w3c.dom.Element;

public class StampBoxParser extends AbstractXMLParser<StampBox> implements XMLDefinitions {

	public static final int DIMENSION = 0;
	public static final int DENOMINATION = 1;
	public static final int DESCRIPTION = 2;
	public static final int DESCRIPTION_SECONDARY = 3;
	public static final int CATALOGUE_NUMBER = 4;
	
	private static Logger logger = Logger.getLogger(StampBoxParser.class.getName());
	
	@SuppressWarnings("unchecked")
	@Override
	public StampBox parse(Element element, PageConfiguration configuration) {
		StampBox stamp = null;
		String content = element.getTextContent();
		if( content != null && !content.isEmpty()) {
			stamp = new StampBox(configuration);
                        if( element.hasAttribute(SKIP)) {
                            stamp.parseSkipTerms(element.getAttribute(SKIP));
                        }
			if( element.hasAttribute(IMAGE)) {
				String imagePath = element.getAttribute(IMAGE);
				try {
					File imageFile = new File(imagePath);
					File folder = getFactory().getWorkingFolder();
					if( folder != null ) {
						imageFile = new File(folder, imagePath);
					}
					if( imageFile.exists()) {
						BufferedImage img = ImageIO.read(imageFile);
						stamp.setImage(img);
					} else {
						logger.warning("The image file: " + imagePath + " was not found relative to the album xml file.");
					}
				} catch (IOException e) {
					logger.log(Level.WARNING,"Could not load the image " + imagePath, e);
				}
			}
			if( element.hasAttribute(IMAGE_ONLY)) {
				stamp.setImageOnly(Boolean.valueOf(element.getAttribute(IMAGE_ONLY)));
			}
                        if( element.hasAttribute(BORDER)) {
                            stamp.setBorder(Boolean.valueOf(element.getAttribute(BORDER)));
                        }
			if( element.hasAttribute(BISECT)) {
				String bisect = element.getAttribute(BISECT);
				stamp.setBisect(Bisect.valueOf(bisect));
			}
			if( element.hasAttribute(SHAPE)) {
				String shape = element.getAttribute(SHAPE);
				stamp.setShape(Shape.valueOf(shape));
			}
			String[] vars = content.trim().split("\"(\\s|,)\"");
			if( vars.length > 0 ) {
				for(int i = 0; i < vars.length; i++) {
					switch(i) {
					case DIMENSION:
						String[] dim = (( vars[i].startsWith("\"")) ? ( vars[i].substring(1)) : vars[i]).split(" ");
						if( dim.length != 2 ) {
							logger.warning("the dimension variable only supports two dimensions: " + vars[i]);
						}
						stamp.setWidth(Integer.parseInt(dim[0]));
						if( dim[1].endsWith("\"")) {
							dim[1] = dim[1].substring(0,dim[1].length()-1);
						}
						stamp.setHeight(Integer.parseInt(dim[1]));
						break;
					case DENOMINATION:
						stamp.setDenomination(vars[i]);
						break;
					case DESCRIPTION:
						stamp.setDescription(vars[i]);
						break;
					case DESCRIPTION_SECONDARY:
						if( !vars[i].trim().isEmpty()) {
							stamp.setDescriptionSecondary(vars[i]);
						}
						break;
					case CATALOGUE_NUMBER:
						String num = ( vars[i].endsWith("\"")) ? vars[i].substring(0,vars[i].length()-1) : vars[i];
						stamp.setCatalogueNumber(num);
						break;
					}
				}
			}
		}
		return stamp;
	}

}
