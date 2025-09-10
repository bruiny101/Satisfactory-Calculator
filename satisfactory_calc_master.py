import tkinter as tk
from tkinter import messagebox
import lib.scrape_data as scrape_data
import shutil
from tkinter import simpledialog

def on_update_recipes():
    try:
        # Get new data (do not overwrite yet)
        temp_json_file = scrape_data.TEMP_RECIPE_JSON_FILE
        scrape_data.update_recipes_table_from_html(json_file=temp_json_file)

        # Show diff to user in a scrollable dialog
        diff_msg = scrape_data.get_recipe_diffs(scrape_data.DEFAULT_RECIPE_JSON_FILE, temp_json_file)
        diff_msg += "\n\nAccept updates?"

        def show_scrollable_dialog(title, message):
            dialog = tk.Toplevel(root)
            dialog.title(title)
            dialog.geometry("600x500")
            dialog.transient(root)
            dialog.grab_set()

            # Text widget with vertical scrollbar
            text_frame = tk.Frame(dialog)
            text_frame.pack(fill=tk.BOTH, expand=True)
            scrollbar = tk.Scrollbar(text_frame)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            text = tk.Text(text_frame, wrap=tk.WORD, yscrollcommand=scrollbar.set)
            text.insert(tk.END, message)
            text.config(state=tk.DISABLED)
            text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.config(command=text.yview)

            # Button frame
            btn_frame = tk.Frame(dialog)
            btn_frame.pack(fill=tk.X, pady=10)
            result = {'value': None}

            def accept():
                result['value'] = True
                dialog.destroy()
            def decline():
                result['value'] = False
                dialog.destroy()

            yes_btn = tk.Button(btn_frame, text="Accept", width=10, command=accept)
            yes_btn.pack(side=tk.LEFT, padx=20)
            no_btn = tk.Button(btn_frame, text="Decline", width=10, command=decline)
            no_btn.pack(side=tk.RIGHT, padx=20)

            dialog.wait_window()
            return result['value']

        result = show_scrollable_dialog("Confirm Recipe Updates", diff_msg)

        if result:
            # Overwrite file by moving temp file
            shutil.move(temp_json_file, scrape_data.DEFAULT_RECIPE_JSON_FILE)
            messagebox.showinfo("Success", f"Recipes updated and saved to {scrape_data.DEFAULT_RECIPE_JSON_FILE}.")
        else:
            messagebox.showinfo("Cancelled", "Updates were cancelled. Old recipes preserved.")
    except Exception as e:
        messagebox.showerror("Error", str(e))

root = tk.Tk()
root.title("Satisfactory Calculator")
root.geometry("400x400")

# Center frame for button
frame = tk.Frame(root)
frame.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

# Square button
button = tk.Button(frame, text="Update Recipes", width=15, height=5, command=on_update_recipes)
button.pack()

root.mainloop()
