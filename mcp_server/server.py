import os

import django
from fastmcp import FastMCP

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "wine_cellar.conf.dev")

django.setup()

from wine_cellar.apps.wine.models import Wine  # noqa: E402

mcp = FastMCP("wine-cellar")


@mcp.tool()
def list_wines_in_stock() -> str:
    """List all wines in stock."""
    wines_in_stock = Wine.objects.filter(
        vintages__storageitem__isnull=False,
        vintages__storageitem__deleted=False,
    )

    lines = []
    for wine in wines_in_stock:
        lines.append(f"{wine.name}: {wine.total_stock} bottle(s) in stock.")

    return "\n".join(lines)


@mcp.tool()
def check_stock(wine_name: str) -> str:
    """Check if a wine is in stock."""
    wines = Wine.objects.filter(name__icontains=wine_name)

    if not wines.exists():
        return f"No stock found for '{wine_name}'."

    lines = []
    for wine in wines:
        count = wine.total_stock
        lines.append(f"{wine.name}: {count} bottle(s) in stock.")

    return "\n".join(lines)


# Only run the server when executing this file directly (python server.py)
if __name__ == "__main__":
    # Use the PORT environment variable in production, or default to 8000 for local dev
    port = int(os.environ.get("PORT", 8000))

    # Start the web server using Server-Sent Events (SSE)
    # mcp.run(transport="sse", host="0.0.0.0", port=port)
    mcp.run(transport="stdio")
