# 전체 재생성 + 검증. 이 파일 하나만 실행하면 됩니다.
#   .\run_all.ps1
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

function Step($n, $t) { Write-Host "`n[$n] $t" -ForegroundColor Cyan }
function Skip($t)     { Write-Host "  $t" -ForegroundColor DarkGray }

# 없는 폴더는 만들고 시작한다 (data\ 는 git 에 안 올라가므로 처음엔 비어 있다)
foreach ($d in 'data', 'data\emission', 'data\pension', 'data\export', 'data\finance',
                'cache', 'out', 'web') {
    if (-not (Test-Path $d)) { New-Item -ItemType Directory -Path $d | Out-Null }
}

if (-not (Get-ChildItem data -Filter '한국산업단지공단_*.csv' -File -ErrorAction SilentlyContinue)) {
    Write-Host '원본 CSV 가 없습니다. data\ 폴더에 넣으십시오:' -ForegroundColor Red
    Write-Host '  Copy-Item "D:\workspace\cabon\factorymap\한국산업단지공단_*.csv" data\' -ForegroundColor Yellow
    exit 1
}

Step '1/8' '원본 분류'
python src\01_prep.py

Step '2/8' '시도 경계'
if (Test-Path cache\boundary.json) { Skip 'cache\boundary.json 있음 - 건너뜁니다' }
else { python src\10_boundary.py }

Step '3/8' '배출량'
if (Get-ChildItem data\emission -File -ErrorAction SilentlyContinue) { python src\03_emission.py }
else { Skip 'data\emission\ 비어 있음 - 건너뜁니다 (docs\EMISSION.md)' }

Step '4/8' '국민연금 (종업원·인건비)'
if (Get-ChildItem data\pension -File -ErrorAction SilentlyContinue) { python src\04_pension.py }
else { Skip 'data\pension\ 비어 있음 - 건너뜁니다 (README 참고)' }

Step '5/8' '수출 명단'
if (Get-ChildItem data\export -File -ErrorAction SilentlyContinue) { python src\07_export.py }
else { Skip 'data\export\ 비어 있음 - 건너뜁니다' }

Step '6/8' '집계'
python src\08_build.py

Step '7/8' '화면'
python src\09_page.py
python src\09_page.py --web

Step '8/8' '검증'
python tests\test_data.py
if ($LASTEXITCODE -ne 0) { Write-Host '데이터 검증 실패' -ForegroundColor Red; exit 1 }
if (Test-Path node_modules\playwright) { node tests\test_ui.js }
else { Skip 'playwright 미설치 - 화면 검증 건너뜁니다' }

Write-Host "`n완료. out\index.html 을 열어 확인하세요." -ForegroundColor Green
Write-Host "  연락처는 따로:  python src\06_contact.py --key 카카오REST키 --scope target" -ForegroundColor DarkGray
Write-Host "  좌표는 따로:    python src\02_geocode.py --key VWorld키 --scope all --max-calls 38000" -ForegroundColor DarkGray
