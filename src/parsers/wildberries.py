import re
from decimal import Decimal
from typing import Optional, Tuple

from curl_cffi.requests import AsyncSession
from loguru import logger

from src.core.config import settings


async def get_wb_product(url: str) -> Optional[Tuple[str, Decimal, str]]:
    """
    Parses a Wildberries URL or article number using stealth requests (curl_cffi).
    Impersonates a real Chrome browser to bypass 403 Forbidden errors.
    """
    # Extract article number from URL
    match = re.search(r"(?:catalog/|/catalog/|wb\.ru/catalog/)(\d+)", url)
    if match:
        article = match.group(1)
    else:
        if url.isdigit():
            article = url
        else:
            logger.debug(f"Invalid WB url/article format: {url}")
            return None

    clean_url = f"https://www.wildberries.ru/catalog/{article}/detail.aspx"
    # Using v4 API endpoint which is universal for articles
    api_url = f"https://card.wb.ru/cards/v4/detail?appType=1&curr=rub&dest=-1257786&nm={article}"

    headers = {
        "Accept": "*/*",
        "Accept-Language": "ru-RU,ru;q=0.9",
        "Origin": "https://www.wildberries.ru",
        "Referer": clean_url,
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "cross-site",
        "Priority": "u=1, i",
    }

    try:
        proxy = (
            settings.PROXY_URL
            if settings.PROXY_URL and settings.USE_PROXY_FOR_PARSER
            else None
        )
        logger.debug(
            f"Fetching WB API for article {article} (Stealth Mode, Proxy: {proxy is not None})..."
        )

        # curl_cffi impersonates Chrome 120+ TLS/HTTP fingerprint
        async with AsyncSession(impersonate="chrome", proxy=proxy) as session:
            response = await session.get(api_url, headers=headers, timeout=15.0)

            if response.status_code == 403:
                logger.error(
                    f"WB API still returned 403 for {article} even with impersonation. IP block is severe."
                )
                return None

            response.raise_for_status()
            data = response.json()

            products = data.get("data", {}).get("products", [])
            if not products:
                products = data.get("products", [])

            if not products:
                logger.debug(f"WB API returned no products for {article}")
                return None

            product_data = products[0]
            title = product_data.get("name")

            sizes = product_data.get("sizes", [])
            if not sizes:
                return None

            price_data = sizes[0].get("price")
            if not price_data:
                return None

            sale_price_u = price_data.get("product")
            if not sale_price_u:
                return None

            price = Decimal(sale_price_u) / Decimal("100.00")

            if title and price:
                logger.success(f"Parsed WB article {article}: {title} at {price:f} RUB")
                return title, price, clean_url

    except Exception as e:
        logger.error(f"Error parsing WB article {article}: {e}")

    return None
