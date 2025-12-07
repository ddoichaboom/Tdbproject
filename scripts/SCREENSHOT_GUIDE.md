# Raspberry Pi GUI Screen Capture Guide (for Wayland)

This document provides commands to capture the GUI screen in a Wayland-based Raspberry Pi OS environment, especially when connected via SSH.

The primary tool used is `grim`, a screenshot utility for Wayland.

---

### 1. Recommended Command (with Timestamp)

This is the recommended method. It saves the screenshot in your home directory (`~/`) with a filename that includes the current date and time, preventing accidental overwrites.

**Command:**
```bash
grim ~/$(date +'%Y-%m-%d_%H-%M-%S')_capture.png
```

**Breakdown:**
- **`grim`**: The screenshot tool for Wayland.
- **`~/`**: Specifies the save location as the user's home directory (e.g., `/home/tdb/`).
- **`$(date +'%Y-%m-%d_%H-%M-%S')`**: Generates a timestamp like `2025-12-06_23-18-00` to create a unique filename.

---

### 2. Simple Command

This command saves the screenshot to the current working directory with the fixed name `wayland_capture.png`. If a file with the same name exists, it will be overwritten.

**Command:**
```bash
grim wayland_capture.png
```

---

### 3. Creating a Shell Alias for Convenience

For frequent use, you can create a short alias like `scap` (screen capture) to run the command easily.

**Step 1: Open `.bashrc`**
Open the bash configuration file with a text editor.
```bash
nano ~/.bashrc
```

**Step 2: Add the Alias**
Add the following line to the end of the file:
```bash
alias scap="grim ~/$(date +'%Y-%m-%d_%H-%M-%S')_capture.png"
```

**Step 3: Save and Exit**
Press `Ctrl+X`, then `Y`, then `Enter`.

**Step 4: Apply Changes**
Load the new configuration into your current shell session.
```bash
source ~/.bashrc
```

**Usage:**
From now on, you can simply type the following command in the terminal to take a screenshot:
```bash
scap
```
The captured image will be saved in your home directory.
