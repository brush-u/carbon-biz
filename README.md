# 산업단지 CBAM 영업 지도

산업단지에 입주한 공장 **84,111곳**에서 탄소 규제가 곧 닿을 곳을 찾아,
전화를 걸 순서를 정하는 도구입니다.

회사마다 **규모 · 연락처 · 배출량 · 수출 여부**를 한 화면에 모아두고,
지도·업종·품목으로 걸러 목록을 CSV로 내려받습니다.

---

## 폴더

```
carbon-biz/
├─ data/     원본 — 직접 내려받아 넣는 것 (git 에 안 올림)
│   ├─ 한국산업단지공단_전국등록공장현황….csv   ← 필수
│   ├─ emission/   배출량 xls·xlsx
│   ├─ pension/    국민연금 사업장 csv
│   ├─ export/     수출기업 명단 (아무 csv·xlsx)
│   └─ finance/    DART 고유번호 (자동 생성)
├─ cache/    다시 만들기 어려운 중간물 (git 에 올림)
│   ├─ clean.pkl · geo_cache.json · boundary.json
│   ├─ emission.json · pension.json · contact.json · export.json
│   └─ vendor/  leaflet, 시도 SVG — 사내망에서 npm 이 막혀도 돌아가게
├─ src/      파이프라인 (아래 표)
├─ tests/    자동 검증
├─ out/      산출물 — index.html, 영업리스트.csv, 각종 매칭결과
├─ web/      배포본 — index.html + data.jgz
└─ docs/     항목별 상세 안내
```

## 파이프라인

| | 하는 일 | 필요한 것 | 문서 |
|---|---|---|---|
| `01_prep.py` | 원본 분류 — 지역·단지유형·업종·열공정·CBAM | 원본 CSV | |
| `02_geocode.py` | 주소 → 좌표 | VWorld 키 | [GEOCODE_ALL](docs/GEOCODE_ALL.md) |
| `03_emission.py` | 배출권거래제·명세서 배출량 | 파일 2종 | [EMISSION](docs/EMISSION.md) |
| `04_pension.py` | **종업원수·인건비·고용 추이** | 국민연금 CSV | 아래 |
| `05_finance.py` | 매출·영업이익 | DART 키 | [FINANCE](docs/FINANCE.md) |
| `06_contact.py` | **전화번호·지도 링크** | 카카오 REST 키 | 아래 |
| `07_export.py` | **수출기업 명단 대조** | 명단 파일 | 아래 |
| `08_build.py` | 모아서 `out/data.json` | | |
| `09_page.py` | 화면 만들기 | | |
| `10_boundary.py` | 시도 경계 | | [BOUNDARY](docs/BOUNDARY.md) |
| `11_mymaps.py` | Google My Maps CSV | | [MYMAPS](docs/MYMAPS.md) |

굵게 표시한 셋이 **영업용으로 새로 넣은 것**입니다.

## 한 번에 돌리기

```powershell
cd D:\workspace\carbon-biz
.\run_all.ps1
```

## 웹에 올리기

처음 한 번만 — GitHub 비공개 저장소를 만들고

```powershell
.\setup_git.ps1 -Repo https://github.com/내계정/carbon-biz.git
```

그다음부터는 이 한 줄이면 다시 만들고·검사하고·올리고·배포까지 됩니다.

```powershell
.\deploy_web.ps1
```

배포처는 **Cloudflare Pages** 입니다 — 무료이고 상업적 이용이 되며, 비공개 저장소도
연결됩니다. 처음 연결하는 법은 [DEPLOY](docs/DEPLOY.md) 에 있습니다.

## 범위 바꾸기

기본은 산업단지 입주업체 84,111곳입니다.

```powershell
$env:SCOPE='national'; python src\08_build.py   # 국가산업단지만 32,636곳
$env:SCOPE='target';   python src\08_build.py   # CBAM·열공정만
$env:SCOPE='all';      python src\08_build.py   # 전국 217,048곳
```

---

## 새로 넣은 것 셋

### 04_pension.py — 회사 규모

매출은 DART 공시 법인만 공개돼 몇 %밖에 안 붙습니다. 국민연금은
**법인 3인 이상 · 개인 10인 이상 사업장이 거의 다** 들어 있고, 법인이 아니라
**사업장 단위**라 우리 공장 데이터와 결이 맞습니다.

| 붙는 것 | 영업에 쓰는 법 |
|---|---|
| 가입자수 | 종업원수 → 중소/중견 판정, 규모별 우선순위 |
| 당월고지금액 | 인건비 규모 → 매출 대리지표 |
| 신규취득·상실 | 사람이 느는가 주는가 → 투자 여력 신호 |
| 업종코드(KSIC) | 우리가 생산품으로 추정한 업종의 검증 |

[국민연금공단_국민연금 가입 사업장 내역](https://www.data.go.kr/data/15083277/fileData.do)
을 받아 `data\pension\` 에 넣고 `python src\04_pension.py`.

### 06_contact.py — 전화번호

카카오 로컬 '키워드로 장소 검색' 으로 상호를 찾아 **전화번호·도로명주소·지도 링크·좌표**를
가져옵니다. 무료이고 한도가 넉넉합니다.

**신뢰도를 반드시 보십시오.** 상호만으로 찾으면 전국의 동명 업체가 딸려옵니다.

| 등급 | 뜻 | 쓰는 법 |
|---|---|---|
| 두 곳 확인 | 카카오·네이버가 같은 주소 | 그대로 전화해도 됩니다 |
| 확실 | 도로명 본번까지 일치 | 그대로 전화해도 됩니다 |
| 보통 | 같은 시군구 + 상호 일치 | 걸기 전에 한 번 확인 |
| 낮음 | 상호만 일치 | 참고용. 영업에 바로 쓰지 마십시오 |
| 주소 불일치 | 카카오와 네이버가 서로 다른 곳 | **쓰지 마십시오.** 동명 업체입니다 |

```powershell
python src\06_contact.py --key 카카오REST키 --limit 30      # 먼저 30건
python src\06_contact.py --key 카카오REST키 --scope target  # CBAM·열공정 8,000곳
```

**네이버로 한 번 더 확인 (권장)** — [developers.naver.com](https://developers.naver.com) 에서
애플리케이션을 만들고 **검색** API 를 추가하면 Client ID·Secret 이 나옵니다. 하루 25,000회 무료.

```powershell
python src\06_contact.py --key 카카오REST키 --naver-id 아이디 --naver-secret 시크릿 --scope target
```

**네이버는 전화번호를 주지 않습니다.** 공개 API 의 `telephone` 항목은 빈 문자열로 내려옵니다
(네이버 지도 화면에 보이는 번호는 API 로 제공되지 않습니다). 그래서 네이버는 번호를 가져오는
곳이 아니라 **카카오가 집어온 장소가 맞는지 주소로 확인해 주는 두 번째 눈**으로 씁니다.
둘이 어긋나면 그 번호는 동명 업체 것이니 걸러냅니다.

### 07_export.py — 수출 여부

**개별 기업의 수출실적은 공개되지 않습니다.** CBAM 영업에서 가장 결정적인 변수인데
정면으로 구할 방법이 없습니다. 그래서 "수출한다고 알려진 기업 명단" 을 모아 겹치는지만 봅니다.
있으면 유력, **없어도 아닐 수 있습니다.**

회사명 컬럼이 있는 CSV·XLSX 를 `data\export\` 에 넣으면 파일명이 그대로 출처가 됩니다.
무역협회 회원사, KOTRA 수출유망중소기업, 수출바우처 참여기업, 사내 거래처 목록 등
구할 수 있는 대로 여러 개 넣으십시오.

---

## 영업 우선순위 점수

화면과 `out\영업리스트.csv` 에 0~130점이 붙습니다. **임의로 정한 가중치라 숫자만 믿으면
안 되고, 그래서 근거를 화면에 그대로 보여줍니다.**

| 근거 | 점수 | 왜 |
|---|---:|---|
| CBAM 품목 | 40 | 규제가 직접 닿습니다 |
| 수출 명단 | 25 | 수출을 해야 CBAM이 실제 문제가 됩니다 |
| 규제 밖 | 20 | 배출량을 세어본 적이 없는 곳 = 도움이 필요한 곳 |
| 고온 열공정 | 15 | 품목이 아니어도 연료 배출이 큽니다 |
| 종업원 20~300 | 15 | 컨설팅을 살 여력이 있으면서 전담 인력은 없는 규모 |
| 연락처 확인 | 10 | 지금 전화할 수 있습니다 |
| 고용 증가 | 5 | 투자 여력 신호 |

---

## 데이터의 한계

- **업종·품목·열공정·CBAM은 생산품 텍스트에서 추정한 값**입니다. 확정 분류가 아닙니다.
- **사업자등록번호가 원본에 없어** 모든 결합이 상호+주소 대조입니다. 동명이인이 섞입니다.
  각 단계의 `out\*_매칭결과.csv` 를 반드시 훑어보십시오.
- **배출량·매출은 법인 단위**입니다. 공장 한 곳의 값이 아닙니다.
- 원본은 연 1회 갱신, 현재 기준일 2024-12-31.

## 출처 표시

시도 경계는 [MapSVG](https://mapsvg.com/maps/south-korea) · CC BY 4.0,
배경지도는 OpenStreetMap · ODbL 입니다. **출처 표시가 조건이니 화면 아래 설명을
지우지 마십시오.**
