# -*- coding: utf-8 -*-
"""공개 배출량 데이터를 공장 목록에 붙인다.

읽는 파일 (data\\emission\\ 폴더에 넣어두면 자동으로 찾는다)
  1) 할당대상업체 현황      https://www.data.go.kr/data/15053949/fileData.do
  2) 관리업체 명세서 배출량  https://www.data.go.kr/data/15053947/fileData.do

둘 다 업체명(법인명)이 들어 있어 공장 목록의 회사명과 이름으로 맞출 수 있다.
사업자등록번호가 양쪽 모두 없어 이름 대조가 유일한 방법이고, 그래서 매칭은
완전하지 않다. 매칭률과 미매칭 사례를 반드시 출력해 눈으로 확인하게 한다.

산출물 : emission.json  (3_build_data.py 가 있으면 자동으로 읽어 붙인다)
"""
import pandas as pd, json, os, re, glob, sys, io, unicodedata
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths

DIR = paths.data('emission')

# ── 이름 정규화 ────────────────────────────────────────────────────────────
# "주식회사 포스코", "(주)포스코", "㈜포스코 광양제철소" 를 모두 "포스코" 로 만든다.
LEGAL = re.compile(r'\(주\)|\(유\)|\(재\)|\(사\)|㈜|㈐|주식회사|유한회사|유한책임회사|'
                   r'합자회사|합명회사|재단법인|사단법인|의료법인|학교법인|주\)|유\)')
SUFFIX = re.compile(r'(제?\d*\s*(공장|사업장|지점|영업소|사업소|제철소|제강소|발전소|'
                    r'센터|캠퍼스|플랜트|단지))+\s*$')
NOISE = re.compile(r'[\s\.\,\-\_\·\(\)\[\]<>/]+')

def norm(s):
    """(붙인 이름, 경계를 | 로 남긴 이름) 두 벌을 만든다.

    경계가 필요한 이유 — 접두 일치를 그냥 허용하면 '포스코케미칼'이 '포스코'로
    붙어버려 7,500만 톤이 엉뚱한 법인에 찍힌다. 원문에서 띄어쓰기나 (주) 자리가
    끊긴 곳에서만 접두 일치를 인정해야 '포스코 광양'은 붙고 '포스코케미칼'은 안 붙는다.
    """
    if not isinstance(s, str):
        return '', ''
    s = unicodedata.normalize('NFKC', s)
    s = LEGAL.sub(' ', s)
    s = SUFFIX.sub(' ', s.strip())
    b = NOISE.sub('|', s).strip('|')
    return b.replace('|', ''), b

# ── 컬럼 자동 인식 ─────────────────────────────────────────────────────────
# 두 파일 모두 연도마다 헤더가 조금씩 바뀐다. 이름을 고정하지 않고 키워드로 찾는다.
def pick(cols, *groups):
    """groups 안 키워드를 모두 만족하는 첫 컬럼. groups=(('업체','법인'),) 는 OR."""
    for c in cols:
        t = str(c).replace(' ', '')
        if all(any(k in t for k in g) for g in groups):
            return c
    return None

# 공공데이터포털의 "XLS"는 실제 내용이 제각각이다. 확장자를 믿지 않고 앞머리를 본다.
#   PK..            → 진짜 xlsx (openpyxl)
#   D0 CF 11 E0..   → 옛 xls 이진 형식 (xlrd 필요)
#   그 밖          → HTML 표이거나 CSV 인데 이름만 .xls 인 경우 (흔하다)
def sniff(path):
    with open(path, 'rb') as f:
        head = f.read(8)
    if head[:4] == b'PK\x03\x04':
        return 'xlsx'
    if head == b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1':
        return 'xls'
    return 'text'

def _csv(path):
    for enc in ('utf-8-sig', 'cp949', 'euc-kr'):
        try:
            return pd.read_csv(path, encoding=enc, dtype=str)
        except (UnicodeDecodeError, pd.errors.ParserError):
            continue
    try:                      # on_bad_lines 는 pandas 1.3+
        return pd.read_csv(path, encoding='utf-8', engine='python',
                           on_bad_lines='skip', dtype=str)
    except TypeError:
        return pd.read_csv(path, encoding='utf-8', engine='python',
                           error_bad_lines=False, dtype=str)

def _html(path):
    raw = open(path, 'rb').read()
    if b'<table' not in raw.lower() and b'<TABLE' not in raw:
        return None
    for enc in ('utf-8-sig', 'cp949', 'euc-kr', 'utf-8'):
        try:
            txt = raw.decode(enc)
        except UnicodeDecodeError:
            continue
        if '\ufffd' in txt:          # 깨진 디코딩
            continue
        try:
            ts = pd.read_html(io.StringIO(txt))
        except Exception:
            continue
        if ts:
            return max(ts, key=len).astype(str)
    return None

def _rows_xls(path):
    """옛 xls 를 xlrd 로 직접 읽는다.

    pandas 를 거치지 않는 이유 — pandas 의 read_excel 은 xlrd 를 부르기 전에
    자체 버전 표를 보고 막는 경우가 있어, xlrd 가 멀쩡히 깔려 있어도
    'Missing optional dependency' 를 던진다. xlrd 를 직접 부르면 그 관문을 지난다.
    """
    import xlrd
    bk = xlrd.open_workbook(path)
    sh = bk.sheet_by_index(0)
    rows = []
    for r in range(sh.nrows):
        row = []
        for c in range(sh.ncols):
            v = sh.cell_value(r, c)
            if isinstance(v, float) and v == int(v):
                v = int(v)
            row.append('' if v is None else str(v).strip())
        rows.append(row)
    return rows

def _rows_xlsx(path):
    """xlsx 를 openpyxl 로 직접 읽는다.

    공공데이터포털 xlsx 는 시트 크기가 A1:A1 로 잘못 적혀 있는 것이 있다.
    read_only 모드는 그 선언을 믿기 때문에 첫 줄만 읽히고 나머지를 통째로 놓친다.
    (할당대상업체현황이 '0개 법인' 으로 나오던 원인) 크기를 다시 재게 한다.
    """
    from openpyxl import load_workbook

    def grab(ws):
        return [['' if v is None else str(v).strip() for v in r]
                for r in ws.iter_rows(values_only=True)]

    wb = load_workbook(path, read_only=True, data_only=True)
    ws = wb[wb.sheetnames[0]]
    try:
        ws.reset_dimensions()
    except AttributeError:
        pass
    rows = grab(ws)
    wb.close()
    if len(rows) > 2:
        return rows
    wb = load_workbook(path, read_only=False, data_only=True)   # 최후 수단
    rows = grab(wb[wb.sheetnames[0]])
    wb.close()
    return rows

def _frame(rows):
    """안내 문구가 몇 줄 붙어 있어도 진짜 헤더 행을 찾아 쓴다.

    맨 윗줄이 '할당대상업체현황 (808건)' 같은 제목인 파일이 있다. 그 줄에도 '업체'가
    들어 있어 키워드만 보면 제목을 헤더로 잡아버리고, 그러면 순번 열을 업체명으로
    읽어 809개의 '1', '2' 를 법인명이라 우기게 된다. 그래서 **셀이 3칸 이상 찬 줄**만
    헤더 후보로 본다. 제목 줄은 한 칸뿐이라 걸러진다.
    """
    rows = [r for r in rows if any(str(c).strip() for c in r)]
    if not rows:
        return pd.DataFrame()

    def build(h):
        w = len(rows[h])
        body = [(r + [''] * w)[:w] for r in rows[h + 1:]]
        return pd.DataFrame(body, columns=rows[h], dtype=str)

    for h in range(min(8, len(rows))):
        filled = sum(1 for c in rows[h] if str(c).strip())
        if filled >= 3 and pick(rows[h], ('업체', '법인', '회사', '사업장')):
            return build(h)
    for h in range(min(8, len(rows))):        # 회사 관련 낱말이 없는 헤더도 있다
        if sum(1 for c in rows[h] if str(c).strip()) >= 3:
            return build(h)
    return build(0)

def read_any(path):
    kind = sniff(path)
    if kind == 'text':
        d = _html(path)
        if d is None:
            d = _csv(path)
        # HTML/CSV 는 헤더가 위쪽 안내문 아래에 있는 경우가 많다
        for h in range(6):
            if pick(d.columns, ('업체', '법인', '회사', '사업장')):
                return d
            d.columns = d.iloc[0]
            d = d.iloc[1:].reset_index(drop=True)
        return d
    try:
        return _frame(_rows_xlsx(path) if kind == 'xlsx' else _rows_xls(path))
    except ImportError as e:
        need = 'openpyxl' if kind == 'xlsx' else 'xlrd'
        sys.exit(
            '\n' + os.path.basename(path) + ' 을 읽지 못했습니다 (' + kind + ' 형식).\n'
            '  실제 오류: ' + str(e) + '\n\n'
            '  pip install ' + need + '\n'
            '를 실행한 뒤 다시 돌리십시오.\n'
            '이미 깔려 있는데도 이 메시지가 나오면 엑셀에서 열어\n'
            '"다른 이름으로 저장 → CSV UTF-8" 로 바꿔 emission\\ 에 넣으면 됩니다.')

def name_col(d):
    """업체명 컬럼. 느슨한 후보는 짧은 이름만 인정한다 —
    '할당대상업체현황 (808건)' 같은 제목이 컬럼명이 된 경우를 걸러내기 위해서다."""
    c = pick(d.columns, ('업체', '법인', '회사'), ('명',))
    if c:
        return c
    c = pick(d.columns, ('업체', '법인', '회사'))
    return c if c and len(str(c).strip()) <= 12 else None

def find(*pats):
    for p in pats:
        hits = sorted(glob.glob(os.path.join(DIR, p))) + sorted(glob.glob(p))
        if hits:
            return hits[0]
    return None

def num(v):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    s = re.sub(r'[^\d\.\-]', '', str(v))
    if s in ('', '-', '.'):
        return None
    try:
        return float(s)
    except ValueError:
        return None

# ── 1. 할당대상업체 현황 ───────────────────────────────────────────────────
bound = {}   # 압축 키 → 경계(|)를 남긴 키
ets = {}
f_ets = find('*할당대상업체*.xls*', '*할당대상업체*.csv', '*할당*.xls*')
if f_ets:
    d = read_any(f_ets)
    c_nm = name_col(d)
    c_in = pick(d.columns, ('업종',))
    c_ad = pick(d.columns, ('주소', '소재'))
    c_yr = pick(d.columns, ('연도', '년도', '기간', '차'))
    if not c_nm:
        print(f'  ! {f_ets} 에서 업체명 컬럼을 찾지 못했습니다. 컬럼: {list(d.columns)[:12]}')
    else:
        for _, r in d.iterrows():
            k, kb = norm(r[c_nm])
            if len(k) < 2:
                continue
            bound[k] = kb
            ets[k] = {'raw': str(r[c_nm]).strip(),
                      'ind': str(r[c_in]).strip() if c_in and pd.notna(r[c_in]) else '',
                      'addr': str(r[c_ad]).strip() if c_ad and pd.notna(r[c_ad]) else '',
                      'yr': str(r[c_yr]).strip() if c_yr and pd.notna(r[c_yr]) else ''}
    print(f'  할당대상업체  {f_ets}  →  {len(ets):,}개 법인')
else:
    print('  할당대상업체 파일 없음 (건너뜀)')

# ── 2. 명세서 배출량 ───────────────────────────────────────────────────────
emit, years = {}, set()
f_em = find('*명세서*.xls*', '*명세서*.csv', '*배출량*.xls*', '*배출량*.csv')
if f_em:
    d = read_any(f_em)
    c_nm = name_col(d)
    c_em = (pick(d.columns, ('배출량',), ('tCO', 'CO2', '온실가스')) or pick(d.columns, ('배출량',)))
    c_en = pick(d.columns, ('에너지',))
    c_yr = pick(d.columns, ('연도', '년도'))
    c_in = pick(d.columns, ('업종',))
    c_gv = pick(d.columns, ('관장',))
    c_ds = pick(d.columns, ('지정', '구분'))
    if not c_nm or not c_em:
        print(f'  ! {f_em} 에서 업체명/배출량 컬럼을 찾지 못했습니다. 컬럼: {list(d.columns)[:14]}')
    else:
        for _, r in d.iterrows():
            k, kb = norm(r[c_nm])
            e = num(r[c_em])
            if len(k) < 2 or e is None:
                continue
            bound[k] = kb
            y = num(r[c_yr]) if c_yr else None
            y = int(y) if y else 0
            years.add(y)
            prev = emit.get(k)
            if prev and prev['y'] >= y:          # 최신 연도만 남긴다
                continue
            # 배출량 0 으로 신고된 법인이 있다. 명세서 제출 사실은 남기되 값은 비운다.
            emit[k] = {'raw': str(r[c_nm]).strip(),
                       'e': round(e, 1) if e > 0 else None, 'y': y,
                       'en': round(num(r[c_en]), 1) if c_en and num(r[c_en]) else None,
                       'ind': str(r[c_in]).strip() if c_in and pd.notna(r[c_in]) else '',
                       'gov': str(r[c_gv]).strip() if c_gv and pd.notna(r[c_gv]) else '',
                       'ds': str(r[c_ds]).strip() if c_ds and pd.notna(r[c_ds]) else ''}
    yr = max(years - {0}) if years - {0} else None
    print(f'  명세서 배출량  {f_em}  →  {len(emit):,}개 법인'
          + (f' (최신 {yr}년)' if yr else ''))
else:
    print('  명세서 배출량 파일 없음 (건너뜀)')

if not ets and not emit:
    print('\ndata\\emission\\ 폴더에 파일이 없습니다. EMISSION.md 의 내려받기 주소를 보십시오.')
    json.dump({'have': False}, open(paths.EMISSION, 'w', encoding='utf-8'), ensure_ascii=False)
    sys.exit(0)

# ── 3. 공장 목록과 이름 대조 ───────────────────────────────────────────────
df = pd.read_pickle(paths.CLEAN)
tgt = df[(df['CBAM'] != '') | (df['열공정'] != '해당없음')].copy()
_n = tgt['회사명'].map(norm)
tgt['키'] = _n.map(lambda t: t[0])
tgt['키경계'] = _n.map(lambda t: t[1])

# 정확 일치가 먼저. 그다음 경계 접두 일치(법인명 + 지역/공장 꼬리표).
keys = sorted(set(ets) | set(emit))
pref = sorted([(bound[k] + '|', k) for k in keys if len(k) >= 3],
              key=lambda t: -len(t[0]))     # 긴 것부터 — '현대제철'이 '현대'보다 먼저

def match(k, kb):
    if not k:
        return None
    if k in ets or k in emit:
        return k
    for p, lk in pref:
        if kb.startswith(p):
            return lk
    return None

hit = {}
for k, kb in tgt[['키', '키경계']].drop_duplicates().itertuples(index=False):
    m = match(k, kb)
    if m:
        hit[k] = m

tgt['매칭'] = tgt['키'].map(hit)
n_ets = int(tgt['매칭'].isin(ets).sum())
n_em = int(tgt['매칭'].isin(emit).sum())

print(f'\n타깃 공장 {len(tgt):,}개소 중')
print(f'  할당대상업체 소속  {n_ets:,}개소 ({n_ets/len(tgt)*100:.1f}%)')
print(f'  배출량 공개 법인   {n_em:,}개소 ({n_em/len(tgt)*100:.1f}%)')
print(f'  규제 밖 추정       {len(tgt)-max(n_ets, n_em):,}개소'
      f' ({(len(tgt)-max(n_ets, n_em))/len(tgt)*100:.1f}%)  ← 지원사업 1차 타깃')

# 매칭된 이름 쌍을 눈으로 볼 수 있게 남긴다. 접두 일치는 오검출이 섞인다.
pairs = (tgt[tgt['매칭'].notna()][['회사명', '매칭']]
         .drop_duplicates().sort_values('회사명'))
pairs['공개명'] = pairs['매칭'].map(lambda k: (emit.get(k) or ets.get(k, {})).get('raw', ''))
pairs['배출량'] = pairs['매칭'].map(lambda k: emit.get(k, {}).get('e'))
pairs[['회사명', '공개명', '배출량']].to_csv(
    paths.out('배출량_매칭결과.csv'), index=False, encoding='utf-8-sig')
print(f'  → 배출량_매칭결과.csv  {len(pairs):,}쌍 (접두 일치가 섞여 있으니 훑어보십시오)')

# ── 4. 산출 ────────────────────────────────────────────────────────────────
# 3_build_data.py 가 정규화를 다시 하지 않아도 되도록 원문 회사명으로 키를 잡는다.
byname = {}
for nm, k in (tgt[tgt['매칭'].notna()][['회사명', '매칭']]
              .drop_duplicates().itertuples(index=False)):
    src = emit.get(k) or ets.get(k, {})
    byname[nm] = {'nm': src.get('raw', ''),
                  'e': emit.get(k, {}).get('e'),
                  'en': emit.get(k, {}).get('en'),
                  'ind': src.get('ind', ''),
                  'ets': bool(k in ets)}

# 업종별 합계 — 매칭된 법인의 배출량을 공장이 속한 업종으로 모은다.
bysec = {}
for se, sub in tgt[tgt['매칭'].notna()].groupby('업종'):
    v = sub.drop_duplicates('매칭')['매칭'].map(lambda k: emit.get(k, {}).get('e'))
    v = sorted(float(x) for x in v if pd.notna(x) and x)   # NaN 은 truthy 라 걸러야 한다
    if v:
        bysec[se] = {'n': len(v), 'sum': round(sum(v), 1), 'med': round(v[len(v)//2], 1)}

out = {
    'have': True,
    'year': max(years - {0}) if years - {0} else None,
    'src': {'ets': os.path.basename(f_ets) if f_ets else None,
            'emit': os.path.basename(f_em) if f_em else None},
    'n': {'ets': len(ets), 'emit': len(emit), 'hitEts': n_ets, 'hitEmit': n_em,
          'tgt': int(len(tgt)), 'out': int(len(tgt) - max(n_ets, n_em))},
    'byName': byname,
    'bySector': bysec,
}
json.dump(out, open(paths.EMISSION, 'w', encoding='utf-8'),
          ensure_ascii=False, separators=(',', ':'))
print(f'\nemission.json {os.path.getsize(paths.EMISSION)/1024:.0f} KB')
print('이어서  python 3_build_data.py  →  python 4_make_page.py  를 돌리십시오.')
