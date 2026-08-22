/*
	Copyright 2014-2026 Jason Drake (jadrake75@gmail.com)
	
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
package org.javad.pdf.fonts;

import com.itextpdf.text.Font;

public enum PdfFontDefinition {

	AlbumTitle, AlbumSubtitle, AlbumDescription, AlbumContents, Title, Subtitle, Classifier, SetIssue,
	CompositeSetDescription, SetDescription, SetDescriptionSecondary, SetComment, RowDescription, Stampbox,
	StampboxOther, ExtendedCharacters;

	public String getDefaultTypeFace() {
		String typeFace;
		switch (this) {
		case Title:
		case Subtitle:
		case AlbumTitle:
		case AlbumSubtitle:
			typeFace = "CastleTLig";
			break;
		case ExtendedCharacters:
			typeFace = "Arial Unicode MS";
			break;
		case StampboxOther:
		case RowDescription:
		case CompositeSetDescription:
		case SetComment:
		case SetDescriptionSecondary:
			typeFace = "Verdana";
			break;
		default:
			typeFace = "Verdana";
		}
		return typeFace;
	}

	@SuppressWarnings("incomplete-switch")
	public int getDefaultStyle() {
		int style = Font.NORMAL;
		switch (this) {
		case StampboxOther:
		case RowDescription:
		case AlbumDescription:
		case CompositeSetDescription:
		case SetComment:
		case SetDescriptionSecondary:
			style = Font.ITALIC;
			break;
		}
		return style;
	}

	@SuppressWarnings("incomplete-switch")
	public float getDefaultSize() {
		float size = 4.5f;
		switch (this) {
		case AlbumTitle:
			size = 36.0f;
			break;
		case Title:
		case AlbumSubtitle:
			size = 24.0f;
			break;
		case Subtitle:
			size = 12.0f;
			break;
		case Classifier:
			size = 7.5f;
			break;
		case SetIssue:
		case AlbumDescription:
			size = 6.5f;
			break;
		}
		return size;
	}

}
