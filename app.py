from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from database import init_db, guardar_pedido, obtener_pedidos
import json
import requests
import os

app = Flask(__name__)
app.secret_key = "sarita_secret_key_2024"

MP_ACCESS_TOKEN = os.environ.get("MP_ACCESS_TOKEN", "")
GEMINI_API_KEY  = os.environ.get("GEMINI_API_KEY", "")

PRODUCTOS = {
    "palmeritas":          {"nombre": "Palmeritas",             "precio": 1000},
    "alfajores":           {"nombre": "Alfajores",              "precio": 1100},
    "trufas":              {"nombre": "Trufas",                 "precio": 1200},
    "tartaleta_fruta":     {"nombre": "Tartaleta de Fruta",     "precio": 3000},
    "kuchen":              {"nombre": "Kuchen",                 "precio": 4200},
    "torta_fruta":         {"nombre": "Torta de Fruta",        "precio": 5000},
    "tartaleta_arandanos": {"nombre": "Tartaleta de Arándanos", "precio": 4500},
}

SISTEMA_SARITA = """Eres Sarita, la asistente virtual de la pastelería "Las Delicias de Sarita".
Eres amable, cálida y entusiasta. Ayudas a los clientes con preguntas sobre los productos, precios, pedidos y cualquier consulta relacionada con la pastelería.

Productos disponibles:
- Palmeritas: $1.000 c/u - Crujientes y caramelizadas
- Alfajores: $1.100 c/u - Rellenos de manjar, cubiertos de coco rallado
- Trufas: $1.200 c/u - Intensas, cremosas y bañadas en chocolate fino
- Tartaleta de Fruta: $3.000 c/u - Masa crocante con crema y frutas frescas
- Kuchen: $4.200 c/u - Tradicional kuchen alemán
- Torta de Fruta: $5.000 c/u - Esponjosa torta con crema y frutas frescas
- Tartaleta de Arándanos: $4.500 c/u - Masa crocante con crema y arándanos frescos

Para hacer un pedido, el cliente debe agregar productos al carrito y completar el formulario con su nombre y teléfono.
Se puede pagar en efectivo o con Mercado Pago.
Responde siempre en español, de forma breve y amigable. Usa emojis ocasionalmente."""


@app.route("/")
def index():
    carrito = session.get("carrito", {})
    total = sum(PRODUCTOS[k]["precio"] * v for k, v in carrito.items() if k in PRODUCTOS)
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

    session["datos_pedido"] = {"nombre": nombre, "telefono": telefono, "detalle": detalle, "total": total, "pago": pago}

    if pago == "mercadopago":
        items = [{"title": PRODUCTOS[k]["nombre"], "quantity": v, "unit_price": PRODUCTOS[k]["precio"], "currency_id": "CLP"} for k, v in detalle.items()]
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
        headers = {"Authorization": f"Bearer {MP_ACCESS_TOKEN}", "Content-Type": "application/json"}
        resp = requests.post("https://api.mercadopago.com/checkout/preferences", json=preference_data, headers=headers)
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
        guardar_pedido(datos["nombre"], datos["telefono"], json.dumps(datos["detalle"], ensure_ascii=False), datos["total"], "mercadopago")
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


@app.route("/chatbot", methods=["POST"])
def chatbot():
    data = request.get_json()
    mensaje  = data.get("mensaje", "").strip()
    historial = data.get("historial", [])

    if not mensaje:
        return jsonify({"respuesta": "Por favor escribe tu pregunta 😊"})

    messages = [{"role": m["role"], "parts": [{"text": m["text"]}]} for m in historial[-6:]]
    messages.append({"role": "user", "parts": [{"text": mensaje}]})

    payload = {"system_instruction": {"parts": [{"text": SISTEMA_SARITA}]}, "contents": messages}
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"

    try:
        resp = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=15)
        result = resp.json()
        respuesta = result["candidates"][0]["content"]["parts"][0]["text"]
    except Exception:
        respuesta = "Lo siento, tuve un problema al responder. Intenta de nuevo 😊"

    return jsonify({"respuesta": respuesta})


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
