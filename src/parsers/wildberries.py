import re
from decimal import Decimal
from typing import Optional, Tuple

import httpx
from fake_useragent import UserAgent
from loguru import logger

from src.core.config import settings

ua = UserAgent()


async def get_wb_product(url: str) -> Optional[Tuple[str, Decimal, str]]:
    """
    Parses a Wildberries URL or article number and returns the product title, current price, and clean URL.
    Returns (title, price, url) if successful, None otherwise.
    """
    # Extract article number from URL
    match = re.search(r"(?:catalog/|/catalog/|wb\.ru/catalog/)(\d+)", url)
    if match:
        article = match.group(1)
    else:
        # Check if the input is just an article number
        if url.isdigit():
            article = url
        else:
            logger.debug(f"Invalid WB url/article format: {url}")
            return None

    clean_url = f"https://www.wildberries.ru/catalog/{article}/detail.aspx"
    # Using v4 API endpoint which currently works and returns price inside sizes[0].price.product
    api_url = f"https://card.wb.ru/cards/v4/detail?appType=1&curr=rub&dest=-1257786&nm={article}"

    headers = {
        "User-Agent": ua.random,
        "Accept": "*/*",
        "Origin": "https://www.wildberries.ru",
        "Referer": clean_url,
    }

    try:
        proxy = settings.PROXY_URL if settings.PROXY_URL else None
        logger.debug(f"Fetching WB API for article {article}...")

        async with httpx.AsyncClient(proxy=proxy) as client:
            response = await client.get(api_url, headers=headers, timeout=10.0)
            response.raise_for_status()
            data = response.json()

            products = data.get("products", [])
            if not products:
                logger.debug(f"WB API returned no products for {article}")
                return None

            product_data = products[0]
            title = product_data.get("name")

            sizes = product_data.get("sizes", [])
            if not sizes:
                logger.debug(f"WB API returned no sizes for {article}")
                return None

            price_data = sizes[0].get("price")
            if not price_data:
                logger.debug(f"WB API returned no price (out of stock?) for {article}")
                # If price is missing, item might be out of stock
                return None

            # 'product' contains the actual selling price in kopecks
            sale_price_u = price_data.get("product")
            if not sale_price_u:
                logger.debug(f"WB API returned no 'product' price field for {article}")
                return None

            price = Decimal(sale_price_u) / Decimal("100.00")

            if title and price:
                logger.success(f"Parsed WB article {article}: {title} at {price:f} RUB")
                return title, price, clean_url

    except Exception as e:
        logger.error(f"Error parsing WB article {article}: {e}")

    return None
