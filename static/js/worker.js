const statusTile = document.getElementById("statusTile");
const appPanel = document.getElementById("appPanel");
const loginPanel = document.getElementById("loginPanel");
const loginBtn = document.getElementById("loginBtn");
const loginMsg = document.getElementById("loginMsg");
const autoSimBtn = document.getElementById("autoSimBtn");
const autoSimStatus = document.getElementById("autoSimStatus");
let autoSimHandle = null;

async function api(path, body) {
  const res = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: body ? JSON.stringify(body) : undefined,
  });
  return res.json();
}

async function login() {
  const workerId = document.getElementById("workerId").value;
  const pin = document.getElementById("pin").value;
  const res = await api("/login/worker", { worker_id: workerId, pin });
  if (res.error) {
    loginMsg.textContent = res.error;
  } else {
    loginPanel.classList.add("hidden");
    appPanel.classList.remove("hidden");
    startPolling();
  }
}

loginBtn.onclick = login;

async function sendReading() {
  const payload = {
    heart_rate: Number(document.getElementById("hr").value),
    spo2: Number(document.getElementById("spo2").value),
    temperature: Number(document.getElementById("temp").value),
    gas: Number(document.getElementById("gas").value),
    fatigue: Number(document.getElementById("fatigue").value),
  };
  const res = await api("/worker/reading", payload);
  updateStatus(res);
}

document.getElementById("sendReading").onclick = sendReading;

document.querySelectorAll(".hazards button").forEach((btn) => {
  btn.onclick = async () => {
    const res = await api("/worker/hazard", { type: btn.dataset.hazard });
    if (res.play_sound) playBeep();
  };
});

document.getElementById("panicBtn").onclick = async () => {
  const res = await api("/worker/emergency", {});
  if (res.play_sound) playBeep();
};

function randomReading() {
  // basic realistic ranges; small chance of spike
  const rand = Math.random();
  let hr = 80 + (Math.random() * 20 - 10);
  let spo2 = 96 + (Math.random() * 2 - 1);
  let temp = 36.8 + (Math.random() * 0.4 - 0.2);
  let gas = 30 + (Math.random() * 20 - 10);
  if (rand > 0.9) {
    gas = 200 + Math.random() * 400;
    spo2 = 88 + Math.random() * 4;
    hr = 110 + Math.random() * 25;
  }
  const fatigue = Math.random() > 0.85 ? 2 : Math.random() > 0.6 ? 1 : 0;
  return {
    heart_rate: Math.round(hr),
    spo2: Math.round(spo2),
    temperature: parseFloat(temp.toFixed(1)),
    gas: Math.round(gas),
    fatigue,
  };
}

function applyReadingToInputs(r) {
  document.getElementById("hr").value = r.heart_rate;
  document.getElementById("spo2").value = r.spo2;
  document.getElementById("temp").value = r.temperature;
  document.getElementById("gas").value = r.gas;
  document.getElementById("fatigue").value = r.fatigue;
}

function toggleAutoSim() {
  if (autoSimHandle) {
    clearInterval(autoSimHandle);
    autoSimHandle = null;
    autoSimBtn.textContent = "Start Auto Simulate";
    autoSimStatus.textContent = "Stopped";
    return;
  }
  autoSimStatus.textContent = "Running...";
  autoSimBtn.textContent = "Stop Auto Simulate";
  // initial send
  (async () => {
    const r = randomReading();
    applyReadingToInputs(r);
    await api("/worker/reading", r);
  })();
  autoSimHandle = setInterval(async () => {
    const r = randomReading();
    applyReadingToInputs(r);
    await api("/worker/reading", r);
  }, 1000);
}

autoSimBtn.onclick = toggleAutoSim;

function renderMessages(msgs) {
  const list = document.getElementById("messageList");
  list.innerHTML = "";
  msgs.forEach((m) => {
    const div = document.createElement("div");
    div.className = "message";
    const cmd = m.command ? `<span class='danger' style="padding:4px 8px;border-radius:6px;display:inline-block;">${m.command}</span>` : "";
    div.innerHTML = `<strong>${m.from_role}</strong>: ${m.message} ${cmd}`;
    const ack = document.createElement("button");
    ack.textContent = "Acknowledge";
    ack.onclick = async () => {
      await api("/worker/ack_message", { id: m.id });
    };
    div.appendChild(ack);
    list.appendChild(div);
  });
}

function updateStatus(res) {
  if (!res || !res.status) return;
  statusTile.textContent = res.status;
  statusTile.className = "status " + res.status;
  if (res.play_sound) playBeep();
}

async function poll() {
  const res = await api("/worker/poll", {});
  updateStatus(res);
  renderMessages(res.messages || []);
  if (res.messages && res.messages.length) playBeep();
}

let pollHandle;
function startPolling() {
  poll();
  pollHandle = setInterval(poll, 1000);
}

