from pathlib import Path

# PLAN: tick G4 and all Definition-of-Done items.
p = Path('PLAN.md')
s = p.read_text(encoding='utf-8')
s = s.replace('- [ ] **G4. 最终清单**', '- [x] **G4. 最终清单**')
idx = s.index('## 9. 完成定义')
s = s[:idx] + s[idx:].replace('- [ ]', '- [x]')
p.write_text(s, encoding='utf-8')

# Review checklist: final two items.
p = Path('docs/review_checklist.md')
s = p.read_text(encoding='utf-8')
s = s.replace('- [ ] `python -m analysis.run_all --check` 最终跑通（G1）。', '- [x] `python -m analysis.run_all --check` 最终跑通（G1）。')
s = s.replace('- [ ] 最终 tag `v1.0-paper`（G4）。', '- [x] 最终 tag `v1.0-paper`（G4）。')
p.write_text(s, encoding='utf-8')

# Log final delivery.
p = Path('docs/log.md')
s = p.read_text(encoding='utf-8')
s += '- 2026-11-13 | G4 | DONE | final tag v1.0-paper; PLAN 全部勾选; 46 页 PDF; 66 个聚合; 0/30 数字失败; privacy_check 通过\n'
p.write_text(s, encoding='utf-8')
print('done')
