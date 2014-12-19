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

import java.util.ArrayList;
import java.util.List;

import org.javad.pdf.ISetContent;
import org.javad.pdf.OutputBounds;
import org.javad.pdf.PositionalContent;
import org.javad.pdf.VerticalAlignment;
import org.javad.pdf.fonts.FontRegistry;
import org.javad.pdf.fonts.PdfFontDefinition;
import org.javad.pdf.model.PageConfiguration;
import org.javad.pdf.util.PdfUtil;

import com.itextpdf.text.BaseColor;
import com.itextpdf.text.Font;
import com.itextpdf.text.pdf.PdfContentByte;
import javax.xml.stream.XMLStreamException;
import javax.xml.stream.XMLStreamWriter;

public class StampRow extends PositionalContent implements ISetContent {

    String description;
    List<IStampContent> stampContents = new ArrayList<>();
    VerticalAlignment valign = VerticalAlignment.top;

    private float padding;

    public StampRow(PageConfiguration configuration) {
        super(configuration);
        padding = configuration.getHorizontalSpacing();
    }

    @Override
    public boolean isTextOnly() {
        return stampContents.isEmpty();
    }

    public String getDescription() {
        return description;
    }

    public void setDescription(String rowText) {
        this.description = rowText.replace("\\n", "\n");
    }

    public float getHorizontalPadding() {
        return padding;
    }

    public void setHorizontalPadding(float padding) {
        this.padding = padding;
    }

    public VerticalAlignment getValign() {
        return valign;
    }

    public void setValign(VerticalAlignment valign) {
        this.valign = valign;
    }

    public void addStampContent(IStampContent box) {
        stampContents.add(box);
    }

    public int size() {
        return stampContents.size();
    }

    public List<IStampContent> getStampContent() {
        return stampContents;
    }

    @Override
    public OutputBounds generate(PdfContentByte content) {
        if (isSkipped()) {
            return new OutputBounds(getX(), getY(), 0, 0);
        }
        float maxWidth = 0;
        float top = getY();
        if (getDescription() != null && !getDescription().isEmpty()) {
            content.setColorStroke(BaseColor.BLACK);
            Font descFont = FontRegistry.getInstance().getFont(PdfFontDefinition.RowDescription);
            content.setFontAndSize(descFont.getBaseFont(), descFont.getSize());
            top -= descFont.getCalculatedSize();
            int count = 0;
            int tc = getDescription().split("\n").length;
            for (String desc : getDescription().split("\n")) {
                maxWidth = Math.max(maxWidth, (int) descFont.getBaseFont().getWidthPoint(desc, descFont.getSize()));
                PdfUtil.renderConstrainedText(content, desc, descFont, getX(), top, (int) (maxWidth * 1.10));
                count++;
                top -= descFont.getCalculatedSize() + ((count < tc) ? 2 : 4);

            }
        }
        float totalWidth = 0;
        int maxHeight = 0;
        int count = 0;
        for (int i = 0; i < stampContents.size(); i++) {
            if( stampContents.get(i).isSkipped() ) {
                continue;
            }
            
            totalWidth += stampContents.get(i).getWidth() + stampContents.get(i).getPadding();
            if (count > 0) {
                totalWidth += padding;
            }
            count++;
            maxHeight = Math.max(maxHeight, stampContents.get(i).getHeight());
        }
        totalWidth = PdfUtil.convertFromMillimeters(totalWidth);
        float start_x = getX() - (totalWidth / 2.0f);
        float cur_x = start_x;
        float totalHeight = getY() - top;
        float deltaHeight = totalHeight;
        count = 0;
        for (IStampContent s : stampContents) {
            if( s.isSkipped()) {
                continue;
            }
            if( count > 0 ) {
                cur_x += PdfUtil.convertFromMillimeters(padding);
            }
            s.setX(cur_x);
            int delta_y = getVerticalAlignmentOffset(s, maxHeight);
            s.setY(top - PdfUtil.convertFromMillimeters(delta_y));
            OutputBounds r = s.generate(content);
            totalHeight = Math.max(r.height + deltaHeight, totalHeight);
            cur_x += r.width;
            count++;
        }
        maxWidth = (int) Math.max(maxWidth, totalWidth);
        return new OutputBounds(start_x, getY(), maxWidth, totalHeight);
    }

    /**
     * Determine the offset to use for the vertical alignment of the stamp row.
     *
     * @param s
     * @param maxHeight
     * @return
     */
    protected int getVerticalAlignmentOffset(IStampContent s, int maxHeight) {
        int delta_y = 0;
        switch (valign) {
            case top:
                delta_y = s.getHeight() + s.getVerticalPadding();
                break;
            case middle:
                delta_y = s.getHeight() + s.getVerticalPadding() + ((maxHeight - s.getHeight()) / 2);
                break;
            case bottom:
                delta_y = maxHeight + s.getVerticalPadding();
                break;
        }
        return delta_y;
    }

    @Override
    public void writeToXml(XMLStreamWriter writer) throws XMLStreamException {
        writer.writeStartElement("row-set");
        if (description != null) {
            writer.writeAttribute("description", description);
        }
        if (valign != VerticalAlignment.top) {
            writer.writeAttribute("valign", valign.toString());
        }
        for (IStampContent row : stampContents) {
            row.writeToXml(writer);
        }
        writer.writeEndElement();
        writer.flush();
    }

}
