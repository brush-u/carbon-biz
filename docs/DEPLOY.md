# 배포 — GitHub 비공개 저장소 + Cloudflare Pages

`push` 하면 Cloudflare 가 알아서 배포합니다. 평소에는 명령 한 줄입니다.

```powershell
.\deploy_web.ps1
```

## 왜 Cloudflare Pages 인가

- **무료 플랜에서 상업적 이용이 됩니다.** Vercel Hobby 는 약관상 비상업·개인 용도만 됩니다.
- 비공개 GitHub 저장소도 연결됩니다.
- Cloudflare Access 로 사내 계정만 통과시킬 수 있습니다 (50명까지 무료).

지켜야 할 한도는 하나입니다 — **파일 하나가 25 MiB 를 넘으면 안 됩니다.**
지금 `data.jgz` 는 **2.6 MB** 라 한참 여유가 있습니다. 넘어가면 스크립트가 먼저 잡아
멈추고, 범위를 줄이는 명령을 알려줍니다.

---

## 처음 한 번만

### 1. GitHub 에 빈 비공개 저장소

[github.com/new](https://github.com/new) → Repository name `carbon-biz` → **Private** →
**Add a README / .gitignore / license 는 전부 체크하지 마십시오** → Create.

### 2. 올립니다

```powershell
cd D:\workspace\carbon-biz
.\setup_git.ps1 -Repo https://github.com/내계정/carbon-biz.git
```

처음 `push` 할 때 GitHub 로그인 창이 뜹니다. 브라우저로 승인하시면 됩니다.

### 3. Cloudflare Pages 에 연결

1. [dash.cloudflare.com](https://dash.cloudflare.com) 로그인 (계정이 없으면 무료로 만듭니다)
2. 왼쪽 **Compute (Workers & Pages)** → **Create** → **Pages** → **Connect to Git**
3. GitHub 계정을 연결합니다. 권한은 **Only select repositories** 로 `carbon-biz` 하나만 주셔도 됩니다
4. 빌드 설정 — **이 셋만** 맞추면 됩니다

   | | |
   |---|---|
   | Framework preset | **None** |
   | Build command | **비워 두십시오** |
   | Build output directory | **`web`** |

5. **Save and Deploy**

1~2분 뒤 `https://carbon-biz.pages.dev` 주소가 나옵니다.

헤더 설정(`_headers`)은 `python src\09_page.py --web` 이 `web\` 안에 자동으로 만듭니다.
대시보드에서 따로 만지실 것 없습니다.

---

## 그다음부터

```powershell
.\deploy_web.ps1
```

이 한 줄이 하는 일:

1. `08_build.py` → `09_page.py` → `09_page.py --web` 으로 다시 만들고
2. `test_data.py` 와 `test_ui.js` 로 검사하고 — **하나라도 실패하면 올리지 않습니다**
3. `data.jgz` 가 25 MiB 안인지, `_headers` 가 있는지 확인하고
4. 커밋하고 `push` 합니다

Cloudflare 가 push 를 받아 1~2분 안에 배포합니다.
진행 상황은 대시보드의 **Compute → 프로젝트 → Deployments** 에서 봅니다.

```powershell
.\deploy_web.ps1 -SkipBuild                  # 이미 만든 web\ 만 올림
.\deploy_web.ps1 -SkipTest                   # 검사 건너뜀 (권하지 않습니다)
.\deploy_web.ps1 -Message "연락처 8천곳 추가"   # 커밋 메시지 직접
```

---

## `_headers` 가 무엇을 하나

```
/data.jgz
  Content-Type: application/octet-stream
```

`data.jgz` 는 우리가 직접 gzip 으로 만든 파일이고, 페이지가 앞 두 바이트(`1f 8b`)를 보고
`DecompressionStream` 으로 **스스로 풉니다.** 그래서 서버가 `Content-Encoding: gzip` 을
붙이면 브라우저가 먼저 풀어버려 우리 코드가 두 번 푸는 꼴이 됩니다. 확장자를 `.jgz` 로
둔 것도, 여기서 `application/octet-stream` 을 못 박는 것도 **서버가 알아서 손대지 않게**
하려는 것입니다.

---

## 올라가는 것 / 안 올라가는 것

**올라갑니다**

- `src\` `tests\` `docs\` — 코드
- `web\` — 배포본 (`index.html` 0.4MB + `data.jgz` 2.6MB + `_headers`)
- `cache\` — 배출량·국민연금·연락처·수출 결합 결과, 시도 경계, leaflet
- `cache\geo_cache.json` — **지오코딩 결과.** 다시 만들려면 며칠 걸리니 꼭 남깁니다

**안 올라갑니다** (`.gitignore`)

- `data\` — 원본. 공공데이터라 각자 받으면 됩니다
- `.kakao_key` `.naver_key` `.vworld_key` `.dart_key` `.env` — **인증키**
- `cache\clean.pkl` — 35MB. 원본 CSV 만 있으면 `python src\01_prep.py` 로 1분이면 다시 만듭니다
- `out\` 의 산출물

`setup_git.ps1` 은 올리기 전에 키 파일이 섞여 있는지 먼저 확인하고 알려줍니다.

---

## 자동 확인 (GitHub Actions)

`.github\workflows\check.yml` 이 push 마다 배포본을 검사합니다. 배포는 Cloudflare 가 하고,
여기서는 **깨진 파일이 배포되는 것만** 막습니다. 실제로 겪었던 사고들입니다.

- `data.jgz` 가 gzip 이 아니거나 잘려 올라감
- `index.html` 에 치환 안 된 `__DATA__` 같은 자리표시자가 남음
- `<meta charset>` 이 빠져 한글이 깨짐
- 25MB 넘는 파일

실패하면 GitHub 저장소의 **Actions** 탭에 빨갛게 뜹니다.

---

## 접근을 사내로 제한하려면

화면에는 업체 상호·주소·전화번호와 **영업 우선순위 기준**이 들어 있습니다. 원본은
공공데이터라 공개해도 법적 문제는 없지만, 영업 기준까지 밖에 보이는 것은 다른 이야기입니다.

Cloudflare 에서 **Zero Trust → Access → Applications → Add an application → Self-hosted**
로 `carbon-biz.pages.dev` 를 걸고, 정책을 **Emails ending in `@lsitc.com`** 으로 두면
사내 메일 계정만 들어옵니다. 50명까지 무료입니다.

---

## 출처 표시는 지우지 마십시오

화면 아래 설명에 들어 있습니다. 조건입니다.

- 시도 경계 — [MapSVG](https://mapsvg.com/maps/south-korea) · CC BY 4.0
- 배경지도 — OpenStreetMap · ODbL
- 원본 — 한국산업단지공단 「전국등록공장현황」, 공공데이터포털 (이용허락범위 제한 없음)
