from pathlib import Path

p = Path('PLAN.md')
s = p.read_text(encoding='utf-8')
out = []
for line in s.splitlines():
    if line.startswith('- [ ] **') and (
        line[8:9] in 'CDEF'
        or line.startswith('- [ ] **G1')
        or line.startswith('- [ ] **G2')
        or line.startswith('- [ ] **G3')
    ):
        line = line.replace('- [ ]', '- [x]', 1)
    out.append(line)
p.write_text('\n'.join(out) + '\n', encoding='utf-8')
print('done')
