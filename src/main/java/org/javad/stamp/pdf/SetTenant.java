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

import java.util.ArrayList;
import java.util.List;

import org.javad.pdf.OutputBounds;
import org.javad.pdf.model.PageConfiguration;
import org.javad.pdf.util.PdfUtil;
import org.javad.stamp.pdf.StampBox.SetTenantPosition;

import com.itextpdf.text.BaseColor;
import com.itextpdf.text.pdf.PdfContentByte;
import javax.xml.stream.XMLStreamException;
import javax.xml.stream.XMLStreamWriter;

public class SetTenant extends AbstractStampContent implements IStampContent {

    private final List<StampBox> stamps = new ArrayList<>();
    private Orientation orientation = Orientation.HORIZONTAL;
    private boolean border = true;

    public SetTenant(PageConfiguration configuration) {
        super(configuration);
    }

    public boolean isBorder() {
        return border;
    }

    public void setBorder(boolean b) {
        border = b;
    }

    public void addStamp(StampBox box) {
        stamps.add(box);
    }

    public void setOrientation(Orientation orientation) {
        this.orientation = orientation;
    }

    public Orientation getOrientation() {
        return orientation;
    }

    @Override
    public int getWidth() {
        if (super.getWidth() == 0) {
            int totalWidth = 0;
            for (int i = 0; i < stamps.size(); i++) {
                switch (getOrientation()) {
                    case HORIZONTAL:
                        totalWidth += stamps.get(i).getWidth();
                        break;
                    case VERTICAL:
                        totalWidth = Math.max(totalWidth, stamps.get(i).getWidth());
                }
            }
            setWidth(totalWidth);
        }
        return super.getWidth();
    }

    @Override
    public int getHeight() {
        if (super.getHeight() == 0) {
            int totalHeight = 0;
            for (int i = 0; i < stamps.size(); i++) {
                switch (getOrientation()) {
                    case HORIZONTAL:
                        totalHeight = Math.max(totalHeight, stamps.get(i).getHeight());
                        break;
                    case VERTICAL:
                        totalHeight += stamps.get(i).getHeight();
                }
            }
            setHeight(totalHeight);
        }
        return super.getHeight();
    }

    @Override
    public OutputBounds generate(PdfContentByte contentByte) {
        if (isSkipped()) {
            return new OutputBounds(getX(), getY(), 0, 0);
        }
        float totalWidth = PdfUtil.convertFromMillimeters(getWidth() + getPadding());
        float totalHeight = PdfUtil.convertFromMillimeters(getHeight() + getVerticalPadding());
        OutputBounds rect = new OutputBounds(getX(), getY(), totalWidth, totalHeight);
        float cur_x = getX();
        float cur_y = getY();
        for (int i = stamps.size() - 1; i >= 0; i--) {
            StampBox s = stamps.get(i);
            s.setPadding(getCalculatedPadding(s, getOrientation(), false));
            s.setVerticalPadding(getCalculatedPadding(s, getOrientation(), true));
            s.setX(cur_x);
            s.setY(cur_y);
            s.setTextPadding((getOrientation() == Orientation.VERTICAL) ? 1.0f + getVerticalPadding() / 2.0f : 0f);
            OutputBounds bounds = s.generate(contentByte);
            cur_x += (getOrientation() == Orientation.HORIZONTAL) ? bounds.getWidth() : 0;
            cur_y += (getOrientation() == Orientation.VERTICAL) ? bounds.getHeight() : 0;
            if (i > 0) {
                if (isBorder()) {
                    drawSeparator(contentByte, cur_x, cur_y, totalWidth, totalHeight);
                }
            }
        }
        if (isBorder()) {
            drawBorder(contentByte, rect);
        }
        return rect;
    }

    protected void drawSeparator(PdfContentByte content, float x, float y, float width, float height) {

        float sx = (getOrientation() == Orientation.HORIZONTAL) ? x : x + PdfUtil.convertFromMillimeters(getPadding() + 2);
        float dx = (getOrientation() == Orientation.HORIZONTAL) ? x : x + width - PdfUtil.convertFromMillimeters(getPadding() + 2);
        float sy = (getOrientation() == Orientation.HORIZONTAL) ? y + PdfUtil.convertFromMillimeters(getVerticalPadding() + 2) : y;
        float dy = (getOrientation() == Orientation.HORIZONTAL) ? y + height - PdfUtil.convertFromMillimeters(getVerticalPadding() + 2) : y;

        content.setLineWidth(0.5f);
        content.setColorStroke(BaseColor.GRAY);
        content.moveTo(sx, sy);
        content.setLineDash(5.0f, 2.0f, 0.0f);
        content.lineTo(dx, dy);
        content.stroke();
        content.setLineDash(1.0f, 0.0f, 0.0f);
    }

    protected int getCalculatedPadding(StampBox box, Orientation orientation, boolean vertical) {
        int padding = 0;
        switch (orientation) {
            case HORIZONTAL:
                if (vertical) {
                    padding = getVerticalPadding();
                } else {
                    padding = (box.getSetTenantPosition() == SetTenantPosition.first || box.getSetTenantPosition() == SetTenantPosition.last) ? getPadding() / 2 : 0;
                }
                break;
            case VERTICAL:
                if (vertical) {
                    padding = (box.getSetTenantPosition() == SetTenantPosition.first || box.getSetTenantPosition() == SetTenantPosition.last) ? getVerticalPadding() / 2 : 0;
                } else {
                    padding = getPadding();
                }

                break;
        }
        return padding;
    }

    void drawBorder(PdfContentByte content, OutputBounds rect) {
        content.setColorStroke(BaseColor.BLACK);
        content.setLineWidth(0.8f);
        content.rectangle(rect.x, rect.y, rect.width, rect.height);
        content.stroke();
    }

    @Override
    public void writeToXml(XMLStreamWriter writer) throws XMLStreamException {
        throw new UnsupportedOperationException("Not supported yet."); //To change body of generated methods, choose Tools | Templates.
    }

    public enum Orientation {

        HORIZONTAL,
        VERTICAL;
    }
}
