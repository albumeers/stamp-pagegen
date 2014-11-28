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
package org.javad.stamp.htmlparser.msword.matchers.legacy;

import org.htmlparser.Node;
import org.htmlparser.nodes.TagNode;
import org.htmlparser.tags.TableTag;
import org.javad.stamp.htmlparser.msword.matchers.NodeMatcher;

/**
 *
 * @author Jason
 */
public class StampSetMatcher extends NodeMatcher {

    @Override
    public boolean matches(Node node) {
        if( node instanceof TagNode ) {
            TagNode tagNode = (TagNode)node;
            if( tagNode instanceof TableTag && tagNode.getAttribute("class").contains("TableGrid")) {
                return true;
            }
        }
        return false;
    }
    
}
