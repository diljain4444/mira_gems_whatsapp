import re

path = r"C:\Users\MIRA GEMS\Desktop\mira_gems\data_fetching\mira-companion\backend\app\core\demand_extract.py"
with open(path, "r", encoding="utf-8") as f:
    lines = f.readlines()

new_lines = []
i = 0
while i < len(lines):
    line = lines[i]
    # Check if this is the start of single_pattern
    if '    # Single carat: 2.6ct, 2.60 carat' in line:
        # Collect single_pattern block up to below_pattern return
        # Let's inspect: lines 442 to 478
        # We want: above_pattern, then below_pattern, then single_pattern
        block = lines[i:i+37]
        # Reconstruct in corrected order
        above_block = lines[i+12:i+24]
        below_block = lines[i+24:i+37]
        single_block = lines[i:i+12]
        new_lines.extend(above_block)
        new_lines.extend(below_block)
        new_lines.extend(single_block)
        i += 37
        continue
    elif '    if re.search(r"\\bnon[\\s-]+certi\\b", normalized):' in line:
        new_lines.append(line)
        new_lines.append('        if re.search(r"\\b(?:stg|slt|strong|slight)\\b", normalized) or result.get("fluorescence") in ["SLT", "STG"]:\n')
        new_lines.append('            result["certification"] = "None"\n')
        new_lines.append('        else:\n')
        new_lines.append('            result["fluorescence"] = "NON"\n')
        new_lines.append('            result["certification"] = "Certi"\n')
        i += 5  # skip the old result["fluorescence"] = "NON" and result["certification"] = "Certi"
        continue
    else:
        new_lines.append(line)
        i += 1

with open(path, "w", encoding="utf-8") as f:
    f.writelines(new_lines)

print("Updated successfully")
