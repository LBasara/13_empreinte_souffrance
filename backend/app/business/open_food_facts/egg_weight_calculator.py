import re
from enum import Enum
from typing import List, Optional, Tuple, Union

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


reasons = Enum(
    "reasons",
    [
        "not_egg_pack",
        "no_extracted_quantity",
        "no_extracted_unit",
        "dozen_unit",
        "piecewise_unit",
        "product_quantity_over_avg_weight",
        "other_case",
        "quantity_unit_g",
        "quantity_unit_mL",
        "from_category_tags",
    ],
)


def calculate_egg_weight_and_reason(product_data: ProductData) -> Tuple[float, reasons]:
    """
    Calculates the weight of eggs based on the product data.

    Returns:
        The egg weight if applicable.
    """

    quantity = product_data.product_quantity
    unit = product_data.product_quantity_unit
    categories_tags = product_data.categories_tags or []

    if quantity and unit:
        if unit == "g":
            return float(quantity), reasons.quantity_unit_g
        else:  # mL
            return 1.03 * float(quantity), reasons.quantity_unit_mL
        # Removed call to get_egg_weight_from_quantity
        # unit is either "g" or "mL", and egg density is >~1
        # kept the function in case we adapt/use it later
    else:
        return get_total_egg_weight_from_tags(categories_tags), reasons.from_category_tags


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


def compute_egg_number_and_reason(product_data: ProductData) -> Tuple[Optional[Union[int, float]], reasons]:
    """
    Extracts a whole number of eggs from the quantity field,
    along with the reason why this number is given.

    Args:
        product_data: ProductData: The product_data
        (expected to have "en:chicken-eggs" in product_data.categories_tags)

    Returns:
        An integer containing the extracted integer if successful, None otherwise
        reason (Enum Weight_reasons)

    """
    if is_egg_pack(product_data):
        extracted_quantity, extracted_unit = extract_quantity_and_unit(product_data.quantity)
        if extracted_quantity is None:
            return None, reasons.no_extracted_quantity
        elif extracted_unit is None:
            return extracted_quantity, reasons.no_extracted_unit
        elif extracted_unit in DOZEN_UNIT:
            return 12 * extracted_quantity, reasons.dozen_unit
        elif extracted_unit in PIECE_UNIT:
            return extracted_quantity, reasons.piecewise_unit
        elif (
            extracted_unit in WEIGHT_UNIT
            and product_data.product_quantity_unit == "g"
            and product_data.product_quantity is not None
        ):
            return int(product_data.product_quantity // AVERAGE_EGG_WEIGHT), reasons.product_quantity_over_avg_weight

    weight, reason = calculate_egg_weight_and_reason(product_data)
    return weight / AVERAGE_EGG_WEIGHT, reason


def calculate_egg_number(product_data: ProductData) -> Union[int, float]:
    """
    Calculates the number of eggs based on the product data.

    Returns:
        Number of eggs, if applicable.
    """
    egg_number, reason = compute_egg_number_and_reason(product_data)
    return egg_number if egg_number is not None else 0
