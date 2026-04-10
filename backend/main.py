from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from decimal import Decimal, ROUND_HALF_UP
import databases
import sqlalchemy
import os
from datetime import datetime

DATABASE_URL = os.getenv("DATABASE_URL", "mysql+aiomysql://root:@localhost:3306/cashback")

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

app = FastAPI(title="Cashback API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class CalcularRequest(BaseModel):
    tipo_cliente: str
    valor_compra: float
    desconto: float = 0.0  # percentual de desconto, opcional (padrão 0%)


def calcular_cashback(tipo_cliente: str, valor_compra: float, desconto: float = 0.0) -> dict:
    tipo = tipo_cliente.lower().strip()
    valor = Decimal(str(valor_compra))
    desc = Decimal(str(desconto))

    # 1. Aplicar desconto para obter valor final
    valor_final = (valor * (1 - desc / 100)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    # 2. Cashback base: 5%
    percentual_base = Decimal("5.0")

    # 3. Bônus VIP: +0,5pp (10% sobre o base)
    bonus_vip = Decimal("0.5") if tipo == "vip" else Decimal("0")

    # 4. Dobro se valor ORIGINAL da compra acima de R$500 (antes do desconto)
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
    await database.execute("""
        CREATE TABLE IF NOT EXISTS consultas (
            id           INT AUTO_INCREMENT PRIMARY KEY,
            ip           VARCHAR(45)   NOT NULL,
            tipo_cliente VARCHAR(10)   NOT NULL,
            valor_compra DECIMAL(10,2) NOT NULL,
            desconto     DECIMAL(5,2)  NOT NULL DEFAULT 0,
            valor_final  DECIMAL(10,2) NOT NULL,
            cashback     DECIMAL(10,2) NOT NULL,
            percentual   DECIMAL(5,2)  NOT NULL,
            criado_em    DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)


@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()


@app.post("/calcular")
async def calcular(request: Request, body: CalcularRequest):
    ip = request.headers.get("X-Forwarded-For", request.client.host).split(",")[0].strip()

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

    return {
        "tipo_cliente": body.tipo_cliente.lower(),
        "valor_compra": body.valor_compra,
        "desconto": body.desconto,
        "valor_final": resultado["valor_final"],
        "percentual": resultado["percentual"],
        "cashback": resultado["cashback"],
    }


@app.get("/historico")
async def historico(request: Request):
    ip = request.headers.get("X-Forwarded-For", request.client.host).split(",")[0].strip()

    query = (
        consultas.select()
        .where(consultas.c.ip == ip)
        .order_by(consultas.c.criado_em.desc())
        .limit(50)
    )
    rows = await database.fetch_all(query)

    return [
        {
            "tipo_cliente": r["tipo_cliente"],
            "valor_compra": float(r["valor_compra"]),
            "desconto": float(r["desconto"]),
            "valor_final": float(r["valor_final"]),
            "cashback": float(r["cashback"]),
            "percentual": float(r["percentual"]),
            "criado_em": r["criado_em"].isoformat(),
        }
        for r in rows
    ]


@app.get("/health")
async def health():
    return {"status": "ok"}