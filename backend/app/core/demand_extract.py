
import re
from typing import Optional

from pydantic import BaseModel, Field, field_validator
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import PydanticOutputParser

from dotenv import load_dotenv
load_dotenv()
# ============================================================
# 1. PYDANTIC OUTPUT SCHEMA
# ============================================================

class GemsIdentifySchema(BaseModel):

    shape: str = Field(default="", description="Diamond shape")
    color: str | list[str] = Field(
    default="",
    description="Single diamond color or list of colors when a color range is requested"
)
    clarity: str | list[str] = Field(
    default="",
    description="Single clarity grade or list of clarity grades when a range is requested"
)
    business_category: str = Field(default="", description="Diamond business_category or business category")

    cut: str = Field(
        default="",
        description=(
            "Individual cut grade (EX/VG/GD/G) — set ONLY when the user explicitly "
            "states a specific cut grade for a ROUND diamond as part of a combined "
            "cut+polish+symm specification (e.g. 'EX VG VG' or 'EX EX VG'). "
            "Leave empty when the user gives only a shorthand like 'EX', '3EX', or 'VG'."
        )
    )

    polish: str = Field(
        default="",
        description=(
            "Individual polish grade (EX/VG/GD/G) — set ONLY when the user explicitly "
            "states specific individual grades (e.g. 'EX VG VG' for round, or 'VG EX' for fancy). "
            "Leave empty for shorthand inputs like 'EX', '3EX', '2EX', or 'VG'."
        )
    )

    symm: str = Field(
        default="",
        description=(
            "Individual symmetry grade (EX/VG/GD/G) — set ONLY when the user explicitly "
            "states specific individual grades (e.g. 'EX VG VG' for round, or 'VG EX' for fancy). "
            "Leave empty for shorthand inputs like 'EX', '3EX', '2EX', or 'VG'."
        )
    )

    certification: str = Field(
        default="",
        description="Allowed values: None, IGI, Certi, or empty string"
    )

    fluorescence: str = Field(
        default="",
        description="Allowed values: NON, SLT, STG, or empty string"
    )

    carat_min: Optional[float] = Field(
        default=None,
        description="Minimum carat requirement"
    )

    carat_max: Optional[float] = Field(
        default=None,
        description="Maximum carat requirement"
    )

    @field_validator("shape", mode="before")
    @classmethod
    def normalize_shape_field(cls, value):
        if value is None:
            return ""
        return str(value)

    @field_validator("color", mode="before")
    @classmethod
    def normalize_color_none(cls, value):
        if value is None:
            return ""
        return value

    @field_validator("clarity", mode="before")
    @classmethod
    def normalize_clarity_field(cls, value):
        if value is None:
            return ""
        group_map = {
            "VVS": ["VVS1", "VVS2"],
            "VS":  ["VS1", "VS2"],
            "SI":  ["SI1", "SI2"],
        }
        if isinstance(value, str):
            upper = value.strip().upper()
            if upper in group_map:
                return group_map[upper]
            return value
        if isinstance(value, list):
            expanded = []
            for item in value:
                item_upper = str(item).strip().upper()
                if item_upper in group_map:
                    expanded.extend(group_map[item_upper])
                elif item_upper:
                    expanded.append(item_upper)
            return list(dict.fromkeys(expanded)) if expanded else ""
        return value

    @field_validator("business_category", mode="before")
    @classmethod
    def normalize_business_category(cls, value):
        if value is None:
            return ""
        value = str(value).strip().upper()

        if value in ["EX", "X", "3EX", "EX EX EX"]:
            return "3EX"

        if value == "VG":
            return "VG"

        return value

    @field_validator("cut", "polish", "symm", mode="before")
    @classmethod
    def normalize_quality_grade_field(cls, value):
        if value is None:
            return ""
        value = str(value).strip().upper()
        mapping = {
            "EX": "EX",
            "EXCELLENT": "EX",
            "X": "EX",
            "VG": "VG",
            "VERY GOOD": "VG",
            "GD": "GD",
            "GOOD": "GD",
            "G": "GD",
        }
        return mapping.get(value, value)

    @field_validator("fluorescence", mode="before")
    @classmethod
    def normalize_fluorescence(cls, value):
        if value is None:
            return ""
        value = str(value).strip().upper()

        mapping = {
            "NON": "NON",
            "NONE": "NON",
            "NO": "NON",
            "SLIGHT": "SLT",
            "SLT": "SLT",
            "STRONG": "STG",
            "STG": "STG"
        }

        return mapping.get(value, "")

    @field_validator("certification", mode="before")
    @classmethod
    def normalize_certification(cls, value):
        if value is None:
            return ""
        value = str(value).strip().upper()

        mapping = {
            "NON": "None",
            "NONE": "None",
            "NON CERTI": "None",
            "NON-CERTI": "None",
            "NON CERTIFIED": "None",
            "NON-CERTIFIED": "None",
            "WITHOUT CERTIFICATE": "None",
            "CERTI": "Certi",
            "CERTIFIED": "Certi",
            "IGI": "IGI"
        }

        return mapping.get(value, "")


# ============================================================
# 2. GROQ MODEL
# ============================================================

llm = ChatGroq(
    model="openai/gpt-oss-120b",
    temperature=0,
    max_retries=2
)

parser = PydanticOutputParser(
    pydantic_object=GemsIdentifySchema
)


# ============================================================
# 3. EXTRACTION PROMPT
# ============================================================

system_prompt = """
You are an expert diamond requirement extraction assistant
working for Mira Gems, a lab-grown diamond company.

Your task is to extract diamond requirements accurately
from informal customer messages.

Extract ONLY information explicitly mentioned by the customer.

FIELDS:

1. SHAPE
Extract the requested diamond shape.
Examples: ROUND, OVAL, PEAR, RADIANT, EMERALD,
PRINCESS, CUSHION, MARQUISE, HEART.


2. COLOR
Extract the requested diamond color accurately.

Allowed individual colors:
D, E, F, G, H, I, J, K, L, M.

Customers may mention a single color or multiple colors
as a range or group.

COLOR RANGE INTERPRETATION:

- D-F = ["D", "E", "F"]
- D/E/F = ["D", "E", "F"]
- D to F = ["D", "E", "F"]
- DEF = ["D", "E", "F"]

- E-G = ["E", "F", "G"]
- E/F/G = ["E", "F", "G"]

- F-H = ["F", "G", "H"]
- G-I = ["G", "H", "I"]

OUTPUT RULES:

1. Single color:
   D -> "D"

2. Multiple colors:
   D-F -> ["D", "E", "F"]

3. If color is not mentioned:
   Return ""

IMPORTANT:
- Include every color within the requested range.
- Do not skip intermediate colors.
- Do not confuse clarity grades with colors.
- Do not invent color requirements.


3. CLARITY

Extract the diamond clarity requirement accurately.

Allowed individual clarity grades:
IF, VVS1, VVS2, VS1, VS2, SI1, SI2.

IMPORTANT: Customers may mention clarity as an individual
grade or as a range/group of clarity grades.

When a clarity range is mentioned, return ALL individual
grades included in that range as a LIST.

CLARITY GROUP SHORTHANDS:

- VVS = ["VVS1", "VVS2"]
- VS  = ["VS1", "VS2"]
- SI  = ["SI1", "SI2"]

CLARITY RANGE INTERPRETATION:

- VVS-VS = ["VVS1", "VVS2", "VS1", "VS2"]
- VVS/VS = ["VVS1", "VVS2", "VS1", "VS2"]
- VVS VS = ["VVS1", "VVS2", "VS1", "VS2"]
- VVS to VS = ["VVS1", "VVS2", "VS1", "VS2"]

- VS-SI = ["VS1", "VS2", "SI1", "SI2"]
- VS/SI = ["VS1", "VS2", "SI1", "SI2"]
- VS SI = ["VS1", "VS2", "SI1", "SI2"]

OUTPUT RULES:

1. If a single clarity is mentioned, return a STRING.
   Example: VVS2 -> "VVS2"

2. If multiple clarity grades or a range is mentioned,
   return a LIST.
   Example: VVS-VS ->
   ["VVS1", "VVS2", "VS1", "VS2"]

3. If clarity is not mentioned, return "".

Never return an empty clarity when a recognized
clarity range or individual grade is present.

Never invent clarity requirements.


4. BUSINESS CATEGORY AND SPECIFIC GRADES

Mira Gems uses TWO modes for quality matching:
  MODE A - Shorthand: user gives a single word like "EX", "3EX", "VG", "VG+".
  MODE B - Specific:  user gives individual grades like "EX VG VG" or "VG EX".

Always extract BOTH business_category AND the specific cut/polish/symm fields.
Do NOT skip or omit clarity, color, shape, or carat when extracting cut/polish/symm.

-----------------------------------------
ROUND DIAMONDS (shape = ROUND)
Quality = Cut + Polish + Symmetry
-----------------------------------------

MODE A - Shorthand (leave cut/polish/symm empty):
  Input          business_category   cut   polish   symm
  "EX"           EX                  ""    ""       ""
  "3EX"          EX                  ""    ""       ""
  "EX EX EX"     EX                  ""    ""       ""
  "X"            EX                  ""    ""       ""
  "ID"           EX                  ""    ""       ""
  "VG"           VG                  ""    ""       ""
  "VG+"          VG                  ""    ""       ""

MODE B - Specific grades (fill cut, polish, symm):
  Input          business_category   cut   polish   symm
  "EX VG VG"     VG                  EX    VG       VG
  "EX EX VG"     VG                  EX    EX       VG
  "VG EX EX"     VG                  VG    EX       EX
  "VG VG EX"     VG                  VG    VG       EX
  "VG VG VG"     VG                  VG    VG       VG
  "GD GD EX"     VG                  GD    GD       EX

RULE: Three space-separated grade tokens in order Cut Polish Symm -> MODE B.

-----------------------------------------
FANCY DIAMONDS (non-ROUND shape)
Quality = Polish + Symmetry only (no Cut)
-----------------------------------------

MODE A - Shorthand (leave cut/polish/symm empty):
  Input          business_category   cut   polish   symm
  "EX"           EX                  ""    ""       ""
  "2EX"          EX                  ""    ""       ""
  "EX EX"        EX                  ""    ""       ""
  "VG"           VG                  ""    ""       ""
  "VG+"          VG                  ""    ""       ""

MODE B - Specific grades (fill polish and symm, leave cut empty):
  Input          business_category   cut   polish   symm
  "EX VG"        VG                  ""    EX       VG
  "VG EX"        VG                  ""    VG       EX
  "VG VG"        VG                  ""    VG       VG

RULE: Two space-separated grade tokens for a fancy shape -> MODE B for polish/symm.

-----------------------------------------
SHAPE NOT MENTIONED (apply best-guess)
-----------------------------------------

  "EX" / "3EX" / "X"       -> business_category=EX, cut="" polish="" symm=""
  "VG" / "VG+"              -> business_category=VG, cut="" polish="" symm=""
  Three tokens "X Y Z"      -> business_category=VG (or EX if all EX), cut=X polish=Y symm=Z
  Two tokens "X Y"          -> business_category=VG (or EX if all EX), cut="" polish=X symm=Y

IMPORTANT:
- "EX EX EX" and "3EX" are always shorthand (Mode A) -> leave cut/polish/symm empty.
- "EX EX" for a fancy shape is shorthand (Mode A) -> leave cut/polish/symm empty.
- Only use Mode B when the user gives explicitly mixed or non-identical grade tokens.
- Do not confuse business category with diamond shape.

Return "EX" or "VG" or "" for business_category.
Return "EX", "VG", "GD", or "" for each of cut / polish / symm.


5. FLUORESCENCE

Mira Gems uses EXACTLY THREE fluorescence values:

- NON = Non fluorescence
- SLT = Slight fluorescence
- STG = Strong fluorescence

Recognize:
- Non, no fluorescence = NON
- Slight, SLT = SLT
- Strong, STG = STG

IMPORTANT:
Fluorescence and certification are two COMPLETELY
INDEPENDENT fields.

6. CERTIFICATION

Allowed values:
- "None" = Non-certified
- "IGI" = IGI certified
- "Certi" = Certified
- "" = Not mentioned

Recognize:
- IGI = IGI
- Certified = Certi
- Certi = Certi
- Non-certified = None
- Without certificate = None

CRITICAL MIRA GEMS TERMINOLOGY:

Interpret "Non", "Certi", and "Non certi" carefully:

- "non certi", "non-certi", "non certified", "non-certified", "without certificate"
  ALWAYS mean certification = "None" (non-certified), whether standalone or inside a full demand.
- Only when "non" appears separately OUTSIDE "non certi" (e.g. "non certi non",
  "non non-certi", "non ... certi", or "non IGI") does "non" mean fluorescence = "NON".

Example 1:
Input: rnd 2-2.20 EX vvs-vs non certi

Output:
fluorescence = ""
certification = None

Here, "non certi" means non-certified (None). No separate fluorescence was requested.

Example 2:
Input: rnd 2-2.20 EX vvs-vs non certi non

Output:
fluorescence = NON
certification = None

Here, "non certi" means non-certified (None) and the separate "non" means fluorescence = NON.

Example 3:
Input: D VS1 Non IGI

Output:
fluorescence = NON
certification = IGI

Example 4:
Input: D VS1 SLT Certi

Output:
fluorescence = SLT
certification = Certi

Example 5:
Input: D VS1 STG Non certi

Output:
fluorescence = STG
certification = None

In Example 5, the explicit STG is fluorescence
and Non certi means non-certified.

Example 6:
Input: rnd 2-2.20 EX vvs-vs non non-certi

Output:
fluorescence = NON
certification = None

In Example 6, standalone "non" is fluorescence (NON)
and "non-certi" means non-certified (None).

Example 7:
Input: Non certi

Output:
fluorescence = ""
certification = None

Never automatically interpret "non certi" as fluorescence=NON + certification=Certi.

Never automatically interpret every occurrence of
"Certi" as fluorescence.

7. CARAT REQUIREMENT

Extract both individual carat values and ranges.

Examples:

- 2.6ct -> carat_min = 2.6, carat_max = 2.6
- 2.60 carat -> 2.6, 2.6
- 1-1.10ct -> 1.0, 1.10
- 1.00-1.50ct -> 1.0, 1.5
- 1 to 1.50 carat -> 1.0, 1.5
- 3ct above -> 3.0, null
- Below 5ct -> null, 5.0

If no carat is mentioned:
carat_min = null
carat_max = null

IMPORTANT - HYPHEN AS A FIELD SEPARATOR:

In Mira Gems requirements, a hyphen '-' is very commonly
used as a visual separator between specification fields
(shape, carat, color, clarity, cut/polish/symm, lab),
NOT as a range indicator between two fields.

Example:
  MARQUISE 14.07 E VS1 - EX EX IGI

Here the '-' separates the quality parameters from the
grade block; it does NOT indicate a carat range.
Extract: shape=MARQUISE, carat_min=14.07, carat_max=14.07,
color=E, clarity=VS1, business_category=EX (fancy: EX EX),
certification=IGI.

Only treat a hyphen as a range indicator when BOTH sides
are clearly the same field type
(e.g. '1.00-1.50ct' for carat, 'D-F' for color).

Do not confuse other numerical values with carat.
A bare number without a 'ct/carat' unit is a carat weight
only when it clearly represents the carat position in the
requirement and no other interpretation fits.

8. MISSING INFORMATION

If a field is not mentioned:
- String fields = ""
- Carat fields = null

Do not guess missing requirements.

Return ONLY valid structured output.

{format_instructions}
"""


prompt = PromptTemplate(
    template=system_prompt,
    input_variables=[],
    partial_variables={
        "format_instructions": parser.get_format_instructions()
    }
)


# ============================================================
# 4. CREATE EXTRACTION CHAIN
# ============================================================

chain = prompt | llm | parser


# ============================================================
# 5. CARAT EXTRACTION FALLBACK
# ============================================================

def extract_carat(text):

    text = text.lower().replace(",", "")

    # Range: 1-1.10, 1.00 to 1.50ct
    range_pattern = (
        r"(\d+(?:\.\d+)?)\s*"
        r"(?:-|to|–|—)\s*"
        r"(\d+(?:\.\d+)?)\s*"
        r"(?:ct|cts|carats?)?"
    )

    range_match = re.search(range_pattern, text)

    if range_match:
        minimum = float(range_match.group(1))
        maximum = float(range_match.group(2))

        # Sanity guard: a valid range always has min <= max.
        # Discard false-positive matches (e.g. a decimal split by
        # the alternation into two separate numbers).
        if minimum <= maximum:
            return minimum, maximum
        # Fall through to other patterns.

    # Above / more than
    above_pattern = (
        r"(\d+(?:\.\d+)?)\s*"
        r"(?:ct|cts|carats?)?\s*"
        r"(?:above|upwards|and above|plus|\+)"
    )

    above_match = re.search(above_pattern, text)

    if above_match:
        return float(above_match.group(1)), None

    # Below / less than
    below_pattern = (
        r"(?:below|under|less than)\s*"
        r"(\d+(?:\.\d+)?)\s*"
        r"(?:ct|cts|carats?)?"
    )

    below_match = re.search(below_pattern, text)

    if below_match:
        return None, float(below_match.group(1))

    # Single carat: 2.6ct, 2.60 carat
    single_pattern = (
        r"(\d+(?:\.\d+)?)\s*"
        r"(?:ct|cts|carats?)\b"
    )

    single_match = re.search(single_pattern, text)

    if single_match:
        carat = float(single_match.group(1))
        return carat, carat

    return None, None



# ============================================================
# 6. MIRA GEMS CERTIFICATION / FLUORESCENCE CORRECTION
# ============================================================

def correct_fluorescence_certification(text, result):

    lower = text.lower()
    normalized = re.sub(r"[^a-z0-9]+", " ", lower).strip()

    # Standalone "Non certi" / "non-certi" / "non certified" / "without certificate"
    if re.fullmatch(r"(?:non certi(?:fied)?|without certificate)", normalized):
        result["fluorescence"] = ""
        result["certification"] = "None"
        return result

    # Any "non certi", "non-certi", "non certified", "non-certified", or
    # "without certificate" means non-certified (certification="None").
    # Fluorescence is resolved strictly from whatever remains outside that phrase:
    #   e.g. "rnd 2-2.20 EX vvs-vs non certi"     -> cert="None", fls=""
    #        "rnd 2-2.20 EX vvs-vs non certi non" -> cert="None", fls="NON"
    #        "rnd 2-2.20 EX vvs-vs non non-certi" -> cert="None", fls="NON"
    #        "D VS1 STG Non certi"                -> cert="None", fls="STG"
    non_certi_pattern = (
        r"\bnon[\s-]+certi(?:fied)?\b|\bwithout\s+certificate\b"
    )
    if re.search(non_certi_pattern, lower):
        result["certification"] = "None"
        remaining = re.sub(non_certi_pattern, " ", lower)
        remaining_norm = re.sub(r"[^a-z0-9]+", " ", remaining).strip()
        if re.search(r"\b(?:stg|strong)\b", remaining_norm):
            result["fluorescence"] = "STG"
        elif re.search(r"\b(?:slt|slight)\b", remaining_norm):
            result["fluorescence"] = "SLT"
        elif re.search(r"\b(?:non|no fls|no fluorescence)\b", remaining_norm):
            result["fluorescence"] = "NON"
        elif result.get("fluorescence") == "NON":
            # Clear false "NON" if LLM inferred it only from "non certi"
            result["fluorescence"] = ""
        return result

    return result


# ============================================================
# 7. MAIN EXTRACTION FUNCTION
# ============================================================

def get_demand(user_input: str):
    """Extract structured diamond requirements from a customer message."""
    return extract_diamond_requirement(user_input)


# ============================================================
# 8. USER INPUT EXTRACTION CHAIN
# ============================================================

input_prompt = PromptTemplate(
    template=system_prompt + "\n\nCUSTOMER REQUIREMENT:\n{user_input}",
    input_variables=["user_input"],
    partial_variables={
        "format_instructions": parser.get_format_instructions()
    }
)

extraction_chain = input_prompt | llm | parser


CLARITY_FALLBACK_ORDER = ["IF", "VVS1", "VVS2", "VS1", "VS2", "SI1", "SI2"]
CLARITY_FALLBACK_GROUPS = {
    "VVS": ["VVS1", "VVS2"],
    "VS":  ["VS1", "VS2"],
    "SI":  ["SI1", "SI2"],
}


def extract_clarity_fallback(text: str):
    """
    Deterministic fallback for unambiguous clarity grades/ranges
    used only when LLM extraction returns an empty clarity field.
    Avoids standalone ambiguous English words like 'if', 'vs', 'si'.
    """
    upper = text.upper()

    # Explicit clarity range: VVS-VS, VVS/VS, VVS to VS, VS-SI, VVS1-VS1, IF-VVS, etc.
    range_match = re.search(
        r"\b(IF|VVS[12]?|VS[12]?|SI[12]?)\s*(?:-|/|TO)\s*(IF|VVS[12]?|VS[12]?|SI[12]?)\b",
        upper
    )
    if range_match:
        start_tok = range_match.group(1)
        end_tok = range_match.group(2)
        group_start = {"VVS": "VVS1", "VS": "VS1", "SI": "SI1"}
        group_end = {"VVS": "VVS2", "VS": "VS2", "SI": "SI2"}
        s = group_start.get(start_tok, start_tok)
        e = group_end.get(end_tok, end_tok)
        if s in CLARITY_FALLBACK_ORDER and e in CLARITY_FALLBACK_ORDER:
            si = CLARITY_FALLBACK_ORDER.index(s)
            ei = CLARITY_FALLBACK_ORDER.index(e)
            if si <= ei:
                return CLARITY_FALLBACK_ORDER[si:ei + 1]

    # Unambiguous clarity tokens (vvs, vvs1, vvs2, vs1, vs2, si1, si2)
    tokens = re.findall(r"\b(VVS1|VVS2|VVS|VS1|VS2|SI1|SI2)\b", upper)
    if tokens:
        expanded = []
        for tok in tokens:
            if tok in CLARITY_FALLBACK_GROUPS:
                expanded.extend(CLARITY_FALLBACK_GROUPS[tok])
            else:
                expanded.append(tok)
        deduped = list(dict.fromkeys(expanded))
        return deduped[0] if len(deduped) == 1 else deduped

    return ""


def extract_diamond_requirement(user_input: str):

    try:

        # Step 1: LLM extraction
        response = extraction_chain.invoke({
            "user_input": user_input
        })

        result = response.model_dump()

        # Step 2: Validate & possibly override LLM carat with deterministic regex.
        # The deterministic extractor is authoritative when it finds a match;
        # otherwise the LLM value is kept but sanitised below.
        carat_min, carat_max = extract_carat(user_input)

        if carat_min is not None or carat_max is not None:
            # Deterministic result takes precedence (already sanity-checked).
            result["carat_min"] = carat_min
            result["carat_max"] = carat_max
        else:
            # Keep LLM carat, but apply a sanity check:
            # if min > max (inverted range), discard both to avoid zero-match.
            llm_min = result.get("carat_min")
            llm_max = result.get("carat_max")
            if (
                llm_min is not None
                and llm_max is not None
                and llm_min > llm_max
            ):
                result["carat_min"] = None
                result["carat_max"] = None
                print(
                    f"[demand_extract] WARNING: LLM returned inverted carat range "
                    f"({llm_min} > {llm_max}); discarding carat filter."
                )

        # Step 3: Correct Mira Gems terminology
        result = correct_fluorescence_certification(
            user_input,
            result
        )

        # Step 4: Clarity fallback if LLM left clarity empty despite clear tokens
        if not result.get("clarity"):
            fallback_clarity = extract_clarity_fallback(user_input)
            if fallback_clarity:
                result["clarity"] = fallback_clarity

        return result

    except Exception as e:

        print("Diamond Extraction Error:", str(e))
        return None


# ============================================================
# 9. TESTING
# ============================================================

if __name__ == "__main__":

    test_inputs = [

        "VS-SI D/E/G 3ct EX EX VG",

    ]

    for test in test_inputs:

        print("\n" + "=" * 60)
        print("INPUT:", test)

        result = extract_diamond_requirement(test)

        print("OUTPUT:")
        print(result)
