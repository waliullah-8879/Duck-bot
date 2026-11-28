"""Map each species (casefold) to the local reference image the user uploaded.

The images were provided by the user as identification charts covering
common ducks, geese, and other waterbirds.  Every species that appears
in the uploaded charts is listed here.  Species without a matching
reference image map to None; the verifier skips them gracefully.
"""
from pathlib import Path

# Base directories where reference images are stored
_REPO_REF_DIR = Path(__file__).parent / "assets" / "references"
_FALLBACK_REF_DIR = Path(r"C:\Users\asus'\.gemini\antigravity\brain\ee7a8668-6d7c-47db-933b-60dde60cd936\.user_uploaded")

# Species name (casefold) → reference image filename
# Charts uploaded cover: Types of Ducks (AnimalSpot), Duck ID Chart,
# Ducks/Geese/Swans Guide, flight silhouettes, Cornell Lab diving ducks
_RAW_MAP: dict[str, str | None] = {
    # --- Ducks visible in uploaded charts ---
    "mallard":                    "media_1794810862380_ebdb1c6c.jpg",   # Types of Ducks chart
    "northern pintail":           "media_1794810975255_8f0e2d06.jpg",   # Duck ID chart
    "wood duck":                  "media_1794810975255_8f0e2d06.jpg",
    "american wigeon":            "media_1794810975255_8f0e2d06.jpg",
    "canvasback":                 "media_1794810975255_8f0e2d06.jpg",
    "gadwall":                    "media_1794810975255_8f0e2d06.jpg",
    "northern shoveler":          "media_1794810975255_8f0e2d06.jpg",
    "common goldeneye":           "media_1794810975255_8f0e2d06.jpg",
    "redhead":                    "media_1794810975255_8f0e2d06.jpg",
    "ruddy duck":                 "media_1794810975255_8f0e2d06.jpg",
    "eurasian wigeon":            "media_1794810975255_8f0e2d06.jpg",
    "tufted duck":                "media_1794810975255_8f0e2d06.jpg",
    # Guide to ducks, geese & swans chart
    "common teal":                "media_1794810945986_d698b2b1.jpg",
    "garganey":                   "media_1794810945986_d698b2b1.jpg",
    "mandarin duck":              "media_1794810945986_d698b2b1.jpg",
    # Cornell Lab diving-ducks chart
    "ring-necked duck":           "media_1794811127799_920fa42c.jpg",
    "common merganser":           "media_1794811127799_920fa42c.jpg",
    "lesser scaup":               "media_1794811127799_920fa42c.jpg",
    "greater scaup":              "media_1794811127799_920fa42c.jpg",
    "bufflehead":                 "media_1794811127799_920fa42c.jpg",
    "hooded merganser":           "media_1794811127799_920fa42c.jpg",
    "red-breasted merganser":     "media_1794811127799_920fa42c.jpg",
    "barrow's goldeneye":         "media_1794811127799_920fa42c.jpg",
    # Flight-silhouette chart (all waterfowl in flight)
    "canada goose":               "media_1794811109584_b725dde1.jpg",
    "greater snow goose":         "media_1794811109584_b725dde1.jpg",
    "white-fronted goose":        "media_1794811109584_b725dde1.jpg",
    "brant":                      "media_1794811109584_b725dde1.jpg",
    "trumpeter swan":             "media_1794811109584_b725dde1.jpg",
    "whistling swan":             "media_1794811109584_b725dde1.jpg",
    "bufflehead (flight)":        "media_1794811109584_b725dde1.jpg",
    "greater white-fronted goose":"media_1794811109584_b725dde1.jpg",
    # Types-of-Ducks infographic (Outforia)
    "blue-winged teal":           "media_1794810991910_380dec41.jpg",
    "cinnamon teal":              "media_1794810991910_380dec41.jpg",
    "american black duck":        "media_1794810991910_380dec41.jpg",
    "black scoter":               "media_1794810991910_380dec41.jpg",
    "harlequin duck":             "media_1794810991910_380dec41.jpg",
    "red-breasted merganser (inf)":"media_1794810991910_380dec41.jpg",
    # --- Species in our topic list without a matching chart ---
    "bar-headed goose":           None,
    "greylag goose":              None,
    "common crane":               None,
    "demoiselle crane":           None,
    "houbara bustard":            None,
    "greater flamingo":           None,
    "lesser flamingo":            None,
    "great white pelican":        None,
    "dalmatian pelican":          None,
    "eurasian spoonbill":         None,
    "black stork":                None,
    "white stork":                None,
    "black-headed gull":          None,
    "brown-headed gull":          None,
    "common cormorant":           None,
    "great cormorant":            None,
    "eurasian curlew":            None,
    "common snipe":               None,
    "little stint":               None,
    "green sandpiper":            None,
    "wood sandpiper":             None,
    "common greenshank":          None,
    "black-tailed godwit":        None,
    "kentish plover":             None,
    "yellow wagtail":             None,
    "white wagtail":              None,
    "barn swallow":               None,
    "sand martin":                None,
    "bluethroat":                 None,
    "common starling":            None,
    "common chiffchaff":          None,
    "osprey":                     None,
    "ruddy shelduck":             None,
    "common shelduck":            None,
    "common pochard":             None,
    "red-crested pochard":        None,
}


def get_reference_image(species: str) -> Path | None:
    """Return the absolute Path of the reference image for *species*, or None."""
    filename = _RAW_MAP.get(species.casefold())
    if filename is None:
        return None
    for ref_dir in (_REPO_REF_DIR, _FALLBACK_REF_DIR):
        candidate = ref_dir / filename
        if candidate.exists():
            return candidate
    return None

