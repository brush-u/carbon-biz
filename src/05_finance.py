# -*- coding: utf-8 -*-
"""회사 규모(매출·영업이익·자산)를 붙인다 → finance.json

**먼저 알아야 할 한계**
  공장 21만 곳 대부분은 재무제표가 어디에도 공개되지 않습니다. 공시 의무가 없기 때문입니다.
  공개되는 곳은 금융감독원 전자공시(DART)에 정기보고서를 내는 법인 — 상장사와
  일부 대형 비상장사뿐입니다. 그래서 붙는 비율은 낮습니다. 그게 정상입니다.
  나머지 회사의 매출을 알려면 NICE평가정보·한국기업데이터 같은 유료 DB를 사야 합니다.

  덧붙여, 붙는 값은 **법인 단위**입니다. 공장 한 곳의 매출이 아닙니다.

인증키
  https://opendart.fss.or.kr → 인증키 신청 (무료, 이메일 인증, 즉시 발급)
  하루 20,000회까지 호출할 수 있습니다.

실행
  python 10_finance.py --key 발급받은키
  python 10_finance.py --key 발급받은키 --year 2024 --limit 50   (먼저 50건만 시험)

산출물
  finance/corpcode.xml   DART 고유번호 목록 (한 번만 받고 재사용)
  fin_cache.json         법인별 재무 캐시. 중간에 끊어도 이어서 합니다
  finance.json           3_build_data.py 가 읽어 붙입니다
  재무_매칭결과.csv       무엇이 무엇에 붙었는지. 반드시 훑어보십시오
"""
import argparse, json, os, re, sys, time, unicodedata, zipfile, io
import urllib.request, urllib.parse
import xml.etree.ElementTree as ET
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths

DIR = paths.data('finance')
CORP_XML = os.path.join(DIR, 'corpcode.xml')
CACHE = paths.cache('fin_cache.json')
BASE = 'https://opendart.fss.or.kr/api/'

# 8_emission.py 와 같은 규칙. 두 곳이 어긋나면 매칭 결과가 서로 달라진다.
LEGAL = re.compile(r'\(주\)|\(유\)|\(재\)|\(사\)|㈜|㈐|주식회사|유한회사|유한책임회사|'
                   r'합자회사|합명회사|재단법인|사단법인|의료법인|학교법인|주\)|유\)')
SUFFIX = re.compile(r'(제?\d*\s*(공장|사업장|지점|영업소|사업소|제철소|제강소|발전소|'
                    r'센터|캠퍼스|플랜트|단지))+\s*$')
NOISE = re.compile(r'[\s\.\,\-\_\·\(\)\[\]<>/]+')

def norm(s):
    if not isinstance(s, str):
        return '', ''
    s = unicodedata.normalize('NFKC', s)
    s = LEGAL.sub(' ', s)
    s = SUFFIX.sub(' ', s.strip())
    b = NOISE.sub('|', s).strip('|')
    return b.replace('|', ''), b

def get(url, timeout=30):
    req = urllib.request.Request(url, headers={'User-Agent': 'factorymap/1.0'})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()

# ── 1. 고유번호 목록 ───────────────────────────────────────────────────────
def load_corpcode(key):
    if not os.path.exists(CORP_XML):
        os.makedirs(DIR, exist_ok=True)
        print('  DART 고유번호 목록을 받는 중… (약 20MB, 한 번만 받습니다)')
        raw = get(BASE + 'corpCode.xml?crtfc_key=' + urllib.parse.quote(key), timeout=120)
        if raw[:2] != b'PK':          # 오류는 XML/JSON 으로 온다
            sys.exit('  고유번호 목록을 받지 못했습니다. 응답 원문:\n  '
                     + raw[:400].decode('utf-8', 'replace'))
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            name = [n for n in z.namelist() if n.lower().endswith('.xml')][0]
            open(CORP_XML, 'wb').write(z.read(name))
    root = ET.parse(CORP_XML).getroot()
    out = []
    for e in root.iter('list'):
        cc = (e.findtext('corp_code') or '').strip()
        nm = (e.findtext('corp_name') or '').strip()
        if cc and nm:
            out.append((cc, nm, (e.findtext('stock_code') or '').strip()))
    return out

# ── 2. 재무 조회 ───────────────────────────────────────────────────────────
WANT = {
    '매출액': 'sales', '수익(매출액)': 'sales', '영업수익': 'sales',
    '영업이익': 'op', '영업이익(손실)': 'op',
    '당기순이익': 'net', '당기순이익(손실)': 'net',
    '자산총계': 'assets',
}

def to_num(v):
    if v in (None, '', '-'):
        return None
    s = str(v).replace(',', '').strip()
    neg = s.startswith('(') and s.endswith(')')
    s = re.sub(r'[^\d\.\-]', '', s)
    if s in ('', '-', '.'):
        return None
    try:
        n = float(s)
    except ValueError:
        return None
    return -n if neg else n

def fetch_fin(key, corp_code, year, sleep, dump=False):
    url = (BASE + 'fnlttSinglAcnt.json?crtfc_key=' + urllib.parse.quote(key)
           + '&corp_code=' + corp_code + '&bsns_year=' + str(year) + '&reprt_code=11011')
    try:
        raw = get(url)
    except Exception as e:
        return None, 'HTTP ' + str(e)
    time.sleep(sleep)
    try:
        j = json.loads(raw.decode('utf-8'))
    except Exception:
        return None, raw[:200].decode('utf-8', 'replace')
    st = j.get('status')
    if st != '000':
        return None, st + ' ' + str(j.get('message'))[:80]
    out = {}
    for r in j.get('list', []):
        k = WANT.get((r.get('account_nm') or '').strip())
        if not k:
            continue
        n = to_num(r.get('thstrm_amount'))
        if n is None:
            continue
        # 연결(CFS)을 우선하고, 없으면 개별(OFS)
        if k not in out or r.get('fs_div') == 'CFS':
            out[k] = n
    if dump:
        print('  [원문]', raw[:300].decode('utf-8', 'replace'))
    return (out or None), None

# ── 실행 ───────────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--key', required=True, help='OpenDART 인증키 (40자리)')
    ap.add_argument('--year', type=int, default=0, help='사업연도 (기본: 작년)')
    ap.add_argument('--limit', type=int, default=0, help='처음 N개 법인만 (0=전체)')
    ap.add_argument('--max', type=int, default=19000,
                    help='한 번에 최대 몇 건까지 조회할지 (DART 일일 한도 20,000)')
    ap.add_argument('--listed-only', action='store_true',
                    help='상장사만 조회 — 30분 안에 끝나는 1차 시험용')
    ap.add_argument('--sleep', type=float, default=0.08)
    ap.add_argument('--verbose-fails', type=int, default=3)
    a = ap.parse_args()
    year = a.year or (pd.Timestamp.today().year - 1)

    corps = load_corpcode(a.key)
    print(f'  DART 고유번호 {len(corps):,}개')

    # 이름 색인
    bound, byname = {}, {}
    for cc, nm, sc in corps:
        k, kb = norm(nm)
        if len(k) < 2:
            continue
        # 상장사를 우선한다 — 같은 이름이 여럿일 때 재무가 있는 쪽이 낫다
        if k in byname and not sc:
            continue
        bound[k] = kb
        byname[k] = (cc, nm, sc)

    df = pd.read_pickle(paths.CLEAN)
    names = df['회사명'].drop_duplicates()

    # 이름 맞추기 — 법인 11만 개 × 회사명 17만 개를 곱으로 훑으면 170억 번이라
    # 몇 시간이 걸린다. 뒤집어서, **회사명 쪽의 경계 조각**을 열쇠로 찾는다.
    #   '쌍용씨앤이|동해'  →  '쌍용씨앤이' 를 사전에서 찾는다 (조회 3~4번이면 끝)
    bybound = {}
    for k in byname:
        if len(k) >= 3:
            bybound.setdefault(bound[k], k)

    hit = {}
    for n in names:
        k, kb = norm(n)
        if k in byname:
            hit[n] = k
            continue
        parts = kb.split('|')
        for j in range(len(parts) - 1, 0, -1):      # 긴 조각부터
            cand = '|'.join(parts[:j])
            lk = bybound.get(cand)
            if lk:
                hit[n] = lk
                break
    if a.listed_only:
        hit = {n: k for n, k in hit.items() if byname[k][2]}
    corp_keys = sorted(set(hit.values()))
    print(f'  공장 회사명 {len(names):,}개 중 {len(hit):,}개가 DART 법인과 이름이 맞습니다'
          f' (법인 {len(corp_keys):,}개)')

    cache = json.load(open(CACHE, encoding='utf-8')) if os.path.exists(CACHE) else {}
    todo = [k for k in corp_keys if (byname[k][0] + ':' + str(year)) not in cache]
    # 상장사를 앞으로 — 재무가 확실히 있고, 도중에 멈춰도 값진 것부터 채워진다
    todo.sort(key=lambda k: (0 if byname[k][2] else 1, byname[k][1]))
    full = len(todo)
    per = a.sleep + 0.17                      # 대기 + 왕복 시간
    print(f'  조회할 법인 {full:,}개 · 전부 돌리면 약 {full*per/60:.0f}분'
          f' (건당 {per:.2f}초, 캐시 {len(corp_keys)-full:,}건은 재사용)')
    if a.limit:
        todo = todo[:a.limit]
    if len(todo) > a.max:
        print(f'  조회 대상이 {len(todo):,}건이라 이번에는 {a.max:,}건만 합니다'
              f' (DART 일일 한도 20,000회). 내일 다시 실행하면 이어서 합니다.')
        todo = todo[:a.max]
    print(f'  이번 회차 {len(todo):,}건 · {year}년 사업보고서'
          f' · 약 {len(todo)*per/60:.0f}분. 중간에 끊어도 이어서 합니다.')

    t0, okc, failc, shown = time.time(), 0, 0, 0
    for i, k in enumerate(todo, 1):
        cc, nm, sc = byname[k]
        fin, err = fetch_fin(a.key, cc, year, a.sleep)
        cache[cc + ':' + str(year)] = fin or {}
        if fin:
            okc += 1
        else:
            failc += 1
            if shown < a.verbose_fails and err and not err.startswith('013'):
                print(f'    [실패] {nm} → {err}'); shown += 1
        if i % 100 == 0 or i == len(todo):
            json.dump(cache, open(CACHE, 'w', encoding='utf-8'), ensure_ascii=False)
            print(f'   {i:>6,}/{len(todo):,}  확보 {okc:,}  없음 {failc:,}  {time.time()-t0:.0f}s')
        if err and err.startswith('020'):
            print('  일일 호출 한도에 걸렸습니다. 내일 다시 실행하면 이어서 합니다.')
            break
    json.dump(cache, open(CACHE, 'w', encoding='utf-8'), ensure_ascii=False)

    # ── 산출 ──
    out, rows = {}, []
    for n, k in hit.items():
        cc, nm, sc = byname[k]
        fin = cache.get(cc + ':' + str(year)) or {}
        if not fin:
            continue
        out[n] = {'nm': nm, 'sc': sc, 'y': year,
                  'sales': fin.get('sales'), 'op': fin.get('op'),
                  'assets': fin.get('assets')}
        rows.append([n, nm, sc, fin.get('sales'), fin.get('op'), fin.get('assets')])
    pd.DataFrame(rows, columns=['회사명', 'DART 법인명', '종목코드', '매출액', '영업이익', '자산총계']) \
      .sort_values('매출액', ascending=False) \
      .to_csv(paths.out('재무_매칭결과.csv'), index=False, encoding='utf-8-sig')

    json.dump({'have': bool(out), 'year': year, 'src': 'DART OpenAPI 단일회사 주요계정',
               'n': {'corp': len(corps), 'match': len(hit), 'fin': len(out)},
               'byName': out},
              open(paths.FINANCE, 'w', encoding='utf-8'),
              ensure_ascii=False, separators=(',', ':'))
    print(f'\nfinance.json  회사명 {len(out):,}개에 재무가 붙었습니다'
          f' (공장 회사명 {len(names):,}개 대비 {len(out)/len(names)*100:.1f}%)')
    print('  → 재무_매칭결과.csv 를 열어 엉뚱하게 붙은 것이 없는지 보십시오')
    print('이어서  python 3_build_data.py  →  python 4_make_page.py')

if __name__ == '__main__':
    main()
