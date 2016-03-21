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
import org.htmlparser.nodes.TagNode;
import org.htmlparser.util.NodeIterator;
import org.htmlparser.util.NodeList;
import org.htmlparser.util.ParserException;
import org.javad.stamp.htmlparser.msword.matchers.NodeMatcher;

/**
 *
 */
public class NodeListProcessor {
    
    public Node findParent(Node n, NodeMatcher matcher) {
        Node parent = null;
        Node p = n.getParent();
        if( p != null ) {
            if( matcher.matches(p) ) {
                parent = p;
            } else {
                try {
                    NodeList validChildren = findChildren(p.getChildren(),matcher);
                    if( validChildren.size() > 0 ) {
                        parent = validChildren.elementAt(0);
                    } else {
                        parent = findParent(p, matcher);
                    }
                } catch (ParserException ex) {
                    Logger.getLogger(NodeListProcessor.class.getName()).log(Level.SEVERE, null, ex);
                }
            }
        }
        return parent;
    }
    
    public Node findParentByTagName(Node n, String tag) {
        Node p = n.getParent();
        if( p != null && p instanceof TagNode ) {
            TagNode tn = (TagNode)p;
            if( tn.getTagName().equalsIgnoreCase(tag)) {
                return p;
            }
            p = findParentByTagName(p,tag);
        }
        return p;
    }
    
    public Node findPredecessorSibling(Node n) {
        Node parent = n.getParent();
        if(parent != null && n instanceof TagNode) {
            TagNode tag = (TagNode)n;
            NodeList list = parent.getChildren();
            int index = list.indexOf(n);
            if( index >= 0 ) {
                for(int i = index -1; i >= 0; i -- ) {
                    Node c = list.elementAt(i);
                    if( c instanceof TagNode ) {
                        TagNode tn = (TagNode)c;
                        if(tag.getTagName().equals(tn.getTagName())) {
                            return c;
                        }
                    }
                }
            }
        }
        return null;
    }
    
    public NodeList findChildrenByTagName(Node n, String tagName) {
        NodeList list = new NodeList();
        NodeList children = n.getChildren();
        if (children != null) {
            for (int i = 0; i < children.size(); i++) {
                Node child = children.elementAt(i);
                if (child instanceof TagNode) {
                    TagNode node = (TagNode) child;
                    if (node.getTagName().equalsIgnoreCase(tagName)) {
                        list.add(node);
                    }
                }
            }
            if (children.size() > 0 && list.size() == 0) {
            for (int i = 0; i < children.size(); i++) {
                Node child = children.elementAt(i);
                list.add(findChildrenByTagName(child, tagName));
            }
        }
        }
        
        return list;
    }
    
    public NodeList findChildren(NodeList n, NodeMatcher matcher) throws ParserException {
        return findChildren(n,matcher,false);
    }

    public NodeList findChildren(NodeList n, NodeMatcher matcher, boolean fullDepth) throws ParserException {
        NodeList list = new NodeList();
        if (n != null) {
            for (NodeIterator iter = n.elements(); iter.hasMoreNodes();) {
                Node node = iter.nextNode();
                if (matcher.matches(node)) {
                    list.add(node);
                    if( !fullDepth ) {
                        continue;
                    }
                    
                }
                NodeList result = this.findChildren(node.getChildren(), matcher, fullDepth);
                if (result.size() > 0) {
                    list.add(result);
                }
            }
        }
        return list;
    }
}
