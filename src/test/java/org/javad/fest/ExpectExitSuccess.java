package org.javad.fest;

import static org.junit.Assert.*;
import org.fest.swing.security.ExitCallHook;

public final class ExpectExitSuccess implements ExitCallHook {

    @Override
    public void exitCalled(int status) {
           assertTrue(status == 0);
    }
}