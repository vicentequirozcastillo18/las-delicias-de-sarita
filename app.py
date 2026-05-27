from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from database import init_db, guardar_pedido, obtener_pedidos
import json
import requests

app = Flask(__name__)
app.secret_key = "sarita_secret_key_2024"

MP_ACCESS_TOKEN = "APP_USR-7515760448910450-052719-3f9db43f11d2b88fd2a98061042a5a92-2665234703"

PRODUCTOS = {
    "palmeritas":          {"nombre": "Palmeritas",          "precio": 1000},
    "alfajores":           {"nombre": "Alfajores",           "precio": 1100},
    "trufas":              {"nombre": "Trufas",              "precio": 1200},
    "tartaleta_fruta":     {"nombre": "Tartaleta de Fruta",  "precio": 3000},
    "kuchen":              {"nombre": "Kuchen",              "precio": 4200},
    "torta_fruta":         {"nombre": "Torta de Fruta",      "precio": 5000},
    "tartaleta_arandanos": {"nombre": "Tartaleta de Arándanos", "precio": 4500},
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
    nombre   = request.form.get("nombre", "").strip()
    telefono = request.form.get("telefono", "").strip()
    pago     = request.form.get("medio_pago", "efectivo")
    carrito  = session.get("carrito", {})

    if not nombre or not telefono or not carrito:
        return redirect(url_for("index"))

    detalle = {k: v for k, v in carrito.items() if k in PRODUCTOS}
    total   = sum(PRODUCTOS[k]["precio"] * v for k, v in detalle.items())

    session["datos_pedido"] = {
        "nombre": nombre,
        "telefono": telefono,
        "detalle": detalle,
        "total": total,
        "pago": pago
    }

    if pago == "mercadopago":
        items = []
        for key, cantidad in detalle.items():
            items.append({
                "title": PRODUCTOS[key]["nombre"],
                "quantity": cantidad,
                "unit_price": PRODUCTOS[key]["precio"],
                "currency_id": "CLP"
            })

        preference_data = {
            "items": items,
            "payer": {"name": nombre},
            "back_urls": {
                "success": url_for("pago_exitoso", _external=True),
                "failure": url_for("pago_fallido", _external=True),
                "pending": url_for("pago_pendiente", _external=True),
            },
            "auto_return": "approved",
            "statement_descriptor": "Las Delicias de Sarita"
        }

        headers = {
            "Authorization": f"Bearer {MP_ACCESS_TOKEN}",
            "Content-Type": "application/json"
        }

        resp = requests.post(
            "https://api.mercadopago.com/checkout/preferences",
            json=preference_data,
            headers=headers
        )
        data = resp.json()

        if "init_point" in data:
            return redirect(data["init_point"])
        else:
            return f"Error al crear pago: {data}", 500
    else:
        guardar_pedido(nombre, telefono, json.dumps(detalle, ensure_ascii=False), total, "efectivo")
        session["carrito"] = {}
        session["pedido_confirmado"] = {"nombre": nombre, "total": total}
        return redirect(url_for("gracias"))


@app.route("/pago/exitoso")
def pago_exitoso():
    datos = session.pop("datos_pedido", None)
    if datos:
        guardar_pedido(
            datos["nombre"],
            datos["telefono"],
            json.dumps(datos["detalle"], ensure_ascii=False),
            datos["total"],
            "mercadopago"
        )
        session["carrito"] = {}
        session["pedido_confirmado"] = {"nombre": datos["nombre"], "total": datos["total"]}
    return redirect(url_for("gracias"))


@app.route("/pago/fallido")
def pago_fallido():
    return render_template("pago_fallido.html")


@app.route("/pago/pendiente")
def pago_pendiente():
    return render_template("pago_pendiente.html")


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
