/* ── GUARD ───────────────────────────────────────────────── */
function initAdminPage(titulo) {
  const usuario = Auth.getUsuarioActivo();
  if (!usuario || usuario.rol !== "ADMIN") {
    window.location.href = BASE_PATH + "index.html";
    return null;
  }
  Sidebar.inject(usuario, window.location.pathname);
  const t = document.getElementById("topbar-title");
  if (t) t.textContent = titulo;
  return usuario;
}

/* Facultad administrada por este usuario (Facultad.admin === usuario.id) */
async function getFacultadAdmin(usuario) {
  const facs = await API.facultades();
  return facs.find(f => f.admin === usuario.id) || null;
}

/* Cuenta estudiantes unicos a lo largo de una lista de cursos */
async function contarEstudiantesUnicos(cursos) {
  const listas = await Promise.all(cursos.map(c => API.inscripciones(c.id)));
  const ids = new Set();
  listas.forEach(ins => ins
    .filter(i => i.rol_en_curso === "ESTUDIANTE")
    .forEach(i => ids.add(i.usuario)));
  return ids.size;
}

/* ── UTILS (reutilizadas del superadmin) ─────────────────── */
function badgeEstado(estado) {
  return estado === "activo"
    ? `<span class="badge badge-success"><i class="bi-check-circle"></i> Activo</span>`
    : `<span class="badge badge-danger"><i class="bi-x-circle"></i> Inactivo</span>`;
}
function badgeCursoEstado(estado) {
  return estado === "activo"
    ? `<span class="badge badge-success">Activo</span>`
    : `<span class="badge badge-neutral">Archivado</span>`;
}
function formatFecha(f) {
  if (!f) return "—";
  return new Date(f).toLocaleDateString("es-EC", { day: "2-digit", month: "short", year: "numeric" });
}

/* ── DASHBOARD ADMIN ─────────────────────────────────────── */
const AdminDashboard = {
  async init() {
    const usuario = initAdminPage("Dashboard");
    if (!usuario) return;
    try {
      const [facultad, cursosF] = await Promise.all([
        getFacultadAdmin(usuario), API.cursos()
      ]);

      const nombreFac = document.getElementById("nombre-facultad");
      if (nombreFac) nombreFac.textContent = facultad ? facultad.nombre : "Mi Facultad";

      const activos = cursosF.filter(c => c.estado === "activo").length;

      /* Estudiantes y profesores unicos */
      const inscLists = await Promise.all(cursosF.map(c => API.inscripciones(c.id)));
      const estudiantes = new Set();
      const profesores  = new Set();
      inscLists.forEach(ins => ins.forEach(i => {
        if (i.rol_en_curso === "ESTUDIANTE") estudiantes.add(i.usuario);
        if (i.rol_en_curso === "PROFESOR")   profesores.add(i.usuario);
      }));

      document.getElementById("kpi-cursos").textContent      = activos;
      document.getElementById("kpi-estudiantes").textContent = estudiantes.size;
      document.getElementById("kpi-profesores").textContent  = profesores.size;
      document.getElementById("kpi-tasa").textContent        = "68%";

      const tbody  = document.getElementById("tabla-cursos-recientes");
      const mobile = document.getElementById("lista-cursos-recientes-mobile");
      if (!tbody) return;
      const recientes = cursosF.slice(0, 5);
      if (!recientes.length) {
        tbody.innerHTML = `<tr><td colspan="4"><div class="empty-state"><i class="bi-book"></i><p>Sin cursos en esta facultad.</p></div></td></tr>`;
        if (mobile) mobile.innerHTML = `<div class="empty-state"><i class="bi-book"></i><p>Sin cursos.</p></div>`;
        return;
      }
      tbody.innerHTML = recientes.map(c => `
        <tr>
          <td class="fw-semibold text-sm">${c.nombre}</td>
          <td class="text-sm">${c.profesor_nombre || "—"}</td>
          <td>${badgeCursoEstado(c.estado)}</td>
          <td class="text-sm text-muted">${formatFecha(c.fecha_fin)}</td>
        </tr>`).join("");
      if (mobile) {
        mobile.innerHTML = recientes.map(c => `
          <div class="mob-card">
            <div class="mob-card-head">
              <div><strong>${c.nombre}</strong></div>
              ${badgeCursoEstado(c.estado)}
            </div>
            <div class="mob-card-row">
              <span class="mob-card-lbl">Profesor</span>
              <span class="mob-card-val">${c.profesor_nombre || "—"}</span>
            </div>
            <div class="mob-card-row">
              <span class="mob-card-lbl">Fecha fin</span>
              <span class="mob-card-val">${formatFecha(c.fecha_fin)}</span>
            </div>
          </div>`).join("");
      }
    } catch (e) { AdminNotif.show(e.message, "danger"); }
  }
};

/* ── USUARIOS ADMIN ──────────────────────────────────────── */
const AdminUsuarios = {
  filtro: "",
  usuario: null,
  _data: [],

  async init() {
    const usuario = initAdminPage("Usuarios de Facultad");
    if (!usuario) return;
    this.usuario = usuario;
    const buscador = document.getElementById("buscador");
    if (buscador) buscador.addEventListener("input", e => {
      this.filtro = e.target.value.toLowerCase();
      this.renderTabla();
    });
    try {
      this._data = await this.getUsuariosFacultad();
      this.renderTabla();
    } catch (e) { AdminNotif.show(e.message, "danger"); }
  },

  async getUsuariosFacultad() {
    const [usuarios, cursosFac] = await Promise.all([API.usuarios(), API.cursos()]);
    if (!cursosFac.length) return usuarios.filter(u => u.rol === "USER");
    const inscLists = await Promise.all(cursosFac.map(c => API.inscripciones(c.id)));
    const ids = new Set();
    inscLists.forEach(ins => ins.forEach(i => ids.add(i.usuario)));
    return usuarios.filter(u => ids.has(u.id));
  },

  renderTabla() {
    const tbody  = document.getElementById("tabla-usuarios");
    const mobile = document.getElementById("lista-usuarios-mobile");
    if (!tbody) return;
    const lista = this._data.filter(u =>
      u.nombres.toLowerCase().includes(this.filtro) ||
      u.apellidos.toLowerCase().includes(this.filtro) ||
      u.identificacion.includes(this.filtro)
    );
    if (!lista.length) {
      tbody.innerHTML = `<tr><td colspan="6"><div class="empty-state"><i class="bi-people"></i><p>No se encontraron usuarios.</p></div></td></tr>`;
      if (mobile) mobile.innerHTML = `<div class="empty-state"><i class="bi-people"></i><p>No se encontraron usuarios.</p></div>`;
      return;
    }
    tbody.innerHTML = lista.map(u => `
      <tr>
        <td>
          <div style="display:flex;align-items:center;gap:8px">
            <div class="avatar avatar-sm">${u.iniciales}</div>
            <div>
              <div class="fw-semibold text-sm">${u.nombres} ${u.apellidos}</div>
              <div class="text-xs text-muted">${u.correo}</div>
            </div>
          </div>
        </td>
        <td class="text-sm">${u.identificacion}</td>
        <td class="text-sm">${u.celular}</td>
        <td class="text-sm">${u.estado_civil}</td>
        <td>${badgeEstado(u.estado)}</td>
        <td>
          <div class="table-actions">
            <button class="btn btn-ghost btn-sm" onclick="AdminModalUsuario.abrir(${u.id})" title="Editar">
              <i class="bi-pencil"></i>
            </button>
            <button class="btn btn-ghost btn-sm" onclick="AdminUsuarios.toggleEstado(${u.id})" title="Cambiar estado">
              <i class="bi-toggle-on"></i>
            </button>
          </div>
        </td>
      </tr>`).join("");
    if (mobile) {
      mobile.innerHTML = lista.map(u => `
        <div class="mob-card">
          <div class="mob-card-head">
            <div style="display:flex;align-items:center;gap:10px">
              <div class="avatar">${u.iniciales}</div>
              <div>
                <strong>${u.nombres} ${u.apellidos}</strong>
                <span class="sub">${u.correo}</span>
              </div>
            </div>
            ${badgeEstado(u.estado)}
          </div>
          <div class="mob-card-row">
            <span class="mob-card-lbl">Identificacion</span>
            <span class="mob-card-val">${u.identificacion}</span>
          </div>
          <div class="mob-card-row">
            <span class="mob-card-lbl">Celular</span>
            <span class="mob-card-val">${u.celular}</span>
          </div>
          <div class="mob-card-row">
            <span class="mob-card-lbl">Estado Civil</span>
            <span class="mob-card-val">${u.estado_civil}</span>
          </div>
          <div class="mob-card-actions">
            <button class="btn btn-ghost btn-sm" onclick="AdminModalUsuario.abrir(${u.id})"><i class="bi-pencil"></i> Editar</button>
            <button class="btn btn-ghost btn-sm" onclick="AdminUsuarios.toggleEstado(${u.id})"><i class="bi-toggle-on"></i></button>
          </div>
        </div>`).join("");
    }
  },

  async toggleEstado(id) {
    try {
      await API.toggleEstado(id);
      const u = this._data.find(x => x.id === id);
      if (u) u.estado = u.estado === "activo" ? "inactivo" : "activo";
      this.renderTabla();
      AdminNotif.show("Estado actualizado.", "success");
    } catch (e) { AdminNotif.show(e.message, "danger"); }
  }
};

/* ── MODAL USUARIO (Admin — campos del modulo Clientes) ──── */
const AdminModalUsuario = {
  usuarioId: null,

  abrir(id) {
    this.usuarioId = id;
    const u = AdminUsuarios._data.find(x => x.id === id);
    if (!u) return;
    document.getElementById("af-nombres").value       = u.nombres;
    document.getElementById("af-apellidos").value     = u.apellidos;
    document.getElementById("af-identificacion").value= u.identificacion;
    document.getElementById("af-celular").value       = u.celular;
    document.getElementById("af-telefono").value      = u.telefono || "";
    document.getElementById("af-correo").value        = u.correo;
    document.getElementById("af-direccion").value     = u.direccion || "";
    document.getElementById("af-estado-civil").value  = u.estado_civil;
    document.getElementById("af-estado").value        = u.estado;
    document.getElementById("modal-admin-usuario").classList.add("open");
  },

  cerrar() {
    document.getElementById("modal-admin-usuario").classList.remove("open");
  },

  async guardar() {
    const campos = {
      nombres:        document.getElementById("af-nombres").value.trim(),
      apellidos:      document.getElementById("af-apellidos").value.trim(),
      identificacion: document.getElementById("af-identificacion").value.trim(),
      celular:        document.getElementById("af-celular").value.trim(),
      telefono:       document.getElementById("af-telefono").value.trim() || null,
      correo:         document.getElementById("af-correo").value.trim(),
      direccion:      document.getElementById("af-direccion").value.trim() || null,
      estado_civil:   document.getElementById("af-estado-civil").value,
      estado:         document.getElementById("af-estado").value,
    };
    try {
      const updated = await API.actualizarUsuario(this.usuarioId, campos);
      const idx = AdminUsuarios._data.findIndex(x => x.id === this.usuarioId);
      if (idx !== -1) AdminUsuarios._data[idx] = { ...AdminUsuarios._data[idx], ...updated };
      this.cerrar();
      AdminUsuarios.renderTabla();
      AdminNotif.show("Usuario actualizado correctamente.", "success");
    } catch (e) { AdminNotif.show(e.message, "danger"); }
  }
};

/* ── CURSOS ADMIN ────────────────────────────────────────── */
const AdminCursos = {
  usuario: null,
  facultadId: null,
  _data: [],
  _usuarios: [],

  async init() {
    const usuario = initAdminPage("Cursos de Facultad");
    if (!usuario) return;
    this.usuario = usuario;
    try {
      const [facultad, cursos, usuarios] = await Promise.all([
        getFacultadAdmin(usuario), API.cursos(), API.usuarios()
      ]);
      this.facultadId = facultad ? facultad.id : null;
      this._usuarios  = usuarios.filter(u => u.rol === "USER");
      this._data      = facultad ? cursos.filter(c => c.facultad === facultad.id) : cursos;
      this.renderTabla();
    } catch (e) { AdminNotif.show(e.message, "danger"); }
  },

  renderTabla() {
    const tbody  = document.getElementById("tabla-cursos");
    const mobile = document.getElementById("lista-cursos-mobile");
    if (!tbody) return;
    if (!this._data.length) {
      tbody.innerHTML = `<tr><td colspan="7"><div class="empty-state"><i class="bi-book"></i><p>No hay cursos en esta facultad.</p></div></td></tr>`;
      if (mobile) mobile.innerHTML = `<div class="empty-state"><i class="bi-book"></i><p>No hay cursos.</p></div>`;
      return;
    }
    tbody.innerHTML = this._data.map(c => `
      <tr>
        <td>
          <div class="fw-semibold text-sm">${c.nombre}</div>
          <div class="text-xs text-muted">${c.codigo}</div>
        </td>
        <td class="text-sm">${c.profesor_nombre || "—"}</td>
        <td class="text-sm">${c.total_estudiantes}</td>
        <td class="text-sm">${formatFecha(c.fecha_inicio)}</td>
        <td class="text-sm">${formatFecha(c.fecha_fin)}</td>
        <td>${badgeCursoEstado(c.estado)}</td>
        <td>
          <div class="table-actions">
            <button class="btn btn-ghost btn-sm" onclick="AdminModalCurso.abrir(${c.id})" title="Editar"><i class="bi-pencil"></i></button>
            <button class="btn btn-ghost btn-sm" onclick="AdminCursos.eliminar(${c.id})" title="Eliminar" style="color:var(--color-danger)"><i class="bi-trash"></i></button>
          </div>
        </td>
      </tr>`).join("");
    if (mobile) {
      mobile.innerHTML = this._data.map(c => `
        <div class="mob-card">
          <div class="mob-card-head">
            <div>
              <strong>${c.nombre}</strong>
              <span class="sub">${c.codigo}</span>
            </div>
            ${badgeCursoEstado(c.estado)}
          </div>
          <div class="mob-card-row">
            <span class="mob-card-lbl">Profesor</span>
            <span class="mob-card-val">${c.profesor_nombre || "—"}</span>
          </div>
          <div class="mob-card-row">
            <span class="mob-card-lbl">Estudiantes</span>
            <span class="mob-card-val">${c.total_estudiantes}</span>
          </div>
          <div class="mob-card-row">
            <span class="mob-card-lbl">Inicio</span>
            <span class="mob-card-val">${formatFecha(c.fecha_inicio)}</span>
          </div>
          <div class="mob-card-row">
            <span class="mob-card-lbl">Fin</span>
            <span class="mob-card-val">${formatFecha(c.fecha_fin)}</span>
          </div>
          <div class="mob-card-actions">
            <button class="btn btn-ghost btn-sm" onclick="AdminModalCurso.abrir(${c.id})"><i class="bi-pencil"></i> Editar</button>
            <button class="btn btn-ghost btn-sm" onclick="AdminCursos.eliminar(${c.id})" style="color:var(--color-danger)"><i class="bi-trash"></i> Eliminar</button>
          </div>
        </div>`).join("");
    }
  },

  async eliminar(id) {
    if (!confirm("¿Eliminar este curso? Esta accion no se puede deshacer.")) return;
    try {
      await API.eliminarCurso(id);
      this._data = this._data.filter(c => c.id !== id);
      this.renderTabla();
      AdminNotif.show("Curso eliminado.", "success");
    } catch (e) { AdminNotif.show(e.message, "danger"); }
  }
};

/* ── MODAL CURSO ─────────────────────────────────────────── */
const AdminModalCurso = {
  cursoId: null,

  abrir(id = null) {
    this.cursoId = id;
    const modal  = document.getElementById("modal-curso");
    const titulo = document.getElementById("modal-curso-titulo");
    if (!modal) return;
    const sel = document.getElementById("cf-profesor");
    sel.innerHTML = `<option value="">Sin asignar</option>` +
      AdminCursos._usuarios.map(u => `<option value="${u.id}">${u.nombres} ${u.apellidos}</option>`).join("");
    if (id) {
      const c = AdminCursos._data.find(x => x.id === id);
      if (!c) return;
      titulo.textContent = "Editar Curso";
      document.getElementById("cf-nombre").value       = c.nombre;
      document.getElementById("cf-codigo").value       = c.codigo;
      document.getElementById("cf-descripcion").value  = c.descripcion || "";
      document.getElementById("cf-profesor").value     = c.profesor_id || "";
      document.getElementById("cf-fecha-inicio").value = c.fecha_inicio || "";
      document.getElementById("cf-fecha-fin").value    = c.fecha_fin || "";
      document.getElementById("cf-estado").value       = c.estado;
      document.getElementById("grupo-estado").style.display = "";
    } else {
      titulo.textContent = "Nuevo Curso";
      document.getElementById("form-curso").reset();
      document.getElementById("grupo-estado").style.display = "none";
    }
    modal.classList.add("open");
  },

  cerrar() {
    const modal = document.getElementById("modal-curso");
    if (modal) modal.classList.remove("open");
  },

  async guardar() {
    const nombre      = document.getElementById("cf-nombre").value.trim();
    const codigo      = document.getElementById("cf-codigo").value.trim();
    const descripcion = document.getElementById("cf-descripcion").value.trim() || null;
    const profesorId  = parseInt(document.getElementById("cf-profesor").value) || null;
    const fechaInicio = document.getElementById("cf-fecha-inicio").value;
    const fechaFin    = document.getElementById("cf-fecha-fin").value;
    const estado      = document.getElementById("cf-estado").value;
    if (!nombre || !codigo || !fechaInicio || !fechaFin) {
      AdminNotif.show("Nombre, codigo y fechas son obligatorios.", "danger"); return;
    }
    const payload = {
      nombre, codigo, descripcion,
      profesor_id: profesorId,
      fecha_inicio: fechaInicio,
      fecha_fin: fechaFin,
      facultad: AdminCursos.facultadId,
      ...(this.cursoId ? { estado } : {})
    };
    try {
      if (this.cursoId) {
        const updated = await API.actualizarCurso(this.cursoId, payload);
        const idx = AdminCursos._data.findIndex(x => x.id === this.cursoId);
        if (idx !== -1) AdminCursos._data[idx] = updated;
        AdminNotif.show("Curso actualizado.", "success");
      } else {
        const nuevo = await API.crearCurso(payload);
        AdminCursos._data.push(nuevo);
        AdminNotif.show("Curso creado.", "success");
      }
      this.cerrar();
      AdminCursos.renderTabla();
    } catch (e) { AdminNotif.show(e.message, "danger"); }
  }
};

/* ── REPORTES ADMIN ──────────────────────────────────────── */
const AdminReportes = {
  usuario: null,

  async init() {
    const usuario = initAdminPage("Reportes");
    if (!usuario) return;
    this.usuario = usuario;
    try {
      const [facultad, cursos] = await Promise.all([
        getFacultadAdmin(usuario), API.cursos()
      ]);
      const fNombre = document.getElementById("nombre-facultad");
      if (fNombre) fNombre.textContent = facultad ? facultad.nombre : "Mi Facultad";

      const estudiantesUnicos = await contarEstudiantesUnicos(cursos);
      document.getElementById("r-cursos").textContent      = cursos.length;
      document.getElementById("r-estudiantes").textContent = estudiantesUnicos;

      const tbody  = document.getElementById("tabla-reportes");
      const mobile = document.getElementById("lista-reportes-mobile");
      if (!tbody) return;
      if (!cursos.length) {
        tbody.innerHTML = `<tr><td colspan="4"><div class="empty-state"><i class="bi-bar-chart"></i><p>Sin datos para esta facultad.</p></div></td></tr>`;
        if (mobile) mobile.innerHTML = `<div class="empty-state"><i class="bi-bar-chart"></i><p>Sin datos.</p></div>`;
        return;
      }
      const filas = cursos.map(c => {
        const tasa  = Math.floor(Math.random() * 30) + 60;
        const badge = tasa >= 70
          ? `<span class="badge badge-success">${tasa}%</span>`
          : `<span class="badge badge-warning">${tasa}%</span>`;
        return { c, badge };
      });
      tbody.innerHTML = filas.map(({ c, badge }) => `
        <tr>
          <td>
            <div class="fw-semibold text-sm">${c.nombre}</div>
            <div class="text-xs text-muted">${c.codigo}</div>
          </td>
          <td class="text-sm">${c.profesor_nombre || "—"}</td>
          <td class="text-sm">${c.total_estudiantes}</td>
          <td>${badge} <span class="text-xs text-muted">aprobacion</span></td>
        </tr>`).join("");
      if (mobile) {
        mobile.innerHTML = filas.map(({ c, badge }) => `
          <div class="mob-card">
            <div class="mob-card-head">
              <div>
                <strong>${c.nombre}</strong>
                <span class="sub">${c.codigo}</span>
              </div>
              ${badge}
            </div>
            <div class="mob-card-row">
              <span class="mob-card-lbl">Profesor</span>
              <span class="mob-card-val">${c.profesor_nombre || "—"}</span>
            </div>
            <div class="mob-card-row">
              <span class="mob-card-lbl">Estudiantes</span>
              <span class="mob-card-val">${c.total_estudiantes}</span>
            </div>
          </div>`).join("");
      }
    } catch (e) { AdminNotif.show(e.message, "danger"); }
  }
};

/* ── NOTIFICACIONES ──────────────────────────────────────── */
const AdminNotif = {
  show(mensaje, tipo = "success") {
    let n = document.getElementById("admin-notif");
    if (!n) {
      n = document.createElement("div");
      n.id = "admin-notif";
      n.style.cssText = `position:fixed;bottom:24px;right:24px;z-index:9999;max-width:340px;
        padding:14px 18px;border-radius:10px;font-size:.875rem;font-family:inherit;
        display:flex;align-items:center;gap:10px;box-shadow:0 4px 20px rgba(0,0,0,.15);
        animation:fadeIn .2s ease;transition:opacity .3s ease;`;
      document.body.appendChild(n);
    }
    const isDark = document.documentElement.getAttribute("data-theme") === "dark";
    const colores = isDark ? {
      success:{ bg:"#064E3B", color:"#6EE7B7", border:"#059669", icon:"check-circle" },
      danger: { bg:"#450A0A", color:"#FCA5A5", border:"#DC2626", icon:"exclamation-circle" }
    } : {
      success:{ bg:"#ECFDF5", color:"#065F46", border:"#059669", icon:"check-circle" },
      danger: { bg:"#FEF2F2", color:"#991B1B", border:"#DC2626", icon:"exclamation-circle" }
    };
    const c = colores[tipo] || colores.success;
    n.style.background = c.bg; n.style.color = c.color; n.style.borderLeft = `4px solid ${c.border}`;
    n.innerHTML = `<i class="bi-${c.icon}"></i><span>${mensaje}</span>`;
    n.style.opacity = "1";
    n.style.pointerEvents = "auto";
    clearTimeout(this._t);
    clearTimeout(this._r);
    this._t = setTimeout(() => {
      n.style.opacity = "0";
      n.style.pointerEvents = "none";
      this._r = setTimeout(() => n.remove(), 310);
    }, 3000);
  }
};
