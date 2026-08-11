/* ── GUARD ───────────────────────────────────────────────── */
function initProfesorPage(titulo) {
  const usuario = Auth.getUsuarioActivo();
  if (!usuario || usuario.rol !== "USER" || sessionStorage.getItem("rol_activo") !== "PROFESOR") {
    window.location.href = BASE_PATH + "index.html";
    return null;
  }
  Sidebar.inject(usuario, window.location.pathname);
  const t = document.getElementById("topbar-title");
  if (t) t.textContent = titulo;
  return usuario;
}

function getParams() { return new URLSearchParams(window.location.search); }

function formatFecha(f) {
  if (!f) return "—";
  return new Date(f).toLocaleDateString("es-EC", { day:"2-digit", month:"short", year:"numeric" });
}

function inicialesDe(nombre) {
  const parts = (nombre || "").trim().split(/\s+/);
  return (((parts[0] || "")[0] || "") + ((parts[1] || "")[0] || "")).toUpperCase() || "?";
}

function badgeCurso(estado) {
  return estado === "activo"
    ? `<span class="badge badge-success">Activo</span>`
    : `<span class="badge badge-neutral">Archivado</span>`;
}

/* ── NOTIF ───────────────────────────────────────────────── */
function Notif(mensaje, tipo = "success") {
  let n = document.getElementById("pnotif");
  if (!n) {
    n = document.createElement("div"); n.id = "pnotif";
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
  clearTimeout(Notif._t);
  clearTimeout(Notif._r);
  Notif._t = setTimeout(() => {
    n.style.opacity = "0";
    n.style.pointerEvents = "none";
    Notif._r = setTimeout(() => n.remove(), 310);
  }, 3000);
}

/* ── MIS CURSOS ──────────────────────────────────────────── */
const MisCursosProfesor = {
  async init() {
    const u = initProfesorPage("Mis Cursos");
    if (!u) return;
    try {
      const todos  = await API.cursos();
      const cursos = todos.filter(c => c.mi_rol === "PROFESOR");
      const activos    = cursos.filter(c => c.estado === "activo");
      const archivados = cursos.filter(c => c.estado === "archivado");
      this.renderGrid("grid-activos", activos);
      this.renderGrid("grid-archivados", archivados);
      const secArch = document.getElementById("sec-archivados");
      if (secArch) secArch.style.display = archivados.length ? "block" : "none";
    } catch (e) { Notif(e.message, "danger"); }
  },

  renderGrid(containerId, cursos) {
    const el = document.getElementById(containerId);
    if (!el) return;
    if (!cursos.length) {
      el.innerHTML = `<div class="empty-state"><i class="bi-book"></i><p>No hay cursos aqui.</p></div>`;
      return;
    }
    el.innerHTML = cursos.map(c => `
        <div class="course-card">
          <div class="course-card-header">
            <h4>${c.nombre}</h4>
            <span>${c.facultad_codigo || "—"} &bull; ${c.codigo}</span>
          </div>
          <div class="course-card-body">
            <p class="text-sm" style="margin:0 0 12px;-webkit-line-clamp:2;display:-webkit-box;-webkit-box-orient:vertical;overflow:hidden">${c.descripcion}</p>
            <div style="display:flex;gap:12px;font-size:.75rem;color:var(--color-text-muted)">
              <span><i class="bi-people"></i> ${c.total_estudiantes} estudiantes</span>
              <span><i class="bi-calendar"></i> ${formatFecha(c.fecha_fin)}</span>
            </div>
          </div>
          <div class="course-card-footer">
            ${badgeCurso(c.estado)}
            <a href="curso.html?id=${c.id}" class="btn btn-primary btn-sm">
              Gestionar <i class="bi-arrow-right"></i>
            </a>
          </div>
        </div>`).join("");
  }
};

/* ── CURSO FORM ──────────────────────────────────────────── */
const CursoForm = {
  componenteIndex: 0,

  async init() {
    const u = initProfesorPage("Curso");
    if (!u) return;
    const id = parseInt(getParams().get("id")) || null;

    /* Poblar select de facultades */
    try {
      const facultades = await API.facultades();
      const selFac = document.getElementById("c-facultad");
      if (selFac) {
        selFac.innerHTML = `<option value="">Seleccionar...</option>` +
          facultades.map(f => `<option value="${f.id}">${f.nombre}</option>`).join("");
      }
    } catch (e) { Notif(e.message, "danger"); }

    if (id) {
      document.getElementById("form-titulo").textContent = "Editar Curso";
      const h2 = document.getElementById("form-titulo-h2");
      if (h2) h2.textContent = "Editar Curso";
      try {
        const c = await API.cursoDetalle(id);
        document.getElementById("c-nombre").value      = c.nombre;
        document.getElementById("c-descripcion").value = c.descripcion;
        document.getElementById("c-facultad").value    = c.facultad;
        document.getElementById("c-inicio").value      = c.fecha_inicio;
        document.getElementById("c-fin").value         = c.fecha_fin;
        document.getElementById("c-codigo").value      = c.codigo;
        (c.formula || []).forEach(f => this.agregarComponente(f.componente, f.porcentaje));
      } catch (e) { Notif(e.message, "danger"); }
    } else {
      document.getElementById("form-titulo").textContent = "Nuevo Curso";
      document.getElementById("c-codigo").value = "CURSO-" + Math.random().toString(36).slice(2,8).toUpperCase();
      this.agregarComponente("Tareas", 40);
      this.agregarComponente("Quizzes", 30);
      this.agregarComponente("Proyecto Final", 30);
    }
    this.actualizarTotal();
  },

  agregarComponente(nombre = "", porcentaje = 0) {
    const idx = this.componenteIndex++;
    const cont = document.getElementById("formula-items");
    if (!cont) return;
    const div = document.createElement("div");
    div.id = `comp-${idx}`;
    div.style.cssText = "display:flex;gap:8px;align-items:center;margin-bottom:8px";
    div.innerHTML = `
      <input type="text"   class="form-control comp-nombre" placeholder="Ej: Examenes" value="${nombre}" style="flex:1" oninput="CursoForm.actualizarTotal()">
      <input type="number" class="form-control comp-pct" placeholder="%" value="${porcentaje}" min="0" max="100" style="width:80px" oninput="CursoForm.actualizarTotal()">
      <span class="text-muted text-sm">%</span>
      <button class="btn btn-ghost btn-sm" onclick="CursoForm.quitarComponente('comp-${idx}')"><i class="bi-trash"></i></button>`;
    cont.appendChild(div);
  },

  quitarComponente(id) {
    const el = document.getElementById(id);
    if (el) { el.remove(); this.actualizarTotal(); }
  },

  actualizarTotal() {
    const vals = Array.from(document.querySelectorAll(".comp-pct")).map(i => parseFloat(i.value) || 0);
    const total = vals.reduce((a, b) => a + b, 0);
    const el    = document.getElementById("formula-total");
    if (el) {
      el.textContent = `Total: ${total}%`;
      el.style.color = total === 100 ? "var(--color-success)" : "var(--color-danger)";
    }
  },

  async guardar() {
    const nombre      = document.getElementById("c-nombre").value.trim();
    const descripcion = document.getElementById("c-descripcion").value.trim();
    const facultad    = parseInt(document.getElementById("c-facultad").value);
    const fecha_inicio= document.getElementById("c-inicio").value;
    const fecha_fin   = document.getElementById("c-fin").value;
    const codigo      = document.getElementById("c-codigo").value.trim();

    if (!nombre || !descripcion || !facultad || !fecha_inicio || !fecha_fin) {
      Notif("Completa todos los campos obligatorios.", "danger"); return;
    }
    if (new Date(fecha_fin) <= new Date(fecha_inicio)) {
      Notif("La fecha de fin debe ser posterior al inicio.", "danger"); return;
    }

    const formula = Array.from(document.querySelectorAll("#formula-items > div")).map(div => ({
      componente: div.querySelector(".comp-nombre").value.trim(),
      porcentaje: parseInt(div.querySelector(".comp-pct").value) || 0
    })).filter(f => f.componente);

    const total = formula.reduce((a, b) => a + b.porcentaje, 0);
    if (total !== 100) { Notif("Los porcentajes de la formula deben sumar 100%.", "danger"); return; }

    const id = parseInt(getParams().get("id")) || null;
    const payload = { nombre, codigo, descripcion, facultad, fecha_inicio, fecha_fin, formula };

    try {
      if (id) {
        await API.actualizarCurso(id, payload);
        Notif("Curso actualizado.");
      } else {
        await API.crearCurso(payload);
        Notif("Curso creado exitosamente.");
      }
      setTimeout(() => { window.location.href = "mis-cursos.html"; }, 900);
    } catch (e) { Notif(e.message, "danger"); }
  }
};

/* ── GESTION DEL CURSO ───────────────────────────────────── */
const GestionCurso = {
  curso: null,
  tab: "modulos",

  async init() {
    const u = initProfesorPage("Gestion del Curso");
    if (!u) return;
    const id = parseInt(getParams().get("id"));
    try {
      this.curso = await API.cursoDetalle(id);
    } catch { window.location.href = "mis-cursos.html"; return; }
    if (!this.curso) { window.location.href = "mis-cursos.html"; return; }

    document.getElementById("curso-nombre").textContent = this.curso.nombre;
    document.getElementById("curso-codigo").innerHTML   =
      `<span class="badge badge-primary">${this.curso.codigo}</span>`;
    document.getElementById("curso-estado").innerHTML   =
      badgeCurso(this.curso.estado);

    this.renderModulos();
    this.renderTareas();
    this.renderQuizzes();
    this.renderEstudiantes();
    this.renderFormula();
  },

  cambiarTab(tab) {
    this.tab = tab;
    document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
    document.querySelectorAll(".tab-panel").forEach(p => p.style.display = "none");
    document.getElementById(`tab-${tab}`).classList.add("active");
    document.getElementById(`panel-${tab}`).style.display = "block";
  },

  async renderModulos() {
    const el = document.getElementById("lista-modulos");
    if (!el) return;
    let modulos = [];
    try { modulos = await API.modulos(this.curso.id); } catch (e) { Notif(e.message, "danger"); }
    if (!modulos.length) {
      el.innerHTML = `<div class="empty-state"><i class="bi-collection"></i><p>No hay modulos creados.</p></div>`;
      return;
    }
    el.innerHTML = modulos.map(m => {
      const mats = (m.materiales || []).length;
      return `
        <div class="module-item">
          <div class="module-num">${m.orden}</div>
          <div class="module-info">
            <strong>${m.titulo}</strong>
            <span>${mats} material${mats !== 1 ? "es" : ""}</span>
          </div>
          <div style="display:flex;gap:6px">
            <a href="modulo-form.html?curso_id=${this.curso.id}&modulo_id=${m.id}" class="btn btn-ghost btn-sm">
              <i class="bi-pencil"></i>
            </a>
          </div>
        </div>`;
    }).join("");
  },

  async renderTareas() {
    const el = document.getElementById("lista-tareas");
    if (!el) return;
    let tareas = [];
    try { tareas = await API.tareas(this.curso.id); } catch (e) { Notif(e.message, "danger"); }
    if (!tareas.length) {
      el.innerHTML = `<div class="empty-state"><i class="bi-file-text"></i><p>No hay tareas creadas.</p></div>`;
      return;
    }
    const total = this.curso.total_estudiantes;
    const entregasPorTarea = await Promise.all(tareas.map(t => API.entregas(t.id).catch(() => [])));
    el.innerHTML = `
      <div class="table-container">
        <table class="table">
          <thead><tr><th>Titulo</th><th>Fecha limite</th><th>Puntaje</th><th>Entregas</th><th>Acciones</th></tr></thead>
          <tbody>
            ${tareas.map((t, i) => {
              const entregas = entregasPorTarea[i].filter(e => e.estado === "entregado").length;
              return `
                <tr>
                  <td class="fw-semibold text-sm">${t.titulo}</td>
                  <td class="text-sm">${formatFecha(t.fecha_limite)}</td>
                  <td class="text-sm">${t.puntaje_maximo} pts</td>
                  <td><span class="badge badge-${entregas === total && total > 0 ? "success" : "warning"}">${entregas}/${total}</span></td>
                  <td>
                    <div class="table-actions">
                      <a href="tarea-entregas.html?tarea_id=${t.id}&curso_id=${this.curso.id}" class="btn btn-ghost btn-sm"><i class="bi-eye"></i></a>
                      <a href="tarea-form.html?curso_id=${this.curso.id}&tarea_id=${t.id}" class="btn btn-ghost btn-sm"><i class="bi-pencil"></i></a>
                    </div>
                  </td>
                </tr>`;
            }).join("")}
          </tbody>
        </table>
      </div>`;
  },

  async renderQuizzes() {
    const el = document.getElementById("lista-quizzes");
    if (!el) return;
    let quizzes = [];
    try { quizzes = await API.quizzes(this.curso.id); } catch (e) { Notif(e.message, "danger"); }
    if (!quizzes.length) {
      el.innerHTML = `<div class="empty-state"><i class="bi-patch-question"></i><p>No hay quizzes creados.</p></div>`;
      return;
    }
    el.innerHTML = `
      <div class="table-container">
        <table class="table">
          <thead><tr><th>Titulo</th><th>Preguntas</th><th>Tiempo</th><th>Fecha limite</th><th>Acciones</th></tr></thead>
          <tbody>
            ${quizzes.map(q => `
              <tr>
                <td class="fw-semibold text-sm">${q.titulo}</td>
                <td class="text-sm">${q.total_preguntas}</td>
                <td class="text-sm">${q.tiempo_limite_min ? q.tiempo_limite_min + " min" : "Sin limite"}</td>
                <td class="text-sm">${formatFecha(q.fecha_limite)}</td>
                <td>
                  <div class="table-actions">
                    <a href="quiz-resultados.html?quiz_id=${q.id}&curso_id=${this.curso.id}" class="btn btn-ghost btn-sm"><i class="bi-bar-chart"></i></a>
                    <a href="quiz-form.html?curso_id=${this.curso.id}&quiz_id=${q.id}" class="btn btn-ghost btn-sm"><i class="bi-pencil"></i></a>
                  </div>
                </td>
              </tr>`).join("")}
          </tbody>
        </table>
      </div>`;
  },

  async renderEstudiantes() {
    const el = document.getElementById("lista-estudiantes");
    if (!el) return;
    let estudiantes = [];
    try {
      const insc = await API.inscripciones(this.curso.id);
      estudiantes = insc.filter(i => i.rol_en_curso === "ESTUDIANTE");
    } catch (e) { Notif(e.message, "danger"); }
    if (!estudiantes.length) {
      el.innerHTML = `<div class="empty-state"><i class="bi-people"></i><p>No hay estudiantes inscritos.</p></div>`;
      return;
    }
    el.innerHTML = `
      <div class="table-container">
        <table class="table">
          <thead><tr><th>Estudiante</th><th>Correo</th><th>Inscripcion</th></tr></thead>
          <tbody>
            ${estudiantes.map(e => `
                <tr>
                  <td>
                    <div style="display:flex;align-items:center;gap:8px">
                      <div class="avatar avatar-sm">${inicialesDe(e.usuario_nombre)}</div>
                      <span class="fw-semibold text-sm">${e.usuario_nombre}</span>
                    </div>
                  </td>
                  <td class="text-sm text-muted">${e.usuario_correo}</td>
                  <td class="text-sm text-muted">${formatFecha(e.fecha)}</td>
                </tr>`).join("")}
          </tbody>
        </table>
      </div>`;
  },

  renderFormula() {
    const el = document.getElementById("formula-display");
    if (!el || !this.curso.formula) return;
    el.innerHTML = this.curso.formula.map(f =>
      `<div style="display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid var(--color-border)">
        <span class="text-sm">${f.componente}</span>
        <span class="fw-semibold text-sm text-primary">${f.porcentaje}%</span>
      </div>`
    ).join("") + `
      <div style="display:flex;justify-content:space-between;padding:10px 0;margin-top:4px">
        <span class="fw-semibold text-sm">Total</span>
        <span class="fw-semibold text-sm">100%</span>
      </div>`;
  },

};

/* ── MODAL INSCRIBIR ESTUDIANTES ─────────────────────────── */
const ModalInscribir = {
  _todos: [],
  _filtrados: [],

  async abrir() {
    const modal = document.getElementById("modal-inscribir");
    if (!modal) return;
    const el = document.getElementById("lista-candidatos");
    if (el) el.innerHTML = `<p class="text-sm text-muted" style="padding:16px;text-align:center">Cargando...</p>`;
    modal.classList.add("open");
    try {
      const [usuarios, insc] = await Promise.all([
        API.usuarios(),
        API.inscripciones(GestionCurso.curso.id)
      ]);
      const yaInscritos = new Set(insc.map(i => i.usuario_id));
      this._todos = usuarios.filter(u => u.rol === "USER" && !yaInscritos.has(u.id));
      this._filtrados = [...this._todos];
      const busq = document.getElementById("buscar-insc");
      if (busq) busq.value = "";
      this._render();
    } catch (e) {
      Notif(e.message, "danger");
      modal.classList.remove("open");
    }
  },

  cerrar() {
    const modal = document.getElementById("modal-inscribir");
    if (modal) modal.classList.remove("open");
  },

  filtrar(q) {
    const term = q.trim().toLowerCase();
    this._filtrados = term
      ? this._todos.filter(u =>
          (u.nombres || "").toLowerCase().includes(term) ||
          (u.apellidos || "").toLowerCase().includes(term) ||
          (u.identificacion || "").includes(term))
      : [...this._todos];
    this._render();
  },

  _render() {
    const el = document.getElementById("lista-candidatos");
    if (!el) return;
    if (!this._filtrados.length) {
      el.innerHTML = `<p class="text-sm text-muted" style="padding:20px;text-align:center">
        ${this._todos.length ? "No hay coincidencias." : "Todos los estudiantes ya estan inscritos."}
      </p>`;
      this._conteo();
      return;
    }
    el.innerHTML = this._filtrados.map(u => `
      <label style="display:flex;align-items:center;gap:10px;padding:10px 16px;border-bottom:1px solid var(--color-border);cursor:pointer">
        <input type="checkbox" class="cand-check" value="${u.id}"
          onchange="ModalInscribir._conteo()"
          style="width:16px;height:16px;flex-shrink:0;cursor:pointer">
        <div class="avatar avatar-sm" style="flex-shrink:0">${inicialesDe(u.nombres + " " + u.apellidos)}</div>
        <div>
          <div class="fw-semibold text-sm">${u.nombres} ${u.apellidos}</div>
          <div class="text-xs text-muted">${u.identificacion}${u.correo ? " · " + u.correo : ""}</div>
        </div>
      </label>`).join("");
    this._conteo();
  },

  _conteo() {
    const n = document.querySelectorAll("#lista-candidatos .cand-check:checked").length;
    const el = document.getElementById("insc-conteo");
    if (el) el.textContent = n ? `${n} seleccionado${n !== 1 ? "s" : ""}` : "";
  },

  async confirmar() {
    const checks = Array.from(document.querySelectorAll("#lista-candidatos .cand-check:checked"));
    if (!checks.length) { Notif("Selecciona al menos un estudiante.", "danger"); return; }
    const ids = checks.map(c => parseInt(c.value));
    let ok = 0;
    for (const id of ids) {
      try { await API.inscribir(GestionCurso.curso.id, id, "ESTUDIANTE"); ok++; }
      catch { /* ya inscrito */ }
    }
    this.cerrar();
    if (ok) {
      GestionCurso.curso.total_estudiantes += ok;
      GestionCurso.renderEstudiantes();
      Notif(`${ok} estudiante${ok !== 1 ? "s" : ""} agregado${ok !== 1 ? "s" : ""} correctamente.`);
    }
  }
};

/* ── MODULO FORM ─────────────────────────────────────────── */
const ModuloForm = {
  async init() {
    const u = initProfesorPage("Modulo");
    if (!u) return;
    const curso_id  = parseInt(getParams().get("curso_id"));
    const modulo_id = parseInt(getParams().get("modulo_id")) || null;

    document.getElementById("btn-volver").href = `curso.html?id=${curso_id}`;

    if (modulo_id) {
      try {
        const modulos = await API.modulos(curso_id);
        const m = modulos.find(m => m.id === modulo_id);
        if (m) {
          document.getElementById("m-titulo").value      = m.titulo;
          document.getElementById("m-descripcion").value = m.descripcion || "";
          document.getElementById("m-orden").value       = m.orden;
          this.renderMateriales(m.materiales || []);
        }
      } catch (e) { Notif(e.message, "danger"); }
    } else {
      try {
        const orden = (await API.modulos(curso_id)).length + 1;
        document.getElementById("m-orden").value = orden;
      } catch { document.getElementById("m-orden").value = 1; }
      document.getElementById("panel-materiales").style.display = "none";
    }
  },

  renderMateriales(mats) {
    const el = document.getElementById("lista-materiales");
    if (!el) return;
    if (!mats.length) {
      el.innerHTML = `<div class="empty-state" style="padding:24px"><i class="bi-folder2-open"></i><p>Sin materiales aun.</p></div>`;
      return;
    }
    el.innerHTML = mats.map(mat => `
      <div class="material-item">
        <div class="material-icon ${mat.tipo}">
          <i class="bi-${mat.tipo === "video" ? "play-circle" : mat.tipo === "pdf" ? "file-pdf" : "link-45deg"}"></i>
        </div>
        <div class="material-info">
          <strong>${mat.titulo}</strong>
          <span class="text-xs text-muted">${mat.tipo === "video" ? "Video externo" : mat.tipo === "pdf" ? "Documento PDF" : "Enlace externo"}</span>
        </div>
        <a href="${mat.url}" target="_blank" class="btn btn-ghost btn-sm"><i class="bi-box-arrow-up-right"></i></a>
      </div>`).join("");
  },

  async guardarModulo() {
    const curso_id  = parseInt(getParams().get("curso_id"));
    const modulo_id = parseInt(getParams().get("modulo_id")) || null;
    const titulo    = document.getElementById("m-titulo").value.trim();
    const descripcion = document.getElementById("m-descripcion").value.trim();
    const orden     = parseInt(document.getElementById("m-orden").value) || 1;
    if (!titulo) { Notif("El titulo es obligatorio.", "danger"); return; }

    try {
      if (modulo_id) {
        await API.actualizarModulo(modulo_id, { titulo, descripcion, orden });
        Notif("Modulo actualizado.");
      } else {
        await API.crearModulo(curso_id, { titulo, descripcion, orden });
        Notif("Modulo creado.");
      }
      setTimeout(() => { window.location.href = `curso.html?id=${curso_id}`; }, 800);
    } catch (e) { Notif(e.message, "danger"); }
  },

  async agregarMaterial() {
    const modulo_id = parseInt(getParams().get("modulo_id"));
    if (!modulo_id) { Notif("Guarda el modulo primero.", "danger"); return; }
    const tipo   = document.getElementById("mat-tipo").value;
    const titulo = document.getElementById("mat-titulo").value.trim();
    const url    = document.getElementById("mat-url").value.trim();
    if (!titulo || !url) { Notif("Titulo y URL son obligatorios.", "danger"); return; }
    try {
      await API.crearMaterial(modulo_id, { tipo, titulo, url });
      document.getElementById("mat-titulo").value = "";
      document.getElementById("mat-url").value    = "";
      const modulos = await API.modulos(parseInt(getParams().get("curso_id")));
      const m = modulos.find(m => m.id === modulo_id);
      this.renderMateriales(m ? (m.materiales || []) : []);
      Notif("Material agregado.");
    } catch (e) { Notif(e.message, "danger"); }
  }
};

/* ── TAREA FORM ──────────────────────────────────────────── */
const TareaForm = {
  async init() {
    const u = initProfesorPage("Tarea");
    if (!u) return;
    const curso_id = parseInt(getParams().get("curso_id"));
    const tarea_id = parseInt(getParams().get("tarea_id")) || null;
    document.getElementById("btn-volver").href = `curso.html?id=${curso_id}`;

    if (tarea_id) {
      try {
        const t = await API.tareaDetalle(tarea_id);
        document.getElementById("t-titulo").value      = t.titulo;
        document.getElementById("t-descripcion").value = t.descripcion;
        document.getElementById("t-limite").value      = (t.fecha_limite || "").slice(0, 16);
        document.getElementById("t-puntaje").value     = t.puntaje_maximo;
        document.getElementById("t-criterios").value   = t.criterios || "";
      } catch (e) { Notif(e.message, "danger"); }
    }
  },

  async guardar() {
    const curso_id = parseInt(getParams().get("curso_id"));
    const tarea_id = parseInt(getParams().get("tarea_id")) || null;
    const titulo      = document.getElementById("t-titulo").value.trim();
    const descripcion = document.getElementById("t-descripcion").value.trim();
    const fecha_limite= document.getElementById("t-limite").value;
    const puntaje_maximo = parseFloat(document.getElementById("t-puntaje").value);
    const criterios   = document.getElementById("t-criterios").value.trim();

    if (!titulo || !descripcion || !fecha_limite || !puntaje_maximo) {
      Notif("Completa todos los campos obligatorios.", "danger"); return;
    }
    const payload = { titulo, descripcion, fecha_limite, puntaje_maximo, criterios };

    try {
      if (tarea_id) {
        await API.actualizarTarea(tarea_id, payload);
        Notif("Tarea actualizada.");
      } else {
        await API.crearTarea(curso_id, payload);
        Notif("Tarea creada.");
      }
      setTimeout(() => { window.location.href = `curso.html?id=${curso_id}`; }, 800);
    } catch (e) { Notif(e.message, "danger"); }
  }
};

/* ── TAREA ENTREGAS ──────────────────────────────────────── */
const TareaEntregas = {
  tarea: null,
  _entregas: {},   // usuario_id -> entrega
  _nombres: {},    // usuario_id -> nombre

  async init() {
    const u = initProfesorPage("Entregas");
    if (!u) return;
    const tarea_id = parseInt(getParams().get("tarea_id"));
    const curso_id = parseInt(getParams().get("curso_id"));
    try {
      this.tarea = await API.tareaDetalle(tarea_id);
    } catch (e) { Notif(e.message, "danger"); return; }

    document.getElementById("tarea-titulo").textContent    = this.tarea.titulo;
    document.getElementById("tarea-puntaje").textContent   = `Puntaje maximo: ${this.tarea.puntaje_maximo} pts`;
    document.getElementById("tarea-limite").textContent    = `Fecha limite: ${formatFecha(this.tarea.fecha_limite)}`;
    document.getElementById("btn-volver").href             = `curso.html?id=${curso_id}`;
    this.renderEntregas(tarea_id, curso_id);
  },

  async renderEntregas(tarea_id, curso_id) {
    const tbody = document.getElementById("tabla-entregas");
    if (!tbody) return;
    let estudiantes = [], entregas = [];
    try {
      [estudiantes, entregas] = await Promise.all([
        API.inscripciones(curso_id).then(ins => ins.filter(i => i.rol_en_curso === "ESTUDIANTE")),
        API.entregas(tarea_id)
      ]);
    } catch (e) { Notif(e.message, "danger"); return; }

    this._entregas = {};
    this._nombres  = {};
    entregas.forEach(e => { this._entregas[e.usuario] = e; });
    estudiantes.forEach(e => { this._nombres[e.usuario] = e.usuario_nombre; });

    tbody.innerHTML = estudiantes.map(e => {
      const entrega = this._entregas[e.usuario];
      const estadoBadge = !entrega || entrega.estado === "pendiente"
        ? `<span class="badge badge-neutral">Pendiente</span>`
        : `<span class="badge badge-success">Entregado</span>`;
      const notaDisplay = entrega && entrega.nota !== null && entrega.nota !== undefined
        ? `<span class="fw-semibold text-primary">${entrega.nota}</span>`
        : `<span class="text-muted text-sm">Sin calificar</span>`;
      return `
        <tr>
          <td>
            <div style="display:flex;align-items:center;gap:8px">
              <div class="avatar avatar-sm">${inicialesDe(e.usuario_nombre)}</div>
              <div>
                <div class="fw-semibold text-sm">${e.usuario_nombre}</div>
                <div class="text-xs text-muted">${e.usuario_correo}</div>
              </div>
            </div>
          </td>
          <td>${entrega && entrega.fecha ? formatFecha(entrega.fecha) : "—"}</td>
          <td>${estadoBadge}</td>
          <td>${notaDisplay} <span class="text-xs text-muted">/ ${this.tarea.puntaje_maximo}</span></td>
          <td>
            <div class="table-actions">
              ${entrega && entrega.estado === "entregado"
                ? `<button class="btn btn-ghost btn-sm" onclick="TareaEntregas.verEntrega(${e.usuario})"><i class="bi-eye"></i> Ver</button>
                   <button class="btn btn-primary btn-sm" onclick="ModalCalificar.abrir(${e.usuario})"><i class="bi-award"></i> Calificar</button>`
                : `<span class="text-muted text-sm">—</span>`}
            </div>
          </td>
        </tr>`;
    }).join("");
  },

  verEntrega(usuario_id) {
    const e = this._entregas[usuario_id];
    if (!e) return;
    const modal = document.getElementById("modal-entrega");
    document.getElementById("entrega-estudiante").textContent = this._nombres[usuario_id] || "";
    const cont = document.getElementById("entrega-contenido");
    cont.innerHTML = "";
    if (e.texto)   cont.innerHTML += `<div class="form-group"><label class="form-label">Texto:</label><p class="text-sm" style="background:#F9FAFB;padding:12px;border-radius:8px;margin:0">${e.texto}</p></div>`;
    if (e.archivo) cont.innerHTML += `<div class="form-group"><label class="form-label">Archivo:</label><p class="text-sm"><i class="bi-file-earmark"></i> ${e.archivo}</p></div>`;
    if (e.link)    cont.innerHTML += `<div class="form-group"><label class="form-label">Link:</label><a href="${e.link}" target="_blank" class="text-sm">${e.link}</a></div>`;
    if (e.comentario) cont.innerHTML += `<div class="alert alert-info"><i class="bi-chat"></i> <span>Retroalimentacion: ${e.comentario}</span></div>`;
    modal.classList.add("open");
  }
};

const ModalCalificar = {
  usuarioId: null,

  abrir(usuario_id) {
    this.usuarioId = usuario_id;
    const e = TareaEntregas._entregas[usuario_id];
    const t = TareaEntregas.tarea;
    document.getElementById("cal-estudiante").textContent = TareaEntregas._nombres[usuario_id] || "";
    document.getElementById("cal-nota").value             = e && e.nota !== null && e.nota !== undefined ? e.nota : "";
    document.getElementById("cal-nota").max               = t ? t.puntaje_maximo : 100;
    document.getElementById("cal-comentario").value       = e && e.comentario ? e.comentario : "";
    document.getElementById("modal-calificar").classList.add("open");
  },

  cerrar() { document.getElementById("modal-calificar").classList.remove("open"); },

  async guardar() {
    const nota = parseFloat(document.getElementById("cal-nota").value);
    const comentario = document.getElementById("cal-comentario").value.trim();
    const t = TareaEntregas.tarea;
    if (isNaN(nota) || nota < 0 || nota > t.puntaje_maximo) {
      Notif(`Nota invalida. Debe estar entre 0 y ${t.puntaje_maximo}.`, "danger"); return;
    }
    const e = TareaEntregas._entregas[this.usuarioId];
    if (!e) { Notif("No hay entrega para calificar.", "danger"); return; }
    try {
      await API.calificar(e.id, { nota, comentario });
      this.cerrar();
      const curso_id = parseInt(getParams().get("curso_id"));
      TareaEntregas.renderEntregas(t.id, curso_id);
      Notif("Calificacion guardada.");
    } catch (err) { Notif(err.message, "danger"); }
  }
};

/* ── QUIZ FORM ───────────────────────────────────────────── */
const QuizForm = {
  preguntaIndex: 0,

  async init() {
    const u = initProfesorPage("Quiz");
    if (!u) return;
    const curso_id = parseInt(getParams().get("curso_id"));
    const quiz_id  = parseInt(getParams().get("quiz_id")) || null;
    document.getElementById("btn-volver").href = `curso.html?id=${curso_id}`;

    if (quiz_id) {
      try {
        const q = await API.quizDetalle(quiz_id);
        document.getElementById("q-titulo").value     = q.titulo;
        document.getElementById("q-descripcion").value= q.descripcion || "";
        document.getElementById("q-tiempo").value     = q.tiempo_limite_min || "";
        document.getElementById("q-limite").value     = (q.fecha_limite || "").slice(0, 16);
        (q.preguntas || []).forEach(p => this.renderPregunta(p));
      } catch (e) { Notif(e.message, "danger"); }
    }
  },

  agregarPregunta(tipo = "opcion_multiple_una") {
    this.renderPregunta({ id: null, tipo, enunciado:"", puntaje: 1, opciones:["",""], respuesta_correcta: 0 });
  },

  renderPregunta(p) {
    const idx  = this.preguntaIndex++;
    const cont = document.getElementById("preguntas-container");
    if (!cont) return;

    const tipoLabel = {
      opcion_multiple_una:    "Opcion multiple (1 respuesta)",
      opcion_multiple_varias: "Opcion multiple (varias respuestas)",
      verdadero_falso:        "Verdadero / Falso",
      completar_espacios:     "Completar espacios en blanco",
      relacionar_columnas:    "Relacionar columnas",
      ordenamiento:           "Ordenamiento / Secuencia",
      respuesta_numerica:     "Respuesta numerica",
      menu_desplegable:       "Menu desplegable",
      seleccion_imagen:       "Seleccion en imagen (Hot spot)",
      respuesta_corta:        "Respuesta corta",
      ensayo:                 "Ensayo / Respuesta larga (LaTeX)",
      subida_archivo:         "Subida de archivo",
      respuesta_imagen:       "Respuesta con imagen",
      editor_codigo:          "Editor de codigo",
      escala_valoracion:      "Escala de valoracion (Likert)"
    }[p.tipo] || p.tipo;

    const autoCorregible = ["opcion_multiple_una","opcion_multiple_varias","verdadero_falso",
      "completar_espacios","relacionar_columnas","ordenamiento","respuesta_numerica",
      "menu_desplegable","seleccion_imagen"].includes(p.tipo);

    const div = document.createElement("div");
    div.className = "card preg-card";
    div.dataset.tipo = p.tipo;
    div.style.marginBottom = "16px";
    div.innerHTML = `
      <div class="card-header">
        <div style="display:flex;align-items:center;gap:8px">
          <span class="badge badge-${autoCorregible ? "success" : "warning"}">
            ${autoCorregible ? "Autocorregible" : "Manual"}
          </span>
          <span class="text-sm fw-semibold">${tipoLabel}</span>
        </div>
        <button class="btn btn-ghost btn-sm" onclick="this.closest('.card').remove()"><i class="bi-trash text-danger"></i></button>
      </div>
      <div class="card-body">
        <div class="form-grid form-grid-2" style="gap:12px;margin-bottom:12px">
          <div class="form-group" style="grid-column:1/-1">
            <label class="form-label">Enunciado <span class="required">*</span></label>
            <textarea class="form-control preg-enunciado" rows="2" placeholder="Escribe la pregunta...">${p.enunciado || ""}</textarea>
          </div>
          <div class="form-group">
            <label class="form-label">Puntaje <span class="required">*</span></label>
            <input type="number" class="form-control preg-puntaje" value="${p.puntaje || 1}" min="0.5" step="0.5">
          </div>
        </div>
        ${this.renderInputPregunta(p, idx)}
      </div>`;
    cont.appendChild(div);
  },

  renderInputPregunta(p, idx) {
    switch(p.tipo) {
      case "opcion_multiple_una":
      case "opcion_multiple_varias": {
        const tipoInput = p.tipo === "opcion_multiple_una" ? "radio" : "checkbox";
        const correctas = Array.isArray(p.respuesta_correcta) ? p.respuesta_correcta : [p.respuesta_correcta];
        const opts = (p.opciones && p.opciones.length ? p.opciones : ["",""]).map((o, i) => `
          <div class="opt-row" style="display:flex;align-items:center;gap:8px;margin-bottom:6px">
            <input type="${tipoInput}" class="opt-correct" name="resp-${idx}" ${correctas.includes(i) ? "checked" : ""}>
            <input type="text" class="form-control opt-text" value="${o}" placeholder="Opcion ${i+1}">
          </div>`).join("");
        return `<div class="opciones-wrap" data-name="resp-${idx}"><label class="form-label text-xs text-muted">OPCIONES (marca la correcta)</label>${opts}
          <button class="btn btn-ghost btn-sm" onclick="QuizForm.agregarOpcion(this, '${tipoInput}', 'resp-${idx}')"><i class="bi-plus"></i> Agregar opcion</button></div>`;
      }

      case "verdadero_falso":
        return `<div><label class="form-label text-xs text-muted">RESPUESTA CORRECTA</label>
          <div style="display:flex;gap:12px;margin-top:6px">
            <label style="display:flex;align-items:center;gap:6px"><input type="radio" class="vf-opt" name="vf-${idx}" value="true" ${p.respuesta_correcta === true ? "checked" : ""}> Verdadero</label>
            <label style="display:flex;align-items:center;gap:6px"><input type="radio" class="vf-opt" name="vf-${idx}" value="false" ${p.respuesta_correcta === false ? "checked" : ""}> Falso</label>
          </div></div>`;

      case "completar_espacios":
      case "respuesta_numerica":
      case "menu_desplegable":
        return `<div class="form-group"><label class="form-label text-xs text-muted">RESPUESTA CORRECTA</label>
          <input type="${p.tipo === "respuesta_numerica" ? "number" : "text"}" class="form-control resp-unica" value="${p.respuesta_correcta != null ? p.respuesta_correcta : ""}" placeholder="Respuesta esperada"></div>`;

      case "respuesta_corta":
      case "ensayo":
        return `<div class="alert alert-info" style="margin-top:8px"><i class="bi-info-circle"></i>
          <span>Esta pregunta requiere correccion manual por el profesor.</span></div>`;

      case "subida_archivo":
      case "respuesta_imagen":
        return `<div class="alert alert-info" style="margin-top:8px"><i class="bi-paperclip"></i>
          <span>El estudiante debera subir un archivo como respuesta. Correccion manual.</span></div>`;

      case "editor_codigo":
        return `<div class="form-group"><label class="form-label text-xs text-muted">LENGUAJE</label>
          <select class="form-control"><option>JavaScript</option><option>Python</option><option>Java</option><option>C++</option></select></div>`;

      case "escala_valoracion":
        return `<div><label class="form-label text-xs text-muted">ESCALA (1 al 5)</label>
          <div style="display:flex;gap:8px;margin-top:6px">${[1,2,3,4,5].map(n => `<span class="badge badge-neutral">${n}</span>`).join("")}</div>
          <p class="form-text">Correccion manual por el profesor.</p></div>`;

      case "relacionar_columnas": {
        const pares = p.columna_a
          ? p.columna_a.map((a, i) => [a, (p.columna_b || [])[i] || ""])
          : [["", ""], ["", ""]];
        return `<div>
          <div style="display:flex;gap:8px;margin-bottom:4px">
            <span class="form-label text-xs text-muted" style="flex:1">COLUMNA A (termino)</span>
            <span style="width:20px"></span>
            <span class="form-label text-xs text-muted" style="flex:1">COLUMNA B (definicion)</span>
            <span style="width:32px"></span>
          </div>
          <div class="rel-pares">
            ${pares.map(([a, b]) => `
              <div class="rel-row" style="display:flex;align-items:center;gap:8px;margin-bottom:6px">
                <input type="text" class="form-control rel-a" value="${a}" placeholder="Termino">
                <i class="bi-arrow-right text-muted" style="flex-shrink:0"></i>
                <input type="text" class="form-control rel-b" value="${b}" placeholder="Definicion">
                <button type="button" class="btn btn-ghost btn-sm" onclick="this.closest('.rel-row').remove()" style="padding:3px 7px;flex-shrink:0"><i class="bi-trash text-danger"></i></button>
              </div>`).join("")}
          </div>
          <button type="button" class="btn btn-ghost btn-sm" onclick="QuizForm.agregarRelacion(this)"><i class="bi-plus"></i> Agregar par</button>
        </div>`;
      }

      case "ordenamiento": {
        const items = p.opciones && p.opciones.length ? p.opciones : ["", "", ""];
        return `<div>
          <label class="form-label text-xs text-muted">ITEMS EN ORDEN CORRECTO (el estudiante los vera mezclados)</label>
          <div class="ord-list">
            ${items.map((item, j) => `
              <div class="ord-row" style="display:flex;align-items:center;gap:8px;margin-bottom:6px">
                <span style="color:var(--color-text-muted);font-size:.75rem;font-weight:700;min-width:22px">${j + 1}</span>
                <input type="text" class="form-control ord-item" value="${item}" placeholder="Item ${j + 1}">
                <button type="button" class="btn btn-ghost btn-sm" onclick="this.closest('.ord-row').remove()" style="padding:3px 7px;flex-shrink:0"><i class="bi-trash text-danger"></i></button>
              </div>`).join("")}
          </div>
          <button type="button" class="btn btn-ghost btn-sm" onclick="QuizForm.agregarOrden(this)"><i class="bi-plus"></i> Agregar item</button>
        </div>`;
      }

      case "seleccion_imagen":
        return `<div>
          <div class="form-group">
            <label class="form-label text-xs text-muted">URL DE LA IMAGEN</label>
            <input type="text" class="form-control si-imagen" value="${p.imagen || ""}" placeholder="https://... URL de la imagen">
          </div>
          <div class="form-group">
            <label class="form-label text-xs text-muted">PUNTO CORRECTO (x%, y%)</label>
            <input type="text" class="form-control si-coord" value="${p.respuesta_correcta || ""}" placeholder="Ej: 45,60 — porcentaje desde esquina superior izquierda">
            <p class="form-text">Deja vacio si la correccion sera manual.</p>
          </div>
        </div>`;

      default:
        return `<div class="alert alert-warning"><i class="bi-exclamation-triangle"></i><span>Configura las opciones de este tipo de pregunta.</span></div>`;
    }
  },

  agregarOpcion(btn, tipoInput, name) {
    const wrap = btn.closest(".opciones-wrap");
    const n = wrap.querySelectorAll(".opt-row").length;
    const row = document.createElement("div");
    row.className = "opt-row";
    row.style.cssText = "display:flex;align-items:center;gap:8px;margin-bottom:6px";
    row.innerHTML = `
      <input type="${tipoInput}" class="opt-correct" name="${name}">
      <input type="text" class="form-control opt-text" placeholder="Opcion ${n+1}">`;
    btn.before(row);
  },

  agregarRelacion(btn) {
    const list = btn.previousElementSibling;
    const row = document.createElement("div");
    row.className = "rel-row";
    row.style.cssText = "display:flex;align-items:center;gap:8px;margin-bottom:6px";
    row.innerHTML = `<input type="text" class="form-control rel-a" placeholder="Termino"><i class="bi-arrow-right text-muted" style="flex-shrink:0"></i><input type="text" class="form-control rel-b" placeholder="Definicion"><button type="button" class="btn btn-ghost btn-sm" onclick="this.closest('.rel-row').remove()" style="padding:3px 7px;flex-shrink:0"><i class="bi-trash text-danger"></i></button>`;
    list.appendChild(row);
  },

  agregarOrden(btn) {
    const list = btn.previousElementSibling;
    const n = list.querySelectorAll(".ord-row").length + 1;
    const row = document.createElement("div");
    row.className = "ord-row";
    row.style.cssText = "display:flex;align-items:center;gap:8px;margin-bottom:6px";
    row.innerHTML = `<span style="color:var(--color-text-muted);font-size:.75rem;font-weight:700;min-width:22px">${n}</span><input type="text" class="form-control ord-item" placeholder="Item ${n}"><button type="button" class="btn btn-ghost btn-sm" onclick="this.closest('.ord-row').remove()" style="padding:3px 7px;flex-shrink:0"><i class="bi-trash text-danger"></i></button>`;
    list.appendChild(row);
  },

  /* Lee las preguntas desde el DOM para enviarlas al backend */
  collectPreguntas() {
    const cards = Array.from(document.querySelectorAll("#preguntas-container .preg-card"));
    return cards.map(card => {
      const tipo      = card.dataset.tipo;
      const enunciado = card.querySelector(".preg-enunciado").value.trim();
      const puntaje   = parseFloat(card.querySelector(".preg-puntaje").value) || 1;
      let opciones = [];
      let respuesta_correcta = null;
      let extra = {};

      if (tipo === "opcion_multiple_una" || tipo === "opcion_multiple_varias") {
        const rows = Array.from(card.querySelectorAll(".opt-row"));
        opciones = rows.map(r => r.querySelector(".opt-text").value.trim());
        const marcadas = rows.reduce((acc, r, i) => {
          if (r.querySelector(".opt-correct").checked) acc.push(i);
          return acc;
        }, []);
        respuesta_correcta = tipo === "opcion_multiple_una" ? (marcadas[0] ?? null) : marcadas;
      } else if (tipo === "verdadero_falso") {
        const sel = card.querySelector(".vf-opt:checked");
        respuesta_correcta = sel ? (sel.value === "true") : null;
      } else if (tipo === "respuesta_numerica") {
        const v = card.querySelector(".resp-unica");
        respuesta_correcta = v && v.value !== "" ? parseFloat(v.value) : null;
      } else if (tipo === "completar_espacios" || tipo === "menu_desplegable") {
        const v = card.querySelector(".resp-unica");
        respuesta_correcta = v ? v.value.trim() : null;
      } else if (tipo === "relacionar_columnas") {
        const colA = Array.from(card.querySelectorAll(".rel-a")).map(r => r.value.trim()).filter(Boolean);
        const colB = Array.from(card.querySelectorAll(".rel-b")).map(r => r.value.trim()).filter(Boolean);
        opciones = colA;
        extra = { columna_a: colA, columna_b: colB };
      } else if (tipo === "ordenamiento") {
        opciones = Array.from(card.querySelectorAll(".ord-item")).map(r => r.value.trim()).filter(Boolean);
      } else if (tipo === "seleccion_imagen") {
        const imgEl = card.querySelector(".si-imagen");
        const coordEl = card.querySelector(".si-coord");
        extra = { imagen: imgEl ? imgEl.value.trim() : "" };
        respuesta_correcta = coordEl ? coordEl.value.trim() || null : null;
      }

      return { tipo, enunciado, puntaje, opciones, respuesta_correcta, ...extra };
    });
  },

  async guardar() {
    const curso_id = parseInt(getParams().get("curso_id"));
    const quiz_id  = parseInt(getParams().get("quiz_id")) || null;
    const titulo   = document.getElementById("q-titulo").value.trim();
    const descripcion = document.getElementById("q-descripcion").value.trim();
    const tiempo   = parseInt(document.getElementById("q-tiempo").value) || null;
    const limite   = document.getElementById("q-limite").value;
    if (!titulo || !limite) { Notif("Titulo y fecha limite son obligatorios.", "danger"); return; }

    const preguntas = this.collectPreguntas();
    if (preguntas.some(p => !p.enunciado)) { Notif("Todas las preguntas necesitan un enunciado.", "danger"); return; }

    const payload = { titulo, descripcion, tiempo_limite_min: tiempo, fecha_limite: limite, preguntas };

    try {
      if (quiz_id) {
        await API.actualizarQuiz(quiz_id, payload);
        Notif("Quiz actualizado.");
      } else {
        await API.crearQuiz(curso_id, payload);
        Notif("Quiz creado.");
      }
      setTimeout(() => { window.location.href = `curso.html?id=${curso_id}`; }, 800);
    } catch (e) { Notif(e.message, "danger"); }
  }
};

/* ── QUIZ RESULTADOS ─────────────────────────────────────── */
const QuizResultados = {
  async init() {
    const u = initProfesorPage("Resultados del Quiz");
    if (!u) return;
    const quiz_id  = parseInt(getParams().get("quiz_id"));
    const curso_id = parseInt(getParams().get("curso_id"));

    let quiz, estudiantes = [], respuestas = [];
    try {
      [quiz, estudiantes, respuestas] = await Promise.all([
        API.quizDetalle(quiz_id),
        API.inscripciones(curso_id).then(ins => ins.filter(i => i.rol_en_curso === "ESTUDIANTE")),
        API.respuestasQuiz(quiz_id)
      ]);
    } catch (e) { Notif(e.message, "danger"); return; }

    document.getElementById("quiz-titulo").textContent  = quiz.titulo;
    document.getElementById("quiz-preguntas").textContent = `${(quiz.preguntas || []).length} preguntas`;
    document.getElementById("btn-volver").href = `curso.html?id=${curso_id}`;

    const minimo = parseInt(localStorage.getItem("porcentaje_minimo") || "60");
    const respPorUsuario = {};
    respuestas.forEach(r => { respPorUsuario[r.usuario] = r; });

    const tbody = document.getElementById("tabla-resultados");
    if (!tbody) return;
    tbody.innerHTML = estudiantes.map(e => {
      const resp = respPorUsuario[e.usuario];
      const notaBadge = resp
        ? `<span class="badge badge-${parseFloat(resp.nota_automatica) >= minimo ? "success" : "warning"}">${resp.nota_automatica} pts</span>`
        : `<span class="badge badge-neutral">Sin responder</span>`;
      return `
        <tr>
          <td>
            <div style="display:flex;align-items:center;gap:8px">
              <div class="avatar avatar-sm">${inicialesDe(e.usuario_nombre)}</div>
              <span class="fw-semibold text-sm">${e.usuario_nombre}</span>
            </div>
          </td>
          <td>${resp ? formatFecha(resp.fecha) : "—"}</td>
          <td>${notaBadge}</td>
          <td>${resp && resp.nota_manual !== null ? `<span class="badge badge-primary">${resp.nota_manual} pts</span>` : `<span class="text-muted text-sm">—</span>`}</td>
        </tr>`;
    }).join("");
  }
};
