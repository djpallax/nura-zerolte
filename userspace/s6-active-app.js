function report(window) {
    callDBus("org.s6.Controls", "/Controls", "org.s6.Controls", "SetActiveApp", window ? String(window.resourceClass) : "");
}
workspace.windowActivated.connect(report);
report(workspace.activeWindow);
