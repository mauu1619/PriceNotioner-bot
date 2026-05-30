from decimal import Decimal

import pytest
from pytest_httpx import HTTPXMock

from src.parsers.wildberries import get_wb_product


@pytest.mark.asyncio
async def test_get_wb_product_success(httpx_mock: HTTPXMock):
    # Mock WB API response
    mock_data = {
        "products": [
            {
                "name": "Тестовый товар",
                "sizes": [
                    {
                        "price": {
                            "product": 150000  # 1500.00 RUB
                        }
                    }
                ],
            }
        ]
    }

    article = "123456"
    httpx_mock.add_response(
        url=f"https://card.wb.ru/cards/v4/detail?appType=1&curr=rub&dest=-1257786&nm={article}",
        json=mock_data,
    )

    result = await get_wb_product(article)

    assert result is not None
    title, price, url = result
    assert title == "Тестовый товар"
    assert price == Decimal("1500.00")
    assert "123456" in url


@pytest.mark.asyncio
async def test_get_wb_product_not_found(httpx_mock: HTTPXMock):
    httpx_mock.add_response(
        url="https://card.wb.ru/cards/v4/detail?appType=1&curr=rub&dest=-1257786&nm=999",
        json={"products": []},
    )

    result = await get_wb_product("999")
    assert result is None


@pytest.mark.asyncio
async def test_get_wb_product_invalid_url():
    result = await get_wb_product("not-a-url")
    assert result is None
