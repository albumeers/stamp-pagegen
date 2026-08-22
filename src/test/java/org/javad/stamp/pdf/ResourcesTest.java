package org.javad.stamp.pdf;

import static org.junit.jupiter.api.Assertions.*;

import org.junit.jupiter.api.Test;

/**
 * Unit tests for {@link Resources}.
 *
 * Mandatory Test Creation (AGENTS.md):
 * AI agents MUST ALWAYS write or update unit tests in src/test/java for every
 * code modification, bug fix, refactor, performance tuning, or default value change
 * without waiting for explicit user prompt.
 */
public class ResourcesTest {

    @Test
    public void testHelpAboutApplicationInfoContainsFilteredProperties() {
        String appInfo = Resources.getString("label.helpAbout.applicationInfo");
        assertNotNull(appInfo, "Application info string should not be null");
        assertFalse(appInfo.isEmpty(), "Application info string should not be empty");

        assertTrue(appInfo.contains("Stamp Album Page Generator"), "Should contain application title");
        assertTrue(appInfo.contains("Version"), "Should contain Version label");
        assertTrue(appInfo.contains("Build:"), "Should contain Build label");
        assertTrue(appInfo.contains("Copyright"), "Should contain Copyright label");
    }
}
