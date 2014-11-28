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
package org.javad.stamp.htmlparser;

import java.util.regex.Matcher;
import java.util.regex.Pattern;
import org.javad.pdf.util.PdfUtil;

/**
 *
 * @author Jason
 */
public class HtmlHelper {
    
    public static final Pattern NUMBERS = Pattern.compile("^([-+]?[0-9]*\\.?[0-9]*)+");
    public static float W_RATIO = 3.73913f;
    public static float PT_RATIO = 2.815f;
    public static float INCH_RATIO = 25.4f;
    
    private static final String[][] modifiers = {
        { " On ", " on " },
        { " Of ", " of "},
        {" And ", " and " },
        {" Over "," over "},
        {" In ", " in "},
        {" By ", " by "},
        { " With ", " with "},
        { " Without ", " without "},
        {" The ", " the "},
        {"&amp;","and"},
        {"&nbsp;", ""},
        {"&quot;", "'"},
        {"\"","'"},
    };
    
    private static final String[][] currencyConversion = {
        { "p", "d" },
        { "sh", "/" },
    };
    
    private static final char[] currencyPrefixes = { '$', '£' ,'¥', '€' };
    
    public static boolean startsWithCurrency(String text) {
        if( text != null && !text.isEmpty()) {
            for(char c: currencyPrefixes) {
                if( c == text.charAt(0)) {
                    return true;
                }
            }
        }
        return false;
    }
 
    public static String normalizeDenomination(String text) {
        String[] parts = text.split(" ");
        StringBuilder buf = new StringBuilder(text.length());
        for(int i = 0; i < parts.length; i++ ) {
            String part = parts[i];
            String number = retrieveNumber(part,true);
            if( !part.isEmpty() && 
                    (Character.isDigit(part.charAt(0)) || part.charAt(0) == '½' || part.charAt(0) == '¼' || part.charAt(0) == '¾') && 
                    number.length() < part.length()) {
                String unit = part.substring(number.length()).toLowerCase();
                for(String[] currency: currencyConversion ) {
                    if( unit.endsWith(currency[0]) ) {
                        unit = unit.replace(currency[0], currency[1]);
                    }
                }
                part = number + unit;
            }
            buf.append(part);
            if( i < parts.length -1) {
                buf.append(' ');
            }
        }
        String val = buf.toString();
        if( val.length() > 0 ) {
            val = val.replace("/ ", "/-");
        }
        return val;
    }
    
    public static String retrieveNumber(String text, boolean notConvertible) {
        String number = "";
        for( int i = 0; i < text.length(); i++ ) {
            try {
                String val = number + text.charAt(i);
                Float.valueOf(val);
                number = val;
            } catch( NumberFormatException nfe ) {
                if( notConvertible && text.charAt(i) == '½' || text.charAt(i) == '¼' || text.charAt(i) == '¾' ) {
                    number = number + text.charAt(i);
                }
                break; // do nothing limit is reached
            }
        }
        return number;
    }
    
    public static String normalizeText(String text) {
        String s = text.replace("\r", "");
        s = s.replace("\u00A0", "");
        s = s.replace("\n", "");
        s = s.replace("  ", " ");
        s = s.replace("  ", " ");
        return s;
    }
    
    public static String normalizeTitle(String text) {
        return normalizeText(text);
    }
    
    public static String normalizeBoxText(String text) {
        String s = normalizeText(text);
        s = PdfUtil.convertToProperCase(s);
        for(String[] modifier : modifiers ) {
            if( s.contains(modifier[0]) ) {
                s = s.replace(modifier[0], modifier[1]);
            }
        }
        return s;
    }
    
      public static float convertToNumber(String value) {
        if (value != null) {
            Matcher matcher = NUMBERS.matcher(value.trim());
            if (matcher.find()) {
                float f = Float.valueOf(matcher.group(0));
                if (value.endsWith("in")) {
                    f = f * INCH_RATIO;
                } else if (value.endsWith("pt")) {
                    f = f / PT_RATIO;
                }
                return f;
            }
        }
        return -1.0f;
    }
    
    public static String extractValueFromStyle(String style, String key) {
        String val = null;
        int index = style.indexOf(key + ":");
        if( index < 0 ) {
            return val;
        }
        String[] styles = style.substring(index + (key.length() + 1)).split(";");
        if( styles.length > 0 ) {
            val = styles[0];
        } 
        return val;
    }
    
}
