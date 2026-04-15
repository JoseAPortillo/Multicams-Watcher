const state = {
  cameras: [],
  selectedCameraId: null,
  snapshotTimer: null,
};

function cameraSnapshotUrl(cameraId) {
  return `/api/cameras/${cameraId}/snapshot.jpg?t=${Date.now()}`;
}

async function fetchJson(url, options = {}) {
  const res = await fetch(url, options);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `HTTP ${res.status}`);
  }
  return res.json();
}

async function loadHealth() {
  const health = await fetchJson("/api/health");
  const el = document.getElementById("system-health");
  el.textContent = `${health.cameras_online}/${health.cameras_total} online`;
}

function renderCameraList() {
  const container = document.getElementById("camera-list");
  container.innerHTML = "";

  state.cameras.forEach((camera) => {
    const button = document.createElement("button");
    button.className = "camera-card";
    if (camera.id === state.selectedCameraId) {
      button.classList.add("active");
    }

    button.innerHTML = `
      <span class="camera-name">${camera.name}</span>
      <span class="camera-type">${camera.type}</span>
      <span class="camera-status ${camera.online ? "online" : "offline"}">
        ${camera.online ? "Online" : "Offline"}
      </span>
      <img src="${cameraSnapshotUrl(camera.id)}" alt="${camera.name}">
    `;

    button.addEventListener("click", () => selectCamera(camera.id));
    container.appendChild(button);
  });
}

function updateViewerMeta(camera) {
  const meta = document.getElementById("viewer-meta");
  meta.innerHTML = `
    <span class="pill ${camera.online ? "online" : "offline"}">${camera.online ? "Online" : "Offline"}</span>
    <span class="pill">${camera.type}</span>
    <span class="pill">${camera.alarm_enabled ? "Alarma activa" : "Alarma desactivada"}</span>
    <span class="pill">${camera.ptz_enabled ? "PTZ disponible" : "Sin PTZ"}</span>
  `;
}

function refreshViewerImage() {
  if (state.selectedCameraId === null) {
    return;
  }
  const img = document.getElementById("viewer-image");
  img.src = cameraSnapshotUrl(state.selectedCameraId);
}

function startSnapshotLoop() {
  if (state.snapshotTimer) {
    clearInterval(state.snapshotTimer);
  }
  refreshViewerImage();
  state.snapshotTimer = setInterval(refreshViewerImage, 2500);
}

async function selectCamera(cameraId) {
  state.selectedCameraId = cameraId;
  renderCameraList();

  const camera = state.cameras.find((item) => item.id === cameraId);
  const title = document.getElementById("viewer-title");
  const img = document.getElementById("viewer-image");
  const empty = document.getElementById("viewer-empty");
  const toggleAlarmBtn = document.getElementById("toggle-alarm-btn");
  const ptzControls = document.getElementById("ptz-controls");

  title.textContent = camera.name;
  img.hidden = false;
  empty.hidden = true;
  toggleAlarmBtn.disabled = false;
  toggleAlarmBtn.textContent = camera.alarm_enabled ? "Desactivar alarma" : "Activar alarma";
  ptzControls.classList.toggle("hidden", !camera.ptz_enabled);

  updateViewerMeta(camera);
  startSnapshotLoop();
}

async function loadCameras() {
  state.cameras = await fetchJson("/api/cameras");
  renderCameraList();

  if (state.selectedCameraId !== null) {
    const updated = state.cameras.find((cam) => cam.id === state.selectedCameraId);
    if (updated) {
      document.getElementById("toggle-alarm-btn").textContent = updated.alarm_enabled
        ? "Desactivar alarma"
        : "Activar alarma";
      document.getElementById("ptz-controls").classList.toggle("hidden", !updated.ptz_enabled);
      updateViewerMeta(updated);
    }
  }
}

async function toggleAlarm() {
  if (state.selectedCameraId === null) {
    return;
  }
  await fetchJson(`/api/cameras/${state.selectedCameraId}/alarm/toggle`, { method: "POST" });
  await loadCameras();
}

async function moveCamera(direction) {
  if (state.selectedCameraId === null) {
    return;
  }

  const moves = {
    up: { x: 0, y: 15 },
    down: { x: 0, y: -15 },
    left: { x: -15, y: 0 },
    right: { x: 15, y: 0 },
    home: { x: 0, y: 0 },
  };

  const move = moves[direction];
  if (!move) {
    return;
  }

  await fetchJson(
    `/api/cameras/${state.selectedCameraId}/move?x=${move.x}&y=${move.y}`,
    { method: "POST" },
  );
}

function setupEvents() {
  document.getElementById("refresh-btn").addEventListener("click", async () => {
    await loadHealth();
    await loadCameras();
  });

  document.getElementById("toggle-alarm-btn").addEventListener("click", toggleAlarm);

  document.querySelectorAll("#ptz-controls button").forEach((button) => {
    button.addEventListener("click", async () => {
      await moveCamera(button.dataset.move);
    });
  });
}

async function init() {
  setupEvents();
  await loadHealth();
  await loadCameras();

  if (state.cameras.length > 0) {
    await selectCamera(state.cameras[0].id);
  }

  setInterval(loadHealth, 10000);
  setInterval(loadCameras, 8000);
}

init().catch((error) => {
  document.getElementById("system-health").textContent = `Error: ${error.message}`;
});
