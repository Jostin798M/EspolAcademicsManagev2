/* Aplicar tema inmediatamente para evitar flash */
(function () {
  const stored = localStorage.getItem("tema");
  if (stored === "oscuro") {
    document.documentElement.setAttribute("data-theme", "dark");
  } else if (!stored && window.matchMedia("(prefers-color-scheme: dark)").matches) {
    document.documentElement.setAttribute("data-theme", "dark");
  }
  /* Seguir cambios del sistema cuando el usuario no ha elegido manualmente */
  window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", e => {
    if (!localStorage.getItem("tema")) {
      if (e.matches) document.documentElement.setAttribute("data-theme", "dark");
      else document.documentElement.removeAttribute("data-theme");
    }
  });
})();

const DarkMode = {
  toggle() {
    const isDark = document.documentElement.getAttribute("data-theme") === "dark";
    if (isDark) {
      document.documentElement.removeAttribute("data-theme");
      localStorage.setItem("tema", "claro");
    } else {
      document.documentElement.setAttribute("data-theme", "dark");
      localStorage.setItem("tema", "oscuro");
    }
    const icono = document.getElementById("icono-tema");
    if (icono) icono.className = isDark ? "bi-moon" : "bi-sun";
  }
};

const Sidebar = {

  /* Cada entrada puede declarar el permiso que necesita. Si el servidor
     no se lo dio a este usuario, la entrada no se dibuja: asi el menu
     nunca lleva a una pantalla que va a responder "no puedes". */
  menus: {
    SUPERADMIN: [
      { label: "Dashboard",   icon: "bi-grid-1x2",     href: "/superadmin/dashboard" },
      { label: "Usuarios",    icon: "bi-people",        href: "/superadmin/usuarios",
        permiso: ["usuarios", "ver"] },
      { label: "Facultades",  icon: "bi-building",      href: "/superadmin/facultades",
        permiso: ["facultades", "ver"] },
      { label: "Reportes",    icon: "bi-bar-chart",     href: "/superadmin/reportes",
        permiso: ["reportes", "ver"] },
      { label: "Configuracion",icon:"bi-gear",          href: "/superadmin/configuracion" }
    ],
    ADMIN: [
      { label: "Dashboard",   icon: "bi-grid-1x2",     href: "/facultad/dashboard" },
      { label: "Usuarios",    icon: "bi-people",        href: "/facultad/usuarios",
        permiso: ["usuarios", "ver"] },
      { label: "Cursos",      icon: "bi-book",          href: "/facultad/cursos",
        permiso: ["cursos", "ver"] },
      { label: "Reportes",    icon: "bi-bar-chart",     href: "/facultad/reportes",
        permiso: ["reportes", "ver"] }
    ],
    PROFESOR: [
      { label: "Mis Cursos",  icon: "bi-book-half",     href: "/profesor/mis-cursos" }
    ],
    ESTUDIANTE: [
      { label: "Mis Cursos",  icon: "bi-book-half",     href: "/estudiante/mis-cursos" },
      { label: "Calificaciones",icon:"bi-award",        href: "/estudiante/calificaciones" },
      { label: "Progreso",    icon: "bi-graph-up-arrow",href: "/estudiante/progreso" }
    ]
  },

  /* El rol con el que se entro. Lo dijo el servidor en el login y se
     guardo en la sesion; aqui no se vuelve a deducir, porque deducirlo mal
     significaria ensenar el menu de otro. */
  rolActual(usuario) {
    const guardado = sessionStorage.getItem("rol_efectivo");
    if (guardado) return guardado;

    /* Sesion antigua o modo demo: se deduce como se hacia antes. */
    if (usuario.rol === "SUPERADMIN" || usuario.rol === "ADMIN") return usuario.rol;
    return sessionStorage.getItem("rol_activo") === "PROFESOR" ? "PROFESOR" : "ESTUDIANTE";
  },

  getMenuByRol(usuario) {
    const items = this.menus[this.rolActual(usuario)] || this.menus.ESTUDIANTE;

    /* window.Permisos existe en cuanto se cargo api.js; en modo demo deja
       pasar todo, que es lo que hacia el sitio antes. */
    if (!window.Permisos) return items;

    return items.filter(item =>
      !item.permiso || window.Permisos.puede(item.permiso[0], item.permiso[1]));
  },

  render(usuario, paginaActual = "") {
    const items = this.getMenuByRol(usuario);
    const iniciales = DB.iniciales(usuario.nombres, usuario.apellidos);
    const rolLabel = {
      SUPERADMIN: "Super Admin",
      ADMIN:      "Admin Facultad",
      PROFESOR:   "Profesor",
      ESTUDIANTE: "Estudiante"
    }[this.rolActual(usuario)] || "Usuario";

    const navItems = items.map(item => {
      const activo = paginaActual.includes(item.href.split("/").pop()) ? "active" : "";
      return `
        <a href="${item.href}" class="nav-item ${activo}">
          <i class="${item.icon}"></i>
          <span>${item.label}</span>
        </a>`;
    }).join("");

    return `
      <aside class="sidebar" id="sidebar">
        <div class="sidebar-brand">
          <div class="sidebar-brand-icon">
            <i class="bi-mortarboard-fill"></i>
          </div>
          <div class="sidebar-brand-text">
            <strong>EspolAcademics</strong>
            <span>${rolLabel}</span>
          </div>
        </div>

        <nav class="sidebar-nav">
          <div class="sidebar-section-label">Menu principal</div>
          ${navItems}
        </nav>

        <div class="sidebar-footer">
          <div class="sidebar-user">
            <div class="avatar">${iniciales}</div>
            <div class="sidebar-user-info">
              <strong>${usuario.nombres} ${usuario.apellidos.split(" ")[0]}</strong>
              <span>${usuario.correo}</span>
            </div>
            <button class="btn-logout" onclick="DarkMode.toggle()" title="Cambiar tema" id="btn-tema">
              <i class="${localStorage.getItem('tema') === 'oscuro' ? 'bi-sun' : 'bi-moon'}" id="icono-tema"></i>
            </button>
            <button class="btn-logout" onclick="Auth.logout()" title="Cerrar sesion">
              <i class="bi-box-arrow-right"></i>
            </button>
          </div>
        </div>
      </aside>`;
  },

  inject(usuario, paginaActual = "") {
    const contenedor = document.getElementById("sidebar-container");
    if (contenedor) contenedor.innerHTML = this.render(usuario, paginaActual);

    /* Toggle movil */
    const toggle = document.getElementById("btn-menu-toggle");
    const sidebar = document.getElementById("sidebar");
    if (toggle && sidebar) {
      toggle.addEventListener("click", () => sidebar.classList.toggle("open"));
      document.addEventListener("click", (e) => {
        if (!sidebar.contains(e.target) && !toggle.contains(e.target)) {
          sidebar.classList.remove("open");
        }
      });
    }
  }
};

/* ── AVISOS DE LA API ────────────────────────────────────── */
/* Antes los datos venian de localStorage y nunca fallaban. Ahora
   vienen del servidor, que puede responder "no puedes" (403),
   "no existe" (404) o "hay algo que lo impide" (409). Si una de
   esas respuestas se pierde sin que nadie la muestre, el usuario
   ve una pantalla que no hace nada y no sabe por que.

   Esto la recoge y la ensena arriba. No sustituye al manejo de
   errores de cada pagina: es la red debajo, para lo que se
   escape. */
const AvisoApi = {
  mostrar(error) {
    const esPermiso = error?.sinPermiso;
    const caduco = error?.sesionCaducada;

    const caja = document.createElement("div");
    caja.setAttribute("role", "alert");
    caja.style.cssText = `
      position: fixed; top: 16px; left: 50%; transform: translateX(-50%);
      z-index: 9999; max-width: min(560px, calc(100vw - 32px));
      display: flex; gap: 12px; align-items: flex-start;
      padding: 14px 16px; border-radius: 12px;
      background: ${esPermiso ? "#FFFBEB" : "#FEF2F2"};
      color: ${esPermiso ? "#92400E" : "#991B1B"};
      border: 1px solid ${esPermiso ? "#FCD34D" : "#FCA5A5"};
      box-shadow: 0 10px 30px rgba(0,0,0,.15); font-size: .9rem;`;

    const icono = esPermiso ? "bi-shield-lock" : "bi-exclamation-triangle";
    const detalle = error?.detalle
      ? `<div style="opacity:.85; margin-top:4px">${error.detalle}</div>` : "";

    caja.innerHTML = `
      <i class="${icono}" style="font-size:1.2rem; line-height:1.2"></i>
      <div style="flex:1">
        <strong>${error?.message || "No se pudo completar la operacion."}</strong>
        ${detalle}
      </div>
      <button style="background:none;border:0;color:inherit;cursor:pointer;font-size:1.1rem"
              aria-label="Cerrar">&times;</button>`;

    caja.querySelector("button").onclick = () => caja.remove();
    document.body.appendChild(caja);

    /* Si la sesion caduco no hay nada que hacer en esta pagina:
       se avisa y se manda de vuelta al login. */
    if (caduco) {
      setTimeout(() => {
        sessionStorage.clear();
        window.location.href = typeof LOGIN !== "undefined" ? LOGIN : "/";
      }, 2500);
      return;
    }

    setTimeout(() => caja.remove(), 8000);
  },
};

/* Cualquier promesa de la API que nadie atrape acaba aqui. */
window.addEventListener("unhandledrejection", (evento) => {
  const error = evento.reason;
  if (error && error.name === "ErrorApi") {
    evento.preventDefault();
    AvisoApi.mostrar(error);
  }
});
