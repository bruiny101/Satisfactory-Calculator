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

        # Show diff to user (simple string comparison)
        diff_msg = scrape_data.get_recipe_diffs(scrape_data.DEFAULT_RECIPE_JSON_FILE, temp_json_file)
        diff_msg += "\n\nAccept updates?"
        result = messagebox.askyesno("Confirm Recipe Updates", diff_msg)

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
