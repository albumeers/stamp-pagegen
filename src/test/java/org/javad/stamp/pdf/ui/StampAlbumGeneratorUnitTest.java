package org.javad.stamp.pdf.ui;

import static org.junit.jupiter.api.Assertions.*;

import java.util.ArrayList;
import java.util.List;
import java.util.logging.Handler;
import java.util.logging.LogRecord;
import java.util.logging.Logger;
import javax.swing.JFrame;

import org.assertj.swing.edt.GuiActionRunner;
import org.junit.jupiter.api.Test;

/**
 * Unit tests for {@link StampAlbumGenerator}.
 *
 * Mandatory Test Creation (AGENTS.md):
 * AI agents MUST ALWAYS write or update unit tests in src/test/java for every
 * code modification, bug fix, refactor, performance tuning, or default value change
 * without waiting for explicit user prompt.
 */
public class StampAlbumGeneratorUnitTest {

    @Test
    public void testDefaultCloseOperationIsExitOnClose() {
        if (java.awt.GraphicsEnvironment.isHeadless()) {
            return;
        }
        StampAlbumGenerator generator = GuiActionRunner.execute(() -> new StampAlbumGenerator());
        assertNotNull(generator);
        assertEquals(JFrame.EXIT_ON_CLOSE, generator.getDefaultCloseOperation());
    }

    @Test
    public void testInitializationLogsCpuCoreCount() {
        if (java.awt.GraphicsEnvironment.isHeadless()) {
            return;
        }
        int expectedCores = Runtime.getRuntime().availableProcessors();
        List<String> logMessages = new ArrayList<>();
        Handler testHandler = new Handler() {
            @Override
            public void publish(LogRecord record) {
                if (record != null && record.getMessage() != null) {
                    logMessages.add(record.getMessage());
                }
            }

            @Override
            public void flush() {}

            @Override
            public void close() throws SecurityException {}
        };

        Logger logger = Logger.getLogger("org.javad");
        logger.addHandler(testHandler);

        try {
            GuiActionRunner.execute(() -> new StampAlbumGenerator());
            boolean found = logMessages.stream().anyMatch(msg ->
                msg.equals("Detected " + expectedCores + " CPU cores for processing.")
            );
            assertTrue(found, "Initialization should log detected CPU cores message");
        } finally {
            logger.removeHandler(testHandler);
        }
    }
}
