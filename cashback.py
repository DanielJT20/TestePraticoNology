from decimal import Decimal, ROUND_HALF_UP


def calcular_cashback(tipo_cliente: str, valor_compra: float, desconto: float = 0.0) -> dict:
    """
    Calcula o cashback conforme as regras de negócio:
    - Cashback base: 5% sobre o valor final (após desconto)
    - Clientes VIP recebem 10% de bônus adicional sobre o cashback base (+0,5pp)
    - Compras com valor ORIGINAL acima de R$500 têm o cashback dobrado
    - O desconto é opcional (padrão 0%)
    """
    tipo = tipo_cliente.lower().strip()
    valor = Decimal(str(valor_compra))
    desc  = Decimal(str(desconto))

    # 1. Aplicar desconto → valor final
    valor_final = (valor * (1 - desc / 100)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    # 2. Cashback base: 5%
    percentual_base = Decimal("5.0")

    # 3. Bônus VIP: 10% sobre o base = +0,5pp
    bonus_vip = Decimal("0.5") if tipo == "vip" else Decimal("0")

    # 4. Dobro se valor ORIGINAL da compra acima de R$500
    multiplicador = Decimal("2") if valor > Decimal("500") else Decimal("1")

    percentual_final = (percentual_base + bonus_vip) * multiplicador
    cashback = (valor_final * percentual_final / Decimal("100")).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )

    return {
        "tipo_cliente":   tipo,
        "valor_compra":   float(valor),
        "desconto_pct":   float(desc),
        "valor_final":    float(valor_final),
        "percentual":     float(percentual_final),
        "cashback":       float(cashback),
    }


if __name__ == "__main__":
    casos = [
        ("VIP",    600, 20),
        ("Normal", 600, 10),
        ("VIP",    600, 15),
        ("Normal", 400,  0),
        ("VIP",    400,  0),
    ]

    print(f"{'Tipo':<8} {'Compra':>8} {'Desc':>6} {'Final':>8} {'%CB':>6} {'Cashback':>10}")
    print("-" * 54)
    for tipo, valor, desc in casos:
        r = calcular_cashback(tipo, valor, desc)
        print(
            f"{r['tipo_cliente'].upper():<8} "
            f"R${r['valor_compra']:>7.2f} "
            f"{r['desconto_pct']:>5.0f}% "
            f"R${r['valor_final']:>6.2f} "
            f"{r['percentual']:>5.1f}% "
            f"R${r['cashback']:>8.2f}"
        )
