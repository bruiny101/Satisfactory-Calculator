# Software Requirements Document: Satisfactory Calculator Recipe Updater

## 1. Overview

This application provides a graphical user interface (GUI) for updating and managing Satisfactory game recipes. It fetches the latest recipe data from the Satisfactory wiki, compares it with the local data, and allows the user to accept or reject updates. The GUI also allows users to select materials and specify requested quantities for recipe optimization.

## 2. Functional Requirements

### 2.1 Satisfactory Data Scraping

#### 2.1.1 Update Recipes Button

When a user clicks the 'Update Recipes' button, the system must:

1. Fetch recipe data from a specified URL (default: Satisfactory wiki).
2. Fetch machine power data from a specified URL (default: Satisfactory wiki).
3. Parse and store the data in a temporary JSON file following the format specified in Appendix A.
4. Compare newly fetched recipe data with existing local recipe data.
5. Present differences (added, removed, or changed recipes) to the user in a readable, scrollable format.
6. Prompt the user to accept or reject the updates after showing the differences.
7. If accepted, replace the old data with the new data and update the materials list in the GUI.
8. If rejected, preserve the old data.

### 2.2 Material Selection and Requested Quantity

- The GUI provides a search bar and drop-down menu (centered near the top) populated with all materials found in the 'Material' column of the recipe data.
- Typing in the search bar filters the drop-down list in real time to show only materials containing the typed string.
- Selecting a material adds a row below the search bar with the material name, a float entry field (only >0 allowed), and a remove button.
- Multiple lines of the same material are allowed; each can have its own requested value.
- The list of selected materials is scrollable if it grows too long.

### 2.3 Calculate Button

- Below the selected materials list, a 'Calculate' button is provided.
- When clicked, all values in the 'Requested' column of the materials DataFrame are reset to 0.0.
- The values entered in the float entry fields for each selected material are summed and added to the 'Requested' column for the corresponding material.
- A confirmation message is displayed when calculation is complete.

### 2.4 Error Handling
- Handle network errors, file errors, and data parsing errors gracefully.
- Display user-friendly error messages in case of failure.

### 2.5 GUI Requirements
- Provide a simple GUI with:
  - A search bar and drop-down menu for material selection (top center).
  - A scrollable list of selected materials, each with a float entry and remove button.
  - A 'Calculate' button below the selected materials list.
  - An 'Update Recipes' button at the bottom right.
  - Scrollable dialogs for recipe differences and confirmation.
  - Confirmation dialogs and error messages as needed.

## 3. Non-Functional Requirements

### 3.1 Usability
- The GUI must be intuitive and require minimal user interaction.

### 3.2 Compatibility
- The application must run on Windows OS.
- Python 3.x is required.

### 3.3 Performance
- Data fetching and comparison should complete within a few seconds under normal network conditions.

## 4. External Dependencies

- Python libraries: `tkinter`, `pandas`, `requests`, `json`, `os`, `shutil`, `re`
- Internet access to fetch recipe data from the wiki.

## 5. Data Storage

- Recipe data is stored in JSON files in the `json_data` directory.

## 6. Security

- No sensitive data is handled.
- Only local file operations are performed.

## Appendix A: JSON Recipe Data Format

The recipe data must be stored in a JSON file with the following structure:

```json
[
	{
		"Recipe": "<string>",
		"Ingredients": [
			{ "Material": "<string>", "Quantity": "<float>" },
			...
		],
		"Produced in": [
            { "Machine": "<string>", "Pwr Cons": "<float>"}
        ],
		"Products": [
			{ "Material": "<string>", "Quantity": "<float>" },
			...
		],
		"Unlocked by": "<string>"
	},
	...
]
```

### Field Descriptions

- **Recipe**: Name of the recipe (string).
- **Ingredients**: List of ingredient objects, each with:
	- **Material**: Name of the ingredient (string).
	- **Quantity**: Amount required (float).
- **Produced in**: List of Machine objects, each with:
    - **Machine**: Name of the recipe's machine (string)
    - **Pwr Cons**: How much power the recipe uses in MW (float)
- **Products**: List of product objects, each with:
	- **Material**: Name of the product (string).
	- **Quantity**: Amount produced (float).
- **Unlocked by**: Description of how the recipe is unlocked (string).

## Appendix B: Materials DataFrame

### Materials DataFrame (recipe_optimization.py)

The materials DataFrame is generated with the following columns and logic:

- **Material** (string): All unique materials found in Ingredients or Products.
- **Requested** (float): User-requested quantity, default 0.0, updated via the GUI.
- **Required** (float): Reserved for future use, default 0.0.
- **Produced** (float): Theoretical maximum extraction rate (if applicable), else 0.0.
- **Base Material** (bool): True if only found in Ingredients or is a resource node material.
- **End Material** (bool): True if only found in Products.

The DataFrame is updated when recipes are updated or when the user clicks 'Calculate'.
