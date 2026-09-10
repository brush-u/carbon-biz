# -*- coding: utf-8 -*-
"""수출기업 명단 붙이기 → EU 수출 가능성 표시

**솔직하게 — 개별 기업의 수출실적은 공개되지 않습니다.**
  관세청도 무역협회도 기업별 수출액은 비공개입니다. CBAM 영업에서 가장 결정적인
  변수인데 정면으로 구할 방법이 없습니다. 그래서 **"수출을 하는 것으로 알려진 기업
  명단"** 을 여러 개 모아 겹치는지만 봅니다. 있으면 유력, 없어도 아닐 수 있습니다.

넣을 수 있는 명단 (구할 수 있는 것만 넣으면 됩니다)
  · 한국무역협회 회원사 명부      https://www.kita.net  (회원 대상)
  · KOTRA 수출유망중소기업 지정   https://www.kotra.or.kr
  · 수출바우처 참여기업           https://www.exportvoucher.com
  · 중소벤처기업진흥공단 수출지원 참여기업
  · 지자체·업종조합의 수출기업 명부
  · 사내에서 이미 가진 거래처·잠재고객 목록도 넣으십시오

넣는 법
  회사명 컬럼이 있는 CSV·XLSX 를 data\\export\\ 폴더에 그대로 넣습니다.
  파일 이름이 그대로 출처 이름이 되니 알아보기 쉽게 두십시오.
  (예: KOTRA_수출유망중소기업_2025.csv, 무역협회_회원사.xlsx)

산출물
  cache\\export.json         08_build.py 가 읽어 붙입니다
  out\\수출명단_매칭결과.csv
"""
import os, sys, json, glob
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths
from lib_match import Index, norm

SRC_DIR = paths.data('export')

NAME_HINTS = ('업체명', '기업명', '회사명', '법인명', '상호', '사업장명', '수출기업', '업체')

def read_any(path):
    low = path.lower()
    if low.endswith(('.xlsx', '.xlsm')):
        return pd.read_excel(path, dtype=str)
    if low.endswith('.xls'):
        try:
            return pd.read_excel(path, dtype=str, engine='xlrd')
        except Exception:
            pass
    for enc in ('utf-8-sig', 'cp949', 'euc-kr'):
        try:
            return pd.read_csv(path, encoding=enc, dtype=str)
        except (UnicodeDecodeError, pd.errors.ParserError):
            continue
    return pd.read_csv(path, encoding='utf-8', engine='python', dtype=str)

def name_col(d):
    for c in d.columns:
        t = str(c).replace(' ', '')
        if any(h in t for h in NAME_HINTS) and len(t) <= 14:
            return c
    # 헤더가 없으면 한글이 가장 많이 든 열을 상호로 본다
    best, bn = None, -1
    for c in d.columns:
        v = d[c].dropna().astype(str).head(200)
        n = sum(1 for x in v if any('가' <= ch <= '힣' for ch in x))
        if n > bn:
            best, bn = c, n
    return best

def main():
    files = sorted(sum([glob.glob(os.path.join(SRC_DIR, e))
                        for e in ('*.csv', '*.xlsx', '*.xls', '*.xlsm')], []))
    if not files:
        print('data\\export\\ 에 파일이 없습니다. 수출기업 명단을 넣으면 붙입니다.')
        print('  회사명 컬럼이 있는 CSV·XLSX 면 무엇이든 됩니다. 파일명이 출처가 됩니다.')
        json.dump({'have': False}, open(paths.EXPORT, 'w', encoding='utf-8'),
                  ensure_ascii=False)
        return

    idx = Index()
    src_names = []
    for f in files:
        label = os.path.splitext(os.path.basename(f))[0]
        d = read_any(f)
        c = name_col(d)
        if not c:
            print(f'  ! {label} — 회사명 컬럼을 찾지 못했습니다. 컬럼: {list(d.columns)[:10]}')
            continue
        n = 0
        for v in d[c].dropna().astype(str):
            v = v.strip()
            if len(v) < 2:
                continue
            k, _ = norm(v)
            prev = idx.exact.get(k)
            if prev:
                if label not in prev['src']:
                    prev['src'].append(label)
            else:
                idx.add(v, {'nm': v, 'src': [label]})
            n += 1
        src_names.append(label)
        print(f'  {label}  (컬럼 {c})  {n:,}건')

    paths.need(paths.CLEAN, 'python src\\01_prep.py 를 먼저 돌리십시오')
    df = pd.read_pickle(paths.CLEAN)
    out, rows = {}, []
    for nm in df['회사명'].drop_duplicates():
        rec, _k, mode = idx.find(nm)
        if rec:
            out[nm] = {'nm': rec['nm'], 'src': rec['src'], 'how': mode}
            rows.append([nm, rec['nm'], ' / '.join(rec['src']), mode])

    uniq = df['회사명'].nunique()
    print(f'\n공장 회사명 {uniq:,}개 중 {len(out):,}개가 수출기업 명단에 있습니다 '
          f'({len(out)/uniq*100:.1f}%)')
    pd.DataFrame(rows, columns=['회사명', '명단상 이름', '출처', '매칭방식']) \
      .to_csv(paths.out('수출명단_매칭결과.csv'), index=False, encoding='utf-8-sig')

    json.dump({'have': bool(out), 'src': src_names,
               'n': {'match': len(out)}, 'byName': out},
              open(paths.EXPORT, 'w', encoding='utf-8'),
              ensure_ascii=False, separators=(',', ':'))
    print('  → out\\수출명단_매칭결과.csv')
    print('  이 표시는 "수출을 한다고 알려진 곳"이지 "EU에 CBAM 품목을 수출한다"가 아닙니다.')
    print('이어서  python src\\08_build.py  →  python src\\09_page.py')

if __name__ == '__main__':
    main()
