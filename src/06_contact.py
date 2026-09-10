# -*- coding: utf-8 -*-
"""회사명·주소로 전화번호와 홈페이지 찾기 (카카오 로컬 API)

**왜 카카오인가**
  공개 데이터에는 공장 연락처가 없다. 웹을 긁는 방법도 있지만 느리고 불안정하다.
  카카오 로컬 '키워드로 장소 검색' 은 상호로 찾으면 **전화번호 · 도로명주소 ·
  장소 상세페이지 · 좌표**를 한 번에 준다. 무료이고 한도가 넉넉하다.

**정확도를 어떻게 담보하나**
  상호만으로 찾으면 전국의 동명 업체가 딸려온다. 그래서 검색 결과마다
  **우리가 아는 주소와 얼마나 겹치는지**를 보고 등급을 매긴다.

    확실   도로명 본번까지 일치           → 그대로 써도 되는 번호
    보통   같은 시군구 + 상호 일치        → 전화 걸기 전 한 번 확인
    낮음   상호만 일치                    → 참고용. 영업에 바로 쓰지 말 것

  등급을 화면과 CSV에 그대로 남긴다. **'확실'이 아닌 번호로 전화를 돌리면
  엉뚱한 회사에 겁니다.**

인증키
  https://developers.kakao.com → 내 애플리케이션 → 앱 만들기
  → 앱 키의 **REST API 키** 를 씁니다. (카카오 로그인 설정은 필요 없습니다)
  한도는 개발자 콘솔의 쿼터 화면에서 확인하십시오.

실행
  python src\\06_contact.py --key REST키 --limit 30          먼저 30건 시험
  python src\\06_contact.py --key REST키 --scope target      CBAM·열공정 (약 8,000곳)
  python src\\06_contact.py --key REST키 --scope complex     산업단지 전체

산출물
  cache\\contact.json        08_build.py 가 읽어 붙입니다
  out\\연락처_수집결과.csv    등급별로 확인하십시오
"""
import argparse, json, os, sys, time, re
import urllib.parse, urllib.request, urllib.error
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths
from lib_match import norm, addr_key

API = 'https://dapi.kakao.com/v2/local/search/keyword.json'
NAVER = 'https://openapi.naver.com/v1/search/local.json'


def naver(cid, csec, query, sleep):
    """네이버 지역 검색. 상호·도로명주소·업종·좌표·플레이스 링크를 준다.

    **전화번호는 못 가져옵니다.** 네이버 공개 API 의 telephone 항목은 빈 문자열로
    내려옵니다. 네이버 지도 화면에 보이는 번호는 공개 API 로 제공되지 않습니다.
    그래서 여기서는 네이버를 '번호를 가져오는 곳'이 아니라
    **'카카오가 찾은 장소가 맞는지 확인해 주는 두 번째 눈'** 으로 씁니다.
    한도 하루 25,000회, 한 번에 최대 5건.
    """
    url = NAVER + '?' + urllib.parse.urlencode({'query': query, 'display': 5})
    req = urllib.request.Request(url, headers={
        'X-Naver-Client-Id': cid, 'X-Naver-Client-Secret': csec})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            body = r.read()
    except urllib.error.HTTPError as e:
        return None, f'HTTP {e.code} ' + e.read()[:160].decode('utf-8', 'replace')
    except Exception as e:
        return None, type(e).__name__ + ' ' + str(e)[:80]
    finally:
        time.sleep(sleep)
    try:
        return json.loads(body.decode('utf-8')).get('items', []), None
    except Exception:
        return None, body[:160].decode('utf-8', 'replace')


TAG = re.compile(r'<[^>]+>')

def search(key, query, sleep):
    url = API + '?' + urllib.parse.urlencode({'query': query, 'size': 15})
    req = urllib.request.Request(url, headers={'Authorization': 'KakaoAK ' + key})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            body = r.read()
    except urllib.error.HTTPError as e:
        return None, f'HTTP {e.code} ' + e.read()[:160].decode('utf-8', 'replace')
    except Exception as e:
        return None, type(e).__name__ + ' ' + str(e)[:80]
    finally:
        time.sleep(sleep)
    try:
        return json.loads(body.decode('utf-8')).get('documents', []), None
    except Exception:
        return None, body[:160].decode('utf-8', 'replace')

SGG = re.compile(r'([가-힣]+[시군구])')

def grade(doc, want_addr, want_sgg):
    """검색 결과 한 건이 우리가 찾는 공장인지 등급을 매긴다."""
    got = addr_key(doc.get('road_address_name') or doc.get('address_name') or '')
    if got and want_addr and got == want_addr:
        return '확실'
    both = (doc.get('road_address_name') or '') + ' ' + (doc.get('address_name') or '')
    if want_sgg and want_sgg in both:
        return '보통'
    return '낮음'

def read_key(name, n):
    """작업 폴더의 키 파일에서 값을 읽는다. 없으면 빈 값 n개."""
    f = os.path.join(paths.ROOT, name)
    if not os.path.exists(f):
        return [''] * n
    lines = [x.strip() for x in open(f, encoding='utf-8') if x.strip()
             and not x.strip().startswith('#')]
    return (lines + [''] * n)[:n]


RANK = {'두곳확인': 4, '확실': 3, '보통': 2, '낮음': 1, '불일치': 0}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--key', default='', help='카카오 REST API 키 (없으면 .kakao_key 파일)')
    ap.add_argument('--naver-id', default='', help='네이버 Client ID (교차 확인용, 선택)')
    ap.add_argument('--naver-secret', default='', help='네이버 Client Secret')
    ap.add_argument('--scope', default='target',
                    choices=['target', 'complex', 'cbam', 'all'],
                    help='target=CBAM·열공정 / complex=산업단지 전체 / cbam=CBAM만 / all=전부')
    ap.add_argument('--limit', type=int, default=0, help='처음 N곳만 (0=전체)')
    ap.add_argument('--max-calls', type=int, default=0, help='이번 회차 호출 상한 (0=무제한)')
    ap.add_argument('--sleep', type=float, default=0.05)
    ap.add_argument('--min-grade', default='낮음', choices=['확실', '보통', '낮음'],
                    help='이 등급 미만이면 저장하지 않는다')
    a = ap.parse_args()

    # 키를 명령창에 매번 치지 않아도 되게, 폴더의 키 파일에서도 읽는다.
    #   .kakao_key   한 줄에 REST API 키
    #   .naver_key   첫 줄 Client ID, 둘째 줄 Client Secret
    # 둘 다 .gitignore 에 있어 git 에 올라가지 않는다.
    if not a.key:
        a.key = read_key('.kakao_key', 1)[0]
    if not (a.naver_id and a.naver_secret):
        nv = read_key('.naver_key', 2)
        a.naver_id = a.naver_id or nv[0]
        a.naver_secret = a.naver_secret or nv[1]
    if not a.key:
        sys.exit('카카오 REST API 키가 없습니다.\n'
                 '  --key 로 넘기거나, D:\\workspace\\carbon-biz\\.kakao_key 파일에 키만 한 줄 적으십시오.\n'
                 '  키는 https://developers.kakao.com → 내 애플리케이션 → 앱 › 플랫폼 키 › REST API 키')

    paths.need(paths.CLEAN, 'python src\\01_prep.py 를 먼저 돌리십시오')
    df = pd.read_pickle(paths.CLEAN)
    if a.scope == 'target':
        df = df[(df['CBAM'] != '') | (df['열공정'] != '해당없음')]
    elif a.scope == 'cbam':
        df = df[df['CBAM'] != '']
    elif a.scope == 'complex':
        df = df[df['입지'] == '산업단지']

    # 같은 회사명+주소는 한 번만 찾는다
    tg = (df[['회사명', '공장주소', '시군구', '시도']]
          .drop_duplicates('회사명').reset_index(drop=True))
    use_nv = bool(a.naver_id and a.naver_secret)
    print(f'범위 {a.scope} — 회사 {len(tg):,}곳'
          + ('  · 네이버 교차 확인 켬' if use_nv else ''))
    if use_nv:
        print('  네이버는 전화번호를 주지 않습니다 (공개 API 의 telephone 은 빈 값).')
        print('  카카오가 찾은 장소가 맞는지 주소로 확인하는 용도로만 씁니다.')

    cache = json.load(open(paths.CONTACT, encoding='utf-8')) if os.path.exists(paths.CONTACT) else {}
    store = cache.get('byName', {}) if isinstance(cache, dict) else {}

    todo = [i for i in range(len(tg)) if tg['회사명'][i] not in store]
    if a.limit:
        todo = todo[:a.limit]
    per = a.sleep + 0.13
    print(f'  아직 안 찾은 곳 {len(todo):,} · 예상 {len(todo)*per/60:.0f}분'
          f' (이미 찾은 곳 {len(store):,}건은 건너뜁니다)')

    calls = 0
    hits = {'두곳확인': 0, '확실': 0, '보통': 0, '낮음': 0, '불일치': 0}
    none = 0
    t0 = time.time()
    stop = ''

    def save():
        json.dump({'have': bool(store), 'src': '카카오 로컬 키워드 장소 검색',
                   'byName': store},
                  open(paths.CONTACT, 'w', encoding='utf-8'),
                  ensure_ascii=False, separators=(',', ':'))

    try:
        for n, i in enumerate(todo, 1):
            nm = tg['회사명'][i]
            addr = tg['공장주소'][i]
            sgg = tg['시군구'][i] if tg['시군구'][i] != '미상' else ''
            want = addr_key(addr)

            q = nm if not sgg else f'{sgg} {nm}'
            docs, err = search(a.key, q, a.sleep)
            calls += 1
            if err:
                if 'HTTP 429' in err or 'quota' in err.lower():
                    stop = '호출 한도에 걸렸습니다. ' + err
                    break
                if 'HTTP 401' in err or 'HTTP 403' in err:
                    stop = '인증키가 거부됐습니다. REST API 키가 맞는지 확인하십시오. ' + err
                    break
                docs = []

            best, bg = None, ''
            for dnode in (docs or []):
                g = grade(dnode, want, sgg)
                if best is None or RANK[g] > RANK[bg]:
                    best, bg = dnode, g
                if bg == '확실':
                    break

            if best and RANK[bg] >= RANK[a.min_grade] and (best.get('phone') or best.get('place_url')):
                rec = {
                    'tel': (best.get('phone') or '').strip(),
                    'url': best.get('place_url') or '',
                    'pnm': best.get('place_name') or '',
                    'padr': best.get('road_address_name') or best.get('address_name') or '',
                    'g': bg,
                    'y': float(best['y']) if best.get('y') else 0,
                    'x': float(best['x']) if best.get('x') else 0,
                }
                # ── 네이버로 한 번 더 확인 ────────────────────────────────
                # 카카오가 집어온 장소의 도로명주소를, 네이버가 같은 상호로 내놓는
                # 주소와 맞춰 본다. 둘이 같으면 그 번호는 믿어도 된다.
                # 서로 다르면 둘 중 하나가 동명 업체다 — 그 사실을 남긴다.
                if use_nv:
                    items, nerr = naver(a.naver_id, a.naver_secret, q, a.sleep)
                    calls += 1
                    if nerr and ('HTTP 401' in nerr or 'HTTP 403' in nerr):
                        stop = '네이버 인증이 거부됐습니다. ' + nerr
                        use_nv = False
                    elif nerr and 'HTTP 429' in nerr:
                        print('  네이버 한도 초과 — 이후는 카카오만 씁니다. ' + nerr)
                        use_nv = False
                    nb, nroad = None, ''
                    for it in (items or []):
                        road = addr_key(it.get('roadAddress') or it.get('address') or '')
                        if road and want and road == want:
                            nb, nroad = it, road
                            break
                        if nb is None:
                            nb, nroad = it, road
                    if nb:
                        rec['nvnm'] = TAG.sub('', nb.get('title') or '')
                        rec['nvadr'] = nb.get('roadAddress') or nb.get('address') or ''
                        rec['nvcat'] = nb.get('category') or ''
                        rec['nvurl'] = nb.get('link') or ''
                        kroad = addr_key(rec['padr'])
                        if nroad and want and nroad == want and bg == '확실':
                            rec['g'] = '두곳확인'
                        elif nroad and want and nroad == want:
                            rec['g'] = '확실'          # 네이버가 우리 주소와 맞음
                        elif nroad and kroad and nroad != kroad:
                            rec['g'] = '불일치'        # 카카오와 네이버가 서로 다른 곳
                    bg = rec['g']
                store[nm] = rec
                hits[bg] = hits.get(bg, 0) + 1
            else:
                store[nm] = {'tel': '', 'url': '', 'pnm': '', 'padr': '', 'g': '없음',
                             'y': 0, 'x': 0}
                none += 1

            if n % 100 == 0 or n == len(todo):
                el = time.time() - t0
                left = len(todo) - n
                print(f'{n:>7,}/{len(todo):,}  두곳확인 {hits["두곳확인"]:,}  확실 {hits["확실"]:,}  '
                      f'보통 {hits["보통"]:,}  낮음 {hits["낮음"]:,}  불일치 {hits["불일치"]:,}  '
                      f'못찾음 {none:,}  {el:.0f}s'
                      + (f'  남은 {left:,}곳 {left*el/n/60:.0f}분' if left else ''))
                save()

            if a.max_calls and calls >= a.max_calls:
                stop = f'이번 회차 호출 상한 {a.max_calls:,}회에 도달했습니다.'
                break
    except KeyboardInterrupt:
        stop = '사용자가 중단했습니다 (Ctrl+C).'
    finally:
        save()

    rows = [[k, v['g'], v['tel'], v['pnm'], v['padr'], v['url'],
             v.get('nvnm', ''), v.get('nvadr', ''), v.get('nvcat', ''), v.get('nvurl', '')]
            for k, v in store.items() if v.get('g') != '없음']
    pd.DataFrame(rows, columns=['회사명', '신뢰도', '전화번호', '카카오 장소명',
                                '카카오 주소', '카카오맵 링크',
                                '네이버 장소명', '네이버 주소', '네이버 업종', '네이버 링크']) \
      .sort_values(['신뢰도', '회사명']) \
      .to_csv(paths.out('연락처_수집결과.csv'), index=False, encoding='utf-8-sig')

    tot = {}
    for v in store.values():
        tot[v.get('g', '없음')] = tot.get(v.get('g', '없음'), 0) + 1
    print('\n누적 — ' + ' · '.join(f'{k} {tot.get(k,0):,}' for k in
          ('두곳확인', '확실', '보통', '낮음', '불일치', '없음')))
    if tot.get('불일치'):
        print(f'  **불일치 {tot["불일치"]:,}건** — 카카오와 네이버가 서로 다른 장소를 가리킵니다.')
        print('   둘 중 하나는 동명 업체입니다. 전화 걸기 전에 CSV 에서 두 주소를 비교하십시오.')
    if stop:
        print(f'  {stop}\n  같은 명령을 다시 실행하면 이어서 합니다.')
    print('  → out\\연락처_수집결과.csv')
    print('  **\'확실\'이 아닌 번호는 전화 걸기 전에 확인하십시오.** 동명 업체일 수 있습니다.')
    print('이어서  python src\\08_build.py  →  python src\\09_page.py')

if __name__ == '__main__':
    main()
