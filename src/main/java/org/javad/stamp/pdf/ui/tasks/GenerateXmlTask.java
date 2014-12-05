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
package org.javad.stamp.pdf.ui.tasks;

import java.io.File;
import java.util.Map;
import javax.swing.SwingWorker;
import org.bushe.swing.event.EventBus;
import org.javad.events.StatusEvent;
import org.javad.events.StatusEvent.StatusType;
import org.javad.stamp.htmlparser.msword.AlbumParser;
import org.javad.stamp.htmlparser.msword.styles.LegacyPageStyle;
import org.javad.stamp.htmlparser.msword.styles.PageStyle;
import org.javad.stamp.pdf.Resources;
import org.javad.stamp.pdf.events.PdfAppEvent;
import org.javad.stamp.pdf.events.PdfAppEvent.EventType;

public class GenerateXmlTask extends SwingWorker<Void, Void> {

	private final Map<String,String> bean;
	private boolean errorRaised = false;
	
	public GenerateXmlTask(Map<String,String> bean) {
		this.bean = bean;
	}
	
	@Override
	protected Void doInBackground() throws Exception {
                AlbumParser parser = new AlbumParser();
                try {
                    File input = new File(bean.get("input"));
                    String out = bean.get("output") + File.separator + input.getName();
                    out = out.substring(0, out.lastIndexOf(".html")) + ".xml";
                    PageStyle style = PageStyle.StyleType.valueOf(bean.get("pageType")).getPageStyle();
                    parser.parse(style, input.getAbsolutePath(), out);
                } catch( Throwable t ) {
                    errorRaised = true;
                    EventBus.publish(new PdfAppEvent(EventType.Generate_Error,t));
                }
		
		return null;
	}
	
	@Override
	protected void done() {
		EventBus.publish(new StatusEvent(StatusType.Finished, Resources.getString("message.finished")));
		if( !errorRaised ) {
			EventBus.publish(new PdfAppEvent(EventType.Generated,null));
		}
	}
}
