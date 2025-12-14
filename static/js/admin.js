let selectedWorker = null;
let workersCache = [];

async function api(path, body) {
  const opts = { method: body ? "POST" : "GET", credentials: "include" };
  if (body) {
    opts.headers = { "Content-Type": "application/json" };
    opts.body = JSON.stringify(body);
  }
  const res = await fetch(path, opts);
  return res.json();
}

async function adminLogin() {
  const username = document.getElementById("adminUser").value;
  const password = document.getElementById("adminPass").value;
  const res = await api("/login/admin", { username, password });
  const msg = document.getElementById("adminLoginMsg");
  if (res.error) {
    msg.textContent = res.error;
  } else {
    document.getElementById("adminLogin").classList.add("hidden");
    document.getElementById("adminApp").classList.remove("hidden");
    startAdminPoll();
  }
}

document.getElementById("adminLoginBtn").onclick = adminLogin;

async function loadWorkers() {
  const workers = await api("/admin/workers");
  workersCache = workers;
  const cards = document.getElementById("workerCards");
  cards.innerHTML = "";
  workers.forEach((w) => {
    const div = document.createElement("div");
    div.className = "worker-card";
    div.innerHTML = `<strong>${w.worker_id}</strong><br>${w.name}<br>Status: ${w.status}<br>Zone: ${w.zone}<br>HR:${w.heart_rate ?? '-'} SpO2:${w.spo2 ?? '-'} Gas:${w.gas ?? '-'}`;
    div.onclick = () => {
      selectedWorker = w.worker_id;
      highlightSelected();
      loadHistory();
      loadLatest();
    };
    if (w.worker_id === selectedWorker) div.classList.add("selected");
    cards.appendChild(div);
  });
  // auto-select first worker if none selected
  if (!selectedWorker && workers.length > 0) {
    selectedWorker = workers[0].worker_id;
    highlightSelected();
    loadHistory();
    loadLatest();
  }
  return workers;
}

function highlightSelected() {
  document.querySelectorAll(".worker-card").forEach((el) => {
    const id = el.querySelector("strong")?.innerText;
    if (id === selectedWorker) el.classList.add("selected"); else el.classList.remove("selected");
  });
}

let historyChart;
function renderHistory(data) {
  const ctx = document.getElementById("historyChart");
  const labels = data.map((d) => d.timestamp);
  const hr = data.map((d) => d.heart_rate);
  const spo2 = data.map((d) => d.spo2);
  if (historyChart) historyChart.destroy();
  historyChart = new Chart(ctx, {
    type: "line",
    data: { labels, datasets: [{ label: "HR", data: hr, borderColor: "#f87171" }, { label: "SpO2", data: spo2, borderColor: "#38bdf8" }] },
    options: { responsive: true, scales: { x: { display: false } } },
  });
}

async function loadHistory() {
  if (!selectedWorker) return;
  const data = await api(`/admin/worker/${selectedWorker}/history`);
  renderHistory(data);
  const detail = document.getElementById("detail");
  const last = data[data.length - 1];
  if (last) {
    detail.innerHTML = `
      <div>Status: ${last.status}</div>
      <div>Risk: ${last.risk_score}</div>
      <div>HR ${last.heart_rate} | SpO2 ${last.spo2} | Temp ${last.temperature} | Gas ${last.gas}</div>`;
    const live = document.getElementById("liveReadings");
    live.innerHTML = `<strong>Latest Reading:</strong> ${new Date(last.timestamp).toLocaleTimeString()} — HR ${last.heart_rate}, SpO2 ${last.spo2}, Temp ${last.temperature}, Gas ${last.gas}, Fatigue ${last.fatigue}`;
  }
}

async function loadLatest() {
  if (!selectedWorker) return;
  const latest = await api(`/admin/latest/${selectedWorker}`);
  if (latest.error) return;
  const live = document.getElementById("liveReadings");
  live.innerHTML = `<strong>Latest Reading:</strong> ${new Date(latest.timestamp).toLocaleTimeString()} — HR ${latest.heart_rate}, SpO2 ${latest.spo2}, Temp ${latest.temperature}, Gas ${latest.gas}, Fatigue ${latest.fatigue} | Status ${latest.status} (Risk ${latest.risk_score})`;
  // Suggest a decision message for admin approval
  const decisionBox = document.getElementById("decisionBox");
  if (decisionBox) {
    let directive = "Continue work. Stay alert.";
    if (latest.status === "EMERGENCY" || latest.risk_score >= 90) {
      directive = "STOP WORK. Move to safe zone. Await instructions.";
    } else if (latest.status === "WARNING" || latest.risk_score >= 70) {
      directive = "Reduce activity. Hydrate. Report if symptoms persist.";
    }
    decisionBox.value = `Status ${latest.status}, risk ${latest.risk_score}. HR ${latest.heart_rate}, SpO2 ${latest.spo2}, Temp ${latest.temperature}, Gas ${latest.gas}, Fatigue ${latest.fatigue}. Directive: ${directive}`;
  }
}

async function loadAlerts() {
  const alerts = await api("/admin/alerts");
  const list = document.getElementById("alertsList");
  list.innerHTML = "";
  alerts.forEach((a) => {
    const div = document.createElement("div");
    div.className = "alert-card";
    div.innerHTML = `<strong>${a.priority}</strong> ${a.worker_id} ${a.reason} <br>${a.alert_type} | ${a.timestamp}`;
    const ack = document.createElement("button");
    ack.textContent = "Acknowledge";
    ack.onclick = async () => {
      await api("/admin/ack_alert", { alert_id: a.id });
    };
    const res = document.createElement("button");
    res.textContent = "Resolve";
    res.onclick = async () => {
      await api("/admin/resolve_alert", { alert_id: a.id });
    };
    div.appendChild(ack);
    div.appendChild(res);
    if (a.escalation_flag) {
      const esc = document.createElement("div");
      esc.textContent = "ESCALATED";
      esc.style.color = "yellow";
      div.appendChild(esc);
    }
    list.appendChild(div);
  });
}

document.getElementById("sendMsgBtn").onclick = async () => {
  const worker_id = document.getElementById("msgWorker").value || selectedWorker;
  const message = document.getElementById("msgText").value;
  const action = document.getElementById("msgAction").value;
  if (!worker_id) { alert("Select or enter a worker ID"); return; }
  const res = await api("/admin/message", { worker_id, message, action });
  if (res.error) { alert(res.error); return; }
  document.getElementById("msgText").value = "";
  playBeep();
};

// Send decision after admin review/approval
document.getElementById("sendDecisionBtn").onclick = async () => {
  const worker_id = selectedWorker || document.getElementById("msgWorker").value;
  if (!worker_id) { alert("Select a worker first"); return; }
  const message = document.getElementById("decisionBox").value || "Decision approved.";
  // if directive contains STOP WORK, send as STOP WORK action to create admin alert/command
  const action = message.toUpperCase().includes("STOP WORK") ? "STOP WORK" : "";
  const res = await api("/admin/message", { worker_id, message, action });
  if (res.error) { alert(res.error); return; }
  playBeep();
};

async function adminPoll() {
  await loadWorkers();
  if (selectedWorker) {
    await loadHistory();
    await loadLatest();
  }
  await loadAlerts();
}

function startAdminPoll() {
  adminPoll();
  setInterval(adminPoll, 1000);
}

