import pandas as pd
import requests, re, json, os
from io import StringIO

DEFAULT_RECIPE_URL               = "https://satisfactory.wiki.gg/wiki/Recipes"
DEFAULT_RECIPE_JSON_FILE         = os.path.join("json_data", "Satisfactory_recipes.json")
TEMP_RECIPE_JSON_FILE            = os.path.join("json_data", "temp_Satisfactory_recipes.json")
DEFAULT_RECIPE_DF_COLS           = ["Recipe", "Ingredients", "Produced in", "Products", "Unlocked by"]

MACHINE_POWER_CONSUMPTION = {
    "Assembler" : 15,
    "Manufacturer": 55,
    "Constructor": 4,
    "Smelter" : 4,
    "Foundry": 16,
    "Blender": 75,
    "Packager": 10,
    "Refinery": 30,
    "Particle Accelerator": 1000,
    # "Nuclear Power Plant": -2500,  # Negative for power generation
    "Nuclear Power Plant": 1,  # Negative for power generation
    "Converter": 250
}

# Theoretical maximum resource extraction rates (per minute) based on:
# https://satisfactory.fandom.com/wiki/Resource_node
RESOURCE_MAXIMUMS = {
    "Coal": 42300.0,
    "Crude Oil": 12600.0,
    "Nitrogen Gas": 12000.0,
    "Bauxite": 12300.0,
    "Copper Ore": 36900.0,
    "Caterium Ore": 15000.0,
    "Iron Ore": 92100.0,
    "Uranium": 2100.0,
    "Raw Quartz": 13500.0,
    "SAM": 10200.0,
    "Limestone": 69300.0,
    "Sulfur": 10800.0,
    "Water": 13125.0
}

def parse_machine_and_power(produced_in_str):
    """
    Parses the 'Produced in' string and returns a dict with 'Machine' and 'Pwr Cons'.
    If a power range is present, uses the max value. Otherwise, uses MACHINE_POWER_CONSUMPTION.
    """
    import re

    # Pattern for format 2: "<Machine> <number> sec <Power Range> MW"
    match = re.match(r'([A-Za-z ]+?)\s+\d+(\.\d+)?\s+sec\s+([\d,\.]+)\s*-\s*([\d,\.]+)\s*MW', produced_in_str)
    if match:
        machine = match.group(1).strip()
        max_power = float(match.group(4).replace(',', ''))
        return [{"Machine": machine, "Pwr Cons": max_power}]

    # Pattern for format 2 (single value): "<Machine> <number> sec <Power> MW"
    match = re.match(r'([A-Za-z ]+?)\s+\d+(\.\d+)?\s+sec\s+([\d,\.]+)\s*MW', produced_in_str)
    if match:
        machine = match.group(1).strip()
        power = float(match.group(3).replace(',', ''))
        return [{"Machine": machine, "Pwr Cons": power}]
    
    # Pattern for format 1: "<Machine> <number> sec"
    match = re.match(r'([A-Za-z ]+?)\s+\d+(\.\d+)?\s+sec', produced_in_str)
    if match:
        machine = match.group(1).strip()
        power = MACHINE_POWER_CONSUMPTION.get(machine, None)
        return [{"Machine": machine, "Pwr Cons": power}]

    # If no match, return an empty list
    return []

def parse_materials(s):
    if not isinstance(s, str):
        return []
    pattern = r'[\d\.]+ x ([^0-9]+?)([\d\.]+) / min'
    matches = re.findall(pattern, s)
    return [{"Material": m[0].strip(), "Quantity": float(m[1].strip())} for m in matches]

def scrub_table_data(cell):
    if isinstance(cell, str):
        # Replace non-breaking space with regular space
        cell = cell.replace('\xa0', ' ')
        cell = cell.replace('\u00d7', 'x')

        # Remove any string matching 'Craft Bench  × <variable number>'
        patterns = [r'Craft Bench\s+x\s+\d+', r'Equipment Workshop\s+x\s+\d+']
        # Remove patterns from cell strings
        for pattern in patterns:
            cell = re.sub(pattern, '', cell)
        cell = cell.strip()
    return cell

def update_recipes_table_from_html( url = DEFAULT_RECIPE_URL, json_file = DEFAULT_RECIPE_JSON_FILE ):
    # Fetch the HTML content
    response = requests.get(url)
    response.raise_for_status()
    html = response.text

    # Use pandas to read all tables in the HTML
    tables = pd.read_html(StringIO(html))

    # Find the table with the expected columns
    required_columns = DEFAULT_RECIPE_DF_COLS
    columns_found = False
    for table in tables:
        columns = table.columns.astype(str)
        if all(col in columns for col in required_columns):
            columns_found = True
            # Select only the relevant columns
            df = table[required_columns]
            df = df.map(scrub_table_data)
            # Remove rows where 'Produced in' is empty or equal to ""
            df = df[df["Produced in"].replace("", pd.NA).notna()]
            # Parse 'Ingredients', 'Products' and 'Produced In' columns
            df["Products"]    = df["Products"].apply(parse_materials)
            df["Ingredients"] = df["Ingredients"].apply(parse_materials)
            df["Produced in"] = df["Produced in"].apply(parse_machine_and_power)
            break

    if columns_found:
        # Save to JSON file
        df.to_json(json_file, orient="records", indent=2)

        # Build dictionary of base materials and fetch extraction MJ values from wiki
        materials_df = get_materials_df(json_file)
        base_materials = materials_df[materials_df["Base Material"] == True]["Material"].tolist()
        # Add base material extraction recipes to the DataFrame
        new_rows = []
        for mat in base_materials:
            produced_in = "Resource Extraction"
            try:
                url = f"https://satisfactory.fandom.com/wiki/{mat.replace(' ', '_')}"
                resp = requests.get(url)
                resp.raise_for_status()
                match = re.search(r'It takes about <span[^>]*title="([\d\.]+)"', resp.text)
                if match:
                    power = float(match.group(1)) / 60.0  # Convert from MJ/min to MW
                elif mat == "Water":
                    power = 10.0 / 60.0  # Convert from MJ/min to MW
                else:
                    print(f"Could not find extraction MJ value for material: {mat} at {url}")
                    power = 10000 # set a high power value to discourage use
                    produced_in = "Hand Crank"
            except Exception as e:
                print(f"Error fetching data for material: {mat} at {url}: {e}")
                power = 10000 # set a high power value to discourage use
                produced_in = "Hand Crank"

            new_rows.append({
            "Recipe": f"{mat} Extraction",
            "Ingredients": [],
            "Produced in": [{"Machine": produced_in, "Pwr Cons": power}],
            "Products": [{"Material": mat, "Quantity": 1.0}],
            "Unlocked by": ""
            })

        # Append new rows to the DataFrame and save again
        if new_rows:
            df = pd.concat([df, pd.DataFrame(new_rows)], ignore_index=True)
            df.to_json(json_file, orient="records", indent=2)
        return
    
    raise ValueError("Could not find the a table with all the required columns.")

def get_recipe_diffs(old_json_file, new_json_file):

    def compare_lists(field, list1, list2):
        if field in ["Ingredients", "Products"]:
            cmp1 = "Material"
            cmp2 = "Quantity"
        elif field == "Produced in":
            cmp1 = "Machine"
            cmp2 = "Pwr Cons"
        else:
            raise ValueError(f"Unsupported field for comparison: {field}")
        
        set1 = set((d[cmp1], d[cmp2]) for d in list1 or [])
        set2 = set((d[cmp1], d[cmp2]) for d in list2 or [])
        if set1 != set2:
            return f"    Old: {sorted(set1)}\n    New: {sorted(set2)}"
        return None
    
    # Check if both files exist
    if not os.path.isfile(old_json_file):
        # raise FileNotFoundError(f"Old JSON file not found: {old_json_file}")
        return "Old JSON file not found. Assuming all recipes are new."
    if not os.path.isfile(new_json_file):
        raise FileNotFoundError(f"New JSON file not found: {new_json_file}")

    # Load both files
    with open(old_json_file, "r", encoding="utf-8") as f:
        old_data = json.load(f)
    with open(new_json_file, "r", encoding="utf-8") as f:
        new_data = json.load(f)

    # Index by recipe name
    old_recipes = {r["Recipe"]: r for r in old_data}
    new_recipes = {r["Recipe"]: r for r in new_data}

    old_names = set(old_recipes.keys())
    new_names = set(new_recipes.keys())

    added = new_names - old_names
    removed = old_names - new_names
    common = old_names & new_names

    fields_to_compare = DEFAULT_RECIPE_DF_COLS
    diff_lines = []
    if added:
        diff_lines.append("Recipes added:\n" + "\n".join(sorted(added)))
    if removed:
        diff_lines.append("Recipes removed:\n" + "\n".join(sorted(removed)))
    for name in sorted(common):
        changes = []
        for field in fields_to_compare:
            old_val = old_recipes[name].get(field, None)
            new_val = new_recipes[name].get(field, None)
            if field in ["Ingredients", "Products", "Produced in"]:
                diff = compare_lists(field, old_val, new_val)
                if diff:
                    changes.append(f"  Field '{field}' changed:\n{diff}")
            else:
                if old_val != new_val:
                    changes.append(f"  Field '{field}' changed:\n    Old: {old_val}\n    New: {new_val}")
        if changes:
            diff_lines.append(f"Recipe changed: {name}\n" + "\n".join(changes))
    if not diff_lines:
        diff_lines.append("No differences found.")

    return "\n\n".join(diff_lines)

def get_materials_df(json_file):
    # Load recipe data
    with open(json_file, "r", encoding="utf-8") as f:
        recipes = json.load(f)

    # Collect all materials from Ingredients and Products
    ingredient_materials = set()
    product_materials = set()

    for recipe in recipes:
        for ing in recipe.get("Ingredients", []):
            ingredient_materials.add(ing["Material"])
        for prod in recipe.get("Products", []):
            product_materials.add(prod["Material"])

    all_materials = ingredient_materials | product_materials

    # Build rows for DataFrame
    rows = []
    for mat in sorted(all_materials):
        base = mat in ingredient_materials and mat not in product_materials
        end = mat in product_materials and mat not in ingredient_materials
        try:
            produced = RESOURCE_MAXIMUMS[mat]
            base = True  # If it's a resource node material, it's a base material
        except KeyError:
            # If not found, it means it's not a resource node material
            produced = 0.0

        rows.append({
            "Material": mat,
            "Requested": 0.0,
            "Required": 0.0,
            "Produced": produced,
            "Satisfied": produced >= 0.0,
            "Base Material": base,
            "End Material": end,
        })

    df = pd.DataFrame(rows, columns=[
        "Material", "Requested", "Required", "Produced", "Base Material", "End Material"
    ])
    return df
