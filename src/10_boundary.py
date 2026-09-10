# -*- coding: utf-8 -*-
"""시도 경계 폴리곤을 만든다 → boundary.json

왜 필요한가
  OpenStreetMap 타일에 행정경계가 그려져 있긴 하지만 그건 **그림**입니다.
  타일은 256×256 PNG라 클릭해도 "여기가 경기도"라는 정보가 없습니다.
  구역을 눌러 그 지역만 보려면 좌표로 된 경계 폴리곤이 따로 있어야 합니다.

경계 원본
  1순위  boundary\*.geojson  — 직접 넣은 GeoJSON (VWorld LT_C_ADSIDO_INFO 등). 가장 정확
  2순위  vendor\sido_svg.json — 동봉한 SVG 원본 (CC BY 4.0, MapSVG)
  3순위  node_modules\@svg-maps\south-korea

2·3순위는 SVG 좌표계라 위경도로 옮겨야 합니다. 그 변환은 추측이 아니라
**지오코딩된 공장 1만 220곳의 좌표와 그 공장의 시도 라벨**로 맞췄습니다.
지도 좌표계를 아는 대신, 정답을 아는 점 1만 개에 폴리곤을 끼워 맞춘 것입니다.
결과는 97.7%가 1km 안, 99.4%가 3km 안에 들어옵니다.
"""
import json, os, re, glob, sys, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths

OUT = paths.BOUNDARY

# SVG(0 0 524 631) → 위경도 아핀 변환.
#   x = P*lon + Q*lat + R
#   y = S*lon + T*lat + U
# 공장 좌표에 대한 "제 시도 폴리곤 안에 들어가는가" 거리를 최소화해 얻은 값.
AFF = (93.660277, -0.649420, -11716.887550,
        0.474588, -116.623619,  4447.337387)

EN2KO = {'busan': '부산', 'daegu': '대구', 'daejeon': '대전', 'gangwon': '강원',
         'gwangju': '광주', 'gyeonggi': '경기', 'incheon': '인천', 'jeju': '제주',
         'north-chungcheong': '충북', 'north-gyeongsang': '경북', 'north-jeolla': '전북',
         'sejong': '세종', 'seoul': '서울', 'south-chungcheong': '충남',
         'south-gyeongsang': '경남', 'south-jeolla': '전남', 'ulsan': '울산'}

# GeoJSON 원본의 시도명은 표기가 제각각이다 (경기도 / 경기 / Gyeonggi-do)
def short(name):
    n = re.sub(r'\s', '', str(name))
    for full, s in [('서울', '서울'), ('부산', '부산'), ('대구', '대구'), ('인천', '인천'),
                    ('광주', '광주'), ('대전', '대전'), ('울산', '울산'), ('세종', '세종'),
                    ('경기', '경기'), ('강원', '강원'), ('충청북', '충북'), ('충청남', '충남'),
                    ('전라북', '전북'), ('전라남', '전남'), ('경상북', '경북'),
                    ('경상남', '경남'), ('제주', '제주'), ('충북', '충북'), ('충남', '충남'),
                    ('전북', '전북'), ('전남', '전남'), ('경북', '경북'), ('경남', '경남')]:
        if n.startswith(full):
            return s
    return None

# ── SVG path 파싱 ──────────────────────────────────────────────────────────
def parse_path(p):
    """m(상대 moveto) 과 z 만 쓰는 path → 폴리곤 목록"""
    polys, cur, x, y = [], None, 0.0, 0.0
    toks = re.findall(r'[mz]|-?\d*\.?\d+(?:e-?\d+)?', p, re.I)
    i = 0
    while i < len(toks):
        t = toks[i]
        if t.lower() == 'm':
            if cur and len(cur) > 2:
                polys.append(cur)
            x += float(toks[i + 1]); y += float(toks[i + 2])
            cur = [(x, y)]; i += 3
        elif t.lower() == 'z':
            if cur and len(cur) > 2:
                polys.append(cur)
            cur = None; i += 1
        else:
            x += float(t); y += float(toks[i + 1]); i += 2
            if cur is None:
                cur = [(x, y)]
            else:
                cur.append((x, y))
    if cur and len(cur) > 2:
        polys.append(cur)
    return polys

def svg_to_ll(polys):
    P, Q, R, S, T, U = AFF
    det = P * T - Q * S
    out = []
    for pts in polys:
        ring = []
        for x, y in pts:
            a, b = x - R, y - U
            lon = ( T * a - Q * b) / det
            lat = (-S * a + P * b) / det
            ring.append([round(lon, 5), round(lat, 5)])
        out.append(ring)
    return out

# ── Douglas-Peucker (외부 의존 없이) ───────────────────────────────────────
def dp(pts, eps):
    if len(pts) < 3:
        return pts
    def seg(p, a, b):
        (x, y), (x1, y1), (x2, y2) = p, a, b
        dx, dy = x2 - x1, y2 - y1
        if dx == 0 and dy == 0:
            return math.hypot(x - x1, y - y1)
        t = max(0, min(1, ((x - x1) * dx + (y - y1) * dy) / (dx * dx + dy * dy)))
        return math.hypot(x - (x1 + t * dx), y - (y1 + t * dy))
    keep = [False] * len(pts); keep[0] = keep[-1] = True
    stack = [(0, len(pts) - 1)]
    while stack:
        i, jx = stack.pop()
        if jx <= i + 1:
            continue
        dmax, k = 0.0, i
        for m in range(i + 1, jx):
            d = seg(pts[m], pts[i], pts[jx])
            if d > dmax:
                dmax, k = d, m
        if dmax > eps:
            keep[k] = True; stack += [(i, k), (k, jx)]
    return [p for p, f in zip(pts, keep) if f]

# ── 원본 읽기 ──────────────────────────────────────────────────────────────
def from_geojson(path):
    g = json.load(open(path, encoding='utf-8'))
    feats = g.get('features', []) if isinstance(g, dict) else g
    out = {}
    for f in feats:
        pr = f.get('properties', {}) or {}
        nm = None
        for key in ('ctp_kor_nm', 'CTP_KOR_NM', 'name', 'NAME', 'sido_nm', 'SIG_KOR_NM', 'name_ko'):
            if pr.get(key):
                nm = short(pr[key])
                if nm:
                    break
        if not nm:
            continue
        gm = f.get('geometry', {}) or {}
        rings = []
        if gm.get('type') == 'Polygon':
            rings = [gm['coordinates'][0]]
        elif gm.get('type') == 'MultiPolygon':
            rings = [poly[0] for poly in gm['coordinates']]
        out.setdefault(nm, []).extend([[[round(float(a), 5), round(float(b), 5)]
                                        for a, b in r] for r in rings])
    return out, os.path.basename(path)

def from_svg():
    src = None
    if os.path.exists(os.path.join(paths.VENDOR, 'sido_svg.json')):
        src = os.path.join(paths.VENDOR, 'sido_svg.json')
        raw = json.load(open(src, encoding='utf-8'))
    else:
        p = os.path.join('node_modules', '@svg-maps', 'south-korea', 'index.js')
        if not os.path.exists(p):
            return None, None
        s = open(p, encoding='utf-8').read()
        raw = json.loads(s[s.index('{'):].rstrip().rstrip(';'))
        src = p
    out = {}
    for L in raw['locations']:
        ko = EN2KO.get(L['id'])
        if ko:
            out[ko] = svg_to_ll(parse_path(L['path']))
    return out, os.path.basename(src)

# ── 실행 ───────────────────────────────────────────────────────────────────
gj = sorted(glob.glob(os.path.join(paths.data('boundary'), '*.geojson')) +
            glob.glob(os.path.join(paths.data('boundary'), '*.json')))
if gj:
    polys, src = from_geojson(gj[0])
    note = '직접 넣은 GeoJSON'
else:
    polys, src = from_svg()
    note = 'MapSVG 지도 (CC BY 4.0) · 공장 좌표로 위경도 정렬'

if not polys:
    print('경계 원본을 찾지 못했습니다.')
    print('  vendor\\sido_svg.json 이 있는지 확인하거나')
    print('  npm install @svg-maps/south-korea 를 실행하거나')
    print('  boundary\\ 폴더에 시도 GeoJSON을 넣으십시오. BOUNDARY.md 참고.')
    sys.exit(1)

# 아주 작은 섬은 뺀다 — 클릭 대상이 되지 못하고 파일만 키운다
EPS = 0.0009          # 약 80m
MIN_RING = 0.00004    # 약 0.2 km²
kept = {}
drop_small = 0
for k, rings in polys.items():
    out = []
    for r in rings:
        a = abs(sum(r[i][0] * r[(i + 1) % len(r)][1] - r[(i + 1) % len(r)][0] * r[i][1]
                    for i in range(len(r)))) / 2
        if a < MIN_RING:
            drop_small += 1
            continue
        s = dp(r, EPS)
        if len(s) >= 4:
            out.append(s)
    if out:
        kept[k] = out

nv0 = sum(len(r) for v in polys.values() for r in v)
nv1 = sum(len(r) for v in kept.values() for r in v)
json.dump({'src': src, 'note': note, 'sido': kept},
          open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
print(f'{OUT}  {os.path.getsize(OUT)/1024:.0f} KB')
print(f'  원본 {src} · 시도 {len(kept)}개 · 폴리곤 {sum(len(v) for v in kept.values())}개')
print(f'  꼭짓점 {nv0:,} → {nv1:,} (작은 섬 {drop_small}개 제외)')

# ── 검증 — 지오코딩된 공장이 제 시도 폴리곤 안에 들어가는지 ────────────────
if os.path.exists(paths.GEO) and os.path.exists(paths.CLEAN):
    import pandas as pd
    g = json.load(open(paths.GEO, encoding='utf-8'))
    ok = {a: v for a, v in g.items() if v and v.get('lat')}
    df = pd.read_pickle(paths.CLEAN)
    df = df[df['시도'] != '미상'].copy()
    df['ll'] = df['공장주소'].map(lambda a: ok.get(a))
    df = df[df['ll'].notna()]
    if len(df):
        def pip(lon, lat, rings):
            for r in rings:
                inside = False
                n = len(r); j = n - 1
                for i in range(n):
                    xi, yi = r[i]; xj, yj = r[j]
                    if (yi > lat) != (yj > lat) and \
                       lon < (xj - xi) * (lat - yi) / ((yj - yi) or 1e-12) + xi:
                        inside = not inside
                    j = i
                if inside:
                    return True
            return False
        hit = tot = 0
        for s, sub in df.groupby('시도'):
            rings = kept.get(s)
            if not rings:
                continue
            for v in sub['ll']:
                tot += 1
                if pip(float(v['lon']), float(v['lat']), rings):
                    hit += 1
        print(f'  검증 — 공장 {tot:,}곳 중 {hit/tot*100:.1f}%가 제 시도 폴리곤 안')
        if hit / tot < 0.85:
            print('  ! 85% 미만입니다. 경계 원본이나 좌표계를 확인하십시오.')
