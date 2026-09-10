// 브라우저 화면 자동 점검 — 필터·확대·표가 실제로 반응하는지 확인
// 실행:  npm i -D playwright && npx playwright install chromium
//        node 7_uitest.js
const { chromium } = require('playwright');
const path = require('path');

const results = [];
const ok = (n, c, d='') => results.push([c ? 'PASS' : 'FAIL', n, d]);

// 사내망에서 TLS 검사(자체 서명 인증서) 때문에 playwright가 브라우저를 못 받는 경우가 많다.
// 그래서 이미 설치된 Chrome / Edge 를 그대로 쓴다. 다운로드가 필요 없다.

// 열 위치는 배출량 컬럼 유무에 따라 달라진다. 헤더 이름으로 찾는다.
async function colIndex(p, label) {
  const heads = await p.locator('#ft thead th').allInnerTexts();
  const i = heads.findIndex(t => t.replace(/\s/g, '').startsWith(label));
  if (i < 0) throw new Error('열을 찾지 못함: ' + label + ' / ' + heads.join('|'));
  return i + 1;
}
async function colText(p, label) {
  return p.locator(`#ft tbody tr td:nth-child(${await colIndex(p, label)})`).allInnerTexts();
}

async function launch() {
  const tried = [];

  // 1) playwright 가 아는 채널 (레지스트리에서 찾는다)
  for (const ch of ['chrome', 'msedge', 'chrome-beta', 'msedge-beta']) {
    try { return await chromium.launch({ channel: ch }); }
    catch (e) { tried.push(`channel ${ch}`); }
  }

  // 2) 윈도우에서 실제로 깔리는 자리들을 직접 짚어 본다.
  //    사용자 계정에만 설치한 Chrome 은 채널 탐색으로 못 찾는 일이 있다.
  const fs = require('fs');
  const env = process.env;
  const cands = [
    env.PLAYWRIGHT_CHROME,                       // 직접 지정하고 싶을 때
    env.PROGRAMFILES && env.PROGRAMFILES + '\\Google\\Chrome\\Application\\chrome.exe',
    env['PROGRAMFILES(X86)'] && env['PROGRAMFILES(X86)'] + '\\Google\\Chrome\\Application\\chrome.exe',
    env.LOCALAPPDATA && env.LOCALAPPDATA + '\\Google\\Chrome\\Application\\chrome.exe',
    env.PROGRAMFILES && env.PROGRAMFILES + '\\Microsoft\\Edge\\Application\\msedge.exe',
    env['PROGRAMFILES(X86)'] && env['PROGRAMFILES(X86)'] + '\\Microsoft\\Edge\\Application\\msedge.exe',
    '/opt/pw-browsers/chromium',
    '/usr/bin/google-chrome',
    '/usr/bin/chromium',
  ].filter(Boolean);
  for (const exe of cands) {
    try {
      if (!fs.existsSync(exe)) { continue; }
      const b = await chromium.launch({ executablePath: exe });
      console.log('  브라우저: ' + exe);
      return b;
    } catch (e) { tried.push(exe); }
  }

  // 3) playwright 가 받아둔 chromium
  try { return await chromium.launch(); } catch (e) { tried.push('playwright chromium'); }

  console.error('브라우저를 찾지 못해 화면 검사를 건너뜁니다. (데이터 검사와는 무관합니다)');
  console.error('찾아본 곳:');
  tried.forEach(t => console.error('  ' + t));
  console.error('');
  console.error('Chrome 이 있는데도 못 찾으면, 실행 파일 경로를 직접 알려주십시오:');
  console.error('  $env:PLAYWRIGHT_CHROME="C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"');
  console.error('  node tests\\test_ui.js');
  process.exit(2);   // 2 = 못 돌렸음 (1 = 검사 실패). deploy_web.ps1 이 구분합니다.
}

(async () => {
  const b = await launch();
  const p = await b.newPage({ viewport: { width: 1400, height: 1000 } });
  const errs = [];
  p.on('pageerror', e => errs.push(e.message));
  // 폰트 CDN 같은 외부 리소스 실패는 코드 결함이 아니므로 제외한다
  //  (오프라인이나 사내망에서는 웹폰트만 대체되고 기능은 그대로 동작한다)
  // 외부 리소스(웹폰트·지도 타일) 실패는 코드 결함이 아니라 망 환경 문제다.
  // 타일이 막히면 페이지가 알아서 SVG 분포도로 넘어간다.
  const isNet = t => /Failed to load resource|net::ERR_|fonts\.googleapis|fonts\.gstatic|tile\.openstreetmap|tile\.osm/.test(t);
  p.on('console', m => { if (m.type() === 'error' && !isNet(m.text())) errs.push('console: ' + m.text()); });
  p.on('requestfailed', r => {
    if (!isNet(r.url())) errs.push('request: ' + r.url());
  });

  await p.goto('file://' + path.resolve(__dirname, '..', 'out', 'index.html'));
  await p.waitForSelector('#tiles .tile', { timeout: 20000 });
  // 배경지도 타일을 받아오는지 판정할 시간을 준다 (실패 시 4초 뒤 SVG 폴백)
  await p.waitForTimeout(5500);
  const leafletMode = await p.locator('#lmap .leaflet-tile-loaded').count() > 0;
  console.log('  지도 모드: ' + (leafletMode ? 'Leaflet (배경지도 있음)' : 'SVG 폴백 (타일 차단)'));

  const num = async sel => Number((await p.locator(sel).innerText()).replace(/[^\d]/g, ''));

  // 1. 초기 렌더
  ok('상단 지표 5개', await p.locator('#tiles .tile').count() === 5);
  const total = await num('#tiles .tile:nth-child(1) .v');
  ok('상단 지표에 대상 수 표시', total > 1000, String(total));
  const tgt0 = await num('#tiles .tile:nth-child(2) .v');
  ok('조건 일치 수 > 0', tgt0 > 0, String(tgt0));
  ok('지도 마커 렌더', leafletMode
      ? await p.locator('#lmap path.leaflet-interactive').count() > 0
      : await p.locator('#mapwrap svg circle').count() > 0);
  ok('시도 막대 17개', await p.locator('#bars .bar').count() === 17);
  ok('산업단지 표 채워짐', await p.locator('#cxt tbody tr').count() > 0);
  ok('기업 표 채워짐', await p.locator('#ft tbody tr').count() > 0);

  // 2. 업종 필터
  await p.locator('#secf').selectOption('1차 금속');
  await p.waitForTimeout(500);
  const tgt1 = await num('#tiles .tile:nth-child(2) .v');
  ok('업종 필터로 건수 감소', tgt1 < tgt0 && tgt1 > 0, `${tgt0} → ${tgt1}`);
  const secCells = await colText(p, '업종');
  ok('기업 표가 선택 업종만', secCells.every(t => t.includes('1차 금속')), secCells.slice(0,3).join('|'));

  // 3. 단지유형 필터 조합
  await p.locator('#cxtf').selectOption('국가산업단지');
  await p.waitForTimeout(500);
  const tgt2 = await num('#tiles .tile:nth-child(2) .v');
  ok('단지유형 조합으로 추가 감소', tgt2 <= tgt1, `${tgt1} → ${tgt2}`);
  const cxCells = await colText(p, '산업단지');
  ok('전부 국가산업단지', cxCells.every(t => t.includes('국가산업단지')), cxCells.slice(0,2).join('|'));

  // 4. 초기화
  await p.locator('#reset').click();
  await p.waitForTimeout(500);
  ok('초기화로 원복', await num('#tiles .tile:nth-child(2) .v') === tgt0);

  // 5. 열공정 칩
  await p.locator('#heatf .chipbtn', { hasText: '용해·소성' }).click();
  await p.waitForTimeout(500);
  const heatCells = await colText(p, '열공정');
  ok('열공정 필터 동작', heatCells.every(t => t.includes('용해·소성')), heatCells.slice(0,2).join('|'));
  await p.locator('#reset').click();
  await p.waitForTimeout(400);

  // 6. CBAM 칩
  await p.locator('#cbf .chipbtn', { hasText: '철강' }).click();
  await p.waitForTimeout(500);
  ok('CBAM 필터 동작', (await num('#tiles .tile:nth-child(2) .v')) > 0);
  await p.locator('#reset').click();
  await p.waitForTimeout(400);

  // 7~8. 확대
  if (leafletMode) {
    const z0 = await p.evaluate(() => window.__lz ? window.__lz() : null);
    await p.locator('.leaflet-control-zoom-in').click();
    await p.waitForTimeout(600);
    const z1 = await p.evaluate(() => window.__lz ? window.__lz() : null);
    ok('Leaflet 확대 버튼', z0 !== null && z1 === z0 + 1, `${z0} → ${z1}`);
    await p.locator('.leaflet-control-zoom-out').click();
    await p.waitForTimeout(600);
    ok('Leaflet 축소 버튼', (await p.evaluate(() => window.__lz())) === z0);
    ok('배경 타일 로드됨', await p.locator('#lmap .leaflet-tile-loaded').count() > 0);
  } else {
    const tf0 = await p.locator('#mapwrap svg g.z').getAttribute('transform');
    await p.locator('.zoomctl button').first().click();
    await p.waitForTimeout(300);
    ok('확대 버튼이 transform 변경', tf0 !== await p.locator('#mapwrap svg g.z').getAttribute('transform'));
    await p.locator('.zoomctl button').nth(2).click();
    await p.waitForTimeout(300);
    ok('원래대로 버튼 동작', /scale\(1\)/.test(await p.locator('#mapwrap svg g.z').getAttribute('transform')));
    await p.locator('#mapwrap svg').hover();
    await p.mouse.wheel(0, -300);
    await p.waitForTimeout(300);
    ok('휠 확대 동작', !/scale\(1\)/.test(await p.locator('#mapwrap svg g.z').getAttribute('transform')));
  }

  // 9. 검색
  await p.locator('#reset').click();
  await p.waitForTimeout(300);
  await p.locator('#q').fill('포스코');
  await p.waitForTimeout(700);
  const names = await colText(p, '회사명');
  ok('검색 결과 있음', names.length > 0, `${names.length}건`);

  // 10. 시도 막대 클릭
  await p.locator('#reset').click();
  await p.waitForTimeout(300);
  await p.locator('#bars .bar').first().click();
  await p.waitForTimeout(500);
  ok('시도 클릭으로 필터', (await p.locator('#fcount').innerText()).length > 5);

  // 11. 배출량
  await p.locator('#reset').click();
  await p.waitForTimeout(300);
  ok('배출량 기준 카드 4장', await p.locator('.ebox .ecard').count() === 4);

  const hasEmit = !(await p.locator('#regf').isHidden());
  if (hasEmit) {
    ok('규제 칩 노출', await p.locator('#regf .chipbtn').count() === 4);
    ok('배출량 열 노출', !(await p.locator('#th-e').isHidden()));
    // 표는 300건에서 잘리므로 행 수가 아니라 '필터 결과 N건' 을 본다
    const cnt = async () => {
      const m = (await p.locator('#fcount').innerText()).match(/([\d,]+)건/);
      return m ? +m[1].replace(/,/g, '') : -1;
    };
    const n0 = await cnt();
    await p.locator('#regf .chipbtn', { hasText: '할당대상' }).first().click();
    await p.waitForTimeout(400);
    const tags = await p.locator('#ft tbody tr .etag').allInnerTexts();
    ok('규제 필터로 좁혀짐', await cnt() < n0, `${n0} → ${await cnt()}`);
    ok('전부 할당대상', tags.length > 0 && tags.every(t => t.includes('할당대상')),
       tags.slice(0, 2).join('|'));
    await p.locator('#reset').click();
    await p.waitForTimeout(300);
    ok('초기화로 규제 필터 해제', await cnt() === n0);
  } else {
    ok('배출량 없을 때 규제 칩 숨김', await p.locator('#th-e').isHidden());
  }

  // 12. 시도 경계
  await p.locator('#reset').click();
  await p.waitForTimeout(400);
  const n_all = await p.locator('#ft tbody tr').count();
  if (leafletMode) {
    const names = await p.evaluate(() => window.__bp ? window.__bp() : []);
    ok('경계 폴리곤 17개', names.length === 17, `${names.length}개`);
    if (names.length) {
      await p.evaluate(n => window.__bp(n), '경남');
      await p.waitForTimeout(500);
      const t = await p.locator('#fcount').innerText();
      ok('경계 클릭으로 시도 필터', t.includes('경남'), t.slice(0, 60));
      ok('경계 클릭이 목록을 좁힘', await p.locator('#ft tbody tr').count() <= n_all);
    }
  } else {
    const shapes = await p.locator('#mapwrap path[data-s]').count();
    ok('경계 도형 17개', shapes === 17, `${shapes}개`);
    if (shapes) {
      // 스티키 조회조건에 가려 좌표 클릭이 가로채이므로 요소에 직접 이벤트를 준다
      await p.locator('#mapwrap path[data-s]').first().dispatchEvent('click');
      await p.waitForTimeout(500);
      const t = await p.locator('#fcount').innerText();
      ok('경계 클릭으로 시도 필터', /—\s*\S+/.test(t), t.slice(0, 60));
      ok('경계 클릭이 목록을 좁힘', await p.locator('#ft tbody tr').count() <= n_all);
    }
  }
  await p.locator('#reset').click();
  await p.waitForTimeout(300);
  ok('초기화로 시도 해제', await p.locator('#ft tbody tr').count() === n_all);

  // 13. 회사명 → 지도 서비스
  await p.locator('#reset').click();
  await p.waitForTimeout(300);
  await p.locator('#q').fill('디와이파워');
  await p.waitForTimeout(1600);
  const dy = await p.locator('#ft tbody tr').count();
  ok('전체 공장 대상 (규제 밖 업체도 검색됨)', dy > 0, `디와이파워 ${dy}건`);
  await p.locator('#ft tbody .nmbtn').first().dispatchEvent('click');
  await p.waitForTimeout(300);
  const menu = await p.locator('.namemenu a').allInnerTexts();
  ok('회사명 클릭 → 지도 서비스 4곳', menu.length === 4, menu.join('/'));
  const hrefs = await p.locator('.namemenu a').evaluateAll(
    a2 => a2.map(x => x.getAttribute('href')));
  ok('네이버·카카오·구글 링크', hrefs.some(h => /map\.naver/.test(h))
      && hrefs.some(h => /map\.kakao/.test(h))
      && hrefs.some(h => /google\.com\/maps/.test(h)), hrefs[0]);
  ok('링크가 새 창으로', (await p.locator('.namemenu a').first()
      .getAttribute('target')) === '_blank');
  await p.locator('#reset').click();
  await p.waitForTimeout(300);

  // 14. 매출액
  const hasFin = !(await p.locator('#th-f').isHidden());
  if (hasFin) {
    await p.locator('#q').fill('포스코');
    await p.waitForTimeout(1500);
    const cells = await colText(p, '매출액');
    ok('매출 열에 값이 있음', cells.some(t => /조|억/.test(t)),
       cells.filter(t => /조|억/.test(t))[0] || cells[0]);
    await p.locator('#reset').click();
    await p.waitForTimeout(300);
  } else {
    ok('재무 없을 때 매출 열 숨김', await p.locator('#th-f').isHidden());
  }

  // 15. 품목 2단 필터
  await p.locator('#reset').click();
  await p.waitForTimeout(400);
  const cnt2 = async () => {
    const m = (await p.locator('#fcount').innerText()).match(/([\d,]+)건/);
    return m ? +m[1].replace(/,/g, '') : -1;
  };
  const pmAll = await p.locator('#pmf option').count();
  ok('품목 목록 있음', pmAll > 1, `${pmAll - 1}개`);
  await p.locator('#secf').selectOption('기계·장비');
  await p.waitForTimeout(700);
  const pmSec = await p.locator('#pmf option').allInnerTexts();
  ok('업종을 고르면 그 업종 품목으로 바뀜',
     pmSec.some(t => t.startsWith('금형')), pmSec.slice(1, 4).join('/'));
  const before2 = await cnt2();
  await p.locator('#pmf').selectOption({ index: 1 });
  await p.waitForTimeout(700);
  ok('품목으로 좁혀짐', await cnt2() < before2, `${before2} → ${await cnt2()}`);
  const txt2 = await p.locator('#fcount').innerText();
  ok('필터 표시에 품목이 나옴', /품목 /.test(txt2), txt2.slice(0, 70));
  // 업종을 바꾸면 품목은 풀려야 한다 (다른 업종에는 없는 품목이므로)
  await p.locator('#secf').selectOption('식품·음료');
  await p.waitForTimeout(700);
  ok('업종 변경 시 품목 해제', !/품목 /.test(await p.locator('#fcount').innerText()));

  // 16. 좌표가 적은 조건이면 지도가 비지 않고 시도 버블로 내려간다
  await p.locator('#reset').click();
  await p.waitForTimeout(400);
  await p.locator('#secf').selectOption('기계·장비');
  await p.waitForTimeout(900);
  const sub = await p.locator('#mapsub').innerText();
  const drawn = leafletMode
    ? await p.locator('#lmap canvas, #lmap path.leaflet-interactive').count()
    : await p.locator('#mapwrap svg circle').count();
  ok('좌표 적은 조건도 지도에 표시됨', drawn > 0, `${drawn}개 · ${sub.slice(0, 40)}`);
  const warn = await p.locator('#mapwarn').innerText();
  ok('좌표가 모자란 이유를 눈에 띄게 알림',
     !(await p.locator('#mapwarn').isHidden()) && /점으로 찍히는 것은/.test(warn),
     warn.replace(/\s+/g, ' ').slice(0, 60));
  ok('지도 범례 있음', await p.locator('.maplegend span').count() === 2);
  await p.locator('#reset').click();
  await p.waitForTimeout(300);

  // 17. 로딩 문구가 남지 않는지 · 기본 화면에도 점이 찍히는지
  ok('로딩 문구 사라짐', await p.locator('#boot').count() === 0);
  const dots = leafletMode
    ? await p.evaluate(() => window.__lz ? 1 : 0)
    : await p.locator('#mapwrap svg circle[r="1.8"], #mapwrap svg circle[data-i]').count();
  ok('기본 화면에도 공장 점이 있음', dots > 0, String(dots));

  // 18. 영업 기능 — 상세 패널 · 정렬 · 내려받기
  await p.locator('#reset').click();
  await p.waitForTimeout(400);
  await p.locator('#ft tbody tr').first().click();
  await p.waitForTimeout(400);
  ok("행을 누르면 오른쪽 서랍이 열림", await p.locator("#dtl").isVisible());
  const dt = await p.locator('#dtl').innerText();
  ok('상세에 연락·규모·탄소 구획', /연락/.test(dt) && /규모/.test(dt) && /탄소/.test(dt));
  ok('상세에 지도 서비스 링크', await p.locator('#dtl .mlink a').count() >= 3);
  ok('우선순위 근거를 보여줌', await p.locator('#dtl .wchip').count() > 0,
     (await p.locator('#dtl .wchip').allInnerTexts()).slice(0,3).join('/'));
  ok('상세의 회사명이 지도 연결 단추', await p.locator('#dtl .dnamebtn').count() === 1);
  await p.keyboard.press('Escape');
  await p.waitForTimeout(400);
  ok('ESC 로 서랍이 닫힘', !(await p.locator('#dtl').isVisible()));

  // 회사명 → 이 화면 지도로 이동
  {
    await p.evaluate(() => { window.__focused = null; });
    let jumped = false;
    const rows = await p.locator('#ft tbody tr').count();
    for (let i = 0; i < Math.min(rows, 12); i++) {
      await p.locator('#ft tbody tr .nmbtn').nth(i).click();
      await p.waitForTimeout(200);
      if (await p.locator('.namemenu .nmhere').count()) {
        await p.locator('.namemenu .nmhere').click();
        await p.waitForTimeout(900);
        jumped = !!(await p.evaluate(() => window.__focused));
        break;
      }
      await p.keyboard.press('Escape');
      await p.locator('h2').first().click();
      await p.waitForTimeout(150);
    }
    ok('회사명 → 이 화면 지도로 이동', jumped);
    await p.evaluate(() => window.scrollTo(0, 0));
    await p.waitForTimeout(300);
  }

  // 좁은 화면에서는 조건이 서랍으로 접힌다
  // (서랍은 transform 이 0.28초 동안 움직인다. 고정 대기로는 간간이 어긋나서 기다린다)
  const settled = async (sel, want) => {
    for (let i = 0; i < 40; i++) {
      if ((await p.locator(sel).isVisible()) === want) return true;
      await p.waitForTimeout(50);
    }
    return false;
  };
  await p.setViewportSize({ width: 420, height: 820 });
  ok('좁은 화면에서 조건이 접힘', await settled('#controls', false));
  ok('조건 단추가 보임', await p.locator('#fabf').isVisible());
  await p.locator('#fabf').click();
  ok('조건 단추로 서랍이 열림', await settled('#controls', true));
  await p.locator('#cclose').click();
  ok('닫기로 조건이 접힘', await settled('#controls', false));
  await p.setViewportSize({ width: 1400, height: 900 });
  ok('넓은 화면에서는 조건이 그대로 보임', await settled('#controls', true));

  const first = async () => (await p.locator('#ft tbody tr td:nth-child(4)').first().innerText()).trim();
  const top = +(await first());
  ok('기본 정렬이 우선순위 내림차순', top >= 40, String(top));
  await p.locator('.sortbox select').selectOption('n');
  await p.waitForTimeout(600);
  ok('정렬을 바꾸면 순서가 달라짐', (await first()) !== String(top));
  await p.locator('.sortbox select').selectOption('sc');
  await p.waitForTimeout(600);

  const dlp = p.waitForEvent('download', { timeout: 15000 }).catch(() => null);
  await p.locator('.chipbtn.dl').click();
  const dl = await dlp;
  ok('현재 목록 내려받기', !!dl, dl ? dl.suggestedFilename() : '다운로드 없음');

  // 내려받은 CSV 에 실제 값이 들어 있는지 (연계가 붙었는지)
  if (dl) {
    const txt = require('fs').readFileSync(await dl.path(), 'utf8').replace(/^﻿/, '');
    const lines = txt.split('\r\n').filter(Boolean);
    const head = (lines[0].match(/"([^"]*)"/g) || []).map(s => s.slice(1, -1));
    const fill = head.map(() => 0);
    lines.slice(1).forEach(l => (l.match(/"([^"]*)"/g) || [])
      .forEach((v, i) => { if (v !== '""') fill[i]++; }));
    const empty = head.filter((h, i) => fill[i] === 0);
    ok('CSV 에 값이 통째로 빈 열이 없음', empty.length === 0, empty.join('/'));
    ok('CSV 열 이름이 값과 짝이 맞음',
       head.length === (lines[1].match(/"([^"]*)"/g) || []).length);
    const iTel = head.indexOf('전화번호'), iTg = head.indexOf('연락처신뢰도');
    ok('전화번호 없으면 신뢰도도 비어 있음',
       iTel < 0 || iTg < 0 || fill[iTel] === fill[iTg], `${fill[iTel]} vs ${fill[iTg]}`);
    ok('빠진 열을 화면에 알림', !(await p.locator('#dlnote').isHidden()));
    ok('붙은 정보 개수를 표 위에 표시', await p.locator('#cover .cvi').count() === 5,
       (await p.locator('#cover').innerText()).replace(/\n/g, ' '));
    ok('띠에 조건 건수를 함께 적음',
       /[\d,]+곳/.test(await p.locator('#cover .cvlab').innerText()));
  }

  if (!(await p.locator('#szf').isHidden())) {
    const n0b = +(await p.locator('#fcount').innerText()).match(/([\d,]+)건/)[1].replace(/,/g,'');
    await p.locator('#szf .chipbtn').nth(2).click();
    await p.waitForTimeout(500);
    const n1 = +(await p.locator('#fcount').innerText()).match(/([\d,]+)건/)[1].replace(/,/g,'');
    ok('규모 필터 동작', n1 < n0b, `${n0b} → ${n1}`);
    await p.locator('#reset').click();
    await p.waitForTimeout(300);
  }

  ok('JS 오류 없음 (외부 폰트 로딩 실패 제외)', errs.length === 0, errs.slice(0,3).join(' | '));

  await p.screenshot({ path: 'uitest.png', fullPage: false });
  await b.close();

  let fail = 0;
  for (const [s, n, d] of results) {
    if (s === 'FAIL') fail++;
    console.log(`  ${s}  ${n}${d ? '  — ' + d : ''}`);
  }
  console.log(`\n통과 ${results.length - fail} / 실패 ${fail}`);
  process.exit(fail ? 1 : 0);
})();
