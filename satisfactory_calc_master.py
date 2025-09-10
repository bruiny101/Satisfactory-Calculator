import tkinter as tk
from tkinter import messagebox
import lib.scrape_data as scrape_data
import lib.recipe_optimization as recipe_op
import shutil

class MaterialSelector(tk.Frame):
    def __init__(self, parent, materials_list):
        super().__init__(parent)
        self.materials_list = materials_list
        self.selected_materials = []  # List of dicts: {name, entry_widget, frame}
        self.filtered_materials = materials_list.copy()

        # Search bar
        self.search_var = tk.StringVar()
        self.search_var.trace_add('write', self.update_dropdown)
        search_entry = tk.Entry(self, textvariable=self.search_var, width=30)
        search_entry.grid(row=0, column=0, padx=5, pady=5, sticky='ew')

        # Dropdown menu (Listbox)
        self.dropdown = tk.Listbox(self, height=6, exportselection=False)
        self.dropdown.grid(row=1, column=0, padx=5, pady=5, sticky='ew')
        self.dropdown.bind('<<ListboxSelect>>', self.on_select)
        self.update_dropdown()

        # Frame for selected materials (with scrollbar)
        self.selected_frame_container = tk.Frame(self)
        self.selected_frame_container.grid(row=2, column=0, sticky='nsew')
        self.selected_frame_container.grid_rowconfigure(0, weight=1)
        self.selected_frame_container.grid_columnconfigure(0, weight=1)

        self.canvas = tk.Canvas(self.selected_frame_container, height=200)
        self.scrollbar = tk.Scrollbar(self.selected_frame_container, orient='vertical', command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas)
        self.scrollable_frame.bind(
            "<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.grid(row=0, column=0, sticky='nsew')
        self.scrollbar.grid(row=0, column=1, sticky='ns')

        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)

    def update_dropdown(self, *args):
        search_text = self.search_var.get().lower()
        self.filtered_materials = [m for m in self.materials_list if search_text in m.lower()]
        self.dropdown.delete(0, tk.END)
        for mat in self.filtered_materials:
            self.dropdown.insert(tk.END, mat)

    def on_select(self, event):
        selection = self.dropdown.curselection()
        if selection:
            mat_name = self.filtered_materials[selection[0]]
            self.add_material_row(mat_name)

    def add_material_row(self, mat_name):
        # Allow multiple of same material
        row_frame = tk.Frame(self.scrollable_frame)
        row_frame.pack(fill='x', pady=2)
        label = tk.Label(row_frame, text=mat_name, width=25, anchor='w')
        label.pack(side='left', padx=5)
        float_var = tk.StringVar()
        entry = tk.Entry(row_frame, textvariable=float_var, width=10)
        entry.pack(side='left', padx=5)
        entry.bind('<FocusOut>', lambda e, v=float_var: self.validate_float(v, entry))
        entry.bind('<KeyRelease>', lambda e, v=float_var: self.validate_float(v, entry))
        remove_btn = tk.Button(row_frame, text='X', width=2, command=lambda: self.remove_material_row(row_frame))
        remove_btn.pack(side='left', padx=5)
        self.selected_materials.append({'name': mat_name, 'entry': entry, 'frame': row_frame, 'var': float_var})

    def remove_material_row(self, row_frame):
        for i, mat in enumerate(self.selected_materials):
            if mat['frame'] == row_frame:
                mat['frame'].destroy()
                del self.selected_materials[i]
                break

    def validate_float(self, var, entry):
        val = var.get()
        try:
            f = float(val)
            if f > 0:
                entry.config(bg='white')
            else:
                entry.config(bg='mistyrose')
        except ValueError:
            if val == '':
                entry.config(bg='white')
            else:
                entry.config(bg='mistyrose')

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Satisfactory Calculator")
        self.root.geometry("600x600")
        self.MATERIALS_DF = recipe_op.get_materials_df(scrape_data.DEFAULT_RECIPE_JSON_FILE)
        self.materials_list = list(self.MATERIALS_DF['Material'])

        # Material selector (top center)
        self.selector = MaterialSelector(self.root, self.materials_list)
        self.selector.place(relx=0.5, rely=0.05, anchor='n', relwidth=0.9)

        # Frame for button at bottom right
        frame = tk.Frame(self.root)
        frame.place(relx=1.0, rely=1.0, anchor='se')
        button = tk.Button(frame, text="Update Recipes", width=15, height=5, command=self.on_update_recipes)
        button.pack()

    def show_scrollable_dialog(self, title, message):
        dialog = tk.Toplevel(self.root)
        dialog.title(title)
        dialog.geometry("600x500")
        dialog.transient(self.root)
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

    def on_update_recipes(self):
        try:
            # Get new data (do not overwrite yet)
            temp_json_file = scrape_data.TEMP_RECIPE_JSON_FILE
            scrape_data.update_recipes_table_from_html(json_file=temp_json_file)

            # Show diff to user in a scrollable dialog
            diff_msg = scrape_data.get_recipe_diffs(scrape_data.DEFAULT_RECIPE_JSON_FILE, temp_json_file)
            diff_msg += "\n\nAccept updates?"

            result = self.show_scrollable_dialog("Confirm Recipe Updates", diff_msg)

            if result:
                # Overwrite file by moving temp file
                shutil.move(temp_json_file, scrape_data.DEFAULT_RECIPE_JSON_FILE)
                messagebox.showinfo("Success", f"Recipes updated and saved to {scrape_data.DEFAULT_RECIPE_JSON_FILE}.")
                self.MATERIALS_DF = recipe_op.get_materials_df(scrape_data.DEFAULT_RECIPE_JSON_FILE)
                self.materials_list = list(self.MATERIALS_DF['Material'])
                self.selector.materials_list = self.materials_list
                self.selector.update_dropdown()
            else:
                messagebox.showinfo("Cancelled", "Updates were cancelled. Old recipes preserved.")
        except Exception as e:
            messagebox.showerror("Error", str(e))

if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()
