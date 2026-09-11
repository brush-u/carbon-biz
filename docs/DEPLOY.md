# 배포 — GitHub 비공개 저장소 + Vercel

`push` 하면 배포됩니다. 평소에는 명령 한 줄입니다.

```powershell
.\deploy_web.ps1
```

저장소: `github.com/brush-u/carbon-biz` (Private) · 브랜치 `main`

---

## 먼저 — Vercel 무료 플랜은 상업적 이용이 안 됩니다

Vercel 문서에 이렇게 적혀 있습니다.

> the Hobby plan restricts users to non-commercial, personal use only

이 도구는 LS ITC 의 영업에 쓰는 것이니 상업적 이용에 해당합니다. 무료로 올려도
기술적으로는 돌아가지만, 약관 위반이라 계정이 정지될 수 있습니다.
**시험·검토 단계라면 Hobby 로 두시고, 실제로 영업에 돌리기 시작하면 Pro($20/사람·월)로
올리십시오.** 판단은 지영님 몫이고, 이 문서는 그 사실을 적어두는 것까지만 합니다.

Cloudflare Pages 는 무료로도 상업적 이용이 됩니다. 그쪽 설정(`wrangler.jsonc`,
`web\_headers`)도 저장소에 그대로 남겨뒀으니 언제든 되돌릴 수 있습니다.

---

## Vercel 에 연결 (처음 한 번만)

1. [vercel.com](https://vercel.com) → **GitHub 계정으로 로그인**
2. **Add New… → Project**
3. `carbon-biz` 저장소 **Import**
   - 안 보이면 **Adjust GitHub App Permissions** 에서 이 저장소에 권한을 주십시오 (비공개라서 그렇습니다)
4. **빌드 설정은 손대지 마십시오.** `vercel.json` 에 이미 다 적혀 있습니다

   | | |
   |---|---|
   | Framework Preset | Other |
   | Build Command | (없음) |
   | Output Directory | `web` |

5. **Deploy**

1~2분 뒤 `https://carbon-biz-....vercel.app` 주소가 나옵니다.
정확한 주소는 프로젝트 화면 위쪽 **Domains** 에 적혀 있습니다.

---

## 그다음부터

```powershell
.\deploy_web.ps1
```

이 한 줄이 하는 일:

1. `08_build.py` → `09_page.py` → `09_page.py --web` 으로 다시 만들고
2. `test_data.py` 와 `test_ui.js` 로 검사하고 — **하나라도 실패하면 올리지 않습니다**
   (브라우저가 없어 화면 검사를 못 돌린 경우는 실패로 치지 않고 건너뜁니다)
3. `data.jgz` 크기와 설정 파일을 확인하고
4. 커밋하고 `push` 합니다

```powershell
.\deploy_web.ps1 -SkipBuild                  # 이미 만든 web\ 만 올림
.\deploy_web.ps1 -SkipTest                   # 검사 건너뜀 (권하지 않습니다)
.\deploy_web.ps1 -Message "매출 붙임"          # 커밋 메시지 직접
```

**`python src\09_page.py` 만 돌리면 `out\` 만 바뀝니다.** 배포본 `web\` 은 `--web` 을
붙여야 만들어집니다. 이것 때문에 배포된 화면이 로컬과 달랐던 적이 있습니다.

---

## 설정 파일 두 개

| 파일 | 누가 읽나 |
|---|---|
| `vercel.json` | Vercel |
| `web\_headers` | Cloudflare Pages / Workers |

둘 다 같은 것을 지정합니다 — `data.jgz` 를 `application/octet-stream` 으로 내려 달라는 것.

`data.jgz` 는 우리가 직접 gzip 으로 만든 파일이고, 페이지가 앞 두 바이트(`1f 8b`)를 보고
`DecompressionStream` 으로 **스스로 풉니다.** 서버가 `Content-Encoding: gzip` 을 붙이면
브라우저가 먼저 풀어버려 우리 코드가 두 번 푸는 꼴이 됩니다. 확장자를 `.jgz` 로 둔 것도
서버가 알아서 손대지 않게 하려는 것입니다.

`web\_headers` 는 `python src\09_page.py --web` 이 자동으로 만듭니다.
두 파일이 같이 있어도 서로 간섭하지 않습니다.

---

## 올라가는 것 / 안 올라가는 것

**올라갑니다**

- `src\` `tests\` `docs\` — 코드
- `web\` — 배포본 (`index.html` · `data.jgz` · `_headers`)
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

`.github\workflows\check.yml` 이 push 마다 배포본을 검사합니다. 배포는 Vercel 이 하고,
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
지금은 주소만 알면 누구나 봅니다.

- **Vercel** — 프로젝트 Settings → **Deployment Protection** → **Vercel Authentication**.
  Pro 에서는 Password Protection(부가 상품)도 됩니다.
- **Cloudflare** — Zero Trust → Access → Applications → Self-hosted.
  정책을 `@lsitc.com` 으로 끝나는 메일만 통과시키게 두면 됩니다. 50명까지 무료.

---

## Cloudflare 로 되돌리려면

설정은 그대로 남아 있으니 대시보드에서 연결만 하면 됩니다.

1. [dash.cloudflare.com](https://dash.cloudflare.com) → **Compute (Workers & Pages)** → **Create**
2. **Pages → Connect to Git** 로 만들면 주소가 `carbon-biz.pages.dev`,
   **Workers** 로 만들어지면 `carbon-biz.<계정서브도메인>.workers.dev` 입니다.
   실제 주소는 프로젝트 **Settings → Domains & Routes** 에 적혀 있습니다
   (`workers.dev` 가 Disabled 면 Enable 을 눌러야 열립니다)
3. 빌드 설정: Framework preset **None** / Build command **비움** / Output directory **`web`**

`wrangler.jsonc` 의 `name` 은 대시보드의 실제 프로젝트 이름과 같아야 합니다.

두 곳 다 저장소에 연결해 두면 push 한 번에 양쪽 모두 배포됩니다.
한쪽만 쓰시려면 다른 쪽 프로젝트를 지우십시오.

---

## 출처 표시는 지우지 마십시오

화면 아래 설명에 들어 있습니다. 조건입니다.

- 시도 경계 — [MapSVG](https://mapsvg.com/maps/south-korea) · CC BY 4.0
- 배경지도 — OpenStreetMap · ODbL
- 원본 — 한국산업단지공단 「전국등록공장현황」, 공공데이터포털 (이용허락범위 제한 없음)
