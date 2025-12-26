from django.utils.translation import gettext_lazy as _

ITEM_CATEGORY_GROUPS = {
    _("Tinned Tomatoes"): _("Meal Food"),
    _("Tinned Meat"): _("Meal Food"),
    _("Tinned Vegetarian"): _("Meal Food"),
    _("Tinned Pasta"): _("Meal Food"),
    _("Confectionery"): _("Snack Food"),
    _("Cereal"): _("Meal Food"),
    _("Tinned Fruit"): _("Meal Food"),
    _("Milk"): _("Drink"),
    _("Fruit Juice"): _("Drink"),
    _("Squash"): _("Drink"),
    _("Condiment"): _("Cooking"),
    _("Noodles"): _("Meal Food"),
    _("Cooking Oil"): _("Cooking"),
    _("Tinned Fish"): _("Meal Food"),
    _("Soup"): _("Meal Food"),
    _("Crisps"): _("Snack Food"),
    _("Biscuits"): _("Snack Food"),
    _("Baked Beans"): _("Meal Food"),
    _("Tinned Vegetables"): _("Meal Food"),
    _("Pasta Sauce"): _("Cooking"),
    _("Pasta"): _("Meal Food"),
    _("Rice"): _("Meal Food"),
    _("Tea"): _("Drink"),
    _("Coffee"): _("Drink"),
    _("Sugar"): _("Cooking"),
    _("Spread"): _("Meal Food"),
    _("Vegetable"): _("Meal Food"),
    _("Instant Mash"): _("Meal Food"),
    _("Dessert"): _("Meal Food"),
    _("Washing Up Liquid"): _("Cleaning"),
    _("Toilet Roll"): _("Toiletries"),
    _("Shower Gel"): _("Toiletries"),
    _("Shampoo"): _("Toiletries"),
    _("Soap"): _("Toiletries"),
    _("Dental"): _("Toiletries"),
    _("Deodorant"): _("Toiletries"),
    _("Laundry"): _("Cleaning"),
    _("Sanitary Products"): _("Toiletries"),
    _("Baby Food"): _("Baby Supplies"),
    _("Baby Milk"): _("Baby Supplies"),
    _("Nappies"): _("Baby Supplies"),
    _("Wipes"): _("Baby Supplies"),
    _("Kitchen Roll"): _("Cleaning"),
    _("Household Supplies"): _("Cleaning"),
    _("Pet Food"): _("Other"),
    _("Carrier Bags"): _("Other"),
    _("Sauce"): _("Cooking"),
    _("Other"): _("Other"),
    _("Toiletries"): _("Toiletries"),
    _("Hot Chocolate"): _("Drink"),
}

ITEM_GROUPS = list(ITEM_CATEGORY_GROUPS.values())
ITEM_GROUPS.sort()
ITEM_GROUPS_CHOICES = tuple((group, group) for group in ITEM_GROUPS)

ITEM_CATEGORIES = list(ITEM_CATEGORY_GROUPS.keys())
ITEM_CATEGORIES.sort()
ITEM_CATEGORIES_CHOICES = tuple((category, category) for category in ITEM_CATEGORIES)
