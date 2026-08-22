package org.javad.stamp.pdf.ui;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;

import javax.swing.JFrame;
import org.assertj.swing.edt.GuiActionRunner;
import org.junit.jupiter.api.Test;

public class StampAlbumGeneratorUnitTest {

    @Test
    public void testDefaultCloseOperationIsExitOnClose() {
        StampAlbumGenerator generator = GuiActionRunner.execute(() -> new StampAlbumGenerator());
        assertNotNull(generator);
        assertEquals(JFrame.EXIT_ON_CLOSE, generator.getDefaultCloseOperation());
    }
}
