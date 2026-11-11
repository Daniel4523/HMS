const roleLabels = {
  admin: "Administrador",
  admisiones: "Admisiones",
  medico: "Médico",
  enfermeria: "Enfermería",
};

const navigationItems = [
  { id: "inicio", label: "Resumen", icon: "⌂", roles: Object.keys(roleLabels) },
  { id: "pacientes", label: "Pacientes", icon: "♧", roles: Object.keys(roleLabels) },
  { id: "citas", label: "Citas", icon: "▦", roles: ["admisiones"] },
  { id: "medicos", label: "Médicos", icon: "✚", roles: ["admin"] },
  { id: "usuarios", label: "Usuarios", icon: "♙", roles: ["admin"] },
  { id: "historia", label: "Historia clínica", icon: "▤", roles: ["medico", "enfermeria"] },
  { id: "auditoria", label: "Auditoría", icon: "◷", roles: ["admin"] },
];

const quickDescriptions = {
  pacientes: ["Pacientes", "Busca personas y consulta sus datos.", "♧"],
  citas: ["Agendar cita", "Programa una atención con un médico.", "▦"],
  medicos: ["Médicos", "Gestiona el equipo y las especialidades.", "✚"],
  usuarios: ["Usuarios", "Crea cuentas para el personal.", "♙"],
  historia: ["Historia clínica", "Consulta las evoluciones del paciente.", "▤"],
  auditoria: ["Auditoría", "Revisa las acciones recientes.", "◷"],
};

const state = {
  token: localStorage.getItem("saludintegral_token"),
  role: localStorage.getItem("saludintegral_role"),
  login: localStorage.getItem("saludintegral_login"),
  patientForAppointment: null,
};

const loginScreen = document.querySelector("#login-screen");
const appScreen = document.querySelector("#app-screen");
const globalMessage = document.querySelector("#global-message");

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[char]);
}

function showMessage(message, isError = false, target = globalMessage) {
  target.textContent = message;
  target.classList.toggle("error", isError);
}

async function api(path, options = {}) {
  const headers = new Headers(options.headers || {});
  if (state.token) headers.set("Authorization", `Bearer ${state.token}`);
  if (options.body && !(options.body instanceof FormData)) headers.set("Content-Type", "application/json");
  const response = await fetch(path, { ...options, headers });
  if (response.status === 401 && state.token) {
    logout();
    throw new Error("Tu sesión terminó. Inicia sesión de nuevo.");
  }
  const contentType = response.headers.get("content-type") || "";
  const data = contentType.includes("application/json") ? await response.json() : null;
  if (!response.ok) {
    const detail = data?.detail;
    const message = Array.isArray(detail)
      ? detail.map((item) => `${item.loc?.slice(-1)[0] || "Dato"}: ${item.msg}`).join(" · ")
      : detail || "No fue posible completar la solicitud.";
    throw new Error(message);
  }
  return data;
}

function formData(form) {
  return Object.fromEntries(new FormData(form).entries());
}

function dateLabel(value) {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString("es-CO", { dateStyle: "medium", timeStyle: "short" });
}

function patientRow(patient, actionLabel = null, action = null) {
  const row = document.createElement("div");
  row.className = "result-row";
  const detail = document.createElement("div");
  const name = document.createElement("strong");
  name.textContent = `${patient.nombres} ${patient.apellidos}`;
  const metadata = document.createElement("small");
  metadata.textContent = `${patient.tipo_doc} ${patient.num_doc} · ${patient.telefono || "Sin teléfono"}`;
  detail.append(name, metadata);
  row.append(detail);
  if (actionLabel && action) {
    const button = document.createElement("button");
    button.className = "button secondary";
    button.type = "button";
    button.textContent = actionLabel;
    button.addEventListener("click", () => action(patient));
    row.append(button);
  }
  return row;
}

function renderPatients(target, patients, actionLabel, action) {
  target.replaceChildren();
  if (!patients.length) {
    const empty = document.createElement("p");
    empty.className = "empty-state";
    empty.textContent = "No se encontraron pacientes.";
    target.append(empty);
    return;
  }
  patients.forEach((patient) => target.append(patientRow(patient, actionLabel, action)));
}

function availableItems() {
  return navigationItems.filter((item) => item.roles.includes(state.role));
}

function showSection(id) {
  document.querySelectorAll(".page-section").forEach((section) => {
    section.hidden = section.id !== `section-${id}`;
  });
  document.querySelectorAll(".nav-link").forEach((link) => {
    link.classList.toggle("active", link.dataset.section === id);
  });
  const item = navigationItems.find((candidate) => candidate.id === id);
  document.querySelector("#page-title").textContent = item?.label || "Resumen";
  globalMessage.textContent = "";
  if (id === "medicos") loadDoctors();
  if (id === "auditoria") loadAudit();
}

function renderApp() {
  if (!state.token || !roleLabels[state.role]) {
    logout(false);
    return;
  }
  loginScreen.hidden = true;
  appScreen.hidden = false;
  document.querySelector("#user-name").textContent = state.login || roleLabels[state.role];
  document.querySelector("#user-role").textContent = roleLabels[state.role];
  document.querySelector("#welcome-user").textContent = state.login || roleLabels[state.role];
  document.querySelector("#today-label").textContent = new Date().toLocaleDateString("es-CO", {
    weekday: "long", day: "numeric", month: "long", year: "numeric",
  });

  const items = availableItems();
  const navigation = document.querySelector("#navigation");
  navigation.replaceChildren();
  items.forEach((item) => {
    const link = document.createElement("a");
    link.className = "nav-link";
    link.href = `#${item.id}`;
    link.dataset.section = item.id;
    link.innerHTML = `<span class="nav-icon" aria-hidden="true">${item.icon}</span><span>${escapeHtml(item.label)}</span>`;
    link.addEventListener("click", (event) => {
      event.preventDefault();
      showSection(item.id);
      history.replaceState(null, "", `#${item.id}`);
    });
    navigation.append(link);
  });

  const quickLinks = document.querySelector("#quick-links");
  quickLinks.replaceChildren();
  items.filter((item) => item.id !== "inicio").forEach((item) => {
    const [label, description, icon] = quickDescriptions[item.id];
    const link = document.createElement("a");
    link.className = "quick-card";
    link.href = `#${item.id}`;
    link.innerHTML = `<span class="quick-icon" aria-hidden="true">${icon}</span><span><strong>${escapeHtml(label)}</strong><small>${escapeHtml(description)}</small></span>`;
    link.addEventListener("click", (event) => {
      event.preventDefault();
      showSection(item.id);
      history.replaceState(null, "", `#${item.id}`);
    });
    quickLinks.append(link);
  });

  document.querySelector("#new-patient-panel").hidden = state.role !== "admisiones";
  showSection(navigationItems.some((item) => item.id === location.hash.slice(1) && item.roles.includes(state.role))
    ? location.hash.slice(1) : "inicio");
}

function logout(showLogin = true) {
  state.token = null;
  state.role = null;
  state.login = null;
  localStorage.removeItem("saludintegral_token");
  localStorage.removeItem("saludintegral_role");
  localStorage.removeItem("saludintegral_login");
  appScreen.hidden = true;
  loginScreen.hidden = !showLogin;
}

document.querySelector("#login-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  const error = document.querySelector("#login-error");
  showMessage("Conectando…", false, error);
  try {
    const credentials = formData(form);
    const result = await api("/login", { method: "POST", body: JSON.stringify(credentials) });
    state.token = result.token;
    state.role = result.rol;
    state.login = credentials.login;
    localStorage.setItem("saludintegral_token", state.token);
    localStorage.setItem("saludintegral_role", state.role);
    localStorage.setItem("saludintegral_login", state.login);
    error.textContent = "";
    form.reset();
    renderApp();
  } catch (errorValue) {
    showMessage(errorValue.message, true, error);
  }
});

document.querySelector("#logout-button").addEventListener("click", () => logout());

document.querySelector("#search-patient-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const query = document.querySelector("#patient-query").value.trim();
  const results = document.querySelector("#patient-results");
  results.innerHTML = '<p class="empty-state">Buscando…</p>';
  try {
    const patients = await api(`/pacientes?q=${encodeURIComponent(query)}`);
    renderPatients(results, patients);
  } catch (error) {
    results.innerHTML = `<p class="empty-state">${escapeHtml(error.message)}</p>`;
  }
});

document.querySelector("#new-patient-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  const patient = formData(form);
  if (!patient.correo) patient.correo = null;
  try {
    const created = await api("/pacientes", { method: "POST", body: JSON.stringify(patient) });
    form.reset();
    document.querySelector("#new-patient-panel").open = false;
    document.querySelector("#patient-query").value = patient.num_doc;
    document.querySelector("#search-patient-form").requestSubmit();
    showMessage(`Paciente registrado correctamente (ID ${created.id}).`);
  } catch (error) {
    showMessage(error.message, true);
  }
});

document.querySelector("#appointment-patient-search").addEventListener("submit", async (event) => {
  event.preventDefault();
  const query = document.querySelector("#appointment-patient-query").value.trim();
  const results = document.querySelector("#appointment-patient-results");
  results.innerHTML = '<p class="empty-state">Buscando…</p>';
  try {
    const patients = await api(`/pacientes?q=${encodeURIComponent(query)}`);
    renderPatients(results, patients, "Seleccionar", selectAppointmentPatient);
  } catch (error) {
    results.innerHTML = `<p class="empty-state">${escapeHtml(error.message)}</p>`;
  }
});

async function selectAppointmentPatient(patient) {
  state.patientForAppointment = patient;
  document.querySelector("#selected-patient").textContent = `Paciente seleccionado: ${patient.nombres} ${patient.apellidos} · ${patient.tipo_doc} ${patient.num_doc}`;
  document.querySelector("#appointment-form").hidden = false;
  const select = document.querySelector("#doctor-select");
  select.innerHTML = '<option value="">Cargando médicos…</option>';
  try {
    const doctors = await api("/medicos");
    select.replaceChildren(new Option("Selecciona un médico", ""));
    doctors.forEach((doctor) => select.add(new Option(`${doctor.nombre} · ${doctor.especialidad} — ${doctor.sede}`, doctor.id)));
    if (!doctors.length) select.replaceChildren(new Option("No hay médicos registrados", ""));
  } catch (error) {
    showMessage(error.message, true);
  }
}

document.querySelector("#appointment-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!state.patientForAppointment) {
    showMessage("Busca y selecciona un paciente primero.", true);
    return;
  }
  const values = formData(event.currentTarget);
  const appointment = {
    id_paciente: state.patientForAppointment.id,
    id_medico: Number(values.id_medico),
    inicio: new Date(values.inicio).toISOString(),
    fin: new Date(values.fin).toISOString(),
    consultorio: values.consultorio,
  };
  try {
    const result = await api("/citas", { method: "POST", body: JSON.stringify(appointment) });
    showMessage(`Cita #${result.id} agendada para ${dateLabel(result.inicio)}.`);
    event.currentTarget.reset();
    event.currentTarget.hidden = true;
    state.patientForAppointment = null;
    document.querySelector("#selected-patient").textContent = "";
  } catch (error) {
    showMessage(error.message, true);
  }
});

document.querySelector("#new-doctor-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  try {
    const result = await api("/medicos", { method: "POST", body: JSON.stringify(formData(form)) });
    form.reset();
    showMessage(`Médico registrado correctamente (ID ${result.id}).`);
    loadDoctors();
  } catch (error) {
    showMessage(error.message, true);
  }
});

document.querySelector("#new-user-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = event.currentTarget;
  try {
    const result = await api("/usuarios", { method: "POST", body: JSON.stringify(formData(form)) });
    form.reset();
    showMessage(`Usuario ${result.login} creado con el rol ${roleLabels[result.rol] || result.rol}.`);
  } catch (error) {
    showMessage(error.message, true);
  }
});

async function loadDoctors() {
  const results = document.querySelector("#doctor-results");
  results.innerHTML = '<p class="empty-state">Cargando médicos…</p>';
  try {
    const doctors = await api("/medicos");
    results.replaceChildren();
    if (!doctors.length) {
      results.innerHTML = '<p class="empty-state">Aún no hay médicos registrados.</p>';
      return;
    }
    doctors.forEach((doctor) => {
      const row = document.createElement("div");
      row.className = "result-row";
      const detail = document.createElement("div");
      const name = document.createElement("strong");
      name.textContent = doctor.nombre;
      const metadata = document.createElement("small");
      metadata.textContent = `${doctor.especialidad} · ${doctor.sede}`;
      detail.append(name, metadata);
      row.append(detail);
      results.append(row);
    });
  } catch (error) {
    results.innerHTML = `<p class="empty-state">${escapeHtml(error.message)}</p>`;
  }
}

document.querySelector("#history-search-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const query = document.querySelector("#history-patient-query").value.trim();
  const results = document.querySelector("#history-patient-results");
  results.innerHTML = '<p class="empty-state">Buscando…</p>';
  try {
    const patients = await api(`/pacientes?q=${encodeURIComponent(query)}`);
    renderPatients(results, patients, "Ver historia", loadHistory);
  } catch (error) {
    results.innerHTML = `<p class="empty-state">${escapeHtml(error.message)}</p>`;
  }
});

async function loadHistory(patient) {
  const container = document.querySelector("#history-content");
  container.innerHTML = '<div class="panel"><p class="empty-state">Cargando historia clínica…</p></div>';
  try {
    const historyRecord = await api(`/historia/${patient.id}`);
    const evolutions = historyRecord.evoluciones || [];
    container.innerHTML = `
      <div class="history-card">
        <h3>${escapeHtml(patient.nombres)} ${escapeHtml(patient.apellidos)}</h3>
        <p class="muted">${escapeHtml(patient.tipo_doc)} ${escapeHtml(patient.num_doc)} · Historia abierta ${escapeHtml(dateLabel(historyRecord.fecha_apertura))}</p>
        ${evolutions.length ? evolutions.map((item) => `
          <article class="evolution">
            <strong>${escapeHtml(item.motivo)} · ${escapeHtml(item.diagnostico_cie10)}</strong>
            <p>${escapeHtml(item.nota)}</p>
            <small>${escapeHtml(dateLabel(item.fecha))} · Versión ${escapeHtml(item.version)}</small>
          </article>`).join("") : '<p class="empty-state">Esta historia aún no tiene evoluciones.</p>'}
        ${state.role === "medico" ? `
          <form id="evolution-form" class="form-stack history-form">
            <h3>Registrar evolución</h3>
            <label>Motivo<input name="motivo" minlength="3" required></label>
            <label>Diagnóstico CIE-10<input name="diagnostico_cie10" placeholder="Ej. J06.9" required></label>
            <label>Nota clínica<textarea name="nota" minlength="3" required></textarea></label>
            <button class="button primary" type="submit">Guardar evolución</button>
          </form>` : ""}
      </div>`;
    const form = container.querySelector("#evolution-form");
    if (form) form.addEventListener("submit", async (event) => {
      event.preventDefault();
      try {
        await api(`/historia/${patient.id}/evoluciones`, { method: "POST", body: JSON.stringify(formData(form)) });
        showMessage("Evolución clínica guardada.");
        await loadHistory(patient);
      } catch (error) {
        showMessage(error.message, true);
      }
    });
  } catch (error) {
    container.innerHTML = `<div class="panel"><p class="empty-state">${escapeHtml(error.message)}</p></div>`;
  }
}

async function loadAudit() {
  const results = document.querySelector("#audit-results");
  results.innerHTML = '<p class="empty-state">Cargando actividad…</p>';
  try {
    const entries = await api("/auditoria");
    results.replaceChildren();
    if (!entries.length) {
      results.innerHTML = '<p class="empty-state">Aún no hay actividad registrada.</p>';
      return;
    }
    entries.forEach((entry) => {
      const row = document.createElement("div");
      row.className = "result-row";
      const detail = document.createElement("div");
      const action = document.createElement("strong");
      action.textContent = entry.accion;
      const metadata = document.createElement("small");
      metadata.textContent = `${entry.recurso} · Usuario ${entry.id_usuario ?? "sistema"}`;
      const date = document.createElement("small");
      date.textContent = dateLabel(entry.fecha);
      detail.append(action, metadata);
      row.append(detail, date);
      results.append(row);
    });
  } catch (error) {
    results.innerHTML = `<p class="empty-state">${escapeHtml(error.message)}</p>`;
  }
}

if (state.token) renderApp();
