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

import com.itextpdf.text.Font;
import com.itextpdf.text.pdf.PdfContentByte;
import java.util.ArrayList;
import java.util.List;
import java.util.StringTokenizer;
import javax.xml.stream.XMLStreamException;
import javax.xml.stream.XMLStreamWriter;
import org.javad.pdf.ISetContent;
import org.javad.pdf.OutputBounds;
import org.javad.pdf.PositionalContent;
import org.javad.pdf.SpacingMode;
import org.javad.pdf.fonts.FontRegistry;
import org.javad.pdf.fonts.PdfFontDefinition;
import org.javad.pdf.model.PageConfiguration;
import org.javad.pdf.util.PdfUtil;

public class ColumnSet extends PositionalContent implements ISetContent {

    private float box_spacing = 4.0f;
    private SpacingMode spacingMode = SpacingMode.high;
    private String issue;
    private List<StampSet> columns = new ArrayList<StampSet>();

    public ColumnSet(PageConfiguration configuration) {
        super(configuration);
        box_spacing = configuration.getHorizontalSpacing();
    }

    public String getIssue() {
        return issue;
    }

    public void setIssue(String issue) {
        this.issue = issue;
    }

    public void addStampSet(StampSet set) {
        columns.add(set);
    }

    @Override
    public boolean isTextOnly() {
        return columns.isEmpty();
    }

    public void setSpacingMode(SpacingMode mode) {
        spacingMode = mode;
    }

    public SpacingMode getSpacingMode() {
        return spacingMode;
    }

    @Override
    public OutputBounds generate(PdfContentByte content) {
        if (isSkipped()) {
            return new OutputBounds(getX(), getY(), 0, 0);
        }
        float totalWidth = 0.0f;
        float maxHeight = 0.0f;
        float cur_x = getX();
        float top = getY();
        if (getIssue() != null && !getIssue().isEmpty()) {
            top -= PdfUtil.convertFromMillimeters(5.0f);
            Font f = FontRegistry.getInstance().getFont(PdfFontDefinition.SetIssue);

            content.setFontAndSize(f.getBaseFont(), f.getSize());
            String is = getIssue().replace("\\n", "\n");
            StringTokenizer tokenizer = new StringTokenizer(is, "\n", true);
            float x = PdfUtil.convertFromMillimeters(configuration.getUsableWidth() / 2 + configuration.getMarginLeft());
            while (tokenizer.hasMoreTokens()) {
                is = tokenizer.nextToken();
                if (is.equals("\n")) {
                    top -= f.getCalculatedSize() + 2;
                } else {
                    PdfUtil.renderConstrainedText(content, is, f, x, top, (int) PdfUtil.convertFromMillimeters(configuration.getUsableWidth()));
                    if (tokenizer.hasMoreTokens()) {
                        top -= f.getCalculatedSize() + 2;
                    }
                }
            }

            top -= PdfUtil.convertFromMillimeters(3.0f);
        }
        float spacing = PdfUtil.convertFromMillimeters(getSpacingMode().getSpacing(box_spacing));
        int count = 0;
        for (int i = 0; i < columns.size(); i++) {
            StampSet set = columns.get(i);
            if( set.isSkipped()) {
                continue;
            }
            float s_w = PdfUtil.findMaximumWidth(set, content);
            set.setX(cur_x + s_w / 2);
            set.setY(top);
            OutputBounds rect = set.generate(content);

            totalWidth += rect.width + ((count > 0) ? spacing : 0.0f);
            cur_x += rect.width + spacing;
            maxHeight = Math.max(maxHeight, rect.height);
            count++;
        }
        return new OutputBounds(getX() - (totalWidth / 2.0f), getY(), totalWidth, maxHeight + (getY() - top));
    }

    @Override
    public void writeToXml(XMLStreamWriter writer) throws XMLStreamException {
        writer.writeStartElement("column-set");
        for (StampSet row : columns) {
            row.writeToXml(writer);
        }
        writer.writeEndElement();
        writer.flush();
    }

}
