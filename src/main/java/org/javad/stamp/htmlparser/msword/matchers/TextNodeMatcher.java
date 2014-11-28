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
package org.javad.stamp.htmlparser.msword.matchers;

import org.htmlparser.Node;
import org.htmlparser.nodes.TextNode;

/**
 *
 */
public class TextNodeMatcher extends NodeMatcher {

    @Override
    public boolean matches(Node n) {
        return ( n instanceof TextNode );
    }
    
}
