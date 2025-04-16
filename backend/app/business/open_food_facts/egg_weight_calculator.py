import re
from typing import List, Optional, Union

from app.schemas.open_food_facts.external import ProductData

AVERAGE_EGG_WEIGHT = 50


UNIT_CONVERSIONS = {
    "pcs": lambda q: float(q) * AVERAGE_EGG_WEIGHT,
    "sans": lambda q: float(q) * AVERAGE_EGG_WEIGHT,
    "unite": lambda q: float(q) * AVERAGE_EGG_WEIGHT,
    "g": lambda q: float(q),
    "gr": lambda q: float(q),
    "gramm": lambda q: float(q),
    "oz": lambda q: float(q) * 28.35,
    "lbs": lambda q: float(q) * 453.59,
    "ml": lambda q: float(q) * 1.03,
    "l": lambda q: float(q) * 1030,
    "litres": lambda q: float(q) * 1030,
}

EGG_WEIGHTS_BY_TAG = {
    60: {"large-eggs", "gros-oeufs"},
    55: {"grade-a-eggs", "grade-aa-eggs"},
    50: {"medium-eggs"},
}


DOZEN_UNIT = ["dzn", "dozen", "doz"]
WEIGHT_UNIT = ["lb", "kg", "oz", "à", "gram", "g", "gr"]
PIECE_UNIT = [
    "frische",
    "unknown",
    "pieze",
    "entre",
    "entre",
    "mixed",
    "pack",
    "portion",
    "p",
    "pk",
    "gro",
    "ud",
    "uova",
    "pz",
    "x",
    "moyen",
    "stuk",
    "st",
    "stück",
    "pc",
    "eier",
    "kpl",
    "n",
    "komada",
    "gal",
    "label",
    "szt",
    "stck",
    "egg",
    "unidade",
    "eieren",
    "unité",
    "stk",
    "oeuf",
    "u",
    "xl",
    "l",
    "m",
    "huevo",
    "lg",
    "large",
    "ovo",
    "kla",
    "unit",
    "pièce",
]


def get_egg_weight_by_tag(categories_tags: List[str]) -> int:
    """
    Returns the standard weight of one egg based on category tags.
    """
    for weight, tags in EGG_WEIGHTS_BY_TAG.items():
        if any(tag in categories_tags for tag in tags):
            return weight
    return 0


def get_number_of_eggs_from_tags(categories_tags: List[str]) -> int:
    """
    Extracts the number of eggs from tags.
    TODO: Add support for other tags
    """
    for tag in categories_tags:
        match = re.search(r"pack-of-(\d+)", tag)
        if match:
            return int(match.group(1))
    return 0


def get_total_egg_weight_from_tags(categories_tags: List[str]) -> float:
    """
    Calculates total egg weight based on standard weights and pack size.
    """
    num_eggs = get_number_of_eggs_from_tags(categories_tags)
    weight_per_egg = get_egg_weight_by_tag(categories_tags)
    return weight_per_egg * num_eggs


def get_egg_weight_from_quantity(quantity: float, unit: str) -> float:
    """
    Converts product quantity and unit into weight in grams.
    """
    unit_key = unit.lower()
    converter = UNIT_CONVERSIONS.get(unit_key)
    if converter:
        try:
            return converter(quantity)
        except (ValueError, TypeError):
            pass
    return 0


def is_egg_pack(product_data: ProductData) -> bool:
    """
    Quick function to check whether we're dealing with egg pack

    Returns:
        True if egg, False if ovoproduct or otherwise
    """
    return product_data.categories_tags is not None and "en:chicken-eggs" in product_data.categories_tags


def calculate_egg_weight(product_data: ProductData) -> float:
    """
    Calculates the weight of eggs based on the product data.

    Returns:
        The egg weight if applicable.
    """

    quantity = product_data.product_quantity
    unit = product_data.product_quantity_unit
    categories_tags = product_data.categories_tags or []

    if quantity and unit:
        egg_weight = float(quantity) if unit == "g" else 1.03 * float(quantity)
        # Removed call to get_egg_weight_from_quantity
        # unit is either "g" or "mL", and egg density is >~1
        # kept the function in case we adapt/use it later
    else:
        egg_weight = get_total_egg_weight_from_tags(categories_tags)

    return egg_weight


def calculate_egg_number(product_data: ProductData) -> Union[int, float]:
    """
    Calculates the number of eggs based on the product data.

    Returns:
        Number of eggs, if applicable.
    """
    if is_egg_pack(product_data):
        n_eggs = get_egg_number(product_data)
        if n_eggs is not None:
            return n_eggs

    return calculate_egg_weight(product_data) / AVERAGE_EGG_WEIGHT


def extract_quantity_and_unit(text):
    """
    Extracts the first integer and optionally the first word
    (of several letters) from a string.

    Args:
        text: The input string.

    Returns:
        A tuple containing the extracted integer (as an integer) and
        the extracted word (as a string, or None if no word is found),
        or (None, None) if no integer is found.
    """
    if text is None:
        return None, None

    match_with_text = re.search(r"(\d+,?\.?\d?)\s*([a-zçàéèêëîïôöûüÿ]+)s?\b", text.lower().replace("œ", "oe"))
    if match_with_text:
        quantity = float(match_with_text.group(1).replace(",", "."))
        unit = match_with_text.group(2).rstrip("s")
        return quantity, unit
    else:
        match_only_quantity = re.search(r"(\d+)", text)
        if match_only_quantity:
            quantity = int(match_only_quantity.group(1))
            return quantity, None
        else:
            return None, None


def get_egg_number(product_data: ProductData) -> Optional[int]:
    """
    Extracts a whole number of eggs from the quantity field

    Args:
        product_data: ProductData: The product_data
        (expected to have "en:chicken-eggs" in product_data.categories_tags)

    Returns:
        An integer containing the extracted integer if successful, None otherwise
    """
    if not is_egg_pack(product_data):  # ovoproduct or otherwise
        return None
    extracted_quantity, extracted_unit = extract_quantity_and_unit(product_data.quantity)
    extracted_quantity = int(extracted_quantity)
    if extracted_quantity is None:
        return None
    elif extracted_unit is None:
        return extracted_quantity
    elif extracted_unit in DOZEN_UNIT:
        return 12 * extracted_quantity
    elif extracted_unit in PIECE_UNIT:
        return extracted_quantity
    elif (
        extracted_unit in WEIGHT_UNIT
        and product_data.product_quantity_unit == "g"
        and product_data.product_quantity is not None
    ):
        return int(product_data.product_quantity // AVERAGE_EGG_WEIGHT)
    else:
        return None
