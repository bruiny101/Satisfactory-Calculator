import json
import pandas as pd
from typing import Dict, List

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
    to_satisfy = [row["Material"] for _, row in materials_df.iterrows()]
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
    # Calculate total power consumption
    total_power = sum(get_recipe_power(recipes[i]) * solution[recipes[i]["Recipe"]] for i in range(len(recipes)))
    return solution, total_power