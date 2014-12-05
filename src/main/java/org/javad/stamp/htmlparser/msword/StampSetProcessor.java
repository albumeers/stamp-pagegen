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

import java.util.logging.Level;
import java.util.logging.Logger;
import org.htmlparser.Node;
import org.htmlparser.nodes.TextNode;
import org.htmlparser.tags.ParagraphTag;
import org.htmlparser.tags.TableTag;
import org.htmlparser.util.NodeIterator;
import org.htmlparser.util.NodeList;
import org.htmlparser.util.ParserException;
import org.javad.pdf.ISetContent;
import org.javad.stamp.htmlparser.HtmlHelper;
import org.javad.stamp.htmlparser.msword.matchers.TextNodeMatcher;
import org.javad.stamp.htmlparser.msword.styles.ComponentType;
import org.javad.stamp.htmlparser.msword.styles.MatcherFactory;
import org.javad.stamp.htmlparser.msword.styles.PageStyle;
import org.javad.stamp.pdf.StampSet;

/**
 *
 * @author Jason
 */
public class StampSetProcessor  extends AbstractProcessor<StampSet> {

    private final MatcherFactory factory;
    
    public StampSetProcessor(PageStyle style) {
        super(style);
        factory = MatcherFactory.getInstance(style);
    }
  
    @Override
    public StampSet process(Node stampSet, Node page) {
        
        StampSet set = new StampSet(getPageConfiguration());
        StampRowProcessor rowProcessor = new StampRowProcessor(getPageStyle());
        NodeList rows = getNodeListProcessor().findChildrenByTagName(stampSet, "TR");
        for(int i = 0; i < rows.size(); i++ ) {
            Node rowNode = rows.elementAt(i);
            ISetContent content = rowProcessor.process(rowNode, page);
            set.addContentRow(content);
        }
        /*
         * This is rather confusing so worth a comment.  Given the stampSet, walk up
         * the DOM to find the nearest TD cell.  From this, we get all matching Paragraphs
         * that contain "stamp row" text.  But then we have to walk through the existing
         * TD children to ensure there are no previous stamp rows (remember this is firing
         * from the TABLE tag).  If the previous row is found, it resets the starting index
         * so we only extract text between the two stamp rows.
        */
        Node previous = getNodeListProcessor().findParentByTagName(stampSet, "TD");
        if( previous != null ) {
            StringBuilder buf = new StringBuilder();
            try {
                NodeList children = previous.getChildren();
                NodeList matchedChildren = getNodeListProcessor().findChildren(children, factory.getMatcher(ComponentType.SetDescription));
                if( matchedChildren != null && matchedChildren.size() > 0 ) {
                    int tableIndex = children.indexOf(stampSet);
                    int startingIndex = 0;
                    for(int i = 0; i < tableIndex; i++ ) {
                        if( children.elementAt(i) instanceof TableTag ) {
                            startingIndex = i;
                        }
                    }
                    for(int i = startingIndex; i < tableIndex; i++ ) {
                        Node n = children.elementAt(i);
                        if( matchedChildren.contains(n)) {
                            if( n instanceof ParagraphTag) {
                                ParagraphTag p = (ParagraphTag)n;
                                NodeList text = getNodeListProcessor().findChildren(p.getChildren(), new TextNodeMatcher());
                                for(NodeIterator iter = text.elements(); iter.hasMoreNodes(); ) {
                                    if( buf.length() > 0 ) {
                                        buf.append(' ');
                                    }
                                    buf.append( ((TextNode)iter.nextNode()).getText());
                                }
                            }
                        }
                    }
                }
            } catch (ParserException ex) {
                Logger.getLogger(StampSetProcessor.class.getName()).log(Level.SEVERE, null, ex);
            }
            processDescription(set, buf.toString());
        }
        return set;
    }

    private void processDescription(StampSet set, String str) {
        String[] tokens = str.split(" ");
        if( tokens.length > 0 ) {
            String issueText = tokens[tokens.length -1];
            boolean valid = true;
            for(int i = 0; i < issueText.length(); i++ ) {
                char c = issueText.charAt(i);
                if( !Character.isDigit(c) && c != '-' && c != ',') {
                    valid = false;
                }
            }
            if( valid && issueText.length() >= 4 ) { // years have to be at least 4 digits
                set.setIssue(issueText);
                str = str.substring(0, Math.max(str.length() - issueText.length() - 1,0));
            }
        }
        str = HtmlHelper.normalizeBoxText(str);
        int indx = str.indexOf("Watermark");
        if( indx < 0) {
            indx = str.indexOf("Unwatermark");
        }
        if( indx >= 0 ) {
            StringBuilder buf = new StringBuilder();
            buf.append(str.substring(0,indx));
            buf.append("\\n");
            buf.append(str.substring(indx));
            str = buf.toString();
        }
        
        set.setDescription(str);
    }
}
