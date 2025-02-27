from dataclasses import dataclass
from typing import List, Dict, Union
from flask import Flask, request, jsonify, Response
import re

# ==== Type Definitions, feel free to add or modify ===========================
@dataclass
class CookbookEntry:
	name: str

@dataclass
class RequiredItem():
	name: str
	quantity: int

@dataclass
class Recipe(CookbookEntry):
	required_items: List[RequiredItem]

@dataclass
class Ingredient(CookbookEntry):
	cook_time: int

@dataclass 
class Cookbook:
	def __init__(self):
		self.entries: Dict[str, CookbookEntry] = {} # Stores the name and the cookbook entry of ingredient/recipe

	def add_entry(self, entry):
		if entry.name in self.entries:
			raise ValueError(f"Entry '{entry.name}' already exists in the cookbook.")
		self.entries[entry.name] = entry

	def get_entry(self, name):
		return self.entries[name]


# =============================================================================
# ==== HTTP Endpoint Stubs ====================================================
# =============================================================================
app = Flask(__name__)

# Store your recipes here!
cookbook = Cookbook()

# Task 1 helper (don't touch)
@app.route("/parse", methods=['POST'])
def parse():
	data = request.get_json()
	recipe_name = data.get('input', '')
	parsed_name = parse_handwriting(recipe_name)
	if parsed_name is None:
		return 'Invalid recipe name', 400
	return jsonify({'msg': parsed_name}), 200

# [TASK 1] ====================================================================
# Takes in a recipeName and returns it in a form that 
def parse_handwriting(recipeName: str) -> Union[str | None]:
    recipeName = recipeName.lower()

    output_string = ""
    # Iterate over each character in the recipeName
    for char in recipeName:
        if char.isalpha() or char == " ":
            # Keep letters and spaces.
            output_string += char
        elif char == "_" or char == "-":
            # Replace hyphens and underscores with a space
            output_string += " "

    # Capitalize the first letter of each word
    output_string = output_string.title()

    # Remove any extra leading/trailing whitespaces
    output_string = " ".join(output_string.split())

    if len(output_string) < 1:
        return None

    return output_string


# [TASK 2] ====================================================================
# Endpoint that adds a CookbookEntry to your magical cookbook
@app.route('/entry', methods=['POST'])
def create_entry():
	data = request.get_json()
	if data is None:
		return Response(status=400)
	
	entry_type = data.get("type")
	if entry_type not in ("recipe", "ingredient"):
		return Response(status=400)
	
	entry_name = data.get("name")
	if not entry_name:
		return Response(status=400)
	
	if entry_type == "ingredient":
		cook_time = data.get("cookTime")
		# Validate cookTime is provided and is a non-negative integer
		if cook_time is None or not isinstance(cook_time, int) or cook_time < 0:
			return Response(status=400)
		# Store the ingredient entry
		ingredient = Ingredient(name=entry_type, cook_time=cook_time)
		try:
			cookbook.add_entry(ingredient)
		except ValueError:
			return Response(status=400)

	elif entry_type == "recipe":
		required_items = data.get("requiredItems")
		# Validate requiredItems is a list
		if not isinstance(required_items, list):
			return Response(status=400)
		
		required_items_objs = []
		seen_names = set() # for duplicate checking
		for item in required_items:
			item_name = item.get("name")
			quantity = item.get("quantity")
			# Validate each required item has a name (string) and quantity (integer)
			if not item_name or not isinstance(item_name, str) or not isinstance(quantity, int):
				return Response(status=400)
			# Check for duplicate required item names
			if item_name in seen_names:
				return Response(status=400)
			seen_names.add(item_name)
			required_items_objs.append(RequiredItem(name=item_name, quantity=quantity))
		
		# Create and store the recipe entry
		recipe = Recipe(name=entry_name, required_items=required_items_objs)
		try:
			cookbook.add_entry(recipe)
		except ValueError:
			return Response(status=400)
		
	return Response(status=200)


# [TASK 3] ====================================================================
# Endpoint that returns a summary of a recipe that corresponds to a query name
@app.route('/summary', methods=['GET'])
def get_summary():
    # Retrieve the recipe name from the query parameter
    recipe_name = request.args.get("name")
    if not recipe_name:
        return Response(status=400)
    
    if recipe_name not in cookbook.entries:
        return Response(status=400)
    
    entry = cookbook.entries[recipe_name]

    if not isinstance(entry, Recipe):
        return Response(status=400)
    
    def flatten_recipe(recipe: Recipe, multiplier: int = 1) -> Dict[str, int]:
        flat = {}
        for req in recipe.required_items:
            # Ensure the required item exists
            if req.name not in cookbook.entries:
                raise ValueError(f"Required item {req.name} not found in the cookbook.")
            item = cookbook.entries[req.name]
            qty = req.quantity * multiplier
            if isinstance(item, Ingredient):
                # Base ingredient: add its quantity
                flat[item.name] = flat.get(item.name, 0) + qty
            elif isinstance(item, Recipe):
                # If the item is a recipe, recursively flatten it
                sub_flat = flatten_recipe(item, multiplier=qty)
                # Merge the sub_flat quantities into flat
                for ing, sub_qty in sub_flat.items():
                    flat[ing] = flat.get(ing, 0) + sub_qty
            else:
                raise ValueError("Invalid cookbook entry type encountered.")
        return flat

    try:
        # Flatten the recipe to get a mapping of base ingredient names to their total quantities
        base_ingredients = flatten_recipe(entry)
    except ValueError:
        return Response(status=400)
    
    total_cook_time = 0
    ingredients_list = []
    for ing_name, quantity in base_ingredients.items():
        # Each base ingredient must exist and be an Ingredient
        if ing_name not in cookbook.entries:
            return Response(status=400)
        ing_entry = cookbook.entries[ing_name]
        if not isinstance(ing_entry, Ingredient):
            return Response(status=400)
        total_cook_time += ing_entry.cook_time * quantity
        ingredients_list.append({"name": ing_name, "quantity": quantity})
    
    summary = {
        "name": recipe_name,
        "cookTime": total_cook_time,
        "ingredients": ingredients_list
    }
    
    return jsonify(summary), 200



# =============================================================================
# ==== DO NOT TOUCH ===========================================================
# =============================================================================

if __name__ == '__main__':
	app.run(debug=True, port=8080)
