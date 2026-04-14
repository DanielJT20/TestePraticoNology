# Cashback App

# LINK APP: https://danieljt20.github.io/TestePraticoNology/

## Estrutura
```
cashback/
├── backend/
│   ├── .venv             ← Ambiente virtual Python
│   ├── main.py           ← API FastAPI (cálculo + histórico por IP)
│   └── requirements.txt
├── index.html            ← Frontend estático (HTML/CSS/JS puro)
├── cashback.py           ← Script Python standalone (questão 1)
├── respostas.docx        ← Documento Word com respostas das questões 2 a 4
└── README.md
```

---

## Regras de negócio

| Tipo   | Compra original ≤ R$500 | Compra original > R$500 |
|--------|-------------------------|-------------------------|
| Normal | 5%                      | 10% (dobro)             |
| VIP    | 5,5%                    | 11% (dobro)             |

- O cashback é calculado sobre o **valor final** da compra (após o desconto)
- O bônus VIP é de 10% sobre o cashback base (5% × 10% = +0,5pp)
- O dobro é aplicado quando o **valor original** da compra for acima de R$500 — independente do valor final após desconto
- O desconto é opcional (padrão 0%)

---

## 1. Pré-requisitos

- Python 3.10+
- MySQL 8.0+

---

## 2. Banco de dados

Conecte ao MySQL e crie o banco:

```sql
CREATE DATABASE IF NOT EXISTS cashback;
```

A tabela `consultas` é criada automaticamente pelo backend na primeira inicialização.

---

## 3. Backend

Entre na pasta do backend, crie o ambiente virtual e instale as dependências:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install fastapi uvicorn[standard] databases aiomysql sqlalchemy pydantic cryptography
```

> Se o comando `Activate.ps1` der erro de permissão, rode antes:
> ```powershell
> Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
> ```

### Definir variável de ambiente e iniciar o servidor

**PowerShell (Windows):**
```powershell
$env:DATABASE_URL = "mysql+aiomysql://root:SUA_SENHA@localhost:3306/cashback"
python -m uvicorn main:app --reload
```

**Linux / macOS:**
```bash
export DATABASE_URL="mysql+aiomysql://root:SUA_SENHA@localhost:3306/cashback"
python -m uvicorn main:app --reload
```

> Use sempre `python -m uvicorn` — o comando `uvicorn` direto pode não ser reconhecido dependendo do ambiente.

API disponível em: http://127.0.0.1:8000
Documentação automática: http://127.0.0.1:8000/docs

### Endpoints

| Método | Rota        | Descrição                                       |
|--------|-------------|-------------------------------------------------|
| POST   | /calcular   | Calcula cashback e salva no banco               |
| GET    | /historico  | Retorna histórico do IP do solicitante (até 50) |
| GET    | /health     | Health check                                    |

**Exemplo de payload para POST /calcular:**
```json
{
  "tipo_cliente": "vip",
  "valor_compra": 600,
  "desconto": 20
}
```

---

## 4. Frontend

Abra `index.html` diretamente no navegador, ou sirva com um servidor estático:

```powershell
python -m http.server 3000
```

Acesse: http://localhost:3000

> O backend precisa estar rodando em http://127.0.0.1:8000 para o frontend funcionar.

---

## 5. Script standalone (questão 1)

```bash
python cashback.py
```

Ou importe a função em qualquer projeto:

```python
from cashback import calcular_cashback

resultado = calcular_cashback(tipo_cliente="vip", valor_compra=600, desconto=20)
print(resultado)
# {'tipo_cliente': 'vip', 'valor_compra': 600.0, 'desconto_pct': 20.0,
#  'valor_final': 480.0, 'percentual': 11.0, 'cashback': 52.8}
```

---

## 6. Exemplos de cálculo

| Tipo   | Compra  | Desconto | Valor final | % Cashback | Cashback |
|--------|---------|----------|-------------|------------|----------|
| VIP    | R$600   | 20%      | R$480,00    | 11%        | R$52,80  |
| Normal | R$600   | 10%      | R$540,00    | 10%        | R$54,00  |
| VIP    | R$600   | 15%      | R$510,00    | 11%        | R$56,10  |
| Normal | R$400   | 0%       | R$400,00    | 5%         | R$20,00  |
| VIP    | R$400   | 0%       | R$400,00    | 5,5%       | R$22,00  |

---

## 7. Solução de problemas

| Erro | Causa | Solução |
|------|-------|---------|
| `export` não reconhecido | PowerShell não usa `export` | Use `$env:VARIAVEL = "valor"` |
| `uvicorn` não reconhecido | Não está no PATH | Use `python -m uvicorn main:app --reload` |
| `mysql` não reconhecido | MySQL não está no PATH | Adicione `C:\Program Files\MySQL\MySQL Server 8.0\bin` ao PATH |
| `MissingGreenlet` | `create_all` síncrono com driver async | Tabela criada via `await database.execute()` no startup |
| `Access denied` | Senha errada na DATABASE_URL | Verifique a senha e redefina `$env:DATABASE_URL` |
| `cryptography` package required | MySQL 8 usa caching_sha2_password | `pip install cryptography` |
| `No module named databases` | Pacotes instalados fora do venv | Ative o `.venv` antes de instalar |
| Tabela já existe (Warning) | Tabela criada anteriormente | Aviso inofensivo, pode ignorar |
| `404 Not Found` ao abrir a API | Rota `/` não existe | Acesse `/docs` ou use o frontend |
