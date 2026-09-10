# 전국 21만 곳 좌표 채우기

## 먼저 — 며칠 걸립니다

| | |
|---|---|
| 고유 주소 | **197,215건** (21만 행에 같은 주소가 겹칩니다) |
| 이미 확보 | 8,931건 |
| **남은 것** | **188,285건** |
| 주소당 호출 | 평균 1.5회 (도로명 실패 시 지번 재시도) |
| **필요 호출** | **약 28만 회** |
| API 일일 한도 | **약 4만 회** (키마다 다름 — VWorld 마이페이지에서 확인) |
| **소요** | **7~9일** · 하루 실제 도는 시간은 2~3시간 |

한 번에 끝낼 방법은 없습니다. 대신 **하루치씩 자동으로 돌게** 해뒀습니다.
중간에 끊겨도 손실이 없고, 그날까지 얻은 좌표만으로 지도를 갱신할 수 있습니다.

---

## 하루치 돌리기

```powershell
cd D:\workspace\carbon-biz
python src\02_geocode.py --key 발급받은키 --scope all --max-calls 38000 --max-tries 4
```

| 옵션 | 뜻 |
|---|---|
| `--scope all` | 전국 등록공장 전부 (기본값은 CBAM·열공정만) |
| `--max-calls 38000` | 오늘 쓸 호출 수. 한도 4만보다 조금 적게 잡아 여유를 둡니다 |
| `--max-tries 4` | 주소 하나에 최대 4번까지만 시도. 안 되는 주소에 8번씩 쓰지 않게 |

이렇게 찍힙니다.

```
범위 전체 — 고유 주소 197,215건
  캐시에 없는 주소 188,285건 · 이번 회차 호출 상한 38,000회
   2,000/197,215  신규성공 1,806  실패 194  캐시 0  성공률 90.3%  호출 2,610  551s  남은 186,285건 예상 14.2시간

  이번 회차 호출 상한 38,000회에 도달했습니다.
  여기까지 저장했습니다. 남은 주소 162,410건 — 같은 명령을 다시 실행하면 이어서 합니다.
```

**다음 날 같은 명령을 그대로 다시 치면 됩니다.** 성공한 주소는 `cache\geo_cache.json` 에
남아 있어 건너뜁니다.

### 중간에 멈춰도 됩니다

- `Ctrl+C` — 그 순간까지 저장하고 끝냅니다
- 한도 초과 응답(HTTP 429)을 받으면 스스로 멈춥니다
- 컴퓨터가 꺼져도 200건마다 저장하므로 잃는 건 200건 미만입니다

---

## 매일 자동으로 (권장)

`geocode_daily.ps1` 을 Windows 작업 스케줄러에 걸어두면 손 댈 일이 없습니다.

**1. 키를 한 번 저장합니다** (명령 이력에 키가 남지 않게)

```powershell
cd D:\workspace\carbon-biz
"발급받은키" | Out-File -Encoding ascii .vworld_key
```

`.vworld_key` 는 `.gitignore` 에 들어 있어 저장소에 올라가지 않습니다.

**2. 스케줄러에 등록합니다** — PowerShell 을 **관리자**로 열고

```powershell
cd D:\workspace\carbon-biz
$a = New-ScheduledTaskAction -Execute "powershell.exe" `
     -Argument "-ExecutionPolicy Bypass -File `"$PWD\geocode_daily.ps1`""
$t = New-ScheduledTaskTrigger -Daily -At 2am
Register-ScheduledTask -TaskName "공장 지오코딩" -Action $a -Trigger $t `
     -Description "전국 등록공장 주소를 좌표로 바꾼다 (하루 38,000회)"
```

매일 새벽 2시에 하루치를 돌고, 다 끝나면 `geocode_done.txt` 를 남기고 더 이상
호출하지 않습니다. 진행 기록은 `geocode_log.txt` 에 쌓입니다.

**등록을 풀려면**

```powershell
Unregister-ScheduledTask -TaskName "공장 지오코딩" -Confirm:$false
```

---

## 진행 상황 보기

```powershell
python -c "import json;g=json.load(open('cache\geo_cache.json',encoding='utf-8'));ok=sum(1 for v in g.values() if v and v.get('lat'));print(f'{ok:,} / {len(g):,} 처리 · 전체 197,215건 중 {len(g)/197215*100:.1f}%')"
```

또는 로그 마지막 줄을 봅니다.

```powershell
Get-Content geocode_log.txt -Tail 5
```

## 중간에 지도에 반영하기

기다릴 필요 없습니다. 아무 때나 이 두 줄이면 그때까지의 좌표가 지도에 들어갑니다.

```powershell
python src\08_build.py
python src\09_page.py
```

---

## 알아둘 것

- **좌표는 도로명 기준**이라 부지 중심이 아니라 **출입구 근처**에 찍힙니다.
  대규모 공장일수록 실제 굴뚝 위치와 차이가 큽니다.
- **성공률은 90% 안팎**입니다. 실패분은 주소에 `외 3필지`, `3층 202호` 같은 꼬리표가
  붙어 있거나 주소 자체가 옛것입니다. `geocode_실패.csv` 로 빠집니다.
- **국토교통부 지오코더(`--provider molit`)는 주의하십시오.** 공공데이터포털 이용조건에
  *"API 요청은 실시간으로 사용하셔야 하며 별도의 저장장치나 데이터베이스에 저장할 수 없습니다"*
  라고 되어 있습니다. 우리는 결과를 캐시에 저장하므로 조건에 어긋납니다.
  **VWorld 를 쓰십시오.**
- 더 빠른 길이 있을 수 있습니다. 행정안전부 **주소기반산업지원서비스**(business.juso.go.kr)에서
  도로명주소 전체 DB를 좌표와 함께 파일로 내려받을 수 있다고 알려져 있습니다.
  그게 되면 API 없이 몇 분 만에 끝납니다. 다만 파일 구성과 이용 조건을 제가 확인하지
  못했으니, 시간이 급하시면 그쪽을 먼저 알아보시는 편이 낫습니다.

## 출처

- [VWorld 오픈API](https://www.vworld.kr/dev/v4dv_apiuse_s001.do)
- [국토교통부 지오코더 API — 일일 40,000건, 저장 금지 조건](https://www.data.go.kr/data/15101106/openapi.do)
- [주소기반산업지원서비스](https://business.juso.go.kr/)
