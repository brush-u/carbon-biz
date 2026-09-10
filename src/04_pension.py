# -*- coding: utf-8 -*-
"""국민연금 사업장 데이터 → 종업원수·인건비 규모·성장 신호

**이게 왜 중요한가**
  영업 리스트를 고를 때 제일 먼저 알아야 할 것이 "이 회사가 얼마나 큰가"다.
  그런데 매출은 DART 공시 법인(상장사 위주)만 공개돼 몇 %밖에 안 붙는다.
  국민연금은 **법인 3인 이상 · 개인 10인 이상 사업장이 거의 다** 들어 있어
  훨씬 넓게 붙고, 게다가 **법인이 아니라 사업장(공장) 단위**라 우리 데이터와 결이 맞다.

붙는 것
  가입자수       → 종업원수. 중소/중견 판정과 규모별 우선순위
  당월고지금액   → 인건비 규모. 매출 대리지표 (연금 보험료율 9%, 노사 절반씩)
  신규취득/상실  → 사람이 늘고 있나 줄고 있나. 성장·축소 신호
  업종코드(KSIC) → 우리가 생산품 텍스트로 추정한 업종을 검증할 수 있다

내려받기
  https://www.data.go.kr/data/15083277/fileData.do
  「국민연금공단_국민연금 가입 사업장 내역」 · 월 단위 갱신 · CSV
  받은 파일을 data\\pension\\ 폴더에 그대로 넣으십시오.

산출물
  cache\\pension.json      08_build.py 가 읽어 붙입니다
  out\\국민연금_매칭결과.csv  무엇이 무엇에 붙었는지. 반드시 훑어보십시오
"""
import os, sys, json, glob, re
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths
from lib_match import Index, norm, addr_key

SRC_DIR = paths.data('pension')

def pick(cols, *groups):
    for c in cols:
        t = str(c).replace(' ', '')
        if all(any(k in t for k in g) for g in groups):
            return c
    return None

def read_any(path):
    """이 파일은 cp949 CSV 로 오는 경우가 많다. 인코딩을 차례로 시도한다."""
    for enc in ('cp949', 'utf-8-sig', 'euc-kr', 'utf-8'):
        try:
            return pd.read_csv(path, encoding=enc, dtype=str, low_memory=False)
        except UnicodeDecodeError:
            continue
    return pd.read_csv(path, encoding='utf-8', errors='replace', dtype=str, low_memory=False)

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

def main():
    files = sorted(glob.glob(os.path.join(SRC_DIR, '*.csv')) +
                   glob.glob(os.path.join(SRC_DIR, '*.CSV')))
    if not files:
        print('data\\pension\\ 에 파일이 없습니다.')
        print('  https://www.data.go.kr/data/15083277/fileData.do 에서 받아 넣으십시오.')
        json.dump({'have': False}, open(paths.PENSION, 'w', encoding='utf-8'),
                  ensure_ascii=False)
        return

    frames = []
    for f in files:
        d = read_any(f)
        print(f'  {os.path.basename(f)}  {len(d):,}행 · {len(d.columns)}열')
        frames.append(d)
    d = pd.concat(frames, ignore_index=True) if len(frames) > 1 else frames[0]

    c_nm = pick(d.columns, ('사업장', '업체', '회사'), ('명',)) or pick(d.columns, ('사업장',))
    c_ad = (pick(d.columns, ('도로명',), ('주소',)) or pick(d.columns, ('주소',))
            or pick(d.columns, ('소재',)))
    c_cnt = pick(d.columns, ('가입자',), ('수',)) or pick(d.columns, ('가입자',))
    c_amt = pick(d.columns, ('고지',), ('금액',)) or pick(d.columns, ('고지',))
    c_in = pick(d.columns, ('신규',))
    c_out = pick(d.columns, ('상실',))
    c_ksic = pick(d.columns, ('업종',), ('명',)) or pick(d.columns, ('업종',))
    c_biz = pick(d.columns, ('사업자',), ('번호',))
    print(f'  컬럼 — 사업장명={c_nm} 주소={c_ad} 가입자수={c_cnt} 고지금액={c_amt} '
          f'신규={c_in} 상실={c_out} 업종={c_ksic}')
    if not c_nm or not c_cnt:
        sys.exit(f'  사업장명/가입자수 컬럼을 찾지 못했습니다. 실제 컬럼: {list(d.columns)[:20]}')

    # ── 색인 두 벌 ─────────────────────────────────────────────────────────
    # 이름만으로는 같은 상호가 전국에 여럿이라 엉뚱한 곳에 붙는다.
    # 그래서 '이름+주소열쇠'를 1순위로, 이름만은 2순위로 둔다.
    by_na, by_n = {}, Index()
    cols = {c: d.columns.get_loc(c) for c in
            [x for x in (c_nm, c_ad, c_cnt, c_amt, c_in, c_out, c_ksic, c_biz) if x]}
    def cell(row, c):
        return row[cols[c]] if c else None

    for row in d.itertuples(index=False, name=None):
        nm = cell(row, c_nm)
        cnt = num(cell(row, c_cnt))
        if not isinstance(nm, str) or cnt is None:
            continue
        rec = {'nm': nm.strip(), 'cnt': int(cnt),
               'amt': int(num(cell(row, c_amt)) or 0),
               'in': int(num(cell(row, c_in)) or 0),
               'out': int(num(cell(row, c_out)) or 0),
               'ksic': str(cell(row, c_ksic) or '').strip(),
               'biz': str(cell(row, c_biz) or '').strip()}
        k, _ = norm(nm)
        if not k:
            continue
        ad = addr_key(cell(row, c_ad)) if c_ad else ''
        if ad:
            key = k + '@' + ad
            # 같은 이름+주소가 여럿이면 사람이 많은 쪽을 남긴다 (본사 사업장)
            if key not in by_na or by_na[key]['cnt'] < rec['cnt']:
                by_na[key] = rec
        # 이름 색인도 사람 많은 쪽을 남긴다 — 동명이인이면 큰 곳이 맞을 확률이 높다
        prev = by_n.exact.get(k)
        by_n.add(nm, rec, prefer=(prev is None or prev['cnt'] < rec['cnt']))

    print(f'  사업장 {len(d):,}건 → 이름+주소 색인 {len(by_na):,} · 이름 색인 {len(by_n.exact):,}')

    # ── 공장 목록과 대조 ───────────────────────────────────────────────────
    paths.need(paths.CLEAN, 'python src\\01_prep.py 를 먼저 돌리십시오')
    f = pd.read_pickle(paths.CLEAN)
    out, rows = {}, []
    n_ad = n_nm = 0
    for nm, ad in zip(f['회사명'], f['공장주소']):
        if nm in out:
            continue
        k, _ = norm(nm)
        akey = addr_key(ad)
        rec, how = None, ''
        if k and akey:
            rec = by_na.get(k + '@' + akey)
            if rec:
                how = '이름+주소'; n_ad += 1
        if rec is None:
            rec, _hit, mode = by_n.find(nm)
            if rec:
                how = '이름(' + mode + ')'; n_nm += 1
        if rec:
            out[nm] = {'nm': rec['nm'], 'cnt': rec['cnt'], 'amt': rec['amt'],
                       'in': rec['in'], 'out': rec['out'], 'ksic': rec['ksic'],
                       'how': how}
            rows.append([nm, rec['nm'], how, rec['cnt'], rec['amt'],
                         rec['in'], rec['out'], rec['ksic']])

    uniq = f['회사명'].nunique()
    print(f'\n공장 회사명 {uniq:,}개 중 {len(out):,}개에 붙었습니다 '
          f'({len(out)/uniq*100:.1f}%)')
    print(f'  이름+주소로 맞은 것 {n_ad:,} · 이름만으로 맞은 것 {n_nm:,}')
    print('  이름만 맞은 것은 동명이인 위험이 있습니다. CSV 에서 확인하십시오.')

    pd.DataFrame(rows, columns=['회사명', '국민연금 사업장명', '매칭방식', '가입자수',
                                '당월고지금액', '신규취득', '상실', '업종(KSIC)']) \
      .sort_values('가입자수', ascending=False) \
      .to_csv(paths.out('국민연금_매칭결과.csv'), index=False, encoding='utf-8-sig')

    json.dump({'have': True, 'src': [os.path.basename(x) for x in files],
               'n': {'rows': int(len(d)), 'match': len(out), 'byAddr': n_ad, 'byName': n_nm},
               'byName': out},
              open(paths.PENSION, 'w', encoding='utf-8'),
              ensure_ascii=False, separators=(',', ':'))
    print(f'\ncache\\pension.json  {os.path.getsize(paths.PENSION)/1e6:.1f} MB')
    print('  → out\\국민연금_매칭결과.csv 를 열어 30줄쯤 눈으로 보십시오')
    print('이어서  python src\\08_build.py  →  python src\\09_page.py')

if __name__ == '__main__':
    main()
