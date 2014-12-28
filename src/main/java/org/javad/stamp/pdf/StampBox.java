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
package org.javad.stamp.pdf;

import java.awt.Color;
import java.awt.Image;
import java.util.logging.Level;
import java.util.logging.Logger;

import org.javad.pdf.OutputBounds;
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

public class StampBox extends AbstractStampContent implements XMLSerializable {

    private static final Logger logger = Logger.getLogger(StampBox.class.getName());

    private static final int TEXT_GAP = 5;

    private String denomination;
    private String description;
    private String descriptionSecondary;
    private String catalogueNumber;

    private Image image;
    private boolean imageOnly = false;
    private boolean border = true;
    private SetTenantPosition setTenantPosition = null;
    private Bisect bisect = Bisect.none;
    private Shape shape = Shape.rectangle;

    private float textPadding = 0;

    public StampBox(PageConfiguration configuration) {
        super(configuration);
    }

    public boolean isImageOnly() {
        return imageOnly;
    }

    public void setImageOnly(boolean imgOnly) {
        imageOnly = imgOnly;
    }
    
    public boolean isBorder() {
        return border;
    }
    
    public void setBorder(boolean border) {
        this.border = border;
    }

    public void setSetTenantPosition(SetTenantPosition position) {
        setTenantPosition = position;
    }

    public SetTenantPosition getSetTenantPosition() {
        return setTenantPosition;
    }

    public String getDenomination() {
        return denomination;
    }

    public Shape getShape() {
        return shape;
    }

    public void setShape(Shape shape) {
        this.shape = shape;
    }

    public float getTextPadding() {
        return textPadding;
    }

    public void setTextPadding(float padding) {
        this.textPadding = padding;
    }

    public Bisect getBisect() {
        return bisect;
    }

    public void setBisect(Bisect b) {
        this.bisect = b;
    }

    public void setDenomination(String denomination) {
        this.denomination = denomination;
    }

    public void setImage(Image img) {
        image = img;
    }

    public Image getImage() {
        return image;
    }

    public String getDescription() {
        return description;
    }

    public void setDescription(String description) {
        this.description = description;
    }

    public String getDescriptionSecondary() {
        return descriptionSecondary;
    }

    public void setDescriptionSecondary(String descriptionSecondary) {
        this.descriptionSecondary = descriptionSecondary;
    }

    public String getCatalogueNumber() {
        return catalogueNumber;
    }

    public void setCatalogueNumber(String catalogueNumber) {
        this.catalogueNumber = catalogueNumber;
    }

    @Override
    public OutputBounds generate(PdfContentByte content) {
        if( isSkipped()) {
            return new OutputBounds(getX(),getY(),0,0);
        }
        OutputBounds rect = new OutputBounds(getX(), getY(),
                PdfUtil.convertFromMillimeters(getWidth() + getPadding()), PdfUtil.convertFromMillimeters(getHeight() + getVerticalPadding()));
        if (bisect != Bisect.none && isBorder()) {
            drawBisect(content, rect);
        }
        if (getSetTenantPosition() == null) {
            drawShape(content, rect);
        }

        float verticalPadding = PdfUtil.convertFromMillimeters(getVerticalPadding());
        float w = rect.width;
        Font f = FontRegistry.getInstance().getFont(PdfFontDefinition.Stampbox);
        float center = getX() + w / 2;
        float top = getY() + verticalPadding + f.getCalculatedSize() * 6 + PdfUtil.convertFromMillimeters(getTextPadding());

        if (image != null) {
            try {
                com.itextpdf.text.Image img = determineScaledImage(rect, f.getCalculatedSize(), top, isImageOnly());
                if (img != null) {
                    content.addImage(img);
                }
            } catch (Exception e) {
                logger.log(Level.FINER, "An error occured scaling the image. ", e);
            }
        }
        if (!isImageOnly()) {
            if( shape == Shape.diamond || shape == Shape.triangleInverted) {
                top = getY() + rect.height/2.0f + f.getCalculatedSize() * 1.5f;   
            }
            top += PdfUtil.renderConstrainedText(content, getDenomination(), f, center, top, getWidth());
            top -= f.getCalculatedSize() + 1;
            float d_delta = PdfUtil.renderConstrainedText(content, getDescription(), f, center, top, getWidth());
            float rows = (float)Math.ceil(d_delta / f.getCalculatedSize());
            top += d_delta;
            Font f2 = FontRegistry.getInstance().getFont(PdfFontDefinition.StampboxOther);
            float delta = PdfUtil.renderConstrainedText(content, getDescriptionSecondary(), f2, center, top, getWidth());
            if (delta < 1.0f && rows > -3.00) {
                delta = -1 * (f.getSize() + 1);
            }
            if (d_delta >= -1 * (f.getSize() + 1)) { // handle one line descriptions
                top -= f.getSize() + 1;
            }
            top += delta;
            PdfUtil.renderConstrainedText(content, getCatalogueNumber(), f, center, top, getWidth());
        }
        return rect;
    }

    /**
     * Will draw a black frame shape for a given stamp box. The current
     * supported shapes include
     * <ul><li>rectangle</li>
     * <li>triangle</li>
     * <li>diamond</li>
     * </ul>
     *
     * @param content
     * @param rect
     */
    void drawShape(PdfContentByte content, OutputBounds rect) {
        
        content.setColorFill(BaseColor.WHITE);
        drawPath(content,rect);
        content.fill();
        if ( isBorder() ) {
            content.setColorStroke(BaseColor.BLACK);
            content.setLineWidth(0.8f);
            drawPath(content, rect);
            content.stroke();
        }
        content.setColorFill(BaseColor.BLACK);
    }
    
    private void drawPath(PdfContentByte content, OutputBounds rect) {
        switch (shape) {
            case rectangle:
                content.rectangle(rect.x, rect.y, rect.width, rect.height);
                break;
            case triangle:
                // calculation of delta x based on triangle and cosine dimensions
                //float delta_x = (getPadding() / 2.0f) * (rect.width / 2.0f) / (float) Math.sqrt(Math.pow(rect.height, 2.0) + Math.pow(rect.width / 2.0, 2.0));
                content.moveTo(rect.x, rect.y);
                content.lineTo(rect.x + rect.width, rect.y);
                content.lineTo(rect.x + rect.width / 2.0f, rect.y + rect.height);
                content.lineTo(rect.x, rect.y);
                break;
            case triangleInverted:
                content.moveTo(rect.x + rect.width / 2.0f, rect.y);
                content.lineTo(rect.x + rect.width, rect.y + rect.height);
                content.lineTo(rect.x, rect.y + rect.height);
                content.lineTo(rect.x + rect.width / 2.0f, rect.y);
                break;
            case diamond:
                content.moveTo(rect.x, rect.y + rect.height / 2.0f);
                content.lineTo(rect.x + rect.width / 2.0f, rect.y);
                content.lineTo(rect.x + rect.width, rect.y + rect.height / 2.0f);
                content.lineTo(rect.x + rect.width / 2.0f, rect.y + rect.height);
                content.lineTo(rect.x, rect.y + rect.height / 2.0f);
                break;
        }
    }

    /**
     * Will draw the bisect lines within the content are of the output
     * rectangle.
     *
     * @param content
     * @param rect
     */
    @SuppressWarnings("incomplete-switch")
    void drawBisect(PdfContentByte content, OutputBounds rect) {
        content.setLineWidth(0.5f);
        content.setColorStroke(BaseColor.GRAY);
        float dx1 = 0.0f;
        float dx2 = 0.0f;
        float dy1 = 0.0f;
        float dy2 = 0.0f;
        float xp = (int) PdfUtil.convertFromMillimeters(getPadding() + 2);
        float yp = (int) PdfUtil.convertFromMillimeters(getVerticalPadding() + 2);
        switch (bisect) {
            case top_left:
                dx1 = xp;
                dy1 = rect.height - yp;
                dx2 = rect.width - xp;
                dy2 = yp;
                break;
            case top_right:
                dx1 = xp;
                dy1 = yp;
                dx2 = rect.width - xp;
                dy2 = rect.height - yp;
                break;
            case vertical:
                dx1 = rect.width / 2;
                dy1 = yp;
                dx2 = dx1;
                dy2 = rect.height - yp;
        }
        content.moveTo(rect.x + dx1, rect.y + dy1);
        content.setLineDash(5.0f, 2.0f, 0.0f);
        content.lineTo(rect.x + dx2, rect.y + dy2);
        content.stroke();
        content.setLineDash(1.0f, 0.0f, 0.0f);
    }

    /**
     * Convert the image into a scaled image that will fit in the remaining size
     * of the rectangular box.
     *
     * @param rect
     * @param fontSize
     * @param top
     * @return
     * @throws Exception
     */
    protected com.itextpdf.text.Image determineScaledImage(OutputBounds rect, float fontSize, float top, boolean onlyImage) throws Exception {
        com.itextpdf.text.Image img = com.itextpdf.text.Image.getInstance(image, Color.BLACK);
        float vGap = rect.y + rect.height - ((onlyImage) ? 0 : (top + fontSize + TEXT_GAP)); // top + fontSize + TEXT_GAP - getY();
        float hGap = rect.width;
        float vRatio = img.getHeight() * 1.4f / vGap;
        float hRatio = img.getWidth() * 1.2f / hGap;
        float ratio = Math.max(1.0f, Math.max(vRatio, hRatio));
        img.scaleAbsolute(img.getWidth() / ratio, img.getHeight() / ratio);
        float deltaH = rect.getHeight() - img.getScaledHeight();
        img.setAbsolutePosition(rect.getX() + (rect.getWidth() - (img.getWidth() / ratio)) / 2, (!onlyImage) ? (top + fontSize + TEXT_GAP) : (rect.y + (deltaH / 2.0f)));
        return img;
    }

    @Override
    public void writeToXml(XMLStreamWriter writer) throws XMLStreamException {
        writer.writeStartElement("s");
        StringBuilder buf = new StringBuilder();
        buf.append("\"").append(width).append(" ").append(height).append("\" \"" + ((denomination != null) ? denomination : "") + "\" \"");
        buf.append(((description != null) ? description : "")).append("\" \"");
        buf.append((( descriptionSecondary != null) ? descriptionSecondary : "")).append("\" \"");
        buf.append((( catalogueNumber != null) ? catalogueNumber : "") +"\"");
        writer.writeCharacters(buf.toString());
        writer.writeEndElement();
        writer.flush();
    }

    public enum Shape {

        rectangle,
        triangle,
        triangleInverted,
        diamond;
    }

    public enum Bisect {

        none,
        vertical,
        top_left,
        top_right;
    }

    public enum SetTenantPosition {

        first,
        middle,
        last
    }
}
