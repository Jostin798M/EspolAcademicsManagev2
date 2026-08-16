/* ── CAPA DE DATOS ──────────────────────────────────────────
   Todo pasa por la API real (/api/): el login, las consultas y
   los cambios. Antes solo el login iba contra el servidor y el
   resto vivia en localStorage; eso hacia que lo que se editaba
   aqui no se viera en la app movil ni al revés.

   Ahora el sitio y la app leen y escriben en la misma base de
   datos, y ademas el servidor decide que puede hacer cada quien
   segun su rol:

     SUPERADMIN -> todo el sistema
     ADMIN      -> su facultad
     PROFESOR   -> los cursos que dicta
     ESTUDIANTE -> los cursos que cursa y lo suyo

   Ese reparto NO se hace aqui. Aqui solo se pregunta (Permisos)
   para no dibujar botones que van a terminar en un 403; quien
   autoriza es el servidor, en cada peticion.

   Queda un modo demo sobre localStorage para cuando no hay
   servidor al que preguntar (abrir index.html suelto, sin
   Django). Se reconoce por Sesion.modo() === "demo".

   Todos los metodos siguen devolviendo Promises y las mismas
   formas de siempre, asi que las paginas no cambian.
──────────────────────────────────────────────────────────── */

const STORE_KEY = "espol_db";

/* ── PUENTE CON EL BACKEND ───────────────────────────────── */
/* Django sirve este frontend desde la raíz del dominio, así que
   la API siempre cuelga de /api/ sea cual sea la página. */
const API_URL = "/api";

/* Error de red: el backend no está. Se distingue de un rechazo
   del servidor, que sí es una respuesta legítima. */
class SinBackend extends Error {}

/* Error del servidor: llega con su código y su motivo, para que
   la página pueda distinguir "no puedes" de "escribiste mal". */
class ErrorApi extends Error {
  constructor(mensaje, { codigo = 0, motivo = null, detalle = "", datos = null } = {}) {
    super(mensaje);
    this.name = "ErrorApi";
    this.codigo = codigo;
    this.motivo = motivo;
    this.detalle = detalle;
    this.datos = datos;
  }

  /* Su rol no llega, o el registro no es suyo. */
  get sinPermiso() {
    return ["sin_permiso", "fuera_de_alcance", "campo_no_permitido"].includes(this.motivo);
  }

  /* La sesión se cayó: hay que volver a entrar. */
  get sesionCaducada() {
    return ["sin_credenciales", "token_invalido", "token_caducado",
            "token_revocado", "cuenta_inactiva", "rol_sin_acceso"].includes(this.motivo);
  }

  /* Campo que el servidor señaló como inválido, si señaló alguno. */
  get campo() {
    return this.datos?.campo || (this.datos?.campos || [])[0] || null;
  }
}

const Backend = {
  /* Con file:// no hay servidor al que preguntar. */
  posible() {
    return window.location.protocol === "http:" || window.location.protocol === "https:";
  },

  /* Una sola puerta para los cinco verbos. Las rutas de escritura
     de la API están exentas de CSRF (se autentican con la sesión
     o con el token), así que no hace falta mandar el token. */
  async pedir(ruta, { metodo = "GET", cuerpo = null } = {}) {
    if (!this.posible()) throw new SinBackend("Sin servidor.");

    let respuesta;
    try {
      respuesta = await fetch(API_URL + ruta, {
        method: metodo,
        headers: {
          Accept: "application/json",
          ...(cuerpo ? { "Content-Type": "application/json" } : {}),
        },
        credentials: "same-origin",   // la cookie de sesión de Django
        body: cuerpo ? JSON.stringify(cuerpo) : undefined,
      });
    } catch {
      throw new SinBackend("No se pudo contactar al servidor.");
    }

    let datos;
    try {
      datos = await respuesta.json();
    } catch {
      throw new SinBackend("El servidor no respondió en JSON.");
    }

    if (!datos.ok) {
      throw new ErrorApi(datos.error || "Error desconocido.", {
        codigo: datos.codigo || respuesta.status,
        motivo: datos.motivo || null,
        detalle: datos.detalle || "",
        datos,
      });
    }

    return datos;
  },

  get(ruta)            { return this.pedir(ruta); },
  post(ruta, cuerpo)   { return this.pedir(ruta, { metodo: "POST", cuerpo }); },
  patch(ruta, cuerpo)  { return this.pedir(ruta, { metodo: "PATCH", cuerpo }); },
  del(ruta)            { return this.pedir(ruta, { metodo: "DELETE" }); },

  /* Atajo: la mayoría de las rutas devuelven lo útil en "datos". */
  async datos(ruta, opciones) {
    return (await this.pedir(ruta, opciones)).datos;
  },

  /* Lista completa de un recurso paginado.

     La API limita el tamaño de página (API_TAM_PAGINA_MAX, 100 por
     defecto) y hace bien: nadie debería poder pedirle la base
     entera de un tirón. Pero las páginas de este sitio se
     escribieron esperando la lista completa, así que se recorren
     las páginas aquí y se devuelve todo junto. */
  async lista(ruta, tam = 100) {
    const union = ruta.includes("?") ? "&" : "?";
    let pagina = 1;
    let todo = [];

    for (;;) {
      const r = await this.pedir(`${ruta}${union}tam=${tam}&pagina=${pagina}`);
      todo = todo.concat(r.datos || []);

      const siguiente = r.paginacion?.siguiente;
      if (!siguiente) return todo;

      pagina = siguiente;
    }
  },

  /* El login antiguo devolvía el cuerpo entero sin lanzar; se
     conserva porque index.html distingue el rechazo de credenciales
     de la caída del servidor. */
  async intentarLogin(cuerpo) {
    try {
      return await this.pedir("/auth/login/", { metodo: "POST", cuerpo });
    } catch (err) {
      if (err instanceof ErrorApi) return { ok: false, error: err.message, motivo: err.motivo };
      throw err;
    }
  },
};

/* ── QUÉ SABE LA SESIÓN ──────────────────────────────────── */
/* Se guarda en sessionStorage lo que la interfaz necesita para
   dibujarse: quién entró, con qué rol y qué permisos tiene. Se
   borra al cerrar la pestaña, y se refresca en cada login. */
const Sesion = {
  guardar({ modo, autorizado, mensaje, via, rol, permisos }) {
    sessionStorage.setItem("modo", modo);
    sessionStorage.setItem("api_autorizado", autorizado ? "1" : "0");
    sessionStorage.setItem("api_mensaje", mensaje || "");
    sessionStorage.setItem("api_via", via || "");
    if (rol) sessionStorage.setItem("rol_efectivo", rol);
    if (permisos) sessionStorage.setItem("permisos", JSON.stringify(permisos));
  },
  modo()       { return sessionStorage.getItem("modo") || "demo"; },
  autorizado() { return sessionStorage.getItem("api_autorizado") === "1"; },
  mensaje()    { return sessionStorage.getItem("api_mensaje") || ""; },
  rol()        { return sessionStorage.getItem("rol_efectivo") || sessionStorage.getItem("rol_activo") || ""; },
  enDemo()     { return this.modo() === "demo"; },
};

/* ── PERMISOS ────────────────────────────────────────────── */
/* Lo que el servidor dijo que este usuario puede hacer. Sirve
   para esconder botones, nunca para autorizar: el servidor lo
   vuelve a comprobar en cada peticion, asi que si aqui se cuela
   un boton de mas lo unico que pasa es un 403 explicado.

   En modo demo no hay servidor que pregunte, asi que se permite
   todo: es una demostracion del frontend, no un sistema real. */
const Permisos = {
  _cache: null,

  todos() {
    if (this._cache) return this._cache;
    try {
      this._cache = JSON.parse(sessionStorage.getItem("permisos") || "null");
    } catch {
      this._cache = null;
    }
    return this._cache;
  },

  /* Permisos.puede("cursos", "crear") */
  puede(recurso, accion = "ver") {
    if (Sesion.enDemo()) return true;
    const ficha = this.todos()?.recursos?.[recurso];
    return Boolean(ficha && ficha[accion]);
  },

  /* Sobre qué datos vale: "todo", "facultad", "cursos", "propio". */
  alcance(recurso, accion = "ver") {
    if (Sesion.enDemo()) return "todo";
    return this.todos()?.recursos?.[recurso]?.[accion] || null;
  },

  rol()        { return this.todos()?.rol || Sesion.rol(); },
  etiqueta()   { return this.todos()?.rol_etiqueta || this.rol(); },

  /* Tira la copia en memoria para que la proxima lectura vuelva a
     sessionStorage. Se llama despues de guardar unos permisos nuevos;
     NO borra los guardados, que es justo lo que se acaba de escribir. */
  refrescar()  { this._cache = null; },

  /* Los olvida del todo. Solo al cerrar sesion. */
  limpiar()    { this._cache = null; sessionStorage.removeItem("permisos"); },

  /* Esconde un elemento del DOM si el rol no llega. Lo usan las
     páginas para apagar botones sin repetir el mismo if. */
  aplicarA(elemento, recurso, accion = "ver") {
    if (!elemento) return;
    if (!this.puede(recurso, accion)) elemento.style.display = "none";
  },
};

/* ── EQUIVALENCIA DE FORMAS ──────────────────────────────── */
/* La API habla de "id_curso", "codigo" y objetos anidados; las
   páginas de este sitio llevan desde el principio "id" y
   "curso_id". Traducir aquí, en un solo sitio, evita tocar las
   catorce páginas y deja la conversión a la vista. */

/* Los cursos se piden a la API por su código, pero las páginas
   los manejan por id. Se guarda la equivalencia cada vez que
   pasa una lista de cursos por aquí. */
const Codigos = {
  _porId: new Map(),

  anotar(cursos) {
    (cursos || []).forEach(c => {
      if (c.id_curso && c.codigo) this._porId.set(c.id_curso, c.codigo);
    });
  },

  async de(idCurso) {
    const id = parseInt(idCurso);
    if (this._porId.has(id)) return this._porId.get(id);

    // No estaba: se refresca la lista y se vuelve a mirar.
    const datos = await Backend.lista("/mi/cursos/");
    this.anotar(datos);

    if (!this._porId.has(id)) throw new ErrorApi("Curso no encontrado.", { codigo: 404 });
    return this._porId.get(id);
  },
};

/* Las facultades igual: la API las direcciona por código. */
const CodigosFacultad = {
  _porId: new Map(),

  anotar(facultades) {
    (facultades || []).forEach(f => {
      if (f.id_facultad && f.codigo) this._porId.set(f.id_facultad, f.codigo);
    });
  },

  async de(idFacultad) {
    const id = parseInt(idFacultad);
    if (this._porId.has(id)) return this._porId.get(id);

    this.anotar(await Backend.lista("/facultades/"));

    if (!this._porId.has(id)) throw new ErrorApi("Facultad no encontrada.", { codigo: 404 });
    return this._porId.get(id);
  },
};

const Desde = {
  usuario(u) {
    if (!u) return null;
    return {
      id: u.id_usuario,
      nombres: u.nombres,
      apellidos: u.apellidos,
      identificacion: u.identificacion || "",
      telefono: u.telefono || "",
      celular: u.celular || "",
      correo: u.correo,
      direccion: u.direccion || "",
      estado_civil: u.estado_civil || "soltero",
      estado: u.estado,
      rol: u.rol,
      rol_efectivo: u.rol_efectivo || null,
      fecha_registro: u.fecha_registro || null,
      facultad_codigo: u.facultad || null,
      facultad: u.facultad || null,
      iniciales: u.iniciales
        || ((u.nombres || "")[0] || "") + ((u.apellidos || "")[0] || ""),
      nombre_completo: u.nombre_completo || `${u.nombres} ${u.apellidos}`,
    };
  },

  facultad(f) {
    if (!f) return null;
    return {
      id: f.id_facultad,
      codigo: f.codigo,
      nombre: f.nombre,
      total_cursos: f.total_cursos ?? null,
      admin: f.admin || null,
      admin_nombre: f.admin_nombre || null,
    };
  },

  curso(c) {
    if (!c) return null;
    Codigos.anotar([c]);
    return {
      id: c.id_curso,
      codigo: c.codigo,
      nombre: c.nombre,
      descripcion: c.descripcion || "",
      estado: c.estado,
      fecha_inicio: c.fecha_inicio,
      fecha_fin: c.fecha_fin,
      facultad: c.facultad?.codigo || null,
      facultad_codigo: c.facultad?.codigo || "—",
      facultad_nombre: c.facultad?.nombre || "—",
      profesor_id: c.profesor?.id_usuario || null,
      profesor_nombre: c.profesor?.nombre_completo || "—",
      total_estudiantes: c.total_estudiantes ?? 0,
      total_tareas: c.total_tareas ?? null,
      /* Lo que ESTE usuario puede hacer en ESTE curso, tal como
         lo calculó el servidor: {cursos:["ver","editar"], ...}. */
      puedo: c.puedo || {},
      /* Con que sombrero esta este usuario en ESTE curso. Lo calcula el
         servidor, que es quien tiene las inscripciones; las paginas de
         profesor y estudiante filtran su lista con esto. */
      mi_rol: c.mi_rol || null,
    };
  },

  inscripcion(i) {
    if (!i) return null;
    return {
      id: i.id_inscripcion,
      curso_id: null,           // la página ya sabe de qué curso pidió
      usuario_id: i.usuario?.id_usuario,
      usuario: i.usuario?.id_usuario,
      usuario_nombre: i.usuario?.nombre_completo || "",
      usuario_correo: i.usuario?.correo || "",
      rol_en_curso: i.rol_en_curso,
      fecha: i.fecha,
    };
  },

  modulo(m, completados) {
    if (!m) return null;
    return {
      id: m.id_modulo,
      titulo: m.titulo,
      descripcion: m.descripcion || "",
      orden: m.orden,
      materiales: (m.materiales || []).map(Desde.material),
      completado: completados ? completados.has(m.id_modulo) : false,
    };
  },

  material(m) {
    if (!m) return null;
    return {
      id: m.id_material,
      tipo: m.tipo,
      titulo: m.titulo,
      url: m.url,
    };
  },

  tarea(t) {
    if (!t) return null;
    return {
      id: t.id_tarea,
      titulo: t.titulo,
      descripcion: t.descripcion || "",
      criterios: t.criterios || "",
      fecha_limite: t.fecha_limite,
      puntaje_maximo: t.puntaje_maximo,
      recibidas: t.recibidas ?? null,
      sin_calificar: t.sin_calificar ?? null,
    };
  },

  entrega(e) {
    if (!e) return null;
    return {
      id: e.id_entrega,
      tarea_id: e.tarea,
      usuario_id: e.usuario ?? null,
      usuario: e.usuario ?? null,
      usuario_nombre: e.estudiante || "",
      usuario_correo: "",
      fecha: e.fecha,
      estado: e.estado,
      texto: e.texto || "",
      archivo: e.archivo || null,
      imagen: e.imagen || null,
      link: e.link || null,
      nota: e.nota,
      comentario: e.comentario || "",
      calificada: e.calificada,
    };
  },

  quiz(q) {
    if (!q) return null;
    const preguntas = (q.preguntas || []).map(Desde.pregunta);
    return {
      id: q.id_quiz,
      titulo: q.titulo,
      descripcion: q.descripcion || "",
      tiempo_limite_min: q.tiempo_limite_min,
      fecha_limite: q.fecha_limite,
      preguntas,
      total_preguntas: q.total_preguntas ?? preguntas.length,
      puntaje_total: preguntas.reduce((a, p) => a + (p.puntaje || 0), 0),
    };
  },

  pregunta(p) {
    if (!p) return null;
    return {
      id: p.id_pregunta,
      tipo: p.tipo,
      enunciado: p.enunciado,
      puntaje: p.puntaje,
      orden: p.orden,
      opciones: p.opciones || [],
      /* Solo llega para quien puede editar el quiz. */
      respuesta_correcta: p.respuesta_correcta,
    };
  },

  respuestaQuiz(r) {
    if (!r) return null;
    return {
      id: r.id_respuesta_quiz,
      quiz_id: r.quiz,
      usuario_id: r.usuario,
      usuario: r.usuario,
      usuario_nombre: r.estudiante || "",
      respuestas: r.respuestas || {},
      nota_automatica: r.nota_automatica,
      nota_manual: r.nota_manual,
      nota_final: r.nota_manual ?? r.nota_automatica,
      fecha: r.fecha,
    };
  },
};

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


/* ── IMPLEMENTACIÓN LOCAL (modo demo) ────────────────────── */
/* La de siempre, sobre localStorage. Ya no es la principal:
   solo entra cuando no hay servidor al que preguntar, para que
   el sitio se pueda enseñar abriendo index.html a secas. Lo que
   se cambie aquí NO llega a la base ni a la app móvil. */
const Local = {
  _ok: v => Promise.resolve(v),
  _err: m => Promise.reject(new Error(m)),

  _loginDemo(correo, password) {
    const d = _db();
    const u = d.usuarios.find(u => u.correo === correo && u.password === password);
    if (!u) return this._err("Correo o contrasena incorrectos.");
    if (u.estado !== "activo") return this._err("La cuenta esta inactiva.");
    let rol_activo = null;
    if (u.rol === "USER") {
      const esProf = d.inscripciones.some(i => i.usuario_id === u.id && i.rol_en_curso === "PROFESOR");
      rol_activo = esProf ? "PROFESOR" : "ESTUDIANTE";
    }
    Sesion.guardar({ modo: "demo", autorizado: false, mensaje: "", via: "" });
    return this._ok({ usuario: _enrichUser(u), rol_activo });
  },

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

/* ── IMPLEMENTACIÓN REMOTA ───────────────────────────────── */
/* Cada método hace la llamada que le toca y devuelve la forma de
   siempre. Lo que NO hace ninguno es filtrar por rol: eso ya
   viene hecho desde el servidor, y filtrar otra vez aquí sería
   una cortina, no una seguridad. */
const Remoto = {

  /* USUARIOS ────────────────────────────────────────────── */
  async me() {
    return Desde.usuario(await Backend.datos("/mi/perfil/"));
  },
  async usuarios() {
    return (await Backend.lista("/usuarios/")).map(Desde.usuario);
  },
  async usuarioDetalle(id) {
    return Desde.usuario(await Backend.datos(`/usuarios/${id}/`));
  },
  async crearUsuario(data) {
    return Desde.usuario(await Backend.datos("/usuarios/", {
      metodo: "POST", cuerpo: _cuerpoUsuario(data),
    }));
  },
  async actualizarUsuario(id, data) {
    return Desde.usuario(await Backend.datos(`/usuarios/${id}/`, {
      metodo: "PATCH", cuerpo: _cuerpoUsuario(data),
    }));
  },
  async toggleEstado(id) {
    /* La API no tiene un "invertir estado": se lee cómo está y se
       manda el contrario. Son dos viajes, pero evita inventar un
       endpoint para algo que ya se puede hacer. */
    const actual = await Backend.datos(`/usuarios/${id}/`);
    const contrario = actual.estado === "activo" ? "inactivo" : "activo";

    return Desde.usuario(await Backend.datos(`/usuarios/${id}/`, {
      metodo: "PATCH", cuerpo: { estado: contrario },
    }));
  },

  /* FACULTADES ──────────────────────────────────────────── */
  async facultades() {
    const datos = await Backend.lista("/facultades/");
    CodigosFacultad.anotar(datos);
    return datos.map(Desde.facultad);
  },
  async crearFacultad(data) {
    return Desde.facultad(await Backend.datos("/facultades/", {
      metodo: "POST",
      cuerpo: { nombre: data.nombre, codigo: data.codigo, admin: data.admin || null },
    }));
  },
  async actualizarFacultad(id, data) {
    const codigo = await CodigosFacultad.de(id);
    return Desde.facultad(await Backend.datos(`/facultades/${codigo}/`, {
      metodo: "PATCH",
      cuerpo: { nombre: data.nombre, codigo: data.codigo, admin: data.admin || null },
    }));
  },

  /* CURSOS ──────────────────────────────────────────────── */
  async cursos() {
    const datos = await Backend.lista("/mi/cursos/");
    Codigos.anotar(datos);
    return datos.map(Desde.curso);
  },
  async cursoDetalle(id) {
    const codigo = await Codigos.de(id);
    return Desde.curso(await Backend.datos(`/cursos/${codigo}/`));
  },
  async crearCurso(data) {
    const creado = await Backend.datos("/cursos/", {
      metodo: "POST", cuerpo: await _cuerpoCurso(data),
    });
    Codigos.anotar([creado]);
    return Desde.curso(creado);
  },
  async actualizarCurso(id, data) {
    const codigo = await Codigos.de(id);
    return Desde.curso(await Backend.datos(`/cursos/${codigo}/`, {
      metodo: "PATCH", cuerpo: await _cuerpoCurso(data, { editando: true }),
    }));
  },
  async eliminarCurso(id) {
    const codigo = await Codigos.de(id);
    await Backend.del(`/cursos/${codigo}/`);
    return null;
  },

  /* INSCRIPCIONES ───────────────────────────────────────── */
  async inscripciones(cursoId) {
    const codigo = await Codigos.de(cursoId);
    const datos = await Backend.lista(`/cursos/${codigo}/estudiantes/?rol=todos`);

    return datos.map(i => ({ ...Desde.inscripcion(i), curso_id: parseInt(cursoId) }));
  },
  async inscribir(cursoId, usuarioId, rol = "ESTUDIANTE") {
    const codigo = await Codigos.de(cursoId);
    const creada = await Backend.datos(`/cursos/${codigo}/estudiantes/`, {
      metodo: "POST", cuerpo: { usuario: usuarioId, rol_en_curso: rol },
    });

    return { ...Desde.inscripcion(creada), curso_id: parseInt(cursoId) };
  },
  async desinscribir(cursoId, usuarioId) {
    /* La API borra por id de inscripción, no por la pareja
       (curso, usuario): primero se busca cuál es. */
    const inscritas = await this.inscripciones(cursoId);
    const suya = inscritas.find(i => i.usuario_id === parseInt(usuarioId));

    if (!suya) throw new ErrorApi("Inscripcion no encontrada.", { codigo: 404 });

    await Backend.del(`/inscripciones/${suya.id}/`);
    return null;
  },

  /* MODULOS ─────────────────────────────────────────────── */
  async modulos(cursoId) {
    const codigo = await Codigos.de(cursoId);

    /* "completado" es una marca personal: solo tiene sentido para quien
       ve su propio progreso. Un profesor mirando el curso no tiene un
       avance propio que marcar, así que ahí ni se pide. */
    const esMiAvance = Permisos.alcance("progreso", "ver") === "propio";

    const [lista, progreso] = await Promise.all([
      Backend.lista(`/cursos/${codigo}/modulos/`),
      esMiAvance
        ? Backend.datos(`/cursos/${codigo}/progreso/`).catch(() => null)
        : Promise.resolve(null),
    ]);

    const mio = progreso?.filas?.[0];
    const completados = new Set(
      (mio?.modulos || []).filter(m => m.completado).map(m => m.id_modulo),
    );

    return lista
      .sort((a, b) => a.orden - b.orden)
      .map(m => Desde.modulo(m, completados));
  },
  async crearModulo(cursoId, data) {
    const codigo = await Codigos.de(cursoId);
    return Desde.modulo(await Backend.datos(`/cursos/${codigo}/modulos/`, {
      metodo: "POST",
      cuerpo: { titulo: data.titulo, descripcion: data.descripcion, orden: data.orden },
    }));
  },
  async actualizarModulo(id, data) {
    return Desde.modulo(await Backend.datos(`/modulos/${id}/`, {
      metodo: "PATCH",
      cuerpo: { titulo: data.titulo, descripcion: data.descripcion, orden: data.orden },
    }));
  },
  async eliminarModulo(id) {
    await Backend.del(`/modulos/${id}/`);
    return null;
  },

  /* MATERIALES ──────────────────────────────────────────── */
  async materiales(moduloId) {
    /* No hay una ruta de materiales sueltos porque un material sin
       módulo no significa nada: vienen dentro del suyo. */
    const modulo = await Backend.datos(`/modulos/${moduloId}/`);

    return (modulo.materiales || []).map(Desde.material);
  },
  async crearMaterial(moduloId, data) {
    return Desde.material(await Backend.datos(`/modulos/${moduloId}/materiales/`, {
      metodo: "POST",
      cuerpo: { titulo: data.titulo, url: data.url, tipo: data.tipo },
    }));
  },
  async eliminarMaterial(id) {
    await Backend.del(`/materiales/${id}/`);
    return null;
  },

  /* PROGRESO ────────────────────────────────────────────── */
  async marcarCompletado(moduloId) {
    await Backend.post(`/modulos/${moduloId}/progreso/`, { completado: true });
    return null;
  },
  async progresoCurso(cursoId) {
    const codigo = await Codigos.de(cursoId);
    const datos = await Backend.datos(`/cursos/${codigo}/progreso/`);
    const mia = (datos.filas || [])[0];

    if (!mia) return { total: datos.total_modulos, completados: 0, porcentaje: 0 };

    return {
      total: mia.total,
      completados: mia.completados,
      porcentaje: Math.round(mia.avance),
    };
  },

  /* TAREAS ──────────────────────────────────────────────── */
  async tareas(cursoId) {
    const codigo = await Codigos.de(cursoId);
    return (await Backend.lista(`/cursos/${codigo}/tareas/`)).map(Desde.tarea);
  },
  async tareaDetalle(id) {
    return Desde.tarea(await Backend.datos(`/tareas/${id}/`));
  },
  async crearTarea(cursoId, data) {
    const codigo = await Codigos.de(cursoId);
    return Desde.tarea(await Backend.datos(`/cursos/${codigo}/tareas/`, {
      metodo: "POST", cuerpo: _cuerpoTarea(data),
    }));
  },
  async actualizarTarea(id, data) {
    return Desde.tarea(await Backend.datos(`/tareas/${id}/`, {
      metodo: "PATCH", cuerpo: _cuerpoTarea(data),
    }));
  },

  /* ENTREGAS ────────────────────────────────────────────── */
  async entregas(tareaId) {
    return (await Backend.lista(`/tareas/${tareaId}/entregas/`)).map(Desde.entrega);
  },
  async miEntrega(tareaId) {
    /* Para un estudiante la lista trae exactamente una fila: la
       suya. El servidor ya recorta, aquí no hay que buscar. */
    const propias = await Backend.datos(`/tareas/${tareaId}/entregas/`);
    const mia = propias[0];

    return mia ? Desde.entrega(mia) : { estado: "pendiente" };
  },
  async entregar(tareaId, data) {
    return Desde.entrega(await Backend.datos(`/tareas/${tareaId}/entregas/`, {
      metodo: "POST",
      cuerpo: {
        texto: data.texto || "",
        archivo: data.archivo || "",
        imagen: data.imagen || "",
        link: data.link || "",
      },
    }));
  },
  async calificar(entregaId, data) {
    return Desde.entrega(await Backend.datos(`/entregas/${entregaId}/`, {
      metodo: "PATCH",
      cuerpo: { nota: data.nota, comentario: data.comentario || "" },
    }));
  },

  /* QUIZZES ─────────────────────────────────────────────── */
  async quizzes(cursoId) {
    const codigo = await Codigos.de(cursoId);
    return (await Backend.lista(`/cursos/${codigo}/quizzes/`)).map(Desde.quiz);
  },
  async quizDetalle(id) {
    return Desde.quiz(await Backend.datos(`/quizzes/${id}/`));
  },
  async crearQuiz(cursoId, data) {
    const codigo = await Codigos.de(cursoId);
    return Desde.quiz(await Backend.datos(`/cursos/${codigo}/quizzes/`, {
      metodo: "POST", cuerpo: _cuerpoQuiz(data),
    }));
  },
  async actualizarQuiz(id, data) {
    return Desde.quiz(await Backend.datos(`/quizzes/${id}/`, {
      metodo: "PATCH", cuerpo: _cuerpoQuiz(data),
    }));
  },
  async respuestasQuiz(quizId) {
    return (await Backend.lista(`/quizzes/${quizId}/respuestas/`))
      .map(Desde.respuestaQuiz);
  },
  async enviarQuiz(quizId, respuestas) {
    return Desde.respuestaQuiz(await Backend.datos(`/quizzes/${quizId}/respuestas/`, {
      metodo: "POST", cuerpo: { respuestas },
    }));
  },
  async notaManual(quizId, data) {
    /* La página identifica el intento por el estudiante; la API,
       por el id del intento. Se traduce buscándolo en la lista. */
    const intentos = await this.respuestasQuiz(quizId);
    const suyo = intentos.find(r => r.usuario_id === parseInt(data.usuario_id));

    if (!suyo) throw new ErrorApi("Ese estudiante todavia no ha rendido el quiz.", { codigo: 404 });

    return Desde.respuestaQuiz(await Backend.datos(`/respuestas/${suyo.id}/`, {
      metodo: "PATCH", cuerpo: { nota_manual: data.nota_manual },
    }));
  },
};

/* ── Cuerpos que espera la API ───────────────────────────── */
/* Las páginas mandan sus nombres de campo de siempre; aquí se
   traducen a los que entiende el servidor y se descarta lo que
   llegue vacío, para no pisar un dato bueno con una cadena en
   blanco cuando la página solo quería cambiar otra cosa. */

function _sinVacios(objeto) {
  return Object.fromEntries(
    Object.entries(objeto).filter(([, v]) => v !== undefined && v !== null && v !== ""),
  );
}

function _cuerpoUsuario(data) {
  return _sinVacios({
    nombres: data.nombres,
    apellidos: data.apellidos,
    identificacion: data.identificacion,
    correo: data.correo,
    celular: data.celular,
    telefono: data.telefono,
    direccion: data.direccion,
    estado_civil: data.estado_civil || data.estadoCivil,
    rol: data.rol,
    estado: data.estado,
    facultad: data.facultad_codigo || data.facultad,
    password: data.password,
  });
}

async function _cuerpoCurso(data, { editando = false } = {}) {
  const cuerpo = _sinVacios({
    nombre: data.nombre,
    codigo: data.codigo,
    descripcion: data.descripcion,
    fecha_inicio: data.fecha_inicio,
    fecha_fin: data.fecha_fin,
    estado: data.estado,
  });

  /* La página manda el id de la facultad y del profesor; la API
     quiere el código de la una y el correo o id del otro. */
  const idFacultad = data.facultad ?? data.facultad_id;
  if (idFacultad) cuerpo.facultad = await CodigosFacultad.de(idFacultad);

  if (data.profesor_id) cuerpo.profesor = data.profesor_id;

  if (!editando && !cuerpo.estado) cuerpo.estado = "activo";

  return cuerpo;
}

function _cuerpoTarea(data) {
  return _sinVacios({
    titulo: data.titulo,
    descripcion: data.descripcion,
    criterios: data.criterios,
    fecha_limite: data.fecha_limite,
    puntaje_maximo: data.puntaje_maximo,
  });
}

function _cuerpoQuiz(data) {
  return _sinVacios({
    titulo: data.titulo,
    descripcion: data.descripcion,
    tiempo_limite_min: data.tiempo_limite_min,
    fecha_limite: data.fecha_limite,
  });
}

/* ── LA API QUE VEN LAS PÁGINAS ──────────────────────────── */
/* Un solo objeto con los métodos de siempre. Por dentro decide
   a quién preguntar: al servidor si lo hay, al almacén local si
   estamos en modo demo. Las páginas no se enteran. */

/* Métodos de datos que existen en las dos implementaciones. */
const METODOS = Object.keys(Local).filter(nombre => !nombre.startsWith("_"));

/* Envuelve un método para elegir implementación en cada llamada.
   Si el servidor deja de responder a mitad de sesión se cae al
   modo demo en vez de dejar la página en blanco; un error del
   servidor (403, 404, 409) sí sube, porque es una respuesta. */
function _repartir(nombre) {
  return async function (...args) {
    if (!Sesion.enDemo()) {
      try {
        return await Remoto[nombre](...args);
      } catch (err) {
        if (!(err instanceof SinBackend)) throw err;
        Sesion.guardar({ modo: "demo", autorizado: false, mensaje: "", via: "" });
      }
    }

    return Local[nombre](...args);
  };
}

const API = {
  _ok: v => Promise.resolve(v),
  _err: m => Promise.reject(new Error(m)),

  /* AUTH ────────────────────────────────────────────────── */

  /* Login único. Un solo formulario y una sola contraseña: el
     backend valida contra la base, abre la sesión de Django (la
     misma que reconocen /admin/, /panel/ y /api/) y devuelve el
     rol y los permisos con los que se va a dibujar el sitio.

     No se pide token: al navegador le basta la cookie, y así no
     queda ningún token guardado en el equipo del usuario. */
  async login(correo, password) {
    let respuesta;

    try {
      respuesta = await Backend.intentarLogin({
        correo, password, sesion: true, token: false,
      });
    } catch (err) {
      if (err instanceof SinBackend) return this._loginDemo(correo, password);
      throw err;
    }

    if (!respuesta.ok) {
      // El servidor rechazó las credenciales: es una respuesta suya,
      // no una caída, y por tanto no se cae al modo demo.
      throw new ErrorApi(respuesta.error || "No se pudo iniciar sesion.", {
        motivo: respuesta.motivo,
      });
    }

    const datos = respuesta.datos;

    Sesion.guardar({
      modo: "backend",
      autorizado: datos.autorizado,
      mensaje: datos.aviso || "",
      via: "sesion",
      rol: datos.rol,
      permisos: datos.permisos,
    });
    Permisos.refrescar();

    return {
      usuario: Desde.usuario(datos.usuario),
      rol_activo: datos.rol_activo || datos.rol,
      rol: datos.rol,
      permisos: datos.permisos,
    };
  },

  /* Respaldo sin servidor: los usuarios de mockdata.js. Sirve
     para enseñar el frontend abriendo index.html directamente. */
  _loginDemo(correo, password) {
    return Local._loginDemo(correo, password);
  },

  /* Cierra las dos puntas: la sesión de Django y la del navegador. */
  async logout() {
    try { await Backend.post("/auth/logout/", {}); } catch { /* modo demo */ }

    Permisos.limpiar();
    return null;
  },

  /* Con qué rol y permisos estamos ahora mismo. El dashboard lo
     consulta al cargar para redibujarse si algo cambió (por
     ejemplo si a este usuario le asignaron un curso desde la app
     móvil mientras tenía la pestaña abierta). */
  async verificarApi() {
    try {
      const r = await Backend.pedir("/auth/verificar/");

      Sesion.guardar({
        modo: "backend",
        autorizado: true,
        mensaje: r.datos.mensaje || "",
        via: r.datos.via,
        rol: r.datos.rol,
        permisos: r.datos.permisos,
      });
      Permisos.refrescar();

      return {
        autorizado: true,
        mensaje: r.datos.mensaje || "",
        via: r.datos.via,
        rol: r.datos.rol,
        permisos: r.datos.permisos,
        usuario: Desde.usuario(r.datos.usuario),
      };
    } catch (err) {
      if (err instanceof SinBackend) return null;

      return {
        autorizado: false,
        mensaje: err.message,
        motivo: err.motivo,
        via: null,
        usuario: null,
      };
    }
  },

  /* Los métodos de datos se generan a partir de los que existen,
     para que añadir uno nuevo no obligue a tocar esta lista. */
  ...Object.fromEntries(METODOS.map(nombre => [nombre, _repartir(nombre)])),
};

/* Se exponen para las páginas: Permisos apaga botones y Sesion
   dice en qué modo estamos. ErrorApi permite distinguir un "no
   puedes" de un "escribiste mal" al mostrar el mensaje. */
window.API = API;
window.Permisos = Permisos;
window.Sesion = Sesion;
window.ErrorApi = ErrorApi;
