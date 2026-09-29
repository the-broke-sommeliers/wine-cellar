import os

import django
from fastmcp import FastMCP

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "wine_cellar.conf.dev")

django.setup()

from typing import Literal  # noqa: E402

from wine_cellar.apps.wine.models import Wine, WineType  # noqa: E402
from wine_cellar.apps.wine.views import _total_stock_count  # noqa: E402

_WINE_TYPE_BY_LABEL = {str(label): code for code, label in WineType.choices}
WineTypeName = Literal[tuple(_WINE_TYPE_BY_LABEL.keys())]

mcp = FastMCP("wine-cellar")


@mcp.tool()
def list_wines_in_stock() -> str:
    """List all wines in stock."""
    wines_in_stock = (
        Wine.objects.filter(
            vintages__storageitem__isnull=False,
            vintages__storageitem__deleted=False,
        )
        .distinct()
        .annotate(total_stock_count=_total_stock_count())
    )

    lines = []
    for wine in wines_in_stock:
        lines.append(f"{wine.name}: {wine.total_stock} bottle(s) in stock.")

    return "\n".join(lines)


@mcp.tool()
def check_stock(wine_name: str) -> str:
    """Check if a wine is in stock."""
    wines = Wine.objects.filter(name__icontains=wine_name).annotate(
        total_stock_count=_total_stock_count()
    )

    if not wines.exists():
        return f"No stock found for '{wine_name}'."

    lines = []
    for wine in wines:
        count = wine.total_stock
        lines.append(f"{wine.name}: {count} bottle(s) in stock.")

    return "\n".join(lines)


@mcp.tool()
def food_pairing(food_name: str) -> str:
    """Check food pairing for a wine."""
    wines = (
        Wine.objects.filter(food_pairings__name__icontains=food_name)
        .distinct()
        .prefetch_related("food_pairings")
    )

    if not wines.exists():
        return f"No wine found for '{food_name}'."

    lines = []
    for wine in wines:
        lines.append(f"{wine.name}: {wine.get_food_pairings}")

    return "\n".join(lines)


@mcp.tool()
def wines_by_type(wine_type: WineTypeName) -> str:
    """List wines of a given type (e.g. red, white, sparkling)."""
    matched_code = _WINE_TYPE_BY_LABEL.get(wine_type)

    if not matched_code:
        return f"'{wine_type}' is not a recognised wine type."

    wines = Wine.objects.filter(wine_type=matched_code)

    if not wines.exists():
        return f"No '{wine_type}' wines found."

    lines = [f"There are {wines.count()} '{wine_type}' wines in the database"]
    for wine in wines:
        lines.append(f"{wine.name}")

    return "\n".join(lines)


# Only run the server when executing this file directly (python server.py)
if __name__ == "__main__":
    # Use the PORT environment variable in production, or default to 8000 for local dev
    port = int(os.environ.get("PORT", 8000))

    # Start the web server using Server-Sent Events (SSE)
    # mcp.run(transport="sse", host="0.0.0.0", port=port)
    mcp.run(transport="stdio")
