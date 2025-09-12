import json
import pandas as pd
from typing import Dict, List

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

# --- Optimization code ---

def run_recipe_optimization(materials_df: pd.DataFrame, recipe_json_file: str) -> Dict:
    """
    Solves the recipe selection problem to satisfy all non-base material requests while minimizing total power usage.
    Returns a dict: {recipe_name: count_used, ...}
    """
    import pulp
    # Load recipes
    with open(recipe_json_file, "r", encoding="utf-8") as f:
        recipes = json.load(f)
    # Build material index
    mat_idx = {row["Material"]: i for i, row in materials_df.iterrows()}
    # Identify non-base materials to satisfy
    to_satisfy = [row["Material"] for _, row in materials_df.iterrows() if not row["Base Material"]]
    requested = {row["Material"]: row["Requested"] + row["Required"] for _, row in materials_df.iterrows()}
    # Decision variables: one per recipe
    recipe_vars = []
    prob = pulp.LpProblem("SatisfactoryRecipeOptimization", pulp.LpMinimize)
    for i, recipe in enumerate(recipes):
        var = pulp.LpVariable(f"Recipe_{i}", lowBound=0, cat="Integer")
        recipe_vars.append(var)
    # Objective: minimize total power usage
    def get_recipe_power(recipe):
        prod_in = recipe.get("Produced in", [])
        if prod_in and isinstance(prod_in, list) and "Pwr Cons" in prod_in[0]:
            return float(prod_in[0]["Pwr Cons"])
        raise ValueError(f"Power consumption not found for recipe: {recipe.get('Recipe', 'Unknown')}")
    prob += pulp.lpSum([get_recipe_power(recipes[i]) * recipe_vars[i] for i in range(len(recipes))])
    # Constraints: for each non-base material, total produced >= requested+required
    for mat in to_satisfy:
        # Sum up all production of mat from all recipes
        prod_sum = []
        ingred_sum = []
        for i, recipe in enumerate(recipes):
            for prod in recipe.get("Products", []):
                if prod["Material"] == mat:
                    prod_sum.append(prod["Quantity"] * recipe_vars[i])
            for ing in recipe.get("Ingredients", []):
                if ing["Material"] == mat:
                    ingred_sum.append(ing["Quantity"] * recipe_vars[i])
                    
        if prod_sum:
            prob += pulp.lpSum(prod_sum) >= pulp.lpSum(ingred_sum) + requested[mat]
        else:
            raise ValueError(f"Material '{mat}' cannot be produced by any recipe.")

    # Solve
    result = prob.solve()
    # Gather solution
    solution = {recipes[i]["Recipe"]: int(recipe_vars[i].varValue) if recipe_vars[i].varValue is not None else 0 for i in range(len(recipes))}
    return solution