# -*- coding: utf-8 -*-
"""Google My Maps 가져오기용 CSV 생성

My Maps는 파일당 2,000행이 상한이고 지도 하나에 레이어 10개까지 올릴 수 있다.
주소 열이 있으면 My Maps가 알아서 위치를 찍으므로 좌표가 없어도 된다.

산출물은 mymaps/ 폴더에 들어간다.
  00_산단공_거점.csv        본사 + 지역본부 13곳
  01_국가산업단지.csv        국가산단 (도드라지게 표시할 대상)
  02_주요_일반산업단지.csv    입주업체 수 상위 일반산업단지
  03_농공단지.csv            농공단지
  업종별/<업종>_01.csv …     업종별 공장 목록 (1,900행씩 분할)
  MANIFEST.csv               파일 목록과 행 수

사용법
    python 5_mymaps.py                  # 기본 패키지
    python 5_mymaps.py --sector 식품·음료 --limit 1900
    python 5_mymaps.py --heat 용해·소성
    python 5_mymaps.py --cbam
"""
import argparse, os, re
import pandas as pd

CHUNK = 1900        # My Maps 상한 2,000행에 여유를 둔다
OUT = 'mymaps'

# 한국산업단지공단 본사·지역본부 (출처: 공단 위치안내)
# 2026-07 광주·전남이 전남광주통합특별시로 통합됐으나, 지오코딩 안정성을 위해
# 도로명주소는 통합 이전 시도명으로 적고 비고에 통합 사실을 남긴다.
KICOX = [
    ('본사',         '대구광역시 동구 첨단로 39', '전국 총괄'),
    ('서울지역본부', '서울특별시 구로구 디지털로26길 38', '서울'),
    ('인천지역본부', '인천광역시 남동구 남동대로 217', '인천'),
    ('경기지역본부', '경기도 안산시 단원구 동산로 57', '경기 (반월·시화)'),
    ('경북지역본부', '경상북도 구미시 수출대로 127', '경북 (구미)'),
    ('대구지역본부', '대구광역시 달서구 성서공단로 217', '대구 (성서)'),
    ('광주지역본부', '광주광역시 북구 첨단과기로 313', '광주 · 2026.7 전남광주통합특별시'),
    ('전남지역본부', '전라남도 여수시 삼동3길 13', '전남 (여수) · 2026.7 전남광주통합특별시'),
    ('경남지역본부', '경상남도 창원시 성산구 창원대로 754', '경남 (창원)'),
    ('충청지역본부', '충청남도 천안시 서북구 3공단2로 90-27', '충청'),
    ('전북지역본부', '전북특별자치도 군산시 산단남북로 169', '전북 (군산)'),
    ('부산지역본부', '부산광역시 강서구 녹산산단335로 5', '부산 (녹산)'),
    ('울산지역본부', '울산광역시 남구 정동로 83', '울산'),
    ('강원지역본부', '강원특별자치도 원주시 흥업면 남원로 150', '강원'),
]

def safe(s):
    return re.sub(r'[\\/:*?"<>|·]', '_', str(s)).strip()

def write(df, path, manifest, note=''):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    df.to_csv(path, index=False, encoding='utf-8-sig')
    manifest.append({'파일': os.path.relpath(path, OUT), '행수': len(df), '설명': note})
    print(f"  {os.path.relpath(path, OUT):<44} {len(df):>6}행")

def chunked(df, base, manifest, note=''):
    if len(df) <= CHUNK:
        write(df, base + '.csv', manifest, note)
        return
    n = (len(df) - 1) // CHUNK + 1
    for i in range(n):
        write(df.iloc[i*CHUNK:(i+1)*CHUNK], f'{base}_{i+1:02d}.csv', manifest,
              f'{note} ({i+1}/{n})')

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--sector', help='특정 업종만')
    ap.add_argument('--heat', help='열공정 구분만 (용해·소성 / 건조·증기)')
    ap.add_argument('--cbam', action='store_true', help='CBAM 대상만')
    ap.add_argument('--all-sectors', action='store_true', help='전 업종 내보내기 (파일 많음)')
    args = ap.parse_args()

    df = pd.read_pickle('clean.pkl')
    # 주소가 비어 있으면 My Maps가 위치를 찍지 못한다. 조용히 사라지면
    # 나중에 건수가 안 맞는 원인을 찾기 어려우므로 여기서 걸러내고 알린다.
    blank = (df['공장주소'].str.strip() == '').sum()
    if blank:
        print(f'주소가 빈 {blank:,}건은 제외합니다 (My Maps가 위치를 찍지 못함)')
        df = df[df['공장주소'].str.strip() != '']
    os.makedirs(OUT, exist_ok=True)
    man = []

    print('거점·단지 레이어')
    write(pd.DataFrame(KICOX, columns=['이름', '주소', '관할']).assign(구분='산단공 거점'),
          f'{OUT}/00_산단공_거점.csv', man, '본사 + 지역본부 13곳')

    cx = (df[df['입지'] == '산업단지']
          .groupby(['단지', '단지유형'])
          .agg(입주업체수=('회사명', 'size'),
               시도=('시도', lambda s: s.mode().iloc[0] if len(s.mode()) else ''),
               시군구=('시군구', lambda s: s.mode().iloc[0] if len(s.mode()) else ''))
          .reset_index().sort_values('입주업체수', ascending=False))
    # My Maps가 장소명으로 찾을 수 있게 '단지명 + 시군구' 형태를 위치 열로 준다
    cx['검색주소'] = cx['시도'] + ' ' + cx['시군구'] + ' ' + cx['단지']
    cx = cx.rename(columns={'단지': '이름'})[
        ['이름', '검색주소', '단지유형', '입주업체수', '시도', '시군구']]

    write(cx[cx['단지유형'] == '국가산업단지'], f'{OUT}/01_국가산업단지.csv', man, '국가산단 전체')
    gen = cx[cx['단지유형'] == '일반산업단지']
    write(gen.head(300), f'{OUT}/02_주요_일반산업단지.csv', man, '입주업체 수 상위 300')
    write(cx[cx['단지유형'] == '농공단지'].head(500), f'{OUT}/03_농공단지.csv', man, '상위 500')
    write(cx[cx['단지유형'].isin(['도시첨단산업단지', '자유무역지역', '외국인투자지역'])],
          f'{OUT}/04_도시첨단_자유무역_외투.csv', man, '특수 유형 단지')

    # 공장 레이어
    base = df.copy()
    tag = '업종별'
    if args.cbam:
        base = base[base['CBAM'] != '']; tag = 'CBAM'
    if args.heat:
        base = base[base['열공정'] == args.heat]; tag = safe(args.heat)
    if args.sector:
        base = base[base['업종'] == args.sector]; tag = safe(args.sector)

    cols = ['회사명', '공장주소', '생산품', '업종', '열공정', 'CBAM', '단지', '단지유형', '시도', '시군구']
    ren = {'회사명': '이름', '공장주소': '주소'}

    if args.sector or args.heat or args.cbam:
        print(f'\n공장 레이어 — {tag}')
        chunked(base[cols].rename(columns=ren), f'{OUT}/{tag}', man, tag)
    else:
        print('\n공장 레이어 — 타깃 (CBAM 또는 열공정 보유)')
        t = base[(base['CBAM'] != '') | (base['열공정'] != '해당없음')]
        chunked(t[cols].rename(columns=ren), f'{OUT}/10_타깃_전체', man, 'CBAM 또는 열공정')
        for h in ['용해·소성', '건조·증기']:
            sub = base[base['열공정'] == h]
            chunked(sub[cols].rename(columns=ren), f'{OUT}/열공정/{safe(h)}', man, f'열공정 {h}')
        if args.all_sectors:
            print('\n업종별')
            for s in base['업종'].value_counts().index:
                sub = base[base['업종'] == s]
                chunked(sub[cols].rename(columns=ren), f'{OUT}/업종별/{safe(s)}', man, f'업종 {s}')

    pd.DataFrame(man).to_csv(f'{OUT}/MANIFEST.csv', index=False, encoding='utf-8-sig')
    print(f'\n{OUT}/ 폴더에 {len(man)}개 파일. MANIFEST.csv 참고')
    print('My Maps 한 지도에 레이어 10개까지 — 필요한 파일만 골라 올리세요.')

if __name__ == '__main__':
    main()
