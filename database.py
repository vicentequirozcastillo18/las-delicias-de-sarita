import sqlite3
from datetime import datetime

DB_PATH = "pedidos.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS pedidos (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre    TEXT NOT NULL,
            telefono  TEXT NOT NULL,
            detalle   TEXT NOT NULL,
            total     INTEGER NOT NULL,
            medio_pago TEXT NOT NULL DEFAULT 'efectivo',
            fecha     TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

def guardar_pedido(nombre, telefono, detalle, total, medio_pago="efectivo"):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    fecha = datetime.now().strftime("%d/%m/%Y %H:%M")
    c.execute(
        "INSERT INTO pedidos (nombre, telefono, detalle, total, medio_pago, fecha) VALUES (?, ?, ?, ?, ?, ?)",
        (nombre, telefono, detalle, total, medio_pago, fecha)
    )
    conn.commit()
    conn.close()

def obtener_pedidos():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM pedidos ORDER BY id DESC")
    pedidos = c.fetchall()
    conn.close()
    return pedidos
