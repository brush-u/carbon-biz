# -*- coding: utf-8 -*-
"""폴더 위치를 한 곳에서 정한다.

스크립트를 어디서 실행하든(폴더 안이든 밖이든) 같은 곳을 보게 하려고 둔 파일이다.
예전 판에서는 스크립트마다 상대경로를 써서, 실행 위치가 다르면 엉뚱한 파일을 읽었다.

    carbon-biz/
    ├─ data/    원본 — 직접 내려받아 넣는 것 (git 에 올리지 않음)
    ├─ cache/   다시 만들기 어려운 중간물 — 지오코딩·경계·수집 결과 (git 에 올림)
    ├─ out/     산출물 — 화면, 리포트 CSV
    ├─ web/     배포본
    └─ src/     이 스크립트들
"""
import os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'data')
CACHE = os.path.join(ROOT, 'cache')
OUT = os.path.join(ROOT, 'out')
WEB = os.path.join(ROOT, 'web')
VENDOR = os.path.join(CACHE, 'vendor')

for d in (DATA, CACHE, OUT, WEB, VENDOR):
    os.makedirs(d, exist_ok=True)

# 자주 쓰는 파일
CLEAN = os.path.join(CACHE, 'clean.pkl')
GEO = os.path.join(CACHE, 'geo_cache.json')
BOUNDARY = os.path.join(CACHE, 'boundary.json')
EMISSION = os.path.join(CACHE, 'emission.json')
PENSION = os.path.join(CACHE, 'pension.json')
FINANCE = os.path.join(CACHE, 'finance.json')
CONTACT = os.path.join(CACHE, 'contact.json')
EXPORT = os.path.join(CACHE, 'export.json')
DATAJSON = os.path.join(OUT, 'data.json')

def data(*p):
    return os.path.join(DATA, *p)

def cache(*p):
    return os.path.join(CACHE, *p)

def out(*p):
    return os.path.join(OUT, *p)

def need(path, how):
    """없으면 무엇을 해야 하는지 알려주고 멈춘다."""
    if not os.path.exists(path):
        sys.exit(f'\n{os.path.relpath(path, ROOT)} 이(가) 없습니다.\n  → {how}\n')
    return path
