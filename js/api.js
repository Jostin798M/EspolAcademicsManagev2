/* ── CAPA DE DATOS (localStorage) — sin backend ─────────────
   Reemplaza por completo la API Django REST.
   Todos los métodos retornan Promises para mantener
   compatibilidad con el código async/await existente.
   Los datos iniciales provienen de js/data/mockdata.js (DB).
──────────────────────────────────────────────────────────── */

const STORE_KEY = "espol_db";

/* ── Persistencia ────────────────────────────────────────── */
function _load() {
  try { const r = localStorage.getItem(STORE_KEY); return r ? JSON.parse(r) : null; } catch { return null; }
}
function _save(d) { localStorage.setItem(STORE_KEY, JSON.stringify(d)); }

function _db() {
  let d = _load();
  if (!d) {
    d = {
      usuarios: DB.usuarios.map(u => ({ ...u, estado_civil: u.estadoCivil || u.estado_civil || "soltero" })),
      facultades: DB.facultades.map(f => ({ ...f })),
      cursos: DB.cursos.map(c => ({ ...c })),
      inscripciones: DB.inscripciones.map(i => ({ ...i })),
      modulos: DB.modulos.map(m => ({ ...m })),
      materiales: DB.materiales.map(m => ({ ...m })),
      progreso_modulos: DB.progreso_modulos.map(p => ({ ...p })),
      tareas: DB.tareas.map(t => ({ ...t })),
      entregas: DB.entregas.map(e => ({ ...e })),
      quizzes: DB.quizzes.map(q => ({ ...q })),
      respuestas_quiz: DB.respuestas_quiz.map(r => ({ ...r })),
      _seq: { usuarios:20, facultades:20, cursos:20, inscripciones:20, modulos:20,
               materiales:20, tareas:20, entregas:20, quizzes:20, respuestas_quiz:20 }
    };
    _save(d);
  }
  return d;
}

function _nextId(d, key) {
  if (!d._seq) d._seq = {};
  d._seq[key] = (d._seq[key] || 10) + 1;
  return d._seq[key];
}

function _uid() { return parseInt(sessionStorage.getItem("usuario_id")) || null; }
function _rolActivo() { return sessionStorage.getItem("rol_activo"); }

/* ── Campos calculados ───────────────────────────────────── */
function _enrichUser(u) {
  return {
    ...u,
    estado_civil: u.estado_civil || u.estadoCivil || "soltero",
    iniciales: (((u.nombres||"")[0]||"") + ((u.apellidos||"")[0]||"")).toUpperCase(),
    nombre_completo: `${u.nombres} ${u.apellidos}`
  };
}

function _enrichCurso(c, d, userId) {
  const fac  = d.facultades.find(f => f.id === c.facultad_id) || null;
  const prof = d.usuarios.find(u => u.id === c.profesor_id)   || null;
  const estCount = d.inscripciones.filter(i => i.curso_id === c.id && i.rol_en_curso === "ESTUDIANTE").length;
  const miInsc   = d.inscripciones.find(i => i.curso_id === c.id && i.usuario_id === userId);
  return {
    ...c,
    facultad: c.facultad_id,
    facultad_nombre: fac  ? fac.nombre  : "—",
    facultad_codigo: fac  ? fac.codigo  : "—",
    profesor_nombre: prof ? `${prof.nombres} ${prof.apellidos}` : "—",
    total_estudiantes: estCount,
    mi_rol: miInsc ? miInsc.rol_en_curso : null
  };
}

function _enrichInscripcion(i, d) {
  const u = d.usuarios.find(u => u.id === i.usuario_id) || {};
  return { ...i, usuario: i.usuario_id,
    usuario_nombre: `${u.nombres||""} ${u.apellidos||""}`.trim(),
    usuario_correo: u.correo || "" };
}

function _enrichFacultad(f, d) {
  const admin = d.usuarios.find(u => u.id === f.admin_id) || null;
  return { ...f, admin: f.admin_id,
    admin_nombre: admin ? `${admin.nombres} ${admin.apellidos}` : null };
}

function _enrichModulo(m, d, userId) {
  const mats = d.materiales.filter(mat => mat.modulo_id === m.id);
  const prog = d.progreso_modulos.find(p => p.usuario_id === userId && p.modulo_id === m.id);
  return { ...m, materiales: mats, completado: prog ? prog.completado : false };
}

function _enrichQuiz(q) {
  const preguntas = q.preguntas || [];
  return { ...q, total_preguntas: preguntas.length,
    puntaje_total: preguntas.reduce((a, p) => a + (p.puntaje || 0), 0) };
}

function _autoGrade(quiz, respuestas) {
  const autoTypes = ["opcion_multiple_una","opcion_multiple_varias","verdadero_falso",
    "completar_espacios","relacionar_columnas","ordenamiento","respuesta_numerica",
    "menu_desplegable","seleccion_imagen"];
  let pts = 0;
  (quiz.preguntas || []).forEach(p => {
    if (!autoTypes.includes(p.tipo)) return;
    const r = respuestas[p.id];
    if (p.tipo === "opcion_multiple_una") {
      if (r !== null && r !== undefined && parseInt(r) === p.respuesta_correcta) pts += p.puntaje;
    } else if (p.tipo === "verdadero_falso") {
      const val = r === "Verdadero" ? true : r === "Falso" ? false : r;
      if (val === p.respuesta_correcta) pts += p.puntaje;
    } else if (p.tipo === "completar_espacios" || p.tipo === "menu_desplegable") {
      if ((r||"").trim().toLowerCase() === (p.respuesta_correcta||"").trim().toLowerCase()) pts += p.puntaje;
    } else if (p.tipo === "respuesta_numerica") {
      if (parseFloat(r) === parseFloat(p.respuesta_correcta)) pts += p.puntaje;
    }
  });
  return pts;
}

/* ── API principal ───────────────────────────────────────── */
const API = {
  _ok: v => Promise.resolve(v),
  _err: m => Promise.reject(new Error(m)),

  /* AUTH ────────────────────────────────────────────────── */
  login(correo, password) {
    const d = _db();
    const u = d.usuarios.find(u => u.correo === correo && u.password === password);
    if (!u) return this._err("Correo o contrasena incorrectos.");
    if (u.estado !== "activo") return this._err("La cuenta esta inactiva.");
    let rol_activo = null;
    if (u.rol === "USER") {
      const esProf = d.inscripciones.some(i => i.usuario_id === u.id && i.rol_en_curso === "PROFESOR");
      rol_activo = esProf ? "PROFESOR" : "ESTUDIANTE";
    }
    return this._ok({ usuario: _enrichUser(u), rol_activo });
  },
  logout() { return this._ok(null); },
  me() {
    const d = _db();
    const u = d.usuarios.find(u => u.id === _uid());
    return u ? this._ok(_enrichUser(u)) : this._err("No autenticado.");
  },

  /* USUARIOS ────────────────────────────────────────────── */
  usuarios() {
    return this._ok(_db().usuarios.map(_enrichUser));
  },
  usuarioDetalle(id) {
    const u = _db().usuarios.find(u => u.id === id);
    return u ? this._ok(_enrichUser(u)) : this._err("Usuario no encontrado.");
  },
  crearUsuario(data) {
    const d = _db();
    const nuevo = { fecha_registro: new Date().toISOString().slice(0,10), ...data, id: _nextId(d,"usuarios") };
    d.usuarios.push(nuevo);
    _save(d);
    return this._ok(_enrichUser(nuevo));
  },
  actualizarUsuario(id, data) {
    const d = _db();
    const idx = d.usuarios.findIndex(u => u.id === id);
    if (idx === -1) return this._err("Usuario no encontrado.");
    d.usuarios[idx] = { ...d.usuarios[idx], ...data };
    _save(d);
    return this._ok(_enrichUser(d.usuarios[idx]));
  },
  toggleEstado(id) {
    const d = _db();
    const u = d.usuarios.find(u => u.id === id);
    if (!u) return this._err("Usuario no encontrado.");
    u.estado = u.estado === "activo" ? "inactivo" : "activo";
    _save(d);
    return this._ok(_enrichUser(u));
  },

  /* FACULTADES ──────────────────────────────────────────── */
  facultades() {
    const d = _db();
    return this._ok(d.facultades.map(f => _enrichFacultad(f, d)));
  },
  crearFacultad(data) {
    const d = _db();
    const nueva = { id: _nextId(d,"facultades"), codigo: data.codigo, nombre: data.nombre, admin_id: data.admin||null };
    d.facultades.push(nueva);
    _save(d);
    return this._ok(_enrichFacultad(nueva, d));
  },
  actualizarFacultad(id, data) {
    const d = _db();
    const idx = d.facultades.findIndex(f => f.id === id);
    if (idx === -1) return this._err("Facultad no encontrada.");
    d.facultades[idx] = { ...d.facultades[idx], codigo: data.codigo, nombre: data.nombre, admin_id: data.admin||null };
    _save(d);
    return this._ok(_enrichFacultad(d.facultades[idx], d));
  },

  /* CURSOS ──────────────────────────────────────────────── */
  cursos() {
    const d = _db(); const uid = _uid();
    return this._ok(d.cursos.map(c => _enrichCurso(c, d, uid)));
  },
  cursoDetalle(id) {
    const d = _db();
    const c = d.cursos.find(c => c.id === id);
    return c ? this._ok(_enrichCurso(c, d, _uid())) : this._err("Curso no encontrado.");
  },
  eliminarCurso(id) {
    const d = _db();
    const idx = d.cursos.findIndex(c => c.id === id);
    if (idx === -1) return this._err("Curso no encontrado.");
    d.cursos.splice(idx, 1);
    _save(d);
    return this._ok(null);
  },
  crearCurso(data) {
    const d = _db(); const uid = _uid();
    const nuevo = { id: _nextId(d,"cursos"), ...data, facultad_id: data.facultad, profesor_id: data.profesor_id || uid, estado: data.estado || "activo" };
    d.cursos.push(nuevo);
    d.inscripciones.push({ id: _nextId(d,"inscripciones"), usuario_id: uid, curso_id: nuevo.id,
      rol_en_curso: "PROFESOR", fecha: new Date().toISOString().slice(0,10) });
    _save(d);
    return this._ok(_enrichCurso(nuevo, d, uid));
  },
  actualizarCurso(id, data) {
    const d = _db(); const uid = _uid();
    const idx = d.cursos.findIndex(c => c.id === id);
    if (idx === -1) return this._err("Curso no encontrado.");
    d.cursos[idx] = {
      ...d.cursos[idx], ...data,
      facultad_id: data.facultad || d.cursos[idx].facultad_id,
      profesor_id: data.profesor_id !== undefined ? (data.profesor_id || null) : d.cursos[idx].profesor_id
    };
    _save(d);
    return this._ok(_enrichCurso(d.cursos[idx], d, uid));
  },

  /* INSCRIPCIONES ───────────────────────────────────────── */
  inscripciones(cursoId) {
    const d = _db();
    return this._ok(d.inscripciones.filter(i => i.curso_id === cursoId).map(i => _enrichInscripcion(i, d)));
  },
  inscribir(cursoId, usuarioId, rol = "ESTUDIANTE") {
    const d = _db();
    if (d.inscripciones.find(i => i.curso_id === cursoId && i.usuario_id === usuarioId))
      return this._err("El usuario ya esta inscrito.");
    const nueva = { id: _nextId(d,"inscripciones"), usuario_id: usuarioId, curso_id: cursoId,
      rol_en_curso: rol, fecha: new Date().toISOString().slice(0,10) };
    d.inscripciones.push(nueva);
    _save(d);
    return this._ok(_enrichInscripcion(nueva, d));
  },
  desinscribir(cursoId, usuarioId) {
    const d = _db();
    const idx = d.inscripciones.findIndex(i => i.curso_id === cursoId && i.usuario_id === usuarioId);
    if (idx === -1) return this._err("Inscripcion no encontrada.");
    d.inscripciones.splice(idx, 1);
    _save(d);
    return this._ok(null);
  },

  /* MODULOS ─────────────────────────────────────────────── */
  modulos(cursoId) {
    const d = _db(); const uid = _uid();
    return this._ok(d.modulos.filter(m => m.curso_id === cursoId)
      .sort((a, b) => a.orden - b.orden).map(m => _enrichModulo(m, d, uid)));
  },
  crearModulo(cursoId, data) {
    const d = _db(); const uid = _uid();
    const nuevo = { id: _nextId(d,"modulos"), curso_id: cursoId, ...data };
    d.modulos.push(nuevo);
    _save(d);
    return this._ok(_enrichModulo(nuevo, d, uid));
  },
  actualizarModulo(id, data) {
    const d = _db();
    const idx = d.modulos.findIndex(m => m.id === id);
    if (idx === -1) return this._err("Modulo no encontrado.");
    d.modulos[idx] = { ...d.modulos[idx], ...data };
    _save(d);
    return this._ok(_enrichModulo(d.modulos[idx], d, _uid()));
  },
  eliminarModulo(id) {
    const d = _db();
    const idx = d.modulos.findIndex(m => m.id === id);
    if (idx !== -1) { d.modulos.splice(idx, 1); _save(d); }
    return this._ok(null);
  },

  /* MATERIALES ──────────────────────────────────────────── */
  materiales(moduloId) {
    return this._ok(_db().materiales.filter(m => m.modulo_id === moduloId));
  },
  crearMaterial(moduloId, data) {
    const d = _db();
    const nuevo = { id: _nextId(d,"materiales"), modulo_id: moduloId, ...data };
    d.materiales.push(nuevo);
    _save(d);
    return this._ok(nuevo);
  },
  eliminarMaterial(id) {
    const d = _db();
    const idx = d.materiales.findIndex(m => m.id === id);
    if (idx !== -1) { d.materiales.splice(idx, 1); _save(d); }
    return this._ok(null);
  },

  /* PROGRESO ────────────────────────────────────────────── */
  marcarCompletado(moduloId) {
    const d = _db(); const uid = _uid();
    const idx = d.progreso_modulos.findIndex(p => p.usuario_id === uid && p.modulo_id === moduloId);
    if (idx !== -1) { d.progreso_modulos[idx].completado = true; }
    else { d.progreso_modulos.push({ usuario_id: uid, modulo_id: moduloId, completado: true }); }
    _save(d);
    return this._ok(null);
  },
  progresoCurso(cursoId) {
    const d = _db(); const uid = _uid();
    const mods = d.modulos.filter(m => m.curso_id === cursoId);
    const total = mods.length;
    const completados = mods.filter(m => {
      const p = d.progreso_modulos.find(p => p.usuario_id === uid && p.modulo_id === m.id);
      return p && p.completado;
    }).length;
    return this._ok({ total, completados, porcentaje: total > 0 ? Math.round((completados/total)*100) : 0 });
  },

  /* TAREAS ──────────────────────────────────────────────── */
  tareas(cursoId) {
    return this._ok(_db().tareas.filter(t => t.curso_id === cursoId));
  },
  tareaDetalle(id) {
    const t = _db().tareas.find(t => t.id === id);
    return t ? this._ok(t) : this._err("Tarea no encontrada.");
  },
  crearTarea(cursoId, data) {
    const d = _db();
    const nueva = { id: _nextId(d,"tareas"), curso_id: cursoId, ...data };
    d.tareas.push(nueva);
    _save(d);
    return this._ok(nueva);
  },
  actualizarTarea(id, data) {
    const d = _db();
    const idx = d.tareas.findIndex(t => t.id === id);
    if (idx === -1) return this._err("Tarea no encontrada.");
    d.tareas[idx] = { ...d.tareas[idx], ...data };
    _save(d);
    return this._ok(d.tareas[idx]);
  },

  /* ENTREGAS ────────────────────────────────────────────── */
  entregas(tareaId) {
    const d = _db();
    return this._ok(d.entregas.filter(e => e.tarea_id === tareaId)
      .map(e => {
        const u = d.usuarios.find(u => u.id === e.usuario_id) || {};
        return { ...e, usuario: e.usuario_id,
          usuario_nombre: `${u.nombres||""} ${u.apellidos||""}`.trim(),
          usuario_correo: u.correo || "" };
      }));
  },
  miEntrega(tareaId) {
    const d = _db(); const uid = _uid();
    const e = d.entregas.find(e => e.tarea_id === tareaId && e.usuario_id === uid);
    return this._ok(e ? { ...e, usuario: e.usuario_id } : { estado: "pendiente" });
  },
  entregar(tareaId, data) {
    const d = _db(); const uid = _uid();
    const idx = d.entregas.findIndex(e => e.tarea_id === tareaId && e.usuario_id === uid);
    const base = { tarea_id: tareaId, usuario_id: uid, fecha: new Date().toISOString(),
      estado: "entregado", nota: null, comentario: null };
    if (idx !== -1) { d.entregas[idx] = { ...d.entregas[idx], ...base, ...data }; }
    else { d.entregas.push({ id: _nextId(d,"entregas"), ...base, ...data }); }
    _save(d);
    return this._ok({ ...base, ...data, usuario: uid });
  },
  calificar(entregaId, data) {
    const d = _db();
    const idx = d.entregas.findIndex(e => e.id === entregaId);
    if (idx === -1) return this._err("Entrega no encontrada.");
    d.entregas[idx] = { ...d.entregas[idx], nota: data.nota, comentario: data.comentario };
    _save(d);
    return this._ok(d.entregas[idx]);
  },

  /* QUIZZES ─────────────────────────────────────────────── */
  quizzes(cursoId) {
    return this._ok(_db().quizzes.filter(q => q.curso_id === cursoId).map(_enrichQuiz));
  },
  quizDetalle(id) {
    const q = _db().quizzes.find(q => q.id === id);
    return q ? this._ok(_enrichQuiz(q)) : this._err("Quiz no encontrado.");
  },
  crearQuiz(cursoId, data) {
    const d = _db();
    const nuevo = { id: _nextId(d,"quizzes"), curso_id: cursoId, ...data };
    d.quizzes.push(nuevo);
    _save(d);
    return this._ok(_enrichQuiz(nuevo));
  },
  actualizarQuiz(id, data) {
    const d = _db();
    const idx = d.quizzes.findIndex(q => q.id === id);
    if (idx === -1) return this._err("Quiz no encontrado.");
    d.quizzes[idx] = { ...d.quizzes[idx], ...data };
    _save(d);
    return this._ok(_enrichQuiz(d.quizzes[idx]));
  },
  respuestasQuiz(quizId) {
    const d = _db(); const uid = _uid();
    const esProfesor = _rolActivo() === "PROFESOR";
    return this._ok(
      d.respuestas_quiz
        .filter(r => r.quiz_id === quizId && (esProfesor || r.usuario_id === uid))
        .map(r => ({ ...r, usuario: r.usuario_id }))
    );
  },
  enviarQuiz(quizId, respuestas) {
    const d = _db(); const uid = _uid();
    const quiz = d.quizzes.find(q => q.id === quizId);
    if (!quiz) return this._err("Quiz no encontrado.");
    const nota_automatica = _autoGrade(quiz, respuestas);
    const nueva = { usuario_id: uid, quiz_id: quizId, fecha: new Date().toISOString(),
      respuestas, nota_automatica, nota_manual: null, nota_final: null };
    d.respuestas_quiz.push(nueva);
    _save(d);
    return this._ok({ ...nueva, usuario: uid });
  },
  notaManual(quizId, data) {
    const d = _db(); const uid = parseInt(data.usuario_id) || null;
    const r = d.respuestas_quiz.find(r => r.quiz_id === quizId && r.usuario_id === uid);
    if (r) { r.nota_manual = data.nota_manual; _save(d); }
    return this._ok(r || null);
  },
};
