# -*- coding: utf-8 -*-
"""모아서 화면용 데이터 만들기 → out/data.json

범위 (환경변수 SCOPE)
    complex   산업단지 입주업체 전체 84,111곳   ← 기본값
    national  국가산업단지만 32,636곳
    target    CBAM·열공정 대상만
    all       전국 등록공장 217,048곳

    $env:SCOPE='national'; python src\\08_build.py

**용량을 줄이는 세 가지**
  1) 반복되는 값(단지·업종·시도·품목·법인명)은 사전에 담고 번호만 적는다
  2) 주소 앞의 "경상남도 창원시 성산구" 덩어리도 사전으로 뺀다 (284종뿐)
  3) 행을 객체가 아니라 배열로 적는다 — 키 이름이 8만 번 반복되지 않는다
"""
import os, sys, re, json, collections
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths

SCOPE = (os.environ.get('SCOPE') or 'complex').lower()

SIDO_XY = {
 '서울': (37.5665, 126.9780), '부산': (35.1796, 129.0756), '대구': (35.8714, 128.6014),
 '인천': (37.4563, 126.7052), '광주': (35.1595, 126.8526), '대전': (36.3504, 127.3845),
 '울산': (35.5384, 129.3114), '세종': (36.4800, 127.2890), '경기': (37.4138, 127.5183),
 '강원': (37.8228, 128.1555), '충북': (36.6357, 127.4917), '충남': (36.5184, 126.8000),
 '전북': (35.7175, 127.1530), '전남': (34.8679, 126.9910), '경북': (36.4919, 128.8889),
 '경남': (35.4606, 128.2132), '제주': (33.4996, 126.5312),
}
CXT = ['국가산업단지', '일반산업단지', '도시첨단산업단지', '농공단지',
       '자유무역지역', '외국인투자지역', '기타 단지', '개별입지']

def load(path):
    if os.path.exists(path):
        d = json.load(open(path, encoding='utf-8'))
        if d.get('have'):
            return d
    return {'have': False}

paths.need(paths.CLEAN, 'python src\\01_prep.py 를 먼저 돌리십시오')
df = pd.read_pickle(paths.CLEAN)
SECTORS = [s for s in df['업종'].value_counts().index if s != '미분류']

geo = {}
if os.path.exists(paths.GEO):
    for a, v in json.load(open(paths.GEO, encoding='utf-8')).items():
        if v and v.get('lat'):
            geo[a] = (round(float(v['lat']), 5), round(float(v['lon']), 5))

em = load(paths.EMISSION);  EMN = em.get('byName', {})
fin = load(paths.FINANCE);  FIN = fin.get('byName', {})
pen = load(paths.PENSION);  PEN = pen.get('byName', {})
con = load(paths.CONTACT);  CON = con.get('byName', {})
exp = load(paths.EXPORT);   EXP = exp.get('byName', {})

# 연락처에서 얻은 좌표도 쓴다 — 카카오가 장소를 찾아주면 거기가 곧 위치다
for nm, c in CON.items():
    if c.get('y') and c.get('g') == '확실':
        pass    # 회사명 기준이라 주소 기준 geo 와 충돌 없이 아래에서 개별 적용

# ── 품목 ───────────────────────────────────────────────────────────────────
# 생산품이 자유기술이라 그대로는 못 고른다. 쉼표·슬래시로 끊어 낱말을 세고,
# 업종마다 자주 나오는 낱말 60개를 그 업종의 '품목' 목록으로 삼는다.
RE_TOK = re.compile(r'[,/·|;]+|\s+및\s+|\s+외\s+|\s*\+\s*')
DROP = re.compile(r'(제조업?|생산|가공|판매|등)$')

def tokens(s):
    out = []
    for t in RE_TOK.split(str(s)):
        t = DROP.sub('', t.strip()).strip()
        if 1 < len(t) <= 14:
            out.append(t)
    return out

TOP_N, MIN_N = 60, 10
sec_tok = collections.defaultdict(collections.Counter)
row_tok = []
for se, pr in zip(df['업종'], df['생산품']):
    ts = tokens(pr)
    row_tok.append(ts)
    sec_tok[se].update(set(ts))
PM_BY_SEC = {se: [w for w, n in c.most_common(TOP_N) if n >= MIN_N]
             for se, c in sec_tok.items()}
pm_rank = {se: {w: i for i, w in enumerate(ws)} for se, ws in PM_BY_SEC.items()}
품목 = []
for se, ts in zip(df['업종'], row_tok):
    rank = pm_rank.get(se, {})
    best, bi = '', 10 ** 9
    for t in ts:
        i = rank.get(t)
        if i is not None and i < bi:
            best, bi = t, i
    품목.append(best)
df['품목'] = 품목

# ── 범위 ───────────────────────────────────────────────────────────────────
if SCOPE == 'complex':
    view = df[df['입지'] == '산업단지'].copy()
elif SCOPE == 'national':
    view = df[df['단지유형'] == '국가산업단지'].copy()
elif SCOPE == 'target':
    view = df[(df['CBAM'] != '') | (df['열공정'] != '해당없음')].copy()
else:
    view = df.copy()

# ── 영업 우선순위 ──────────────────────────────────────────────────────────
# 임의로 매기는 점수라 **근거를 화면에 그대로 보여준다.** 숫자만 믿으면 안 된다.
SCORE = [
    ('cbam',   40, 'CBAM 품목'),
    ('heat',   15, '고온 열공정'),
    ('unreg',  20, '규제 밖'),
    ('size',   15, '종업원 20~300'),
    ('export', 25, '수출 명단'),
    ('tel',    10, '연락처 확인'),
    ('grow',    5, '고용 증가'),
]

def score_of(cbam, heat, reg, cnt, exported, telg, gin, gout):
    s, why = 0, []
    for k, pt, label in SCORE:
        ok = (k == 'cbam' and cbam) or \
             (k == 'heat' and heat != '해당없음') or \
             (k == 'unreg' and not reg) or \
             (k == 'size' and cnt and 20 <= cnt <= 300) or \
             (k == 'export' and exported) or \
             (k == 'tel' and telg in (3, 4)) or \
             (k == 'grow' and gin and gin > gout)
        if ok:
            s += pt; why.append(label)
    return s, why

# ── 사전 ───────────────────────────────────────────────────────────────────
SIDO_FULL = (r'(서울특별시|부산광역시|대구광역시|인천광역시|광주광역시|대전광역시|'
             r'울산광역시|세종특별자치시|경기도|강원특별자치도|강원도|충청북도|충청남도|'
             r'전라북도|전북특별자치도|전라남도|경상북도|경상남도|제주특별자치도)')
RE_PRE = re.compile(r'^' + SIDO_FULL +
                    r'\s*((?:[가-힣]+(?:특별자치)?시\s+[가-힣]+구|[가-힣]+시|[가-힣]+군|[가-힣]+구))?\s*')

def split_addr(a):
    m = RE_PRE.match(a)
    return (m.group(0).strip(), a[m.end():]) if m else ('', a)

def build_dict(values):
    vals = [''] + sorted(v for v in set(values) if v)
    return vals, {v: i for i, v in enumerate(vals)}

pre_pairs = [split_addr(a) for a in view['공장주소']]
D_ap, I_ap = build_dict(p for p, _ in pre_pairs)
D_cx, I_cx = build_dict(view.loc[view['입지'] == '산업단지', '단지'])
D_ct, I_ct = build_dict(CXT)
D_si, I_si = build_dict(view['시도'])
D_gg, I_gg = build_dict(view['시군구'])
D_se, I_se = build_dict(view['업종'])
D_he, I_he = build_dict(view['열공정'])
D_cb, I_cb = build_dict(view['CBAM'])
D_pm, I_pm = build_dict(view['품목'])
D_ln, I_ln = build_dict(v['nm'] for v in EMN.values() if v.get('nm'))
D_fn, I_fn = build_dict(v['nm'] for v in FIN.values() if v.get('nm'))
D_ex, I_ex = build_dict(s for v in EXP.values() for s in v.get('src', []))

GRADE = {'두곳확인': 4, '불일치': 5, '확실': 3, '보통': 2, '낮음': 1, '없음': 0}

# ── 행 ─────────────────────────────────────────────────────────────────────
#  0 회사명 1 생산품 2 주소뒤 3 주소앞 4 단지 5 단지유형 6 시도 7 시군구
#  8 업종 9 열공정 10 CBAM 11 위도 12 경도
# 13 규제구분 14 배출법인 15 배출량 16 매출 17 DART법인 18 상장 19 품목
# 20 종업원 21 고지금액 22 신규 23 상실
# 24 전화 25 지도링크 26 연락처등급 27 수출여부 28 수출출처 29 점수
firms = []
ngeo = ntel = nexp = npen = 0
for (pre, suf), r in zip(pre_pairs, view.itertuples(index=False)):
    e = EMN.get(r.회사명); v = FIN.get(r.회사명)
    p = PEN.get(r.회사명); c = CON.get(r.회사명); x = EXP.get(r.회사명)

    ll = geo.get(r.공장주소)
    if not ll and c and c.get('g') in ('확실', '두곳확인') and c.get('y'):
        ll = (round(c['y'], 5), round(c['x'], 5))     # 카카오가 찾아준 장소 좌표
    if ll:
        ngeo += 1

    reg = (1 if e['ets'] else 2) if e else 0
    cnt = int(p['cnt']) if p else 0
    telg = GRADE.get(c['g'], 0) if c else 0
    if telg and c.get('tel'):
        ntel += 1
    if p:
        npen += 1
    if x:
        nexp += 1
    s, _why = score_of(r.CBAM, r.열공정, reg, cnt, bool(x), telg,
                       int(p['in']) if p else 0, int(p['out']) if p else 0)

    firms.append([
        r.회사명, r.생산품, suf, I_ap[pre],
        I_cx[r.단지] if r.입지 == '산업단지' else 0,
        I_ct.get(r.단지유형, 0), I_si[r.시도], I_gg[r.시군구],
        I_se[r.업종], I_he[r.열공정], I_cb[r.CBAM],
        ll[0] if ll else 0, ll[1] if ll else 0,
        reg, I_ln.get(e['nm'], 0) if e else 0, (e.get('e') or 0) if e else 0,
        (v.get('sales') or 0) if v else 0, I_fn.get(v['nm'], 0) if v else 0,
        1 if (v and v.get('sc')) else 0,
        I_pm[r.품목],
        cnt, int(p['amt']) if p else 0, int(p['in']) if p else 0, int(p['out']) if p else 0,
        (c['tel'] if c else '') or '', (c['url'] if c else '') or '', telg,
        1 if x else 0, I_ex.get((x['src'][0] if x and x.get('src') else ''), 0),
        s,
    ])

def by(sub, col, keys):
    return {k: int((sub[col] == k).sum()) for k in keys}

sido = []
for s_, xy in SIDO_XY.items():
    d = df[df['시도'] == s_]
    sido.append({'name': s_, 'lat': xy[0], 'lon': xy[1],
                 'total': int(len(d)), 'sec': by(d, '업종', SECTORS)})

cx_rows = []
for name, sub in df[df['입지'] == '산업단지'].groupby('단지'):
    cx_rows.append({'name': name, 'type': sub['단지유형'].iloc[0],
                    'sido': sub['시도'].mode().iloc[0] if len(sub['시도'].mode()) else '미상',
                    'sgg': sub['시군구'].mode().iloc[0] if len(sub['시군구'].mode()) else '미상',
                    'total': int(len(sub))})
cx_rows.sort(key=lambda z: -z['total'])

SCOPE_LABEL = {'complex': '산업단지 입주업체', 'national': '국가산업단지 입주업체',
               'target': 'CBAM·열공정 대상', 'all': '전국 등록공장'}

meta = {
    'source': '한국산업단지공단 전국등록공장현황 (2024-12-31 기준)',
    'scope': SCOPE, 'scopeLabel': SCOPE_LABEL.get(SCOPE, SCOPE),
    'rows': int(len(df)), 'shown': int(len(view)),
    'cbam': int((view['CBAM'] != '').sum()),
    'heat': int((view['열공정'] != '해당없음').sum()),
    'complexes': int(view[view['입지'] == '산업단지']['단지'].nunique()),
    'complexesAll': int(df[df['입지'] == '산업단지']['단지'].nunique()),
    'unparsed': int((view['시도'] == '미상').sum()),
    'sectors': SECTORS, 'cxtypes': CXT,
    'heats': ['용해·소성', '건조·증기'],
    'cbams': ['철강', '알루미늄', '시멘트', '비료', '수소'],
    'pmBySector': {k: [w for w in v if w in I_pm] for k, v in PM_BY_SEC.items()},
    'geocoded': ngeo,
    'secTotals': {k: int((view['업종'] == k).sum()) for k in SECTORS},
    'cxtTotals': {k: int((view['단지유형'] == k).sum()) for k in CXT},
    'score': [{'k': k, 'pt': pt, 'label': lb} for k, pt, lb in SCORE],
    'pension': {'have': pen.get('have', False), 'src': pen.get('src'),
                'rows': npen, 'n': pen.get('n')},
    'contact': {'have': con.get('have', False), 'rows': ntel},
    'export': {'have': exp.get('have', False), 'src': exp.get('src'),
               'rows': nexp, 'list': D_ex},
    'fin': {'have': fin.get('have', False), 'year': fin.get('year'),
            'rows': int(sum(1 for f in firms if f[16]))},
    'emit': {'have': em.get('have', False), 'year': em.get('year'),
             'ets': int(sum(1 for f in firms if f[13] == 1)),
             'mgmt': int(sum(1 for f in firms if f[13] == 2))},
}

out = {'meta': meta,
       'dict': {'ap': D_ap, 'cx': D_cx, 'ct': D_ct, 'si': D_si, 'gg': D_gg,
                'se': D_se, 'he': D_he, 'cb': D_cb, 'pm': D_pm,
                'ln': D_ln, 'fn': D_fn, 'ex': D_ex},
       'sido': sido, 'complexes': cx_rows, 'firms': firms}
json.dump(out, open(paths.DATAJSON, 'w', encoding='utf-8'),
          ensure_ascii=False, separators=(',', ':'))

mb = os.path.getsize(paths.DATAJSON) / 1e6
print(f"out\\data.json {mb:.2f} MB | {meta['scopeLabel']} {len(view):,}곳")
print(f"  CBAM {meta['cbam']:,} · 열공정 {meta['heat']:,} · 좌표 {ngeo:,}"
      f" · 종업원 {npen:,} · 연락처 {ntel:,} · 수출명단 {nexp:,}")

# 영업용 CSV — 점수 높은 순
cols = ['회사명', '단지', '단지유형', '업종', '품목', '생산품', 'CBAM', '열공정',
        '시도', '시군구', '공장주소']
sales = view[cols].copy()
sales['종업원수'] = view['회사명'].map(lambda n: (PEN.get(n) or {}).get('cnt', ''))
sales['당월고지금액'] = view['회사명'].map(lambda n: (PEN.get(n) or {}).get('amt', ''))
sales['전화번호'] = view['회사명'].map(lambda n: (CON.get(n) or {}).get('tel', ''))
sales['연락처신뢰도'] = view['회사명'].map(lambda n: (CON.get(n) or {}).get('g', ''))
sales['수출명단'] = view['회사명'].map(
    lambda n: ' / '.join((EXP.get(n) or {}).get('src', [])))
sales['규제'] = view['회사명'].map(
    lambda n: '할당대상' if (EMN.get(n) or {}).get('ets') else
              ('명세서' if EMN.get(n) else '규제 밖'))
sales['우선순위'] = [f[29] for f in firms]
sales.sort_values('우선순위', ascending=False).to_csv(
    paths.out('영업리스트.csv'), index=False, encoding='utf-8-sig')
print(f"  → out\\영업리스트.csv  ({len(sales):,}행, 우선순위 높은 순)")
