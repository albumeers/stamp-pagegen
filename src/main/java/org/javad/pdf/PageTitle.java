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

import org.javad.pdf.fonts.FontRegistry;
import org.javad.pdf.fonts.PdfFontDefinition;
import org.javad.pdf.model.PageConfiguration;
import org.javad.pdf.util.PdfUtil;

import com.itextpdf.text.BaseColor;
import com.itextpdf.text.Font;
import com.itextpdf.text.pdf.PdfContentByte;
import javax.xml.stream.XMLStreamException;
import javax.xml.stream.XMLStreamWriter;
import org.javad.xml.XMLSerializable;

public class PageTitle extends PositionalContent implements XMLSerializable, IContentGenerator {

    public static final int DASH_LENGTH = 6;
    private String title;
    private String subTitle;
    private String classifier;

    public PageTitle(PageConfiguration configuration) {
        super(configuration);
    }

    public String getTitle() {
        return title;
    }

    public void setTitle(String title) {
        this.title = title;
    }

    public String getSubTitle() {
        return subTitle;
    }

    public void setSubTitle(String subTitle) {
        this.subTitle = subTitle;
    }

    public String getClassifier() {
        return classifier;
    }

    public void setClassifier(String classifier) {
        this.classifier = classifier;
    }

    @Override
    public OutputBounds generate(PdfContentByte content) {
        int maxWidth = 0;
        content.setColorStroke(BaseColor.BLACK);
        Font f = FontRegistry.getInstance().getFont(PdfFontDefinition.Title);
        content.setFontAndSize(f.getBaseFont(), f.getSize());
        float top = getY();
        content.setHorizontalScaling(110.0f);
        
        if(getTitle() != null && !getTitle().isEmpty()) {
            String[] _title = PdfUtil.toUpperCase(getTitle()).split("\n");
            int t_count = 0;
            for (String theTitle : _title) {
                 maxWidth = (int) f.getBaseFont().getWidthPoint(theTitle, f.getSize());
                 PdfUtil.renderConstrainedText(content, theTitle, f, getX(),top, (int) (maxWidth * 1.1));
                 top -= ((++t_count < _title.length) ? (f.getCalculatedSize() + 2) : 0);
            }
        }
        if (getSubTitle() != null && !getSubTitle().isEmpty()) {
            Font subFont = FontRegistry.getInstance().getFont(PdfFontDefinition.Subtitle);
            top -= subFont.getCalculatedSize() + PdfUtil.convertFromMillimeters(3.0f);
            content.setFontAndSize(subFont.getBaseFont(), subFont.getSize());
            String[] _subtitle = PdfUtil.toUpperCase(getSubTitle()).split("\n");
            int count = 0;
            for (String sTitle : _subtitle) {
                maxWidth = Math.max(maxWidth, (int) subFont.getBaseFont().getWidthPoint(sTitle, subFont.getSize()));
                PdfUtil.renderConstrainedText(content, sTitle, subFont, getX(), top, (int) (maxWidth * 1.10));
                top -= ((++count < _subtitle.length) ? subFont.getCalculatedSize() + 2 : 0);
            }
        }
        content.setHorizontalScaling(100.0f);
        if (getClassifier() != null && !getClassifier().isEmpty()) {
            Font classFont = FontRegistry.getInstance().getFont(PdfFontDefinition.Classifier);
            content.setFontAndSize(classFont.getBaseFont(), classFont.getSize());
            top -= classFont.getCalculatedSize() + PdfUtil.convertFromMillimeters(3.0f);
            float width = classFont.getBaseFont().getWidthPoint(getClassifier(), classFont.getCalculatedSize()) + 4;
            maxWidth = Math.max(maxWidth, (int) width + (2 * DASH_LENGTH));
            content.setLineWidth(0.8f);
            float lineTop = top + ((int) classFont.getSize() / 2 - 1);
            content.moveTo(getX() - (width / 2) - DASH_LENGTH, lineTop);
            content.lineTo(getX() - (width / 2), lineTop);
            content.moveTo(getX() + (width / 2), lineTop);
            content.lineTo(getX() + (width / 2) + DASH_LENGTH, lineTop);
            content.stroke();
            PdfUtil.renderConstrainedText(content,getClassifier(), classFont, getX(),top, (int) (maxWidth * 1.10));
        }
        OutputBounds rect = new OutputBounds(getX() - maxWidth / 2, getY(), maxWidth, getY() - top);
        return rect;
    }

    @Override
    public String toString() {
        StringBuilder buf = new StringBuilder();
        buf.append("title:      ").append( title );
        if( subTitle != null ) {
            buf.append("\nsubtitle:   ").append( subTitle);
        }
        if( classifier != null ) {
            buf.append("\nclassifier: ").append( classifier );
        }
        return buf.toString();
    }

    
    @Override
    public void writeToXml(XMLStreamWriter writer) throws XMLStreamException {
        if( getTitle() != null ) {
            writer.writeAttribute("title", getTitle());
        }
        if (getSubTitle() != null) {
            writer.writeAttribute("subtitle", getSubTitle());
        }
        if (getClassifier() != null) {
            writer.writeAttribute("classifier", getClassifier());
        }
    }

}
