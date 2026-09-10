# -*- coding: utf-8 -*-
"""이름·주소로 다른 데이터를 붙이는 공통 규칙.

**왜 이 파일이 따로 있나**
  등록공장현황에는 사업자등록번호가 없다. 그래서 배출량·재무·국민연금·수출명단을
  붙일 때마다 상호(와 주소)를 대조하는 수밖에 없다. 규칙이 스크립트마다 조금씩
  다르면 "어디는 붙고 어디는 안 붙는" 상태가 되므로 한 곳에 모았다.

**규칙**
  1. 법인 표기를 지운다        (주)포스코 · 주식회사 포스코 · ㈜포스코 → 포스코
  2. 공장 꼬리표를 지운다      현대제철(주)제1공장 → 현대제철
  3. 남은 이름이 같으면 붙인다
  4. 같지 않으면, **띄어쓰기나 (주) 자리에서 끊긴 경계**에서만 앞부분 일치를 본다

  4번의 경계 조건이 핵심이다. 그냥 앞부분 일치를 허용하면 '포스코케미칼'이 '포스코'에
  붙어 69조 매출이 엉뚱한 법인에 찍힌다. 경계를 요구하면 '쌍용씨앤이(주)동해공장'은
  붙고 '포스코케미칼'은 안 붙는다.
"""
import re, unicodedata

LEGAL = re.compile(r'\(주\)|\(유\)|\(재\)|\(사\)|㈜|㈐|주식회사|유한회사|유한책임회사|'
                   r'합자회사|합명회사|재단법인|사단법인|의료법인|학교법인|주\)|유\)')
SUFFIX = re.compile(r'(제?\d*\s*(공장|사업장|지점|영업소|사업소|제철소|제강소|발전소|'
                    r'센터|캠퍼스|플랜트|단지))+\s*$')
NOISE = re.compile(r'[\s\.\,\-\_\·\(\)\[\]<>/]+')

def norm(s):
    """(붙인 이름, 경계를 | 로 남긴 이름)"""
    if not isinstance(s, str):
        return '', ''
    s = unicodedata.normalize('NFKC', s)
    s = LEGAL.sub(' ', s)
    s = SUFFIX.sub(' ', s.strip())
    b = NOISE.sub('|', s).strip('|')
    return b.replace('|', ''), b

class Index:
    """붙일 쪽(배출량·국민연금 등)의 이름 색인.

    11만 개 × 17만 개를 곱으로 훑으면 170억 번이라 몇 시간이 걸린다.
    뒤집어서 **찾는 쪽 이름의 경계 조각**을 열쇠로 쓰면 조회 3~4번이면 끝난다.
    """
    def __init__(self):
        self.exact = {}     # 압축 이름 → 값
        self.bound = {}     # 경계 이름 → 압축 이름

    def add(self, name, value, prefer=False):
        k, kb = norm(name)
        if len(k) < 2:
            return None
        if k in self.exact and not prefer:
            return k
        self.exact[k] = value
        if len(k) >= 3:
            self.bound.setdefault(kb, k)
        return k

    def find(self, name):
        """(값, 맞은 키, 방식) — 못 찾으면 (None, None, '')"""
        k, kb = norm(name)
        if not k:
            return None, None, ''
        if k in self.exact:
            return self.exact[k], k, '정확'
        parts = kb.split('|')
        for j in range(len(parts) - 1, 0, -1):       # 긴 조각부터
            lk = self.bound.get('|'.join(parts[:j]))
            if lk:
                return self.exact[lk], lk, '앞부분'
        return None, None, ''

# ── 주소 ───────────────────────────────────────────────────────────────────
RE_SP = re.compile(r'\s+')
RE_TAIL = re.compile(r'\s*[,\s]*외\s*\d+\s*(필지|호|동|공장)?\s*$')
RE_PAREN = re.compile(r'\([^()]*\)')

def addr_key(a):
    """주소를 '도로명 + 본번(-부번)' 까지만 남긴 비교용 열쇠.

    같은 건물인데 '3층 202호', '외 2필지' 때문에 다른 주소로 보이는 것을 막는다.
    """
    if not isinstance(a, str):
        return ''
    a = unicodedata.normalize('NFKC', a).strip()
    prev = None
    while prev != a:
        prev = a
        a = RE_PAREN.sub(' ', a)
    a = RE_TAIL.sub('', a)
    a = RE_SP.sub(' ', a).strip()
    m = re.match(r'^(.*?(?:로|길)\s?\d+(?:-\d+)?)(?![\d\-]|번길)', a)
    if m:
        a = m.group(1)
    else:                       # 지번주소는 '동/리 + 번지' 까지
        m2 = re.match(r'^(.*?[동리]\s?\d+(?:-\d+)?)', a)
        if m2:
            a = m2.group(1)
    return RE_SP.sub('', a)
