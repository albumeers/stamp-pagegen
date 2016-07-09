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


package org.javad.pdf.util;

import com.itextpdf.text.Document;
import com.itextpdf.text.Font;
import com.itextpdf.text.pdf.BaseFont;
import com.itextpdf.text.pdf.PdfContentByte;
import com.itextpdf.text.pdf.PdfWriter;
import java.io.ByteArrayOutputStream;
import java.util.HashMap;
import java.util.Map;
import java.util.StringTokenizer;
import org.javad.pdf.IContentGenerator;
import org.javad.pdf.OutputBounds;
import org.javad.pdf.fonts.FontRegistry;
import org.javad.pdf.fonts.PdfFontDefinition;

public class PdfUtil {

    public static float DPI = 72.0f;
    public static float MM_INCH = 25.4f;
    private static long LAST_CHECK_TIME = 0;
    private static BaseFont i18Font;
    private static final Map<String,String> UPPERCASE_REPLACEMENTS = new HashMap<>();
    
    static {
        UPPERCASE_REPLACEMENTS.put("\u00DF", "\u1E9E");
    }
    
    public static float convertFromMillimeters(float mm) {
        return mm / MM_INCH * DPI;
    }
    
    public static float convertFromDPI(float dpi) {
        return dpi / DPI * MM_INCH;
    }

    public static boolean isTextTooWide(String text, Font f, float width) {
        return f.getBaseFont().getWidthPoint(text, f.getSize()) > width;
    }

    /**
     * Convert the string to a Proper Case String
     *
     * @param s
     * @return
     */
    public static String convertToProperCase(String s) {
        StringBuilder buf = new StringBuilder(s.length());
        StringTokenizer t = new StringTokenizer(s, " ", true);
        while (t.hasMoreTokens()) {
            String token = t.nextToken();
            String remainder = (token.length() > 1) ? token.substring(1).toLowerCase() : token;
            if (token.length() > 1) {
                buf.append(("" + token.charAt(0)).toUpperCase());
            }
            buf.append(remainder);

        }
        return buf.toString();
    }

    /**
     * Whether the text represents an issue Text string.
     * 
     * @param s
     * @return 
     */
    @SuppressWarnings("null")
    public static boolean isIssueText(String s) {
        boolean valid = (s != null && !s.isEmpty());
        if (valid) {
            for (int i = 0; i < s.length(); i++) {
                char c = s.charAt(i);
                if (!Character.isDigit(c) && c != '-') {
                    valid = false;
                }
            }
        }
        return valid;
    }
    
    public static float convertToStampBoxWidth(int width) {
        return PdfUtil.convertFromMillimeters(width) * 0.95f;
    }

    public static String toUpperCase(String s) {
        String str = s;
        for( String key : UPPERCASE_REPLACEMENTS.keySet()) {
            str = str.replace( key, UPPERCASE_REPLACEMENTS.get(key));
        }
        str = str.toUpperCase();
        for( String key : UPPERCASE_REPLACEMENTS.keySet()) {
            str = str.replace( UPPERCASE_REPLACEMENTS.get(key), key);
        }
        return str;
    }
    
    public static float renderConstrainedText(PdfContentByte content, String text, Font f, float x, float y, int width) {
        float offset = 0.0f;
        if (text == null || text.isEmpty()) {
            return offset;
        }
        float w = PdfUtil.convertToStampBoxWidth(width);

        String prevStr = "";
        text = text.replace("\\n", "\n");
        for (String v : text.split("\n")) {
            String str = "";
            for (String s : v.split(" ")) {
                str += ((!str.isEmpty()) ? " " : "") + s;
                if (isTextTooWide(str, f, w)) {
                    improveRenderText(content, prevStr, f, x, y + offset);
                    offset -= f.getSize() + 1;
                    prevStr = s;
                    str = s;
                    continue;
                }
                prevStr = str;
            }
            if (!str.isEmpty()) {
                improveRenderText(content, prevStr, f, x, y + offset);
                offset -= f.getSize() + 1;
            }
        }

        return offset;
    }
    
    private static class ReplacementRecord {
        int position;
        char character;
    }
   
    protected static void improveRenderText(PdfContentByte content, String str, Font f, float x, float y) {

        BaseFont bf = f.getCalculatedBaseFont(false);
        if( i18Font == null && (System.currentTimeMillis() - LAST_CHECK_TIME > 10000)) {
            i18Font = FontRegistry.getInstance().getFont(PdfFontDefinition.ExtendedCharacters).getCalculatedBaseFont(false);
            LAST_CHECK_TIME = System.currentTimeMillis();
        }
        StringBuilder buf = new StringBuilder(str.length());
        boolean extendedCodePoint = false;
        float effWidth = 0.0f;
        for (int i = 0; i < str.length(); i++) {
            char c = str.charAt(i);
            int codePoint = Character.codePointAt("" + c, 0);
            boolean curCodePoint = (!bf.charExists(codePoint)) ? true : false;
            if( curCodePoint != extendedCodePoint ) {
                content.setFontAndSize((extendedCodePoint) ? i18Font: bf, f.getSize());
                effWidth += content.getEffectiveStringWidth(buf.toString(), false);
                buf = new StringBuilder();
                extendedCodePoint = curCodePoint;
            } 
            buf.append(c);
        }
        content.setFontAndSize(bf, f.getSize());
        effWidth += content.getEffectiveStringWidth(buf.toString(), false);
        float x_pos = x - (effWidth / 2.0f); // eq. to showTextAligned

        content.beginText();
        content.setTextMatrix(x_pos, y);
        BaseFont lastFont = bf;
        @SuppressWarnings("UnusedAssignment")
        BaseFont currentFont = lastFont;
        buf = new StringBuilder();
        for (int i = 0; i < str.length(); i++) {
            char c = str.charAt(i);
            int codePoint = Character.codePointAt("" + c, 0);
            if (!bf.charExists(codePoint)) {
                currentFont = i18Font;
            } else {
                currentFont = bf;
            }
            if (currentFont != lastFont) {
                content.showText(buf.toString());
                buf = new StringBuilder();
                content.setFontAndSize(currentFont, f.getSize());
                lastFont = currentFont;
            }
            buf.append(c);
        }
        if (buf.length() > 0) {
            content.showText(buf.toString());
        }
        content.endText();
    }

    @SuppressWarnings("CallToPrintStackTrace")
    public static int getDescriptionTextRowsForStampBox(PdfContentByte content, Font f, Font secondary_f, String description, String secondary_description, int width) {
        
        int rows = 0;
        try {
            Document d = new Document(content.getPdfDocument().getPageSize());
            PdfWriter writer = PdfWriter.getInstance(d, new ByteArrayOutputStream());
            d.open();
            PdfContentByte c = writer.getDirectContent();
            float top = 0;
            float d_delta = PdfUtil.renderConstrainedText(c, description, f, 0, top, width);
            rows += (int)Math.ceil(d_delta / f.getCalculatedSize());
            top += d_delta;
            float delta = PdfUtil.renderConstrainedText(c, secondary_description, secondary_f, 0, top, width);
            if (delta < 1.0f) {
                rows += (int) Math.ceil(delta / f.getCalculatedSize());
            }
            if (rows > -3 && d_delta >= -1 * (f.getSize() + 1)) { // handle one line descriptions
                rows--;
            }
            c.lineTo(1, 1); // force an action to cause close to function
            d.close();
        } catch( Throwable e) {
            e.printStackTrace();
        }
        return -1 * rows; // the row offset is a negative number currently
    }
    
    @SuppressWarnings("CallToPrintStackTrace")
    public static float findMaximumWidth(IContentGenerator generator, PdfContentByte content) {
        float width = 0.0f;
        try {
            Document d = new Document(content.getPdfDocument().getPageSize());
            PdfWriter writer = PdfWriter.getInstance(d, new ByteArrayOutputStream());
            d.open();
            PdfContentByte c = writer.getDirectContent();
            OutputBounds bounds = generator.generate(c);
            width = bounds.width;
            d.newPage();
            d.close();
        } catch (Throwable e) {
            e.printStackTrace();
        }
        return width;
    }

}
