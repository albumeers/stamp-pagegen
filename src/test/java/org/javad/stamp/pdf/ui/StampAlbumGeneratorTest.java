package org.javad.stamp.pdf.ui;

import static org.junit.jupiter.api.Assertions.assertTrue;

import java.awt.Dialog;
import java.awt.Frame;
import java.io.File;
import java.util.prefs.Preferences;

import org.assertj.swing.core.GenericTypeMatcher;
import org.assertj.swing.edt.GuiActionRunner;
import org.assertj.swing.fixture.DialogFixture;
import org.assertj.swing.fixture.FrameFixture;
import org.assertj.swing.junit.testcase.AssertJSwingJUnitTestCase;
import org.assertj.swing.timing.Pause;
import org.javad.components.AboutDialog;
import org.javad.fixtures.components.StatusPanelFixture;
import org.javad.fixtures.swing.JdFileChooserFixture;
import org.javad.stamp.pdf.Resources;
import org.junit.After;
import org.junit.Before;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;


public class StampAlbumGeneratorTest extends AssertJSwingJUnitTestCase {

    private FrameFixture window;
    private String storePath;
    private String outputFolder;
    private String inputFolder;
    private String input;

    @Override
    protected void onSetUp() {
        // Intentionally empty; setup done in @BeforeEach
    }

    @Before
    public void setUpTest() {
        storePath = System.getProperty("java.io.tmpdir") + File.separator + System.currentTimeMillis();
        File output = new File(storePath);
        if (!output.exists()) {
            output.mkdir();
        }

        Preferences prefNode = Resources.getPreferencesNode();
        outputFolder = prefNode.get(GeneratorConstants.DEFAULT_OUTPUT_FOLDER_KEY, null);
        inputFolder = prefNode.get(GeneratorConstants.DEFAULT_FOLDER_KEY, null);
        prefNode.put(GeneratorConstants.DEFAULT_OUTPUT_FOLDER_KEY, storePath);
        input = System.getProperty("user.dir") + File.separator + "target/test-classes";
        prefNode.put(GeneratorConstants.DEFAULT_FOLDER_KEY, input);

        // Launch GUI safely on EDT
        StampAlbumGenerator app = GuiActionRunner.execute(() -> {
            StampAlbumGenerator generator = new StampAlbumGenerator();
            return generator;
        });

        window = new FrameFixture(robot(), app);
        window.show(); // ensure visible
    }

    @After
    public void tearDownTest() {
        Preferences prefNode = Resources.getPreferencesNode();
        prefNode.put(GeneratorConstants.DEFAULT_OUTPUT_FOLDER_KEY, outputFolder);
        prefNode.put(GeneratorConstants.DEFAULT_FOLDER_KEY, inputFolder);

        if (window != null) {
            window.cleanUp();
        }

        // Delete temporary folder on exit
        File f = new File(storePath);
        f.deleteOnExit();
    }

    /*
    @Test
    public void verifyAboutDialog() {
        StatusPanelFixture.waitForCompletion(window);
        window.menuItem("menu.help.about").click();

        DialogFixture dialog = window.dialog(new GenericTypeMatcher<Dialog>(Dialog.class) {
            @Override
            protected boolean isMatching(Dialog dlg) {
                return dlg instanceof AboutDialog && dlg.isShowing();
            }
        });

        dialog.requireModal();
        dialog.requireVisible();
        String text = dialog.textBox("text-license").text();
        assertTrue(text.contains("Lead Developer: Jason Drake"));
        assertTrue(text.contains("STAMP ALBUM GENERATOR LICENSE INFORMATION"));

        dialog.button("btn-ok").click();
        dialog.requireNotVisible();
    }

    @Test
    public void testGeneration() {
        StatusPanelFixture.waitForCompletion(window);

        window.button("pagegen-inputFile").click();
        Pause.pause(1000);
        JdFileChooserFixture.getInstance(window).open(input + File.separator + "test.xml");

        window.button("pagegen-outputFolder").click();
        Pause.pause(1000);
        JdFileChooserFixture.getInstance(window).open(storePath);

        window.button("pagegen-generate").click();
        Pause.pause(500);
        StatusPanelFixture.waitForCompletion(window);

        File output = new File(storePath + File.separator + "test.pdf");
        assertTrue(output.exists());
        assertTrue(output.isFile());
    }*/
}