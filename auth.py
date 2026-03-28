import os
import psycopg2
from dotenv import load_dotenv
from flask import Flask, redirect, url_for, session, render_template_string, request, flash
from authlib.integrations.flask_client import OAuth

app = Flask(__name__)

# ==============================
# CONFIGURACIÓN
# ==============================

load_dotenv('env.env') 

DATABASE_URL = os.getenv("DATABASE_URL")
app.secret_key = os.getenv("SECRET_KEY")

app.secret_key = "CLAVE_SUPER_LARGA_Y_ALEATORIA_2026_CAMBIAR_EN_PRODUCCION"

GOOGLE_CLIENT_ID = "966775310840-78j9h1djoobjsbff5qd2n00va59cmljs.apps.googleusercontent.com"
GOOGLE_CLIENT_SECRET = "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"

app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=True
)

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
# HTML
# ==============================
HTML_HOME = """
<!doctype html>
<html lang="es">
<head>
    <meta charset="utf-8">
    <title>Inicio</title>
</head>
<body>
    <h1>Login con Google en Flask</h1>

    {% with messages = get_flashed_messages() %}
      {% if messages %}
        <ul style="color: green;">
          {% for msg in messages %}
            <li>{{ msg }}</li>
          {% endfor %}
        </ul>
      {% endif %}
    {% endwith %}

    {% if user %}
        <h2 style="color: green;">✅ Usuario autenticado con Google</h2>
        <p><b>Nombre:</b> {{ user.get("name", "N/A") }}</p>
        <p><b>Correo:</b> {{ user.get("email", "N/A") }}</p>
        <p><b>Correo verificado:</b> {{ user.get("email_verified", False) }}</p>

        {% if user.get("picture") %}
            <p><img src="{{ user.get('picture') }}" width="100" alt="Foto de perfil"></p>
        {% endif %}

        <p><a href="{{ url_for('privado') }}">Ir a zona privada</a></p>
        <p><a href="{{ url_for('logout') }}">Cerrar sesión</a></p>
    {% else %}
        <p>No has iniciado sesión.</p>
        <p><a href="{{ url_for('login') }}">Iniciar sesión con Google</a></p>
    {% endif %}
</body>
</html>
"""

HTML_PRIVADO = """
<!doctype html>
<html lang="es">
<head>
    <meta charset="utf-8">
    <title>Zona privada</title>
</head>
<body>
    <h1>Zona privada</h1>

    {% with messages = get_flashed_messages() %}
      {% if messages %}
        <ul style="color: blue;">
          {% for msg in messages %}
            <li>{{ msg }}</li>
          {% endfor %}
        </ul>
      {% endif %}
    {% endwith %}

    <p>Has iniciado sesión como: <b>{{ user.get("email", "N/A") }}</b></p>
    <p>Nombre: <b>{{ user.get("name", "N/A") }}</b></p>
    <p style="color: green;"><b>Mensaje:</b> Usuario autenticado correctamente con Google.</p>

    <hr>
    <h3>Enviar mensaje simple</h3>
    <form method="post" action="{{ url_for('enviar_mensaje') }}">
        <label>Escribe un mensaje:</label><br><br>
        <input type="text" name="mensaje" style="width: 300px;" required>
        <button type="submit">Enviar</button>
    </form>

    {% if ultimo_mensaje %}
        <p style="margin-top:20px; color: darkred;">
            <b>Último mensaje enviado por {{ user.get("name", "N/A") }}:</b>
            {{ ultimo_mensaje }}
        </p>
    {% endif %}

    <p><a href="{{ url_for('home') }}">Volver al inicio</a></p>
    <p><a href="{{ url_for('logout') }}">Cerrar sesión</a></p>
</body>
</html>
"""

# ==============================
# RUTAS
# ==============================

def test_db():
    try:
        conn = psycopg2.connect(os.getenv("DATABASE_URL"))
        print("¡Conectao a la base de datos de los Pokémon, cuadro!")
        conn.close()
    except Exception as e:
        print(f"Lío con la conexión: {e}")

test_db()

@app.route("/")
def home():
    user = session.get("user")
    return render_template_string(HTML_HOME, user=user)

@app.route("/login")
def login():
    redirect_uri = "https://web-pg59.onrender.com/callback"
    return google.authorize_redirect(redirect_uri)

@app.route("/callback")
def auth_callback():
    try:
        token = google.authorize_access_token()
        user_info = token.get("userinfo")

        if not user_info:
            resp = google.get("https://openidconnect.googleapis.com/v1/userinfo")
            user_info = resp.json()

        session["user"] = {
            "sub": user_info.get("sub"),
            "name": user_info.get("name"),
            "email": user_info.get("email"),
            "email_verified": user_info.get("email_verified"),
            "picture": user_info.get("picture"),
        }

        flash("Autenticación exitosa. Bienvenido/a.")
        return redirect(url_for("privado"))

    except Exception as e:
        return f"Error en autenticación: {str(e)}", 500

@app.route("/privado")
def privado():
    user = session.get("user")
    if not user:
        return redirect(url_for("login"))

    ultimo_mensaje = session.get("ultimo_mensaje")
    return render_template_string(
        HTML_PRIVADO,
        user=user,
        ultimo_mensaje=ultimo_mensaje
    )

@app.route("/enviar-mensaje", methods=["POST"])
def enviar_mensaje():
    user = session.get("user")
    if not user:
        return redirect(url_for("login"))

    mensaje = request.form.get("mensaje", "").strip()
    if not mensaje:
        flash("Debes escribir un mensaje.")
        return redirect(url_for("privado"))

    session["ultimo_mensaje"] = mensaje
    flash(f'Mensaje enviado por {user.get("name", "Usuario")}.')
    return redirect(url_for("privado"))

@app.route("/logout")
def logout():
    session.clear()
    flash("Sesión cerrada correctamente.")
    return redirect(url_for("home"))

# ==============================
# MAIN
# ==============================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
