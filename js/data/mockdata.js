/* Rutas relativas al root del proyecto (funciona con file:/// y con servidor) */
const BASE_PATH = window.location.pathname.includes('/pages/') ? '../../' : '';

const DB = {

  config: { porcentaje_minimo_aprobacion: 60 },

  usuarios: [
    { id: 1, nombres: "Carlos Alberto", apellidos: "Mendoza Rios",
      identificacion: "0912345678", telefono: "042123456", celular: "0991234567",
      correo: "carlos.mendoza@espol.edu.ec", direccion: "Cdla. Kennedy Norte",
      estadoCivil: "casado", estado: "activo", rol: "SUPERADMIN",
      facultad_id: null, fecha_registro: "2025-01-10", password: "admin123" },

    { id: 2, nombres: "Maria Elena", apellidos: "Torres Vega",
      identificacion: "0923456789", telefono: null, celular: "0987654321",
      correo: "maria.torres@espol.edu.ec", direccion: null,
      estadoCivil: "soltera", estado: "activo", rol: "ADMIN",
      facultad_id: 1, fecha_registro: "2025-02-15", password: "admin123" },

    { id: 3, nombres: "Roberto", apellidos: "Llerena Castillo",
      identificacion: "0934567890", telefono: "042987654", celular: "0976543210",
      correo: "roberto.llerena@espol.edu.ec", direccion: "Urdesa Central",
      estadoCivil: "divorciado", estado: "activo", rol: "USER",
      facultad_id: null, fecha_registro: "2025-03-01", password: "user123" },

    { id: 4, nombres: "Ana Lucia", apellidos: "Paredes Suarez",
      identificacion: "0945678901", telefono: null, celular: "0965432109",
      correo: "ana.paredes@espol.edu.ec", direccion: null,
      estadoCivil: "soltera", estado: "activo", rol: "USER",
      facultad_id: null, fecha_registro: "2025-03-10", password: "user123" },

    { id: 5, nombres: "Diego Fernando", apellidos: "Ochoa Mora",
      identificacion: "0956789012", telefono: "042111222", celular: "0954321098",
      correo: "diego.ochoa@espol.edu.ec", direccion: "Los Ceibos",
      estadoCivil: "soltero", estado: "inactivo", rol: "USER",
      facultad_id: null, fecha_registro: "2025-04-05", password: "user123" }
  ],

  facultades: [
    { id: 1, codigo: "FIEC", nombre: "Facultad de Ingenieria en Electricidad y Computacion", admin_id: 2 },
    { id: 2, codigo: "FCNM", nombre: "Facultad de Ciencias Naturales y Matematicas", admin_id: null },
    { id: 3, codigo: "FIMCP", nombre: "Facultad de Ingenieria Mecanica y Ciencias de la Produccion", admin_id: null }
  ],

  cursos: [
    { id: 1, nombre: "Desarrollo de Aplicaciones Web y Moviles", codigo: "DAWM-2026A",
      descripcion: "Curso de desarrollo frontend, backend, APIs y aplicaciones moviles.",
      facultad_id: 1, profesor_id: 3,
      fecha_inicio: "2026-03-01", fecha_fin: "2026-07-31", estado: "activo",
      formula: [
        { componente: "Tareas",         porcentaje: 40 },
        { componente: "Quizzes",        porcentaje: 30 },
        { componente: "Proyecto Final", porcentaje: 30 }
      ]},
    { id: 2, nombre: "Estructuras de Datos", codigo: "ED-2026A",
      descripcion: "Algoritmos, listas, arboles, grafos y complejidad computacional.",
      facultad_id: 1, profesor_id: 3,
      fecha_inicio: "2026-03-01", fecha_fin: "2026-07-31", estado: "activo",
      formula: [
        { componente: "Tareas",   porcentaje: 50 },
        { componente: "Examenes", porcentaje: 50 }
      ]},
    { id: 3, nombre: "Calculo Diferencial", codigo: "CD-2025B",
      descripcion: "Limites, derivadas y aplicaciones del calculo.",
      facultad_id: 2, profesor_id: 3,
      fecha_inicio: "2025-08-01", fecha_fin: "2025-12-15", estado: "archivado",
      formula: [
        { componente: "Quizzes",  porcentaje: 30 },
        { componente: "Examenes", porcentaje: 70 }
      ]}
  ],

  inscripciones: [
    { id: 1, usuario_id: 4, curso_id: 1, rol_en_curso: "ESTUDIANTE", fecha: "2026-03-05" },
    { id: 2, usuario_id: 5, curso_id: 1, rol_en_curso: "ESTUDIANTE", fecha: "2026-03-06" },
    { id: 3, usuario_id: 3, curso_id: 1, rol_en_curso: "PROFESOR",   fecha: "2026-02-20" },
    { id: 4, usuario_id: 4, curso_id: 2, rol_en_curso: "ESTUDIANTE", fecha: "2026-03-05" },
    { id: 5, usuario_id: 3, curso_id: 2, rol_en_curso: "PROFESOR",   fecha: "2026-02-20" }
  ],

  modulos: [
    { id: 1, curso_id: 1, orden: 1, titulo: "Introduccion al Desarrollo Web",
      descripcion: "Conceptos basicos de HTML, CSS y el ecosistema web." },
    { id: 2, curso_id: 1, orden: 2, titulo: "CSS Moderno y Responsive Design",
      descripcion: "Flexbox, Grid, Bootstrap y diseno adaptativo." },
    { id: 3, curso_id: 1, orden: 3, titulo: "JavaScript Fundamentos",
      descripcion: "Variables, funciones, DOM y eventos." },
    { id: 4, curso_id: 2, orden: 1, titulo: "Complejidad Algoritmica",
      descripcion: "Notacion Big O, analisis de algoritmos." }
  ],

  materiales: [
    { id: 1, modulo_id: 1, tipo: "video", titulo: "Que es la web y como funciona",      url: "https://www.youtube.com/watch?v=example1" },
    { id: 2, modulo_id: 1, tipo: "pdf",   titulo: "Guia de referencia HTML5",           url: "https://drive.google.com/file/example1" },
    { id: 3, modulo_id: 2, tipo: "video", titulo: "Flexbox en 20 minutos",              url: "https://www.youtube.com/watch?v=example2" },
    { id: 4, modulo_id: 2, tipo: "pdf",   titulo: "Cheatsheet Bootstrap 5",             url: "https://drive.google.com/file/example2" },
    { id: 5, modulo_id: 3, tipo: "video", titulo: "JavaScript desde cero",              url: "https://www.youtube.com/watch?v=example3" }
  ],

  progreso_modulos: [
    { usuario_id: 4, modulo_id: 1, completado: true  },
    { usuario_id: 4, modulo_id: 2, completado: true  },
    { usuario_id: 4, modulo_id: 3, completado: false }
  ],

  tareas: [
    { id: 1, curso_id: 1, titulo: "Pagina HTML estatica",
      descripcion: "Crear una pagina web con estructura semantica correcta usando HTML5.",
      fecha_limite: "2026-04-10T23:59", puntaje_maximo: 10,
      criterios: "Uso correcto de etiquetas semanticas, estructura valida, al menos 3 secciones." },
    { id: 2, curso_id: 1, titulo: "Diseno responsive con Bootstrap",
      descripcion: "Adaptar la pagina del ejercicio anterior usando el grid de Bootstrap 5.",
      fecha_limite: "2026-04-25T23:59", puntaje_maximo: 10,
      criterios: "Uso del sistema de grid, responsive en movil y escritorio." }
  ],

  entregas: [
    { id: 1, tarea_id: 1, usuario_id: 4, fecha: "2026-04-09T18:30", estado: "entregado",
      texto: "Adjunto mi pagina HTML con las secciones solicitadas.",
      archivo: "tarea1_ana.html", imagen: null, link: null,
      nota: 9.0, comentario: "Buen trabajo, falta atributo alt en las imagenes." },
    { id: 2, tarea_id: 1, usuario_id: 5, fecha: null, estado: "pendiente",
      texto: null, archivo: null, imagen: null, link: null, nota: null, comentario: null },
    { id: 3, tarea_id: 2, usuario_id: 4, fecha: "2026-04-24T20:10", estado: "entregado",
      texto: null, archivo: "tarea2_ana.zip", imagen: null, link: null, nota: null, comentario: null }
  ],

  quizzes: [
    { id: 1, curso_id: 1, titulo: "Quiz — HTML y CSS",
      descripcion: "Evaluacion de conocimientos basicos del modulo 1 y 2.",
      tiempo_limite_min: 20, fecha_limite: "2026-04-15T23:59",
      preguntas: [
        { id: 1, tipo: "opcion_multiple_una",
          enunciado: "Cual etiqueta define el titulo principal de una pagina?",
          puntaje: 2, opciones: ["<h1>", "<title>", "<header>", "<main>"], respuesta_correcta: 0 },
        { id: 2, tipo: "verdadero_falso",
          enunciado: "CSS Grid es una tecnica de diseno bidimensional.",
          puntaje: 2, respuesta_correcta: true },
        { id: 3, tipo: "completar_espacios",
          enunciado: "La propiedad ___ de flexbox alinea elementos en el eje principal.",
          puntaje: 3, respuesta_correcta: "justify-content" },
        { id: 4, tipo: "respuesta_corta",
          enunciado: "Explica la diferencia entre margin y padding.",
          puntaje: 3, respuesta_correcta: null }
      ]}
  ],

  respuestas_quiz: [
    { usuario_id: 4, quiz_id: 1, fecha: "2026-04-14T10:20",
      respuestas: [
        { pregunta_id: 1, valor: 0 },
        { pregunta_id: 2, valor: true },
        { pregunta_id: 3, valor: "justify-content" },
        { pregunta_id: 4, valor: "Margin es el espacio exterior y padding el interior." }
      ],
      nota_automatica: 7, nota_manual: null, nota_final: null }
  ],

  /* ── HELPERS ──────────────────────────────────────────── */
  getUsuarioById:    function(id)       { return this.usuarios.find(u => u.id === id) || null; },
  getCursoById:      function(id)       { return this.cursos.find(c => c.id === id) || null; },
  getFacultadById:   function(id)       { return this.facultades.find(f => f.id === id) || null; },

  getModulosByCurso: function(curso_id) {
    return this.modulos.filter(m => m.curso_id === curso_id).sort((a,b) => a.orden - b.orden);
  },
  getMaterialesByModulo: function(modulo_id) {
    return this.materiales.filter(m => m.modulo_id === modulo_id);
  },
  getTareasByCurso:  function(curso_id) { return this.tareas.filter(t => t.curso_id === curso_id); },
  getQuizzesByCurso: function(curso_id) { return this.quizzes.filter(q => q.curso_id === curso_id); },
  getEntregasByTarea:function(tarea_id) { return this.entregas.filter(e => e.tarea_id === tarea_id); },
  getEntregaByTareaYUsuario: function(tarea_id, usuario_id) {
    return this.entregas.find(e => e.tarea_id === tarea_id && e.usuario_id === usuario_id) || null;
  },
  getCursosByProfesor: function(profesor_id) {
    const ids = this.inscripciones.filter(i => i.usuario_id === profesor_id && i.rol_en_curso === "PROFESOR").map(i => i.curso_id);
    return this.cursos.filter(c => ids.includes(c.id));
  },
  getCursosByEstudiante: function(usuario_id) {
    const ids = this.inscripciones.filter(i => i.usuario_id === usuario_id && i.rol_en_curso === "ESTUDIANTE").map(i => i.curso_id);
    return this.cursos.filter(c => ids.includes(c.id));
  },
  getEstudiantesByCurso: function(curso_id) {
    const ids = this.inscripciones.filter(i => i.curso_id === curso_id && i.rol_en_curso === "ESTUDIANTE").map(i => i.usuario_id);
    return this.usuarios.filter(u => ids.includes(u.id));
  },
  getProgresoCurso: function(usuario_id, curso_id) {
    const modulos = this.getModulosByCurso(curso_id);
    if (!modulos.length) return 0;
    const completados = modulos.filter(m => {
      const p = this.progreso_modulos.find(p => p.usuario_id === usuario_id && p.modulo_id === m.id);
      return p && p.completado;
    }).length;
    return Math.round((completados / modulos.length) * 100);
  },
  autenticar: function(correo, password) {
    return this.usuarios.find(u => u.correo === correo && u.password === password) || null;
  },
  iniciales: function(nombres, apellidos) {
    return (nombres.charAt(0) + apellidos.charAt(0)).toUpperCase();
  }
};
