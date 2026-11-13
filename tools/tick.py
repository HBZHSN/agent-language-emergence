import sys
from pathlib import Path

plan = Path('PLAN.md')
text = plan.read_text(encoding='utf-8')
if len(sys.argv) < 2:
    raise SystemExit('usage: python tools/tick.py "A1. ..."')
needle = '- [ ] **' + sys.argv[1] + '**'
if needle not in text:
    if '- [x] **' + sys.argv[1] + '**' in text:
        print('already checked')
        raise SystemExit(0)
    raise SystemExit('not found: ' + sys.argv[1])
text = text.replace(needle, '- [x] **' + sys.argv[1] + '**')
plan.write_text(text, encoding='utf-8')
print('checked:', sys.argv[1])
