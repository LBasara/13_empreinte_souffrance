from typing import Callable
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.business.open_food_facts.knowledge_panel import (
    KnowledgePanelGenerator,
    get_data_from_off_search_a_licious,
    get_data_from_off_v3,
    get_knowledge_panel_response,
)
from app.business.open_food_facts.pain_report_calculator import PainReportCalculator
from app.config.exceptions import ResourceNotFoundException
from app.config.i18n import I18N
from app.enums.open_food_facts.enums import AnimalType, LayingHenBreedingType, PainIntensity, PainType
from app.schemas.open_food_facts.external import ProductData
from app.schemas.open_food_facts.internal import (
    BreedingTypeAndWeight,
    KnowledgePanelResponse,
)


@pytest.mark.asyncio
async def test_get_data_from_off_search_a_licious_success():
    """Test when the OFF API returns valid data"""
    barcode = "123456789"
    mock_response_data = {
        "hits": [
            {
                "categories_tags": ["en:cage-chicken-eggs", "other"],
                "labels_tags": ["organic"],
                "product_name": "Fake product name",
                "image_url": "https://example.com/image.jpg",
            }
        ]
    }

    mock_response = AsyncMock()
    mock_response.json = MagicMock(return_value=mock_response_data)
    mock_response.raise_for_status = AsyncMock(return_value=None)

    with patch("httpx.AsyncClient.get", return_value=mock_response):
        result = await get_data_from_off_search_a_licious(barcode, locale="en")

    assert result == ProductData.model_validate(mock_response_data["hits"][0])


@pytest.mark.asyncio
async def test_get_data_from_off_v3_success(sample_product_data: ProductData):
    """Test when the OFF API returns valid data"""
    barcode = "123456789"
    mock_response_data = {"product": sample_product_data}

    mock_response = AsyncMock()
    mock_response.json = MagicMock(return_value=mock_response_data)
    mock_response.raise_for_status = AsyncMock(return_value=None)

    with patch("httpx.AsyncClient.get", return_value=mock_response):
        result = await get_data_from_off_v3(barcode, locale="en")

    assert result == sample_product_data


@pytest.mark.asyncio
async def test_get_data_from_off_search_a_licious_no_hits():
    """Test when the OFF API returns no hits"""
    barcode = "000000000"
    mock_response_data = {"hits": []}

    mock_response = AsyncMock()
    mock_response.json = MagicMock(return_value=mock_response_data)
    mock_response.raise_for_status = AsyncMock(return_value=None)

    with patch("httpx.AsyncClient.get", return_value=mock_response):
        with pytest.raises(ResourceNotFoundException, match=f"No hits returned by OFF API: {barcode}"):
            await get_data_from_off_search_a_licious(barcode, locale="en")


@pytest.mark.asyncio
@pytest.mark.parametrize("get_data_from_off_function", [get_data_from_off_search_a_licious, get_data_from_off_v3])
async def test_get_data_from_off_validation_error(get_data_from_off_function: Callable):
    """Test when the OFF API returns invalid data"""
    barcode = "999999999"
    mock_response_data = {"product": "invalid_value"}

    mock_response = AsyncMock()
    mock_response.json = MagicMock(return_value=mock_response_data)
    mock_response.raise_for_status = AsyncMock(return_value=None)

    with patch("httpx.AsyncClient.get", return_value=mock_response):
        with pytest.raises(
            ResourceNotFoundException, match=f"Failed to validate product data retrieved from OFF: {barcode}"
        ):
            await get_data_from_off_function(barcode, locale="en")


@pytest.mark.asyncio
@pytest.mark.parametrize("get_data_from_off_function", [get_data_from_off_search_a_licious, get_data_from_off_v3])
async def test_get_data_from_off_http_call_exception(get_data_from_off_function: Callable):
    """Test when the OFF API returns an HTTP error"""
    barcode = "111111111"

    with patch("httpx.AsyncClient.__aenter__", side_effect=httpx.ReadTimeout("Network error")):
        with pytest.raises(ResourceNotFoundException, match=f"Can't get product data from OFF API: {barcode}"):
            await get_data_from_off_function(barcode, locale="en")


def test_compute_breeding_types_with_weights(sample_product_data: ProductData):
    """Test computing breeding types with weights"""
    calculator = PainReportCalculator(sample_product_data)

    breeding_types = calculator._get_breeding_types()
    result = calculator._get_breeding_types_with_weights(breeding_types)

    # product_data fixture contains the `en:cage-chicken-eggs` tag
    assert AnimalType.LAYING_HEN in result
    assert result[AnimalType.LAYING_HEN].breeding_type == LayingHenBreedingType.FURNISHED_CAGE
    assert result[AnimalType.LAYING_HEN].animal_product_weight == 200


def test_get_breeding_types(sample_product_data: ProductData):
    """Test getting breeding types from product data"""
    calculator = PainReportCalculator(sample_product_data)

    result = calculator._get_breeding_types()
    assert AnimalType.LAYING_HEN in result
    assert result[AnimalType.LAYING_HEN].breeding_type == LayingHenBreedingType.FURNISHED_CAGE


def test_generate_pain_levels_for_type(sample_product_data: ProductData):
    """Test generating pain levels for a specific animal, breeding type, and pain type"""

    calculator = PainReportCalculator(sample_product_data)

    breeding_type = BreedingTypeAndWeight(breeding_type=LayingHenBreedingType.FURNISHED_CAGE, animal_product_weight=200)

    # Test generating physical pain levels
    physical_pain_levels = calculator._generate_pain_levels_for_type(
        AnimalType.LAYING_HEN, breeding_type, PainType.PHYSICAL
    )

    assert len(physical_pain_levels) == 4  # One for each intensity
    for level in physical_pain_levels:
        assert level.pain_type == PainType.PHYSICAL
        assert isinstance(level.pain_intensity, PainIntensity)
        assert isinstance(level.seconds_in_pain, int)

    # Test generating psychological pain levels
    psychological_pain_levels = calculator._generate_pain_levels_for_type(
        AnimalType.LAYING_HEN, breeding_type, PainType.PSYCHOLOGICAL
    )

    assert len(psychological_pain_levels) == 4  # One for each intensity
    for level in psychological_pain_levels:
        assert level.pain_type == PainType.PSYCHOLOGICAL
        assert isinstance(level.pain_intensity, PainIntensity)
        assert isinstance(level.seconds_in_pain, int)


def test_knowledge_panel_generator(pain_report):
    """Test the KnowledgePanelGenerator class"""
    translator = I18N().get_translator(locale="en")

    # Create generator and test individual methods
    generator = KnowledgePanelGenerator(pain_report, translator)

    # Test main panel
    main_panel = generator.create_main_panel()
    assert main_panel.level == "info"
    assert main_panel.title_element.title == "Suffering footprint"
    assert len(main_panel.elements) > 3

    # Test intensities definitions panel
    intensities_panel = generator.create_intensities_definitions_panel()
    assert intensities_panel.title_element.title == "Intensity level definitions"
    assert len(intensities_panel.elements) == 4  # One for each intensity

    # Test physical pain panel
    physical_panel = generator.create_physical_pain_panel()
    assert physical_panel.title_element.title == "Physical pain"
    assert len(physical_panel.elements) > 3  # Intro, description, animal pain data, and footer

    # Test psychological pain panel
    psychological_panel = generator.create_psychological_pain_panel()
    assert psychological_panel.title_element.title == "Psychological pain"
    assert len(psychological_panel.elements) > 3  # Intro, description, animal pain data, and footer

    # Test animal pain element generation
    animal_element = generator.get_animal_pain_for_panel(AnimalType.LAYING_HEN, PainType.PHYSICAL)
    assert animal_element is not None
    assert animal_element.element_type == "text"
    assert "Laying hen" in animal_element.text_element.html

    # Test complete response
    response = generator.get_response()
    assert isinstance(response, KnowledgePanelResponse)
    assert len(response.panels) == 4


def test_get_knowledge_panel_response(pain_report):
    """Test the get_knowledge_panel_response function"""
    translator = I18N().get_translator(locale="en")

    # Generate knowledge panel response using the function
    response = get_knowledge_panel_response(pain_report, translator)

    # Verify response structure
    assert "main" in response.panels
    assert "physical_pain" in response.panels
    assert "psychological_pain" in response.panels
    assert "intensities_definitions" in response.panels

    # Verify each panel has the required fields
    for panel in response.panels.values():
        assert hasattr(panel, "elements")
        assert hasattr(panel, "title_element")
