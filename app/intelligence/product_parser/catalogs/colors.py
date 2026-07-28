"""Color alias catalog.

Maps normalized color codes / names → canonical color labels.
Keys must be lowercase.
"""

from __future__ import annotations

COLOR_ALIASES: dict[str, str] = {
    # Apple Titanium (iPhone 15/16/17 Pro)
    "bt": "Black Titanium",
    "black titanium": "Black Titanium",
    "blk titanium": "Black Titanium",
    "wt": "White Titanium",
    "white titanium": "White Titanium",
    "nt": "Natural Titanium",
    "natural titanium": "Natural Titanium",
    "nat titanium": "Natural Titanium",
    "dt": "Desert Titanium",
    "desert titanium": "Desert Titanium",
    "blue titanium": "Blue Titanium",
    "blt": "Blue Titanium",
    # Common solid colors
    "black": "Black",
    "blk": "Black",
    "white": "White",
    "wht": "White",
    "blue": "Blue",
    "blu": "Blue",
    "red": "Red",
    "green": "Green",
    "grn": "Green",
    "pink": "Pink",
    "purple": "Purple",
    "ppl": "Purple",
    "yellow": "Yellow",
    "gold": "Gold",
    "silver": "Silver",
    "slv": "Silver",
    "graphite": "Graphite",
    "midnight": "Midnight",
    "starlight": "Starlight",
    "sierra blue": "Sierra Blue",
    "alpine green": "Alpine Green",
    "deep purple": "Deep Purple",
    "space black": "Space Black",
    "space gray": "Space Gray",
    "space grey": "Space Gray",
    "ultramarine": "Ultramarine",
    "teal": "Teal",
}
