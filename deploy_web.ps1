# 다시 만들고 → 검사하고 → 올린다. 올리면 Cloudflare Pages 가 알아서 배포합니다.
#
#   .\deploy_web.ps1                 데이터부터 다시 만들어 올림
#   .\deploy_web.ps1 -SkipBuild      이미 만든 web\ 을 그대로 올림
#   .\deploy_web.ps1 -Message "연락처 8천곳 추가"

param(
  [switch]$SkipBuild,
  [switch]$SkipTest,
  [string]$Message = ''
)
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

function Step($n, $t) { Write-Host "`n[$n] $t" -ForegroundColor Cyan }
function Note($t)     { Write-Host "  $t" -ForegroundColor DarkGray }

if (-not (Test-Path .git)) {
  Write-Host 'git 저장소가 아직 없습니다. 먼저 한 번 실행하십시오:' -ForegroundColor Red
  Write-Host '  .\setup_git.ps1 -Repo https://github.com/내계정/carbon-biz.git' -ForegroundColor Yellow
  exit 1
}

if (-not $SkipBuild) {
  Step '1/4' '데이터·화면 다시 만들기'
  python src\08_build.py
  if ($LASTEXITCODE -ne 0) { Write-Host '08_build 실패' -ForegroundColor Red; exit 1 }
  python src\09_page.py
  if ($LASTEXITCODE -ne 0) { Write-Host '09_page 실패' -ForegroundColor Red; exit 1 }
  python src\09_page.py --web
  if ($LASTEXITCODE -ne 0) { Write-Host '09_page --web 실패' -ForegroundColor Red; exit 1 }
} else {
  Step '1/4' '다시 만들기 건너뜀 (-SkipBuild)'
}

Step '2/4' '검사'
if ($SkipTest) {
  Note '건너뜀 (-SkipTest)'
} else {
  python tests\test_data.py
  if ($LASTEXITCODE -ne 0) {
    Write-Host '데이터 검사에서 실패했습니다. 올리지 않습니다.' -ForegroundColor Red
    Write-Host '  그래도 올리시려면  .\deploy_web.ps1 -SkipTest' -ForegroundColor Yellow
    exit 1
  }
  if (Test-Path node_modules\playwright) {
    node tests\test_ui.js
    # 종료 코드 2 = 브라우저를 못 찾아 아예 못 돌린 것. 검사 실패가 아니다.
    # 이걸 실패로 보고 배포를 막으면, 브라우저 없는 PC 에서는 영영 못 올린다.
    if ($LASTEXITCODE -eq 2) {
      Note '브라우저가 없어 화면 검사를 건너뜁니다 (데이터 검사는 통과했습니다)'
    } elseif ($LASTEXITCODE -ne 0) {
      Write-Host '화면 검사에서 실패했습니다. 올리지 않습니다.' -ForegroundColor Red
      Write-Host '  그래도 올리시려면  .\deploy_web.ps1 -SkipTest' -ForegroundColor Yellow
      exit 1
    }
  } else { Note 'playwright 없음 — 화면 검사 건너뜁니다' }
}

Step '3/4' '올릴 것 확인'
if (-not (Test-Path web\index.html) -or -not (Test-Path web\data.jgz)) {
  Write-Host '  web\ 이 비어 있습니다.' -ForegroundColor Red; exit 1
}
$mb = [math]::Round((Get-Item web\data.jgz).Length / 1MB, 2)
Note "web\data.jgz  $mb MB"
if ($mb -gt 25) {
  Write-Host '  data.jgz 가 25MiB 를 넘습니다. Cloudflare Pages 가 파일 하나에 두는 한도입니다.' -ForegroundColor Red
  Write-Host '  범위를 줄여 다시 만드십시오:' -ForegroundColor Yellow
  Write-Host '    $env:SCOPE=''target''; python src\08_build.py; python src\09_page.py --web' -ForegroundColor Yellow
  exit 1
}
if (-not (Test-Path web\_headers)) {
  Write-Host '  web\_headers 가 없습니다 (Cloudflare 헤더 설정).' -ForegroundColor Red
  Write-Host '    python src\09_page.py --web' -ForegroundColor Yellow
  exit 1
}

git add -A
if ((git diff --cached --name-only | Measure-Object).Count -eq 0) {
  Note '바뀐 것이 없습니다. 올리지 않습니다.'
  exit 0
}
git diff --cached --stat | Select-Object -Last 12

Step '4/4' 'GitHub 로 올리기'
if (-not $Message) {
  # 커밋 메시지는 날짜와 배포본 크기로 짓는다.
  # (예전에 여기서 영업리스트.csv 줄 수를 세려고 Select-String -Pattern '' 를 썼는데,
  #  빈 패턴은 PowerShell 이 거부한다. 20MB 파일을 훑는 것도 느려서 아예 뺐다.)
  $Message = "갱신 $(Get-Date -Format 'yyyy-MM-dd HH:mm') · data $mb MB"
}
git commit -m $Message | Out-Null
git push

Write-Host "`n올렸습니다. Cloudflare Pages 가 1~2분 안에 배포합니다." -ForegroundColor Green
Note 'https://dash.cloudflare.com 의 Compute > 프로젝트 > Deployments 에서 진행 상황을 봅니다.'
