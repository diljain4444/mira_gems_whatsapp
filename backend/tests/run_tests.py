import sys, os

backend = r'C:\Users\MIRA GEMS\Desktop\mira_gems\data_fetching\mira-companion\backend'
sys.path.insert(0, os.path.join(backend, 'app', 'core'))
sys.path.insert(0, os.path.join(backend, 'app', 'services'))

from demand_extract import extract_carat, correct_fluorescence_certification
from inventory_service import parse_stone_ids

passed = 0
failed = 0

def check(label, got, expected):
    global passed, failed
    ok = got == expected
    tag = 'PASS' if ok else 'FAIL'
    if ok: passed += 1
    else:
        failed += 1
        print(f'  [{tag}]  {label}')
        print(f'         got      : {got}')
        print(f'         expected : {expected}')
    if ok:
        print(f'  [{tag}]  {label}')

# ── extract_carat ─────────────────────────────────────────────────────────────
print('=== extract_carat ===')
check('2.6ct',            extract_carat('2.6ct round'),         (2.6, 2.6))
check('1.00 to 1.10ct',   extract_carat('1.00 to 1.10ct'),      (1.0, 1.1))
check('1-1.10',           extract_carat('1-1.10'),              (1.0, 1.1))
check('3ct above',        extract_carat('3ct above'),           (3.0, None))
check('below 5ct',        extract_carat('below 5ct'),           (None, 5.0))
check('no carat',         extract_carat('D VS1 EX EX EX'),      (None, None))

# ── correct_fluorescence_certification ───────────────────────────────────────
print()
print('=== correct_fluorescence_certification ===')

def corr(text, init=None):
    r = dict(init) if init else {'fluorescence': '', 'certification': ''}
    return correct_fluorescence_certification(text, r)

r1 = corr('non certi')
check('standalone non certi -> fls empty', r1['fluorescence'], '')
check('standalone non certi -> cert None', r1['certification'], 'None')

r2 = corr('rnd 2-2.20 EX vvs-vs non certi', {'fluorescence': 'NON', 'certification': 'Certi'})
check('full req non certi -> fls empty', r2['fluorescence'], '')
check('full req non certi -> cert None', r2['certification'], 'None')

r2b = corr('rnd 2-2.20 EX vvs-vs non certi non', {'fluorescence': 'NON', 'certification': 'Certi'})
check('non certi non -> fls NON',   r2b['fluorescence'], 'NON')
check('non certi non -> cert None', r2b['certification'], 'None')

r3 = corr('D VS1 EX EX EX', {'fluorescence': 'SLT', 'certification': 'IGI'})
check('no pattern -> fls unchanged SLT', r3['fluorescence'], 'SLT')
check('no pattern -> cert unchanged IGI', r3['certification'], 'IGI')

# ── parse_stone_ids ──────────────────────────────────────────────────────────
print()
print('=== parse_stone_ids ===')
check('newline separated', parse_stone_ids('B000216\nB000217\nB000218'), ['B000216','B000217','B000218'])
check('mixed separators',  parse_stone_ids('B001, B002; B003 B004'),     ['B001','B002','B003','B004'])
check('deduplication',     parse_stone_ids('B001 B001 B001'),            ['B001'])
check('empty input',       parse_stone_ids('   '),                       [])
check('comma+newline dup', parse_stone_ids('B001,B001\nB002'),           ['B001','B002'])

print()
print(f'Result: {passed} passed, {failed} failed out of {passed+failed} tests')
