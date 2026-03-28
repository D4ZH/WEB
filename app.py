import os
import psycopg2
from flask import Flask, request, redirect, url_for, session, render_template_string, flash
from dotenv import load_dotenv

# ==============================
# CONFIGURACIÓN
# ==============================
if os.path.exists("env.env"):
    load_dotenv("env.env")

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "CLAVE_POR_DEFECTO_2026")

DATABASE_URL = os.getenv("DATABASE_URL")

IS_PRODUCTION = os.getenv("RENDER", False)
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=bool(IS_PRODUCTION)
)

# ==============================
# CONEXIÓN A NEON
# ==============================
def get_db_connection():
    try:
        # psycopg2 no soporta channel_binding, lo removemos si viene en la URL
        clean_url = DATABASE_URL.replace("&channel_binding=require", "").replace("?channel_binding=require", "")
        conn = psycopg2.connect(clean_url)
        return conn
    except Exception as e:
        print(f"Error conectando a la base de datos: {e}")
        return None

# ==============================
# TEMPLATES
# ==============================
HTML_HOME = """
<!doctype html>
<html lang="es">
<head><meta charset="utf-8"><title>Inicio</title></head>
<body>
    <h1>Bienvenido</h1>

    {% with messages = get_flashed_messages() %}
      {% if messages %}
        <ul style="color: green;">
          {% for msg in messages %}<li>{{ msg }}</li>{% endfor %}
        </ul>
      {% endif %}
    {% endwith %}

    {% if session.usuario %}
        <p>Hola, <b>{{ session.usuario }}</b>!</p>
        <p><a href="{{ url_for('privado') }}">Ir a zona privada</a></p>
        <p><a href="{{ url_for('logout') }}">Cerrar sesión</a></p>
    {% else %}
        <p>No has iniciado sesión.</p>
        <p><a href="{{ url_for('login') }}">Iniciar sesión</a></p>
    {% endif %}
</body>
</html>
"""

HTML_LOGIN = """
<!doctype html>
<html lang="es">
<head><meta charset="utf-8"><title>Login</title></head>
<body>
    <h1>Iniciar sesión</h1>

    {% if error %}
        <p style="color: red;">{{ error }}</p>
    {% endif %}

    <form method="post">
        <label>Usuario:</label><br>
        <input type="text" name="username" required><br><br>

        <label>Contraseña:</label><br>
        <input type="password" name="clave" required><br><br>

        <button type="submit">Entrar</button>
    </form>

    <br>
    <a href="{{ url_for('home') }}">Volver al inicio</a>
</body>
</html>
"""

HTML_PRIVADO = """
<!doctype html>
<html lang="es">
<head><meta charset="utf-8"><title>Zona Privada</title></head>
<body>
    <h1>Zona privada</h1>
    <p>Sesión activa como: <b>{{ session.usuario }}</b></p>
    <p>Este contenido solo lo ve un usuario autenticado.</p>
    <p><a href="{{ url_for('logout') }}">Cerrar sesión</a></p>
    <p><a href="{{ url_for('home') }}">Volver al inicio</a></p>
</body>
</html>
"""

# ==============================
# RUTAS
# ==============================
@app.route("/")
def home():
    return render_template_string(HTML_HOME)

@app.route("/login", methods=["GET", "POST"])
def login():
    error = None

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        clave = request.form.get("clave", "").strip()

        conn = get_db_connection()
        if not conn:
            error = "No se pudo conectar a la base de datos. Intenta más tarde."
        else:
            try:
                cur = conn.cursor()
                cur.execute(
                    "SELECT id FROM users WHERE username = %s AND clave = %s;",
                    (username, clave)
                )
                user = cur.fetchone()
                cur.close()
                conn.close()

                if user:
                    session["usuario"] = username
                    flash(f"Bienvenido, {username}!")
                    return redirect(url_for("privado"))
                else:
                    error = "Usuario o contraseña incorrectos."
            except Exception as e:
                error = f"Error consultando la base de datos: {e}"
                print(error)

    return render_template_string(HTML_LOGIN, error=error)

@app.route("/privado")
def privado():
    if "usuario" not in session:
        return redirect(url_for("login"))
    return render_template_string(HTML_PRIVADO)

@app.route("/logout")
def logout():
    session.clear()
    flash("Sesión cerrada correctamente.")
    return redirect(url_for("home"))

if __name__ == "__main__":
    app.run(debug=True)
