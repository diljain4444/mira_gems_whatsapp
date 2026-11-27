
import os
import requests

from dotenv import load_dotenv

load_dotenv()


# ============================================================
# 1. API CONFIGURATION
# ============================================================

API_URL = (
    "http://api.miragems.com/"
    "MiraGemsPortalStock.svc/GetMiraGemsDAStock"
)

API_KEY = os.getenv("MIRA_GEMS_API_KEY")


# ============================================================
# 2. NORMALIZATION
# ============================================================

def clean_text(value):
    if value is None:
        return ""

    return str(value).strip().upper()


def normalize_availability(value):

    mapping = {
        "A": "AVAILABLE",
        "AVAILABLE": "AVAILABLE",
        "M": "MEMO",
        "MEMO": "MEMO",
        "H": "HOLD",
        "HOLD": "HOLD"
    }

    return mapping.get(clean_text(value), clean_text(value))


def normalize_quality_grade(value):

    mapping = {
        "EX": "EX",
        "EXCELLENT": "EX",
        "ID": "EX",
        "IDEAL": "EX",
        "VG": "VG",
        "VG+": "VG",
        "VERY GOOD": "VG",
        "G": "G",
        "GOOD": "G"
    }

    return mapping.get(clean_text(value), clean_text(value))


# ============================================================
# 3. BUSINESS CATEGORY
# ============================================================

def calculate_business_category(stone):

    shape = clean_text(stone.get("Shape"))

    cut = normalize_quality_grade(stone.get("Cut"))
    polish = normalize_quality_grade(stone.get("Polish"))
    symm = normalize_quality_grade(stone.get("Symm"))

    if shape == "ROUND":
        grades = [cut, polish, symm]
    else:
        grades = [polish, symm]

    if any(grade and grade != "EX" for grade in grades):
        return "VG"

    if all(grade == "EX" for grade in grades):
        return "EX"

    return ""


# ============================================================
# 4. FETCH INVENTORY - ONLY ONCE
# ============================================================

def fetch_inventory():

    if not API_KEY:
        raise ValueError(
            "MIRA_GEMS_API_KEY environment variable is missing."
        )

    try:

        response = requests.get(
            API_URL,
            params={"ApiKey": API_KEY},
            timeout=60
        )

        response.raise_for_status()

        data = response.json()

        result = data.get("GetMiraGemsDAStockResult", {})

        if not isinstance(result, dict):
            raise ValueError("Invalid API result structure.")

        inventory = result.get("Data", [])

        if not isinstance(inventory, list):
            raise ValueError("Inventory data is not a list.")

        print(f"Total inventory fetched: {len(inventory)}")

        return inventory

    except requests.RequestException as e:
        raise RuntimeError(f"API request failed: {e}") from e

    except (ValueError, TypeError) as e:
        raise RuntimeError(f"Invalid API response: {e}") from e


# ============================================================
# 5. GET MULTIPLE STONE DETAILS
# ============================================================

def get_multiple_stone_details(stone_ids):

    if isinstance(stone_ids, str):
        stone_ids = [stone_ids]

    # Clean IDs and remove duplicates
    requested_ids = list(dict.fromkeys(
        str(stone_id).strip()
        for stone_id in stone_ids
        if stone_id is not None and str(stone_id).strip()
    ))

    if not requested_ids:
        raise ValueError("Please provide at least one valid Stock ID.")

    # Fetch inventory only once
    inventory = fetch_inventory()

    # Create StockId lookup for fast searching
    inventory_lookup = {}

    for stone in inventory:

        if not isinstance(stone, dict):
            continue

        stock_id = str(stone.get("StockId", "")).strip().casefold()

        if stock_id:
            inventory_lookup.setdefault(stock_id, []).append(stone)

    matched_stones = []
    not_found = []
    duplicates = []

    for stone_id in requested_ids:

        key = stone_id.casefold()

        matches = inventory_lookup.get(key, [])

        if not matches:
            not_found.append(stone_id)
            continue

        if len(matches) > 1:
            duplicates.append(stone_id)
            continue

        stone = matches[0].copy()

        # Add calculated information
        stone["business_category"] = calculate_business_category(stone)

        # Normalize availability
        stone["Availability"] = normalize_availability(
            stone.get("Availability")
        )

        matched_stones.append(stone)

    return {
        "total_requested": len(requested_ids),
        "total_found": len(matched_stones),
        "total_not_found": len(not_found),
        "total_duplicates": len(duplicates),
        "matched_stones": matched_stones,
        "not_found": not_found,
        "duplicates": duplicates
    }


# ============================================================
# 6. CUSTOMER-FRIENDLY DETAILS
# ============================================================

FIELD_LABELS = {
    "StockId": "Stock ID",
    "Availability": "Availability",
    "Shape": "Shape",
    "Weight": "Carat Weight",
    "Color": "Color",
    "Clarity": "Clarity",
    "Cut": "Cut",
    "Polish": "Polish",
    "Symm": "Symmetry",
    "Fls": "Fluorescence",
    "Lab": "Certification / Lab",
    "FinalPrice": "Final Price",
    "Location": "Location",
    "Measurements": "Measurements"
}


def format_customer_details(result):
    formatted_stones = []
    for stone in result["matched_stones"]:
        lines = []

        for field, label in FIELD_LABELS.items():

            value = stone.get(field)

            if value is None or str(value).strip() == "":
                continue

            lines.append(f"{label}: {value}")

        formatted_stones.append("\n".join(lines))

    return "\n\n".join(
        f"DIAMOND {index + 1}\n{details}"
        for index, details in enumerate(formatted_stones)
    )


# ============================================================
# 7. TESTING
# ============================================================

if __name__ == "__main__":

    stone_ids = [
        "B000216",
        "B000217",
        "B000218"
    ]

    try:

        result = get_multiple_stone_details(stone_ids)

        print("\n========== SEARCH SUMMARY ==========")

        print("Requested:", result["total_requested"])
        print("Found:", result["total_found"])
        print("Not found:", result["total_not_found"])
        print("Duplicates:", result["total_duplicates"])

        if result["matched_stones"]:

            print("\n========== CUSTOMER DETAILS ==========\n")

            print(format_customer_details(result))

        if result["not_found"]:
            print("\nSTOCK IDs NOT FOUND:")
            print(result["not_found"])

        if result["duplicates"]:
            print("\nDUPLICATE STOCK IDs:")
            print(result["duplicates"])

    except Exception as e:

        print("ERROR:", str(e))
