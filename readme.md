# ESP32 IoT API

API construída com FastAPI para receber dados de temperatura e umidade
de um ESP32 simulado no Wokwi, armazenar no SQLite e exibir em um
dashboard web. Roda no GitHub Codespaces sem configuração extra.

## Como funciona

O ESP32 lê o sensor DHT22 a cada 10 segundos, calcula estatísticas
locais (média, máxima, mínima dos últimos 5 valores) e envia tudo via
HTTP POST para a API. A API valida, salva no banco e disponibiliza um
dashboard que atualiza automaticamente.

Fluxo resumido:
ESP32 (Wokwi) → POST /sensors → FastAPI → SQLite → GET /dashboard

## Pré-requisitos

- Python 3.10+
- Conta no GitHub com Codespaces habilitado
- Projeto aberto no Wokwi

## Instalação

```bash
pip install -r requirements.txt
python main.py
```

Após iniciar, o terminal vai mostrar a URL pública do Codespaces.
Copie essa URL e cole no campo `serverUrl` do código do ESP32 no Wokwi,
adicionando `/sensors` no final.

Antes de rodar o ESP32, certifique que a porta 8000 está como **Public**
nas configurações de portas do Codespaces.

## Endpoints

| Método | Rota | O que faz |
|--------|------|-----------|
| GET | `/` | Retorna status e lista de endpoints |
| GET | `/health` | Verificação rápida se a API está viva |
| POST | `/sensors` | Recebe dados do ESP32 |
| GET | `/sensors` | Lista últimas leituras em JSON |
| GET | `/dados` | Versão simplificada das leituras |
| GET | `/dashboard` | Dashboard visual com tabela e cards |
| DELETE | `/sensors` | Limpa todos os registros do banco |

## Exemplo de payload (o que o ESP32 envia)

```json
{
  "device_id": "ESP32_WOKWI",
  "temperature": 28.4,
  "humidity": 62.0,
  "media_temperatura": 27.9,
  "media_umidade": 61.2,
  "max_temperatura": 29.1,
  "min_temperatura": 26.8,
  "leitura_num": 15
}
```

## Dependências principais

**FastAPI** — framework web que define as rotas e valida os dados de entrada automaticamente.

**Uvicorn** — servidor ASGI que executa a aplicação FastAPI. É ele que você está rodando quando chama `python main.py`.

**SQLAlchemy** — ORM que mapeia a classe `SensorData` para uma tabela no banco. Você escreve Python, ele gera o SQL.

**Pydantic** — validação de dados. Se o ESP32 mandar um campo com tipo errado ou obrigatório faltando, o Pydantic rejeita automaticamente com erro 422.

**python-dotenv** — carrega variáveis de ambiente de um arquivo `.env`. Útil se você quiser mudar configurações sem alterar o código.

## Observações

- O banco `esp32_iot.db` é criado automaticamente na primeira execução.
- O dashboard não usa JavaScript — atualiza via meta refresh do HTML.
- `setInsecure()` no ESP32 desativa verificação de certificado SSL.
  Serve para desenvolvimento; em produção use um certificado válido.
- A URL do Codespaces muda se você recriar o ambiente. Lembre de
  atualizar o `serverUrl` no Wokwi quando isso acontecer.