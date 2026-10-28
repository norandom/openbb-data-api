"""FMP Helpers Module."""

from dataclasses import dataclass
from datetime import UTC, date, datetime
from functools import lru_cache
from typing import Any
from urllib.parse import urlencode

from openbb_core.provider.utils.errors import EmptyDataError
from openbb_core.provider.utils.helpers import get_querystring


@dataclass(frozen=True)
class FMPAcquisition:
    """Successful network receipt; transformations must retain this UTC timestamp."""

    payload: list | dict
    retrieved_at: datetime


async def response_callback(response, _, *, typed=False):
    """Classify protocol and legacy payload failures without exposing their text."""
    from openbb_fmp.utils.errors import classify, fail

    category = classify(response.status)
    if category:
        fail(
            category,
            typed=typed,
            retry_after=getattr(response, "headers", {}).get("Retry-After"),
        )
    try:
        data = await response.json()
    except Exception:  # noqa: BLE001 - JSON decoder failures must discard provider text.
        data = None
        invalid_response = True
    else:
        invalid_response = False
    if invalid_response:
        fail("invalid_response", typed=typed)
    if isinstance(data, dict):
        message = data.get("Error Message", data.get("error"))
        if message is not None:
            fail(
                classify(response.status, str(message)) or "upstream",
                typed=typed,
                retry_after=getattr(response, "headers", {}).get("Retry-After"),
            )
    if data == [] or data == {} or data is None:
        fail("missing_data", typed=typed)
    if not isinstance(data, (list, dict)) or (
        isinstance(data, list) and any(not isinstance(row, dict) for row in data)
    ):
        fail("invalid_response", typed=typed)
    return data


async def get_data(url: str, *, with_provenance=False, **kwargs: Any):
    """Get data from FMP endpoint."""
    # pylint: disable=import-outside-toplevel
    from aiohttp import ClientConnectionError
    from openbb_core.provider.utils.financial_errors import FinancialError
    from openbb_core.provider.utils.helpers import amake_request

    from openbb_fmp.utils.errors import FMPEmptyData, FMPError, FMPUnauthorized, fail

    async def callback(response, session):
        return await response_callback(response, session, typed=with_provenance)

    try:
        data = await amake_request(url, response_callback=callback, **kwargs)
    except TimeoutError:
        category = "timeout"
    except (ConnectionError, ClientConnectionError):
        category = "connection"
    except (FinancialError, FMPError, FMPUnauthorized, FMPEmptyData):
        raise
    except Exception:  # noqa: BLE001 - Unknown transport failures may contain credentials.
        category = "transport"
    else:
        return FMPAcquisition(data, datetime.now(UTC)) if with_provenance else data
    # Raise outside the handler so the unsafe original exception is not chained.
    fail(category, typed=with_provenance)


async def get_data_urls(urls: list[str], **kwargs: Any) -> list | dict:
    """Fetch one to twenty URLs serially; failures stop the batch without retries."""
    # pylint: disable=import-outside-toplevel
    from openbb_fmp.utils.errors import fail

    # Sequential requests bound concurrency and stop on the first failure.
    if (
        not isinstance(urls, list)
        or not 1 <= len(urls) <= 20
        or any(not isinstance(url, str) or not url for url in urls)
    ):
        fail("invalid_parameters", typed=kwargs.get("with_provenance", False))
    results = []
    for url in urls:
        result = await get_data(url, **kwargs)
        if isinstance(result, list):
            results.extend(result)
        else:
            results.append(result)
    return results


def create_url(
    version: int,
    endpoint: str,
    api_key: str | None,
    query: Any | None = None,
    exclude: list[str] | None = None,
) -> str:
    """Return a URL for the FMP API.

    Parameters
    ----------
    version: int
        The version of the API to use.
    endpoint: str
        The endpoint to use.
    api_key: str
        The API key to use.
    query: Optional[BaseModel]
        The dictionary to be turned into a querystring.
    exclude: list[str]
        The keys to be excluded from the querystring.

    Returns
    -------
    str
        The querystring.
    """
    # pylint: disable=import-outside-toplevel
    from pydantic import BaseModel

    the_dict = {}
    if query:
        the_dict = query.model_dump() if isinstance(query, BaseModel) else query
    query_string = urlencode(
        {
            k: v
            for k, v in the_dict.items()
            if k not in (exclude or []) and k != "apikey" and v is not None
        }
    )
    base_url = f"https://financialmodelingprep.com/api/v{version}/"
    return f"{base_url}{endpoint}?{query_string}&{urlencode({'apikey': api_key or ''})}"


async def get_data_many(
    url: str, sub_dict: str | None = None, **kwargs: Any
) -> list[dict] | FMPAcquisition:
    """Get data from FMP endpoint and convert to list of schemas.

    Parameters
    ----------
    url: str
        The URL to get the data from.
    sub_dict: Optional[str]
        The sub-dictionary to use.

    Returns
    -------
    list[dict]
        Dictionary of data.
    """
    acquired = await get_data(url, **kwargs)
    data = acquired.payload if isinstance(acquired, FMPAcquisition) else acquired

    if sub_dict and isinstance(data, dict):
        data = data.get(sub_dict, [])
    from openbb_fmp.utils.errors import fail

    if not isinstance(data, list) or any(not isinstance(row, dict) for row in data):
        fail("invalid_response", typed=kwargs.get("with_provenance", False))
    if len(data) == 0:
        fail("missing_data", typed=kwargs.get("with_provenance", False))

    return (
        FMPAcquisition(data, acquired.retrieved_at)
        if isinstance(acquired, FMPAcquisition)
        else data
    )


async def get_data_one(url: str, **kwargs: Any) -> dict | FMPAcquisition:
    """Get data from FMP endpoint and convert to schema."""
    acquired = await get_data(url, **kwargs)
    data = acquired.payload if isinstance(acquired, FMPAcquisition) else acquired
    if isinstance(data, list):
        if len(data) == 0:
            raise ValueError("Expected dict, got empty list")

        try:
            data = {i: data[i] for i in range(len(data))} if len(data) > 1 else data[0]
        except TypeError as e:
            raise ValueError("Expected dict, got list of dicts") from e

    return (
        FMPAcquisition(data, acquired.retrieved_at)
        if isinstance(acquired, FMPAcquisition)
        else data
    )


def most_recent_quarter(base: date | None = None) -> date:
    """Get the most recent quarter date."""
    if base is None:
        base = date.today()
    base = min(base, date.today())  # This prevents dates from being in the future
    exacts = [(3, 31), (6, 30), (9, 30), (12, 31)]
    for exact in exacts:
        if base.month == exact[0] and base.day == exact[1]:
            return base
    if base.month < 4:
        return date(base.year - 1, 12, 31)
    if base.month < 7:
        return date(base.year, 3, 31)
    if base.month < 10:
        return date(base.year, 6, 30)
    return date(base.year, 9, 30)


def get_interval(value: str) -> str:
    """Get the intervals for the FMP API."""
    intervals = {
        "m": "min",
        "h": "hour",
        "d": "day",
    }

    return f"{value[:-1]}{intervals[value[-1]]}"


async def get_historical_ohlc(query, credentials, **kwargs: Any) -> list[dict]:
    """Return the raw data from the FMP endpoint."""
    # pylint: disable=import-outside-toplevel
    import asyncio  # noqa
    from openbb_core.provider.utils.helpers import (
        amake_request,
    )
    from warnings import warn

    api_key = credentials.get("fmp_api_key") if credentials else ""

    base_url = "https://financialmodelingprep.com/stable/"

    if hasattr(query, "adjustment") and query.adjustment == "unadjusted":
        base_url += "historical-price-eod/non-split-adjusted?"
    elif hasattr(query, "adjustment") and query.adjustment == "splits_and_dividends":
        base_url += "historical-price-eod/dividend-adjusted?"
    elif query.interval == "1d":
        base_url += "historical-price-eod/full?"
    elif query.interval == "1m":
        base_url += "historical-chart/1min?"
    elif query.interval == "5m":
        base_url += "historical-chart/5min?"
    elif query.interval in ["60m", "1h"]:
        query.interval = "60m"
        base_url += "historical-chart/1hour?"

    query_str = get_querystring(
        query.model_dump(), ["symbol", "adjustment", "interval"]
    )
    symbols = query.symbol.split(",")

    results: list = []
    messages: list = []

    async def get_one(symbol):
        """Get data for one symbol."""
        url = f"{base_url}symbol={symbol}&{query_str}&apikey={api_key}"
        data: list = []
        response = await amake_request(
            url, response_callback=response_callback, **kwargs
        )

        if isinstance(response, dict) and response.get("Error Message"):
            message = (
                f"Error fetching data for {symbol}: {response.get('Error Message', '')}"
            )
            warn(message)
            messages.append(message)

        if isinstance(response, list) and len(response) > 0:
            data = response

        elif isinstance(response, dict) and response.get("historical"):
            data = response.get("historical", [])

        if not data:
            message = f"No data found for {symbol}."
            warn(message)
            messages.append(message)

        elif data:
            for d in data:
                d["symbol"] = symbol
                results.append(d)

    await asyncio.gather(*[get_one(symbol) for symbol in symbols])

    if not results:
        raise EmptyDataError(
            f"{str(','.join(messages)).replace(',', ' ') if messages else 'No data found'}"
        )

    return results


@lru_cache(maxsize=1)
def get_available_transcript_symbols(api_key) -> list:
    """Return the available symbols for earnings call transcripts."""
    # pylint: disable=import-outside-toplevel
    from openbb_core.provider.utils.helpers import make_request

    url = f"https://financialmodelingprep.com/stable/earnings-transcript-list?apikey={api_key}"

    data = make_request(url)

    data.raise_for_status()

    return data.json()


@lru_cache(maxsize=64)
def get_transcript_dates_for_symbol(symbol: str, api_key: str) -> list:
    """Return the available dates for a given symbol's earnings call transcripts."""
    # pylint: disable=import-outside-toplevel
    from openbb_core.provider.utils.helpers import make_request

    url = f"https://financialmodelingprep.com/stable/earning-call-transcript-dates?symbol={symbol}&apikey={api_key}"

    data = make_request(url)

    data.raise_for_status()

    return data.json()
