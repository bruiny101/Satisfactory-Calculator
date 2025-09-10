import json
import pandas as pd

# Theoretical maximum resource extraction rates (per minute) based on:
# https://satisfactory.fandom.com/wiki/Resource_node
RESOURCE_MAXIMUMS = {
    "Coal": 42300,
    "Crude Oil": 12600,
    "Nitrogen Gas": 12000,
    "Bauxite": 12300,
    "Copper Ore": 36900,
    "Caterium Ore": 15000,
    "Iron Ore": 92100,
    "Uranium": 2100,
    "Raw Quartz": 13500,
    "SAM": 10200,
    "Limestone": 69300,
    "Sulfur": 10800,
    "Water": 13125
}

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
            produced = 0

        rows.append({
            "Material": mat,
            "Requested": 0,
            "Required": 0,
            "Produced": produced,
            "Base Material": base,
            "End Material": end
        })

    df = pd.DataFrame(rows, columns=[
        "Material", "Requested", "Required", "Produced", "Base Material", "End Material"
    ])
    return df