from flask import Blueprint, render_template, request, redirect, url_for, session
from auth import iniciar_sesion, cerrar_sesion

auth_bp = Blueprint("auth_bp", __name__)


def _redirigir_segun_rol():
    rol = session.get("rol")
    if rol == "admin":
        return redirect(url_for("admin_bp.dashboard"))
    if rol == "coordinadora":
        return redirect(url_for("coordinadora_bp.dashboard"))
    return redirect(url_for("doctor_bp.dashboard"))


@auth_bp.route("/", methods=["GET"])
def index():
    if "user_id" in session:
        return _redirigir_segun_rol()
    return redirect(url_for("auth_bp.login"))


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    email = request.form.get("email", "").strip()
    password = request.form.get("password", "")

    if not email or not password:
        return render_template("login.html", error="Ingresa tu correo y contraseña.")

    ok, error = iniciar_sesion(email, password)
    if not ok:
        return render_template("login.html", error=error)

    return _redirigir_segun_rol()


@auth_bp.route("/logout")
def logout():
    cerrar_sesion()
    return redirect(url_for("auth_bp.login"))
