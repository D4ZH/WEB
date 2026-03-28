import os
import psycopg2
from flask import Flask, redirect, url_for, session, render_template_string, request, flash
from authlib.integrations.flask_client import OAuth
from dotenv import load_dotenv
 
# ==============================
# CARGA DE CONFIGURACIÓN
# ==============================
if os.path.exists("env.env"):
    load_dotenv("env.env")
 
app = Flask(__name__)
 
app.secret_key = os.getenv("SECRET_KEY", "CLAVE_POR_DEFECTO_BACANA_2026")
DATABASE_URL = os.getenv("DATABASE_URL")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
 
# En producción (Render) las cookies deben ser Secure=True
# En desarrollo local sin HTTPS, ponlo en False o usa una variable de entorno
IS_PRODUCTION = os.getenv("RENDER", False)  # Render inyecta esta variable automáticamente
 
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=bool(IS_PRODUCTION)  # True en Render, False en local
)
 
# ==============================
# CONEXIÓN A NEON (POSTGRESQL)
# ==============================
def get_db_connection():
    try:
        # BUG FIX: channel_binding=require no es soportado por psycopg2, lo removemos
        clean_url = DATABASE_URL.replace("&channel_binding=require", "").replace("?channel_binding=require", "")
        conn = psycopg2.connect(clean_url)
        return conn
    except Exception as e:
        print(f"Error conectando a la base de datos: {e}")
        return None
 
# ==============================
# OAUTH GOOGLE
# ==============================
oauth = OAuth(app)
google = oauth.register(
    name="google",
    client_id=GOOGLE_CLIENT_ID,
    client_secret=GOOGLE_CLIENT_SECRET,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={
        "scope": "openid email profile"
    },
)
 
# ==============================
# HTML TEMPLATES
# ==============================
HTML_HOME = """
<!doctype html>
<html lang="es">
<head><meta charset="utf-8"><title>Inicio</title></head>
<body>
    <h1>App con Google y Neon</h1>
    {% with messages = get_flashed_messages() %}
      {% if messages %}<ul style="color: blue;">{% for msg in messages %}<li>{{ msg }}</li>{% endfor %}</ul>{% endif %}
    {% endwith %}
    {% if session.user %}
        <p>Hola, {{ session.user.name }}! <a href="{{ url_for('privado') }}">Ir a zona privada</a></p>
        <p><a href="{{ url_for('logout') }}">Cerrar sesión</a></p>
    {% else %}
        <a href="{{ url_for('login') }}">Iniciar sesión con Google</a>
    {% endif %}
</body>
</html>
"""
 
HTML_PRIVADO = """
<!doctype html>
<html lang="es">
<head><meta charset="utf-8"><title>Zona Privada</title></head>
<body>
    <h1>Bienvenido, {{ user.name }}</h1>
    <img src="{{ user.picture }}" width="50"><br>
    <p>Email: {{ user.email }}</p>
    
    <hr>
    <h3>Lista de Usuarios (Desde Neon)</h3>
    {% if pokemones %}
    <ul>
    {% for p in pokemones %}
        <li>ID: {{ p[0] }} - Usuario: <b>{{ p[1] }}</b></li>
    {% endfor %}
    </ul>
    {% else %}
        <p style="color: orange;">No se encontraron registros en la base de datos.</p>
    {% endif %}
    
    <a href="{{ url_for('logout') }}">Cerrar sesión</a>
    <a href="{{ url_for('home') }}">Volver al inicio</a>
</body>
</html>
"""
 
# ==============================
# RUTAS
# ==============================
@app.route("/")
def home():
    return render_template_string(HTML_HOME)
 
@app.route("/login")
def login():
    redirect_uri = url_for("auth_callback", _external=True)
    return google.authorize_redirect(redirect_uri)
 
@app.route("/callback")
def auth_callback():
    try:
        token = google.authorize_access_token()
 
        # BUG FIX: parse_id_token() fue removido en Authlib moderno
        # El userinfo viene directo en el token después de authorize_access_token()
        user_info = token.get("userinfo")
 
        if not user_info:
            # Fallback: pedirlo explícitamente al endpoint de Google
            resp = google.get("https://openidconnect.googleapis.com/v1/userinfo")
            user_info = resp.json()
 
        session["user"] = {
            "sub": user_info.get("sub"),
            "name": user_info.get("name"),
            "email": user_info.get("email"),
            "picture": user_info.get("picture"),
        }
        flash("¡Autenticación exitosa!")
        return redirect(url_for("privado"))
    except Exception as e:
        return f"Error en autenticación: {str(e)}", 500
 
@app.route("/privado")
def privado():
    user = session.get("user")
    if not user:
        return redirect(url_for("home"))
    
    conn = get_db_connection()
    pokemones = []
    if conn:
        try:
            cur = conn.cursor()
            cur.execute("SELECT id, username FROM users ORDER BY id ASC LIMIT 20;")
            pokemones = cur.fetchall()
            cur.close()
        except Exception as e:
            flash(f"Error consultando la DB: {e}")
        finally:
            conn.close()
    else:
        flash("No se pudo conectar a la base de datos.")
    
    return render_template_string(HTML_PRIVADO, user=user, pokemones=pokemones)
 
@app.route("/logout")
def logout():
    session.clear()
    flash("Sesión cerrada. ¡Hasta luego!")
    return redirect(url_for("home"))
 
if __name__ == "__main__":
    app.run(debug=True)
