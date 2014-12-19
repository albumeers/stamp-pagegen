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

import com.itextpdf.text.BaseColor;
import com.itextpdf.text.Font;
import com.itextpdf.text.pdf.PdfContentByte;
import java.awt.Color;
import java.awt.Image;
import java.awt.Transparency;
import java.awt.image.BufferedImage;
import java.util.ArrayList;
import java.util.List;
import java.util.logging.Level;
import java.util.logging.Logger;
import javax.xml.stream.XMLStreamException;
import javax.xml.stream.XMLStreamWriter;
import org.javad.pdf.fonts.FontRegistry;
import org.javad.pdf.fonts.PdfFontDefinition;
import org.javad.pdf.model.PageConfiguration;
import org.javad.pdf.util.PdfUtil;
import org.javad.stamp.xml.XMLDefinitions;
import org.javad.xml.XMLSerializable;

/**
 *
 */
public class TitlePageContent extends PositionalContent implements XMLSerializable, IContentGenerator {

    private String title;
    private String subTitle;
    private Image image;
    private String description;
    private List<String> items = new ArrayList<>();
    private static final Logger logger = Logger.getLogger(TitlePageContent.class.getName());
    
    public TitlePageContent(PageConfiguration configuration) {
        super(configuration);
    }

    @Override
    public void writeToXml(XMLStreamWriter writer) throws XMLStreamException {
        if( getTitle() != null ) {
            writer.writeAttribute("title", getTitle());
        }
        if (getSubTitle() != null) {
            writer.writeAttribute("subtitle", getSubTitle());
        }
        if( getDescription() != null ) {
            writer.writeAttribute(XMLDefinitions.DESCRIPTION, getDescription());
        }
        if( !getItems().isEmpty()) {
            writer.writeStartElement(XMLDefinitions.CONTENT_ITEMS);
            for(String s: getItems()) {
                writer.writeStartElement(XMLDefinitions.ITEM);
                writer.writeCharacters(s);
                writer.writeEndElement();
            }
            writer.writeEndElement();
        }
    }

    protected com.itextpdf.text.Image determineScaledImage(Image image) throws Exception {
        com.itextpdf.text.Image img = com.itextpdf.text.Image.getInstance(image, Color.WHITE);
        if(image instanceof BufferedImage ) {
            BufferedImage bImg = (BufferedImage)image;
            int[] transparencyMask;
            if( bImg.getColorModel().getTransparency() == Transparency.TRANSLUCENT) {
                int components = bImg.getColorModel().getColorSpace().getNumComponents();
                transparencyMask = new int[components*2];
                for( int i = 0; i < transparencyMask.length; i = i + 2) {
                    transparencyMask[i] = 0;
                    transparencyMask[i+1] = 1;
                }
                img.setTransparency(transparencyMask);
            }
        }
        
        float vRatio = img.getHeight() / PdfUtil.convertFromMillimeters(configuration.getHeight() - configuration.getMarginTop() - configuration.getMarginBottom());
        float hRatio = img.getWidth() / PdfUtil.convertFromMillimeters(configuration.getWidth() - configuration.getMarginLeft() - configuration.getMarginRight());
        float ratio = Math.max(1.0f, Math.max(vRatio / 0.5f, hRatio / 0.5f));
        logger.log(Level.FINE, "Ratio is: {0}", ratio);
        img.scaleAbsolute(img.getWidth() / ratio, img.getHeight() / ratio);
        float x = PdfUtil.convertFromMillimeters(configuration.getMarginLeft() + ( configuration.getWidth() - configuration.getMarginLeft() - configuration.getMarginRight()) / 2) - img.getWidth() / (2 * ratio);
        float y = PdfUtil.convertFromMillimeters(configuration.getMarginBottom() + (configuration.getHeight() - configuration.getMarginTop() - configuration.getMarginBottom())/ 1.5f) - img.getHeight() / (2 * ratio);
        img.setAbsolutePosition(x, y); 
        return img;
    }
        
    @Override
    public OutputBounds generate(PdfContentByte content) {
        if (isSkipped()) {
            return new OutputBounds(getX(), getY(), 0, 0);
        }
        int maxWidth = 0;
        float top = getY() - PdfUtil.convertFromMillimeters((configuration.getHeight() - configuration.getMarginBottom() - configuration.getMarginTop()) / 2);
        if (getImage() != null) {
            try {
                com.itextpdf.text.Image img = determineScaledImage(getImage());
                if (img != null) {
                    content.addImage(img);
                    top = img.getAbsoluteY() - PdfUtil.convertFromMillimeters(25.0f);
                }
            } catch (Exception e) {
                logger.log(Level.FINER, "An error occured scaling the image. ", e);
            }
        }
        content.setColorStroke(BaseColor.BLACK);
        
        Font f = FontRegistry.getInstance().getFont(PdfFontDefinition.AlbumTitle);
        content.setFontAndSize(f.getBaseFont(), f.getSize());
        
        content.setHorizontalScaling(110.0f);
        if(getTitle() != null && !getTitle().isEmpty()) {
            maxWidth = (int) f.getBaseFont().getWidthPoint(getTitle().toUpperCase(), f.getSize());
            PdfUtil.renderConstrainedText(content, getTitle().toUpperCase(), f, getX(), top, maxWidth);
        }
        if (getSubTitle() != null && !getSubTitle().isEmpty()) {
            Font subFont = FontRegistry.getInstance().getFont(PdfFontDefinition.AlbumSubtitle);
            top -= subFont.getCalculatedSize() + PdfUtil.convertFromMillimeters(3.0f);
            content.setFontAndSize(subFont.getBaseFont(), subFont.getSize());
            maxWidth = Math.max(maxWidth, (int)content.getEffectiveStringWidth(getSubTitle().toUpperCase(), false));
            PdfUtil.renderConstrainedText(content, getSubTitle().toUpperCase(), subFont, getX(), top, maxWidth);
        }
        if( getDescription() != null && !getDescription().isEmpty()) {
            Font subFont = FontRegistry.getInstance().getFont(PdfFontDefinition.AlbumDescription);
            top -= PdfUtil.convertFromMillimeters(15.0f);
            float width = PdfUtil.convertFromMillimeters((configuration.getWidth() - configuration.getMarginLeft() - configuration.getMarginRight()) /2 );
            content.setFontAndSize(subFont.getBaseFont(), subFont.getSize());
            top += PdfUtil.renderConstrainedText(content, getDescription(), subFont, width + PdfUtil.convertFromMillimeters(configuration.getMarginLeft()), top, (int)(width * 0.7f));
        }
        if( !getItems().isEmpty()) {
            Font subFont = FontRegistry.getInstance().getFont(PdfFontDefinition.AlbumContents);
            top -= subFont.getCalculatedSize() + PdfUtil.convertFromMillimeters(6.0f);
            content.setFontAndSize(subFont.getBaseFont(), subFont.getSize());
            for(String s: getItems() ) {
                maxWidth = Math.max(maxWidth, (int) subFont.getBaseFont().getWidthPoint(s, subFont.getSize()));
                PdfUtil.renderConstrainedText(content, s, subFont, getX(), top, maxWidth);
                top -= PdfUtil.convertFromMillimeters(3.0f);
            }
        }
        content.setHorizontalScaling(100.0f);
        
        OutputBounds rect = new OutputBounds(getX() - maxWidth / 2, getY(), maxWidth, getY() - top);
        return rect;
    }

    public String getTitle() {
        return title;
    }

    public Image getImage() {
        return image;
    }

    public String getSubTitle() {
        return subTitle;
    }

    public String getDescription() {
        return description;
    }

    public List<String> getItems() {
        return items;
    }

    public void setDescription(String description) {
        this.description = description;
    }

    public void setImage(Image image) {
        this.image = image;
    }

    public void setItems(List<String> items) {
        this.items = items;
    }

    public void setSubTitle(String subTitle) {
        this.subTitle = subTitle;
    }

    public void setTitle(String title) {
        this.title = title;
    }
    
    
}
