from typing import List, Dict

from pydantic import BaseModel, HttpUrl


class ProductData(BaseModel):
    """
    Product data model for search-a-licious request.
    """
    categories_tags: List[str] | None = None
    labels_tags: List[str] | None = None
    ingredients_tags: List[str] | None = None
    ingredients: List[Dict] | None = None
    allergens_tags: List[str] | None = None
    image_url: HttpUrl | None = None
    product_name: str
    quantity: str | None = None
    product_quantity: str | None = None
    product_quantity_unit: str | None = None


class ProductResponse(BaseModel):
    """
    Response model for search-a-licious request.
    """

    hits: List[ProductData]
