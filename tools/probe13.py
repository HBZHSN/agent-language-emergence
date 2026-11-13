import json
from pathlib import Path
p=Path(r'C:\path\to\valuation\data\opencode\config.json')
b=p.read_bytes()
print('utf8 decode strict?')
try:
    s=b.decode('utf-8')
    print('utf8 ok', len(s))
except Exception as e:
    print('utf8 fail', e)
    s=b.decode('gbk')
    print('gbk ok', len(s))
d=json.loads(s)
sys=d['agents']['valuation-main']['system']
print(repr(sys[:80]))
print(sys[:80].encode('utf-8').hex())
print('has replacement', '\ufffd' in sys)
# try gbk bytes roundtrip
try:
    print('re-encode gbk', sys[:20].encode('gbk'))
except Exception as e:
    print('gbk encode fail', e)
