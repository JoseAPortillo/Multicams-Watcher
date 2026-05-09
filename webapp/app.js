const state = {
  cameras: [],
  selectedCameraId: null,
  snapshotTimer: null,
  configuredCameras: [],
  scanResults: [],
  selectedForAdd: new Set(),
  selectedForRemove: new Set(),
  renamedCameras: new Map(),
  editingCameraField: null,
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
    const card = document.createElement("article");
    card.className = "camera-card";
    card.tabIndex = 0;
    if (camera.id === state.selectedCameraId) {
      card.classList.add("active");
    }

    card.innerHTML = `
      <label class="camera-field">
        <span>Nombre</span>
        <input class="camera-name-input" type="text" value="${escapeHtml(camera.name)}" data-field="name">
      </label>
      <div class="camera-meta-row">
        <span class="camera-type">${camera.type}</span>
        <span class="camera-status ${camera.online ? "online" : "offline"}">
          ${camera.online ? "Online" : "Offline"}
        </span>
      </div>
      <label class="camera-field camera-cooldown-field">
        <span>Cooldown alerta</span>
        <input class="camera-cooldown-input" type="number" min="0" max="3600" step="1" value="${camera.alert_cooldown_seconds ?? 10}" data-field="alert_cooldown_seconds">
        <span class="camera-unit">s</span>
      </label>
      <img src="${cameraSnapshotUrl(camera.id)}" alt="${camera.name}">
    `;

    card.addEventListener("click", () => selectCamera(camera.id));
    card.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        selectCamera(camera.id);
      }
    });

    card.querySelectorAll("input").forEach((input) => {
      const field = input.dataset.field;
      input.addEventListener("click", (event) => event.stopPropagation());
      input.addEventListener("keydown", (event) => {
        event.stopPropagation();
        if (event.key === "Enter") {
          input.blur();
        }
      });
      input.addEventListener("focus", () => {
        state.editingCameraField = `${camera.id}:${field}`;
      });
      input.addEventListener("blur", async () => {
        state.editingCameraField = null;
        await saveCameraField(camera, field, input.value);
      });
    });

    container.appendChild(card);
  });
}

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

async function saveCameraField(camera, field, rawValue) {
  const payload = {};

  if (field === "name") {
    const name = rawValue.trim();
    if (!name || name === camera.name) {
      return;
    }
    payload.name = name;
  }

  if (field === "alert_cooldown_seconds") {
    const alertCooldownSeconds = Number(rawValue);
    if (!Number.isFinite(alertCooldownSeconds) || alertCooldownSeconds < 0 || alertCooldownSeconds > 3600) {
      alert("El cooldown de alerta debe estar entre 0 y 3600 segundos.");
      renderCameraList();
      return;
    }
    if (Number(camera.alert_cooldown_seconds) === alertCooldownSeconds) {
      return;
    }
    payload.alert_cooldown_seconds = alertCooldownSeconds;
  }

  try {
    const updated = await fetchJson(`/api/camera-config/${camera.id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    const index = state.cameras.findIndex((item) => item.id === camera.id);
    if (index !== -1) {
      state.cameras[index] = { ...state.cameras[index], ...updated };
      Object.assign(camera, updated);
    }

    if (state.selectedCameraId === camera.id && index !== -1) {
      document.getElementById("viewer-title").textContent = state.cameras[index].name;
      updateViewerMeta(state.cameras[index]);
    }

    renderCameraList();
  } catch (error) {
    alert(`Error al guardar la camara: ${error.message}`);
    await loadCameras();
  }
}

function updateViewerMeta(camera) {
  const meta = document.getElementById("viewer-meta");
  meta.innerHTML = `
    <span class="pill ${camera.online ? "online" : "offline"}">${camera.online ? "Online" : "Offline"}</span>
    <span class="pill">${camera.type}</span>
    <span class="pill">${camera.alarm_enabled ? "Alarma activa" : "Alarma desactivada"}</span>
    <span class="pill">${camera.ptz_enabled ? "PTZ disponible" : "Sin PTZ"}</span>
    <span class="pill ${camera.light_on ? "light-on" : ""}">${camera.light_enabled ? (camera.light_on ? "Luz encendida" : "Luz apagada") : "Sin luz remota"}</span>
    <span class="pill">Cooldown alerta ${camera.alert_cooldown_seconds ?? 10}s</span>
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
  const toggleLightBtn = document.getElementById("toggle-light-btn");
  const ptzControls = document.getElementById("ptz-controls");

  title.textContent = camera.name;
  img.hidden = false;
  empty.hidden = true;
  toggleAlarmBtn.disabled = false;
  toggleAlarmBtn.textContent = camera.alarm_enabled ? "Desactivar alarma" : "Activar alarma";
  toggleLightBtn.disabled = !camera.light_enabled;
  toggleLightBtn.classList.toggle("hidden", !camera.light_enabled);
  toggleLightBtn.classList.toggle("active-light", camera.light_on);
  toggleLightBtn.textContent = camera.light_on ? "Apagar luz" : "Encender luz";
  ptzControls.classList.toggle("hidden", !camera.ptz_enabled);

  updateViewerMeta(camera);
  startSnapshotLoop();
}

async function loadCameras() {
  if (state.editingCameraField) {
    return;
  }

  state.cameras = await fetchJson("/api/cameras");
  renderCameraList();

  if (state.selectedCameraId !== null) {
    const updated = state.cameras.find((cam) => cam.id === state.selectedCameraId);
    if (updated) {
      document.getElementById("toggle-alarm-btn").textContent = updated.alarm_enabled
        ? "Desactivar alarma"
        : "Activar alarma";
      document.getElementById("toggle-light-btn").disabled = !updated.light_enabled;
      document.getElementById("toggle-light-btn").classList.toggle("hidden", !updated.light_enabled);
      document.getElementById("toggle-light-btn").classList.toggle("active-light", updated.light_on);
      document.getElementById("toggle-light-btn").textContent = updated.light_on
        ? "Apagar luz"
        : "Encender luz";
      document.getElementById("ptz-controls").classList.toggle("hidden", !updated.ptz_enabled);
      updateViewerMeta(updated);
    } else {
      state.selectedCameraId = state.cameras.length > 0 ? state.cameras[0].id : null;
      if (state.selectedCameraId !== null) {
        await selectCamera(state.selectedCameraId);
      }
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

async function toggleLight() {
  if (state.selectedCameraId === null) {
    return;
  }
  await fetchJson(`/api/cameras/${state.selectedCameraId}/light/toggle`, { method: "POST" });
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

async function showModal() {
  const modal = document.getElementById("add-camera-modal");
  modal.classList.remove("hidden");
  modal.style.display = "flex";
  resetModal();
  try {
    await loadConfiguredCameras();
  } catch (error) {
    document.getElementById("scan-warnings").classList.remove("hidden");
    document.getElementById("scan-warnings").innerHTML = `<p>Error al cargar la configuracion: ${error.message}</p>`;
  }
}

function hideModal() {
  const modal = document.getElementById("add-camera-modal");
  modal.classList.add("hidden");
  modal.style.display = "none";
  resetModal();
}

function resetModal() {
  state.configuredCameras = [];
  state.scanResults = [];
  state.selectedForAdd.clear();
  state.selectedForRemove.clear();
  state.renamedCameras.clear();
  document.getElementById("scan-progress").classList.add("hidden");
  document.getElementById("configured-camera-list").innerHTML = "";
  document.getElementById("scan-results").innerHTML = "";
  document.getElementById("scan-warnings").classList.add("hidden");
  document.getElementById("scan-warnings").innerHTML = "";
  document.getElementById("scan-btn").classList.remove("hidden");
  document.getElementById("accept-btn").classList.remove("hidden");
}

async function loadConfiguredCameras() {
  const result = await fetchJson("/api/camera-config");
  state.configuredCameras = result.cameras;
  renderConfiguredCameras();
}

function renderConfiguredCameras() {
  const container = document.getElementById("configured-camera-list");
  container.innerHTML = "";

  if (state.configuredCameras.length === 0) {
    container.innerHTML = "<p class=\"empty-note\">No hay camaras configuradas.</p>";
    return;
  }

  state.configuredCameras.forEach((camera) => {
    const row = document.createElement("div");
    row.className = "configured-camera-item";
    if (state.selectedForRemove.has(camera.id)) {
      row.classList.add("pending-remove");
    }

    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.className = "round-checkbox";
    checkbox.id = `configured-cam-${camera.id}`;
    checkbox.checked = state.selectedForRemove.has(camera.id);
    checkbox.title = "Marcar para quitar";
    checkbox.addEventListener("change", () => {
      if (checkbox.checked) {
        state.selectedForRemove.add(camera.id);
      } else {
        state.selectedForRemove.delete(camera.id);
      }
      renderConfiguredCameras();
    });

    const info = document.createElement("div");
    info.className = "configured-camera-info";

    const nameButton = document.createElement("button");
    nameButton.type = "button";
    nameButton.className = "configured-camera-name";
    nameButton.textContent = state.renamedCameras.get(camera.id) || camera.name;
    nameButton.addEventListener("click", () => showRenameInput(camera, info));

    const meta = document.createElement("span");
    meta.className = "configured-camera-meta";
    meta.textContent = `${camera.type}${camera.ip ? ` - ${camera.ip}` : ""}`;

    info.appendChild(nameButton);
    info.appendChild(meta);
    row.appendChild(checkbox);
    row.appendChild(info);
    container.appendChild(row);
  });
}

function showRenameInput(camera, container) {
  const input = document.createElement("input");
  input.type = "text";
  input.className = "rename-input";
  input.value = state.renamedCameras.get(camera.id) || camera.name;
  let cancelled = false;

  const commit = () => {
    if (cancelled) {
      return;
    }
    const nextName = input.value.trim();
    if (nextName && nextName !== camera.name) {
      state.renamedCameras.set(camera.id, nextName);
    } else {
      state.renamedCameras.delete(camera.id);
    }
    renderConfiguredCameras();
  };

  input.addEventListener("blur", commit);
  input.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      input.blur();
    }
    if (event.key === "Escape") {
      cancelled = true;
      state.renamedCameras.delete(camera.id);
      renderConfiguredCameras();
    }
  });

  container.replaceChildren(input);
  input.focus();
  input.select();
}

function updateProgress(progress) {
  const fill = document.querySelector(".progress-fill");
  const span = document.querySelector("#scan-progress span");
  fill.style.width = `${progress * 100}%`;
  span.textContent = `Escaneando red... ${Math.round(progress * 100)}%`;
}

async function scanNetwork() {
  document.getElementById("scan-progress").classList.remove("hidden");
  document.getElementById("scan-btn").classList.add("hidden");
  document.getElementById("scan-warnings").classList.add("hidden");
  document.getElementById("scan-results").innerHTML = "";

  try {
    const result = await fetchJson("/api/scan-cameras");
    state.scanResults = result.cameras;
    renderScanResults();
  } catch (error) {
    document.getElementById("scan-warnings").classList.remove("hidden");
    document.getElementById("scan-warnings").innerHTML = `<p>Error durante el escaneo: ${error.message}</p>`;
    document.getElementById("scan-btn").classList.remove("hidden");
  } finally {
    document.getElementById("scan-progress").classList.add("hidden");
  }
}

function renderScanResults() {
  const container = document.getElementById("scan-results");
  container.innerHTML = "";

  if (state.scanResults.length === 0) {
    container.innerHTML = "<p class=\"empty-note\">No se detectaron camaras nuevas.</p>";
    return;
  }

  state.scanResults.forEach((cam, index) => {
    const div = document.createElement("div");
    div.className = "scan-result-item";

    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.className = "round-checkbox";
    checkbox.id = `cam-${index}`;
    checkbox.checked = state.selectedForAdd.has(index);
    checkbox.addEventListener("change", () => {
      if (checkbox.checked) {
        state.selectedForAdd.add(index);
      } else {
        state.selectedForAdd.delete(index);
      }
    });

    const label = document.createElement("label");
    label.htmlFor = `cam-${index}`;
    label.innerHTML = `${cam.type} en ${cam.ip}`;

    div.appendChild(checkbox);
    div.appendChild(label);
    container.appendChild(div);
  });
}

async function acceptSelection() {
  const toAdd = Array.from(state.selectedForAdd).map(idx => state.scanResults[idx]);
  const toRemove = Array.from(state.selectedForRemove)
    .map(id => state.configuredCameras.find(camera => camera.id === id))
    .filter(Boolean);
  const toRename = Array.from(state.renamedCameras.entries()).map(([id, name]) => ({ id, name }));

  if (toAdd.length === 0 && toRemove.length === 0 && toRename.length === 0) {
    hideModal();
    return;
  }

  try {
    const payload = {};
    if (toAdd.length > 0) {
      payload.add = toAdd;
    }
    if (toRemove.length > 0) {
      payload.remove = toRemove;
    }
    if (toRename.length > 0) {
      payload.rename = toRename;
    }

    await fetchJson("/api/update-cameras", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    alert("Configuracion actualizada.");
    hideModal();
    await loadCameras();
    await loadHealth();
  } catch (error) {
    alert(`Error al actualizar: ${error.message}`);
  }
}

function setupEvents() {
  document.getElementById("refresh-btn").addEventListener("click", async () => {
    await loadHealth();
    await loadCameras();
  });

  document.getElementById("add-camera-btn").addEventListener("click", showModal);
  document.getElementById("close-modal-btn").addEventListener("click", hideModal);
  document.getElementById("cancel-btn").addEventListener("click", hideModal);
  document.getElementById("scan-btn").addEventListener("click", scanNetwork);
  document.getElementById("accept-btn").addEventListener("click", acceptSelection);

  const modalOverlay = document.getElementById("add-camera-modal");
  const modalContent = modalOverlay.querySelector(".modal-content");
  modalOverlay.addEventListener("click", hideModal);
  modalContent.addEventListener("click", (event) => event.stopPropagation());
  window.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      hideModal();
    }
  });

  document.getElementById("toggle-alarm-btn").addEventListener("click", toggleAlarm);
  document.getElementById("toggle-light-btn").addEventListener("click", toggleLight);

  document.querySelectorAll("#ptz-controls button").forEach((button) => {
    button.addEventListener("click", async () => {
      await moveCamera(button.dataset.move);
    });
  });
}

async function init() {
  setupEvents();
  hideModal();
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
