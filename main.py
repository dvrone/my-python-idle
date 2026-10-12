import os
import subprocess
import sys
import tempfile
import threading
import tkinter as tk
from tkinter import filedialog, messagebox

# ==================== CONFIGURATION ====================

BG = "#1e222a"
SIDEBAR = "#252a34"
EDITOR_BG = "#282c34"
OUTPUT_BG = "#21252b"
ACCENT = "#61afef"
TEXT = "#abb2bf"
GREEN = "#98c379"
RED = "#e06c75"
BORDER = "#363c48"
FONT = "GoogleSansCode Nerd Font"

root = tk.Tk()
root.geometry("1280x720")
root.title("Python IDLE")
root.configure(bg=BG)
root.resizable(False, False)

current_file = None
modified = False
running = False

# ==================== FILE STATE ====================


def update_title():
    name = os.path.basename(current_file) if current_file else "Untitled"
    root.title(f"{'*' if modified else ''}{name} - Python IDLE")


def update_status(message="Ready"):
    status_label.config(
        text=f"  Python {sys.version_info.major}.{sys.version_info.minor}  |  {message}"
    )


def update_cursor(event=None):
    position = code_input.index("insert").split(".")
    cursor_label.config(text=f"Ln {position[0]}, Col {int(position[1]) + 1}   ")


def on_modified(event=None):
    global modified
    if code_input.edit_modified():
        modified = True
        update_title()
        code_input.edit_modified(False)


# ==================== TERMINAL ====================


def terminal_write(text, color=GREEN):
    code_output.config(state="normal")
    code_output.insert("end", text, color)
    code_output.see("end")
    code_output.config(state="disabled")


def clear_terminal():
    code_output.config(state="normal")
    code_output.delete("1.0", "end")
    code_output.config(state="disabled")
    update_status("Terminal cleared")


def terminal_start():
    code_output.config(state="normal")
    code_output.insert("end", "\n>>> Running Python code...\n", ACCENT)
    code_output.config(state="disabled")


# ==================== SAVE / OPEN ====================


def save_file():
    global current_file, modified

    path = current_file
    if not path:
        path = filedialog.asksaveasfilename(
            title="Save Python file",
            defaultextension=".py",
            filetypes=[("Python files", "*.py"), ("All files", "*.*")],
        )

    if not path:
        return False

    try:
        with open(path, "w", encoding="utf-8") as file:
            file.write(code_input.get("1.0", "end-1c"))

        current_file = path
        modified = False
        update_title()
        update_status(f"Saved: {os.path.basename(path)}")
        return True

    except OSError as error:
        messagebox.showerror("Save error", str(error))
        return False


def confirm_save():
    if not modified:
        return True

    answer = messagebox.askyesnocancel(
        "Unsaved changes", "Save changes before continuing?"
    )

    if answer is None:
        return False

    if answer:
        return save_file()

    return True


def open_file():
    global current_file, modified

    if not confirm_save():
        return

    path = filedialog.askopenfilename(
        title="Open Python file",
        filetypes=[("Python files", "*.py"), ("All files", "*.*")],
    )

    if not path:
        return

    try:
        with open(path, "r", encoding="utf-8") as file:
            content = file.read()

        code_input.delete("1.0", "end")
        code_input.insert("1.0", content)
        code_input.edit_modified(False)

        current_file = path
        modified = False
        update_title()
        update_cursor()
        update_status(f"Opened: {os.path.basename(path)}")

    except (OSError, UnicodeError) as error:
        messagebox.showerror("Open error", str(error))


def new_file():
    global current_file, modified

    if not confirm_save():
        return

    code_input.delete("1.0", "end")
    code_input.edit_modified(False)

    current_file = None
    modified = False
    update_title()
    update_cursor()
    update_status("New file")


# ==================== RUN PYTHON CODE ====================


def run_code():
    global running

    if running:
        return

    source = code_input.get("1.0", "end-1c")

    if not source.strip():
        update_status("No code to run")
        return

    # Save a temporary snapshot of the editor contents.
    # This also allows running code that has not been saved.
    try:
        temp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", encoding="utf-8", delete=False
        )
        temp.write(source)
        temp.close()
        temp_path = temp.name

    except OSError as error:
        messagebox.showerror("Run error", str(error))
        return

    working_dir = (
        os.path.dirname(os.path.abspath(current_file)) if current_file else os.getcwd()
    )

    running = True
    run_button.config(state="disabled")
    update_status("Running...")

    terminal_start()
    terminal_write(source + "\n\n", TEXT)

    def worker():
        try:
            result = subprocess.run(
                [sys.executable, "-u", temp_path],
                cwd=working_dir,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=60,
            )

            stdout = result.stdout
            stderr = result.stderr
            exit_code = result.returncode

            def finish():
                global running
                running = False
                run_button.config(state="normal")

                if stdout:
                    terminal_write(stdout, GREEN)

                if stderr:
                    terminal_write(stderr, RED)

                if exit_code == 0:
                    terminal_write("\nProcess finished successfully.\n", ACCENT)
                    update_status("Execution completed")
                else:
                    terminal_write(f"\nProcess exited with code {exit_code}.\n", RED)
                    update_status("Execution failed")

            root.after(0, finish)

        except subprocess.TimeoutExpired:

            def timeout_finish():
                global running
                running = False
                run_button.config(state="normal")
                terminal_write("\nExecution stopped: 60-second timeout.\n", RED)
                update_status("Execution timed out")

            root.after(0, timeout_finish)

        except OSError as error:

            def error_finish():
                global running
                running = False
                run_button.config(state="normal")
                terminal_write(f"\nError: {error}\n", RED)
                update_status("Execution error")

            root.after(0, error_finish)

        finally:
            try:
                os.unlink(temp_path)
            except OSError:
                pass

    threading.Thread(target=worker, daemon=True).start()


# ==================== INTERFACE ====================

sidebar = tk.Frame(root, bg=SIDEBAR, width=80, height=720)
sidebar.place(x=0, y=0)

tk.Label(sidebar, text="Py", font=(FONT, 22, "bold"), bg=SIDEBAR, fg=ACCENT).place(
    x=22, y=20
)

tk.Frame(sidebar, bg=BORDER, height=1, width=48).place(x=16, y=75)

editor_frame = tk.Frame(
    root, bg=EDITOR_BG, highlightbackground=BORDER, highlightthickness=1
)
editor_frame.place(x=80, y=0, width=780, height=696)

editor_header = tk.Frame(editor_frame, bg=SIDEBAR, height=48)
editor_header.pack(fill="x")
editor_header.pack_propagate(False)

file_label = tk.Label(
    editor_header,
    text="  ●  Untitled.py",
    font=(FONT, 12),
    bg=SIDEBAR,
    fg=TEXT,
    anchor="w",
)
file_label.pack(side="left", fill="y")

tk.Label(
    editor_header, text="Python", font=(FONT, 10), bg=SIDEBAR, fg=ACCENT, padx=16
).pack(side="right", fill="y")

# Editor with line numbers
editor_body = tk.Frame(editor_frame, bg=EDITOR_BG)
editor_body.pack(fill="both", expand=True)

line_numbers = tk.Text(
    editor_body,
    width=4,
    font=(FONT, 15),
    bg=EDITOR_BG,
    fg="#636d83",
    bd=0,
    padx=8,
    pady=18,
    state="disabled",
    takefocus=0,
    wrap="none",
)
line_numbers.pack(side="left", fill="y")

code_input = tk.Text(
    editor_body,
    font=(FONT, 15),
    bg=EDITOR_BG,
    fg=TEXT,
    insertbackground=ACCENT,
    selectbackground="#3e4451",
    selectforeground="#ffffff",
    bd=0,
    padx=12,
    pady=18,
    wrap="none",
    undo=True,
    relief="flat",
    highlightthickness=0,
)
code_input.pack(side="left", fill="both", expand=True)

editor_scroll = tk.Scrollbar(editor_body, orient="vertical", command=code_input.yview)
editor_scroll.pack(side="right", fill="y")
code_input.configure(yscrollcommand=editor_scroll.set)


def refresh_lines(event=None):
    line_numbers.config(state="normal")
    line_numbers.delete("1.0", "end")

    total_lines = int(code_input.index("end-1c").split(".")[0])
    numbers = "\n".join(str(i) for i in range(1, total_lines + 1))
    line_numbers.insert("1.0", numbers)

    line_numbers.config(state="disabled")
    update_cursor()


code_input.bind("<<Modified>>", on_modified)
code_input.bind("<KeyRelease>", refresh_lines)
code_input.bind("<ButtonRelease-1>", update_cursor)
code_input.bind("<MouseWheel>", refresh_lines)

# Terminal
output_frame = tk.Frame(root, bg=OUTPUT_BG)
output_frame.place(x=860, y=0, width=420, height=696)

output_header = tk.Frame(output_frame, bg=SIDEBAR, height=48)
output_header.pack(fill="x")
output_header.pack_propagate(False)

tk.Label(
    output_header, text="  TERMINAL", font=(FONT, 11, "bold"), bg=SIDEBAR, fg=GREEN
).pack(side="left", fill="y")

tk.Button(
    output_header,
    text="Clear",
    font=(FONT, 9),
    bg=SIDEBAR,
    fg=TEXT,
    activebackground=BORDER,
    activeforeground="white",
    bd=0,
    cursor="hand2",
    command=clear_terminal,
).pack(side="right", padx=12)

code_output = tk.Text(
    output_frame,
    font=(FONT, 12),
    bg=OUTPUT_BG,
    fg=GREEN,
    insertbackground=GREEN,
    bd=0,
    padx=18,
    pady=18,
    wrap="word",
    relief="flat",
    state="disabled",
)
code_output.pack(fill="both", expand=True)

code_output.tag_config("green", foreground=GREEN)
code_output.tag_config("red", foreground=RED)
code_output.tag_config("blue", foreground=ACCENT)
code_output.tag_config("white", foreground=TEXT)

# ==================== SIDEBAR BUTTONS ====================


def make_button(y, image_path, fallback, command):
    try:
        image = tk.PhotoImage(file=image_path)

        # Scale large images down to a maximum of 24x24.
        factor = max(1, (image.width() + 23) // 24, (image.height() + 23) // 24)
        image = image.subsample(factor, factor)

        button = tk.Button(
            root,
            image=image,
            bg=SIDEBAR,
            activebackground="#343b49",
            bd=0,
            relief="flat",
            cursor="hand2",
            command=command,
        )
        button.image = image

    except tk.TclError:
        button = tk.Button(
            root,
            text=fallback,
            font=(FONT, 10, "bold"),
            bg=SIDEBAR,
            fg=ACCENT,
            activebackground="#343b49",
            activeforeground="white",
            bd=0,
            relief="flat",
            cursor="hand2",
            command=command,
        )

    button.place(x=16, y=y, width=48, height=48)
    return button


make_button(100, "plus.png", "NEW", new_file)
make_button(165, "folder.png", "OPEN", open_file)
make_button(230, "diskette.png", "SAVE", save_file)

run_button = make_button(295, "play.png", "RUN", run_code)

tk.Frame(sidebar, bg=BORDER, height=1, width=48).place(x=16, y=365)

make_button(390, "terminal.png", "CLR", clear_terminal)

# ==================== STATUS BAR ====================

status_bar = tk.Frame(root, bg="#181b21", height=24)
status_bar.place(x=80, y=696, width=1200, height=24)

status_label = tk.Label(
    status_bar, text="  Python Ready", font=(FONT, 9), bg="#181b21", fg=TEXT
)
status_label.pack(side="left", fill="y")

cursor_label = tk.Label(
    status_bar, text="Ln 1, Col 1   ", font=(FONT, 9), bg="#181b21", fg=TEXT
)
cursor_label.pack(side="right", fill="y")

# ==================== KEYBOARD SHORTCUTS ====================

root.bind("<Control-n>", lambda event: new_file())
root.bind("<Control-o>", lambda event: open_file())
root.bind("<Control-s>", lambda event: save_file())
root.bind("<F5>", lambda event: run_code())


def on_close():
    if confirm_save():
        root.destroy()


root.protocol("WM_DELETE_WINDOW", on_close)

# Initial state
refresh_lines()
update_title()
update_status()

root.mainloop()
