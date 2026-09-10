# GitHub 비공개 저장소에 처음 올리는 스크립트. 한 번만 실행하면 됩니다.
#
#   .\setup_git.ps1 -Repo https://github.com/내계정/carbon-biz.git
#
# 저장소는 GitHub 에서 먼저 만들어 두십시오 (New repository → Private → 빈 저장소).
# README·.gitignore 는 체크하지 마십시오. 여기 있는 것을 그대로 올립니다.

param(
  [Parameter(Mandatory = $true)][string]$Repo,
  [string]$Branch = 'main'
)
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

function Say($t, $c = 'Cyan') { Write-Host "`n$t" -ForegroundColor $c }

# ── 0. git 이 있는지 ────────────────────────────────────────────────────────
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
  Write-Host 'git 이 설치돼 있지 않습니다. https://git-scm.com/download/win' -ForegroundColor Red
  exit 1
}

# ── 1. 키 파일이 실수로 올라가지 않는지 먼저 확인 ───────────────────────────
Say '1/5  인증키가 섞여 있지 않은지 확인'
$leak = Get-ChildItem -File -Recurse -Force -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -in '.kakao_key', '.naver_key', '.vworld_key', '.dart_key', '.env' } |
        Where-Object { $_.FullName -notlike '*\.git\*' }
foreach ($f in $leak) {
  $rel = $f.FullName.Substring($PSScriptRoot.Length + 1)
  Write-Host "  $rel — .gitignore 에 있어 올라가지 않습니다" -ForegroundColor DarkGray
}
if (-not $leak) { Write-Host '  키 파일 없음' -ForegroundColor DarkGray }

# ── 2. 배포본이 최신인지 ────────────────────────────────────────────────────
Say '2/5  배포본(web\) 확인'
if (-not (Test-Path web\index.html) -or -not (Test-Path web\data.jgz)) {
  Write-Host '  web\ 이 비어 있습니다. 먼저 만드십시오:' -ForegroundColor Red
  Write-Host '    python src\08_build.py; python src\09_page.py --web' -ForegroundColor Yellow
  exit 1
}
$mb = [math]::Round((Get-Item web\data.jgz).Length / 1MB, 2)
Write-Host "  web\index.html + web\data.jgz ($mb MB)" -ForegroundColor DarkGray
if ($mb -gt 25) {
  Write-Host '  data.jgz 가 25MiB 를 넘습니다. Cloudflare Pages 가 거부합니다.' -ForegroundColor Red
  Write-Host '    $env:SCOPE=''target''; python src\08_build.py; python src\09_page.py --web' -ForegroundColor Yellow
  exit 1
}
if (-not (Test-Path web\_headers)) {
  Write-Host '  web\_headers 가 없습니다. python src\09_page.py --web 을 다시 돌리십시오.' -ForegroundColor Red
  exit 1
}

# ── 3. 저장소 만들기 ────────────────────────────────────────────────────────
Say '3/5  git 저장소 준비'
if (-not (Test-Path .git)) {
  git init -b $Branch | Out-Null
  Write-Host "  새로 만들었습니다 (브랜치 $Branch)" -ForegroundColor DarkGray
} else {
  Write-Host '  이미 git 저장소입니다' -ForegroundColor DarkGray
}

# ── 4. 무엇이 올라가는지 보여주고 커밋 ──────────────────────────────────────
Say '4/5  올라갈 파일'
git add -A
$n = (git diff --cached --name-only | Measure-Object).Count
$big = git diff --cached --name-only | ForEach-Object {
  if (Test-Path $_) { $i = Get-Item $_; if ($i.Length -gt 5MB) { '{0,8:N1} MB  {1}' -f ($i.Length / 1MB), $_ } }
}
Write-Host "  파일 $n 개"
if ($big) { Write-Host '  큰 파일:' -ForegroundColor DarkGray; $big | ForEach-Object { Write-Host "   $_" -ForegroundColor DarkGray } }

if ((git diff --cached --name-only | Measure-Object).Count -eq 0) {
  Write-Host '  바뀐 것이 없습니다' -ForegroundColor DarkGray
} else {
  git commit -m "산업단지 CBAM 영업 지도" | Out-Null
  Write-Host '  커밋했습니다' -ForegroundColor DarkGray
}

# ── 5. 올리기 ───────────────────────────────────────────────────────────────
Say '5/5  GitHub 로 올리기'
if (git remote | Select-String -Quiet '^origin$') { git remote set-url origin $Repo }
else { git remote add origin $Repo }
git push -u origin $Branch

Say '끝났습니다.' 'Green'
Write-Host @'
이제 Cloudflare Pages 에 연결하면, 앞으로는 push 만 하면 자동으로 배포됩니다.

  1. https://dash.cloudflare.com  로그인
  2. 왼쪽 Compute (Workers & Pages) > Create > Pages > Connect to Git
  3. GitHub 계정을 연결하고 carbon-biz 저장소를 고릅니다
     (비공개 저장소도 됩니다. Only select repositories 로 이것만 주셔도 됩니다)
  4. 빌드 설정 - 이 세 가지만 맞추면 됩니다
       Framework preset        None
       Build command           (비워 두십시오)
       Build output directory  web
  5. Save and Deploy

  헤더 설정은 web\_headers 에 이미 들어 있습니다. 따로 만지실 것 없습니다.

다음부터는 이 한 줄이면 끝입니다.

  .\deploy_web.ps1

'@ -ForegroundColor Gray
Write-Host 'Cloudflare Pages 무료 플랜은 상업적 이용이 됩니다. 파일당 25MiB 한도만 지키면 됩니다.' -ForegroundColor DarkGray
