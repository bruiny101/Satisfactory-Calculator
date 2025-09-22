import tkinter as tk
from tkinter import messagebox
from tkinter import filedialog
import lib.scrape_data as scrape_data
import lib.recipe_optimization as recipe_op
import shutil, os, json, pandas as pd

CACHE_DIR = os.path.join(os.getcwd(), '.cache')
ADVANCED_OPTIONS_FILE = os.path.join(CACHE_DIR, 'user_advanced_options.json')

class MaterialSelector(tk.Frame):
    def __init__(self, parent, MATERIALS_DF, RECIPES, calculate_callback, open_advanced_options_callback):
        super().__init__(parent)
        self.calculate_callback = calculate_callback
        self.open_advanced_options_callback = open_advanced_options_callback

        # Search bar
        self.search_var = tk.StringVar()
        self.search_var.trace_add('write', self.update_dropdown)
        search_entry = tk.Entry(self, textvariable=self.search_var, width=30)
        search_entry.grid(row=0, column=0, padx=5, pady=5, sticky='ew')

        # Dropdown menu (Listbox)
        self.dropdown = tk.Listbox(self, height=6, exportselection=False)
        self.dropdown.grid(row=1, column=0, padx=5, pady=5, sticky='ew')
        self.dropdown.bind('<<ListboxSelect>>', self.on_select)
        self.reset_available_recipes(RECIPES, MATERIALS_DF)

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

        # Advanced Options button to the left of Calculate
        adv_btn = tk.Button(self.selected_frame_container, text="Advanced Options", width=15, height=2, command=self.open_advanced_options_callback)
        adv_btn.grid(row=1, column=0, pady=10, sticky='w')
        calc_btn = tk.Button(self.selected_frame_container, text="Calculate", width=15, height=2, command=self.calculate_callback)
        calc_btn.grid(row=1, column=1, pady=10, sticky='e')

    def reset_recipes(self, RECIPES, MATERIALS_DF):
        self.MATERIALS_DF = MATERIALS_DF
        self.RECIPES = RECIPES
        self.available_recipes = RECIPES.copy()
        self.selected_materials = []  # List of dicts: {name, entry_widget, frame}
        self.available_materials = sorted(MATERIALS_DF['Material'].tolist())
        self.filtered_materials = self.available_materials.copy()

    def reset_available_recipes(self, RECIPES, MATERIALS_DF):
        self.reset_recipes(RECIPES, MATERIALS_DF)
        self.user_advanced_options = self.load_user_advanced_options()
        self.update_recipes_by_unlocked_conditions()
        self.update_available_materials()
        self.update_dropdown()

    def load_user_advanced_options(self) -> dict | int:
        cache_file = ADVANCED_OPTIONS_FILE
        if os.path.exists(cache_file):
            with open(cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            return -1
        return {"tier": None, "sections": [], "mam": {}, "alternate": []}

    def update_recipes_by_unlocked_conditions(self):
        # If not user advanced options, return all materials
        if isinstance(self.user_advanced_options, int):
            if self.user_advanced_options == -1:
                return
            raise ValueError("Invalid user advanced options data.")
  

        unlocked_recipes = []
        tier = self.user_advanced_options.get("tier")
        sections = self.user_advanced_options.get("sections", [])
        mam = self.user_advanced_options.get("mam", {})
        alternate = self.user_advanced_options.get("alternate", [])

        for recipe in self.RECIPES:
            ub = recipe.get('Unlocked by', {})
            # If no unlock conditions, always unlocked
            if not ub:
                unlocked_recipes.append(recipe)
                continue
            # Alternate unlock
            # The alternate field is ONLY unlocked if the user specifically selects it, and the tier/MAM conditions are satisfied
            if ub.get('Alternate'):
                alt_name = recipe.get('Recipe', '')
                if not (alternate and alt_name and alt_name in alternate):
                    continue
            if tier is None and not mam:
                unlocked_recipes.append(recipe)
                continue
            # Tier unlock
            if tier is not None and ub.get('Tier'):
                t = ub['Tier'][0]
                lvl = t.get('Level')
                sec = t.get('Section')
                if lvl is not None and ((lvl < tier) or (lvl == tier and sec in sections)):
                    unlocked_recipes.append(recipe)
                    continue
            # MAM unlock
            if mam and ub.get('MAM Research'):
                m = ub['MAM Research'][0]
                tree = m.get('Tree')
                node = m.get('Node')
                if tree in mam and node in mam[tree]:
                    unlocked_recipes.append(recipe)
                    continue

        self.available_recipes = unlocked_recipes
    
    def update_available_materials(self):
        unlocked_materials = set()
        for recipe in self.available_recipes:
            products = recipe.get('Products', [])
            ingredients = recipe.get('Ingredients', [])
            for product in products:
                mat = product.get('Material', '')
                if mat:
                    unlocked_materials.add(mat)
            for ingredient in ingredients:
                mat = ingredient.get('Material', '')
                if mat:
                    unlocked_materials.add(mat)
        self.available_materials = list(sorted(unlocked_materials))

    def update_dropdown(self, *args):
        search_text = self.search_var.get().lower()
        self.filtered_materials = [m for m in self.available_materials if search_text in m.lower()]
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
        if os.path.exists(scrape_data.DEFAULT_RECIPE_JSON_FILE):
            self.load_default_recipes()
        else:
            self.RECIPES = []
            self.MATERIALS_DF = pd.DataFrame(columns=['Material', 'Produced', 'Required', 'Requested', 'Satisfied', 'Base Material', 'End Material', 'Tier', 'Section', 'MAM Research', 'Alternate', 'No Unlock'])

        # Material selector (top center)
        self.selector = MaterialSelector(self.root, self.MATERIALS_DF, self.RECIPES, self.calculate_requested, self.open_advanced_options)
        self.selector.place(relx=0.5, rely=0.05, anchor='n', relwidth=0.9)

        # Frame for button at bottom right
        frame = tk.Frame(self.root)
        frame.place(relx=1.0, rely=1.0, anchor='se')
        button = tk.Button(frame, text="Update Recipes", width=15, height=5, command=self.on_update_recipes)
        button.pack()

    @staticmethod
    def exception_wrapper(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                messagebox.showerror("Error", str(e))
        return wrapper

    def load_default_recipes(self):
        self.RECIPES = scrape_data.load_recipes_from_json(scrape_data.DEFAULT_RECIPE_JSON_FILE)
        self.MATERIALS_DF = scrape_data.get_materials_df(self.RECIPES) 

    @exception_wrapper
    def open_advanced_options(self):
        cache_dir = CACHE_DIR
        cache_file = ADVANCED_OPTIONS_FILE
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)

        # Gather data from the JSON file directly
        tier_dict = {}
        mam_dict = {}
        alternate_recipes = set()

        for recipe in self.RECIPES:
            ub = recipe.get('Unlocked by', {})
            # Tier
            if ub and isinstance(ub, dict) and ub.get('Tier'):
                for t in ub['Tier']:
                    lvl = t.get('Level')
                    sec = t.get('Section')
                    if lvl is not None:
                        tier_dict.setdefault(lvl, set()).add(sec)
            # MAM
            if ub and isinstance(ub, dict) and ub.get('MAM Research'):
                for m in ub['MAM Research']:
                    tree = m.get('Tree')
                    node = m.get('Node')
                    if tree:
                        mam_dict.setdefault(tree, set()).add(node)
            # Alternate
            if ub and isinstance(ub, dict) and ub.get('Alternate'):
                if ub['Alternate']:
                    alt_name = recipe.get('Recipe', '')
                    if alt_name:
                        alternate_recipes.add(alt_name)

        # Sort tiers and sections
        sorted_tiers = sorted(tier_dict.keys())
        tier_sections = {lvl: sorted([s for s in tier_dict[lvl] if s]) for lvl in sorted_tiers}
        # Sort MAM trees and nodes
        sorted_trees = sorted(mam_dict.keys())
        mam_nodes = {tree: sorted([n for n in mam_dict[tree] if n]) for tree in sorted_trees}
        # Sort alternates
        alternate_recipes = sorted(list(alternate_recipes))

        # Load previous options if exist
        selected = {
            'tier': None,
            'sections': [],
            'mam': {},
            'alternate': []
        }
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    prev = json.load(f)
                    selected.update(prev)
            except Exception:
                pass

        # Create window
        adv_win = tk.Toplevel(self.root)
        adv_win.title('Advanced Options')
        adv_win.geometry('700x700')
        adv_win.transient(self.root)
        adv_win.grab_set()

        # --- Main scrollable content frame ---
        main_frame = tk.Frame(adv_win)
        main_frame.pack(fill='both', expand=True)
        canvas = tk.Canvas(main_frame, borderwidth=0)
        scroll_y = tk.Scrollbar(main_frame, orient='vertical', command=canvas.yview)
        canvas.configure(yscrollcommand=scroll_y.set)
        scroll_y.pack(side='right', fill='y')
        canvas.pack(side='left', fill='both', expand=True)
        content_frame = tk.Frame(canvas)
        canvas.create_window((0, 0), window=content_frame, anchor='nw')
        def _on_frame_configure(event):
            canvas.configure(scrollregion=canvas.bbox('all'))
        content_frame.bind('<Configure>', _on_frame_configure)

        # --- Tier selection ---
        tier_frame = tk.Frame(content_frame)
        tier_frame.pack(fill='x', pady=10)
        tk.Label(tier_frame, text='Tier Selection:', font=('TkDefaultFont', 12, 'bold')).pack(side='left', padx=5)
        tier_var = tk.StringVar(value=str(selected['tier']) if selected['tier'] is not None else '')
        section_vars = {}

        def update_sections(*args):
            # Destroy any existing section widgets to refresh the UI
            for w in section_vars.values():
                w['frame'].destroy()
            section_vars.clear()
            sel_tier = tier_var.get()
            if sel_tier and sel_tier.isdigit():
                sec_list = tier_sections.get(int(sel_tier), [])
            else:
                sec_list = []
            sec_frame = tk.Frame(tier_frame)
            sec_frame.pack(side='left', padx=10)
            tk.Label(sec_frame, text='Sections:').pack(anchor='w')
            # Create checkboxes for each section
            sec_vars = {}
            for sec in sec_list:
                var = tk.BooleanVar(value=sec in selected['sections'])
                cb = tk.Checkbutton(sec_frame, text=sec, variable=var, anchor='w')
                cb.pack(anchor='w', padx=5)
                sec_vars[sec] = var
            # Check/Uncheck all buttons
            btns_frame = tk.Frame(sec_frame)
            btns_frame.pack(anchor='w', pady=5)
            def check_all():
                for v in sec_vars.values():
                    v.set(True)
            def uncheck_all():
                for v in sec_vars.values():
                    v.set(False)
            tk.Button(btns_frame, text='Check all', width=10, command=check_all).pack(side='left', padx=2)
            tk.Button(btns_frame, text='Uncheck all', width=10, command=uncheck_all).pack(side='left', padx=2)
            # Store references for later access
            section_vars['sections'] = {'sec_list': sec_list, 'frame': sec_frame, 'sec_vars': sec_vars}

        tier_dropdown = tk.OptionMenu(tier_frame, tier_var, *[str(t) for t in sorted_tiers], command=update_sections)
        tier_dropdown.pack(side='left', padx=5)
        update_sections()

        # --- MAM Research Trees ---
        mam_frame = tk.Frame(content_frame)
        mam_frame.pack(fill='x', pady=10)
        tk.Label(mam_frame, text='MAM Research Trees:', font=('TkDefaultFont', 12, 'bold')).pack(anchor='w', padx=5)
        mam_node_vars = {}
        for tree in sorted_trees:
            tree_label = tk.Label(mam_frame, text=tree, font=('TkDefaultFont', 10, 'bold'))
            tree_label.pack(anchor='w', padx=10)
            node_frame = tk.Frame(mam_frame)
            node_frame.pack(fill='x', padx=20)

            # Create columns of checkboxes for nodes
            columns = [mam_nodes[tree][i:i+4] for i in range(0, len(mam_nodes[tree]), 4)]
            for col in columns:
                col_frame = tk.Frame(node_frame)
                col_frame.pack(side='left', padx=10, anchor='n')
                for node in col:
                    var = tk.BooleanVar(value=node in selected['mam'].get(tree, []))
                    cb = tk.Checkbutton(col_frame, text=node, variable=var, anchor='w')
                    cb.pack(anchor='w')
                    mam_node_vars.setdefault(tree, {})[node] = var

        # --- Alternate Recipes ---
        alt_frame = tk.Frame(content_frame)
        alt_frame.pack(fill='x', pady=10)
        tk.Label(alt_frame, text='Alternate Recipes:', font=('TkDefaultFont', 12, 'bold')).pack(anchor='w', padx=5)
        alt_listbox = tk.Listbox(alt_frame, selectmode='multiple', height=8)
        for recipe in alternate_recipes:
            alt_listbox.insert(tk.END, recipe)
        alt_listbox.pack(fill='x', padx=10)
        # Preselect
        for i, recipe in enumerate(alternate_recipes):
            if recipe in selected['alternate']:
                alt_listbox.selection_set(i)

        # Bind mouse wheel to canvas scrolling
        def _on_mouse_wheel(event):
            canvas.yview_scroll(-1 * (event.delta // 120), 'units')

        canvas.bind_all("<MouseWheel>", _on_mouse_wheel)

        # Unbind mouse wheel globally when the window is closed
        def on_close():
            canvas.unbind_all("<MouseWheel>")  # Remove global binding
            self.selector.reset_available_recipes(self.RECIPES, self.MATERIALS_DF)  # Refresh main selector based on new options
            adv_win.destroy()

        adv_win.protocol("WM_DELETE_WINDOW", on_close)

        # Bind mouse wheel to listbox scrolling when hovered
        def _on_listbox_mouse_wheel(event):
            alt_listbox.yview_scroll(-1 * (event.delta // 120), 'units')

        alt_listbox.bind("<Enter>", lambda e: canvas.unbind_all("<MouseWheel>"))
        alt_listbox.bind("<Leave>", lambda e: canvas.bind_all("<MouseWheel>", _on_mouse_wheel))
        alt_listbox.bind("<MouseWheel>", _on_listbox_mouse_wheel)

        # --- Save/Exit buttons (fixed at bottom) ---
        btn_frame = tk.Frame(adv_win)
        btn_frame.pack(side='bottom', fill='x', pady=10)
        def save_options():
            # Tier
            sel_tier = tier_var.get()
            sel_sections = []
            if 'sections' in section_vars:
                sec_vars = section_vars['sections']['sec_vars']
                sel_sections = [sec for sec, var in sec_vars.items() if var.get()]
            # MAM
            sel_mam = {}
            for tree, nodes in mam_node_vars.items():
                sel_mam[tree] = [node for node, var in nodes.items() if var.get()]
            # Alternate
            sel_alt = [alternate_recipes[i] for i in alt_listbox.curselection()]
            # Save
            options = {
                'tier': int(sel_tier) if sel_tier.isdigit() else None,
                'sections': sel_sections,
                'mam': sel_mam,
                'alternate': sel_alt
            }
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(options, f, indent=2)
            messagebox.showinfo('Saved', 'Advanced options saved.')
        save_btn = tk.Button(btn_frame, text='Save', width=15, command=save_options)
        save_btn.pack(side='left', padx=40)
        exit_btn = tk.Button(btn_frame, text='Exit', width=15, command=on_close)
        exit_btn.pack(side='right', padx=40)

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
        result = {'value': bool()}

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

    @exception_wrapper
    def on_update_recipes(self):
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
            self.load_default_recipes()
            self.selector.reset_available_recipes(self.RECIPES, self.MATERIALS_DF)
        else:
            messagebox.showinfo("Cancelled", "Updates were cancelled. Old recipes preserved.")

    @exception_wrapper
    def calculate_requested(self):
        # Reset all Requested values to 0.0
        self.MATERIALS_DF['Requested'] = 0.0
        # For each selected material, add its float value to Requested
        for mat in self.selector.selected_materials:
            name = mat['name']
            try:
                val = float(mat['var'].get())
                if val > 0:
                    idx = self.MATERIALS_DF[self.MATERIALS_DF['Material'] == name].index
                    if len(idx) > 0:
                        self.MATERIALS_DF.loc[idx, 'Requested'] += val
            except ValueError:
                continue

        # Update Satisfied column
        self.MATERIALS_DF['Satisfied'] = self.MATERIALS_DF['Produced'] >= self.MATERIALS_DF['Required'] + self.MATERIALS_DF['Requested']

        # Only include materials/recipes currently available to be displayed in the MaterialSelector
        available_recipes = self.selector.available_recipes
        available_materials = self.selector.available_materials
        filtered_df = self.MATERIALS_DF[self.MATERIALS_DF['Material'].isin(available_materials)].copy()

        # Run recipe optimization
        solution, total_power = recipe_op.run_recipe_optimization(filtered_df, available_recipes)

        # Build mapping from recipe name to machine
        recipe_to_machine = {}
        for recipe in self.RECIPES:
            name = recipe.get('Recipe')
            produced_in = recipe.get('Produced in', [])
            if produced_in:
                recipe_to_machine[name] = produced_in[0].get('Machine', 'Unknown Machine')

        # Group solution by machine
        machine_groups = {}
        for recipe, count in solution.items():
            if count > 0:
                machine = recipe_to_machine.get(recipe, 'Unknown Machine')
                machine_groups.setdefault(machine, []).append((recipe, count))

        # Build result string for display and file output (grouped by machine)
        result_str_display = f"Total Power Consumption: {total_power:.2f} MW\n\n"
        result_str_file = result_str_display
        for machine, recipes in machine_groups.items():
            result_str_display += f"[{machine}]\n"
            result_str_file += f"[{machine}]\n"
            for recipe, count in recipes:
                result_str_display += f"  {recipe}: {count}\n"
                result_str_file += f"  {recipe}: {count}\n"
            result_str_display += "\n"
            result_str_file += "\n"

        # Show scrollable dialog with save option and bold total power
        def show_optimization_result_dialog():
            dialog = tk.Toplevel(self.root)
            dialog.title("Optimization Result")
            dialog.geometry("600x500")
            dialog.transient(self.root)
            dialog.grab_set()

            # Text widget with vertical scrollbar
            text_frame = tk.Frame(dialog)
            text_frame.pack(fill=tk.BOTH, expand=True)
            scrollbar = tk.Scrollbar(text_frame)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            text = tk.Text(text_frame, wrap=tk.WORD, yscrollcommand=scrollbar.set)
            # Insert total power in bold
            text.tag_configure('bold', font=('TkDefaultFont', 10, 'bold'))
            text.insert(tk.END, "Total Power Consumption: ", ())
            text.insert(tk.END, f"{total_power:.2f} MW\n\n", 'bold')
            text.insert(tk.END, "Optimal Recipe Usage (min power):\n\n")
            for machine, recipes in machine_groups.items():
                text.insert(tk.END, f"[{machine}]\n", 'bold')
                for recipe, count in recipes:
                    text.insert(tk.END, f"  {recipe}: {count}\n")
                text.insert(tk.END, "\n")
            text.config(state=tk.DISABLED)
            text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.config(command=text.yview)

            # Button frame
            btn_frame = tk.Frame(dialog)
            btn_frame.pack(fill=tk.X, pady=10)
            def save_to_file():
                file_path = filedialog.asksaveasfilename(
                    title="Save Optimization Result",
                    defaultextension=".txt",
                    filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")]
                )
                if file_path:
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(result_str_file)
            save_btn = tk.Button(btn_frame, text="Save to File", width=15, command=save_to_file)
            save_btn.pack(side=tk.LEFT, padx=20)
            close_btn = tk.Button(btn_frame, text="Close", width=10, command=dialog.destroy)
            close_btn.pack(side=tk.RIGHT, padx=20)
            dialog.wait_window()

        show_optimization_result_dialog()

if __name__ == "__main__":
    root = tk.Tk()

    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR)

    app = App(root)
    root.mainloop()
