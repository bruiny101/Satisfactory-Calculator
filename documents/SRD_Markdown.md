# Software Requirements Document: Satisfactory Calculator Recipe Updater

## 1. Overview

This application provides a graphical user interface (GUI) for updating and managing Satisfactory game recipes. It fetches the latest recipe data from the Satisfactory wiki, compares it with the local data, and allows the user to accept or reject updates. The GUI also allows users to select materials and specify requested quantities for recipe optimization.

## 2. Functional Requirements

### 2.1 Update Recipes Button

2.1.1 Fetch recipe data from a specified URL (default: Satisfactory wiki).  
2.1.2 Fetch machine power data from a specified URL (default: Satisfactory wiki).  
2.1.3 Parse and store the data in a temporary JSON file following the format specified in Appendix A.  
2.1.4 Compare newly fetched recipe data with existing local recipe data.  
2.1.5 Present differences (added, removed, or changed recipes) to the user in a readable, scrollable format.  
2.1.6 Prompt the user to accept or reject the updates after showing the differences.  
2.1.7 If accepted, replace the old data with the new data and update the materials list in the GUI.  
2.1.8 If rejected, preserve the old data. 

### 2.2 Material Selection and Requested Quantity

2.2.1 The GUI provides a search bar and drop-down menu (centered near the top) populated with all materials found in the 'Material' column of the recipe data.  
2.2.2 Typing in the search bar filters the drop-down list in real time to show only materials containing the typed string.  
2.2.3 Selecting a material adds a row below the search bar with the material name, a float entry field (only >0 allowed), and a remove button.  
2.2.4 Multiple lines of the same material are allowed; each can have its own requested value.  
2.2.5 The list of selected materials is scrollable if it grows too long.  

### 2.3 Calculate Button

2.3.1 Below the selected materials list, a 'Calculate' button is provided.  
2.3.2 When clicked, all values in the 'Requested' column of the materials DataFrame are reset to 0.0.  
2.3.3 The values entered in the float entry fields for each selected material are summed and added to the 'Requested' column for the corresponding material.  
2.3.4 A confirmation message is displayed when calculation is complete.  

### 2.4 Error Handling

2.4.1 Handle network errors, file errors, and data parsing errors gracefully.  
2.4.2 Display user-friendly error messages in case of failure.  

### 2.5 GUI Requirements

2.5.1 Provide a simple GUI with:  
  - 2.5.1.1 A search bar and drop-down menu for material selection (top center).  
  - 2.5.1.2 A scrollable list of selected materials, each with a float entry and remove button.  
  - 2.5.1.3 A 'Calculate' button below the selected materials list.  
  - 2.5.1.4 An 'Update Recipes' button at the bottom right.  
  - 2.5.1.5 Scrollable dialogs for recipe differences and confirmation.  
  - 2.5.1.6 Confirmation dialogs and error messages as needed.  

## 3. Non-Functional Requirements

### 3.1 Usability

3.1.1 The GUI must be intuitive and require minimal user interaction.  

### 3.2 Compatibility

3.2.1 The application must run on Windows OS.  
3.2.2 Python 3.x is required.  

### 3.3 Performance

3.3.1 Data fetching and comparison should complete within a few seconds under normal network conditions.  

## 4. External Dependencies

4.1 Python libraries: `tkinter`, `pandas`, `requests`, `json`, `os`, `shutil`, `re`  
4.2 Internet access to fetch recipe data from the wiki.  

## 5. Data Storage

5.1 Recipe data is stored in JSON files in the `json_data` directory.  

## 6. Security

6.1 No sensitive data is handled.  
6.2 Only local file operations are performed.  

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
- **Satisfied** (bool): True if Produced >= Required + Requested
- **Base Material** (bool): True if only found in Ingredients or is a resource node material.
- **End Material** (bool): True if only found in Products.

The DataFrame is updated when recipes are updated or when the user clicks 'Calculate'.
