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

import com.itextpdf.text.BaseColor;
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
import org.javad.pdf.fonts.FontRegistry;
import org.javad.pdf.fonts.PdfFontDefinition;
import org.javad.pdf.model.PageConfiguration;
import org.javad.pdf.util.PdfUtil;

public class StampSet extends PositionalContent implements ISetContent {

    private String issue;
    private String description;
    private String descriptionSecondary;
    private String comment;
    List<ISetContent> rows = new ArrayList<>();
    private float verticalPadding = 4.0f;

    public StampSet(PageConfiguration configuration) {
        super(configuration);
        verticalPadding = configuration.getVerticalSpacing();
    }

    public boolean isTextOnly() {
        return rows.isEmpty();
    }

    public String getIssue() {
        return issue;
    }

    public void setIssue(String issue) {
        this.issue = issue;
    }

    public String getDescription() {
        return description;
    }

    public void setDescription(String description) {
        this.description = (description != null) ? description.replace("\\n", "\n") : null;
    }

    public String getDescriptionSecondary() {
        return descriptionSecondary;
    }

    public void setDescriptionSecondary(String descriptionSecondary) {
        this.descriptionSecondary = (descriptionSecondary !=null ) ?  descriptionSecondary.replace("\\n", "\n") : null;
    }

    public String getComment() {
        return comment;
    }

    public void setComment(String comment) {
        this.comment = (comment != null) ? comment.replace("\\n", "\n") : null;
    }

    public void addContentRow(ISetContent row) {
        rows.add(row);
    }

    public List<ISetContent> getContentRows() {
        return rows;
    }

    @Override
    public OutputBounds generate(PdfContentByte content) {
        float maxWidth = 0;
        content.setColorStroke(BaseColor.BLACK);

        float top = getY();
        if (getIssue() != null && !getIssue().isEmpty()) {
            top -= PdfUtil.convertFromMillimeters(5.0f);
            Font f = FontRegistry.getInstance().getFont(PdfFontDefinition.SetIssue);
            content.setFontAndSize(f.getBaseFont(), f.getSize());
            String is = getIssue().replace("\\n", "\n");
            StringTokenizer tokenizer = new StringTokenizer(is, "\n", true);
            while(tokenizer.hasMoreTokens()) {
                is = tokenizer.nextToken();
                maxWidth = Math.max(maxWidth, content.getEffectiveStringWidth(is, false));
                if( is.equals("\n")) {
                    top -= f.getCalculatedSize() + 2;
                } else {
                    PdfUtil.renderConstrainedText(content, is, f, getX(), top, (int)maxWidth);
                    if( tokenizer.hasMoreTokens()) {
                        top -= f.getCalculatedSize() + 2;
                    }
                }
                
            }
            top -= PdfUtil.convertFromMillimeters(3.0f);
        }
        if (getDescription() != null && !getDescription().isEmpty()) {
            Font descFont = FontRegistry.getInstance().getFont(PdfFontDefinition.SetDescription);
            content.setFontAndSize(descFont.getBaseFont(), descFont.getSize());
            top -= descFont.getCalculatedSize();
            int count = 0;
            int tc = getDescription().split("\n").length;
            for (String desc : getDescription().split("\n")) {
                maxWidth = Math.max(maxWidth, content.getEffectiveStringWidth(desc, false));
                PdfUtil.renderConstrainedText(content, desc, descFont, getX(), top, (int)maxWidth);
                count++;
                if (count < tc) {
                    top -= descFont.getCalculatedSize() + 2;
                }
                
            }
        }
        if (getDescriptionSecondary() != null && !getDescriptionSecondary().isEmpty()) {
            Font secFont = FontRegistry.getInstance().getFont(PdfFontDefinition.SetDescriptionSecondary);
            content.setFontAndSize(secFont.getBaseFont(), secFont.getSize());
            top -= secFont.getCalculatedSize() + PdfUtil.convertFromMillimeters(3.0f);
            int count = 0;
            int tc = getDescriptionSecondary().split("\n").length;
            for (String desc : getDescriptionSecondary().split("\n")) {
                maxWidth = Math.max(maxWidth, content.getEffectiveStringWidth(desc, false));
                PdfUtil.renderConstrainedText(content, desc, secFont, getX(), top, (int)maxWidth);
                count++;
                if (count < tc) {
                    top -= secFont.getCalculatedSize() + 2;
                }

            }
        }
        
        if (!rows.isEmpty()) {
            top -= ((top != getY()) ? PdfUtil.convertFromMillimeters(3.0f) : 0);
            for (int i = 0; i < rows.size(); i++) {
                ISetContent row = rows.get(i);
                if (row instanceof CompositeRow) {
                    row.setX(getX());
                } else {
                    row.setX(getX());
                }
                row.setY(top);
                OutputBounds bounds = row.generate(content);
                top -= ((i < rows.size() - 1) ? (PdfUtil.convertFromMillimeters(verticalPadding)) : 0.0f) + bounds.height;
                maxWidth = Math.max(maxWidth, bounds.width);
            }
        }
        if (getComment() != null && !getComment().isEmpty()) {
            
            top -= PdfUtil.convertFromMillimeters((int)(0.75 * verticalPadding));
            Font cFont = FontRegistry.getInstance().getFont(PdfFontDefinition.SetComment);
            content.setFontAndSize(cFont.getBaseFont(), cFont.getSize());
            for (String s : getComment().split("\n")) {
                top -= cFont.getCalculatedSize();
                maxWidth = Math.max(maxWidth, content.getEffectiveStringWidth(s, false));
                PdfUtil.renderConstrainedText(content, s, cFont, getX(), top, (int)maxWidth);
            }
           
        }

        OutputBounds rect = new OutputBounds(getX() - maxWidth / 2, getY(), maxWidth, getY() - top);
        return rect;
    }

    @Override
    public void writeToXml(XMLStreamWriter writer) throws XMLStreamException {
        writer.writeStartElement("set");
        if (issue != null) {
            writer.writeAttribute("issue", issue);
        }
        if (description != null) {
            writer.writeAttribute("description", description);
        }
        if (descriptionSecondary != null) {
            writer.writeAttribute("description-secondary", descriptionSecondary);
        }
        if (comment != null) {
            writer.writeAttribute("comment", comment);
        }
        for(ISetContent row: rows) {
            row.writeToXml(writer);
        }
        writer.writeEndElement();
        writer.flush();
    }

}
