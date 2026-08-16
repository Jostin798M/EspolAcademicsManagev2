const Auth = {

  async login() {
    const correo   = document.getElementById("correo").value.trim();
    const password = document.getElementById("password").value;
    const btnLogin = document.getElementById("btn-login");

    this.clearErrors();

    let valido = true;
    if (!correo) {
      this.showError("error-correo", "El correo es obligatorio.");
      valido = false;
    } else if (!this.validarEmail(correo)) {
      this.showError("error-correo", "Ingresa un correo valido.");
      valido = false;
    }
    if (!password) {
      this.showError("error-password", "La contrasena es obligatoria.");
      valido = false;
    } else if (password.length < 6) {
      this.showError("error-password", "Minimo 6 caracteres.");
      valido = false;
    }
    if (!valido) return;

    btnLogin.disabled = true;
    btnLogin.innerHTML = '<i class="bi-arrow-repeat"></i> Ingresando...';

    try {
      const data = await API.login(correo, password);
      const usuario = data.usuario;

      /* El backend manda "id"; si respondiera una version antigua sin ese
         campo, se guardaria un id vacio y la propia pagina de destino nos
         echaria de vuelta aqui. Mejor decirlo claro. */
      const id = usuario.id ?? usuario.id_usuario;
      if (!id) throw new Error(
        "El servidor respondio sin identificar al usuario. " +
        "Reinicia el sitio para que cargue la ultima version.");

      sessionStorage.setItem("usuario_id", id);
      sessionStorage.setItem("usuario_data", JSON.stringify(usuario));

      /* El rol con el que se entra lo decide el servidor, no esta pagina.
         Un USER puede ser profesor o estudiante segun sus inscripciones, y
         quien sabe eso es la base de datos. Aqui solo se guarda para que el
         menu y las redirecciones sepan a donde llevarlo. */
      const rol = data.rol || usuario.rol_efectivo || data.rol_activo || usuario.rol;
      sessionStorage.setItem("rol_efectivo", rol);
      if (data.rol_activo) sessionStorage.setItem("rol_activo", data.rol_activo);

      this.redirigir(rol);
    } catch (err) {
      /* El servidor explica el motivo aparte del mensaje; si lo mando, se
         ensena, porque "cuenta inactiva" y "contrasena incorrecta" piden
         cosas distintas del usuario. */
      const detalle = err.detalle ? ` ${err.detalle}` : "";
      this.showError("error-form", err.message + detalle);
      btnLogin.disabled = false;
      btnLogin.innerHTML = '<i class="bi-box-arrow-in-right"></i> Ingresar';
    }
  },

  /* A donde va cada rol al entrar. */
  redirigir(rol) {
    const rutas = {
      SUPERADMIN: "/superadmin/dashboard",
      ADMIN:      "/facultad/dashboard",
      PROFESOR:   "/profesor/mis-cursos",
      ESTUDIANTE: "/estudiante/mis-cursos",
    };
    window.location.href = rutas[rol] || LOGIN;
  },

  /* Un solo "Salir": cierra la sesion de Django (y con ella el acceso
     a /admin/, /panel/ y la API) ademas de la del navegador. */
  async logout() {
    try { await API.logout(); } catch { /* en modo demo no hay servidor */ }
    sessionStorage.clear();
    window.location.href = LOGIN;
  },

  getUsuarioActivo() {
    const id = parseInt(sessionStorage.getItem("usuario_id"));
    if (!id) { window.location.href = LOGIN; return null; }
    try {
      const data = sessionStorage.getItem("usuario_data");
      return data ? JSON.parse(data) : null;
    } catch {
      window.location.href = LOGIN;
      return null;
    }
  },

  validarEmail(email) {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
  },

  showError(id, mensaje) {
    const el = document.getElementById(id);
    if (el) { el.textContent = mensaje; el.style.display = "block"; }
  },

  clearErrors() {
    ["error-correo", "error-password", "error-form"].forEach(id => {
      const el = document.getElementById(id);
      if (el) { el.textContent = ""; el.style.display = "none"; }
    });
    document.querySelectorAll(".form-control").forEach(el => el.classList.remove("is-invalid"));
  }
};

/* Enter para submit */
document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("login-form");
  if (form) {
    form.addEventListener("keydown", (e) => {
      if (e.key === "Enter") Auth.login();
    });
  }
});
