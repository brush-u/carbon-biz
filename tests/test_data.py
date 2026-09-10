import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src'))
import paths
os.chdir(paths.ROOT)
# -*- coding: utf-8 -*-
"""파이프라인 검증

각 단계의 산출물이 서로 어긋나지 않는지 확인한다.
분류 규칙을 고쳤거나 데이터를 갱신했으면 이걸 돌려서 통과하는지 먼저 보라.

    python 6_test.py
"""
import glob, json, os, re, sys
import pandas as pd

PASS, FAIL, WARN = [], [], []

def ok(name, cond, detail=''):
    (PASS if cond else FAIL).append((name, detail))
def warn(name, detail):
    WARN.append((name, detail))

# ---------------------------------------------------------------- 1. 원본 ↔ clean.pkl
src = os.environ.get('FACTORY_CSV')
if not src:
    hits = sorted(glob.glob('*등록공장현황*.csv')) or sorted(glob.glob('*공장현황*.csv'))
    src = hits[0] if hits else None

if not os.path.exists(paths.CLEAN):
    print("clean.pkl 이 없습니다. 먼저 python src\\01_prep.py 를 실행하세요.")
    sys.exit(1)

df = pd.read_pickle(paths.CLEAN)
N = len(df)

# clean.pkl 이 예전 버전이면 컬럼이 다르다 (품목군 → 업종/열공정/단지유형으로 개편됨)
need_cols = ['업종', '열공정', '단지유형', 'CBAM', '시도', '시군구']
missing = [c for c in need_cols if c not in df.columns]
if missing:
    print("clean.pkl 이 예전 버전입니다. 없는 컬럼: " + ', '.join(missing))
    print("현재 컬럼: " + ', '.join(df.columns))
    print()
    print("아래 순서로 다시 만들고 나서 테스트하세요.")
    print("    python src\\01_prep.py")
    print("    python src\\08_build.py")
    print("    python src\\09_page.py")
    print("    python 5_mymaps.py")
    print("    Copy-Item map_page.html index.html -Force")
    sys.exit(1)

if src:
    raw_n = sum(1 for _ in open(src, encoding='cp949')) - 1
    ok('원본 행 수 == 분류 결과 행 수', raw_n == N, f'원본 {raw_n:,} / 분류 {N:,}')
else:
    warn('원본 대조', '원본 CSV를 찾지 못해 행 수 대조를 건너뜀')

# ---------------------------------------------------------------- 2. 분류 누락 없음
for col in ['업종', '단지유형', '열공정']:
    s = df[col].value_counts().sum()
    ok(f'{col} 분류 합계 == 전체', s == N, f'{s:,} / {N:,}')
    ok(f'{col} 공백 없음', (df[col].astype(str).str.strip() == '').sum() == 0)

ok('CBAM 컬럼 값이 정해진 5종 + 공백', 
   set(df['CBAM'].unique()) <= {'', '철강', '알루미늄', '시멘트', '비료', '수소'},
   str(sorted(df['CBAM'].unique())))

# ---------------------------------------------------------------- 3. 주소 파싱 품질
unp = (df['시도'] == '미상').sum()
ok('시도 파싱 실패 2% 미만', unp / N < 0.02, f'{unp:,}건 ({unp/N*100:.2f}%)')
blank_addr = (df['공장주소'].str.strip() == '').sum()
ok('주소 미상 대부분이 빈 주소', unp - blank_addr < N * 0.005,
   f'미상 {unp:,} 중 빈 주소 {blank_addr:,}')

# ---------------------------------------------------------------- 4. 단지유형 정합성
cx_has_name = df['단지명'].str.strip() != ''
ok('단지명 있으면 개별입지가 아님',
   (df.loc[cx_has_name, '단지유형'] == '개별입지').sum() == 0)
ok('단지명 없으면 개별입지',
   (df.loc[~cx_has_name, '단지유형'] != '개별입지').sum() == 0)

# ---------------------------------------------------------------- 5. 분류 스팟 체크
# 생산품 → 기대 업종/열공정. 규칙을 고쳤을 때 의도치 않게 깨지는지 잡는다.
SPOT = [
    ('시멘트',        '비금속광물·건자재', '용해·소성'),
    ('판유리',        '비금속광물·건자재', '용해·소성'),
    ('열연강판',      '1차 금속',        '해당없음'),
    ('알루미늄괴',    '1차 금속',        '용해·소성'),
    ('유기질비료',    '화학·정밀화학',    None),
    ('마른김',        '식품·음료',       None),
    ('의약품',        '바이오·의약',      None),
    ('골판지',        '목재·가구·제지',   None),
    ('반도체',        '전기·전자',       None),
    ('자동차부품',    '자동차·운송장비',  None),
]
sys.path.insert(0, '.')
import importlib.util
spec = importlib.util.spec_from_file_location('prep', os.path.join(paths.ROOT,'src','01_prep.py'))
prep = importlib.util.module_from_spec(spec)
try:
    spec.loader.exec_module(prep)          # 원본 CSV 탐색 때문에 실패할 수 있음
except SystemExit:
    prep = None

if prep:
    for prod, exp_sec, exp_heat in SPOT:
        got_sec = prep.classify(prep.SECT_RX, prod, '기타 제조')
        ok(f'업종 판정: {prod} → {exp_sec}', got_sec == exp_sec, f'실제 {got_sec}')
        if exp_heat:
            got_h = prep.classify(prep.HEAT_RX, prod, '해당없음')
            if got_h == '미분류':
                got_h = '해당없음'
            ok(f'열공정 판정: {prod} → {exp_heat}', got_h == exp_heat, f'실제 {got_h}')
    # 전력은 CBAM에서 빠져 있어야 한다 (발전설비 제조업 오분류 방지)
    ok('발전기는 CBAM 대상이 아님',
       prep.classify(prep.CBAM_RX, '태양광발전장치', '') == '')
    ok('요소수는 비료가 아님', prep.classify(prep.CBAM_RX, '요소수', '') == '')
    ok('과산화수소는 수소가 아님', prep.classify(prep.CBAM_RX, '과산화수소', '') == '')
else:
    warn('스팟 체크', '1_prep.py 로드 실패 (원본 CSV 없음) — 건너뜀')

# ---------------------------------------------------------------- 6. data.json
if os.path.exists(paths.DATAJSON):
    D = json.load(open(paths.DATAJSON, encoding='utf-8'))
    m = D['meta']
    ok('data.json 총 건수 일치', m['rows'] == N, f"{m['rows']:,} / {N:,}")
    tgt_n = int(((df['CBAM'] != '') | (df['열공정'] != '해당없음')).sum())
    SCOPE_N = {'all': N,
               'complex': int((df['입지'] == '산업단지').sum()),
               'national': int((df['단지유형'] == '국가산업단지').sum()),
               'target': tgt_n}
    exp = SCOPE_N.get(m.get('scope'), tgt_n)
    ok('data.json 실린 건수 일치', m['shown'] == exp == len(D['firms']),
       f"meta {m['shown']:,} / 기대 {exp:,} / firms {len(D['firms']):,}")
    ok('CBAM·열공정 건수 일치',
       (m['cbam'], m['heat']) ==
       (int((df['CBAM'] != '').sum()), int((df['열공정'] != '해당없음').sum()))
       if m.get('scope') == 'all' else True,
       f"CBAM {m['cbam']:,} / 열공정 {m['heat']:,}")
    ok('시도 17개', len(D['sido']) == 17)
    ok('시도 합계 == 전체 - 미상',
       sum(s['total'] for s in D['sido']) == N - unp,
       f"{sum(s['total'] for s in D['sido']):,} / {N-unp:,}")
    ok('단지 수 일치', len(D['complexes']) == df.loc[cx_has_name, '단지'].nunique())
    need = {'ap','cx','ct','si','gg','se','he','cb'}
    ok('사전 완비', need <= set(D['dict']), ', '.join(sorted(need - set(D['dict']))))
    ok('사전 0번은 빈 값', all(D['dict'][k][0] == '' for k in need))
    sz = os.path.getsize(paths.DATAJSON) / 1e6
    if m.get('scope') in ('all', 'complex', 'national'):
        ok('data.json 40MB 미만', sz < 40, f'{sz:.2f} MB · 전체 범위')
    else:
        ok('data.json 16MB 미만 (아티팩트 한도)', sz < 16, f'{sz:.2f} MB')
else:
    warn(paths.DATAJSON, '없음 — python src\\08_build.py 실행 필요')

# ---------------------------------------------------------------- 7. My Maps CSV
if os.path.isdir(paths.out('mymaps')):
    files = sorted(glob.glob('mymaps/**/*.csv', recursive=True))
    files = [f for f in files if not f.endswith('MANIFEST.csv')]
    man_n = len(pd.read_csv('mymaps/MANIFEST.csv'))
    ok('mymaps 파일 수 == MANIFEST 기재 수', len(files) == man_n, f'실제 {len(files)}개 / 기재 {man_n}개')
    ok('mymaps 기본 패키지 최소 파일 수', len(files) >= 20, f'{len(files)}개')
    for req in ['00_산단공_거점.csv','01_국가산업단지.csv','02_주요_일반산업단지.csv','03_농공단지.csv']:
        ok(f'필수 레이어 {req}', os.path.exists('mymaps/'+req))
    over = []
    noaddr = []
    for f in files:
        d = pd.read_csv(f, dtype=str).fillna('')
        if len(d) > 2000:
            over.append(f'{os.path.basename(f)} {len(d)}행')
        loc = '주소' if '주소' in d.columns else ('검색주소' if '검색주소' in d.columns else None)
        if loc is None:
            noaddr.append(os.path.basename(f))
        elif (d[loc].str.strip() == '').any():
            noaddr.append(f'{os.path.basename(f)} 빈 위치 {(d[loc].str.strip()=="").sum()}건')
        if '이름' not in d.columns:
            noaddr.append(f'{os.path.basename(f)} 이름 열 없음')
    ok('모든 파일 2,000행 이하 (My Maps 한도)', not over, '; '.join(over))
    ok('모든 파일에 위치 열과 이름 열 존재', not noaddr, '; '.join(noaddr[:5]))
else:
    warn(paths.out('mymaps'), '없음 — python 5_mymaps.py 실행 필요')

# ---------------------------------------------------------------- 8. 생성된 페이지
if os.path.exists(paths.out('index.html')):
    h = open(paths.out('index.html'), encoding='utf-8').read()
    ok('페이지에 데이터가 들어 있음', '<script id="payload"' in h and len(h) > 100000,
       f'{len(h)/1e6:.2f} MB')
    ok('확대·이동 코드 포함', 'attachZoom' in h and 'class="z"' in h)
    ok('업종/단지유형 선택 UI 포함', "id=\"secf\"" in h and "id=\"cxtf\"" in h)
    # 임베드된 JSON이 실제로 파싱되는지
    mth = re.search(r'<script id="payload" type="application/json">(.*?)</script>', h, re.S)
    try:
        json.loads(mth.group(1)); ok('임베드 JSON 파싱 가능', True)
    except Exception as e:
        ok('임베드 JSON 파싱 가능', False, str(e)[:80])
else:
    warn(paths.out('index.html'), '없음 — python src\\09_page.py 실행 필요')

# ---------------------------------------------------------------- 시도 경계
SIDO17 = ['서울','부산','대구','인천','광주','대전','울산','세종','경기','강원',
          '충북','충남','전북','전남','경북','경남','제주']
if os.path.exists(paths.BOUNDARY):
    bd = json.load(open(paths.BOUNDARY, encoding='utf-8'))
    sd = bd.get('sido', {})
    ok('경계 17개 시도', sorted(sd) == sorted(SIDO17),
       '없음: ' + ', '.join(sorted(set(SIDO17) - set(sd))))
    rings = [r for v in sd.values() for r in v]
    ok('폴리곤이 닫힌 고리', all(len(r) >= 4 for r in rings), f'{len(rings)}개')
    lons = [p[0] for r in rings for p in r]; lats = [p[1] for r in rings for p in r]
    ok('좌표가 한반도 범위 안',
       124.0 < min(lons) and max(lons) < 132.0 and 32.5 < min(lats) and max(lats) < 39.0,
       f'lon {min(lons):.2f}~{max(lons):.2f} / lat {min(lats):.2f}~{max(lats):.2f}')
    ok('경계 파일 크기 400KB 미만', os.path.getsize(paths.BOUNDARY) < 400_000,
       f'{os.path.getsize(paths.BOUNDARY)/1024:.0f} KB')

    # 지오코딩 좌표가 제 시도 안에 들어가는지 — 좌표계가 어긋나면 여기서 잡힌다
    if os.path.exists(paths.GEO):
        g = json.load(open(paths.GEO, encoding='utf-8'))
        gg = {a2: v for a2, v in g.items() if v and v.get('lat')}
        sub = df[(df['시도'] != '미상')].copy()
        sub['ll'] = sub['공장주소'].map(lambda a2: gg.get(a2))
        sub = sub[sub['ll'].notna()]
        if len(sub) > 100:
            def pip(lon, lat, rr):
                for r in rr:
                    ins = False; n = len(r); j = n - 1
                    for i in range(n):
                        xi, yi = r[i]; xj, yj = r[j]
                        if (yi > lat) != (yj > lat) and \
                           lon < (xj - xi) * (lat - yi) / ((yj - yi) or 1e-12) + xi:
                            ins = not ins
                        j = i
                    if ins:
                        return True
                return False
            hit = tot = 0
            for s2, g2 in sub.groupby('시도'):
                rr = sd.get(s2)
                if not rr:
                    continue
                for v in g2['ll']:
                    tot += 1
                    hit += pip(float(v['lon']), float(v['lat']), rr)
            ok('공장 좌표가 제 시도 경계 안 (85% 이상)', hit / tot >= 0.85,
               f'{hit/tot*100:.1f}% ({hit:,}/{tot:,})')
        else:
            warn('경계 좌표 검증', '지오코딩된 점이 적어 건너뜀')
    if os.path.exists(paths.out('index.html')):
        ok('페이지에 경계 포함', 'id="bnd"' in h and '"sido"' in h)
else:
    warn('시도 경계', 'boundary.json 없음 — python src\\10_boundary.py 실행 필요')

# ---------------------------------------------------------------- 배출량
if os.path.exists(paths.EMISSION):
    em = json.load(open(paths.EMISSION, encoding='utf-8'))
    if not em.get('have'):
        warn('배출량', 'emission/ 폴더에 원본 파일이 없어 붙이지 않았습니다')
    else:
        byname = em.get('byName', {})
        ok('배출량 매칭 결과 있음', len(byname) > 0, f'{len(byname):,}개 회사명')
        # 법인 단위 값이라 한 법인에 여러 공장이 붙는 것은 정상. 값 자체는 양수여야 한다.
        bad = [k for k, v in byname.items() if v.get('e') is not None and v['e'] <= 0]
        ok('배출량에 음수·0 없음', not bad, ', '.join(bad[:3]))
        noval = sum(1 for v in byname.values() if v.get('e') is None)
        ok('값 없는 법인은 소수', noval <= len(byname) * 0.5,
           f'{noval}/{len(byname)}건 (할당대상 명단에만 있거나 0 신고)')
        # 접두 일치 오검출 방지 — 붙은 법인명이 회사명의 실제 접두여야 한다
        import unicodedata as _u
        def compact(x):
            # 법인 표기를 먼저 지운다 — 괄호부터 지우면 '(주)'의 '주'가 남는다
            return re.sub(r'[\s\.\,\-\_\·\(\)\[\]<>/]', '',
                   re.sub(r'\(주\)|㈜|주식회사|유한회사', '', _u.normalize('NFKC', x)))
        odd = [k for k, v in byname.items()
               if v.get('nm') and not compact(k).startswith(compact(v['nm'])[:4])]
        ok('붙은 법인명이 회사명 앞부분과 일치', len(odd) <= len(byname) * 0.05,
           f'{len(odd)}건 / {len(byname)}건: ' + ', '.join(odd[:3]))
        ok('매칭결과 CSV 생성', os.path.exists(paths.out('배출량_매칭결과.csv'))
           or os.path.exists(os.path.join(paths.ROOT, '배출량_매칭결과.csv')),
           '03_emission.py 를 새 폴더에서 한 번 돌리면 생깁니다')

        d2 = json.load(open(paths.DATAJSON, encoding='utf-8'))
        me = d2['meta'].get('emit', {})
        ok('data.json에 배출량 메타 병합', me.get('have') is True)
        nr = sum(1 for f in d2['firms'] if f[13])          # 13 = 규제구분
        ok('규제 구분이 공장에 붙음', nr == me.get('ets', 0) + me.get('mgmt', 0),
           f'{nr}건')
        ok('규제 밖이 대다수', nr < len(d2['firms']) * 0.2,
           f"규제 안 {nr:,} / 전체 {len(d2['firms']):,}")
        if os.path.exists(paths.out('index.html')):
            ok('페이지에 규제 필터 포함', 'id="regf"' in h and 'id="th-e"' in h)
else:
    warn('배출량', 'emission.json 없음 — python src\\03_emission.py 실행 시 검사합니다')

# ---------------------------------------------------------------- 재무
if os.path.exists(paths.FINANCE):
    fi = json.load(open(paths.FINANCE, encoding='utf-8'))
    if not fi.get('have'):
        warn('재무', 'DART 에서 붙은 값이 없습니다')
    else:
        bn = fi.get('byName', {})
        ok('재무 매칭 결과 있음', len(bn) > 0, f'{len(bn):,}개 회사명')
        bad = [k for k, v in bn.items()
               if v.get('sales') is not None and v['sales'] < 0]
        ok('매출액에 음수 없음', not bad, ', '.join(bad[:3]))
        big = [k for k, v in bn.items()
               if (v.get('sales') or 0) > 5e14]      # 500조 넘는 값은 단위 오류
        ok('매출 단위가 원 단위', not big, ', '.join(big[:3]))
        ok('재무 매칭결과 CSV 생성', os.path.exists(paths.out('재무_매칭결과.csv')))
        d3 = json.load(open(paths.DATAJSON, encoding='utf-8'))
        mf = d3['meta'].get('fin', {})
        ok('data.json에 재무 메타 병합', mf.get('have') is True)
        ok('재무가 붙은 행이 전체보다 적음',
           0 < mf.get('rows', 0) < d3['meta']['rows'],
           f"{mf.get('rows',0):,} / {d3['meta']['rows']:,}")
        if os.path.exists(paths.out('index.html')):
            ok('페이지에 매출 열 포함', 'id="th-f"' in h)
else:
    warn('재무', 'finance.json 없음 — python src\\05_finance.py 실행 시 검사합니다')

# ---------------------------------------------------------------- 범위
if os.path.exists(paths.DATAJSON):
    d4 = json.load(open(paths.DATAJSON, encoding='utf-8'))
    sc = d4['meta'].get('scope')
    ok('data.json 범위 표시', sc in ('all', 'target', 'complex', 'national'), str(sc))
    if sc == 'all':
        ok('전국 공장 전부 실림', len(d4['firms']) == d4['meta']['rows'],
           f"{len(d4['firms']):,} / {d4['meta']['rows']:,}")
        # CBAM 도 열공정도 아닌 평범한 공장이 들어 있어야 한다 (예: 디와이파워)
        se = d4['dict']['se'].index('기계·장비') if '기계·장비' in d4['dict']['se'] else -1
        plain = sum(1 for f in d4['firms'] if not f[10] and f[9] == d4['dict']['he'].index('해당없음'))
        ok('규제와 무관한 공장도 포함', plain > 150000, f'{plain:,}건')
    ok('배열 한 줄의 칸 수', all(len(f) == 30 for f in d4['firms'][:1000]),
       str(len(d4['firms'][0])))
    # 품목
    pm = d4['meta'].get('pmBySector', {})
    ok('업종별 품목 목록 있음', len(pm) >= 15, f'{len(pm)}개 업종')
    ok('품목이 사전에 다 있음',
       all(w in d4['dict']['pm'] for ws in pm.values() for w in ws))
    npm = sum(1 for f in d4['firms'] if f[19])
    ok('품목이 붙은 행 비율', 0.15 < npm / len(d4['firms']) < 0.9,
       f"{npm:,} / {len(d4['firms']):,} ({npm/len(d4['firms'])*100:.1f}%)")
    ok('품목은 업종 목록 안에서만 붙음',
       all(d4['dict']['pm'][f[19]] in pm.get(d4['dict']['se'][f[8]], [])
           for f in d4['firms'][:5000] if f[19]))

# ---------------------------------------------------------------- 결과
print()
for n, d in PASS:
    print(f'  PASS  {n}' + (f'  — {d}' if d else ''))
for n, d in WARN:
    print(f'  SKIP  {n}  — {d}')
for n, d in FAIL:
    print(f'  FAIL  {n}' + (f'  — {d}' if d else ''))
print(f'\n통과 {len(PASS)} / 실패 {len(FAIL)} / 건너뜀 {len(WARN)}')
sys.exit(1 if FAIL else 0)
