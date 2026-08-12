/* === Trading Education — Shared Site Chrome ===
   輕量、無依賴。只負責兩件全站一致的事：
   1) 標準免責聲明頁尾（教育用途、非投資建議、風險警語）
   2) 跨模組導航（← 上一課 / 回首頁 / 下一課 →），依學習路徑順序
   刻意不碰各頁既有的 inline tab / quiz 邏輯，避免衝突。 */
(function () {
  // 學習路徑順序（與首頁分區一致）：基建 → 心理/紀律/風控 → 核心資產 → 判讀/事件/回測 → 宏觀資金流 → 技術分析 → 加密選修
  var ORDER = [
    { file: 'tw_reality.html',            title: '台灣散戶實戰基建' },
    { file: 'cognitive_traps.html',       title: '交易認知陷阱' },
    { file: 'trading_psychology.html',    title: '交易心理學' },
    { file: 'risk_management.html',       title: '資金管理與風險控制' },
    { file: 'trading_strategy.html',      title: '波段與日內策略' },
    { file: 'us_equity_etf.html',         title: '美股與 ETF 核心持倉' },
    { file: 'precious_metals.html',       title: '貴金屬交易（黃金/白銀/礦股）' },
    { file: 'regime_identification.html', title: 'Regime 快速判定' },
    { file: 'event_trading_sop.html',     title: '事件交易 SOP' },
    { file: 'backtesting.html',           title: '回測與績效統計' },
    { file: 'macro_liquidity.html',       title: '宏觀流動性與經濟數據' },
    { file: 'forex_analysis.html',        title: '外匯與宏觀傳導' },
    { file: 'capital_flow_commodity.html',title: '跨資產資金流與商品供需' },
    { file: 'ai_semiconductor.html',      title: 'AI 半導體供應鏈分析' },
    { file: 'market_psychology.html',     title: '市場心理與主力動向' },
    { file: 'supertrend_guide.html',      title: 'SuperTrend 實戰手冊' },
    { file: 'candlestick_patterns.html',  title: '裸 K 線型態' },
    { file: 'options_volatility.html',    title: '期權與波動率（進階）' },
    { file: 'liquidity_grid.html',        title: '流動性結構與網格（加密選修）' },
    { file: 'futures_analytics.html',     title: '永續合約籌碼（加密選修）' },
    { file: 'onchain_crypto.html',        title: '鏈上數據分析（加密選修）' }
  ];

  function currentFile() {
    var p = location.pathname.split('/').pop();
    return (!p || p === 'index.html') ? 'trade_home.html' : p;
  }

  function buildNav() {
    var here = currentFile();
    if (here === 'trade_home.html') return null; // 首頁不需要
    var idx = -1;
    for (var i = 0; i < ORDER.length; i++) if (ORDER[i].file === here) { idx = i; break; }
    var wrap = document.createElement('nav');
    wrap.className = 'site-lesson-nav';
    wrap.setAttribute('data-site-nav', '1');
    var prev = idx > 0 ? ORDER[idx - 1] : null;
    var next = idx >= 0 && idx < ORDER.length - 1 ? ORDER[idx + 1] : null;
    var html = '';
    html += prev
      ? '<a class="ln-prev" href="' + prev.file + '">&larr; <span>' + prev.title + '</span></a>'
      : '<span class="ln-spacer"></span>';
    html += '<a class="ln-home" href="trade_home.html">回學習中心</a>';
    html += next
      ? '<a class="ln-next" href="' + next.file + '"><span>' + next.title + '</span> &rarr;</a>'
      : '<span class="ln-spacer"></span>';
    wrap.innerHTML = html;
    return wrap;
  }

  function buildDisclaimer() {
    var d = document.createElement('footer');
    d.className = 'site-disclaimer';
    d.setAttribute('data-site-disclaimer', '1');
    d.innerHTML =
      '<strong>免責聲明</strong>：本站所有內容僅供<strong>教育與研究用途，不構成任何投資建議、要約或招攬</strong>。' +
      '交易股票、ETF、貴金屬、期貨、期權與衍生品具有<strong>重大虧損風險，可能損失全部本金</strong>，槓桿會放大虧損。' +
      '過往績效與任何示意數字不代表未來結果。文中案例、比例與情境多為教學示意，並非實際交易紀錄或保證獲利。' +
      '請在自身財務狀況與風險承受度內、只用可承受損失的閒錢決策，必要時諮詢合格的專業顧問。' +
      '<span class="sd-brand">交易技術分析學習中心 · 學習不等於獲利，活得夠久才有複利</span>';
    return d;
  }

  function injectStyle() {
    if (document.getElementById('site-chrome-style')) return;
    var css = document.createElement('style');
    css.id = 'site-chrome-style';
    css.textContent =
      '.site-lesson-nav{display:flex;align-items:stretch;gap:10px;margin:32px 0 8px;flex-wrap:wrap;}' +
      '.site-lesson-nav a{flex:1;min-width:120px;display:flex;align-items:center;gap:6px;padding:12px 14px;' +
        'background:var(--bg2,#fff);border:1px solid var(--border,#cbd5e1);border-radius:10px;font-size:13px;' +
        'font-weight:600;color:var(--text2,#334155);text-decoration:none;transition:all .15s;}' +
      '.site-lesson-nav a:hover{border-color:var(--blue,#2563eb);color:var(--blue,#2563eb);text-decoration:none;}' +
      '.site-lesson-nav .ln-next{justify-content:flex-end;text-align:right;}' +
      '.site-lesson-nav .ln-home{flex:0 0 auto;justify-content:center;background:var(--bg3,#f1f5f9);}' +
      '.site-lesson-nav .ln-spacer{flex:1;min-width:120px;}' +
      '.site-disclaimer{margin:20px 0 8px;padding:14px 16px;border:1px solid var(--border,#cbd5e1);' +
        'border-radius:10px;background:var(--bg3,#f1f5f9);color:var(--text3,#64748b);font-size:11.5px;line-height:1.7;}' +
      '.site-disclaimer strong{color:var(--text2,#334155);}' +
      '.site-disclaimer .sd-brand{display:block;margin-top:8px;font-size:11px;color:var(--text3,#64748b);opacity:.8;}' +
      '@media (max-width:480px){.site-lesson-nav a,.site-lesson-nav .ln-spacer{min-width:100%;}}';
    document.head.appendChild(css);
  }

  function run() {
    injectStyle();
    var body = document.body;
    if (!body) return;
    var nav = buildNav();
    if (nav && !document.querySelector('[data-site-nav]')) body.appendChild(nav);
    if (!document.querySelector('[data-site-disclaimer]')) body.appendChild(buildDisclaimer());
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', run);
  } else {
    run();
  }
})();
