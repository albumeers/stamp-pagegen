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
package org.javad.pdf;

import java.util.Arrays;
import java.util.HashSet;
import java.util.Set;
import org.javad.pdf.model.PageConfiguration;

public abstract class PositionalContent implements IPositionalContent {

	private float x;
	private float y;
	protected PageConfiguration configuration;
        protected Set<String> skipTerms = new HashSet<>();
	
	public PositionalContent(PageConfiguration configuration) {
		super();
		this.configuration = configuration;
	}
	
	public float getX() {
		return x;
	}

	public void setX(float x) {
		this.x = x;
	}

	public float getY() {
		return y;
	}

	public void setY(float y) {
		this.y = y;
	}
        
        public void parseSkipTerms(String text) {
            skipTerms.clear();
            if( text != null && !text.isEmpty()) {
                skipTerms.addAll(Arrays.asList(text.split(" ")));
            }
        }
        
        @Override
        public boolean isSkipped() {
            Set<String> terms = configuration.getSkipTerms();
            if( !terms.isEmpty()) {
                for(String term : skipTerms ) {
                    if(terms.contains(term)) {
                        return true;
                    }
                }
            }
            return false;
        }
        
}
