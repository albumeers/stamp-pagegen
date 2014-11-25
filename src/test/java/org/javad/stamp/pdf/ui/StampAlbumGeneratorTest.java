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
package org.javad.stamp.pdf.ui;

import static org.fest.swing.finder.WindowFinder.findFrame;
import static org.fest.swing.launcher.ApplicationLauncher.application;
import static org.junit.Assert.*;

import java.awt.Frame;
import java.io.File;
import java.util.prefs.Preferences;

import org.fest.swing.core.BasicRobot;
import org.fest.swing.core.GenericTypeMatcher;
import org.fest.swing.core.Robot;
import org.fest.swing.finder.WindowFinder;
import org.fest.swing.fixture.DialogFixture;
import org.fest.swing.fixture.FrameFixture;
import org.fest.swing.security.NoExitSecurityManagerInstaller;
import org.fest.swing.timing.Pause;
import org.javad.components.AboutDialog;
import org.javad.fixtures.components.StatusPanelFixture;
import org.javad.fixtures.swing.JdFileChooserFixture;
import org.javad.stamp.pdf.Resources;
import org.junit.After;
import org.junit.AfterClass;
import org.junit.Before;
import org.junit.BeforeClass;
import org.junit.Test;

public class StampAlbumGeneratorTest {

	private FrameFixture window;
	private Robot robot;
	private String storePath;
	private String outputFolder;
	private String inputFolder;
	private String input;
	private static NoExitSecurityManagerInstaller manager = null;
	
	@BeforeClass
	public static void setUpOnce() {
		manager = NoExitSecurityManagerInstaller.installNoExitSecurityManager();
	}
	
	@AfterClass
	public static void closeOut() {
		manager.uninstall();
	}
	
	@Before
	public void setUp() throws Exception {
		storePath = System.getProperty("java.io.tmpdir") + File.separator + System.currentTimeMillis();
		File output = new File(storePath);
		if( !output.exists()) {
			output.mkdir();
		}
		Preferences prefNode = Resources.getPreferencesNode();
		outputFolder = prefNode.get(GeneratorConstants.DEFAULT_OUTPUT_FOLDER_KEY,null);
		inputFolder = prefNode.get(GeneratorConstants.DEFAULT_FOLDER_KEY,null);
		prefNode.put(GeneratorConstants.DEFAULT_OUTPUT_FOLDER_KEY, storePath);
		input = System.getProperty("user.dir") + File.separator + "target/test-classes"; 
		prefNode.put(GeneratorConstants.DEFAULT_FOLDER_KEY, input);
		robot = BasicRobot.robotWithNewAwtHierarchy();
		application(StampAlbumGenerator.class).start();
		window = findFrame(new GenericTypeMatcher<Frame>(Frame.class) {
			protected boolean isMatching(Frame frame) {
				return "stamp-pagegen".equals(frame.getName()) && frame.isVisible(); 
			}
		}).using(robot);
	}

	@After
	public void tearDown() {
		Preferences prefNode = Resources.getPreferencesNode();
		prefNode.put(GeneratorConstants.DEFAULT_OUTPUT_FOLDER_KEY, outputFolder );
		prefNode.put(GeneratorConstants.DEFAULT_FOLDER_KEY, inputFolder );
		window.cleanUp();
		robot.cleanUp();
		// Delete any temporary folders
		File f = new File(storePath);
		f.deleteOnExit();
	}
	
	@Test
	public void verifyAboutDialog() {
		StatusPanelFixture.waitForCompletion(window);
		window.menuItem("menu.help.about").click();
		DialogFixture dialog = WindowFinder.findDialog(AboutDialog.class).using(window.robot);
		dialog.requireModal();
		dialog.requireVisible();
		String text = dialog.textBox("text-license").text();
		assertTrue( text.contains("Lead Developer: Jason Drake"));
		assertTrue( text.contains("STAMP ALBUM GENERATOR LICENSE INFORMATION"));
		dialog.button("btn-ok").click();
		dialog.requireNotVisible();
	}
	
	@Test
	public void testGeneration() {
		StatusPanelFixture.waitForCompletion(window);
		window.button("pagegen-inputFile").click();
		Pause.pause(1000);
		JdFileChooserFixture.getInstance(window).open(input + File.separator + "test.xml");
		Pause.pause(250);
		window.button("pagegen-outputFolder").click();
		Pause.pause(1000);
		JdFileChooserFixture.getInstance(window).open(storePath);
		Pause.pause(1000);
		window.button("pagegen-generate").click();
		Pause.pause(500);
		StatusPanelFixture.waitForCompletion(window);
		
		File output = new File(storePath + File.separator + "test.pdf");
		assertTrue( output.exists());
		assertTrue( output.isFile());
	}
	

}
