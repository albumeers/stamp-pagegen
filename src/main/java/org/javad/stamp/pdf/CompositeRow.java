/*
 Copyright 2023 Jason Drake (jadrake75@gmail.com)
 
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
import org.javad.pdf.fonts.FontRegistry;
import org.javad.pdf.fonts.PdfFontDefinition;
import org.javad.pdf.model.PageConfiguration;
import org.javad.pdf.util.PdfUtil;

import com.itextpdf.text.BaseColor;
import com.itextpdf.text.Font;
import com.itextpdf.text.pdf.PdfContentByte;
import javax.xml.stream.XMLStreamException;
import javax.xml.stream.XMLStreamWriter;
import org.javad.pdf.SpacingMode;

public class CompositeRow extends PositionalContent implements ISetContent {

    private String description;
    private float box_spacing = 4.0f;
    private float verticalOffset = 0.0f;
    private SpacingMode spacingMode = SpacingMode.high;

    List<StampRow> rows = new ArrayList<>();

    public CompositeRow(PageConfiguration configuration) {
        super(configuration);
        box_spacing = configuration.getHorizontalSpacing();
    }

    @Override
    public boolean isTextOnly() {
        return rows.isEmpty();
    }

    public void setSpacingMode(SpacingMode mode) {
        spacingMode = mode;
    }

    public SpacingMode getSpacingMode() {
        return spacingMode;
    }

    public void addStampRow(StampRow row) {
        rows.add(row);
    }

    public String getDescription() {
        return description;
    }

    public void setDescription(String rowText) {
        this.description = rowText.replace("\\n", "\n");
    }

    public float getVerticalOffset() {
		return verticalOffset;
	}

	public void setVerticalOffset(float verticalOffset) {
		this.verticalOffset = verticalOffset;
	}

	@Override
    public OutputBounds generate(PdfContentByte content) {
        if (isSkipped()) {
            return new OutputBounds(getX(), getY(), 0, 0);
        }
        float maxHeight = 0.0f;
        float maxWidth = 0.0f;
        float top = getY() - PdfUtil.convertFromMillimeters(getVerticalOffset());

        if (getDescription() != null && !getDescription().isEmpty()) {
            content.setColorStroke(BaseColor.BLACK);
            Font descFont = FontRegistry.getInstance().getFont(PdfFontDefinition.CompositeSetDescription);
            content.setFontAndSize(descFont.getBaseFont(), descFont.getSize());
            top -= descFont.getCalculatedSize();
            int count = 0;
            int tc = getDescription().split("\n").length;
            for (String desc : getDescription().split("\n")) {
                maxWidth = Math.max(maxWidth, content.getEffectiveStringWidth(desc, false));
                PdfUtil.renderConstrainedText(content, desc, descFont, getX(), top, (int) maxWidth);
                count++;
                top -= descFont.getCalculatedSize() + ((count < tc) ? 2 : 4);
            }
        }

        float totalWidth = 0.0f;
        float totalHeight = getY() - top;
        float spacing = PdfUtil.convertFromMillimeters(getSpacingMode().getSpacing(box_spacing));
        int count = 0;
        for (int i = 0; i < rows.size(); i++) {
            StampRow set = rows.get(i);
            if( set.isSkipped()) {
                continue;
            }
            totalWidth += PdfUtil.findMaximumWidth(set, content) + ((count > 0) ? spacing : 0.0f);
            count++;
        }
        float cur_x = getX() - totalWidth / 2.0f;
        count = 0;
        for (StampRow set : rows) {
            if( set.isSkipped()) {
                continue;
            }
            set.setX(cur_x + PdfUtil.findMaximumWidth(set, content) / 2.0f);
            set.setY(top);
            OutputBounds rect = set.generate(content);
            count ++;
            cur_x += rect.width + ((count > 0 ) ? spacing :0 );
            maxHeight = Math.max(maxHeight, rect.height);
            
        }
        maxWidth = Math.max(maxWidth, totalWidth);
        totalHeight += maxHeight;
        return new OutputBounds(getX() - (maxWidth / 2.0f), getY(), maxWidth, totalHeight);
    }

    @Override
    public void writeToXml(XMLStreamWriter writer) throws XMLStreamException {
        throw new UnsupportedOperationException("Not supported yet."); //To change body of generated methods, choose Tools | Templates.
    }
}
