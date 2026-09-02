"use strict";

// ---- 共通ユーティリティ --------------------------------------------------
const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));
const esc = (s) =>
  String(s ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])
  );

async function api(path, opts) {
  const res = await fetch(path, opts);
  if (!res.ok) {
    let detail = res.statusText;
    try { detail = (await res.json()).detail || detail; } catch (_) {}
    throw new Error(detail);
  }
  return res.json();
}

// ---- モード切替 ----------------------------------------------------------
$$(".mode-btn").forEach((btn) =>
  btn.addEventListener("click", () => {
    $$(".mode-btn").forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    const mode = btn.dataset.mode;
    $("#mode-console").hidden = mode !== "console";
    $("#mode-search").hidden = mode !== "search";
  })
);

// ==========================================================================
// ケースコンソール(複数タブ)
// ==========================================================================
const tabs = new Map(); // key -> { title, data }
let activeTab = null;

$("#open-form").addEventListener("submit", (e) => {
  e.preventDefault();
  const v = $("#open-input").value.trim();
  if (v) openByInput(v);
  $("#open-input").value = "";
});

async function openByInput(value) {
  // ケースIDっぽい(ハイフン多め/CS始まり) → ケース、それ以外 → エラーコード
  const looksCase = /^cs[-_]/i.test(value) || value.includes("-2025-") || value.includes("-2024-");
  try {
    if (looksCase) {
      const data = await api(`/api/console/case/${encodeURIComponent(value)}`);
      addTab(data.case.case_id, data);
    } else {
      const res = await api(`/api/console/error/${encodeURIComponent(value)}`);
      if (res.count === 1) {
        addTab(res.consoles[0].case.case_id, res.consoles[0]);
      } else {
        // 複数該当 → すべて別タブで開く
        res.consoles.forEach((c) => addTab(c.case.case_id, c));
      }
    }
  } catch (err) {
    alert("開けませんでした: " + err.message);
  }
}

function addTab(key, data) {
  tabs.set(key, { title: `${data.case.customer_name} / ${key}`, data });
  activeTab = key;
  renderTabs();
  renderConsole(data);
}

function closeTab(key) {
  tabs.delete(key);
  if (activeTab === key) {
    activeTab = tabs.size ? Array.from(tabs.keys())[tabs.size - 1] : null;
  }
  renderTabs();
  if (activeTab) renderConsole(tabs.get(activeTab).data);
  else $("#tab-content").innerHTML = '<div class="empty-hint">ケースID または エラーコードを入力して開いてください。</div>';
}

function renderTabs() {
  const bar = $("#tab-bar");
  bar.innerHTML = "";
  tabs.forEach((t, key) => {
    const el = document.createElement("div");
    el.className = "tab" + (key === activeTab ? " active" : "");
    el.innerHTML = `<span>${esc(t.title)}</span><span class="close" title="閉じる">×</span>`;
    el.addEventListener("click", (e) => {
      if (e.target.classList.contains("close")) { closeTab(key); return; }
      activeTab = key; renderTabs(); renderConsole(t.data);
    });
    bar.appendChild(el);
  });
}

// ---- コンソール描画 ------------------------------------------------------
function renderConsole(d) {
  const c = d.case;
  const rm = d.remote_maintenance || {};
  const hot = d.hot_issue_site;
  const el = $("#tab-content");

  el.innerHTML = `
  <div class="console">
    <div class="case-head">
      <div>
        <div class="ttl">${esc(c.customer_name)} <span class="muted mono small">${esc(c.case_id)}</span></div>
        <div class="small muted">${esc(c.model)}（${esc(c.model_code)}） / 機器ID ${esc(c.customer_equipment_id)}</div>
      </div>
      <div class="badges" style="margin-left:auto">
        <span class="badge ${hot ? "hot" : "cool"}">${hot ? "🔥 Hot Issueサイト" : "Hot Issue対象外"}</span>
        <span class="badge sla">SLA ${esc(c.sla_level)}</span>
        <span class="badge status">${esc(c.status)}</span>
      </div>
      <div class="sym">現象: ${esc(c.symptom)} ${c.error_code ? `<span class="tag">${esc(c.error_code)}</span>` : ""}</div>
    </div>

    <!-- 左列 -->
    <div class="col-left">
      ${customerPanel(d)}
      ${installBasePanel(d)}
      ${workHistoryPanel(d)}
      ${nfitsPanel(d)}
    </div>

    <!-- 中央列 -->
    <div class="col-center">
      ${errorPanel(d)}
      ${partsPanel(d)}
      ${nextInspectionPanel(d)}
    </div>

    <!-- 右列 -->
    <div class="col-right">
      ${dispatchPanel(d)}
      ${remotePanel(d)}
      ${scriptsPanel(d)}
      ${relatedPanel(d)}
      ${actionsPanel(d)}
    </div>
  </div>`;

  wireConsole(d);
}

function customerPanel(d) {
  const cu = d.customer || {};
  const caution = (cu.caution_persons || []).map((x) => `<li>${esc(x)}</li>`).join("") || '<li class="muted small">なし</li>';
  const banned = (cu.banned_persons || []).map((x) => `<li class="danger">${esc(x)}</li>`).join("") || '<li class="muted small">なし</li>';
  const notes = (cu.notes || []).map((n) =>
    `<li>${esc(n.text)}<div class="muted small">— ${esc(n.author)} / ${esc(n.created_at)}</div></li>`
  ).join("") || '<li class="muted small">メモなし</li>';
  return `
  <div class="panel">
    <h3>得意先情報 / メモ</h3>
    <dl class="kv">
      <dt>入館方法</dt><dd>${esc(cu.access_method || "-")}</dd>
      <dt>部品受取</dt><dd>${esc(cu.part_receipt_location || "-")}</dd>
      <dt>約束事項</dt><dd>${esc(cu.promises || "-")}</dd>
      <dt>特異対応</dt><dd>${esc(cu.special_handling || "-")}</dd>
    </dl>
    <div class="small muted" style="margin-top:8px">要注意人物</div>
    <ul class="list">${caution}</ul>
    <div class="small muted">出入り禁止者</div>
    <ul class="list">${banned}</ul>
    <div class="small muted">共有メモ</div>
    <ul class="list" id="note-list">${notes}</ul>
    <form class="note-form" data-customer="${esc(cu.customer_id || "")}">
      <input type="text" placeholder="得意先メモを追記…" required />
      <button type="submit">追記</button>
    </form>
  </div>`;
}

function installBasePanel(d) {
  const rows = (d.install_base || []).map((u) =>
    `<li><span class="mono">${esc(u.unit)}</span> ${esc(u.model_code)} <span class="muted small mono">${esc(u.serial)}</span></li>`
  ).join("") || '<li class="muted small">情報なし</li>';
  return `<div class="panel"><h3>インストールベース</h3><ul class="list">${rows}</ul></div>`;
}

function workHistoryPanel(d) {
  const rows = (d.work_history || []).map((w) => {
    const parts = (w.parts_replaced || []).map((p) => `<span class="tag">${esc(p)}</span>`).join("");
    return `<li><b>${esc(w.date)}</b> ${esc(w.summary)}<div class="muted small">訪問: ${esc(w.engineer)} ${parts}</div></li>`;
  }).join("") || '<li class="muted small">履歴なし</li>';
  return `<div class="panel"><h3>過去の対応履歴</h3><ul class="list">${rows}</ul></div>`;
}

function nfitsPanel(d) {
  const rows = (d.nfits_history || []).map((n) =>
    `<li><b>${esc(n.date)}</b> ${esc(n.name)} <span class="mono">${esc(n.part_no)}</span> ×${esc(n.qty)}<div class="muted small">WO: ${esc(n.work_order)}</div></li>`
  ).join("") || '<li class="muted small">交換歴なし</li>';
  return `<div class="panel"><h3>NFITS 部品交換歴</h3><ul class="list">${rows}</ul></div>`;
}

function errorPanel(d) {
  const e = d.error;
  const body = e
    ? `<dl class="kv">
         <dt>コード</dt><dd class="mono">${esc(e.code)}</dd>
         <dt>メッセージ</dt><dd>${esc(e.message)}</dd>
         <dt>発生源</dt><dd>${esc(e.source)}</dd>
         <dt>原因</dt><dd>${esc(e.cause)}</dd>
         <dt>対処</dt><dd>${esc(e.action)}</dd>
         <dt>重要度</dt><dd>${esc(e.severity)}</dd>
       </dl>`
    : '<div class="muted small">エラーコード情報なし。下の欄で4桁コード検索できます。</div>';
  return `
  <div class="panel">
    <h3>エラーコード情報（TERRA）</h3>
    <div class="code-lookup">
      <input id="code-input" type="text" placeholder="4桁コードを入力 例: 2104" />
      <button id="code-btn" type="button">検索</button>
    </div>
    <div id="code-result">${body}</div>
  </div>`;
}

function partsPanel(d) {
  const stats = d.replacement_stats || [];
  const rows = stats.map((s) => {
    const pct = Math.round((s.replace_rate || 0) * 100);
    const st = s.stock;
    let stockHtml = '<span class="muted">在庫情報なし</span>';
    if (st) {
      const cls = st.on_hand === 0 ? "stock-none" : st.on_hand <= 1 ? "stock-low" : "stock-ok";
      stockHtml = `<span class="${cls}">在庫 ${st.on_hand}（${esc(st.status)}／${esc(st.location)}${st.lead_time_days ? "／L/T " + st.lead_time_days + "日" : ""}）</span>`;
    }
    return `<div class="part-row">
      <div class="top"><span><span class="mono">${esc(s.part_no)}</span> ${esc(s.name)}<span class="tag" style="margin-left:6px">${esc(s.category)}</span></span><b>${pct}%</b></div>
      <div class="bar"><span style="width:${pct}%"></span></div>
      <div class="small">${stockHtml} <span class="muted">過去${esc(s.count)}件</span></div>
    </div>`;
  }).join("") || '<div class="muted small">エラーコードに紐づく交換部品データなし</div>';
  return `<div class="panel"><h3>エラーコード別 過去交換部品（判定率）+ 在庫</h3>${rows}</div>`;
}

function nextInspectionPanel(d) {
  const ni = d.next_inspection;
  const body = ni
    ? `<dl class="kv"><dt>予定日</dt><dd><b>${esc(ni.date)}</b></dd><dt>内容</dt><dd>${esc(ni.type)}</dd></dl>`
    : '<div class="muted small">予定なし</div>';
  return `<div class="panel"><h3>次回点検予定</h3>${body}</div>`;
}

function dispatchPanel(d) {
  const dp = d.dispatch || {};
  return `<div class="panel"><h3>ディスパッチ先</h3>
    <dl class="kv">
      <dt>エリア</dt><dd>${esc(dp.area || "-")}</dd>
      <dt>FS担当</dt><dd>${esc(dp.fs_contact || "-")}</dd>
      <dt>夜間当番</dt><dd>${esc(dp.night_contact || "-")}</dd>
      <dt>到着見込</dt><dd>${esc((dp.estimated_arrival || "-").replace("T", " "))}</dd>
    </dl></div>`;
}

function remotePanel(d) {
  const rm = d.remote_maintenance || {};
  const avail = rm.available;
  const badge = avail
    ? `<span class="badge ok">リモメン可（${esc(rm.connection_status)}）</span>`
    : `<span class="badge warn">${esc(rm.connection_status || "リモメン不可")}</span>`;
  return `<div class="panel"><h3>リモメン / 直前アラート</h3>
    <div class="badges">${badge}</div>
    <dl class="kv" style="margin-top:8px">
      <dt>接続確認</dt><dd>${esc((rm.connection_checked_at || "-").replace("T", " "))}</dd>
      <dt>直前アラート</dt><dd>${esc(rm.last_alert || "なし")}</dd>
    </dl></div>`;
}

function scriptsPanel(d) {
  const rows = (d.scripts || []).map((s) =>
    `<li><b>${esc(s.doc_type)}</b> ${esc(s.title)}<div class="muted small mono">${esc(s.path)}</div></li>`
  ).join("") || '<li class="muted small">なし</li>';
  return `<div class="panel"><h3>SLA判定 / 初動スクリプト</h3><ul class="list">${rows}</ul></div>`;
}

function relatedPanel(d) {
  const bbs = (d.related_bulletin || []).map((b) =>
    `<li><a href="${esc(b.url)}" target="_blank" rel="noopener">${esc(b.title)}</a><div class="muted small">${esc(b.category || "")} ${esc((b.posted_at || "").slice(0, 10))}</div></li>`
  ).join("") || '<li class="muted small">なし</li>';
  const cases = (d.related_cases || []).map((r) =>
    `<li><b>${esc(r.fault_name)}</b><div class="muted small">${esc(r.occurred_on)} ${esc(r.resolution)}</div></li>`
  ).join("") || '<li class="muted small">なし</li>';
  return `<div class="panel"><h3>関連掲示板 / 関連事例</h3>
    <div class="small muted">掲示板</div><ul class="list">${bbs}</ul>
    <div class="small muted">過去事例</div><ul class="list">${cases}</ul></div>`;
}

function actionsPanel(d) {
  const id = esc(d.case.case_id);
  return `<div class="panel"><h3>アクション（受付→CEディスパッチ / メール）</h3>
    <div class="actions">
      <button data-dispatch="${id}">▶ 現地へ作業指示（CEディスパッチ）</button>
      <button data-mail="in_progress" data-case="${id}">✉ 対応中メール（FS掲示板）</button>
      <button data-mail="part_order" data-case="${id}">✉ 部品出荷依頼メール</button>
      <button data-mail="part_proxy" data-case="${id}">✉ 部品代理登録メール</button>
      <button data-mail="ctfs_board" data-case="${id}">📋 CT-FS掲示板 反映内容</button>
    </div></div>`;
}

// ---- コンソール内イベント配線 -------------------------------------------
function wireConsole(d) {
  // 4桁コード検索
  const codeBtn = $("#code-btn");
  if (codeBtn) {
    const run = async () => {
      const code = $("#code-input").value.trim();
      if (!code) return;
      try {
        const res = await api(`/api/console/error/${encodeURIComponent(code)}`);
        // TERRA 情報を直接引くため error API ではなく検索結果の error を使う
      } catch (_) {}
      // TERRA 単独引きは search 経由（manuals）で取得
      try {
        const s = await api(`/api/search?q=${encodeURIComponent(code)}&sources=manuals`);
        const terra = s.results.find((r) => r.result_id === `TERRA-${code}`) ||
          s.results.find((r) => (r.metadata && r.metadata.code === code));
        const box = $("#code-result");
        if (terra) {
          box.innerHTML = `<dl class="kv">
            <dt>コード</dt><dd class="mono">${esc(terra.metadata.code || code)}</dd>
            <dt>内容</dt><dd>${esc(terra.title.replace(/^\[TERRA\]\s*/, ""))}</dd>
            <dt>発生源</dt><dd>${esc(terra.metadata.source || "-")}</dd>
            <dt>対処</dt><dd>${esc(terra.snippet)}</dd>
          </dl>`;
        } else {
          box.innerHTML = '<div class="muted small">該当するTERRA情報が見つかりません。</div>';
        }
      } catch (err) {
        $("#code-result").innerHTML = `<div class="danger small">検索エラー: ${esc(err.message)}</div>`;
      }
    };
    codeBtn.addEventListener("click", run);
    $("#code-input").addEventListener("keydown", (e) => { if (e.key === "Enter") run(); });
  }

  // 得意先メモ追記
  const nf = $(".note-form");
  if (nf) {
    nf.addEventListener("submit", async (e) => {
      e.preventDefault();
      const cid = nf.dataset.customer;
      const input = nf.querySelector("input");
      const text = input.value.trim();
      if (!cid || !text) return;
      try {
        await api(`/api/customers/${encodeURIComponent(cid)}/notes`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ text, author: "受付" }),
        });
        // 再取得して反映
        const fresh = await api(`/api/console/case/${encodeURIComponent(d.case.case_id)}`);
        tabs.get(d.case.case_id).data = fresh;
        renderConsole(fresh);
      } catch (err) {
        alert("メモ追記に失敗: " + err.message);
      }
    });
  }

  // メール生成
  $$('[data-mail]').forEach((btn) =>
    btn.addEventListener("click", () => openMail(btn.dataset.case, btn.dataset.mail))
  );
  $$('[data-dispatch]').forEach((btn) =>
    btn.addEventListener("click", () => openDispatch(btn.dataset.dispatch))
  );
}

// ---- メールモーダル ------------------------------------------------------
async function openMail(caseId, template) {
  try {
    const r = await api(`/api/console/case/${encodeURIComponent(caseId)}/mail`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ template, parts: [] }),
    });
    $("#mail-title").textContent = r.label;
    $("#mail-subject").value = r.subject;
    $("#mail-body").value = r.body;
    $("#mail-note").textContent = "";
    $("#mail-send").hidden = true;
    $("#mail-to-field").hidden = true;
    dispatchCaseId = null;
    $("#mail-modal").hidden = false;
  } catch (err) {
    alert("メール生成に失敗: " + err.message);
  }
}
// 受付 → CE ディスパッチ（作業指示メール生成 + 送信）
let dispatchCaseId = null;
async function openDispatch(caseId) {
  try {
    const r = await api(`/api/console/case/${encodeURIComponent(caseId)}/dispatch`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ send: false }),
    });
    dispatchCaseId = caseId;
    $("#mail-title").textContent = "作業指示（CEディスパッチ）";
    $("#mail-to-field").hidden = false;
    $("#mail-to").value = r.to || "";
    $("#mail-subject").value = r.subject;
    $("#mail-body").value = r.body;
    $("#mail-send").hidden = false;
    $("#mail-note").textContent = r.smtp_enabled
      ? (r.to ? "" : "宛先(CEメール)が未解決です。上の欄に入力してください。")
      : "※SMTP未設定のため送信は無効（下書き/コピーのみ）。";
    $("#mail-modal").hidden = false;
  } catch (err) {
    alert("ディスパッチ生成に失敗: " + err.message);
  }
}
$("#mail-send").addEventListener("click", async () => {
  if (!dispatchCaseId) return;
  try {
    const r = await api(`/api/console/case/${encodeURIComponent(dispatchCaseId)}/dispatch`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        to: $("#mail-to").value.trim(),
        subject: $("#mail-subject").value,
        body: $("#mail-body").value,
        send: true,
      }),
    });
    $("#mail-note").textContent = (r.sent ? "✔ " : "") + r.reason + (r.to ? `（宛先: ${r.to}）` : "");
  } catch (err) {
    $("#mail-note").textContent = "送信エラー: " + err.message;
  }
});
function closeMailModal() {
  $("#mail-modal").hidden = true;
  $("#mail-send").hidden = true;
  $("#mail-to-field").hidden = true;
  dispatchCaseId = null;
}
$("#mail-close").addEventListener("click", closeMailModal);
$("#mail-modal").addEventListener("click", (e) => { if (e.target.id === "mail-modal") closeMailModal(); });
$("#mail-copy").addEventListener("click", async () => {
  const text = `件名: ${$("#mail-subject").value}\n\n${$("#mail-body").value}`;
  try {
    await navigator.clipboard.writeText(text);
    $("#mail-note").textContent = "コピーしました";
  } catch (_) {
    $("#mail-note").textContent = "コピーできない環境です（手動で選択してください）";
  }
});

// ---- クイックオープン ----------------------------------------------------
async function loadQuickOpen() {
  // ケース一覧を検索APIで拾えないので、代表ケースをチップ表示（デモ用固定）
  const samples = [
    ["CS-2025-100427", "○○中央病院 / CT 2104"],
    ["CS-2025-100311", "△△総合 / MRI ヘリウム"],
    ["CS-2025-100508", "□□クリニック / 超音波"],
  ];
  const box = $("#quick-open");
  box.innerHTML = '<span class="lbl">クイック:</span>';
  samples.forEach(([id, label]) => {
    const chip = document.createElement("span");
    chip.className = "chip";
    chip.textContent = label;
    chip.addEventListener("click", () => openByInput(id));
    box.appendChild(chip);
  });
}

// ==========================================================================
// 横断検索
// ==========================================================================
let sourceList = [];

async function loadSources() {
  sourceList = await api("/api/sources");
  const box = $("#source-filters");
  box.innerHTML = "";
  sourceList.forEach((s) => {
    const lbl = document.createElement("label");
    lbl.innerHTML = `<input type="checkbox" value="${esc(s.key)}" checked /> ${esc(s.label)}`;
    box.appendChild(lbl);
  });
}

$("#search-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const q = $("#search-input").value.trim();
  if (!q) return;
  const keys = $$('#source-filters input:checked').map((i) => i.value);
  $("#search-results").innerHTML = '<div class="muted">検索中…</div>';
  try {
    const res = await api(`/api/search?q=${encodeURIComponent(q)}&sources=${keys.join(",")}`);
    renderSearch(res);
  } catch (err) {
    $("#search-results").innerHTML = `<div class="danger">検索エラー: ${esc(err.message)}</div>`;
  }
});

function renderSearch(res) {
  const counts = Object.entries(res.counts_by_source)
    .map(([k, v]) => `${labelOf(k)}:${v}`).join(" / ");
  $("#search-meta").textContent = `${res.total}件（${res.took_ms}ms）  ${counts}`;
  if (!res.results.length) {
    $("#search-results").innerHTML = '<div class="muted">該当なし。キーワードを変えてお試しください。</div>';
    return;
  }
  $("#search-results").innerHTML = res.results.map((r) => {
    const title = r.url
      ? `<a class="rtitle" href="${esc(r.url)}" target="_blank" rel="noopener">${esc(r.title)}</a>`
      : `<span class="rtitle">${esc(r.title)}</span>`;
    const meta = [r.metadata.record_type, r.metadata.model, r.metadata.error_code || r.metadata.code, r.timestamp]
      .filter(Boolean).map(esc).join(" ・ ");
    const openBtn = r.source_key === "repair_history" && r.metadata.record_type === "受付ケース"
      ? `<button class="chip" data-open="${esc(r.result_id)}">コンソールで開く</button>` : "";
    return `<div class="result">
      <div class="rhead">${title}<span class="src ${esc(r.source_key)}">${esc(r.source_label)}</span></div>
      <div class="snippet">${esc(r.snippet)}</div>
      <div class="meta">${meta} ${openBtn}</div>
    </div>`;
  }).join("");

  $$('[data-open]').forEach((b) => b.addEventListener("click", () => {
    $$(".mode-btn").forEach((x) => x.classList.remove("active"));
    $('.mode-btn[data-mode="console"]').classList.add("active");
    $("#mode-console").hidden = false; $("#mode-search").hidden = true;
    openByInput(b.dataset.open);
  }));
}

const labelOf = (key) => (sourceList.find((s) => s.key === key) || {}).label || key;

// ---- 初期化 --------------------------------------------------------------
loadSources().catch(() => {});
loadQuickOpen();
