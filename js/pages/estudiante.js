/* ── GUARD ───────────────────────────────────────────────── */
function initEstudiantePage(titulo) {
  const usuario = Auth.getUsuarioActivo();
  if (!usuario || usuario.rol !== "USER" || sessionStorage.getItem("rol_activo") !== "ESTUDIANTE") {
    window.location.href = BASE_PATH + "index.html";
    return null;
  }
  Sidebar.inject(usuario, window.location.pathname);
  const t = document.getElementById("topbar-title");
  if (t) t.textContent = titulo;
  return usuario;
}

function getParams() { return new URLSearchParams(window.location.search); }

function minimoAprobacion() { return parseInt(localStorage.getItem("porcentaje_minimo") || "60"); }
function num(v) { return v === null || v === undefined || v === "" ? null : Number(v); }

function formatFechaE(f) {
  if (!f) return "—";
  return new Date(f).toLocaleDateString("es-EC", { day:"2-digit", month:"short", year:"numeric" });
}

function formatFechaHora(f) {
  if (!f) return "—";
  const d = new Date(f);
  return d.toLocaleDateString("es-EC", { day:"2-digit", month:"short", year:"numeric" }) +
    " " + d.toLocaleTimeString("es-EC", { hour:"2-digit", minute:"2-digit" });
}

function eVencida(fecha) { return fecha && new Date(fecha) < new Date(); }

/* ── NOTIF ───────────────────────────────────────────────── */
function ENotif(mensaje, tipo = "success") {
  let n = document.getElementById("enotif");
  if (!n) {
    n = document.createElement("div"); n.id = "enotif";
    n.style.cssText = `position:fixed;bottom:24px;right:24px;z-index:9999;max-width:340px;
      padding:14px 18px;border-radius:10px;font-size:.875rem;font-family:inherit;
      display:flex;align-items:center;gap:10px;box-shadow:0 4px 20px rgba(0,0,0,.15);
      animation:fadeIn .2s ease;transition:opacity .3s ease;`;
    document.body.appendChild(n);
  }
  const c = tipo === "success"
    ? { bg:"#ECFDF5", color:"#065F46", border:"#059669", icon:"check-circle" }
    : { bg:"#FEF2F2", color:"#991B1B", border:"#DC2626", icon:"exclamation-circle" };
  n.style.background = c.bg; n.style.color = c.color; n.style.borderLeft = `4px solid ${c.border}`;
  n.innerHTML = `<i class="bi-${c.icon}"></i><span>${mensaje}</span>`;
  n.style.opacity = "1";
  n.style.pointerEvents = "auto";
  clearTimeout(ENotif._t);
  clearTimeout(ENotif._r);
  ENotif._t = setTimeout(() => {
    n.style.opacity = "0";
    n.style.pointerEvents = "none";
    ENotif._r = setTimeout(() => n.remove(), 310);
  }, 3000);
}

/* ── MIS CURSOS ──────────────────────────────────────────── */
const MisCursosEstudiante = {
  async init() {
    const u = initEstudiantePage("Mis Cursos");
    if (!u) return;
    try {
      const todos  = await API.cursos();
      const cursos = todos.filter(c => c.mi_rol === "ESTUDIANTE");
      const activos    = cursos.filter(c => c.estado === "activo");
      const archivados = cursos.filter(c => c.estado === "archivado");

      /* Progreso por curso (en paralelo) */
      const progresos = await Promise.all(cursos.map(c => API.progresoCurso(c.id).catch(() => ({ porcentaje: 0 }))));
      const pctById = {};
      cursos.forEach((c, i) => { pctById[c.id] = progresos[i].porcentaje; });

      this.renderGrid("grid-activos", activos, pctById);
      this.renderGrid("grid-archivados", archivados, pctById);
      const secArch = document.getElementById("sec-archivados");
      if (secArch) secArch.style.display = archivados.length ? "block" : "none";

      const kpiEl = document.getElementById("kpi-cursos");
      if (kpiEl) kpiEl.textContent = activos.length;
    } catch (e) { ENotif(e.message, "danger"); }
  },

  renderGrid(containerId, cursos, pctById) {
    const el = document.getElementById(containerId);
    if (!el) return;
    if (!cursos.length) {
      el.innerHTML = `<div class="empty-state"><i class="bi-mortarboard"></i><p>No hay cursos aqui.</p></div>`;
      return;
    }
    el.innerHTML = cursos.map(c => {
      const pct = pctById[c.id] || 0;
      return `
        <div class="course-card">
          <div class="course-card-header">
            <h4>${c.nombre}</h4>
            <span>${c.facultad_codigo || "—"} &bull; ${c.codigo}</span>
          </div>
          <div class="course-card-body">
            <p class="text-sm" style="margin:0 0 10px;-webkit-line-clamp:2;display:-webkit-box;-webkit-box-orient:vertical;overflow:hidden">${c.descripcion}</p>
            ${c.profesor_nombre ? `<p class="text-xs text-muted" style="margin:0 0 10px"><i class="bi-person-workspace"></i> ${c.profesor_nombre}</p>` : ""}
            <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px">
              <div class="progress-bar" style="flex:1"><div class="progress-fill ${pct===100?"success":""}" style="width:${pct}%"></div></div>
              <span class="text-xs text-muted">${pct}%</span>
            </div>
          </div>
          <div class="course-card-footer">
            <span class="badge badge-${c.estado === "activo" ? "success" : "neutral"}">${c.estado === "activo" ? "Activo" : "Archivado"}</span>
            <a href="curso.html?id=${c.id}" class="btn btn-primary btn-sm">
              Ir al curso <i class="bi-arrow-right"></i>
            </a>
          </div>
        </div>`;
    }).join("");
  }
};

/* ── CURSO (vista estudiante) ────────────────────────────── */
const CursoEstudiante = {
  async init() {
    const u = initEstudiantePage("Curso");
    if (!u) return;
    const id = parseInt(getParams().get("id"));
    let curso;
    try { curso = await API.cursoDetalle(id); }
    catch { window.location.href = "mis-cursos.html"; return; }
    if (!curso) { window.location.href = "mis-cursos.html"; return; }

    const prog = await API.progresoCurso(id).catch(() => ({ porcentaje: 0 }));
    const pct  = prog.porcentaje;

    document.getElementById("curso-nombre").textContent = curso.nombre;
    document.getElementById("curso-descripcion").textContent = curso.descripcion;
    document.getElementById("curso-codigo").innerHTML   = `<span class="badge badge-primary">${curso.codigo}</span>`;
    document.getElementById("curso-facultad").textContent = curso.facultad_nombre || "—";
    document.getElementById("curso-fechas").textContent = `${formatFechaE(curso.fecha_inicio)} — ${formatFechaE(curso.fecha_fin)}`;
    const profEl = document.getElementById("curso-profesor");
    if (profEl && curso.profesor_nombre) profEl.textContent = curso.profesor_nombre;

    const pctEl = document.getElementById("progreso-pct");
    const barEl = document.getElementById("progreso-bar");
    if (pctEl) pctEl.textContent = `${pct}%`;
    if (barEl) { barEl.style.width = `${pct}%`; if (pct === 100) barEl.classList.add("success"); }

    if (curso.estado === "archivado") {
      const aviso = document.getElementById("aviso-archivado");
      if (aviso) aviso.style.display = "flex";
    }

    this.renderModulos(id);
    this.renderTareasPendientes(id);
    this.renderQuizzesPendientes(id);
  },

  async renderModulos(cursoId) {
    const el = document.getElementById("lista-modulos");
    if (!el) return;
    let modulos = [];
    try { modulos = await API.modulos(cursoId); } catch (e) { ENotif(e.message, "danger"); }
    if (!modulos.length) {
      el.innerHTML = `<div class="empty-state"><i class="bi-collection"></i><p>No hay modulos disponibles aun.</p></div>`;
      return;
    }
    el.innerHTML = modulos.map(m => {
      const completado = !!m.completado;
      const mats = (m.materiales || []).length;
      return `
        <a href="modulo.html?modulo_id=${m.id}&curso_id=${cursoId}" style="text-decoration:none">
          <div class="module-item" style="cursor:pointer;transition:background .15s" onmouseover="this.style.background='#F9FAFB'" onmouseout="this.style.background=''">
            <div class="module-num" style="${completado ? "background:var(--color-success);color:#fff" : ""}">${completado ? '<i class="bi-check-lg"></i>' : m.orden}</div>
            <div class="module-info">
              <strong>${m.titulo}</strong>
              <span>${mats} material${mats !== 1 ? "es" : ""}</span>
            </div>
            <span class="badge badge-${completado ? "success" : "neutral"}">${completado ? "Completado" : "Pendiente"}</span>
          </div>
        </a>`;
    }).join("");
  },

  async renderTareasPendientes(cursoId) {
    const el = document.getElementById("lista-tareas");
    if (!el) return;
    let tareas = [];
    try { tareas = await API.tareas(cursoId); } catch (e) { ENotif(e.message, "danger"); }
    const entregas = await Promise.all(tareas.map(t => API.miEntrega(t.id).catch(() => ({ estado: "pendiente" }))));
    const pendientes = tareas.filter((t, i) => entregas[i].estado !== "entregado");
    if (!pendientes.length) {
      el.innerHTML = `<div class="empty-state" style="padding:20px"><i class="bi-check2-all"></i><p>Sin tareas pendientes.</p></div>`;
      return;
    }
    el.innerHTML = pendientes.map(t => {
      const vencida = eVencida(t.fecha_limite);
      return `
        <a href="tarea.html?tarea_id=${t.id}&curso_id=${cursoId}" style="text-decoration:none">
          <div style="display:flex;justify-content:space-between;align-items:center;padding:12px 0;border-bottom:1px solid var(--color-border);gap:12px">
            <div>
              <p class="fw-semibold text-sm" style="margin:0">${t.titulo}</p>
              <p class="text-xs text-muted" style="margin:2px 0 0"><i class="bi-clock"></i> ${formatFechaHora(t.fecha_limite)}</p>
            </div>
            <span class="badge badge-${vencida ? "danger" : "warning"}">${vencida ? "Vencida" : "Pendiente"}</span>
          </div>
        </a>`;
    }).join("");
  },

  async renderQuizzesPendientes(cursoId) {
    const el = document.getElementById("lista-quizzes");
    if (!el) return;
    let quizzes = [];
    try { quizzes = await API.quizzes(cursoId); } catch (e) { ENotif(e.message, "danger"); }
    const resps = await Promise.all(quizzes.map(q => API.respuestasQuiz(q.id).catch(() => [])));
    const pendientes = quizzes.filter((q, i) => resps[i].length === 0);
    if (!pendientes.length) {
      el.innerHTML = `<div class="empty-state" style="padding:20px"><i class="bi-check2-all"></i><p>Sin quizzes pendientes.</p></div>`;
      return;
    }
    el.innerHTML = pendientes.map(q => {
      const vencida = eVencida(q.fecha_limite);
      return `
        <a href="quiz.html?quiz_id=${q.id}&curso_id=${cursoId}" style="text-decoration:none">
          <div style="display:flex;justify-content:space-between;align-items:center;padding:12px 0;border-bottom:1px solid var(--color-border);gap:12px">
            <div>
              <p class="fw-semibold text-sm" style="margin:0">${q.titulo}</p>
              <p class="text-xs text-muted" style="margin:2px 0 0">
                <i class="bi-clock"></i> ${formatFechaHora(q.fecha_limite)}
                ${q.tiempo_limite_min ? ` &bull; ${q.tiempo_limite_min} min` : ""}
              </p>
            </div>
            <span class="badge badge-${vencida ? "danger" : "warning"}">${vencida ? "Vencido" : "Pendiente"}</span>
          </div>
        </a>`;
    }).join("");
  }
};

/* ── MODULO (vista estudiante) ───────────────────────────── */
const ModuloEstudiante = {
  _modulos: [],

  async init() {
    const u = initEstudiantePage("Modulo");
    if (!u) return;
    const modulo_id = parseInt(getParams().get("modulo_id"));
    const curso_id  = parseInt(getParams().get("curso_id"));
    try { this._modulos = await API.modulos(curso_id); }
    catch { window.location.href = `curso.html?id=${curso_id}`; return; }
    const m = this._modulos.find(m => m.id === modulo_id);
    if (!m) { window.location.href = `curso.html?id=${curso_id}`; return; }

    document.getElementById("modulo-titulo").textContent     = m.titulo;
    document.getElementById("modulo-descripcion").textContent= m.descripcion || "";
    document.getElementById("btn-volver").href               = `curso.html?id=${curso_id}`;

    const completado = !!m.completado;
    const btnComp    = document.getElementById("btn-completar");
    if (btnComp) {
      if (completado) {
        btnComp.textContent = "Modulo completado";
        btnComp.disabled    = true;
        btnComp.className   = "btn btn-ghost btn-sm";
      } else {
        btnComp.onclick = () => this.marcarCompletado(modulo_id);
      }
    }

    this.renderMateriales(m.materiales || []);
    this.renderNavegacion(modulo_id, curso_id);
  },

  renderMateriales(mats) {
    const el = document.getElementById("lista-materiales");
    if (!el) return;
    if (!mats.length) {
      el.innerHTML = `<div class="empty-state"><i class="bi-folder2-open"></i><p>Este modulo no tiene materiales aun.</p></div>`;
      return;
    }
    el.innerHTML = mats.map(mat => {
      const iconos = { video:"play-circle-fill", pdf:"file-pdf-fill", enlace:"link-45deg" };
      const colores = { video:"#EF4444", pdf:"#F97316", enlace:"#2563EB" };
      const icon   = iconos[mat.tipo] || "file";
      const color  = colores[mat.tipo] || "var(--color-primary)";
      return `
        <a href="${mat.url}" target="_blank" style="text-decoration:none">
          <div class="material-item" style="cursor:pointer;border:1px solid var(--color-border);border-radius:var(--radius-lg);padding:14px 16px;margin-bottom:8px;display:flex;align-items:center;gap:12px;transition:box-shadow .15s" onmouseover="this.style.boxShadow='var(--shadow-md)'" onmouseout="this.style.boxShadow=''">
            <div class="material-icon" style="background:${color}1A;color:${color};width:40px;height:40px;border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:1.25rem;flex-shrink:0">
              <i class="bi-${icon}"></i>
            </div>
            <div style="flex:1;min-width:0">
              <p class="fw-semibold text-sm" style="margin:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${mat.titulo}</p>
              <p class="text-xs text-muted" style="margin:2px 0 0;text-transform:capitalize">${mat.tipo}</p>
            </div>
            <i class="bi-box-arrow-up-right text-muted text-xs"></i>
          </div>
        </a>`;
    }).join("");
  },

  renderNavegacion(modulo_id, curso_id) {
    const modulos = [...this._modulos].sort((a, b) => a.orden - b.orden);
    const idx     = modulos.findIndex(m => m.id === modulo_id);
    const prev    = idx > 0 ? modulos[idx - 1] : null;
    const next    = idx < modulos.length - 1 ? modulos[idx + 1] : null;
    const navEl   = document.getElementById("nav-modulos");
    if (!navEl) return;
    navEl.innerHTML = `
      <div style="display:flex;justify-content:space-between;gap:12px">
        ${prev
          ? `<a href="modulo.html?modulo_id=${prev.id}&curso_id=${curso_id}" class="btn btn-ghost btn-sm"><i class="bi-arrow-left"></i> ${prev.titulo}</a>`
          : `<span></span>`}
        ${next
          ? `<a href="modulo.html?modulo_id=${next.id}&curso_id=${curso_id}" class="btn btn-primary btn-sm">${next.titulo} <i class="bi-arrow-right"></i></a>`
          : `<a href="curso.html?id=${curso_id}" class="btn btn-ghost btn-sm">Volver al curso <i class="bi-arrow-right"></i></a>`}
      </div>`;
  },

  async marcarCompletado(modulo_id) {
    try {
      await API.marcarCompletado(modulo_id);
      ENotif("Modulo marcado como completado.");
      const btn = document.getElementById("btn-completar");
      if (btn) { btn.textContent = "Modulo completado"; btn.disabled = true; btn.className = "btn btn-ghost btn-sm"; }
    } catch (e) { ENotif(e.message, "danger"); }
  }
};

/* ── TAREA (vista estudiante) ────────────────────────────── */
const TareaEstudiante = {
  async init() {
    const u = initEstudiantePage("Tarea");
    if (!u) return;
    const tarea_id = parseInt(getParams().get("tarea_id"));
    const curso_id = parseInt(getParams().get("curso_id"));
    let tarea;
    try { tarea = await API.tareaDetalle(tarea_id); }
    catch { window.location.href = `curso.html?id=${curso_id}`; return; }

    document.getElementById("tarea-titulo").textContent     = tarea.titulo;
    document.getElementById("tarea-descripcion").innerHTML  = (tarea.descripcion || "").replace(/\n/g, "<br>");
    document.getElementById("tarea-limite").textContent     = formatFechaHora(tarea.fecha_limite);
    document.getElementById("tarea-puntaje").textContent    = `${tarea.puntaje_maximo} pts`;
    document.getElementById("btn-volver").href              = `curso.html?id=${curso_id}`;

    if (tarea.criterios) {
      const crit = document.getElementById("tarea-criterios");
      if (crit) { crit.textContent = tarea.criterios; crit.closest(".card").style.display = ""; }
    }

    const entrega = await API.miEntrega(tarea_id).catch(() => ({ estado: "pendiente" }));
    const vencida = eVencida(tarea.fecha_limite);

    if (entrega && entrega.estado === "entregado") {
      this.mostrarEntregaHecha(entrega, tarea);
    } else if (vencida) {
      const f = document.getElementById("form-entrega");
      if (f) f.innerHTML = `<div class="alert alert-danger" style="display:flex;gap:8px">
        <i class="bi-exclamation-circle"></i><span>La fecha limite ha vencido. No se pueden recibir mas entregas.</span></div>`;
    }
  },

  mostrarEntregaHecha(entrega, tarea) {
    const f = document.getElementById("form-entrega");
    if (!f) return;
    const nota = num(entrega.nota);
    const notaHtml = nota !== null
      ? `<div class="kpi-card" style="max-width:200px">
          <div class="kpi-icon ${nota >= minimoAprobacion() ? "success" : "warning"}"><i class="bi-award"></i></div>
          <div class="kpi-info"><div class="kpi-value">${entrega.nota} / ${tarea.puntaje_maximo}</div><div class="kpi-label">Calificacion</div></div>
         </div>`
      : `<div class="alert alert-info" style="margin-bottom:0"><i class="bi-hourglass-split"></i><span>Pendiente de calificacion.</span></div>`;
    f.innerHTML = `
      <div class="alert alert-success" style="display:flex;gap:8px;margin-bottom:16px">
        <i class="bi-check-circle-fill"></i><span>Tarea entregada el ${formatFechaHora(entrega.fecha)}.</span>
      </div>
      ${notaHtml}
      ${entrega.comentario ? `<div class="alert alert-info" style="margin-top:12px"><i class="bi-chat-left-text"></i><span><strong>Retroalimentacion:</strong> ${entrega.comentario}</span></div>` : ""}`;
  },

  async entregar() {
    const tarea_id = parseInt(getParams().get("tarea_id"));
    const curso_id = parseInt(getParams().get("curso_id"));
    const tipo     = document.getElementById("tipo-entrega").value;
    let valor = "";

    if (tipo === "texto")   valor = document.getElementById("entrega-texto").value.trim();
    if (tipo === "archivo") valor = document.getElementById("entrega-archivo").value.trim();
    if (tipo === "link")    valor = document.getElementById("entrega-link").value.trim();

    if (!valor) { ENotif("Completa el campo de entrega.", "danger"); return; }

    const payload = {
      texto:  tipo === "texto"   ? valor : null,
      archivo:tipo === "archivo" ? valor : null,
      link:   tipo === "link"    ? valor : null,
    };
    try {
      await API.entregar(tarea_id, payload);
      ENotif("Tarea entregada correctamente.");
      setTimeout(() => { window.location.href = `curso.html?id=${curso_id}`; }, 1000);
    } catch (e) { ENotif(e.message, "danger"); }
  },

  cambiarTipo(tipo) {
    ["texto","archivo","link"].forEach(t => {
      const el = document.getElementById(`campo-${t}`);
      if (el) el.style.display = t === tipo ? "block" : "none";
    });
  }
};

/* ── QUIZ (vista estudiante) ─────────────────────────────── */
const QuizEstudiante = {
  quiz: null,
  timer: null,
  _ordenActual: {},

  async init() {
    const u = initEstudiantePage("Quiz");
    if (!u) return;
    const quiz_id  = parseInt(getParams().get("quiz_id"));
    const curso_id = parseInt(getParams().get("curso_id"));
    let quiz, misRespuestas;
    try {
      [quiz, misRespuestas] = await Promise.all([
        API.quizDetalle(quiz_id),
        API.respuestasQuiz(quiz_id).catch(() => [])
      ]);
    } catch { window.location.href = `curso.html?id=${curso_id}`; return; }
    if (!quiz) { window.location.href = `curso.html?id=${curso_id}`; return; }

    this.quiz = quiz;
    const preguntas = quiz.preguntas || [];
    document.getElementById("quiz-titulo").textContent     = quiz.titulo;
    document.getElementById("quiz-descripcion").textContent= quiz.descripcion || "";
    document.getElementById("quiz-preguntas").textContent  = `${preguntas.length} preguntas`;
    document.getElementById("btn-volver").href             = `curso.html?id=${curso_id}`;

    const yaRespondido = misRespuestas && misRespuestas.length ? misRespuestas[0] : null;
    const vencido      = eVencida(quiz.fecha_limite);

    if (yaRespondido) { this.mostrarResultado(yaRespondido, quiz); return; }
    if (vencido) {
      const f = document.getElementById("form-quiz");
      if (f) f.innerHTML = `<div class="alert alert-danger" style="display:flex;gap:8px">
        <i class="bi-exclamation-circle"></i><span>Este quiz ha vencido y ya no acepta respuestas.</span></div>`;
      return;
    }

    if (quiz.tiempo_limite_min) {
      const timerEl = document.getElementById("quiz-timer");
      if (timerEl) { timerEl.style.display = "flex"; this.iniciarTimer(quiz.tiempo_limite_min, timerEl); }
    }
    this.renderPreguntas(quiz);
  },

  iniciarTimer(minutos, el) {
    let segundos = minutos * 60;
    const span = el.querySelector("span");
    this.timer = setInterval(() => {
      segundos--;
      const m = Math.floor(segundos / 60).toString().padStart(2,"0");
      const s = (segundos % 60).toString().padStart(2,"0");
      if (span) span.textContent = `${m}:${s}`;
      if (segundos <= 60) el.style.color = "var(--color-danger)";
      if (segundos <= 0)  { clearInterval(this.timer); this.enviar(true); }
    }, 1000);
  },

  renderPreguntas(quiz) {
    const el = document.getElementById("preguntas-quiz");
    const preguntas = quiz.preguntas || [];
    if (!el || !preguntas.length) return;
    el.innerHTML = preguntas.map((p, i) => `
      <div class="card" style="margin-bottom:16px" id="pregunta-${p.id}">
        <div class="card-header">
          <span class="text-sm fw-semibold text-muted">Pregunta ${i + 1} de ${preguntas.length}</span>
          <span class="badge badge-neutral">${p.puntaje} pt${num(p.puntaje) !== 1 ? "s" : ""}</span>
        </div>
        <div class="card-body">
          <p class="fw-semibold" style="margin:0 0 16px">${p.enunciado}</p>
          ${this.renderInputRespuesta(p, i)}
        </div>
      </div>`).join("");
  },

  renderInputRespuesta(p, i) {
    const opciones = p.opciones || [];
    switch (p.tipo) {
      case "opcion_multiple_una":
        return opciones.map((o, j) => `
          <label style="display:flex;align-items:center;gap:8px;padding:10px 12px;border:1px solid var(--color-border);border-radius:8px;margin-bottom:6px;cursor:pointer">
            <input type="radio" name="resp-${p.id}" value="${j}" class="preg-resp" data-id="${p.id}">
            <span class="text-sm">${o}</span>
          </label>`).join("");

      case "opcion_multiple_varias":
        return opciones.map((o, j) => `
          <label style="display:flex;align-items:center;gap:8px;padding:10px 12px;border:1px solid var(--color-border);border-radius:8px;margin-bottom:6px;cursor:pointer">
            <input type="checkbox" name="resp-${p.id}" value="${j}" class="preg-resp" data-id="${p.id}">
            <span class="text-sm">${o}</span>
          </label>`).join("");

      case "verdadero_falso":
        return ["Verdadero","Falso"].map(v => `
          <label style="display:flex;align-items:center;gap:8px;padding:10px 12px;border:1px solid var(--color-border);border-radius:8px;margin-bottom:6px;cursor:pointer">
            <input type="radio" name="resp-${p.id}" value="${v}" class="preg-resp" data-id="${p.id}">
            <span class="text-sm">${v}</span>
          </label>`).join("");

      case "completar_espacios":
      case "menu_desplegable":
      case "respuesta_numerica":
        return `<input type="${p.tipo === "respuesta_numerica" ? "number" : "text"}" class="form-control preg-resp" data-id="${p.id}" placeholder="Tu respuesta...">`;

      case "respuesta_corta":
        return `<input type="text" class="form-control preg-resp" data-id="${p.id}" placeholder="Escribe tu respuesta...">`;

      case "ensayo":
        return `<textarea class="form-control preg-resp" data-id="${p.id}" rows="5" placeholder="Desarrolla tu respuesta..."></textarea>`;

      case "subida_archivo":
      case "respuesta_imagen":
        return `<div style="border:2px dashed var(--color-border);border-radius:10px;padding:24px;text-align:center">
          <i class="bi-upload" style="font-size:1.5rem;color:var(--color-text-muted);display:block;margin-bottom:6px"></i>
          <p class="text-sm text-muted" style="margin:0 0 8px">Selecciona un archivo</p>
          <input type="file" class="preg-resp" data-id="${p.id}" style="display:none" id="file-${p.id}">
          <button class="btn btn-outline btn-sm" onclick="document.getElementById('file-${p.id}').click()">Elegir archivo</button>
        </div>`;

      case "editor_codigo":
        return `<textarea class="form-control preg-resp" data-id="${p.id}" rows="8" placeholder="// Escribe tu codigo aqui..." style="font-family:monospace;font-size:.8125rem"></textarea>`;

      case "escala_valoracion":
        return `<div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:4px">
          ${[1,2,3,4,5].map(n => `
            <label style="display:flex;flex-direction:column;align-items:center;gap:4px;padding:8px 12px;border:1px solid var(--color-border);border-radius:8px;cursor:pointer;min-width:52px">
              <input type="radio" name="resp-${p.id}" value="${n}" class="preg-resp" data-id="${p.id}">
              <span class="text-sm fw-semibold">${n}</span>
            </label>`).join("")}
        </div>`;

      case "relacionar_columnas": {
        const colA = p.columna_a || opciones;
        const colB = p.columna_b || p.opciones_b || [...opciones].sort(() => Math.random() - 0.5);
        return `<div style="margin-top:4px">
          ${colA.map((a, j) => `
            <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px">
              <div style="flex:1;padding:8px 12px;background:var(--color-primary-soft);border-radius:8px;font-size:.875rem;font-weight:500">${a}</div>
              <i class="bi-arrow-right" style="color:var(--color-text-muted);flex-shrink:0"></i>
              <select class="form-control preg-resp-rel" data-id="${p.id}" data-col="${j}" style="flex:1">
                <option value="">Selecciona...</option>
                ${colB.map(b => `<option value="${b}">${b}</option>`).join("")}
              </select>
            </div>`).join("")}
        </div>`;
      }

      case "ordenamiento":
      case "secuencia": {
        const items = [...opciones].sort(() => Math.random() - 0.5);
        this._ordenActual[p.id] = items;
        return `<div id="orden-${p.id}" data-id="${p.id}">` +
          items.map((item, j) => `
            <div class="orden-item" style="display:flex;align-items:center;gap:8px;padding:8px 12px;border:1px solid var(--color-border);border-radius:8px;margin-bottom:6px;background:var(--color-surface)">
              <span style="color:var(--color-text-muted);font-size:.75rem;font-weight:700;min-width:22px">${j + 1}</span>
              <span class="text-sm" style="flex:1">${item}</span>
              <div style="display:flex;gap:2px">
                <button type="button" class="btn btn-ghost btn-sm" style="padding:3px 7px" onclick="QuizEstudiante.moverOrden('${p.id}', ${j}, -1)"><i class="bi-chevron-up"></i></button>
                <button type="button" class="btn btn-ghost btn-sm" style="padding:3px 7px" onclick="QuizEstudiante.moverOrden('${p.id}', ${j}, 1)"><i class="bi-chevron-down"></i></button>
              </div>
            </div>`).join("") +
          `</div>`;
      }

      case "seleccion_imagen": {
        const imgSrc = p.imagen || "";
        if (imgSrc) {
          return `<div style="position:relative;display:inline-block;cursor:crosshair;max-width:100%" onclick="QuizEstudiante.marcarHotspot(event,'${p.id}',this)">
            <img src="${imgSrc}" style="max-width:100%;border-radius:8px;display:block">
            <div id="hotspot-mark-${p.id}" style="position:absolute;display:none;width:22px;height:22px;border-radius:50%;background:var(--color-primary);border:3px solid white;transform:translate(-50%,-50%);pointer-events:none"></div>
            <input type="hidden" class="preg-resp" data-id="${p.id}" id="hotspot-val-${p.id}">
          </div>
          <p class="text-sm text-muted" id="hotspot-txt-${p.id}" style="margin-top:6px">Haz clic en la imagen para marcar tu respuesta.</p>`;
        }
        return `<div style="border:2px dashed var(--color-border);border-radius:10px;padding:36px;text-align:center;cursor:crosshair;position:relative" onclick="QuizEstudiante.marcarHotspot(event,'${p.id}',this)">
          <i class="bi-cursor" style="font-size:1.75rem;color:var(--color-text-muted);display:block;margin-bottom:8px"></i>
          <p class="text-sm text-muted" style="margin:0">Haz clic aqui para marcar tu respuesta</p>
          <div id="hotspot-mark-${p.id}" style="position:absolute;display:none;width:18px;height:18px;border-radius:50%;background:var(--color-primary);border:3px solid white;transform:translate(-50%,-50%);pointer-events:none"></div>
          <input type="hidden" class="preg-resp" data-id="${p.id}" id="hotspot-val-${p.id}">
        </div>
        <p class="text-sm text-muted" id="hotspot-txt-${p.id}" style="margin-top:6px">No has marcado ningun punto.</p>`;
      }

      default:
        return `<input type="text" class="form-control preg-resp" data-id="${p.id}" placeholder="Tu respuesta...">`;
    }
  },

  moverOrden(pregId, idx, dir) {
    const arr = this._ordenActual[pregId];
    if (!arr) return;
    const newIdx = idx + dir;
    if (newIdx < 0 || newIdx >= arr.length) return;
    [arr[idx], arr[newIdx]] = [arr[newIdx], arr[idx]];
    const el = document.getElementById(`orden-${pregId}`);
    if (!el) return;
    el.innerHTML = arr.map((item, j) => `
      <div class="orden-item" style="display:flex;align-items:center;gap:8px;padding:8px 12px;border:1px solid var(--color-border);border-radius:8px;margin-bottom:6px;background:var(--color-surface)">
        <span style="color:var(--color-text-muted);font-size:.75rem;font-weight:700;min-width:22px">${j + 1}</span>
        <span class="text-sm" style="flex:1">${item}</span>
        <div style="display:flex;gap:2px">
          <button type="button" class="btn btn-ghost btn-sm" style="padding:3px 7px" onclick="QuizEstudiante.moverOrden('${pregId}', ${j}, -1)"><i class="bi-chevron-up"></i></button>
          <button type="button" class="btn btn-ghost btn-sm" style="padding:3px 7px" onclick="QuizEstudiante.moverOrden('${pregId}', ${j}, 1)"><i class="bi-chevron-down"></i></button>
        </div>
      </div>`).join("");
  },

  marcarHotspot(event, pregId, container) {
    const rect = container.getBoundingClientRect();
    const x = Math.round(((event.clientX - rect.left) / rect.width) * 100);
    const y = Math.round(((event.clientY - rect.top) / rect.height) * 100);
    const mark = document.getElementById(`hotspot-mark-${pregId}`);
    const val  = document.getElementById(`hotspot-val-${pregId}`);
    const txt  = document.getElementById(`hotspot-txt-${pregId}`);
    if (mark) { mark.style.display = "block"; mark.style.left = `${x}%`; mark.style.top = `${y}%`; }
    if (val)  val.value = `${x},${y}`;
    if (txt)  txt.textContent = `Punto marcado: (${x}%, ${y}%)`;
  },

  async enviar(automatico = false) {
    if (!this.quiz) return;
    if (this.timer) clearInterval(this.timer);
    const respuestas = {};

    (this.quiz.preguntas || []).forEach(p => {
      if (p.tipo === "opcion_multiple_una") {
        const sel = document.querySelector(`input[name="resp-${p.id}"]:checked`);
        respuestas[p.id] = sel ? sel.value : null;
      } else if (p.tipo === "verdadero_falso") {
        const sel = document.querySelector(`input[name="resp-${p.id}"]:checked`);
        respuestas[p.id] = sel ? sel.value : null;
      } else if (p.tipo === "opcion_multiple_varias" || p.tipo === "escala_valoracion") {
        const sels = Array.from(document.querySelectorAll(`input[name="resp-${p.id}"]:checked`)).map(i => i.value);
        respuestas[p.id] = sels;
      } else if (p.tipo === "relacionar_columnas") {
        const sels = document.querySelectorAll(`.preg-resp-rel[data-id="${p.id}"]`);
        const result = {};
        sels.forEach(s => { result[s.dataset.col] = s.value; });
        respuestas[p.id] = result;
      } else if (p.tipo === "ordenamiento" || p.tipo === "secuencia") {
        respuestas[p.id] = this._ordenActual[p.id] || [];
      } else {
        const inp = document.querySelector(`.preg-resp[data-id="${p.id}"]`);
        respuestas[p.id] = inp ? inp.value : null;
      }
    });

    try {
      await API.enviarQuiz(this.quiz.id, respuestas);
      if (!automatico) ENotif("Quiz enviado correctamente.");
      setTimeout(() => { window.location.reload(); }, 800);
    } catch (e) { ENotif(e.message, "danger"); }
  },

  mostrarResultado(resultado, quiz) {
    const total    = (quiz.preguntas || []).reduce((a, p) => a + num(p.puntaje), 0);
    const notaAuto = num(resultado.nota_automatica) || 0;
    const pct      = total > 0 ? Math.round((notaAuto / total) * 100) : 0;
    const aprobado = pct >= minimoAprobacion();
    const notaManual = num(resultado.nota_manual);
    const f        = document.getElementById("form-quiz");
    if (!f) return;
    f.innerHTML = `
      <div class="card">
        <div class="card-body" style="text-align:center;padding:32px">
          <div style="width:64px;height:64px;border-radius:50%;background:${aprobado ? "#ECFDF5" : "#FEF2F2"};display:flex;align-items:center;justify-content:center;margin:0 auto 16px;font-size:1.75rem">
            <i class="bi-${aprobado ? "patch-check-fill" : "x-circle-fill"}" style="color:${aprobado ? "var(--color-success)" : "var(--color-danger)"}"></i>
          </div>
          <h3 style="margin:0 0 6px">${aprobado ? "Aprobado" : "No aprobado"}</h3>
          <p class="text-muted text-sm" style="margin:0 0 20px">Enviado el ${formatFechaHora(resultado.fecha)}</p>
          <div class="kpi-grid" style="max-width:400px;margin:0 auto">
            <div class="kpi-card"><div class="kpi-icon ${aprobado ? "success" : "warning"}"><i class="bi-award"></i></div>
              <div class="kpi-info"><div class="kpi-value">${notaAuto} / ${total}</div><div class="kpi-label">Puntos</div></div></div>
            <div class="kpi-card"><div class="kpi-icon primary"><i class="bi-percent"></i></div>
              <div class="kpi-info"><div class="kpi-value">${pct}%</div><div class="kpi-label">Porcentaje</div></div></div>
          </div>
          ${notaManual !== null ? `<div class="alert alert-info" style="margin-top:16px"><i class="bi-award"></i><span>Nota manual asignada por el profesor: <strong>${resultado.nota_manual} pts</strong></span></div>` : ""}
        </div>
      </div>`;
  }
};

/* ── CALIFICACIONES ──────────────────────────────────────── */
const CalificacionesEstudiante = {
  async init() {
    const u = initEstudiantePage("Calificaciones");
    if (!u) return;
    const el = document.getElementById("lista-calificaciones");
    if (!el) return;
    let cursos;
    try { cursos = (await API.cursos()).filter(c => c.mi_rol === "ESTUDIANTE"); }
    catch (e) { ENotif(e.message, "danger"); return; }

    if (!cursos.length) {
      el.innerHTML = `<div class="empty-state"><i class="bi-clipboard-data"></i><p>No estas inscrito en ningun curso.</p></div>`;
      return;
    }

    const bloques = await Promise.all(cursos.map(c => this.renderCurso(c)));
    el.innerHTML = bloques.join("");
  },

  async renderCurso(c) {
    const minimo = minimoAprobacion();
    const [tareas, quizzes, prog] = await Promise.all([
      API.tareas(c.id).catch(() => []),
      API.quizzes(c.id).catch(() => []),
      API.progresoCurso(c.id).catch(() => ({ porcentaje: 0 }))
    ]);
    const [entregas, resps] = await Promise.all([
      Promise.all(tareas.map(t => API.miEntrega(t.id).catch(() => ({})))),
      Promise.all(quizzes.map(q => API.respuestasQuiz(q.id).catch(() => [])))
    ]);

    const tareaRows = tareas.map((t, i) => ({
      titulo: t.titulo, nota: num(entregas[i].nota), max: num(t.puntaje_maximo), tipo: "Tarea"
    }));
    const quizRows = quizzes.map((q, i) => ({
      titulo: q.titulo, nota: resps[i].length ? num(resps[i][0].nota_automatica) : null,
      max: num(q.puntaje_total), tipo: "Quiz"
    }));
    const items = [...tareaRows, ...quizRows];
    const formula = c.formula || [];
    const pct = prog.porcentaje;

    return `
      <div class="card" style="margin-bottom:20px">
        <div class="card-header">
          <div>
            <h4 style="margin:0">${c.nombre}</h4>
            <span class="text-xs text-muted">${c.codigo}</span>
          </div>
          <div style="display:flex;align-items:center;gap:8px">
            <div class="progress-bar" style="width:80px"><div class="progress-fill" style="width:${pct}%"></div></div>
            <span class="text-xs text-muted">${pct}%</span>
          </div>
        </div>
        <div class="card-body" style="padding:0">
          <div class="table-container" style="border:none;box-shadow:none;border-radius:0">
            <table class="table">
              <thead><tr><th>Actividad</th><th>Tipo</th><th>Nota</th><th>Maximo</th><th>Estado</th></tr></thead>
              <tbody>
                ${items.length
                  ? items.map(item => {
                      const pctItem = item.nota !== null && item.max ? Math.round((item.nota / item.max) * 100) : null;
                      const ok      = pctItem !== null && pctItem >= minimo;
                      return `
                        <tr>
                          <td class="fw-semibold text-sm">${item.titulo}</td>
                          <td><span class="badge badge-${item.tipo === "Tarea" ? "primary" : "secondary"}">${item.tipo}</span></td>
                          <td class="fw-semibold text-sm ${item.nota !== null ? (ok ? "text-success" : "text-danger") : "text-muted"}">${item.nota !== null ? item.nota : "—"}</td>
                          <td class="text-sm text-muted">${item.max ?? "—"}</td>
                          <td>${item.nota !== null ? `<span class="badge badge-${ok ? "success" : "danger"}">${ok ? "Aprobado" : "Reprobado"}</span>` : `<span class="badge badge-neutral">Pendiente</span>`}</td>
                        </tr>`;
                    }).join("")
                  : `<tr><td colspan="5" class="text-center text-muted text-sm" style="padding:20px">Sin actividades calificadas aun.</td></tr>`}
              </tbody>
            </table>
          </div>
          ${formula.length
            ? `<div style="padding:12px 16px;border-top:1px solid var(--color-border);background:#F9FAFB">
                <p class="text-xs text-muted fw-semibold" style="margin:0 0 6px;text-transform:uppercase;letter-spacing:.05em">Formula de calificacion</p>
                <div style="display:flex;gap:16px;flex-wrap:wrap">
                  ${formula.map(f => `<span class="text-xs"><span class="fw-semibold">${f.componente}</span> ${f.porcentaje}%</span>`).join("")}
                </div>
              </div>`
            : ""}
        </div>
      </div>`;
  }
};

/* ── PROGRESO ────────────────────────────────────────────── */
const ProgresoEstudiante = {
  async init() {
    const u = initEstudiantePage("Mi Progreso");
    if (!u) return;
    const el = document.getElementById("lista-progreso");
    if (!el) return;
    let cursos;
    try { cursos = (await API.cursos()).filter(c => c.mi_rol === "ESTUDIANTE" && c.estado === "activo"); }
    catch (e) { ENotif(e.message, "danger"); return; }

    if (!cursos.length) {
      el.innerHTML = `<div class="empty-state"><i class="bi-graph-up"></i><p>No tienes cursos activos.</p></div>`;
      return;
    }

    const datos = await Promise.all(cursos.map(c => this.datosCurso(c)));

    const totalMods = datos.reduce((a, d) => a + d.prog.total, 0);
    const compMods  = datos.reduce((a, d) => a + d.prog.completados, 0);
    const kpiPct    = totalMods > 0 ? Math.round((compMods / totalMods) * 100) : 0;

    const kpiMods   = document.getElementById("kpi-modulos");
    const kpiCursos = document.getElementById("kpi-cursos-activos");
    const kpiGlobal = document.getElementById("kpi-global");
    if (kpiMods)   kpiMods.textContent   = `${compMods} / ${totalMods}`;
    if (kpiCursos) kpiCursos.textContent = cursos.length;
    if (kpiGlobal) kpiGlobal.textContent = `${kpiPct}%`;

    el.innerHTML = datos.map(d => {
      const c = d.curso, pct = d.prog.porcentaje;
      return `
        <div class="card" style="margin-bottom:20px">
          <div class="card-header">
            <h4 style="margin:0">${c.nombre}</h4>
            <a href="curso.html?id=${c.id}" class="btn btn-ghost btn-sm">Ver curso <i class="bi-arrow-right"></i></a>
          </div>
          <div class="card-body">
            <div style="margin-bottom:16px">
              <div style="display:flex;justify-content:space-between;margin-bottom:6px">
                <span class="text-sm fw-semibold">Progreso general</span>
                <span class="text-sm fw-semibold text-primary">${pct}%</span>
              </div>
              <div class="progress-bar" style="height:10px;border-radius:999px">
                <div class="progress-fill ${pct===100?"success":""}" style="width:${pct}%;height:10px;border-radius:999px;transition:width .6s ease"></div>
              </div>
            </div>
            <div class="kpi-grid">
              <div class="kpi-card">
                <div class="kpi-icon ${d.prog.completados === d.prog.total && d.prog.total > 0 ? "success" : "secondary"}"><i class="bi-collection"></i></div>
                <div class="kpi-info"><div class="kpi-value">${d.prog.completados} / ${d.prog.total}</div><div class="kpi-label">Modulos completados</div></div>
              </div>
              <div class="kpi-card">
                <div class="kpi-icon ${d.entregadas === d.totalTareas && d.totalTareas > 0 ? "success" : "warning"}"><i class="bi-file-check"></i></div>
                <div class="kpi-info"><div class="kpi-value">${d.entregadas} / ${d.totalTareas}</div><div class="kpi-label">Tareas entregadas</div></div>
              </div>
              <div class="kpi-card">
                <div class="kpi-icon ${d.respondidos === d.totalQuizzes && d.totalQuizzes > 0 ? "success" : "warning"}"><i class="bi-patch-check"></i></div>
                <div class="kpi-info"><div class="kpi-value">${d.respondidos} / ${d.totalQuizzes}</div><div class="kpi-label">Quizzes respondidos</div></div>
              </div>
            </div>
          </div>
        </div>`;
    }).join("");
  },

  async datosCurso(c) {
    const [prog, tareas, quizzes] = await Promise.all([
      API.progresoCurso(c.id).catch(() => ({ total: 0, completados: 0, porcentaje: 0 })),
      API.tareas(c.id).catch(() => []),
      API.quizzes(c.id).catch(() => [])
    ]);
    const [entregas, resps] = await Promise.all([
      Promise.all(tareas.map(t => API.miEntrega(t.id).catch(() => ({ estado: "pendiente" })))),
      Promise.all(quizzes.map(q => API.respuestasQuiz(q.id).catch(() => [])))
    ]);
    return {
      curso: c, prog,
      totalTareas: tareas.length,
      entregadas: entregas.filter(e => e.estado === "entregado").length,
      totalQuizzes: quizzes.length,
      respondidos: resps.filter(r => r.length > 0).length,
    };
  }
};
