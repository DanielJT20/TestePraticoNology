from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from decimal import Decimal, ROUND_HALF_UP
import databases
import sqlalchemy
import os
from datetime import datetime

# 1. Primeiro inicializamos o App
app = FastAPI(title="Cashback API")

# 2. Depois configuramos o CORS (Coloquei "*" para facilitar o teste, mas pode manter o seu link do GitHub)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. Configuração do Banco (Pega a URL da nuvem ou usa o local de teste)
# DICA: Se usar Render, a URL começará com postgres://. O 'databases' precisa que mude para postgresql://
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./test.db") # Usei sqlite para teste local fácil
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

database = databases.Database(DATABASE_URL)
metadata = sqlalchemy.MetaData()

consultas = sqlalchemy.Table(
    "consultas",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True),
    sqlalchemy.Column("ip", sqlalchemy.String(45), nullable=False),
    sqlalchemy.Column("tipo_cliente", sqlalchemy.String(10), nullable=False),
    sqlalchemy.Column("valor_compra", sqlalchemy.Numeric(10, 2), nullable=False),
    sqlalchemy.Column("desconto", sqlalchemy.Numeric(5, 2), nullable=False),
    sqlalchemy.Column("valor_final", sqlalchemy.Numeric(10, 2), nullable=False),
    sqlalchemy.Column("cashback", sqlalchemy.Numeric(10, 2), nullable=False),
    sqlalchemy.Column("percentual", sqlalchemy.Numeric(5, 2), nullable=False),
    sqlalchemy.Column("criado_em", sqlalchemy.DateTime, default=datetime.utcnow),
)

class CalcularRequest(BaseModel):
    tipo_cliente: str
    valor_compra: float
    desconto: float = 0.0

def calcular_cashback(tipo_cliente: str, valor_compra: float, desconto: float = 0.0) -> dict:
    tipo = tipo_cliente.lower().strip()
    valor = Decimal(str(valor_compra))
    desc = Decimal(str(desconto))

    valor_final = (valor * (1 - desc / 100)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    percentual_base = Decimal("5.0")
    bonus_vip = Decimal("0.5") if tipo == "vip" else Decimal("0")
    multiplicador = Decimal("2") if valor > Decimal("500") else Decimal("1")

    percentual_final = (percentual_base + bonus_vip) * multiplicador
    cashback = (valor_final * percentual_final / Decimal("100")).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )

    return {
        "valor_final": float(valor_final),
        "percentual": float(percentual_final),
        "cashback": float(cashback),
    }

@app.on_event("startup")
async def startup():
    await database.connect()
    # Cria a tabela automaticamente independente se é MySQL ou Postgres
    engine = sqlalchemy.create_engine(DATABASE_URL.replace("+aiomysql", "").replace("+asyncpg", ""))
    metadata.create_all(engine)

@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()

@app.post("/calcular")
async def calcular(request: Request, body: CalcularRequest):
    # Captura o IP real na nuvem
    forwarded = request.headers.get("X-Forwarded-For")
    ip = forwarded.split(",")[0].strip() if forwarded else request.client.host

    resultado = calcular_cashback(body.tipo_cliente, body.valor_compra, body.desconto)

    query = consultas.insert().values(
        ip=ip,
        tipo_cliente=body.tipo_cliente.lower(),
        valor_compra=body.valor_compra,
        desconto=body.desconto,
        valor_final=resultado["valor_final"],
        cashback=resultado["cashback"],
        percentual=resultado["percentual"],
        criado_em=datetime.utcnow(),
    )
    await database.execute(query)
    return {**resultado, "tipo_cliente": body.tipo_cliente, "valor_compra": body.valor_compra, "desconto": body.desconto}

@app.get("/historico")
async def historico(request: Request):
    forwarded = request.headers.get("X-Forwarded-For")
    ip = forwarded.split(",")[0].strip() if forwarded else request.client.host

    query = consultas.select().where(consultas.c.ip == ip).order_by(consultas.c.criado_em.desc()).limit(50)
    rows = await database.fetch_all(query)

    return [dict(r) for r in rows]

@app.get("/health")
async def health():
    return {"status": "ok"}