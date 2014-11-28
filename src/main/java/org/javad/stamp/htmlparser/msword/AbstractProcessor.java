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
import org.javad.pdf.model.PageConfiguration;
import org.javad.pdf.model.PageConfigurations;
import org.javad.stamp.htmlparser.msword.styles.PageStyle;

/**
 *
 * @author Jason
 * @param <T>
 */
public abstract class AbstractProcessor<T> {
    
    private final PageStyle style;
    private NodeListProcessor processor;
    private PageConfiguration pageConfiguration;
    
    public AbstractProcessor(PageStyle style) {
        super();
        this.style = style;
    }
    
    public PageConfiguration getPageConfiguration() {
        if( pageConfiguration == null ) {
            pageConfiguration = PageConfigurations.getInstance().getActiveConfiguration();
        }
        return pageConfiguration;
    }
    
    public PageStyle getPageStyle() {
        return style;
    }
    
    public NodeListProcessor getNodeListProcessor() {
        if( processor == null ) {
            processor = new NodeListProcessor();
        }
        return processor;
    }
    
    public abstract T process(Node stampSet, Node page);
}
