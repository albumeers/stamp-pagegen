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
package org.javad.stamp.pdf.ui.tasks;

import javax.swing.SwingWorker;

import org.bushe.swing.event.EventBus;
import org.javad.events.StatusEvent;
import org.javad.events.StatusEvent.StatusType;
import org.javad.stamp.pdf.PdfGenerator;
import org.javad.stamp.pdf.Resources;
import org.javad.stamp.pdf.events.PdfAppEvent;
import org.javad.stamp.pdf.events.PdfAppEvent.EventType;
import org.javad.stamp.pdf.ui.model.GenerateBean;

import com.itextpdf.text.ExceptionConverter;

public class GeneratePdfTask extends SwingWorker<Void, Void> {

	private GenerateBean bean;
	private boolean errorRaised = false;
	
	public GeneratePdfTask(GenerateBean bean) {
		this.bean = bean;
	}
	
	@Override
	protected Void doInBackground() throws Exception {
		PdfGenerator generator = new PdfGenerator();
		try {
			generator.generate(bean);
		} catch( Throwable e ) {
			errorRaised = true;
			if( e instanceof ExceptionConverter ) {
				e = ((ExceptionConverter)e).getException();
			}
			EventBus.publish(new PdfAppEvent(EventType.Generate_Error,e));
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
