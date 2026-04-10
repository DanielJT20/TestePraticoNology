import os
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

import databases
import sqlalchemy
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# 1. Configuração do Banco de Dados
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./test.db")
# Render usa postgres://, mas o driver precisa de postgresql://
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

# 2. Inicialização do App (Ordem correta)
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Libera geral para o teste funcionar
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class CalcularRequest(BaseModel):
    tipo_cliente: str
    valor_compra: float
    desconto: float = 0.0

@app.on_event("startup")
async def startup():
    await database.connect()
    # Cria a tabela se ela não existir
    engine = sqlalchemy.create_engine(DATABASE_URL.replace("+asyncpg", ""))
    metadata.create_all(engine)

@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()

@app.post("/calcular")
async def calcular(request: Request, body: CalcularRequest):
    # Pega o IP real (importante para o Render)
    forwarded = request.headers.get("X-Forwarded-For")
    ip = forwarded.split(",")[0].strip() if forwarded else request.client.host

    # Lógica de Cálculo
    valor = Decimal(str(body.valor_compra))
    desc = Decimal(str(body.desconto))
    valor_final = (valor * (1 - desc / 100)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    
    perc_base = Decimal("5.5") if body.tipo_cliente.lower() == "vip" else Decimal("5.0")
    mult = Decimal("2") if valor > 500 else Decimal("1")
    perc_final = perc_base * mult
    
    cashback = (valor_final * perc_final / 100).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    # Salva no Banco
    query = consultas.insert().values(
        ip=ip,
        tipo_cliente=body.tipo_cliente.lower(),
        valor_compra=body.valor_compra,
        desconto=body.desconto,
        valor_final=float(valor_final),
        cashback=float(cashback),
        percentual=float(perc_final),
        criado_em=datetime.utcnow(),
    )
    await database.execute(query)

    return {
        "valor_final": float(valor_final),
        "cashback": float(cashback),
        "percentual": float(perc_final)
    }

@app.get("/historico")
async def historico(request: Request):
    forwarded = request.headers.get("X-Forwarded-For")
    ip = forwarded.split(",")[0].strip() if forwarded else request.client.host

    query = consultas.select().where(consultas.c.ip == ip).order_by(consultas.c.id.desc())
    rows = await database.fetch_all(query)
    return rows