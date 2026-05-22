from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from database import init_db, guardar_pedido, obtener_pedidos
import json

app = Flask(__name__)
app.secret_key = "sarita_secret_key_2024"

PRODUCTOS = {
    "palmeritas": {"nombre": "Palmeritas", "precio": 1000},
    "alfajores":  {"nombre": "Alfajores",  "precio": 1100},
    "trufas":     {"nombre": "Trufas",     "precio": 1200},
}

@app.route("/")
def index():
    carrito = session.get("carrito", {})
    total = sum(
        PRODUCTOS[k]["precio"] * v
        for k, v in carrito.items()
        if k in PRODUCTOS
    )
    return render_template("index.html", productos=PRODUCTOS, carrito=carrito, total=total)


@app.route("/agregar/<producto>")
def agregar(producto):
    if producto not in PRODUCTOS:
        return redirect(url_for("index"))
    carrito = session.get("carrito", {})
    carrito[producto] = carrito.get(producto, 0) + 1
    session["carrito"] = carrito
    return redirect(url_for("index"))


@app.route("/actualizar", methods=["POST"])
def actualizar():
    producto = request.form.get("producto")
    cantidad = int(request.form.get("cantidad", 0))
    carrito = session.get("carrito", {})
    if cantidad <= 0:
        carrito.pop(producto, None)
    else:
        carrito[producto] = cantidad
    session["carrito"] = carrito
    return redirect(url_for("index"))


@app.route("/vaciar")
def vaciar():
    session["carrito"] = {}
    return redirect(url_for("index"))


@app.route("/confirmar", methods=["POST"])
def confirmar():
    nombre    = request.form.get("nombre", "").strip()
    telefono  = request.form.get("telefono", "").strip()
    carrito   = session.get("carrito", {})

    if not nombre or not telefono or not carrito:
        return redirect(url_for("index"))

    detalle = {k: v for k, v in carrito.items() if k in PRODUCTOS}
    total = sum(PRODUCTOS[k]["precio"] * v for k, v in detalle.items())

    guardar_pedido(nombre, telefono, json.dumps(detalle, ensure_ascii=False), total)
    session["carrito"] = {}
    session["pedido_confirmado"] = {"nombre": nombre, "total": total}
    return redirect(url_for("gracias"))


@app.route("/gracias")
def gracias():
    pedido = session.pop("pedido_confirmado", None)
    return render_template("gracias.html", pedido=pedido)


@app.route("/admin/pedidos")
def admin_pedidos():
    pedidos = obtener_pedidos()
    return render_template("admin.html", pedidos=pedidos, productos=PRODUCTOS)


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
