import re, sys

path = r"C:\Users\MIRA GEMS\Desktop\mira_gems\data_fetching\mira-companion\backend\app\core\demand_extract.py"
with open(path, "r", encoding="utf-8") as f:
    code = f.read()

namespace = {"re": re}
carat_code = re.search(r"(def extract_carat\(text\):.*?\n\n\n#)", code, re.DOTALL).group(1)
exec(carat_code, namespace)

corr_code = re.search(r"(def correct_fluorescence_certification\(text, result\):.*?\n\n\n#)", code, re.DOTALL).group(1)
exec(corr_code, namespace)

extract_carat = namespace["extract_carat"]
correct_fluorescence_certification = namespace["correct_fluorescence_certification"]

# Import parse_stone_ids from inventory_service.py
inv_service_path = r"C:\Users\MIRA GEMS\Desktop\mira_gems\data_fetching\mira-companion\backend\app\services\inventory_service.py"
with open(inv_service_path, "r", encoding="utf-8") as f:
    inv_code = f.read()

parse_ids_match = re.search(r"(def parse_stone_ids\(raw_input: str\) -> list\[str\]:.*?\n\n)(?=\ndef\s)", inv_code, re.DOTALL)
exec(parse_ids_match.group(1), namespace)
parse_stone_ids = namespace["parse_stone_ids"]

passed = 0
failed = 0

def check(label, got, expected):
    global passed, failed
    ok = (got == expected)
    if ok:
        passed += 1
        print(f"  [PASS]  {label}")
    else:
        failed += 1
        print(f"  [FAIL]  {label}")
        print(f"           got:      {got!r}")
        print(f"           expected: {expected!r}")

print("=== extract_carat (from backend/app/core/demand_extract.py) ===")
check("2.6ct exact",      extract_carat("2.6ct round"),     (2.6,  2.6))
check("1.00 to 1.10ct",   extract_carat("1.00 to 1.10ct"),  (1.0,  1.1))
check("1-1.10 dash",      extract_carat("1-1.10"),          (1.0,  1.1))
check("3ct above",        extract_carat("3ct above"),       (3.0,  None))
check("below 5ct",        extract_carat("below 5ct"),       (None, 5.0))
check("no carat at all",  extract_carat("D VS1 EX EX EX"),  (None, None))
check("1.00-1.50ct range",extract_carat("1.00-1.50ct"),     (1.0,  1.5))

print()
print("=== correct_fluorescence_certification ===")
def corr(text, init=None):
    r = dict(init) if init else {"fluorescence": "", "certification": ""}
    return correct_fluorescence_certification(text, r)

r = corr("non certi")
check("standalone non certi -> fluorescence empty", r["fluorescence"], "")
check("standalone non certi -> certification None", r["certification"], "None")

r = corr("rnd 2-2.20 EX vvs-vs non certi", {"fluorescence": "NON", "certification": "Certi"})
check("full req non certi -> fluorescence empty",  r["fluorescence"],  "")
check("full req non certi -> certification None", r["certification"], "None")

r = corr("rnd 2-2.20 EX vvs-vs non certi non", {"fluorescence": "NON", "certification": "Certi"})
check("non certi non -> fluorescence NON",   r["fluorescence"],  "NON")
check("non certi non -> certification None", r["certification"], "None")

r = corr("D VS1 EX EX EX", {"fluorescence": "SLT", "certification": "IGI"})
check("no pattern -> fluorescence unchanged SLT",  r["fluorescence"],  "SLT")
check("no pattern -> certification unchanged IGI", r["certification"], "IGI")

r = corr("D VS1 STG Non certi", {"fluorescence": "STG"})
check("STG Non certi -> fluorescence STG",  r["fluorescence"],  "STG")
check("STG Non certi -> certification None", r["certification"], "None")

r = corr("rnd 2-2.20 EX vvs-vs non non-certi", {"fluorescence": "NON", "certification": "Certi"})
check("non non-certi -> fluorescence NON",   r["fluorescence"],  "NON")
check("non non-certi -> certification None", r["certification"], "None")

r = corr("rnd 2-2.20 EX vvs-vs non non certi", {"fluorescence": "NON", "certification": "Certi"})
check("non non certi -> fluorescence NON",   r["fluorescence"],  "NON")
check("non non certi -> certification None", r["certification"], "None")

r = corr("rnd 2ct D VVS2 non-certi", {"fluorescence": "NON", "certification": "Certi"})
check("hyphen non-certi only -> fluorescence empty",  r["fluorescence"],  "")
check("hyphen non-certi only -> certification None",  r["certification"], "None")

print()
print("=== parse_stone_ids ===")
check("newline separated",  parse_stone_ids("B000216\nB000217\nB000218"), ["B000216","B000217","B000218"])
check("mixed separators",   parse_stone_ids("B001, B002; B003 B004"),     ["B001","B002","B003","B004"])
check("deduplication",      parse_stone_ids("B001 B001 B001"),            ["B001"])
check("empty input",        parse_stone_ids("   "),                       [])
check("comma+newline dup",  parse_stone_ids("B001,B001\nB002"),           ["B001","B002"])
check("semicolon+space",    parse_stone_ids("B001; B002 B003"),           ["B001","B002","B003"])

print()
print(f"========================================")
print(f"RESULT: {passed} passed, {failed} failed  (total {passed+failed})")
if failed > 0:
    sys.exit(1)
print("ALL BACKEND BUSINESS LOGIC TESTS 100% PASSED!")
