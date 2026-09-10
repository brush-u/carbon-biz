# -*- coding: utf-8 -*-
import json, io, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import paths

paths.need(paths.DATAJSON, 'python src\\08_build.py 를 먼저 돌리십시오')
data = open(paths.DATAJSON, encoding='utf-8').read()

# Leaflet을 파일 안에 넣는다. 사내망·오프라인에서도 CDN 없이 동작하고,
# 아티팩트처럼 외부 스타일시트가 막힌 환경에서도 레이아웃이 깨지지 않는다.
# vendor/ 를 먼저 본다 — npm 설치가 막힌 사내망을 위해 폴더에 동봉해 뒀다.
def leaflet(name):
    for p in (os.path.join(paths.VENDOR, 'leaflet.' + name),
              os.path.join('node_modules', 'leaflet', 'dist', 'leaflet.' + name)):
        if os.path.exists(p):
            return open(p, encoding='utf-8').read()
    sys.exit(
        'leaflet.' + name + ' 을 찾지 못했습니다.\n'
        '  cache\\vendor\\leaflet.' + name + ' 이 있는지 확인하십시오.')

LEAFLET_CSS = leaflet('css')
LEAFLET_JS  = leaflet('js')

# 시도 경계 (9_boundary.py 산출물). 없으면 경계 없이 예전처럼 그린다.
BOUNDARY = open(paths.BOUNDARY, encoding='utf-8').read() \
    if os.path.exists(paths.BOUNDARY) else '{"sido":{}}'

HTML = r'''<title>산업단지 CBAM 영업 지도</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+KR:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600;700&display=swap">
<style>
  :root{
    --ground:#EAEDEC; --surface:#FFFFFF; --sunk:#E3E8E6;
    --line:#C9D2CF; --line-soft:#DCE3E1;
    --ink:#141A19; --ink-mid:#46534F; --ink-soft:#6C7A76;
    --verdigris:#1F6F63; --verdigris-deep:#14524A; --verdigris-wash:#DCE9E6;
    --s1:#2a78d6; --s2:#eb6834; --s3:#1baf7a; --s4:#eda100; --s5:#e87ba4;
    --seq:#2a78d6;
    --warn:#9A6B00; --warn-wash:#F7ECD2;
    --crit:#A6472C; --crit-wash:#F5E3DD;
  }
  @media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
    --ground:#101615; --surface:#171F1D; --sunk:#131B19;
    --line:#2C3936; --line-soft:#222D2B;
    --ink:#E6EDEB; --ink-mid:#A7B5B1; --ink-soft:#7E8D89;
    --verdigris:#59B8A6; --verdigris-deep:#7FD2C2; --verdigris-wash:#17302C;
    --s1:#3987e5; --s2:#d95926; --s3:#199e70; --s4:#c98500; --s5:#d55181;
    --seq:#3987e5;
    --warn:#D3AE5C; --warn-wash:#2C2517;
    --crit:#E08163; --crit-wash:#33201A;
  }}
  :root[data-theme="dark"]{
    --ground:#101615; --surface:#171F1D; --sunk:#131B19;
    --line:#2C3936; --line-soft:#222D2B;
    --ink:#E6EDEB; --ink-mid:#A7B5B1; --ink-soft:#7E8D89;
    --verdigris:#59B8A6; --verdigris-deep:#7FD2C2; --verdigris-wash:#17302C;
    --s1:#3987e5; --s2:#d95926; --s3:#199e70; --s4:#c98500; --s5:#d55181;
    --seq:#3987e5;
    --warn:#D3AE5C; --warn-wash:#2C2517;
    --crit:#E08163; --crit-wash:#33201A;
  }
  /* 글꼴 — Pretendard 가 깔려 있으면 그걸 쓰고, 없으면 웹폰트,
     사내망처럼 둘 다 막히면 윈도우 기본 맑은 고딕으로 내려간다. */
  :root{
    --sans:"Pretendard Variable",Pretendard,"IBM Plex Sans KR",-apple-system,
           "Apple SD Gothic Neo","Malgun Gothic","맑은 고딕",system-ui,sans-serif;
    --mono:"JetBrains Mono","IBM Plex Mono",ui-monospace,"SFMono-Regular",Menlo,Consolas,monospace;
  }
  *{box-sizing:border-box}
  body{background:var(--ground);color:var(--ink);font-family:var(--sans);font-size:18px;line-height:1.65;-webkit-font-smoothing:antialiased}
  .app{max-width:1180px;margin:0 auto;padding:0 20px 72px}

  header{padding:26px 0 16px;border-bottom:2px solid var(--ink)}
  .eyebrow{font-family:var(--mono);font-size:13px;letter-spacing:.16em;text-transform:uppercase;color:var(--ink-soft);margin-bottom:12px}
  h1{font-family:var(--sans);font-weight:800;font-size:clamp(32px,4.8vw,50px);line-height:1.2;margin:0 0 12px;letter-spacing:-.03em}
  h1 em{font-style:normal;color:var(--verdigris)}
  header p{margin:0;color:var(--ink-mid);font-size:17px;max-width:70ch}

  .tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:1px;background:var(--line);border:1px solid var(--line);margin:22px 0 16px}
  .tile{background:var(--surface);padding:15px 17px;display:flex;flex-direction:column;gap:3px}
  .tile .k{font-size:15px;color:var(--ink-mid);font-weight:500}
  .tile .v{font-family:var(--mono);font-size:35.5px;font-weight:700;letter-spacing:-.035em;font-variant-numeric:tabular-nums;line-height:1.15}
  .tile .v small{font-size:17px;font-weight:500;color:var(--ink-mid)}
  .tile .u{font-size:13px;color:var(--ink-soft);font-family:var(--mono)}
  /* 눈이 먼저 가야 할 숫자에만 색을 준다 — 다 칠하면 아무것도 강조되지 않는다 */
  .tile.hi{box-shadow:inset 3px 0 0 var(--verdigris)}
  .tile.hi .v{color:var(--verdigris-deep)}
  .tile.cb .v{color:var(--s1)}
  .tile.ht .v{color:var(--s2)}

  /* 회사명 → 지도 서비스 */
  .nmbtn{font-family:inherit;font-size:inherit;font-weight:600;color:var(--verdigris-deep);
    background:none;border:none;padding:0;text-align:left;cursor:pointer;line-height:inherit}
  .nmbtn:hover{text-decoration:underline}
  .nmbtn::after{content:"↗";font-size:.72em;margin-left:4px;opacity:.5;vertical-align:super}
  .namemenu{position:absolute;z-index:1300;min-width:196px;background:var(--surface);
    border:1px solid var(--line);box-shadow:0 8px 26px rgba(0,0,0,.18);padding:5px}
  .nmhead{padding:7px 9px 8px;font-size:15px;font-weight:600;color:var(--ink);
    border-bottom:1px solid var(--line-soft);margin-bottom:4px;line-height:1.35}
  .nmhead span{display:block;font-size:13px;font-weight:400;color:var(--ink-soft);margin-top:2px}
  .namemenu a{display:block;padding:7px 9px;font-size:15.5px;color:var(--ink-mid);text-decoration:none}
  .namemenu a:hover{background:var(--verdigris-wash);color:var(--verdigris-deep)}
  .namemenu .nmhere{display:block;width:100%;text-align:left;font-family:inherit;
    padding:8px 9px;font-size:15.5px;font-weight:600;cursor:pointer;border:none;
    background:var(--verdigris-wash);color:var(--verdigris-deep);
    border-bottom:1px solid var(--line-soft)}
  .namemenu .nmhere:hover{background:var(--verdigris);color:#fff}
  .namemenu .nmno{display:block;padding:7px 9px;font-size:14px;color:var(--ink-soft);
    border-bottom:1px solid var(--line-soft)}
  .mlink{display:flex;flex-wrap:wrap;gap:4px;margin-top:8px;padding-top:8px;border-top:1px solid #e3e3e3}
  .mlink a{font-size:13px;padding:2px 7px;border:1px solid #ccc;color:#1a5f56;text-decoration:none}
  .mlink a:hover{background:#eef5f3}

  .notice{display:flex;gap:10px;padding:14px 16px;font-size:16px;line-height:1.65;align-items:flex-start;margin-bottom:20px}
  .notice.warn{background:var(--warn-wash);border-left:3px solid var(--warn)}
  .notice b{font-weight:600}

  /* 조회조건 — 라벨 열을 고정해 행마다 시작점이 맞도록 격자로 짠다.
     지도(Leaflet)가 스크롤 시 이 위를 덮지 않도록 z-index를 높게 둔다. */
  .controls{display:grid;grid-template-columns:auto minmax(0,1fr);gap:9px 14px;align-items:center;
    padding:14px 16px;background:var(--surface);border:1px solid var(--line);
    margin-bottom:22px;position:sticky;top:0;z-index:600}
  .cg-l{font-family:var(--mono);font-size:12.5px;font-weight:600;letter-spacing:.08em;color:var(--ink-soft);
    text-align:right;white-space:nowrap;align-self:center;padding-top:1px}
  .cg-l i{display:block;font-style:normal;font-size:11px;font-weight:400;letter-spacing:.02em;opacity:.75}
  .cf{display:flex;align-items:center;gap:7px;flex-wrap:wrap;min-width:0}
  /* .cf 의 display:flex 가 브라우저 기본 [hidden]{display:none} 을 이겨서,
     숨긴 줄이 격자 칸을 계속 차지했다. 그러면 라벨과 입력이 한 칸씩 밀려
     설명글이 라벨 칸으로 들어가며 라벨 칸이 1,100px 로 벌어진다. */
  .controls [hidden]{display:none!important}
  .cf.spread{justify-content:space-between}
  .cf.spread>.q-wrap{display:flex;gap:7px;flex:1 1 260px;min-width:0}
  @media (min-width:821px) and (max-height:780px){.controls{position:static}}

  /* 좁은 화면 — 조건이 화면의 절반을 먹으면 지도도 목록도 못 본다.
     그래서 오른쪽 서랍으로 접어 넣고, 오른쪽 아래 단추로 여닫는다. */
  .cclose{display:none;position:absolute;right:12px;top:10px;background:none;border:none;
    font-size:27.5px;line-height:1;color:var(--ink-soft);cursor:pointer}
  .fabf{display:none;position:fixed;right:14px;bottom:14px;z-index:1150;
    font-family:inherit;font-size:16px;font-weight:600;padding:12px 18px;cursor:pointer;
    background:var(--verdigris);color:#fff;border:none;border-radius:999px;
    box-shadow:0 6px 20px rgba(0,0,0,.22);align-items:center;gap:7px}
  .fabf .fabn{font-family:var(--mono);font-size:13px;background:rgba(255,255,255,.26);
    padding:1px 7px;border-radius:999px}
  @media (max-width:820px){
    .controls{position:fixed;top:0;right:0;height:100%;width:min(440px,94vw);z-index:1200;
      grid-template-columns:1fr;gap:4px 0;margin:0;padding:52px 18px 44px;
      overflow-y:auto;overscroll-behavior:contain;
      border:none;border-left:3px solid var(--verdigris);
      box-shadow:-20px 0 48px rgba(0,0,0,.16);
      transform:translateX(101%);visibility:hidden;
      transition:transform .28s cubic-bezier(.4,0,.2,1),visibility 0s .28s}
    .controls.open{transform:translateX(0);visibility:visible;
      transition:transform .28s cubic-bezier(.4,0,.2,1),visibility 0s}
    .cg-l{text-align:left;margin-top:11px}
    .cf.spread{flex-wrap:wrap}
    .cclose{display:block}
    .fabf{display:inline-flex}
  }
  .chipbtn{font-family:inherit;font-size:15.5px;padding:6px 12px;cursor:pointer;background:var(--surface);border:1px solid var(--line);color:var(--ink-mid);display:inline-flex;align-items:center;gap:6px}
  .chipbtn:hover{border-color:var(--verdigris)}
  .chipbtn[aria-pressed="true"]{background:var(--verdigris);border-color:var(--verdigris);color:#fff;font-weight:600}
  :root[data-theme="dark"] .chipbtn[aria-pressed="true"]{color:#0B1211}
  @media (prefers-color-scheme:dark){:root:not([data-theme="light"]) .chipbtn[aria-pressed="true"]{color:#0B1211}}
  .chipbtn i{width:9px;height:9px;flex:none;border-radius:2px}
  .chipbtn .ct{font-family:var(--mono);font-size:13px;font-weight:600;opacity:.8}
  /*__LEAFLET_CSS__*/
  #lmap{height:620px;width:100%;background:var(--sunk)}
  .leaflet-container{font-family:var(--sans);font-size:15px;background:var(--sunk)}
  .leaflet-popup-content{margin:11px 13px;font-size:15.5px;line-height:1.6}
  .leaflet-popup-content b{font-weight:600}
  .leaflet-popup-content .sub2{color:#666;font-size:13px}
  .popdtl{margin-top:8px;font-family:inherit;font-size:14.5px;padding:4px 10px;cursor:pointer;
    background:#1F6F63;color:#fff;border:none}
  .leaflet-control-attribution{font-size:11.5px}
  select{font-family:inherit;font-size:15.5px;padding:6px 9px;border:1px solid var(--line);background:var(--surface);color:var(--ink);
    flex:0 1 190px;min-width:150px;max-width:230px}
  .zoomctl{position:absolute;right:8px;top:8px;display:flex;flex-direction:column;gap:1px;z-index:5}
  .zoomctl button{width:28px;height:28px;font-family:var(--mono);font-size:16px;line-height:1;
    background:var(--surface);border:1px solid var(--line);color:var(--ink);cursor:pointer}
  .zoomctl button:hover{border-color:var(--verdigris);color:var(--verdigris)}
  .maphint{font-size:14px;color:var(--ink-soft);margin-top:7px;line-height:1.55}
  /* 업체 상세 — 전화 걸기 직전에 보는 화면.
     목록 사이에 끼워 넣으면 표가 밀려 어디를 눌렀는지 놓친다.
     그래서 오른쪽에서 밀려 나오는 서랍으로 띄우고, 목록은 그대로 둔다. */
  .dtl{position:fixed;top:0;right:0;height:100%;width:min(480px,95vw);z-index:1200;
    background:var(--surface);border-left:3px solid var(--verdigris);
    box-shadow:-20px 0 48px rgba(0,0,0,.16);
    padding:22px 24px 48px;overflow-y:auto;overscroll-behavior:contain;
    transform:translateX(101%);visibility:hidden;
    transition:transform .28s cubic-bezier(.4,0,.2,1),visibility 0s .28s}
  .dtl.open{transform:translateX(0);visibility:visible;
    transition:transform .28s cubic-bezier(.4,0,.2,1),visibility 0s}
  .dscrim{position:fixed;inset:0;z-index:1199;background:rgba(11,18,17,.32);
    opacity:0;visibility:hidden;pointer-events:none;
    transition:opacity .28s,visibility 0s .28s}
  .dscrim.open{opacity:1;visibility:visible;pointer-events:auto;
    transition:opacity .28s,visibility 0s}
  @media (prefers-reduced-motion:reduce){.dtl,.dscrim{transition:none}}
  .dclose{position:absolute;right:14px;top:12px;background:none;border:none;
    font-size:27.5px;line-height:1;color:var(--ink-soft);cursor:pointer}
  .dclose:hover{color:var(--ink)}
  .dtitle{font-size:23px;font-weight:700;letter-spacing:-.02em;padding-right:28px}
  .dsub{font-size:15px;color:var(--ink-soft);margin-top:3px}
  .dscore{margin-top:12px;font-size:15px;color:var(--ink-mid)}
  .dscore b{font-family:var(--mono);font-size:30px;font-weight:700;color:var(--verdigris-deep)}
  .dscore span{margin-left:4px}
  .dwhy{display:flex;flex-wrap:wrap;gap:5px;margin-top:7px}
  .wchip{font-size:13px;padding:2px 8px;background:var(--verdigris-wash);
    color:var(--verdigris-deep);border:1px solid var(--verdigris)}
  .dsect{margin:16px 0 6px;font-family:var(--mono);font-size:12px;letter-spacing:.12em;
    color:var(--ink-soft);border-bottom:1px solid var(--line-soft);padding-bottom:5px}
  .drow{display:flex;gap:14px;padding:5px 0;font-size:15.5px;line-height:1.55}
  .drow>span{flex:0 0 88px;color:var(--ink-soft);font-size:14.5px;padding-top:2px}
  .drow>b{font-weight:500;color:var(--ink);min-width:0;word-break:break-word}
  .drow b.up{color:var(--s3)} .drow b.down{color:var(--crit)}
  .drow b.hi{color:var(--verdigris-deep);font-weight:700}
  .dim{color:var(--ink-soft);font-size:14px;font-weight:400}
  .dempty{margin:5px 0 2px;padding:9px 11px;font-size:13px;line-height:1.65;
    color:var(--ink-soft);background:var(--sunk);border-left:2px solid var(--line)}
  .dempty code{font-family:var(--mono);font-size:12px;background:var(--surface);
    padding:1px 5px;border:1px solid var(--line);color:var(--ink-mid);
    display:inline-block;margin-top:3px;word-break:break-all}
  .dnote code{font-family:var(--mono);font-size:12px;background:var(--surface);
    padding:1px 5px;border:1px solid var(--line);word-break:break-all}
  .dnote{margin-top:10px;font-size:14px;color:var(--ink-soft);line-height:1.6}
  .dtl .mlink{margin:0;padding:0;border:none}

  /* 어느 정보가 몇 곳에 붙었는지 — 내려받기 전에 알아야 한다 */
  .cover{display:flex;flex-wrap:wrap;gap:6px;align-items:center;margin:10px 0 4px}
  .cvlab{font-size:14px;color:var(--ink-soft);margin-right:2px}
  .cvlab b{color:var(--ink);font-weight:700;font-family:var(--mono)}
  .cvi{font-size:14px;padding:3px 9px;border:1px solid var(--line);color:var(--ink-mid);
    font-family:var(--mono);letter-spacing:.01em}
  .cvi b{font-weight:700;color:var(--ink)}
  .cvp{margin-left:5px;opacity:.6;font-size:12px}
  .cvi.zero{color:var(--crit);border-color:var(--crit);opacity:.85}
  .cvi.zero b{color:var(--crit)}
  .dlnote{margin:8px 0 10px;padding:11px 14px;font-size:14.5px;line-height:1.6;
    background:var(--warn-wash);border-left:3px solid var(--warn);color:var(--ink-mid)}
  .dlnote b{color:var(--ink);font-weight:600}
  .dlfix{margin:6px 0 0;padding-left:18px}
  .dlfix li{margin:2px 0;font-family:var(--mono);font-size:13px}

  .sortbox{display:inline-flex;align-items:center;gap:6px;font-size:14.5px;color:var(--ink-soft)}
  .sortbox select{flex:0 0 auto;min-width:140px}
  .chipbtn.dl{border-color:var(--verdigris);color:var(--verdigris-deep);font-weight:600}

  .maplegend{display:flex;flex-wrap:wrap;gap:14px;margin:0 0 10px;font-size:14px;color:var(--ink-mid)}
  .maplegend span{display:inline-flex;align-items:center;gap:6px}
  .maplegend i{flex:none}
  .maplegend i.dot{width:8px;height:8px;border-radius:50%;background:var(--s1)}
  .maplegend i.area{width:15px;height:11px;background:var(--seq);opacity:.42;border:1px solid var(--seq)}
  .mapwarn{background:var(--warn-wash);border-left:3px solid var(--warn);
    padding:10px 13px;margin-bottom:11px;font-size:14.5px;line-height:1.6;color:var(--ink)}
  .mapwarn b{font-weight:600}
  input[type=search]{font-family:inherit;font-size:16.5px;padding:7px 11px;border:1px solid var(--line);background:var(--surface);color:var(--ink);
    width:100%;min-width:0}
  input:focus-visible,button:focus-visible{outline:2px solid var(--verdigris);outline-offset:1px}

  .cols{display:grid;grid-template-columns:minmax(0,1.15fr) minmax(0,1fr);gap:18px;margin-bottom:22px}
  @media (max-width:880px){.cols{grid-template-columns:1fr}}
  .card{background:var(--surface);border:1px solid var(--line);padding:17px}
  .card>h2{font-family:var(--sans);font-size:21.5px;font-weight:700;margin:0 0 5px;letter-spacing:-.02em}
  .card>.sub{font-size:14.5px;color:var(--ink-soft);margin-bottom:14px}

  /* isolate — Leaflet 내부 z-index(400~800)를 이 안에 가둔다.
     이게 없으면 스크롤할 때 지도가 상단 조회조건을 덮는다. */
  .mapwrap{position:relative;z-index:0;isolation:isolate}
  .card{position:relative;z-index:0}
  svg{display:block;width:100%;height:auto}
  svg text{font-family:var(--sans)}
  .tip{position:absolute;pointer-events:none;background:var(--ink);color:var(--ground);font-size:13px;line-height:1.55;padding:8px 10px;white-space:nowrap;z-index:9;opacity:0;transition:opacity .1s}
  .tip b{font-family:var(--mono)}

  .ebox{display:grid;grid-template-columns:repeat(auto-fit,minmax(215px,1fr));gap:12px;margin-bottom:16px}
  .ecard{background:var(--surface);border:1px solid var(--line);padding:14px 15px}
  .ecard.hi{border-left:3px solid var(--verdigris)}
  .ek{font-size:15px;font-weight:600;color:var(--ink);margin-bottom:10px}
  .erow{display:flex;justify-content:space-between;align-items:baseline;gap:10px;padding:4px 0;font-size:15.5px;color:var(--ink-mid)}
  .erow b{font-family:var(--mono);font-size:18.5px;font-weight:700;color:var(--ink);font-variant-numeric:tabular-nums}
  .en{font-size:13px;color:var(--ink-soft);margin-top:10px;padding-top:8px;border-top:1px solid var(--line-soft);line-height:1.5}
  /* 배출량 열은 지우지 않고 감춘다 — 지우면 thead/tbody 열 수가 어긋난다 */
  /* 열 순서: 1 회사명 2 업종 3 열공정 4 배출량 5 매출액 6 생산품 7 산업단지 8 주소
     감춘 열도 nth-child 로는 세어지므로 번호는 그대로 쓴다 */
  /* 1 회사명 2 업종 3 열공정 4 우선순위 5 종업원 6 연락처 7 배출량 8 매출 9 생산품 10 산업단지 */
  #ft th:nth-child(1),#ft td:nth-child(1){min-width:168px}
  #ft th:nth-child(9),#ft td:nth-child(9){min-width:180px}
  #ft th:nth-child(10),#ft td:nth-child(10){min-width:150px}
  #ft.noemit .ec{display:none}
  #ft.nofin .fc{display:none}
  #ft.nopen .pc{display:none}
  #ft.notel .tc{display:none}
  #ft .tc{white-space:nowrap;min-width:118px}
  #ft .sc{min-width:52px}
  .scv{display:inline-block;min-width:30px;padding:2px 7px;font-family:var(--mono);
    font-size:14.5px;font-weight:700;background:var(--sunk);color:var(--ink-mid)}
  .scv.hot{background:var(--verdigris);color:#fff}
  .tg{display:inline-block;font-family:var(--mono);font-size:11.5px;padding:1px 5px;margin-left:4px;
    border:1px solid var(--line);color:var(--ink-soft)}
  .tg3,.tg4{background:var(--verdigris-wash);border-color:var(--verdigris);color:var(--verdigris-deep)}
  .tg4{font-weight:700}
  .tg1{background:var(--crit-wash);border-color:var(--crit);color:var(--crit)}
  .tg5{background:var(--crit);border-color:var(--crit);color:#fff;font-weight:700}
  .exchip{display:inline-block;font-size:12px;padding:1px 6px;
    background:var(--warn-wash);border:1px solid var(--warn);color:var(--ink)}
  #ft .fc{white-space:nowrap;min-width:104px}
  #ft .fc .sub{white-space:normal}
  .etag.lst{background:var(--verdigris-wash);border-color:var(--verdigris);color:var(--verdigris-deep)}
  #ft .n{white-space:nowrap;min-width:120px}
  #ft .n .sub{white-space:normal}
  .etag{display:inline-block;font-family:var(--mono);font-size:12px;letter-spacing:.04em;padding:1px 5px;border:1px solid var(--line);color:var(--ink-soft);white-space:nowrap}
  .etag.ets{background:var(--warn-wash);border-color:var(--warn);color:var(--ink)}

  .hintline{font-size:14.5px;color:var(--ink-soft);line-height:1.6}
  .hintline b{color:var(--ink-mid);font-weight:600}
  .hintline a{color:var(--verdigris-deep)}

  .boot{padding:22px 18px;margin-bottom:20px;background:var(--surface);border:1px solid var(--line);
    font-size:16.5px;color:var(--ink-mid);line-height:1.7}
  .boot b{color:var(--crit)}

  .barlist{display:flex;flex-direction:column;gap:7px}
  .bar{display:grid;grid-template-columns:46px 1fr 64px;gap:9px;align-items:center;cursor:pointer;background:none;border:none;padding:2px 0;font-family:inherit;text-align:left}
  .bar:hover .bname{color:var(--verdigris)}
  .bname{font-size:15.5px;color:var(--ink);font-weight:500}
  .btrack{height:16px;background:var(--sunk);position:relative;overflow:hidden;display:flex}
  .btrack i{display:block;height:100%}
  .bval{font-family:var(--mono);font-size:15px;font-weight:600;text-align:right;font-variant-numeric:tabular-nums;color:var(--ink)}
  .bar[aria-pressed="true"] .bname{color:var(--verdigris);font-weight:600}

  .legend{display:flex;flex-wrap:wrap;gap:12px;margin:0 0 12px}
  .legend span{display:inline-flex;align-items:center;gap:6px;font-size:14.5px;color:var(--ink-mid)}
  .legend i{width:11px;height:11px;flex:none;border-radius:2px}

  .twrap{overflow:auto;border:1px solid var(--line);max-height:540px}
  table{width:100%;border-collapse:collapse;font-size:16.5px;background:var(--surface)}
  thead th{position:sticky;top:0;background:var(--sunk);font-family:var(--mono);font-size:12.5px;font-weight:600;letter-spacing:.05em;color:var(--ink-mid);text-align:left;padding:9px 11px;border-bottom:1px solid var(--line);white-space:nowrap;z-index:2}
  td{padding:10px 12px;border-bottom:1px solid var(--line-soft);vertical-align:top}
  tr:last-child td{border-bottom:none}
  td.n,th.n{text-align:right;font-variant-numeric:tabular-nums}
  td.n{font-family:var(--mono)}
  td .sub{display:block;font-size:14px;color:var(--ink-soft);margin-top:3px}
  tbody tr:hover{background:var(--verdigris-wash)}
  .kchip{display:inline-block;font-family:var(--mono);font-size:12.5px;font-weight:600;padding:3px 7px;color:#fff;white-space:nowrap}
  :root[data-theme="dark"] .kchip{color:#0B1211}
  @media (prefers-color-scheme:dark){:root:not([data-theme="light"]) .kchip{color:#0B1211}}

  section{margin-bottom:22px}
  section>h2{font-family:var(--sans);font-size:26.5px;font-weight:750;margin:0 0 5px;letter-spacing:-.03em}
  section>.sub{font-size:15.5px;color:var(--ink-soft);margin-bottom:13px}
  .rowcount{font-family:var(--mono);font-size:14.5px;color:var(--ink-soft);margin-top:9px}

  details{border:1px solid var(--line);background:var(--surface);padding:0}
  summary{padding:14px 17px;cursor:pointer;font-weight:600;font-size:17px}
  summary:hover{background:var(--sunk)}
  .dbody{padding:0 17px 17px;font-size:16.5px;color:var(--ink-mid);line-height:1.75}
  .dbody h3{font-size:16.5px;color:var(--ink);margin:17px 0 7px}
  .dbody ul{margin:0;padding-left:19px;display:flex;flex-direction:column;gap:6px}
  .dbody code{font-family:var(--mono);font-size:15px;background:var(--sunk);padding:1px 5px;color:var(--ink)}
  footer{border-top:1px solid var(--line);padding-top:17px;margin-top:28px;font-size:15px;color:var(--ink-soft);line-height:1.65}
  @media (prefers-reduced-motion:reduce){*{transition:none!important}}
</style>

<div class="app">
  <header>
    <div class="eyebrow" id="eyebrow"></div>
    <h1>산업단지 입주업체 <em>CBAM 영업</em> 지도</h1>
    <p>산업단지에 입주한 공장을 업종·품목으로 걸러 <b>탄소 규제가 곧 닿을 곳</b>을 찾는 도구입니다.
       회사마다 규모·연락처·배출·수출 여부를 한 화면에 모아, 전화를 걸 순서를 정할 수 있게 했습니다.</p>
  </header>

  <div class="boot" id="boot">전국 등록공장 데이터를 불러오는 중입니다… (약 6MB)</div>

  <div class="controls" id="controls">
    <button class="cclose" id="cclose" type="button" aria-label="조건 닫기">×</button>
    <span class="cg-l">분류</span>
    <div class="cf"><select id="secf"></select><select id="pmf"></select><select id="cxtf"></select></div>

    <span class="cg-l">열공정 <i>고온</i></span>
    <div class="cf" id="heatf"></div>

    <span class="cg-l">CBAM <i>EU</i></span>
    <div class="cf" id="cbf"></div>

    <span class="cg-l" id="regl" hidden>규제</span>
    <div class="cf" id="regf" hidden></div>

    <span class="cg-l" id="szl" hidden>규모 <i>종업원</i></span>
    <div class="cf" id="szf" hidden></div>

    <span class="cg-l">영업</span>
    <div class="cf" id="bizf"></div>

    <span class="cg-l"></span>
    <div class="cf"><span class="hintline">
      <b>CBAM</b> = EU 탄소국경조정제도가 지목한 6개 품목군 중 제조업에 해당하는 5개 ·
      <b>열공정</b> = CBAM 품목은 아니지만 고온 공정을 써서 연료 배출이 큰 곳 (우리가 만든 구분)
      <a href="#howto">자세히</a>
    </span></div>

    <span class="cg-l">검색</span>
    <div class="cf spread">
      <div class="q-wrap"><input type="search" id="q" placeholder="회사명 · 생산품 · 단지 · 주소"></div>
      <button class="chipbtn" id="reset" type="button">초기화</button>
    </div>
  </div>

  <div class="cols">
    <div class="card">
      <h2>지역 분포</h2>
      <div class="sub" id="mapsub"></div>
      <div class="maplegend">
        <span><i class="dot"></i>점 = 공장 한 곳 (좌표 확보분)</span>
        <span><i class="area"></i>시도 색 진하기 = 조건에 걸린 공장 수</span>
      </div>
      <div class="mapwarn" id="mapwarn" hidden></div>
      <div class="mapwrap" id="mapwrap"><div id="lmap"></div></div>
      <div class="maphint" id="maphint"></div>
    </div>
    <div class="card">
      <h2>시도별 구성</h2>
      <div class="sub">막대를 누르면 해당 시도로 필터됩니다</div>
      <div class="legend" id="legend"></div>
      <div class="barlist" id="bars"></div>
    </div>
  </div>

  <div class="tiles" id="tiles"></div>

  <section>
    <h2>산업단지 순위</h2>
    <div class="sub">현재 조건에 걸린 공장이 있는 산업단지 <span id="cxn"></span>개 · 단지를 누르면 아래 목록이 그 단지로 좁혀집니다</div>
    <div class="twrap"><table id="cxt"><thead><tr>
      <th>산업단지 / 유형</th><th>지역</th><th class="n">조건 일치</th><th class="n">단지 전체</th><th class="n">비중</th><th>주요 업종</th>
    </tr></thead><tbody></tbody></table></div>
  </section>

  <section>
    <h2>업체 목록</h2>
    <div class="sub">행을 누르면 오른쪽에서 상세가 열립니다 (ESC 로 닫기) · 회사명을 누르면 지도 서비스로 바로 갑니다 · 화면에는 300건까지, 내려받기는 전체</div>
    <div class="sub" id="f-hint" style="margin-top:-8px"></div>
    <div class="cover" id="cover"></div>
    <div class="dlnote" id="scorewarn" hidden></div>
    <div class="dlnote" id="dlnote" hidden></div>
    <div class="twrap"><table id="ft"><thead><tr>
      <th>회사명</th><th>업종</th><th>열공정</th><th class="n sc">우선<br><small>순위</small></th><th class="n pc" id="th-p">종업원<br><small>국민연금</small></th><th class="tc" id="th-t">연락처</th><th class="n ec" id="th-e">배출량<br><small>tCO₂eq</small></th><th class="n fc" id="th-f">매출액<br><small>DART</small></th><th>생산품</th><th>산업단지</th>
    </tr></thead><tbody></tbody></table></div>
    <div class="rowcount" id="fcount"></div>
  </section>

  <section>
    <h2>왜 「규제 밖」이 영업 대상인가</h2>
    <div class="sub">배출량을 나라에 보고해야 하는 문턱은 아래와 같습니다.
      이 문턱을 넘는 곳은 이미 담당자도, 컨설팅 업체도 있습니다.
      <b>문턱 아래에 있는데 CBAM 품목을 만드는 곳</b>이 아무 준비 없이 규제를 맞는 자리이고,
      그래서 우선순위 점수에서 「규제 밖」에 20점을 줍니다.</div>
    <div class="ebox">
      <div class="ecard">
        <div class="ek">배출권거래제 (ETS)</div>
        <div class="erow"><span>업체 단위</span><b>125,000</b></div>
        <div class="erow"><span>사업장 단위</span><b>25,000</b></div>
        <div class="erow"><span>자발적 참여</span><b>3,000</b></div>
        <div class="en">최근 3년 연평균 tCO₂eq · 할당대상업체 2,030건 공개</div>
      </div>
      <div class="ecard">
        <div class="ek">목표관리제</div>
        <div class="erow"><span>업체 단위</span><b>50,000</b></div>
        <div class="erow"><span>사업장 단위</span><b>15,000</b></div>
        <div class="erow"><span>관리업체 수</span><b>348</b></div>
        <div class="en">2022-03-25 기준 · 2025-06-30 고시</div>
      </div>
      <div class="ecard">
        <div class="ek">국가 배출량 (2024 잠정)</div>
        <div class="erow"><span>총배출</span><b>691.6</b></div>
        <div class="erow"><span>산업 부문</span><b>285.9</b></div>
        <div class="erow"><span>전환·발전</span><b>218.3</b></div>
        <div class="en">백만 tCO₂eq · 2006 IPCC 기준 · 전년 대비 2% 감소</div>
      </div>
      <div class="ecard hi" id="ecard-gap">
        <div class="ek">규제 안과 밖</div>
        <div class="erow"><span>규제 안</span><b id="e-in">—</b></div>
        <div class="erow"><span>규제 밖</span><b id="e-out">—</b></div>
        <div class="en" id="e-note">배출량 파일을 넣으면 여기에 구분이 표시됩니다</div>
      </div>
    </div>
    <div class="notice" id="e-hint">
      <span><b>배출량 데이터를 붙이려면</b> — 공공데이터포털에서 <code>할당대상업체 현황</code>(2,030행)과
      <code>관리업체 명세서 배출량</code>(10,557행) 두 파일을 받아 <code>emission\\</code> 폴더에 넣고
      <code>python 8_emission.py</code> 를 돌리면 됩니다. 자세한 것은 <code>EMISSION.md</code>에 있습니다.</span>
    </div>
  </section>

  <div class="notice warn">
    <span><b>이 화면의 성격</b> — 업종은 생산품 자유기술 텍스트에서 <b>추정</b>한 것이고, 위치는 <b id="posnote">원본에 좌표가 없어 시도 대표 좌표에 모아 표시한 것</b>입니다.
    목록과 필터는 <b>등록공장 217,048곳 전부</b>를 대상으로 합니다. 다만 <b>지도의 점은 지오코딩을 마친 곳만</b> 찍힙니다 —
    나머지는 시도 구역 색으로만 보입니다. 더 찍으려면 <code>2_geocode.py</code>로 좌표를 늘리면 됩니다.
    전체 분류 결과는 <code>전체공장_분류결과.csv</code>에 있습니다. 자세한 방법과 한계는 맨 아래에 정리했습니다.</span>
  </div>

  <details id="howto" open>
    <summary>용어와 분류 방법 — 이 숫자를 인용하기 전에 읽어야 할 것</summary>
    <div class="dbody">
      <h3>CBAM 대상 후보란</h3>
      <ul>
        <li><b>CBAM(탄소국경조정제도)</b>은 EU가 수입품에 그 제품을 만들며 나온 탄소만큼 값을 물리는 제도입니다.
            2026년부터 확정기간이 시작되고 첫 신고 기한은 2027년 9월 30일입니다.</li>
        <li>규정이 지목한 품목군은 <b>철강 · 알루미늄 · 시멘트 · 비료 · 수소 · 전력</b> 여섯입니다.
            이 중 <b>전력은 뺐습니다</b> — 전기를 수입할 때 붙는 것이라 발전기나 태양광 발전장치를
            만드는 제조업은 대상이 아닙니다. 그래서 화면에는 <b>다섯 개</b>가 나옵니다.</li>
        <li>여기 잡힌 9,324곳은 <b>후보</b>입니다. 생산품 텍스트로 추정했고, EU로 수출하는지는 알 수 없습니다.</li>
      </ul>
      <h3>열공정은 왜 조건에 있나</h3>
      <ul>
        <li><b>열공정은 규제 용어가 아니라 우리가 만든 구분입니다.</b> 공식 분류에 이런 항목은 없습니다.</li>
        <li>CBAM 다섯 품목만 보면 9,324곳입니다. 그런데 탄소 배출을 세어야 할 곳은 그보다 넓습니다 —
            <b>1,000℃ 넘는 용해·소성로를 돌리거나, 보일러로 건조·증기를 쓰는 공장</b>은 품목과 무관하게
            연료 연소 배출이 큽니다. 김을 말리는 공장도 그렇습니다.</li>
        <li>이런 곳은 (1) 원청이 공급망 배출량을 요구하기 시작했고, (2) EU가 CBAM 품목을 넓히면 바로 들어오며,
            (3) 국내 배출권거래제 문턱에 가까워지면 곧 규제 대상이 됩니다.
            <b>즉 지금 배출량 산정을 도와줄 대상</b>이라 조건으로 넣었습니다.</li>
        <li>판정 근거는 생산품 텍스트입니다. <code>용해·소성</code> 4,202곳(주물·알루미늄괴·시멘트·유리·도자),
            <code>건조·증기</code> 5,551곳(제지·염색·식품건조·도장).</li>
      </ul>
      <h3>품목은 어떻게 만들었나</h3>
      <ul>
        <li>생산품이 자유기술이라 그대로는 고를 수가 없습니다. 쉼표·슬래시로 끊어 낱말을 세고,
            <b>업종마다 자주 나오는 낱말 60개</b>를 그 업종의 품목 목록으로 삼았습니다.</li>
        <li>업종을 고르면 품목 목록이 그 업종 것으로 바뀝니다. 예를 들어 기계·장비를 고르면
            금형·기계부품·밸브·열교환기가, 1차 금속을 고르면 강관·주물·알루미늄괴가 나옵니다.</li>
        <li><b>전체의 36%에만 품목이 붙습니다.</b> 나머지는 표기가 제각각이라 묶이지 않았습니다.
            그런 것은 검색창으로 찾으십시오.</li>
      </ul>
      <h3>원본 데이터</h3>
      <ul>
        <li>한국산업단지공단 「전국등록공장현황 등록공장현황자료」 2024-12-31 기준, 217,048건, 연 1회 갱신.</li>
        <li>제공 컬럼은 <code>순번 · 회사명 · 단지명 · 생산품 · 공장주소</code> 다섯 개뿐입니다. <b>업종코드(KSIC)도, 위경도도, 종업원수도, 사업자등록번호도 없습니다.</b></li>
        <li>단지명이 비어 있는 행이 132,937건(61.2%)입니다. 등록공장의 다수가 산업단지 밖 개별입지입니다.</li>
      </ul>
      <h3>품목군 추정 방법</h3>
      <ul>
        <li>생산품 텍스트에 CBAM 대상 CN코드 범위에 대응하는 키워드 규칙을 적용했습니다. 철강(CN 72 및 73 일부), 알루미늄(76), 시멘트(2523), 비료(2808·2814·3102·3105), 수소(2804.10).</li>
        <li>오분류를 줄이려고 제외 규칙을 함께 걸었습니다. 시멘트에서 기와·블록·몰탈·혼화제·레미콘, 비료에서 유기질·부산물·퇴비·요소수, 수소에서 과산화수소·연료전지·센서를 뺐습니다.</li>
        <li><b>전력은 분류에서 뺐습니다.</b> CBAM의 전력은 전기 수입에 적용되는 것이라, 발전기·태양광 발전장치를 만드는 제조업은 대상이 아닙니다. 규칙을 처음 돌렸을 때 1,301건이 잡혔는데 전수가 발전설비 제조업이었습니다.</li>
        <li>생산품은 자유기술 텍스트입니다. 표기가 제각각이라 <b>누락과 과대포집이 모두 남아 있습니다.</b> 이 숫자는 규모 감을 잡는 용도이지 확정 집계가 아닙니다.</li>
      </ul>
      <h3>위치</h3>
      <ul>
        <li>원본에 좌표가 없어 주소 문자열에서 시도·시군구만 파싱했습니다. 파싱 실패 1,981건(0.9%)은 대부분 주소가 비어 있는 행입니다.</li>
        <li>지오코딩은 <b>CBAM·열공정 대상부터</b> 채워 넣었습니다. 그래서 그 밖의 조건(예: 기계·장비)을 고르면
            좌표가 있는 행이 3%밖에 안 됩니다. 이럴 때는 점 대신 <b>시도별로 모은 원</b>으로 자동 전환됩니다 —
            지도가 빈 것이 아니라 개별 위치를 아직 모르는 것입니다.</li>
        <li>좌표를 더 채우려면 <code>2_geocode.py</code> 를 돌리면 됩니다. 전국 21만 곳을 다 하려면
            일일 호출 한도 때문에 며칠 걸립니다.</li>
      </ul>
      <h3>이 데이터로 알 수 없는 것</h3>
      <ul>
        <li><b>EU 수출 여부</b> — 기업별 수출 실적은 공개되지 않습니다. 후보군에서 실제 CBAM 대상으로 좁히려면 무역협회·KOTRA 경로나 원청 확인이 필요합니다.</li>
        <li><b>기업 규모·재무</b> — 종업원수, 매출은 공공데이터에 없습니다. 민간 기업정보(NICE디앤비, 한국기업데이터 등)를 붙여야 합니다.</li>
        <li><b>에너지 사용량·배출량</b> — 배출권거래제 할당대상업체가 아닌 중소기업은 공개 데이터가 없습니다.</li>
      </ul>
    </div>
  </details>

  <footer>
    출처: 한국산업단지공단 「전국등록공장현황 등록공장현황자료」(2024-12-31), 공공데이터포털. 이용허락범위 제한 없음.
    품목군 분류와 행정구역 파싱은 원본에 없는 파생 항목으로, 이 페이지에서 생성한 <b>추정값</b>입니다.
  </footer>
</div>

<div class="dscrim" id="dscrim"></div>
<aside class="dtl" id="dtl" role="dialog" aria-modal="true" aria-label="업체 상세"></aside>
<div class="dscrim" id="fscrim"></div>
<button class="fabf" id="fabf" type="button">조건<span class="fabn" id="fabn">전체</span></button>

<script>//__LEAFLET_JS__</script>
<script id="payload" type="application/json">__DATA__</script>
<script id="bnd" type="application/json">__BOUNDARY__</script>
<script>
(function(){
  "use strict";
  function boot(D){

  // 전송은 배열로 받고(21만 줄에 키 이름을 반복하지 않으려고) 여기서 객체로 편다.
  // [회사명,생산품,주소뒤,주소앞,단지,단지유형,시도,시군구,업종,열공정,CBAM,위도,경도,규제,법인,배출량]
  (function unpack(){
    var K = D.dict, F = D.firms, out = new Array(F.length);
    for(var i = 0; i < F.length; i++){
      var r = F[i], pre = K.ap[r[3]];
      var o = { n:r[0], p:r[1], a:(pre ? pre + ' ' : '') + r[2],
                c:K.cx[r[4]], ct:K.ct[r[5]], s:K.si[r[6]], g:K.gg[r[7]],
                se:K.se[r[8]], h:K.he[r[9]], cb:K.cb[r[10]] };
      if(r[11]){ o.y = r[11]; o.x = r[12]; }
      if(r[13]){ o.r = r[13]; o.ln = K.ln[r[14]]; if(r[15]) o.e = r[15]; }
      if(r[16]){ o.fs = r[16]; o.fn = K.fn[r[17]]; o.lst = r[18]; }
      o.pm = K.pm[r[19]];
      if(r[20]){ o.emp = r[20]; o.amt = r[21]; o.hin = r[22]; o.hout = r[23]; }
      if(r[24] || r[25]){ o.tel = r[24]; o.murl = r[25]; }
      o.tg = r[26];                     // 연락처 신뢰도 0없음 1낮음 2보통 3확실
      if(r[27]){ o.ex = K.ex[r[28]] || '명단'; }
      o.sc = r[29];                     // 영업 우선순위
      out[i] = o;
    }
    D.firms = out;
  })();
  var CBCOLOR = {'철강':'var(--s1)','알루미늄':'var(--s2)','시멘트':'var(--s3)','비료':'var(--s4)','수소':'var(--s5)'};
  // 업종은 16종이라 색으로 다 구분할 수 없다. 상위 5종만 색을 주고 나머지는 회색으로 묶는다.
  // (색 개수를 늘리면 색맹 판별 한계를 넘는다 — 나머지는 표와 필터로 구분한다)
  var SECLEG = D.meta.sectors.slice(0,5);
  function SECCOLOR(k){
    var i = SECLEG.indexOf(k);
    return i<0 ? 'var(--ink-soft)' : ['var(--s1)','var(--s2)','var(--s3)','var(--s4)','var(--s5)'][i];
  }
  var EM = (D.meta.emit && D.meta.emit.have) ? D.meta.emit : null;
  var FI = (D.meta.fin  && D.meta.fin.have)  ? D.meta.fin  : null;
  var PN = (D.meta.pension && D.meta.pension.have) ? D.meta.pension : null;
  var CT = (D.meta.contact && D.meta.contact.have) ? D.meta.contact : null;
  var EX = (D.meta.export  && D.meta.export.have)  ? D.meta.export  : null;
  var TG = ['없음', '낮음', '보통', '확실', '두 곳 확인', '주소 불일치'];
  // 시도 경계 — OSM 타일에는 경계가 '그려져' 있을 뿐 클릭할 정보가 없다.
  // 구역을 눌러 그 지역만 보려면 좌표 폴리곤이 따로 있어야 한다.
  var B  = JSON.parse(document.getElementById('bnd').textContent);
  var BS = B.sido || {};
  var HASB = Object.keys(BS).length > 0;
  var st = { sec:null, pm:null, cxt:null, heat:null, cb:null, reg:null,
             size:null, tel:false, exp:false, sido:null, cx:null, q:'',
             sort:'sc' };
  var SIZE = [['1~19인', 1, 19], ['20~99인', 20, 99], ['100~299인', 100, 299],
              ['300인 이상', 300, 1e9]];

  // 21만 건이라 한 번 그릴 때 전수 훑기를 여러 번 하면 눈에 띄게 느려진다.
  // 그릴 때마다 딱 두 번(필터 결과 / 시도 집계)만 훑고 결과를 재활용한다.
  var _F = null, _SA = null;
  // 검색어가 처음 들어올 때만 소문자 색인을 만든다 (만드는 데 0.3초쯤 걸린다)
  var HAY = null;
  function buildHay(){
    HAY = new Array(D.firms.length);
    for(var i = 0; i < D.firms.length; i++){
      var f = D.firms[i];
      HAY[i] = (f.n + ' ' + f.p + ' ' + f.c + ' ' + f.a).toLowerCase();
    }
  }
  // 칩에 붙는 총건수는 필터와 무관하므로 시작할 때 한 번만 센다
  var TOT = { h:{}, cb:{}, reg:{} };
  var PMTOT = {}, TOPPM = [], SZTOT = {}, TELTOT = 0, EXPTOT = 0;
  var view = { k:1, tx:0, ty:0 };     // 지도 확대·이동

  var $ = function(id){ return document.getElementById(id); };
  function el(t,c,h){ var e=document.createElement(t); if(c)e.className=c; if(h!==undefined)e.innerHTML=h; return e; }
  function n0(v){ return Math.round(v).toLocaleString('ko-KR'); }
  // 원 단위 숫자를 조·억으로 줄여 쓴다. 6,900,000,000,000 → 6.9조
  function won(v){
    if(!v) return '';
    var a = Math.abs(v), sign = v < 0 ? '-' : '';
    if(a >= 1e12) return sign + (a/1e12).toFixed(a/1e12 >= 10 ? 0 : 1) + '조';
    if(a >= 1e8)  return sign + n0(a/1e8) + '억';
    if(a >= 1e4)  return sign + n0(a/1e4) + '만';
    return sign + n0(a);
  }

  // Leaflet 은 canvas 로 그리는데 canvas 의 fillStyle 은 var(--x) 를 못 읽는다.
  // (지도의 점이 전부 검게 찍히던 원인) 실제 색값으로 풀어서 넘긴다.
  var _cc = {};
  function col(v){
    if(typeof v !== 'string' || v.indexOf('var(') !== 0) return v;
    var k = v.slice(4, -1).trim();
    if(!(k in _cc)) _cc[k] = getComputedStyle(document.documentElement)
                               .getPropertyValue(k).trim() || '#888';
    return _cc[k];
  }
  function esc(s){ return String(s==null?'':s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }
  function attr(s){ return esc(s).replace(/"/g,'&quot;').replace(/'/g,'&#39;'); }

  // ---- 지도 서비스 연결 ----
  // 공장은 상호로 등록돼 있지 않은 곳이 많아 회사명만으로는 못 찾는 일이 흔하다.
  // 그래서 이름 검색과 주소 검색 두 갈래를 다 만들어 둔다.
  function mapLinks(f){
    // 상호만 넘기면 전국의 동명 업체가 걸린다. 주소를 함께 넘겨야 그 공장이 나온다.
    var addr = f.a || ((f.s || '') + ' ' + (f.g || ''));
    var both = encodeURIComponent((f.n + ' ' + addr).trim());
    var byName = encodeURIComponent(f.n + ' ' + (f.g || f.s || ''));
    var byAddr = encodeURIComponent(addr);
    return [
      ['네이버 지도',  'https://map.naver.com/p/search/' + byName],
      ['카카오맵',    'https://map.kakao.com/?q=' + byName],
      ['구글 지도',   'https://www.google.com/maps/search/?api=1&query=' + both],
      ['주소로 찾기', 'https://map.naver.com/p/search/' + byAddr]
    ];
  }
  function linkRow(f){
    return '<span class="mlink">' + mapLinks(f).map(function(o){
      return '<a href="' + attr(o[1]) + '" target="_blank" rel="noopener">' + o[0] + '</a>';
    }).join('') + '</span>';
  }

  // ---- 이 페이지 지도로 이동 ----
  // 바깥 지도 서비스로 나가기 전에, 우선 이 화면 지도에서 어디쯤인지 보여준다.
  // 좌표가 있는 곳만 된다 (지오코딩이 아직 전체가 아니다).
  var FOCUS = null, DF = null;
  function focusOnMap(f){
    if(!f.y) return false;
    closeMenu(); closeDrawer(); closeFilters();
    var w = $('mapwrap');
    if(w) w.scrollIntoView({block:'center', behavior:'smooth'});
    window.__focused = f.n;              // 화면 검사에서 확인하는 표식
    if(!LMAP){                           // 타일이 막혀 SVG 로 그린 경우
      var h = $('maphint');
      if(h) h.innerHTML = '<b>' + esc(f.n) + '</b> — ' + esc(f.a)
                        + ' · 배경지도를 못 불러와 위치를 확대할 수 없습니다.';
      return true;
    }
    LMAP.setView([f.y, f.x], 16, {animate:true});
    if(FOCUS){ LMAP.removeLayer(FOCUS); FOCUS = null; }
    FOCUS = L.circleMarker([f.y, f.x], {radius:14, weight:3, color:'#C1440E', fill:false})
             .addTo(LMAP)
             .bindPopup('<b>' + esc(f.n) + '</b><br><span class="sub2">' + esc(f.a) + '</span>');
    setTimeout(function(){ if(FOCUS) FOCUS.openPopup(); }, 400);
    return true;
  }

  // 표에서는 이름 자체가 버튼이고, 누르면 갈래가 뜬다
  var MENU = null, MENUAT = 0;
  function closeMenu(){ if(MENU){ MENU.remove(); MENU = null; } }
  document.addEventListener('click', function(ev){
    if(MENU && !ev.target.closest('.namemenu') && !ev.target.closest('.nmbtn')) closeMenu();
  });
  // 표를 스크롤하면 버튼과 어긋나므로 닫는다. 다만 스크롤 이벤트가 클릭보다
  // 늦게 오는 경우가 있어, 연 직후 0.3초는 무시한다.
  window.addEventListener('scroll', function(){
    if(Date.now() - MENUAT > 300) closeMenu();
  }, true);
  function openMenu(btn, f){
    closeMenu();
    var m = el('div', 'namemenu');
    m.innerHTML = '<div class="nmhead">' + esc(f.n) +
      '<span>' + esc(f.s + ' ' + f.g + (f.c ? ' · ' + f.c : '')) +
      (f.fs ? ' · 매출 ' + won(f.fs) : '') + '</span></div>'
      + (f.y ? '<button type="button" class="nmhere">이 지도에서 보기</button>'
             : '<span class="nmno">이 화면 지도에는 아직 좌표가 없습니다</span>')
      + mapLinks(f).map(function(o){
          return '<a href="' + attr(o[1]) + '" target="_blank" rel="noopener">' + o[0] + '</a>';
        }).join('');
    document.body.appendChild(m);
    var here = m.querySelector('.nmhere');
    if(here) here.onclick = function(ev){ ev.stopPropagation(); focusOnMap(f); };
    var r = btn.getBoundingClientRect();
    m.style.left = Math.min(r.left + window.scrollX,
                            window.scrollX + window.innerWidth - 215) + 'px';
    m.style.top  = (r.bottom + window.scrollY + 4) + 'px';
    MENU = m; MENUAT = Date.now();
  }

  // r: 1=배출권거래제 할당대상, 2=명세서 제출 법인(목표관리제 등), 없으면 규제 밖
  var REG = ['할당대상', '명세서 제출', '규제 밖'];
  function regKey(f){ return f.r===1 ? REG[0] : (f.r===2 ? REG[1] : REG[2]); }

  // 시도·단지를 뺀 나머지 조건. 시도 집계와 시도 막대가 이걸 쓴다 —
  // 이미 고른 시도 때문에 다른 시도가 0으로 보이면 고를 수가 없기 때문이다.
  function passBase(f, i){
    if(st.sec  && f.se!==st.sec) return false;
    if(st.pm   && f.pm!==st.pm) return false;
    if(st.tel  && !(f.tel)) return false;
    if(st.exp  && !f.ex) return false;
    if(st.size){
      var b = null;
      for(var z=0; z<SIZE.length; z++) if(SIZE[z][0]===st.size) b = SIZE[z];
      if(!b || !f.emp || f.emp < b[1] || f.emp > b[2]) return false;
    }
    if(st.cxt  && f.ct!==st.cxt) return false;
    if(st.heat && f.h!==st.heat) return false;
    if(st.cb   && f.cb!==st.cb) return false;
    if(st.reg  && regKey(f)!==st.reg) return false;
    if(st.q){ if(!HAY) buildHay(); if(HAY[i].indexOf(st.q)<0) return false; }
    return true;
  }
  function firmPass(f, i){
    if(!passBase(f, i)) return false;
    if(st.sido && f.s!==st.sido) return false;
    if(st.cx   && f.c!==st.cx) return false;
    return true;
  }
  function filtered(){
    if(_F) return _F;
    _F = D.firms.filter(firmPass);
    var k = st.sort;
    if(k === 'n'){
      _F.sort(function(a,b){ return a.n < b.n ? -1 : (a.n > b.n ? 1 : 0); });
    } else {
      _F.sort(function(a,b){ return (b[k]||0) - (a[k]||0); });
    }
    return _F;
  }
  function sidoAgg(){
    if(_SA) return _SA;
    var m = {}, i;
    for(i = 0; i < D.sido.length; i++) m[D.sido[i].name] = { tot:0, seg:{} };
    var isLeg = {}; SECLEG.forEach(function(k){ isLeg[k] = 1; });
    for(i = 0; i < D.firms.length; i++){
      var f = D.firms[i];
      if(!passBase(f, i)) continue;
      var e = m[f.s]; if(!e) continue;
      e.tot++;
      var k = isLeg[f.se] ? f.se : '그 외';
      e.seg[k] = (e.seg[k] || 0) + 1;
    }
    _SA = m; return m;
  }
  function sidoCount(s){ var a = sidoAgg()[s.name]; return a ? a.tot : 0; }

  // ---- 상단 지표 ----
  function tiles(){
    var rows = filtered();
    var inCx=0, nCb=0, nHt=0, nTel=0, nHot=0, cxSet={};
    for(var i=0;i<rows.length;i++){
      var f=rows[i];
      if(f.c){ inCx++; cxSet[f.c]=1; }
      if(f.cb) nCb++;
      if(f.h!=='해당없음') nHt++;
      if(f.tel) nTel++;
      if(f.sc>=60) nHot++;
    }
    $('tiles').innerHTML =
      '<div class="tile hi"><span class="k">조건에 걸린 곳</span><span class="v">'+n0(rows.length)+'</span><span class="u">'+n0(Object.keys(cxSet).length)+'개 단지 · 대상 '+n0(D.meta.shown)+'곳 중</span></div>'+
      '<div class="tile cb"><span class="k">CBAM 대상 후보</span><span class="v">'+n0(nCb)+'</span><span class="u">철강·알루미늄·시멘트·비료·수소</span></div>'+
      '<div class="tile ht"><span class="k">고온 열공정</span><span class="v">'+n0(nHt)+'</span><span class="u">용해·소성 또는 건조·증기</span></div>'+
      '<div class="tile"><span class="k">전화 가능</span><span class="v">'+n0(nTel)+'</span><span class="u">'+(CT?'수집한 연락처':'06_contact.py 로 수집')+'</span></div>'+
      '<div class="tile hi"><span class="k">우선 접촉 (60점↑)</span><span class="v">'+n0(nHot)+'</span><span class="u">CBAM·규제 밖·규모가 겹치는 곳</span></div>';
  }

  function controls(){
    function fillSel(id, items, totals, cur, setter, label){
      var sel=$(id); sel.innerHTML='';
      var o0=document.createElement('option'); o0.value=''; o0.textContent='전체 '+label;
      sel.appendChild(o0);
      items.forEach(function(k){
        var o=document.createElement('option'); o.value=k;
        o.textContent=k+' ('+n0(totals[k]||0)+')';
        sel.appendChild(o);
      });
      sel.value = cur || '';
      sel.onchange=function(){ setter(sel.value||null); st.cx=null; draw(); };
    }
    fillSel('secf', D.meta.sectors, D.meta.secTotals, st.sec,
            function(v){ st.sec=v; st.pm=null; }, '업종');   // 업종을 바꾸면 품목은 푼다

    // 품목은 업종에 딸린 목록이다. 업종을 안 고르면 전체 상위 품목을 보여준다.
    var pmList = st.sec ? (D.meta.pmBySector[st.sec] || []) : TOPPM;
    fillSel('pmf', pmList, PMTOT, st.pm, function(v){st.pm=v;}, '품목');
    $('pmf').title = st.sec ? st.sec + ' 의 주요 품목' : '업종을 고르면 그 업종 품목만 나옵니다';

    fillSel('cxtf', D.meta.cxtypes, D.meta.cxtTotals, st.cxt, function(v){st.cxt=v;}, '단지유형');

    function chips(id, items, cur, setter, colorMap){
      var box=$(id); box.innerHTML='';
      var all=el('button','chipbtn','전체'); all.type='button';
      all.setAttribute('aria-pressed', cur===null);
      all.onclick=function(){ setter(null); st.cx=null; draw(); };
      box.appendChild(all);
      items.forEach(function(k){
        var tot=(TOT[colorMap.tot]||{})[k]||0;
        var b=el('button','chipbtn',(colorMap.c?'<i style="background:'+colorMap.c(k)+'"></i>':'')+k+' <span class="ct">'+n0(tot)+'</span>');
        b.type='button'; b.setAttribute('aria-pressed', cur===k);
        b.onclick=function(){ setter(cur===k?null:k); st.cx=null; draw(); };
        box.appendChild(b);
      });
    }
    chips('heatf', D.meta.heats, st.heat, function(v){st.heat=v;}, {key:'h', tot:'h'});
    chips('cbf',   D.meta.cbams, st.cb,   function(v){st.cb=v;},   {key:'cb', tot:'cb', c:function(k){return CBCOLOR[k];}});

    // 규모 (국민연금 종업원수)
    if(PN){
      $('szl').hidden = false; $('szf').hidden = false;
      var sb = $('szf'); sb.innerHTML = '';
      var sa = el('button','chipbtn','전체'); sa.type='button';
      sa.setAttribute('aria-pressed', st.size===null);
      sa.onclick=function(){ st.size=null; st.cx=null; draw(); };
      sb.appendChild(sa);
      SIZE.forEach(function(b){
        var tot = SZTOT[b[0]] || 0;
        var x = el('button','chipbtn', b[0]+' <span class="ct">'+n0(tot)+'</span>');
        x.type='button'; x.setAttribute('aria-pressed', st.size===b[0]);
        x.onclick=function(){ st.size=(st.size===b[0]?null:b[0]); st.cx=null; draw(); };
        sb.appendChild(x);
      });
    }

    // 영업 전용 토글
    var bf = $('bizf'); bf.innerHTML = '';
    [['연락처 있는 곳', 'tel', CT, TELTOT],
     ['수출 명단', 'exp', EX, EXPTOT]].forEach(function(o){
      if(!o[2]) return;
      var b = el('button','chipbtn', o[0]+' <span class="ct">'+n0(o[3])+'</span>');
      b.type='button'; b.setAttribute('aria-pressed', !!st[o[1]]);
      b.onclick=function(){ st[o[1]] = !st[o[1]]; st.cx=null; draw(); };
      bf.appendChild(b);
    });
    var sv = el('span','sortbox','정렬 ');
    var sel = document.createElement('select');
    [['sc','영업 우선순위'],['emp','종업원 많은 순'],['e','배출량 많은 순'],
     ['fs','매출 큰 순'],['n','회사명']].forEach(function(o){
      var op=document.createElement('option'); op.value=o[0]; op.textContent=o[1];
      sel.appendChild(op);
    });
    sel.value = st.sort;
    sel.onchange=function(){ st.sort=sel.value; draw(); };
    sv.appendChild(sel); bf.appendChild(sv);
    var dl = el('button','chipbtn dl','현재 목록 내려받기'); dl.type='button';
    dl.onclick = downloadCsv; bf.appendChild(dl);

    if(EM){
      $('regl').hidden = false; $('regf').hidden = false;
      var box=$('regf'); box.innerHTML='';
      var all=el('button','chipbtn','전체'); all.type='button';
      all.setAttribute('aria-pressed', st.reg===null);
      all.onclick=function(){ st.reg=null; st.cx=null; draw(); };
      box.appendChild(all);
      REG.forEach(function(k){
        var tot=TOT.reg[k]||0;
        var b=el('button','chipbtn',k+' <span class="ct">'+n0(tot)+'</span>');
        b.type='button'; b.setAttribute('aria-pressed', st.reg===k);
        b.onclick=function(){ st.reg=(st.reg===k?null:k); st.cx=null; draw(); };
        box.appendChild(b);
      });
    }

    $('legend').innerHTML = SECLEG.map(function(k){
      return '<span><i style="background:'+SECCOLOR(k)+'"></i>'+k+'</span>';
    }).join('') + '<span style="opacity:.7"><i style="background:var(--ink-soft)"></i>그 외 업종</span>';
  }

  // ---- 지도 ----
  function proj(W,H,PAD){
    var lat0=33.0,lat1=38.85,lon0=125.4,lon1=130.0;
    var mlat=(lat0+lat1)/2, kx=Math.cos(mlat*Math.PI/180);
    var sc=Math.min((W-PAD*2)/((lon1-lon0)*kx),(H-PAD*2)/(lat1-lat0));
    var ox=PAD+((W-PAD*2)-(lon1-lon0)*kx*sc)/2, oy=PAD+((H-PAD*2)-(lat1-lat0)*sc)/2;
    return {
      xy:function(lon,lat){ return [ox+(lon-lon0)*kx*sc, oy+(lat1-lat)*sc]; },
      lat0:lat0,lat1:lat1,lon0:lon0,lon1:lon1
    };
  }
  // SVG 폴백에서도 같은 경계를 쓴다. 격자선보다 훨씬 읽기 쉽다.
  function sidoShapes(P){
    if(!HASB) return '';
    var vals={}, mx=0;
    D.sido.forEach(function(v){ var n=sidoCount(v); vals[v.name]=n; if(n>mx) mx=n; });
    var out='';
    Object.keys(BS).forEach(function(name){
      var d='';
      BS[name].forEach(function(r){
        for(var i=0;i<r.length;i++){
          var q=P.xy(r[i][0], r[i][1]);
          d += (i?'L':'M') + q[0].toFixed(1) + ' ' + q[1].toFixed(1);
        }
        d += 'Z';
      });
      var n=vals[name]||0, on=(st.sido===name);
      var fo = st.sido && !on ? 0.03 : (n<=0 ? 0.04 : 0.10 + Math.sqrt(n/(mx||1))*0.42);
      out += '<path d="'+d+'" fill="var(--seq)" fill-opacity="'+fo.toFixed(3)+
             '" stroke="var(--seq)" stroke-opacity="'+(on?1:0.5)+
             '" stroke-width="'+(on?1.6:0.7)+'" data-s="'+name+
             '" data-n="'+n+'" style="cursor:pointer"/>';
    });
    return out;
  }

  // 경계 도형에 hover·click 을 붙인다 (폴백 SVG 전용)
  function bindShapes(w, tip){
    w.querySelectorAll('path[data-s]').forEach(function(el2){
      el2.addEventListener('mouseenter', function(){
        el2.setAttribute('stroke-width','2');
        if(tip){
          var nm=el2.getAttribute('data-s');
          var v=D.sido.filter(function(x){return x.name===nm;})[0];
          tip.innerHTML='<b>'+nm+'</b> · '+n0(el2.getAttribute('data-n'))+'곳'+
            (v?'<br><span style="opacity:.7">등록공장 전체 '+n0(v.total)+'건</span>':'');
          tip.style.opacity='1';
        }
      });
      el2.addEventListener('mouseleave', function(){
        el2.setAttribute('stroke-width', st.sido===el2.getAttribute('data-s')?'1.6':'0.7');
        if(tip) tip.style.opacity='0';
      });
      el2.addEventListener('click', function(){
        var nm=el2.getAttribute('data-s');
        st.sido=(st.sido===nm?null:nm); st.cx=null; draw();
      });
    });
  }

  function grid(P,W,H){
    if(HASB) return '';   // 경계가 있으면 격자선은 군더더기
    var s='';
    for(var g=126;g<=130;g++){ var a=P.xy(g,P.lat0),b=P.xy(g,P.lat1);
      s+='<line x1="'+a[0].toFixed(1)+'" y1="'+a[1].toFixed(1)+'" x2="'+b[0].toFixed(1)+'" y2="'+b[1].toFixed(1)+'" stroke="currentColor" stroke-opacity=".08"/>'; }
    for(var t=33;t<=38;t++){ var c=P.xy(P.lon0,t),d=P.xy(P.lon1,t);
      s+='<line x1="'+c[0].toFixed(1)+'" y1="'+c[1].toFixed(1)+'" x2="'+d[0].toFixed(1)+'" y2="'+d[1].toFixed(1)+'" stroke="currentColor" stroke-opacity=".08"/>'; }
    return s;
  }

  // ---- 지도 ----
  // 1순위: 실제 배경지도(OpenStreetMap 타일) 위에 표시.
  // 사내망이나 아티팩트 샌드박스처럼 타일을 못 받는 곳에서는 좌표 격자 위의
  // 추상 분포도로 자동 전환한다. (흰 배경으로 보이던 것이 이 폴백 상태였다)
  var LMAP = null, LLAYER = null, BLAYER = null, BPOLY = {}, mapMode = 'try';

  // 시도별 색 농도 — 값이 클수록 진하게. 0건은 거의 투명.
  function shade(n, mx){ return n <= 0 ? 0.04 : 0.10 + Math.sqrt(n / (mx || 1)) * 0.42; }

  function buildBoundary(){
    if(!HASB || !BLAYER) return;
    BPOLY = {};
    Object.keys(BS).forEach(function(name){
      var rings = BS[name].map(function(r){
        return r.map(function(p){ return [p[1], p[0]]; });   // [lon,lat] → [lat,lng]
      });
      var poly = L.polygon(rings, {
        color: col('var(--seq)'), weight:1, opacity:.55,
        fillColor: col('var(--seq)'), fillOpacity:.12, interactive:true
      });
      poly.on('click', function(ev){
        if(ev.originalEvent) L.DomEvent.stop(ev);
        st.sido = (st.sido === name ? null : name); st.cx = null; draw();
      });
      poly.on('mouseover', function(){ poly.setStyle({weight:2.5, opacity:1}); });
      poly.on('mouseout',  function(){ poly.setStyle({weight: st.sido===name?2.5:1,
                                                      opacity: st.sido===name?1:.55}); });
      poly.bindTooltip(name, {sticky:true});
      poly.addTo(BLAYER);
      BPOLY[name] = poly;
    });
  }

  function styleBoundary(){
    if(!HASB || !BLAYER) return;
    var vals = {}, mx = 0;
    D.sido.forEach(function(v){ var n = sidoCount(v); vals[v.name] = n; if(n > mx) mx = n; });
    Object.keys(BPOLY).forEach(function(name){
      var n = vals[name] || 0, on = (st.sido === name);
      BPOLY[name].setStyle({
        weight: on ? 2.5 : 1, opacity: on ? 1 : .55,
        fillOpacity: st.sido && !on ? 0.03 : shade(n, mx)
      });
      BPOLY[name].setTooltipContent(
        '<b>' + name + '</b> · ' + n0(n) + '곳'
      );
    });
  }

  function map(){
    if(mapMode === 'svg'){ mapSvg(); return; }
    if(!LMAP) initLeaflet();
    if(LMAP) drawLeaflet();
  }
  function mapSvg(){
    var lm = $('lmap'); if(lm) lm.style.display='none';
    var _r = filtered(), _p = 0;
    for(var _i = 0; _i < _r.length; _i++) if(_r[_i].y) _p++;
    if(_p > 0 && _p / _r.length >= 0.5) mapPoints(); else mapBubbles(_p > 0);
    attachZoom();
    mapNotice(_r.length, _p);
    $('maphint').innerHTML = '배경지도를 불러오지 못해 좌표 격자 위 분포도로 표시하고 있습니다. '
      + '휠로 확대, 끌어서 이동할 수 있습니다.'
      ;
  }

  function initLeaflet(){
    if(typeof L === 'undefined'){ mapMode='svg'; return; }
    try{
      LMAP = L.map('lmap', { center:[36.4,127.9], zoom:7, zoomControl:true,
                             preferCanvas:true, attributionControl:true });
    }catch(e){ mapMode='svg'; LMAP=null; return; }

    var loaded = 0, errored = 0;
    var tiles = L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 18, minZoom: 6,
      attribution: '&copy; OpenStreetMap 기여자'
    });
    tiles.on('tileload', function(){ loaded++; });
    tiles.on('tileerror', function(){ errored++; });
    tiles.addTo(LMAP);

    // 타일이 하나도 안 들어오면 배경 없는 지도가 되므로 폴백으로 넘어간다
    setTimeout(function(){
      if(loaded === 0){
        mapMode = 'svg';
        try{ LMAP.remove(); }catch(e){}
        LMAP = null; LLAYER = null;
        var lm=$('lmap'); if(lm) lm.style.display='none';
        draw();
      }
    }, 4000);

    // 경계를 먼저 올려 공장 점 아래에 깔리게 한다
    BLAYER = L.layerGroup().addTo(LMAP);
    buildBoundary();
    LLAYER = L.layerGroup().addTo(LMAP);
    window.__lz = function(){ return LMAP ? LMAP.getZoom() : null; };   // 자동 테스트용
    window.__bp = function(n){                                          // 자동 테스트용
      if(n === undefined) return Object.keys(BPOLY);
      if(BPOLY[n]) BPOLY[n].fire('click');
      return !!BPOLY[n];
    };
    setTimeout(function(){ if(LMAP) LMAP.invalidateSize(); }, 200);
  }

  function drawLeaflet(){
    if(!LLAYER) return;
    styleBoundary();
    LLAYER.clearLayers();
    var rows = filtered();

    // 지도에 그리는 것은 두 가지뿐이다.
    //   · 시도 구역의 색 진하기 = 조건에 걸린 공장 수 (전부 반영된다)
    //   · 점 = 좌표를 확보한 공장 (지오코딩을 CBAM·열공정부터 해서 아직 일부다)
    // 예전에 여기에 '시도 대표 좌표 버블'을 하나 더 그렸는데, 구역 색과 같은 값을
    // 두 번 그리는 셈이라 그 큰 원이 무엇인지 알 수 없다는 지적을 받고 뺐다.
    var pts = rows.filter(function(f){ return f.y; });
    var cover = rows.length ? pts.length / rows.length : 0;

    if(pts.length){
      pts.forEach(function(f){
        L.circleMarker([f.y, f.x], {
          radius: 3, weight: 0, fillColor: col(SECCOLOR(f.se)), fillOpacity: .75
        }).bindPopup(
          '<b>'+esc(f.n)+'</b><br>'+esc(f.p)+
          '<br><span class="sub2">'+esc(f.se)+(f.h!=='해당없음'?' · '+esc(f.h):'')+
          (f.cb?' · CBAM '+esc(f.cb):'')+'</span>'+
          '<br><span class="sub2">'+(f.c?esc(f.c)+' · ':'')+esc(f.a)+'</span>'+
          (f.fs?'<br><span class="sub2">매출 '+won(f.fs)+' · '+esc(f.fn)+' '+FI.year+'</span>':'')+
          (f.e?'<br><span class="sub2">배출 '+n0(f.e)+' tCO₂eq · '+esc(f.ln)+'</span>':'')+
          linkRow(f) +
          '<br><button type="button" class="popdtl" data-n="'+attr(f.n)+'">상세 보기</button>'
        ).on('popupopen', function(ev){
          var b = ev.popup.getElement().querySelector('.popdtl');
          if(b) b.onclick = function(){ detail(f); };
        }).addTo(LLAYER);
      });
    }
    mapNotice(rows.length, pts.length);
    $('maphint').innerHTML =
      (pts.length ? '점을 누르면 상세가 열립니다. ' : '')
      + (HASB ? '시도 구역을 누르면 그 지역만 남습니다. 구역에 마우스를 올리면 건수가 뜹니다.' : '');
  }

  // 좌표가 모자란 조건이면 지도 위에 대놓고 알린다. 아래 작은 글씨로는 안 보인다.
  function mapNotice(nRows, nPts){
    var w = $('mapwarn'); if(!w) return;
    var cov = nRows ? nPts / nRows : 0;
    if(nRows === 0){
      w.hidden = false;
      w.innerHTML = '<b>조건에 맞는 공장이 없습니다.</b> 조건을 줄여 보십시오.';
      return;
    }
    if(cov >= 0.5){ w.hidden = true; return; }
    w.hidden = false;
    w.innerHTML = '<b>이 조건 ' + n0(nRows) + '곳 중 지도에 점으로 찍히는 것은 '
      + n0(nPts) + '곳뿐입니다.</b> 나머지는 주소만 있고 좌표가 없어 '
      + '<b>시도 구역 색으로만</b> 보입니다 — 목록과 건수는 ' + n0(nRows) + '곳 전부 반영돼 있습니다. '
      + '좌표는 CBAM·열공정 대상부터 채워 넣었고, <code>2_geocode.py</code> 로 더 늘릴 수 있습니다.';
  }

  // SVG 폴백에서 쓰는 확대·이동. 휠로 확대, 끌어서 이동.
  function attachZoom(){
    var w=$('mapwrap'), svg=w.querySelector('svg'), g=svg && svg.querySelector('g.z');
    if(!g) return;
    function apply(){ g.setAttribute('transform','translate('+view.tx+','+view.ty+') scale('+view.k+')'); }
    apply();
    var ctl=el('div','zoomctl');
    [['+',1.4],['−',1/1.4],['⟲',0]].forEach(function(o){
      var b=el('button',null,o[0]); b.type='button';
      b.title = o[1]===0?'원래대로':(o[1]>1?'확대':'축소');
      b.onclick=function(){
        if(o[1]===0){ view={k:1,tx:0,ty:0}; }
        else{
          var vb=svg.viewBox.baseVal, cx=vb.width/2, cy=vb.height/2;
          view.tx = cx-(cx-view.tx)*o[1];
          view.ty = cy-(cy-view.ty)*o[1];
          view.k = Math.min(14, Math.max(1, view.k*o[1]));
        }
        apply();
      };
      ctl.appendChild(b);
    });
    w.appendChild(ctl);

    svg.addEventListener('wheel', function(ev){
      ev.preventDefault();
      var r=svg.getBoundingClientRect(), vb=svg.viewBox.baseVal;
      var mx=(ev.clientX-r.left)/r.width*vb.width, my=(ev.clientY-r.top)/r.height*vb.height;
      var f = ev.deltaY<0 ? 1.18 : 1/1.18;
      var nk = Math.min(14, Math.max(1, view.k*f)); f = nk/view.k;
      view.tx = mx-(mx-view.tx)*f; view.ty = my-(my-view.ty)*f; view.k = nk;
      apply();
    }, {passive:false});

    var drag=null;
    svg.addEventListener('mousedown', function(ev){
      drag={x:ev.clientX,y:ev.clientY,tx:view.tx,ty:view.ty}; svg.style.cursor='grabbing';
    });
    window.addEventListener('mouseup', function(){ drag=null; if(svg) svg.style.cursor=''; });
    window.addEventListener('mousemove', function(ev){
      if(!drag) return;
      var r=svg.getBoundingClientRect(), vb=svg.viewBox.baseVal;
      view.tx = drag.tx+(ev.clientX-drag.x)/r.width*vb.width;
      view.ty = drag.ty+(ev.clientY-drag.y)/r.height*vb.height;
      apply();
    });
  }

  // 좌표가 있을 때 — 공장 하나가 점 하나
  function mapPoints(){
    var W=560,H=620,PAD=30;
    var P=proj(W,H,PAD);
    var rows=filtered().filter(function(f){ return f.y; });
    var s='<svg viewBox="0 0 '+W+' '+H+'" role="img" aria-label="공장 위치 점 분포" style="cursor:grab"><g class="z">'
          +grid(P,W,H)+sidoShapes(P);
    D.sido.forEach(function(v){
      var p=P.xy(v.lon,v.lat);
      s+='<text x="'+p[0].toFixed(1)+'" y="'+p[1].toFixed(1)+'" text-anchor="middle" font-size="11" font-weight="600" fill="currentColor" fill-opacity=".22" pointer-events="none">'+v.name+'</text>';
    });
    var r = rows.length>4000?1.7:(rows.length>1200?2.2:3);
    var op = rows.length>4000?0.5:0.68;
    for(var i=0;i<rows.length;i++){
      var f=rows[i], p=P.xy(f.x,f.y);
      s+='<circle cx="'+p[0].toFixed(1)+'" cy="'+p[1].toFixed(1)+'" r="'+r+'" fill="'+SECCOLOR(f.se)+'" fill-opacity="'+op+'" data-i="'+i+'"/>';
    }
    s+='</g>';
    s+='<text x="'+PAD+'" y="'+(H-24)+'" font-size="10.5" fill="currentColor" fill-opacity=".5">점 하나 = 공장 한 곳 · '+n0(rows.length)+'개소</text>';
    s+='<text x="'+PAD+'" y="'+(H-10)+'" font-size="10.5" fill="currentColor" fill-opacity=".5">좌표 있는 '+n0(D.meta.geocoded)+'곳만 점으로 표시</text></svg>';

    var w=$('mapwrap');
    var keep=$('lmap'); w.innerHTML=''; if(keep) w.appendChild(keep);
    w.insertAdjacentHTML('beforeend', s); w.style.color='var(--ink-mid)';
    var tip=el('div','tip'); w.appendChild(tip);
    w.querySelector('svg').addEventListener('mouseover',function(ev){
      var c=ev.target.closest('circle[data-i]'); if(!c) return;
      var f=rows[+c.getAttribute('data-i')];
      tip.innerHTML='<b>'+esc(f.n)+'</b><br>'+esc(f.p)+'<br><span style="opacity:.75">'+
        esc(f.se)+(f.h!=='해당없음'?' · '+esc(f.h):'')+(f.cb?' · CBAM '+esc(f.cb):'')+'<br>'+
        (f.c?esc(f.c)+' · ':'')+esc(f.s)+' '+esc(f.g)+'</span>';
      tip.style.opacity='1'; c.setAttribute('r', (r*2.2).toFixed(1));
    });
    w.querySelector('svg').addEventListener('mouseout',function(ev){
      var c=ev.target.closest('circle[data-i]'); if(c) c.setAttribute('r', r);
      tip.style.opacity='0';
    });
    w.querySelector('svg').addEventListener('mousemove',function(ev){
      var b=w.getBoundingClientRect();
      tip.style.left=Math.min(ev.clientX-b.left+13,b.width-210)+'px';
      tip.style.top=(ev.clientY-b.top-58)+'px';
    });
    bindShapes(w, tip);
  }

  // 좌표가 없을 때 — 시도 대표 좌표에 모은 버블
  function mapBubbles(withPts){
    var W=560,H=620,PAD=44;
    var P=proj(W,H,PAD);
    // 수도권·충청권이 붙어 있어 라벨이 겹친다 — 시도별로 자리를 지정
    // 수도권·충청권이 붙어 있어 그냥 두면 글자가 겹친다. 시도마다 자리를 지정한다.
    var LBL={ '서울':[13,-13,'start'], '인천':[-16,2,'end'], '경기':[-38,-40,'end'],
              '강원':[16,-6,'start'], '세종':[-6,16,'end'], '대전':[14,12,'start'],
              '충북':[20,-4,'start'], '충남':[-22,-2,'end'], '대구':[17,-8,'start'],
              '울산':[16,4,'start'], '부산':[14,14,'start'], '광주':[-15,-4,'end'],
              '전남':[2,30,'middle'], '경남':[-10,-22,'middle'], '경북':[10,-4,'start'],
              '전북':[-19,0,'end'], '제주':[0,-13,'middle'] };
    var vals=D.sido.map(sidoCount);
    var mx=Math.max.apply(null,vals)||1;
    var fill = 'var(--seq)';
    var s='<svg viewBox="0 0 '+W+' '+H+'" role="img" aria-label="시도별 분포" style="cursor:grab"><g class="z">'
          +grid(P,W,H)+sidoShapes(P);
    var order=D.sido.map(function(v,i){return i;}).sort(function(a,b){return sidoCount(D.sido[b])-sidoCount(D.sido[a]);});
    order.forEach(function(i){
      var v=D.sido[i], n=sidoCount(v), p=P.xy(v.lon,v.lat);
      // 원은 그리지 않는다 — 구역 색이 이미 같은 값을 말하고 있어서,
      // 원까지 겹치면 "이 큰 원이 뭐냐"는 물음만 남는다. 숫자 라벨만 얹는다.
      var on = !st.sido || st.sido===v.name;
      var lb=LBL[v.name], lx,ly,an;
      if(lb){ lx=p[0]+lb[0]; ly=p[1]+lb[1]; an=lb[2]; } else { lx=p[0]; ly=p[1]-8; an='middle'; }
      s+='<text x="'+lx.toFixed(1)+'" y="'+ly.toFixed(1)+'" text-anchor="'+an+'" font-size="11.5" font-weight="600" fill="currentColor" fill-opacity="'+(on?0.95:0.35)+'" pointer-events="none">'+v.name+' '+n0(n)+'</text>';
    });
    if(withPts){            // 좌표가 있는 것은 원 위에 작은 점으로 겹쳐 찍는다
      var pr=filtered().filter(function(f){ return f.y; });
      for(var pi=0; pi<pr.length; pi++){
        var pf=pr[pi], pp=P.xy(pf.x, pf.y);
        s+='<circle cx="'+pp[0].toFixed(1)+'" cy="'+pp[1].toFixed(1)+'" r="1.8" fill="'
           +SECCOLOR(pf.se)+'" fill-opacity=".8" pointer-events="none"/>';
      }
    }
    s+='</g>';
    s+='<text x="'+PAD+'" y="'+(H-24)+'" font-size="10.5" fill="currentColor" fill-opacity=".5">구역 색 진하기 = 조건 일치 수 · 최대 '+n0(mx)+'건</text>';
    s+='<text x="'+PAD+'" y="'+(H-10)+'" font-size="10.5" fill="currentColor" fill-opacity=".5">주소 파싱 실패 '+n0(D.meta.unparsed)+'건은 지도에 없음</text></svg>';
    var w=$('mapwrap');
    var keep=$('lmap'); w.innerHTML=''; if(keep) w.appendChild(keep);
    w.insertAdjacentHTML('beforeend', s); w.style.color='var(--ink-mid)';
    var tip=el('div','tip'); w.appendChild(tip);
    w.addEventListener('mousemove',function(ev){
      var b=w.getBoundingClientRect();
      tip.style.left=Math.min(ev.clientX-b.left+13,b.width-200)+'px';
      tip.style.top=(ev.clientY-b.top-52)+'px';
    });
    bindShapes(w, tip);
  }

  // ---- 시도 막대 (업종 상위 5 + 그 외) ----
  function bars(){
    var keys = SECLEG.concat(['그 외']);
    var agg = sidoAgg();
    var rows=D.sido.map(function(v){
      var a=agg[v.name], seg={};
      keys.forEach(function(k){ seg[k]=(a && a.seg[k])||0; });
      return {name:v.name, seg:seg, tot:a?a.tot:0};
    }).sort(function(a,b){return b.tot-a.tot;});
    var mx=Math.max.apply(null,rows.map(function(r){return r.tot;}))||1;
    var box=$('bars'); box.innerHTML='';
    rows.forEach(function(r){
      var b=el('button','bar'); b.type='button';
      b.setAttribute('aria-pressed', st.sido===r.name);
      var segs=keys.filter(function(k){return r.seg[k]>0;}).map(function(k){
        return '<i style="width:'+(r.seg[k]/mx*100)+'%;background:'+(k==='그 외'?'var(--ink-soft)':SECCOLOR(k))+'"></i>';
      }).join('');
      b.innerHTML='<span class="bname">'+r.name+'</span><span class="btrack">'+segs+'</span>'+
                  '<span class="bval">'+n0(r.tot)+'</span>';
      b.onclick=function(){ st.sido=(st.sido===r.name?null:r.name); st.cx=null; draw(); };
      box.appendChild(b);
    });
  }

  // ---- 산업단지 표 ----
  function cxTable(){
    var agg={};
    filtered().forEach(function(f){
      if(!f.c) return;
      if(!agg[f.c]) agg[f.c]={n:0,by:{},sido:f.s,sgg:f.g,type:f.ct};
      agg[f.c].n++;
      agg[f.c].by[f.se]=(agg[f.c].by[f.se]||0)+1;
    });
    var meta={}; D.complexes.forEach(function(c){ meta[c.name]=c; });
    var rows=Object.keys(agg).map(function(k){
      return {name:k,n:agg[k].n,by:agg[k].by,sido:agg[k].sido,sgg:agg[k].sgg,
              type:agg[k].type, total:(meta[k]?meta[k].total:0)};
    }).sort(function(a,b){return b.n-a.n;});
    $('cxn').textContent=n0(rows.length);
    var tb=$('cxt').querySelector('tbody'); tb.innerHTML='';
    rows.slice(0,200).forEach(function(r){
      var tr=el('tr');
      var comp=Object.keys(r.by).sort(function(a,b){return r.by[b]-r.by[a];}).slice(0,4).map(function(k){
        return '<span class="kchip" style="background:'+SECCOLOR(k)+'">'+k+' '+r.by[k]+'</span>';
      }).join(' ');
      tr.innerHTML='<td><b>'+esc(r.name)+'</b><span class="sub">'+esc(r.type)+'</span></td>'+
        '<td>'+esc(r.sido)+'<span class="sub">'+esc(r.sgg)+'</span></td>'+
        '<td class="n"><b>'+n0(r.n)+'</b></td>'+
        '<td class="n">'+(r.total?n0(r.total):'—')+'</td>'+
        '<td class="n">'+(r.total?(r.n/r.total*100).toFixed(1)+'%':'—')+'</td>'+
        '<td>'+comp+'</td>';
      tr.style.cursor='pointer';
      tr.onclick=function(){ st.cx=(st.cx===r.name?null:r.name); draw(); window.scrollTo({top:document.getElementById('ft').offsetTop-120,behavior:'smooth'}); };
      if(st.cx===r.name) tr.style.background='var(--verdigris-wash)';
      tb.appendChild(tr);
    });
  }

  // ---- 기업 표 ----
  // 배출량은 법인 단위 공개값이다. 한 법인에 공장이 여럿이면 같은 값이 반복해서
  // 붙으므로, 사업장 배출량으로 읽지 않도록 법인명을 함께 보여준다.
  function emitCell(f){
    if(!f.r) return '<span class="sub" style="margin:0">—</span>';
    var t = '<span class="etag'+(f.r===1?' ets':'')+'">'+(f.r===1?'할당대상':'명세서')+'</span>';
    if(f.e) t = '<b>'+n0(f.e)+'</b><span class="sub">'+t+'</span>';
    if(f.ln) t += '<span class="sub">'+esc(f.ln)+' 전체</span>';
    return t;
  }

  // 재무는 DART 공시 법인만 있다. 대부분의 공장은 비어 있는 게 정상이다.
  function finCell(f){
    if(!f.fs) return '<span class="sub" style="margin:0">—</span>';
    return '<b>'+won(f.fs)+'</b>'
      + (f.lst?'<span class="sub"><span class="etag lst">상장</span></span>':'')
      + '<span class="sub">'+esc(f.fn)+' '+FI.year+'</span>';
  }

  function emitPanel(){
    $('ft').classList.toggle('noemit', !EM);
    $('ft').classList.toggle('nofin', !FI);
    $('ft').classList.toggle('nopen', !PN);
    $('ft').classList.toggle('notel', !CT);
    var fh=$('f-hint');
    if(fh) fh.textContent = FI
      ? 'DART 공시 법인만 매출이 붙습니다 — 공장 ' + n0(D.meta.rows) + '곳 중 '
        + n0(FI.rows) + '곳(' + (FI.rows/D.meta.rows*100).toFixed(1) + '%). '
        + '나머지는 공시 의무가 없어 어디에도 공개되지 않습니다.'
      : '';
    if(!EM) return;
    var inn=0, out=0;
    D.firms.forEach(function(f){ if(f.r) inn++; else out++; });
    $('e-in').textContent  = n0(inn);
    $('e-out').textContent = n0(out);
    $('e-note').textContent =
      '공장 ' + n0(inn+out) + '곳 중 규제 밖이 ' + (out/(inn+out)*100).toFixed(1) + '%'
      + (EM.year ? ' · 배출량 ' + EM.year + '년 명세서' : '');
    var h=$('e-hint');
    if(h) h.querySelector('span').innerHTML =
      (EM.src && (EM.src.ets || EM.src.emit)
        ? '이 배출량은 <b>' + esc(EM.src.ets || '—') + '</b> 와 <b>'
          + esc(EM.src.emit || '—') + '</b> 두 파일에서 가져왔습니다. '
        : '배출량 원본 파일 이름이 기록돼 있지 않습니다 (예전 방식으로 만든 캐시). '
          + '<code>python src\\03_emission.py</code> 를 다시 돌리면 기록됩니다. ')
      + '원본에 사업자등록번호가 없어 <b>법인 이름을 맞춰 붙였습니다</b>. '
      + '이름이 비슷한 다른 법인에 잘못 붙었을 수 있으니, '
      + '무엇이 무엇에 붙었는지는 <code>out\\배출량_매칭결과.csv</code> 를 열어 확인하십시오.';
  }

  // ---- 업체 상세 ----
  // 영업 담당자가 전화를 걸기 직전에 보는 화면이다. 한 곳에 다 모아둔다.
  function detail(f){
    function row(k, v, cls){
      return v ? '<div class="drow"><span>'+k+'</span><b'+(cls?' class="'+cls+'"':'')
                 +'>'+v+'</b></div>' : '';
    }
    // 구획에 붙은 값이 하나도 없으면 제목만 덩그러니 남아 "비었다"로 보인다.
    // 그럴 때는 왜 비었는지와 무엇을 돌려야 채워지는지를 대신 적는다.
    function sect(title, rows, why){
      var body = rows.join('');
      return '<div class="dsect">' + title + '</div>'
           + (body || '<div class="dempty">' + why + '</div>');
    }
    var why = [];
    (D.meta.score || []).forEach(function(o){
      var ok = (o.k==='cbam' && f.cb) || (o.k==='heat' && f.h!=='해당없음')
            || (o.k==='unreg' && !f.r) || (o.k==='size' && f.emp>=20 && f.emp<=300)
            || (o.k==='export' && f.ex) || (o.k==='tel' && (f.tg===3 || f.tg===4))
            || (o.k==='grow' && f.hin > f.hout);
      if(ok) why.push('<span class="wchip">'+esc(o.label)+' +'+o.pt+'</span>');
    });
    var tel = f.tel ? '<a href="tel:'+attr(f.tel)+'">'+esc(f.tel)+'</a>'
                      + '<span class="tg tg'+f.tg+'">'+TG[f.tg]+'</span>' : '';
    var trend = (f.hin || f.hout)
      ? (f.hin - f.hout > 0 ? '▲ +' : (f.hin - f.hout < 0 ? '▼ ' : '– '))
        + (f.hin - f.hout) + '명 (신규 ' + f.hin + ' / 상실 ' + f.hout + ')'
      : '';

    var telWarn = f.tg === 5
      ? '<div class="dempty"><b>이 번호는 쓰지 마십시오.</b> 카카오와 네이버가 서로 '
        + '다른 장소를 가리킵니다 — 둘 중 하나는 같은 이름의 다른 업체입니다. '
        + '<code>out\\연락처_수집결과.csv</code> 에서 두 주소를 비교하십시오.</div>'
      : (f.tg === 2 || f.tg === 1
          ? '<div class="dempty">이 번호는 상호만 맞은 것입니다. 걸기 전에 위 지도 '
            + '서비스에서 주소가 같은지 한 번 보십시오.</div>'
          : '');
    var telWhy = CT
      ? '이 업체는 카카오 장소 검색에서 못 찾았습니다. 아래 지도 서비스로 직접 찾아보십시오.'
      : '아직 연락처를 모읍니다 — <code>python src\\06_contact.py --key 카카오REST키 --scope target</code>';
    var sizeWhy = (PN || FI)
      ? '이 업체는 국민연금·DART 어느 쪽에도 이름이 맞는 곳이 없었습니다. '
        + '3인 미만이거나 상호가 다르게 등록됐을 수 있습니다.'
      : '아직 규모 정보를 안 붙였습니다 — <code>python src\\04_pension.py</code> (종업원·인건비), '
        + '<code>python src\\05_finance.py --key DART키</code> (매출)';

    DF = f;
    $('dtl').innerHTML =
      '<button class="dclose" type="button" aria-label="닫기">×</button>'
      + '<div class="dtitle"><button type="button" class="nmbtn dnamebtn">'
      + esc(f.n) + '</button></div>'
      + '<div class="dsub">' + esc(f.se) + (f.pm ? ' · ' + esc(f.pm) : '')
      + ' · ' + esc(f.s) + ' ' + esc(f.g) + '</div>'
      + (f.sc ? '<div class="dscore"><b>' + f.sc + '</b>점 <span>영업 우선순위</span></div>'
                + '<div class="dwhy">' + why.join('') + '</div>' : '')
      + sect('연락', [
          row('전화', tel),
          row('지도', linkRow(f)),
          row('주소', esc(f.a)),
          row('산업단지', f.c ? esc(f.c) + ' <span class="dim">' + esc(f.ct) + '</span>' : '개별입지')
        ], telWhy)
      + telWarn
      + sect('규모', [
          row('종업원', f.emp ? n0(f.emp) + '명 <span class="dim">국민연금 가입자</span>' : ''),
          row('인건비', f.amt ? won(f.amt * 12 / 0.09) + ' <span class="dim">고지액에서 추정한 연 급여총액</span>' : ''),
          row('고용 추이', trend, (f.hin - f.hout) > 0 ? 'up' : ((f.hin - f.hout) < 0 ? 'down' : '')),
          row('매출', f.fs ? won(f.fs) + ' <span class="dim">' + esc(f.fn) + ' ' + (FI ? FI.year : '') + '</span>' : '')
        ], sizeWhy)
      + sect('탄소', [
          row('생산품', esc(f.p)),
          row('CBAM 품목', f.cb ? '<span class="kchip" style="background:'+CBCOLOR[f.cb]+'">'+esc(f.cb)+'</span>' : ''),
          row('열공정', f.h !== '해당없음' ? esc(f.h) : ''),
          row('규제', f.r ? (f.r === 1 ? '배출권거래제 할당대상' : '명세서 제출 법인')
                          : '<b class="hi">규제 밖</b> <span class="dim">배출량을 세어본 적이 없는 곳</span>'),
          row('배출량', f.e ? n0(f.e) + ' tCO₂eq <span class="dim">' + esc(f.ln) + ' 법인 전체</span>' : ''),
          row('수출 명단', f.ex ? esc(f.ex) : '')
        ], '생산품 정보가 없어 탄소 관련 판정을 못 했습니다.')
      + (f.ex ? ''
              : '<div class="dnote">' + (EX
                  ? '수출 명단에 없습니다 — 수출을 안 한다는 뜻은 아닙니다. 개별 기업 수출실적은 공개되지 않습니다.'
                  : '수출 명단을 아직 안 붙였습니다 — 명단 파일을 <code>data\\export\\</code> 에 넣고 '
                    + '<code>python src\\07_export.py</code>') + '</div>');
    openDrawer();
  }

  // ---- 오른쪽 서랍 여닫기 (상세 · 조건) ----
  function openDrawer(){
    closeFilters();
    $('dtl').classList.add('open');
    $('dscrim').classList.add('open');
    var b = $('dtl').querySelector('.dclose');
    if(b){ b.onclick = closeDrawer; b.focus(); }
    var t = $('dtl').querySelector('.dnamebtn');
    if(t) t.onclick = function(ev){ ev.stopPropagation(); openMenu(t, DF); };
    $('dtl').scrollTop = 0;
  }
  function closeDrawer(){
    $('dtl').classList.remove('open');
    $('dscrim').classList.remove('open');
  }
  function openFilters(){
    closeDrawer();
    $('controls').classList.add('open');
    $('fscrim').classList.add('open');
  }
  function closeFilters(){
    $('controls').classList.remove('open');
    $('fscrim').classList.remove('open');
  }
  $('dscrim').onclick = closeDrawer;
  $('fscrim').onclick = closeFilters;
  $('cclose').onclick = closeFilters;
  $('fabf').onclick = function(){
    if($('controls').classList.contains('open')) closeFilters(); else openFilters();
  };
  document.addEventListener('keydown', function(e){
    if(e.key !== 'Escape') return;
    if($('dtl').classList.contains('open')) closeDrawer();
    else if($('controls').classList.contains('open')) closeFilters();
  });

  // ---- 현재 목록 내려받기 ----
  // 지금 조건에서 어느 정보가 몇 곳에 붙어 있는지를 표 위에 늘 띄운다.
  // 0곳이면 붙이는 단계를 안 돌린 것이지 연결이 깨진 것이 아니다 — 그 말을 화면이 해야 한다.
  // 지금 조건에서 어느 정보가 몇 곳에 붙어 있는지를 표 위에 늘 띄운다.
  // 이 숫자는 업체마다 붙는 값이고, 여기 적히는 것은 "그 값을 가진 곳이 몇 곳인가"다.
  // 0곳이면 붙이는 단계를 안 돌린 것이지 연결이 깨진 것이 아니다 — 그 말을 화면이 해야 한다.
  function coverStrip(rows){
    var c = {e:0, emp:0, fs:0, tel:0, ex:0};
    rows.forEach(function(f){
      if(f.e) c.e++; if(f.emp) c.emp++; if(f.fs) c.fs++;
      if(f.tel) c.tel++; if(f.ex) c.ex++;
    });
    var N = rows.length;
    var pc = function(v){ return N ? (v / N * 100).toFixed(v / N >= 0.1 ? 0 : 1) + '%' : '0%'; };
    var items = [['배출량', c.e], ['종업원', c.emp], ['매출', c.fs],
                 ['전화', c.tel], ['수출명단', c.ex]];
    $('cover').innerHTML =
      '<span class="cvlab">지금 조건에 걸린 <b>' + n0(N) + '</b>곳 가운데, 값이 붙어 있는 업체 수</span>'
      + items.map(function(o){
          return '<span class="cvi' + (o[1] ? '' : ' zero') + '" title="'
               + attr(o[0] + ' 값이 있는 업체 ' + n0(o[1]) + '곳 / ' + n0(N) + '곳')
               + '">' + o[0] + ' <b>' + n0(o[1]) + '</b>'
               + (o[1] ? '<span class="cvp">' + pc(o[1]) + '</span>' : '') + '</span>';
        }).join('');
    scoreWarn(rows);
  }

  // 우선순위가 전부 같은 값으로 나오는 일이 있다. 붙인 자료가 없어서
  // 7개 기준 중 몇 개가 아예 켜지지 않기 때문이다. 그 사정을 그대로 적는다.
  function scoreWarn(rows){
    var w = $('scorewarn');
    var live = { cbam:true, heat:true, unreg:true,
                 size:!!PN, grow:!!PN, tel:!!CT, export:!!EX };
    var off = (D.meta.score || []).filter(function(o){ return !live[o.k]; });
    var seen = {}, nd = 0;
    for(var i = 0; i < rows.length; i++){
      var v = rows[i].sc || 0;
      if(!seen[v]){ seen[v] = 1; nd++; }
    }
    if(!off.length && nd > 3){ w.hidden = true; return; }
    w.hidden = false;
    w.innerHTML =
      '<b>우선순위 점수가 몇 종류로 뭉쳐 있습니다.</b> 지금 조건에서 나오는 점수는 '
      + nd + '가지뿐입니다. 7개 기준 가운데 <b>' + (7 - off.length) + '개</b>만 켜져 있기 때문입니다.'
      + (off.length
          ? '<ul class="dlfix">' + off.map(function(o){
              return '<li>' + esc(o.label) + ' (+' + o.pt + ') — 자료가 없어 모든 업체가 0점</li>';
            }).join('') + '</ul>'
            + '종업원·연락처·수출명단을 붙이면 같은 75점 안에서도 순위가 갈립니다.'
          : '');
  }

  function showDlNote(nRows, nKeep, gone){
    var note = $('dlnote');
    note.hidden = false;
    if(!gone.length){
      note.innerHTML = '내려받았습니다 — ' + n0(nRows) + '곳 · 열 ' + nKeep + '개 모두 값이 있습니다.';
      return;
    }
    note.innerHTML = '내려받았습니다 — ' + n0(nRows) + '곳. <b>'
      + gone.map(function(c){ return esc(c[0]); }).join(' · ')
      + '</b> 열은 이 조건에서 값이 하나도 없어 파일에서 뺐습니다. '
      + '연결이 끊긴 것이 아니라 <b>그 정보를 붙이는 단계를 아직 안 돌린 것</b>입니다.'
      + '<ul class="dlfix">' + gone.filter(function(c){ return c[2]; })
          .map(function(c){ return '<li>' + esc(c[2]) + '</li>'; }).join('') + '</ul>';
  }

  // 내려받기 열 정의. 어느 열이 비는지 알아야 하니 한 곳에 모아 둔다.
  // 붙이는 단계(04 국민연금 · 05 재무 · 06 연락처 · 07 수출명단)를 안 돌리면
  // 그 열은 전부 빈다. 빈 열을 그대로 내보내면 "연계가 깨졌다"로 읽히므로,
  // 통째로 빈 열은 빼고 무엇이 왜 빠졌는지 화면에 적는다.
  var CSVCOL = [
    ['회사명',       function(f){ return f.n; },  ''],
    ['업종',         function(f){ return f.se; }, ''],
    ['품목',         function(f){ return f.pm; }, ''],
    ['생산품',       function(f){ return f.p; },  ''],
    ['CBAM',        function(f){ return f.cb; }, ''],
    ['열공정',       function(f){ return f.h !== '해당없음' ? f.h : ''; }, ''],
    ['규제',         function(f){ return f.r===1?'할당대상':(f.r===2?'명세서':'규제 밖'); }, ''],
    ['배출량tCO2eq', function(f){ return f.e || ''; },
     '배출량 — 규제 대상 법인만 공개됩니다. data\\emission\\ 을 채우고  python src\\03_emission.py'],
    ['종업원수',     function(f){ return f.emp || ''; },
     '종업원수 — 국민연금 사업장 자료가 있어야 붙습니다. data\\pension\\ 을 채우고  python src\\04_pension.py'],
    ['매출액',       function(f){ return f.fs || ''; },
     '매출액 — DART 공시 법인만 있습니다.  python src\\05_finance.py --key DART키'],
    ['전화번호',     function(f){ return f.tel || ''; },
     '전화번호 —  python src\\06_contact.py --key 카카오REST키 --scope target'],
    ['연락처신뢰도', function(f){ return f.tel ? (TG[f.tg] || '') : ''; }, ''],
    ['수출명단',     function(f){ return f.ex || ''; },
     '수출명단 — 명단 파일을 data\\export\\ 에 넣고  python src\\07_export.py'],
    ['산업단지',     function(f){ return f.c; },  ''],
    ['단지유형',     function(f){ return f.ct; }, ''],
    ['시도',         function(f){ return f.s; },  ''],
    ['시군구',       function(f){ return f.g; },  ''],
    ['주소',         function(f){ return f.a; },  ''],
    ['우선순위',     function(f){ return f.sc; }, '']
  ];

  function downloadCsv(){
    var rows = filtered();
    var vals = CSVCOL.map(function(){ return []; });
    rows.forEach(function(f){
      CSVCOL.forEach(function(c, i){
        var v = c[1](f);
        vals[i].push(v == null ? '' : String(v));
      });
    });
    var keep = [], gone = [];
    CSVCOL.forEach(function(c, i){
      var any = false;
      for(var j = 0; j < vals[i].length; j++){ if(vals[i][j] !== ''){ any = true; break; } }
      if(any) keep.push(i); else gone.push(c);
    });

    var q = function(v){ return '"' + v.replace(/"/g,'""') + '"'; };
    var out = [keep.map(function(i){ return q(CSVCOL[i][0]); }).join(',')];
    for(var r = 0; r < rows.length; r++){
      out.push(keep.map(function(i){ return q(vals[i][r]); }).join(','));
    }
    showDlNote(rows.length, keep.length, gone);

    var blob = new Blob(['﻿' + out.join('\r\n')],
                        {type:'text/csv;charset=utf-8;'});
    var a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = '영업리스트_' + rows.length + '곳.csv';
    document.body.appendChild(a); a.click();
    setTimeout(function(){ URL.revokeObjectURL(a.href); a.remove(); }, 500);
  }

  function firmTable(){
    var rows=filtered();
    var tb=$('ft').querySelector('tbody'); tb.innerHTML='';
    var shown=rows.slice(0,300);
    shown.forEach(function(f, i){
      var tr=el('tr');
      tr.innerHTML='<td><button type="button" class="nmbtn" data-i="'+i+'">'+esc(f.n)+'</button></td>'+
        '<td><span class="kchip" style="background:'+SECCOLOR(f.se)+'">'+esc(f.se)+'</span></td>'+
        '<td>'+(f.h!=='해당없음'?esc(f.h):'<span class="sub" style="margin:0">—</span>')+
          (f.cb?'<span class="sub">CBAM '+esc(f.cb)+'</span>':'')+'</td>'+
        '<td class="n sc"><span class="scv'+(f.sc>=60?' hot':'')+'">'+(f.sc||0)+'</span></td>'+
        '<td class="n pc">'+(f.emp?'<b>'+n0(f.emp)+'</b>':'<span class="sub" style="margin:0">—</span>')+'</td>'+
        '<td class="tc">'+(f.tel?esc(f.tel)+'<span class="sub"><span class="tg tg'+f.tg+'">'+TG[f.tg]+'</span></span>'
                              :'<span class="sub" style="margin:0">—</span>')+'</td>'+
        '<td class="n ec">'+(EM?emitCell(f):'')+'</td>'+
        '<td class="n fc">'+(FI?finCell(f):'')+'</td>'+
        '<td>'+esc(f.p)+(f.ex?'<span class="sub"><span class="exchip">수출 '+esc(f.ex)+'</span></span>':'')+'</td>'+
        '<td>'+(f.c?esc(f.c)+'<span class="sub">'+esc(f.ct)+'</span>':'<span class="sub" style="margin:0">개별입지</span>')+'</td>';
      tr.style.cursor='pointer';
      tr.onclick=function(ev){ if(!ev.target.closest('.nmbtn')) detail(f); };
      tb.appendChild(tr);
    });
    tb.querySelectorAll('.nmbtn').forEach(function(b){
      b.onclick=function(ev){ ev.stopPropagation(); openMenu(b, shown[+b.getAttribute('data-i')]); };
    });
    var extra = rows.length>300 ? ' · 표에는 300건만 표시 (검색으로 좁히세요)' : '';
    var f=[];
    if(st.sec)f.push(st.sec); if(st.pm)f.push('품목 '+st.pm);
    if(st.cxt)f.push(st.cxt); if(st.heat)f.push('열공정 '+st.heat);
    if(st.cb)f.push('CBAM '+st.cb); if(st.reg)f.push(st.reg);
    if(st.size)f.push(st.size); if(st.tel)f.push('연락처 있음'); if(st.exp)f.push('수출명단');
    if(st.sido)f.push(st.sido); if(st.cx)f.push(st.cx);
    if(st.q)f.push('"'+st.q+'"');
    $('fcount').textContent='필터 결과 '+n0(rows.length)+'건'+(f.length?' — '+f.join(' / '):'')+extra;
  }

  function draw(){
    _F = null; _SA = null;
    var _rr = filtered(), _pp = 0;
    for(var _k = 0; _k < _rr.length; _k++) if(_rr[_k].y) _pp++;
    $('mapsub').textContent = (_pp > 0 && _pp / _rr.length >= 0.5)
      ? '점 하나가 공장 한 곳 · ' + n0(_pp) + '곳 표시'
      : '시도 색 = 조건 일치 ' + n0(_rr.length) + '곳 · 점 = 좌표를 확보한 ' + n0(_pp) + '곳';
    controls(); tiles(); map(); bars(); cxTable(); firmTable(); emitPanel();
    coverStrip(_rr);
    $('dlnote').hidden = true;
    // 조건 서랍을 접어두는 좁은 화면에서는, 지금 몇 개가 걸려 있는지 단추에 적어준다
    var on = 0;
    ['sec','pm','cxt','heat','cb','reg','size','sido','cx','q'].forEach(function(k){
      if(st[k]) on++;
    });
    if(st.tel) on++; if(st.exp) on++;
    $('fabn').textContent = on ? on + '개 · ' + n0(_rr.length) : n0(_rr.length) + '곳';
  }

  var t=null;
  $('q').addEventListener('input',function(e){
    clearTimeout(t);
    t=setTimeout(function(){ st.q=e.target.value.trim().toLowerCase(); st.cx=null; draw(); },180);
  });
  $('reset').onclick=function(){ st={sec:null,pm:null,cxt:null,heat:null,cb:null,reg:null,
    size:null,tel:false,exp:false,sido:null,cx:null,q:'',sort:st.sort}; view={k:1,tx:0,ty:0}; $('q').value=''; draw(); };

  (function label(){
    var e=$('eyebrow');
    if(e) e.textContent = D.meta.scopeLabel + ' ' + n0(D.meta.shown) + '곳 · '
      + D.meta.source;
  })();

  (function countOnce(){
    for(var i=0;i<D.firms.length;i++){
      var f=D.firms[i];
      TOT.h[f.h]=(TOT.h[f.h]||0)+1;
      if(f.cb) TOT.cb[f.cb]=(TOT.cb[f.cb]||0)+1;
      var k=regKey(f); TOT.reg[k]=(TOT.reg[k]||0)+1;
      if(f.pm) PMTOT[f.pm]=(PMTOT[f.pm]||0)+1;
      if(f.tel) TELTOT++;
      if(f.ex) EXPTOT++;
      if(f.emp) for(var z=0;z<SIZE.length;z++)
        if(f.emp>=SIZE[z][1] && f.emp<=SIZE[z][2]) SZTOT[SIZE[z][0]]=(SZTOT[SIZE[z][0]]||0)+1;
    }
    TOPPM = Object.keys(PMTOT).sort(function(a,b){ return PMTOT[b]-PMTOT[a]; }).slice(0,80);
  })();

  if(D.meta.geocoded>0){
    var pn=document.getElementById('posnote');
    if(pn) pn.textContent='지오코딩으로 얻은 좌표('+n0(D.meta.geocoded)+'건)입니다 — 도로명 기준이라 부지 중심이 아닌 출입구 근처일 수 있습니다';
  }
  draw();
  }   // boot 끝

  // ---- 데이터 공급 ----
  // 로컬 파일은 HTML 안에 데이터를 넣어 두고(파일 하나로 열려야 하니까),
  // 웹에 올린 판은 data.jgz 를 따로 받는다. 확장자를 .gz 로 두면 서버가
  // 알아서 풀어 보내는 곳이 있어 두 번 푸는 사고가 나므로 .jgz 로 둔다.
  function showErr(msg){
    var b = document.getElementById('boot');
    if(b) b.innerHTML = '<b>데이터를 불러오지 못했습니다</b><br>' + msg;
  }
  function dropBoot(){ var b = document.getElementById('boot'); if(b) b.remove(); }
  var _p = document.getElementById('payload'), _t = _p ? _p.textContent.trim() : '';
  if(_t.length > 2){
    // 데이터가 파일 안에 들어 있는 판 — 로딩 문구를 지우는 걸 빠뜨려
    // "불러오는 중"이 계속 남아 있었다.
    boot(JSON.parse(_t));
    dropBoot();
  } else {
    fetch('data.jgz').then(function(r){
      if(!r.ok) throw new Error('data.jgz — HTTP ' + r.status);
      return r.arrayBuffer();
    }).then(function(buf){
      var u = new Uint8Array(buf);
      // gzip 매직(1f 8b)이 남아 있으면 우리가 풀고, 서버가 이미 풀었으면 그대로 쓴다
      if(u[0] === 0x1f && u[1] === 0x8b){
        if(typeof DecompressionStream === 'undefined')
          throw new Error('이 브라우저는 gzip 해제를 지원하지 않습니다. 최신 크롬·엣지·사파리를 쓰십시오.');
        return new Response(new Blob([u]).stream()
                 .pipeThrough(new DecompressionStream('gzip'))).json();
      }
      return JSON.parse(new TextDecoder().decode(u));
    }).then(function(d){
      dropBoot();
      boot(d);
    }).catch(function(e){ showErr(String(e && e.message || e)); });
  }
})();
</script>'''

SHELL = (HTML.replace('/*__LEAFLET_CSS__*/', LEAFLET_CSS)
             .replace('//__LEAFLET_JS__', LEAFLET_JS)
             .replace('__BOUNDARY__', BOUNDARY))

def standalone(body):
    """혼자 열리는 완전한 HTML 로 감싼다.

    charset 을 안 적으면 서버나 브라우저가 제 마음대로 인코딩을 골라 한글이 깨진다.
    (파일을 웹서버에 올리자마자 '필터 결과'가 'í•„í„° ê²°ê³¼'로 나왔다.)
    map_page.html 은 감싸지 않은 조각으로 둔다 — 아티팩트 쪽이 머리말을 직접 붙인다.
    """
    head, rest = body.split('<div class="app">', 1)
    return ('<!doctype html>\n<html lang="ko">\n<head>\n'
            '<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width,initial-scale=1">\n'
            '<meta name="color-scheme" content="light dark">\n'
            + head +
            '</head>\n<body>\n<div class="app">' + rest + '\n</body>\n</html>\n')

if '--web' in sys.argv:
    # 배포용 — HTML 과 데이터를 나눈다.
    #   · Cloudflare Pages 는 파일 하나가 25 MiB 를 넘으면 올라가지 않는다
    #   · 나눠 두면 데이터만 브라우저가 캐시한다
    #   · gzip 으로 27MB → 6MB 남짓이 된다
    import gzip
    open(os.path.join(paths.WEB, 'index.html'), 'w', encoding='utf-8').write(
        standalone(SHELL.replace('__DATA__', '')))
    with gzip.GzipFile(os.path.join(paths.WEB, 'data.jgz'), 'wb',
                       compresslevel=9, mtime=0) as f:
        f.write(data.encode('utf-8'))
    # Cloudflare Pages 설정 파일. 배포 폴더 안에 있어야 먹으므로 여기서 같이 쓴다.
    #
    #   data.jgz 는 우리가 직접 gzip 으로 만든 파일이고, 페이지가 앞 두 바이트(1f 8b)를
    #   보고 DecompressionStream 으로 스스로 풉니다. 그래서 서버가 Content-Encoding: gzip
    #   을 붙이면 브라우저가 먼저 풀어버려 우리 코드가 두 번 푸는 꼴이 됩니다.
    #   확장자를 .jgz 로 둔 것도 서버가 알아서 손대지 않게 하려는 것입니다.
    open(os.path.join(paths.WEB, '_headers'), 'w', encoding='utf-8').write(
        '/data.jgz\n'
        '  Content-Type: application/octet-stream\n'
        '  Cache-Control: public, max-age=300, must-revalidate\n'
        '\n'
        '/index.html\n'
        '  Cache-Control: public, max-age=0, must-revalidate\n'
        '\n'
        '/*\n'
        '  X-Content-Type-Options: nosniff\n'
        '  Referrer-Policy: strict-origin-when-cross-origin\n')

    h = os.path.getsize(os.path.join(paths.WEB, 'index.html')) / 1e6
    d = os.path.getsize(os.path.join(paths.WEB, 'data.jgz')) / 1e6
    print(f"web/index.html {h:.2f} MB + web/data.jgz {d:.2f} MB  (원본 {len(data.encode())/1e6:.1f} MB)")
    print("  web/_headers 도 같이 만들었습니다 (Cloudflare Pages 설정)")
    if d > 25:
        print("  ! data.jgz 가 25 MiB 를 넘습니다. Cloudflare Pages 한도입니다. "
              "SCOPE=target 으로 줄이십시오.")
else:
    full = SHELL.replace('__DATA__', data)
    frag = paths.out('page_fragment.html')
    idx = paths.out('index.html')
    open(frag, 'w', encoding='utf-8').write(full)            # 아티팩트용 조각
    open(idx, 'w', encoding='utf-8').write(standalone(full))  # 두 번 눌러 여는 판
    print(f"out\\index.html {os.path.getsize(idx)/1e6:.2f} MB")
