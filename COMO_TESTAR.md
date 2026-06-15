# Guia de testes - Anime Store API

Este guia mostra como rodar os testes automatizados, como testar a API manualmente e como explicar a cobertura da Anime Store.

## 1. Rodar todos os testes com Docker

Primeiro abra o Docker Desktop e espere ele ficar com status de running. Depois abra um terminal na pasta do projeto:

```bash
cd "<PASTA_DO_PROJETO>"
```

Rode:

```bash
docker compose run --rm api pytest -q
```

Resultado esperado:

```text
11 passed
```

Se aparecer erro parecido com `dockerDesktopLinuxEngine`, o Docker Desktop esta fechado ou ainda nao terminou de iniciar.

## 2. Rodar a API

Com Docker Desktop aberto:

```bash
docker compose up --build
```

Depois acesse:

- Swagger: http://localhost:8000/docs
- Health check: http://localhost:8000/health
- Loja integrada: http://localhost:8000/
- Adminer: http://localhost:8080

Para parar:

```bash
docker compose down
```

## 3. Rodar testes sem Docker

Use isso se o Docker Desktop nao abrir.

```bash
cd "<PASTA_DO_PROJETO>"
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pytest -q
```

Resultado esperado:

```text
11 passed
```

## 4. Rodar um teste especifico

Exemplo para testar apenas o calculo de totais do pedido:

```bash
docker compose run --rm api pytest tests/test_orders.py::test_create_order_calculates_totals -q
```

Exemplo para testar apenas reserva de estoque:

```bash
docker compose run --rm api pytest tests/test_orders.py::test_confirm_order_reserves_stock -q
```

Exemplo para testar apenas bloqueio de estoque insuficiente:

```bash
docker compose run --rm api pytest tests/test_orders.py::test_confirm_order_rejects_insufficient_stock -q
```

Exemplo para testar apenas pagamento com valor divergente:

```bash
docker compose run --rm api pytest tests/test_orders.py::test_payment_amount_must_match_total -q
```

## 5. O que cada teste prova

- `test_create_order_calculates_totals`: garante calculo de subtotal, frete, total final e status inicial `draft`.
- `test_product_list_supports_pagination_and_filter`: garante listagem de produtos com paginacao e filtros por franquia/status.
- `test_confirm_order_reserves_stock`: prova transicao `draft -> confirmed` e reserva de estoque.
- `test_confirm_order_rejects_insufficient_stock`: prova bloqueio quando dois pedidos disputam estoque limitado.
- `test_invalid_state_transition_is_rejected`: prova que a maquina de estados impede `draft -> delivered`.
- `test_payment_requires_confirmed_order`: prova que pedido em `draft` nao pode ser pago.
- `test_payment_amount_must_match_total`: prova que pagamento precisa bater exatamente com `grand_total`.
- `test_paid_order_can_be_shipped`: prova pagamento aprovado, criacao de envio e transicao para `shipped`.
- `test_coupon_applies_discount_and_free_shipping`: prova aplicacao de cupom e recalculo dos totais.
- `test_coupon_minimum_subtotal_is_enforced`: prova regra de subtotal minimo do cupom.
- `test_stock_adjust_cannot_go_below_reserved`: prova que estoque fisico nao pode ficar abaixo do reservado.

## 6. Como testar manualmente pelo Swagger

Acesse http://localhost:8000/docs e siga esta ordem:

1. `POST /catalog/categories`

```json
{
  "name": "Figures",
  "description": "Colecionaveis oficiais de anime"
}
```

2. `POST /catalog/products`

```json
{
  "category_id": 1,
  "name": "Naruto Uzumaki Figure",
  "description": "Colecionavel oficial de mesa",
  "franchise": "Naruto"
}
```

3. `POST /catalog/variants`

```json
{
  "product_id": 1,
  "sku": "nar-fig-01",
  "name": "Standard",
  "price": "120.00",
  "stock_quantity": 2
}
```

4. `POST /customers`

```json
{
  "name": "Bruno",
  "email": "bruno@example.com",
  "city": "Sao Paulo",
  "state": "sp"
}
```

5. `POST /coupons`

```json
{
  "code": "AKATSUKI10",
  "percent_off": 10,
  "min_subtotal": "100.00",
  "usage_limit": 1
}
```

6. `POST /orders`

```json
{
  "customer_id": 1,
  "coupon_code": "AKATSUKI10",
  "items": [
    {
      "variant_id": 1,
      "quantity": 1
    }
  ]
}
```

7. `POST /orders/1/transition`

```json
{
  "status": "confirmed"
}
```

8. `POST /orders/1/payment`

Use o valor retornado em `grand_total` no pedido.

```json
{
  "amount": "126.90",
  "provider_reference": "PIX-ANIME-001"
}
```

9. `POST /orders/1/shipment`

```json
{
  "carrier": "Correios",
  "tracking_code": "BR123456789BR"
}
```

10. `GET /orders`

Use para conferir o pedido criado e seu status final.

## 7. Testes manuais de erro

### Estoque insuficiente

Crie dois pedidos para a mesma variante, usando quantidade total maior que o estoque. Confirme o primeiro e tente confirmar o segundo.

Resultado esperado: HTTP 409 com `INSUFFICIENT_STOCK`.

### Transicao invalida

Crie um pedido e tente ir direto para `delivered`:

```json
{
  "status": "delivered"
}
```

Resultado esperado: HTTP 409 com `INVALID_ORDER_TRANSITION`.

### Pagamento antes da confirmacao

Crie um pedido e tente pagar antes de confirmar.

Resultado esperado: HTTP 409 com `ORDER_NOT_PAYABLE`.

### Valor de pagamento diferente do total

Confirme um pedido e envie:

```json
{
  "amount": "1.00"
}
```

Resultado esperado: HTTP 422 com `PAYMENT_AMOUNT_MISMATCH`.

### Cupom abaixo do subtotal minimo

Crie um cupom com `min_subtotal` maior que o subtotal do pedido e tente usa-lo.

Resultado esperado: HTTP 422 com `COUPON_MIN_SUBTOTAL`.

### Estoque abaixo do reservado

Confirme um pedido para reservar estoque e depois tente reduzir o estoque fisico da variante:

```json
{
  "quantity_delta": -1,
  "reason": "inventory_count"
}
```

Resultado esperado: HTTP 409 com `STOCK_BELOW_RESERVED`.

## 8. Testar migrations

Com Docker:

```bash
docker compose run --rm api alembic upgrade head
docker compose run --rm api alembic downgrade -1
docker compose run --rm api alembic upgrade head
```

O que explicar:

- `upgrade head`: aplica as 3 migrations.
- `downgrade -1`: volta uma migration e prova rollback incremental.
- `upgrade head`: reaplica e prova que a migration nao ficou quebrada.

## 9. Como explicar a parte que "IA nao resolve"

- O pedido confirmado reserva estoque, mas nao baixa estoque fisico; a baixa acontece no envio.
- O bloqueio de estoque usa `stock_quantity - reserved_quantity`, nao apenas a quantidade fisica.
- Estados terminais (`delivered`, `canceled`) nao voltam porque representam historico fechado.
- Validator Pydantic ficou para regras locais do payload; regras que consultam banco ficaram nos services.
- A migration 2 nasceu da regra de reserva de estoque e dos indices para consulta.
- A migration 3 nasceu da necessidade de explicar historico com movimentos de estoque e auditoria.
- A pagina HTML foi servida pelo FastAPI para mostrar que a vitrine faz parte da entrega.

## 10. Registro de execucao

- Primeiro testei o fluxo basico de pedido com produto Naruto, cliente e variante com estoque 2.
- Depois forcei dois pedidos disputando o mesmo estoque e confirmei que o segundo recebe `INSUFFICIENT_STOCK`.
- Em seguida validei pagamento: pedido em `draft` nao paga e pedido confirmado so aceita valor exato.
- Depois testei cupom com subtotal minimo para garantir erro padronizado.
- Por fim testei ajuste de estoque abaixo do reservado para provar que a reserva protege a venda ja confirmada.
