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

  menus: {
    SUPERADMIN: [
      { label: "Dashboard",   icon: "bi-grid-1x2",     href: "/superadmin/dashboard" },
      { label: "Usuarios",    icon: "bi-people",        href: "/superadmin/usuarios" },
      { label: "Facultades",  icon: "bi-building",      href: "/superadmin/facultades" },
      { label: "Reportes",    icon: "bi-bar-chart",     href: "/superadmin/reportes" },
      { label: "Configuracion",icon:"bi-gear",          href: "/superadmin/configuracion" }
    ],
    ADMIN: [
      { label: "Dashboard",   icon: "bi-grid-1x2",     href: "/facultad/dashboard" },
      { label: "Usuarios",    icon: "bi-people",        href: "/facultad/usuarios" },
      { label: "Cursos",      icon: "bi-book",          href: "/facultad/cursos" },
      { label: "Reportes",    icon: "bi-bar-chart",     href: "/facultad/reportes" }
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

  getMenuByRol(usuario) {
    if (usuario.rol === "SUPERADMIN") return this.menus.SUPERADMIN;
    if (usuario.rol === "ADMIN")      return this.menus.ADMIN;
    /* Para USER determinamos el rol activo de curso guardado en sesion */
    const rolCurso = sessionStorage.getItem("rol_activo") || "ESTUDIANTE";
    return rolCurso === "PROFESOR" ? this.menus.PROFESOR : this.menus.ESTUDIANTE;
  },

  render(usuario, paginaActual = "") {
    const items = this.getMenuByRol(usuario);
    const iniciales = DB.iniciales(usuario.nombres, usuario.apellidos);
    const rolLabel = {
      SUPERADMIN: "Super Admin",
      ADMIN:      "Admin Facultad",
      USER:       sessionStorage.getItem("rol_activo") === "PROFESOR" ? "Profesor" : "Estudiante"
    }[usuario.rol] || "Usuario";

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
