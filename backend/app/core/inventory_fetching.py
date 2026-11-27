import os
import re
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

AVAILABLE_VALUES = {"A", "AVAILABLE"}

# When a customer specifies a single exact carat weight (e.g. 14.07) the
# stored weight in the API may differ by a tiny floating-point amount.
# Allow a small tolerance so that e.g. 14.0700001 still matches 14.07.
CARAT_TOLERANCE = 0.005


# ============================================================
# 2. BASIC NORMALIZATION
# ============================================================

def clean_text(value):

    if value is None:
        return ""

    return str(value).strip().upper()


def to_float(value):

    try:
        if value is None or str(value).strip() == "":
            return None

        return float(str(value).replace(",", "").strip())

    except (ValueError, TypeError):
        return None


def normalize_shape(value):

    return clean_text(value)


def normalize_fluorescence(value):

    value = clean_text(value)

    mapping = {
        "NON": "NON",
        "NONE": "NON",
        "NO": "NON",
        "NO FLUORESCENCE": "NON",
        "NON FLUORESCENCE": "NON",

        "SLT": "SLT",
        "SLIGHT": "SLT",

        "STG": "STG",
        "STRONG": "STG"
    }

    return mapping.get(value, value)


def normalize_business_category(value):

    value = clean_text(value)

    mapping = {
        "EX": "EX",
        "3EX": "EX",
        "X": "EX",
        "EX EX EX": "EX",
        "EXCELLENT": "EX",

        "VG": "VG",
        "VG+": "VG",
        "VERY GOOD": "VG"
    }

    return mapping.get(value, value)


# ============================================================
# 3. NORMALIZE MULTIPLE COLOR REQUIREMENTS
# ============================================================

COLOR_ORDER = [
    "D", "E", "F", "G", "H",
    "I", "J", "K", "L", "M"
]


def expand_color_range(start, end):

    if start not in COLOR_ORDER or end not in COLOR_ORDER:
        return []

    start_index = COLOR_ORDER.index(start)
    end_index = COLOR_ORDER.index(end)

    if start_index > end_index:
        return []

    return COLOR_ORDER[start_index:end_index + 1]


def normalize_color_requirement(value):

    if not value:
        return []

    # Already a list from the extraction model
    if isinstance(value, list):

        colors = []

        for item in value:
            if isinstance(item, list):
                colors.extend(normalize_color_requirement(item))
                continue

            item_str = clean_text(item)

            if item_str in COLOR_ORDER:
                colors.append(item_str)
            elif item_str:
                colors.extend(normalize_color_requirement(item_str))

        return list(dict.fromkeys(colors))

    value = clean_text(value)

    if not value:
        return []

    # Examples: D-F, D/F, D TO F
    range_match = re.fullmatch(
        r"([D-M])\s*(?:-|/|TO)\s*([D-M])",
        value
    )

    if range_match:

        return expand_color_range(
            range_match.group(1),
            range_match.group(2)
        )

    # Examples: DEF, DEFG
    if (
        len(value) >= 2
        and all(char in COLOR_ORDER for char in value)
    ):

        return list(dict.fromkeys(value))

    # Examples: D E F
    tokens = re.findall(r"\b[D-M]\b", value)

    if len(tokens) > 1:
        return list(dict.fromkeys(tokens))

    # Single color
    if value in COLOR_ORDER:
        return [value]

    return []


# ============================================================
# 4. NORMALIZE MULTIPLE CLARITY REQUIREMENTS
# ============================================================

CLARITY_ORDER = [
    "IF",
    "VVS1",
    "VVS2",
    "VS1",
    "VS2",
    "SI1",
    "SI2"
]


def expand_clarity_range(start, end):

    if start not in CLARITY_ORDER:
        return []

    if end not in CLARITY_ORDER:
        return []

    start_index = CLARITY_ORDER.index(start)
    end_index = CLARITY_ORDER.index(end)

    if start_index > end_index:
        return []

    return CLARITY_ORDER[start_index:end_index + 1]


CLARITY_GROUPS = {
    "VVS": ["VVS1", "VVS2"],
    "VS":  ["VS1", "VS2"],
    "SI":  ["SI1", "SI2"],
}


def normalize_clarity_requirement(value):

    if not value:
        return []

    # Already a list from the extraction model
    if isinstance(value, list):

        clarities = []

        for item in value:
            if isinstance(item, list):
                clarities.extend(normalize_clarity_requirement(item))
                continue

            item_str = clean_text(item)

            if item_str in CLARITY_ORDER:
                clarities.append(item_str)
            elif item_str:
                clarities.extend(normalize_clarity_requirement(item_str))

        return list(dict.fromkeys(clarities))

    value = clean_text(value)

    if not value:
        return []

    # Group shorthands: VVS -> [VVS1, VVS2], VS -> [VS1, VS2], SI -> [SI1, SI2]
    if value in CLARITY_GROUPS:
        return list(CLARITY_GROUPS[value])

    # VVS-VS, VVS/VS, VVS TO VS, VVS1-VS1, etc.
    range_match = re.fullmatch(
        r"(IF|VVS[12]?|VS[12]?|SI[12]?)\s*(?:-|/|TO)\s*(IF|VVS[12]?|VS[12]?|SI[12]?)",
        value
    )

    if range_match:

        start = range_match.group(1)
        end = range_match.group(2)

        # Convert group names into their first and last grades
        group_start = {
            "IF": "IF",
            "VVS": "VVS1",
            "VS": "VS1",
            "SI": "SI1"
        }

        group_end = {
            "IF": "IF",
            "VVS": "VVS2",
            "VS": "VS2",
            "SI": "SI2"
        }

        return expand_clarity_range(
            group_start.get(start, start),
            group_end.get(end, end)
        )

    # Individual clarity
    if value in CLARITY_ORDER:
        return [value]

    # Space / comma / slash separated tokens e.g. "VVS1, VVS2" or "VVS VS"
    tokens = re.findall(r"\b(?:IF|VVS[12]?|VS[12]?|SI[12]?)\b", value)
    if tokens:
        clarities = []
        for tok in tokens:
            if tok in CLARITY_GROUPS:
                clarities.extend(CLARITY_GROUPS[tok])
            elif tok in CLARITY_ORDER:
                clarities.append(tok)
        return list(dict.fromkeys(clarities))

    return []


# ============================================================
# 5. CALCULATE BUSINESS CATEGORY
# ============================================================

def normalize_quality_grade(value):

    value = clean_text(value)

    mapping = {
        "EX": "EX",
        "EXCELLENT": "EX",
        "ID": "EX",
        "IDEAL": "EX",
        "VG": "VG",
        "VG+": "VG",
        "VERY GOOD": "VG",
        "GD": "GD",
        "G": "GD",
        "GOOD": "GD"
    }

    return mapping.get(value, value)


def calculate_business_category(stone):

    shape = normalize_shape(stone.get("Shape"))

    cut = normalize_quality_grade(stone.get("Cut"))
    polish = normalize_quality_grade(stone.get("Polish"))
    symm = normalize_quality_grade(stone.get("Symm"))

    if shape == "ROUND":

        # Round requires Cut + Polish + Symmetry

        grades = [cut, polish, symm]

    else:

        # Fancy requires Polish + Symmetry

        grades = [polish, symm]

    # If any known grade is not EX, category is VG
    if any(grade and grade != "EX" for grade in grades):
        return "VG"

    # EX requires all required grades to be present
    if all(grade == "EX" for grade in grades):
        return "EX"

    # Insufficient quality information
    return ""


# ============================================================
# 6. FETCH INVENTORY FROM API
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

        if not isinstance(data, dict):
            raise ValueError("API response is not a valid object.")

        result = data.get("GetMiraGemsDAStockResult", {})

        if not isinstance(result, dict):
            raise ValueError("Invalid API result structure.")

        inventory = result.get("Data", [])

        if not isinstance(inventory, list):
            raise ValueError("Inventory Data is not a list.")

        print(f"Total API stones fetched: {len(inventory)}")

        return inventory

    except requests.RequestException as e:

        raise RuntimeError(
            f"Inventory API request failed: {e}"
        ) from e

    except (ValueError, TypeError) as e:

        raise RuntimeError(
            f"Invalid inventory API response: {e}"
        ) from e


# ============================================================
# 7. CERTIFICATION MATCHING
# ============================================================

def matches_certification(stone, requirement):

    requirement = clean_text(requirement)

    # No certification preference
    if not requirement:
        return True

    lab = clean_text(stone.get("Lab"))

    recognized_labs = {"IGI", "WISE"}

    # Specifically requires IGI
    if requirement == "IGI":
        return lab == "IGI"

    # Any recognized certificate
    if requirement in {"CERTI", "CERTIFIED"}:
        return lab in recognized_labs

    # Non-certified
    if requirement in {
        "NONE",
        "NON",
        "NON-CERTI",
        "NON CERTI",
        "NON-CERTIFIED",
        "NON CERTIFIED"
    }:

        return lab not in recognized_labs

    # Unknown requirement should not silently match
    return False


# ============================================================
# 8. AVAILABILITY MATCHING
# ============================================================

def matches_availability(stone):

    availability = clean_text(
        stone.get("Availability")
    )

    return availability in AVAILABLE_VALUES


# ============================================================
# 9. INDIVIDUAL STONE MATCHING
# ============================================================

def matches_stone(stone, requirement):

    # --------------------------------------------------------
    # A. Availability
    # --------------------------------------------------------

    if not matches_availability(stone):
        return False

    # --------------------------------------------------------
    # B. Shape
    # --------------------------------------------------------

    required_shape = normalize_shape(
        requirement.get("shape")
    )

    actual_shape = normalize_shape(
        stone.get("Shape")
    )

    if required_shape and actual_shape != required_shape:
        return False

    # --------------------------------------------------------
    # C. Color - Single or Multiple
    # --------------------------------------------------------

    required_colors = normalize_color_requirement(
        requirement.get("color")
    )

    actual_color = clean_text(
        stone.get("Color")
    )

    if required_colors and actual_color not in required_colors:
        return False

    # --------------------------------------------------------
    # D. Clarity - Single or Multiple
    # --------------------------------------------------------

    required_clarities = normalize_clarity_requirement(
        requirement.get("clarity")
    )

    actual_clarity = clean_text(
        stone.get("Clarity")
    )

    if (
        required_clarities
        and actual_clarity not in required_clarities
    ):
        return False

    # --------------------------------------------------------
    # E. Carat Range - Inclusive
    # --------------------------------------------------------

    weight = to_float(
        stone.get("Weight")
    )

    carat_min = to_float(
        requirement.get("carat_min")
    )

    carat_max = to_float(
        requirement.get("carat_max")
    )

    if carat_min is not None or carat_max is not None:

        # When both bounds are equal the customer gave an exact carat weight
        # (e.g. '14.07'). Apply a small tolerance so minor float differences
        # in the stored weight (e.g. 14.0700001) do not prevent a match.
        effective_min = carat_min
        effective_max = carat_max
        if (
            carat_min is not None
            and carat_max is not None
            and carat_min == carat_max
        ):
            effective_min = carat_min - CARAT_TOLERANCE
            effective_max = carat_max + CARAT_TOLERANCE

        if effective_min is not None:
            if weight is None or weight < effective_min:
                return False

        if effective_max is not None:
            if weight is None or weight > effective_max:
                return False

    # --------------------------------------------------------
    # F. Fluorescence
    # --------------------------------------------------------

    required_fls = normalize_fluorescence(
        requirement.get("fluorescence")
    )

    actual_fls = normalize_fluorescence(
        stone.get("Fls")
    )

    if required_fls and actual_fls != required_fls:
        return False

    # --------------------------------------------------------
    # G. Certification
    # --------------------------------------------------------

    if not matches_certification(
        stone,
        requirement.get("certification", "")
    ):
        return False

    # --------------------------------------------------------
    # H. Quality Grade Matching (two-mode)
    # --------------------------------------------------------
    # Mode A (shorthand): user said "EX", "3EX", "VG", etc.
    #   → cut / polish / symm are all empty → compare by business_category.
    # Mode B (specific):  user said "EX VG VG" / "VG EX" etc.
    #   → at least one of cut/polish/symm is set → each specified grade
    #     must match the stone's individual grade exactly.
    # --------------------------------------------------------

    req_cut    = normalize_quality_grade(requirement.get("cut") or "")
    req_polish = normalize_quality_grade(requirement.get("polish") or "")
    req_symm   = normalize_quality_grade(requirement.get("symm") or "")

    has_specific_grades = bool(req_cut or req_polish or req_symm)

    if has_specific_grades:
        # Specific-grade mode: each set grade must match exactly.
        stone_cut    = normalize_quality_grade(stone.get("Cut") or "")
        stone_polish = normalize_quality_grade(stone.get("Polish") or "")
        stone_symm   = normalize_quality_grade(stone.get("Symm") or "")

        is_round = (actual_shape == "ROUND") if required_shape else True

        if is_round:
            # ROUND: cut + polish + symm
            if req_cut    and stone_cut    != req_cut:    return False
            if req_polish and stone_polish != req_polish: return False
            if req_symm   and stone_symm   != req_symm:   return False
        else:
            # FANCY: polish + symm only (cut is ignored)
            if req_polish and stone_polish != req_polish: return False
            if req_symm   and stone_symm   != req_symm:   return False
    else:
        # Shorthand mode: use business_category as before.
        required_category = normalize_business_category(
            requirement.get("business_category")
        )

        if required_category:

            actual_category = calculate_business_category(stone)

            if not actual_category:
                return False

            if actual_category != required_category:
                return False

    return True


# ============================================================
# 10. SIMILAR DIAMOND FINDER (Fallback when exact match = 0)
# ============================================================

# How many similar stones to return at most
SIMILAR_DIAMONDS_LIMIT = 8

# Carat tolerance for relaxed similar search: +-5% of the demanded weight
SIMILAR_CARAT_PERCENT = 0.05

# Fluorescence adjacency order (best to worst quality perception)
FLS_ORDER = ["NON", "SLT", "MED", "STG"]

# Business category adjacency order (best to lower)
CATEGORY_ORDER = ["EX", "VG", "G"]


def _color_distance(c1, c2):
    """Return absolute distance between two color grades. None if either unknown."""
    if c1 not in COLOR_ORDER or c2 not in COLOR_ORDER:
        return None
    return abs(COLOR_ORDER.index(c1) - COLOR_ORDER.index(c2))


def _clarity_distance(c1, c2):
    """Return absolute distance between two clarity grades. None if either unknown."""
    if c1 not in CLARITY_ORDER or c2 not in CLARITY_ORDER:
        return None
    return abs(CLARITY_ORDER.index(c1) - CLARITY_ORDER.index(c2))


def _fls_distance(f1, f2):
    """Return absolute distance between two fluorescence values. None if either unknown."""
    if f1 not in FLS_ORDER or f2 not in FLS_ORDER:
        return None
    return abs(FLS_ORDER.index(f1) - FLS_ORDER.index(f2))


def _category_distance(cat1, cat2):
    """Return distance between business categories. None if either unknown."""
    if cat1 not in CATEGORY_ORDER or cat2 not in CATEGORY_ORDER:
        return None
    return abs(CATEGORY_ORDER.index(cat1) - CATEGORY_ORDER.index(cat2))


def _cert_distance(lab, req_cert):
    """
    Return a distance score for certification mismatch.
    0 = exact match, 1 = slightly relaxed, 2 = more different.
    """
    req_cert = clean_text(req_cert)
    lab = clean_text(lab)
    if not req_cert:
        return 0
    if req_cert == "IGI":
        return 0 if lab == "IGI" else (1 if lab in {"WISE"} else 2)
    if req_cert in {"CERTI", "CERTIFIED"}:
        return 0 if lab in {"IGI", "WISE"} else 2
    if req_cert in {"NONE", "NON", "NON-CERTI", "NON CERTI", "NON-CERTIFIED", "NON CERTIFIED"}:
        return 0 if lab not in {"IGI", "WISE"} else 2
    return 1


def _build_diff_tags(stone, requirement):
    """
    Compare a stone against the original requirement and return a list of
    human-readable difference tags shown as badges in the UI.
    E.g. ["Color: E (adj)", "Clarity: VS1 (better)", "Carat: 10.50ct (+5%)"]
    """
    tags = []

    # --- Color ---
    req_colors = normalize_color_requirement(requirement.get("color"))
    actual_color = clean_text(stone.get("Color"))
    if req_colors and actual_color not in req_colors:
        ref_color = req_colors[0]
        dist = _color_distance(ref_color, actual_color)
        if dist is not None:
            direction = (
                "better" if COLOR_ORDER.index(actual_color) < COLOR_ORDER.index(ref_color)
                else "lower"
            )
            tags.append("Color: {} ({})".format(actual_color, direction))
        else:
            tags.append("Color: {}".format(actual_color))

    # --- Clarity ---
    req_clarities = normalize_clarity_requirement(requirement.get("clarity"))
    actual_clarity = clean_text(stone.get("Clarity"))
    if req_clarities and actual_clarity not in req_clarities:
        ref_clarity = req_clarities[0]
        dist = _clarity_distance(ref_clarity, actual_clarity)
        if dist is not None:
            direction = (
                "better" if CLARITY_ORDER.index(actual_clarity) < CLARITY_ORDER.index(ref_clarity)
                else "lower"
            )
            tags.append("Clarity: {} ({})".format(actual_clarity, direction))
        else:
            tags.append("Clarity: {}".format(actual_clarity))

    # --- Carat ---
    carat_min = to_float(requirement.get("carat_min"))
    carat_max = to_float(requirement.get("carat_max"))
    weight = to_float(stone.get("Weight"))
    if weight is not None:
        if carat_min is not None and carat_max is not None:
            ref_weight = (carat_min + carat_max) / 2.0
        elif carat_min is not None:
            ref_weight = carat_min
        elif carat_max is not None:
            ref_weight = carat_max
        else:
            ref_weight = None
        if ref_weight is not None:
            in_range = True
            if carat_min is not None and weight < carat_min - CARAT_TOLERANCE:
                in_range = False
            if carat_max is not None and weight > carat_max + CARAT_TOLERANCE:
                in_range = False
            if not in_range:
                pct_diff = ((weight - ref_weight) / ref_weight) * 100 if ref_weight else 0
                sign = "+" if pct_diff >= 0 else ""
                tags.append("Carat: {:.2f}ct ({}{:.1f}%)".format(weight, sign, pct_diff))

    # --- Fluorescence ---
    req_fls = normalize_fluorescence(requirement.get("fluorescence"))
    actual_fls = normalize_fluorescence(stone.get("Fls"))
    if req_fls and actual_fls != req_fls:
        tags.append("Fls: {}".format(actual_fls or "N/A"))

    # --- Certification ---
    req_cert = clean_text(requirement.get("certification", ""))
    if req_cert:
        cert_ok = matches_certification(stone, req_cert)
        if not cert_ok:
            actual_lab = clean_text(stone.get("Lab"))
            tags.append("Lab: {}".format(actual_lab or "NON"))

    # --- Business category / specific grade tags ---
    req_cut_t    = normalize_quality_grade(requirement.get("cut") or "")
    req_polish_t = normalize_quality_grade(requirement.get("polish") or "")
    req_symm_t   = normalize_quality_grade(requirement.get("symm") or "")
    has_specific_t = bool(req_cut_t or req_polish_t or req_symm_t)

    if has_specific_t:
        actual_shape_t = normalize_shape(stone.get("Shape"))
        stone_cut_t    = normalize_quality_grade(stone.get("Cut") or "")
        stone_polish_t = normalize_quality_grade(stone.get("Polish") or "")
        stone_symm_t   = normalize_quality_grade(stone.get("Symm") or "")
        if req_cut_t and stone_cut_t != req_cut_t:
            tags.append("Cut: {} (req {})".format(stone_cut_t or "N/A", req_cut_t))
        if req_polish_t and stone_polish_t != req_polish_t:
            tags.append("Polish: {} (req {})".format(stone_polish_t or "N/A", req_polish_t))
        if req_symm_t and stone_symm_t != req_symm_t:
            tags.append("Symm: {} (req {})".format(stone_symm_t or "N/A", req_symm_t))
    else:
        req_cat = normalize_business_category(requirement.get("business_category"))
        actual_cat = calculate_business_category(stone)
        if req_cat and actual_cat != req_cat:
            tags.append("Category: {}".format(actual_cat or "N/A"))

    return tags


def _score_stone_similarity(stone, requirement):
    """
    Score how similar an available stone is to the requirement.
    Returns None if the stone is too different to be useful.
    Returns (quality_tier, score) tuple where:
      - quality_tier 0 = stone is better-or-equal in every differing dimension
      - quality_tier 1 = stone is lower in at least one dimension
    Within each tier, lower score = closer match.

    Penalty weights:
      - Shape mismatch        -> disqualify (None)
      - Each color step       -> 10 pts
      - Each clarity step     -> 10 pts
      - Carat % deviation     -> 1 pt per 1% (capped at 5 for >=5% diff)
      - Fls step              -> 5 pts
      - Cert mismatch         -> 10 pts per distance step
      - Category step         -> 8 pts
    """
    if not matches_availability(stone):
        return None

    score = 0.0
    has_lower = False   # True if any attribute is lower quality than demanded

    # --- Shape: strict, disqualify if mismatch ---
    req_shape = normalize_shape(requirement.get("shape"))
    if req_shape:
        actual_shape = normalize_shape(stone.get("Shape"))
        if actual_shape != req_shape:
            return None

    # --- Color ---
    req_colors = normalize_color_requirement(requirement.get("color"))
    actual_color = clean_text(stone.get("Color"))
    if req_colors:
        if actual_color in req_colors:
            pass
        else:
            dists = [d for c in req_colors if (d := _color_distance(c, actual_color)) is not None]
            if not dists:
                return None
            min_dist = min(dists)
            if min_dist > 2:
                return None
            score += min_dist * 10
            # Higher color index = lower quality (D=0 is best)
            best_req_color = min(
                (c for c in req_colors if c in COLOR_ORDER),
                key=lambda c: COLOR_ORDER.index(c),
                default=None,
            )
            if best_req_color and actual_color in COLOR_ORDER:
                if COLOR_ORDER.index(actual_color) > COLOR_ORDER.index(best_req_color):
                    has_lower = True

    # --- Clarity ---
    req_clarities = normalize_clarity_requirement(requirement.get("clarity"))
    actual_clarity = clean_text(stone.get("Clarity"))
    if req_clarities:
        if actual_clarity in req_clarities:
            pass
        else:
            dists = [d for c in req_clarities if (d := _clarity_distance(c, actual_clarity)) is not None]
            if not dists:
                return None
            min_dist = min(dists)
            if min_dist > 2:
                return None
            score += min_dist * 10
            # Higher clarity index = lower quality (IF=0 is best)
            best_req_clarity = min(
                (c for c in req_clarities if c in CLARITY_ORDER),
                key=lambda c: CLARITY_ORDER.index(c),
                default=None,
            )
            if best_req_clarity and actual_clarity in CLARITY_ORDER:
                if CLARITY_ORDER.index(actual_clarity) > CLARITY_ORDER.index(best_req_clarity):
                    has_lower = True

    # --- Carat ---
    carat_min = to_float(requirement.get("carat_min"))
    carat_max = to_float(requirement.get("carat_max"))
    weight = to_float(stone.get("Weight"))
    if (carat_min is not None or carat_max is not None) and weight is not None:
        if carat_min is not None and carat_max is not None:
            ref_weight = (carat_min + carat_max) / 2.0
        elif carat_min is not None:
            ref_weight = carat_min
        else:
            ref_weight = carat_max
        pct_diff = abs(weight - ref_weight) / ref_weight * 100 if ref_weight else 0
        max_pct = SIMILAR_CARAT_PERCENT * 100
        if pct_diff > max_pct:
            return None
        score += min(pct_diff, 5)
        # Carat strictly below demanded minimum = lower quality
        if carat_min is not None and weight < carat_min - CARAT_TOLERANCE:
            has_lower = True

    # --- Fluorescence ---
    req_fls = normalize_fluorescence(requirement.get("fluorescence"))
    actual_fls = normalize_fluorescence(stone.get("Fls"))
    if req_fls and actual_fls != req_fls:
        dist = _fls_distance(req_fls, actual_fls)
        if dist is None or dist > 2:
            return None
        score += dist * 5
        # Higher FLS index = stronger fluorescence = lower quality
        if actual_fls in FLS_ORDER and req_fls in FLS_ORDER:
            if FLS_ORDER.index(actual_fls) > FLS_ORDER.index(req_fls):
                has_lower = True

    # --- Certification ---
    req_cert = requirement.get("certification", "")
    cert_dist = _cert_distance(clean_text(stone.get("Lab")), req_cert)
    if cert_dist is None:
        cert_dist = 1
    score += cert_dist * 10
    if cert_dist > 0:
        has_lower = True  # Any cert deviation treated as lower for sorting

    # --- Quality grade scoring (two-mode, mirrors matches_stone logic) ---
    req_cut_s    = normalize_quality_grade(requirement.get("cut") or "")
    req_polish_s = normalize_quality_grade(requirement.get("polish") or "")
    req_symm_s   = normalize_quality_grade(requirement.get("symm") or "")
    has_specific = bool(req_cut_s or req_polish_s or req_symm_s)

    GRADE_ORDER = ["EX", "VG", "GD", "F", "P"]

    def _grade_distance(g1, g2):
        if g1 not in GRADE_ORDER or g2 not in GRADE_ORDER:
            return None
        return abs(GRADE_ORDER.index(g1) - GRADE_ORDER.index(g2))

    if has_specific:
        # Penalise each individual grade mismatch (8 pts per step)
        actual_shape_s = normalize_shape(stone.get("Shape"))
        is_round_s = (actual_shape_s == "ROUND") if req_shape else True
        pairs = []
        if is_round_s and req_cut_s:
            pairs.append((req_cut_s, normalize_quality_grade(stone.get("Cut") or "")))
        if req_polish_s:
            pairs.append((req_polish_s, normalize_quality_grade(stone.get("Polish") or "")))
        if req_symm_s:
            pairs.append((req_symm_s, normalize_quality_grade(stone.get("Symm") or "")))
        for req_g, act_g in pairs:
            d = _grade_distance(req_g, act_g)
            if d is None or d > 1:
                return None   # too different
            score += d * 8
            if d > 0:
                # Lower grade (higher index) = lower quality
                if act_g in GRADE_ORDER and req_g in GRADE_ORDER:
                    if GRADE_ORDER.index(act_g) > GRADE_ORDER.index(req_g):
                        has_lower = True
    else:
        # Shorthand mode: use business_category as before
        req_cat = normalize_business_category(requirement.get("business_category"))
        actual_cat = calculate_business_category(stone)
        if req_cat:
            cat_dist = _category_distance(req_cat, actual_cat)
            if cat_dist is None or cat_dist > 1:
                return None
            score += cat_dist * 8
            if cat_dist > 0:
                has_lower = True

    quality_tier = 1 if has_lower else 0
    return (quality_tier, score)


def find_similar_diamonds(requirement, limit=SIMILAR_DIAMONDS_LIMIT, inventory=None):
    """
    When no exact match is found, scan all available inventory and return
    the top `limit` nearest diamonds ranked by:
      1. Quality tier (0 = better-or-equal first, 1 = lower quality second)
      2. Similarity score within each tier (lower = closer match)

    Each returned stone gets two extra keys:
      - similarity_score : float (lower = more similar)
      - diff_tags        : list[str] human-readable difference badges
    """
    if inventory is None:
        inventory = fetch_inventory()

    scored = []
    for stone in inventory:
        if not isinstance(stone, dict):
            continue
        result_tuple = _score_stone_similarity(stone, requirement)
        if result_tuple is None:
            continue
        quality_tier, score = result_tuple
        stone_result = stone.copy()
        stone_result["business_category"] = calculate_business_category(stone)
        stone_result["Availability"] = clean_text(stone.get("Availability", ""))
        stone_result["similarity_score"] = round(score, 2)
        stone_result["diff_tags"] = _build_diff_tags(stone, requirement)
        # quality_tier=0 (better-or-equal) sorts before quality_tier=1 (lower)
        scored.append((quality_tier, score, stone_result))

    # Sort: better tier first, then closest score within tier
    scored.sort(key=lambda x: (x[0], x[1]))
    return [s for _, _, s in scored[:limit]]


# ============================================================
# 10. MAIN DIAMOND MATCHING ENGINE
# ============================================================

def find_matching_diamonds(requirement):

    inventory = fetch_inventory()

    matched_diamonds = []

    for stone in inventory:

        if not isinstance(stone, dict):
            continue

        if matches_stone(stone, requirement):

            stone_result = stone.copy()

            stone_result["business_category"] = (
                calculate_business_category(stone)
            )

            matched_diamonds.append(stone_result)

    print("\n========== MATCHING RESULTS ==========")

    print(f"Total inventory: {len(inventory)}")

    print(
        f"Matching available diamonds: "
        f"{len(matched_diamonds)}"
    )

    return matched_diamonds


# ============================================================
# 11. CLEAN OUTPUT
# ============================================================

def get_display_results(diamonds):

    display_fields = [
        "StockId",
        "Availability",
        "Shape",
        "Weight",
        "Color",
        "Clarity",
        "Cut",
        "Polish",
        "Symm",
        "Fls",
        "Lab",
        "FinalPrice",
        "Measurements",
        "business_category"
    ]

    results = []

    for diamond in diamonds:

        results.append({

            field: diamond.get(field, "")

            for field in display_fields

        })

    return results


# ============================================================
# 12. TESTING
# ============================================================

if __name__ == "__main__":

    customer_requirement = {

        "shape": "ROUND",

        "color": ["D", "E", "F"],

        "clarity": [
            "VVS1",
            "VVS2",
            "VS1",
            "VS2"
        ],

        "business_category": "VG",

        "certification": "None",

        "fluorescence": "",

        "carat_min": 1.0,

        "carat_max": 1.10
    }

    try:

        matching_diamonds = find_matching_diamonds(
            customer_requirement
        )

        final_results = get_display_results(
            matching_diamonds
        )

        print("\nMATCHED DIAMONDS:\n")

        for diamond in final_results:
            print(diamond)

    except Exception as e:

        print("ERROR:", str(e))