# -*- coding: utf-8 -*-
"""주소 → 좌표 (지오코딩)

공장 주소를 좌표로 바꾼다. 범위는 둘 중 하나다.

    --scope target   CBAM·열공정 대상만 (기본값, 9,324건)
    --scope all      전국 등록공장 전부 (고유 주소 197,216건)

**전국을 할 때는 하루에 끝나지 않는다.** API 일일 한도가 4만 건쯤이라
며칠에 나눠 돌려야 한다. 그래서 이렇게 만들어 뒀다.

  · `--max-calls` 로 하루치만 쓰고 깔끔하게 멈춘다
  · 성공한 주소는 `geo_cache.json` 에 남아 다음 날 이어서 한다
  · Ctrl+C 로 끊어도 그 순간까지의 결과는 저장된다
  · 한도 초과 응답을 받으면 스스로 멈춘다

자세한 절차는 GEOCODE_ALL.md 에 있다.
- 캐시를 남겨 재실행하면 이미 성공한 건은 다시 호출하지 않는다 (중단해도 이어서 진행)
- 주소 정제 후 도로명 → 지번 순으로 재시도한다
- 실패 건은 따로 CSV로 빼서 눈으로 고칠 수 있게 한다

사용법
    python 2_geocode.py --key 발급받은키 --limit 20     # 먼저 20건으로 시험
    python 2_geocode.py --key 발급받은키                # 전체 실행
    python 2_geocode.py --key 발급받은키 --provider molit   # 국토부 지오코더로 전환

인증키 발급
    VWorld : https://www.vworld.kr  회원가입 → 오픈API → 인증키 발급 (Geocoder 2.0 선택)
    국토부  : https://www.data.go.kr/data/15101106/openapi.do  활용신청
"""
import argparse, csv, json, os, re, sys, time
import urllib.parse, urllib.request, urllib.error
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths

IN_CSV    = paths.out('CBAM_대상후보.csv')
CACHE     = paths.GEO
OUT_CSV   = paths.out('좌표결과.csv')
FAIL_CSV  = paths.out('지오코딩_실패.csv')

# ---------------------------------------------------------------- 주소 정제
# 공장 주소에는 지오코딩을 방해하는 꼬리표가 많다.
#   "경기도 화성시 비봉면 현대기아로830번길 8 외 1필지"
#   "대구광역시 달서구 호산동로 12-9, (3차단지 109B 5L) (호림동)"
#   "경기도 부천시 원미구 평천로 790, 3층(도당동, (주)제너렉스)"
RE_EXTRA   = re.compile(r'\s*[,\s]*외\s*\d+\s*(필지|호|동|공장)?\s*$')
RE_FLOOR   = re.compile(r'[,\s]+(지하\s*)?B?\d+\s*층(\s*\d+\s*호)?')
RE_ROOM    = re.compile(r'[,\s]+\d+\s*호(실)?')
RE_INNER   = re.compile(r'\([^()]*\)')          # 가장 안쪽 괄호부터
RE_SPACE   = re.compile(r'\s+')
# 도로명 기본주소: "…로/길 <본번>(-<부번>)". "현대기아로830번길"처럼
# 숫자 뒤에 '번길'이 이어지는 경우는 도로명이 아직 안 끝난 것이므로 건너뛴다.
RE_ROADBASE = re.compile(r'^(.*?(?:로|길)\s?\d+(?:-\d+)?)(?![\d\-]|번길)')

def strip_parens(s):
    """중첩 괄호를 안쪽부터 제거한다. (주) 같은 표기가 섞여 있어 단순 치환은 깨진다."""
    prev = None
    while prev != s:
        prev = s
        s = RE_INNER.sub(' ', s)
    return s

def clean(addr):
    """지오코딩 성공률을 높이기 위한 정제 후보를 넓은 것부터 좁은 것 순으로 돌려준다."""
    a0 = RE_SPACE.sub(' ', str(addr).strip())
    if not a0:
        return []
    cands = []

    def push(x):
        x = RE_SPACE.sub(' ', x).strip().strip(',').strip()
        if x and x not in cands:
            cands.append(x)

    a = RE_EXTRA.sub('', a0)
    a = RE_FLOOR.sub('', a)
    a = RE_ROOM.sub('', a)
    push(a)                      # 1) 괄호 포함 정제본
    b = strip_parens(a)
    push(b)                      # 2) 괄호 제거본

    m = RE_ROADBASE.match(b) or RE_ROADBASE.match(a)
    if m:
        base = m.group(1)
        push(base)               # 3) 도로명 기본주소
        if '-' in base.split()[-1]:
            push(base.rsplit('-', 1)[0])   # 4) 부번 제거

    return cands

# ---------------------------------------------------------------- 제공자
def call(url, timeout=8):
    req = urllib.request.Request(url, headers={'User-Agent': 'cbam-geocoder/1.0'})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode('utf-8'))

def geocode_vworld(addr, key, atype):
    """VWorld Geocoder 2.0 — 주소를 좌표로.
    atype: ROAD(도로명) | PARCEL(지번)
    성공 시 response.status == 'OK', 좌표는 response.result.point.x(경도) / y(위도)"""
    q = urllib.parse.urlencode({
        'service': 'address', 'request': 'getcoord', 'version': '2.0',
        'crs': 'epsg:4326', 'address': addr, 'refine': 'true',
        'simple': 'false', 'format': 'json', 'type': atype, 'key': key,
    })
    d = call('https://api.vworld.kr/req/address?' + q)
    resp = d.get('response', {})
    st = resp.get('status')
    if st == 'OK':
        p = resp.get('result', {}).get('point', {})
        return float(p['y']), float(p['x']), st, d
    return None, None, st or 'ERROR', d

def geocode_molit(addr, key, atype):
    """국토교통부 지오코더 API (공공데이터포털 15101106)."""
    q = urllib.parse.urlencode({
        'service': 'address', 'request': 'getcoord', 'version': '2.0',
        'crs': 'epsg:4326', 'address': addr, 'refine': 'true',
        'simple': 'false', 'format': 'json', 'type': atype, 'key': key,
    })
    d = call('https://api.vworld.kr/req/address?' + q)   # 국토부 지오코더도 동일 규격
    resp = d.get('response', {})
    st = resp.get('status')
    if st == 'OK':
        p = resp.get('result', {}).get('point', {})
        return float(p['y']), float(p['x']), st, d
    return None, None, st or 'ERROR', d

PROVIDERS = {'vworld': geocode_vworld, 'molit': geocode_molit}

# ---------------------------------------------------------------- 실행
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--key', required=True, help='지오코딩 API 인증키')
    ap.add_argument('--provider', default='vworld', choices=list(PROVIDERS))
    ap.add_argument('--limit', type=int, default=0, help='처음 N건만 (0=전체)')
    ap.add_argument('--sleep', type=float, default=0.06, help='호출 간 대기(초)')
    ap.add_argument('--verbose-fails', type=int, default=3, help='초반 실패 원문을 몇 건 출력할지')
    ap.add_argument('--scope', default='target', choices=['target', 'all'],
                    help='target=CBAM·열공정만 / all=전국 등록공장 전부')
    ap.add_argument('--max-calls', type=int, default=0,
                    help='이번 회차에 쓸 API 호출 수 상한 (0=무제한). 일일 한도를 넘지 않게 쓴다')
    ap.add_argument('--max-tries', type=int, default=0,
                    help='주소 하나에 시도할 최대 호출 수 (0=제한 없음, 전국일 때는 4를 권함)')
    ap.add_argument('--retry-fails', action='store_true',
                    help='예전에 실패한 주소도 다시 시도한다 (기본은 건너뜀)')
    args = ap.parse_args()

    if args.scope == 'all':
        import pandas as pd
        if not os.path.exists(paths.CLEAN):
            sys.exit('clean.pkl 이 없습니다. python src\\01_prep.py 를 먼저 돌리십시오.')
        addrs = (pd.read_pickle(paths.CLEAN)['공장주소'].astype(str).str.strip()
                 .replace('', pd.NA).dropna().drop_duplicates().tolist())
        rows = [{'공장주소': a} for a in addrs]
        print(f'범위 전체 — 고유 주소 {len(rows):,}건')
    else:
        if not os.path.exists(IN_CSV):
            sys.exit(f'입력 파일이 없습니다: {IN_CSV}')
        rows = list(csv.DictReader(open(IN_CSV, encoding='utf-8-sig')))
    if args.limit:
        rows = rows[:args.limit]

    cache = json.load(open(CACHE, encoding='utf-8')) if os.path.exists(CACHE) else {}
    fn = PROVIDERS[args.provider]

    stat = {'cache': 0, 'ok': 0, 'fail': 0, 'calls': 0}
    shown = 0
    t0 = time.time()
    stop = ''

    todo = sum(1 for r in rows
               if r['공장주소'] not in cache
               or (args.retry_fails and not (cache[r['공장주소']] or {}).get('lat')))
    print(f'  캐시에 없는 주소 {todo:,}건'
          + (f' · 이번 회차 호출 상한 {args.max_calls:,}회' if args.max_calls else ''))
    if todo == 0:
        print('  새로 할 것이 없습니다.')

    def save():
        json.dump(cache, open(CACHE, 'w', encoding='utf-8'), ensure_ascii=False)

    try:
        for i, r in enumerate(rows, 1):
            raw = r['공장주소']
            done_before = raw in cache and (
                (cache[raw] or {}).get('lat') or not args.retry_fails)
            if done_before:
                stat['cache'] += 1
            else:
                hit = None
                tries = 0
                for cand in clean(raw):
                    for atype in ('ROAD', 'PARCEL'):
                        if args.max_tries and tries >= args.max_tries:
                            break
                        try:
                            lat, lon, st, raw_resp = fn(cand, args.key, atype)
                        except urllib.error.HTTPError as e:
                            if e.code == 429:
                                stop = '일일 호출 한도(HTTP 429)에 걸렸습니다.'
                            else:
                                stop = f'HTTP {e.code} — 인증키나 파라미터를 확인하세요.'
                            raise KeyboardInterrupt
                        except KeyboardInterrupt:
                            raise
                        except Exception as e:
                            lat = lon = None; st = type(e).__name__; raw_resp = {}
                        tries += 1; stat['calls'] += 1
                        time.sleep(args.sleep)
                        if lat is not None:
                            hit = {'lat': lat, 'lon': lon, 'q': cand, 'type': atype, 'status': st}
                            break
                        # 한도 초과는 상태 문자열로도 온다
                        if isinstance(st, str) and ('LIMIT' in st.upper() or 'QUOTA' in st.upper()):
                            stop = f'API 가 한도 초과를 알려왔습니다 ({st}).'
                            raise KeyboardInterrupt
                        if shown < args.verbose_fails and st not in ('NOT_FOUND',):
                            print(f'  [원문] {cand} ({atype}) -> '
                                  f'{json.dumps(raw_resp, ensure_ascii=False)[:300]}')
                            shown += 1
                    if hit or (args.max_tries and tries >= args.max_tries):
                        break
                cache[raw] = hit or {'lat': None, 'lon': None, 'q': '', 'type': '', 'status': 'FAIL'}
                stat['ok' if hit else 'fail'] += 1

            if i % 200 == 0 or i == len(rows):
                done = stat['ok'] + stat['fail']
                rate = (stat['ok'] / done * 100) if done else 0
                el = time.time() - t0
                eta = ''
                if done and todo:
                    left = todo - done
                    eta = f'  남은 {left:,}건 예상 {left * el / done / 3600:.1f}시간'
                print(f'{i:>7,}/{len(rows):,}  신규성공 {stat["ok"]:,}  실패 {stat["fail"]:,}  '
                      f'캐시 {stat["cache"]:,}  성공률 {rate:.1f}%  호출 {stat["calls"]:,}  '
                      f'{el:.0f}s{eta}')
                save()

            if args.max_calls and stat['calls'] >= args.max_calls:
                stop = f'이번 회차 호출 상한 {args.max_calls:,}회에 도달했습니다.'
                break
    except KeyboardInterrupt:
        if not stop:
            stop = '사용자가 중단했습니다 (Ctrl+C).'
    finally:
        save()

    if stop:
        left = sum(1 for r in rows if r['공장주소'] not in cache)
        print(f'\n  {stop}')
        print(f'  여기까지 저장했습니다. 남은 주소 {left:,}건 — 같은 명령을 다시 실행하면 이어서 합니다.')
        if args.scope == 'all':
            print('  이어서 하려면:  python src\\08_build.py  →  python src\\09_page.py '
                  '(지금까지 얻은 좌표만으로도 지도가 갱신됩니다)')
        return

    # 결과 병합
    if args.scope == 'all':
        got = sum(1 for r in rows if (cache.get(r['공장주소']) or {}).get('lat'))
        with open(paths.out('주소_좌표.csv'), 'w', encoding='utf-8-sig', newline='') as f:
            w = csv.writer(f); w.writerow(['공장주소', '위도', '경도', '매칭주소', '매칭유형'])
            for r in rows:
                c = cache.get(r['공장주소']) or {}
                if c.get('lat'):
                    w.writerow([r['공장주소'], c['lat'], c['lon'], c.get('q', ''), c.get('type', '')])
        print(f'\n완료 — 고유 주소 {len(rows):,}건 중 {got:,}건 좌표 확보 ({got/len(rows)*100:.1f}%)')
        print('  주소_좌표.csv 저장 · 이어서  python src\\08_build.py  →  python src\\09_page.py')
        return

    cols = list(rows[0].keys()) + ['위도', '경도', '지오코딩상태', '매칭주소', '매칭유형']
    with open(OUT_CSV, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=cols); w.writeheader()
        for r in rows:
            c = cache.get(r['공장주소']) or {}
            r = dict(r)
            r.update({'위도': c.get('lat') or '', '경도': c.get('lon') or '',
                      '지오코딩상태': c.get('status') or 'FAIL',
                      '매칭주소': c.get('q') or '', '매칭유형': c.get('type') or ''})
            w.writerow(r)

    fails = [r for r in rows if not (cache.get(r['공장주소']) or {}).get('lat')]
    if fails:
        with open(FAIL_CSV, 'w', encoding='utf-8-sig', newline='') as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader()
            w.writerows(fails)

    got = len(rows) - len(fails)
    print(f'\n완료 — {got:,}/{len(rows):,}건 좌표 확보 ({got/len(rows)*100:.1f}%)')
    print(f'  {OUT_CSV}  좌표가 붙은 전체 목록')
    if fails:
        print(f'  {FAIL_CSV}  실패 {len(fails):,}건 — 주소를 손으로 고친 뒤 다시 실행하면 이어서 처리됩니다')

if __name__ == '__main__':
    main()
