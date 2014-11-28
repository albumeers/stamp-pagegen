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
package org.javad.stamp.htmlparser.msword;

import org.htmlparser.Node;
import org.htmlparser.nodes.TagNode;
import org.htmlparser.tags.Span;
import org.htmlparser.util.NodeList;
import org.javad.pdf.ISetContent;
import org.javad.stamp.htmlparser.HtmlHelper;
import org.javad.stamp.htmlparser.msword.styles.PageStyle;
import org.javad.stamp.pdf.StampBox;
import org.javad.stamp.pdf.StampRow;

/**
 *
 * @author Jason
 */
public class StampRowProcessor extends AbstractProcessor<ISetContent> {
 
    public StampRowProcessor(PageStyle style) {
        super(style);
        mapper = ColorMapper.getInstance();
    }

    public static int W_PADDING = 4;
    public static int V_PADDING = 5;
 
    ColorMapper mapper;
            
    @Override
    public ISetContent process(Node stampSet, Node page) {
        StampRow rowSet = new StampRow(getPageConfiguration());
        NodeList boxes = getNodeListProcessor().findChildrenByTagName(stampSet, "TD");
        for(int i = 0; i < boxes.size(); i++ ) {
            Node n = boxes.elementAt(i);
            if( n instanceof TagNode ) {
                TagNode bNode = (TagNode)n;
                String style = bNode.getAttribute("style");
                String border = HtmlHelper.extractValueFromStyle(style, "border");
                String borderRight = HtmlHelper.extractValueFromStyle(style, "border-right");
                if( (border == null && borderRight == null) || 
                        (border != null && border.equals("none") && borderRight != null) ||
                        (borderRight != null && borderRight.equals("none") && border != null)) {
                    continue;
                }
                StampBox box = new StampBox(getPageConfiguration());
                String width = HtmlHelper.extractValueFromStyle(style, "width");
                float f_w = HtmlHelper.convertToNumber(width);
                if( f_w < 0.0f) {
                    continue;
                } else {
                    box.setWidth((int)Math.ceil(f_w) - W_PADDING);
                }
                String height = HtmlHelper.extractValueFromStyle(style, "height");
                float f_h = HtmlHelper.convertToNumber(height);
                if( f_h < 0.0f) {
                    continue;
                } else {
                    box.setHeight((int)Math.floor(f_h) - V_PADDING);
                }
                NodeList textList = getNodeListProcessor().findChildrenByTagName(bNode, "SPAN");
                if( textList != null && textList.size() > 0 ) {
                    StringBuilder textBuf = new StringBuilder();
                    Node parent = null;
                    for(int j = 0; j < textList.size(); j++ ) {
                        Span span = (Span)textList.elementAt(j);
                        String text = span.getStringText();
                        if( parent != null && span.getParent() != parent) {
                            text = " " + text;
                        }
                        parent = span.getParent();
                        textBuf.append(text);
                    }
                    if( textBuf.length() > 0 ) {
                        setBoxText(box, textBuf.toString().trim());
                    }
                }
                rowSet.addStampContent(box);
            }
        }
        return rowSet;
    }

    private void setBoxText(StampBox box, String str) {
        str = str.toLowerCase();
        String text = HtmlHelper.normalizeText(str);
        String[] parts = text.split(" ");
        StringBuilder denom = new StringBuilder();
        StringBuilder desc = new StringBuilder();
        boolean denomination = true;
        for (String part : parts) {
            if (!HtmlHelper.retrieveNumber(part, true).equals("") || (
                    (HtmlHelper.startsWithCurrency(part) || part.equals("on") || part.equals("+")) && denomination)) {
                if( denom.length() > 0 ) {
                    denom.append(' ');
                }
                denom.append(part);
            } else {
                denomination = false;
                if( desc.length() > 0 ) {
                    desc.append(' ');
                }
                desc.append(part);
            }
        }
        String denomText = HtmlHelper.normalizeDenomination(denom.toString());
        box.setDenomination(denomText);
        String description = mapper.normalizeText(HtmlHelper.normalizeBoxText(desc.toString()));
        box.setDescription(description);
        
    }

}
