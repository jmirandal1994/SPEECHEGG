from functools import wraps
from flask import session, redirect, url_for, flash, g
from supabase_client import get_client, get_admin_client


def iniciar_sesion(email: str, password: str):
    """
    Autentica contra Supabase Auth. Devuelve (ok: bool, mensaje_error: str|None).
    Si es exitoso, guarda tokens y perfil en la sesión de Flask (cookie firmada).
    """
    client = get_client()
    try:
        resultado = client.auth.sign_in_with_password({"email": email, "password": password})
    except Exception:
        return False, "Usuario o contraseña incorrectos."

    if not resultado.session:
        return False, "Usuario o contraseña incorrectos."

    user_id = resultado.user.id

    # Traemos el perfil (rol, nombre) con el cliente admin para no depender
    # de que la sesión recién creada ya tenga permisos propagados.
    admin = get_admin_client()
    perfil_res = admin.table("profiles").select("*").eq("id", user_id).single().execute()
    perfil = perfil_res.data

    if not perfil or not perfil.get("activo", True):
        return False, "Esta cuenta no está activa. Contacta al administrador."

    session["access_token"] = resultado.session.access_token
    session["refresh_token"] = resultado.session.refresh_token
    session["user_id"] = user_id
    session["nombre"] = perfil["nombre"]
    session["rol"] = perfil["rol"]
    session.permanent = True
    return True, None


def cerrar_sesion():
    client = get_client(session.get("access_token"), session.get("refresh_token"))
    try:
        client.auth.sign_out()
    except Exception:
        pass  # si el token ya expiró, no importa: igual limpiamos la sesión local
    session.clear()


def requiere_login(vista):
    @wraps(vista)
    def envoltura(*args, **kwargs):
        if "user_id" not in session:
            flash("Debes iniciar sesión para continuar.", "warning")
            return redirect(url_for("auth_bp.login"))
        g.user_id = session["user_id"]
        g.rol = session["rol"]
        g.nombre = session["nombre"]
        return vista(*args, **kwargs)
    return envoltura


def requiere_admin(vista):
    @wraps(vista)
    def envoltura(*args, **kwargs):
        if "user_id" not in session:
            flash("Debes iniciar sesión para continuar.", "warning")
            return redirect(url_for("auth_bp.login"))
        if session.get("rol") != "admin":
            flash("No tienes permisos para acceder a esta sección.", "danger")
            return redirect(url_for("doctor_bp.dashboard"))
        g.user_id = session["user_id"]
        g.rol = session["rol"]
        g.nombre = session["nombre"]
        return vista(*args, **kwargs)
    return envoltura
