# Anime Store API

API REST em FastAPI para um ecommerce de produtos de anime, com estoque reservado, cupons, pedidos, pagamento e envio. O foco do dominio e impedir estados invalidos: vender item sem estoque, pagar pedido errado, reutilizar cupom esgotado ou alterar pedidos em estados terminais.

## Como Rodar

```bash
cp .env.example .env
docker compose up --build
```

Documentacao interativa: `http://localhost:8000/docs`

Testes dentro do container:

```bash
docker compose run api pytest
```

## Entidades

- `Category`: agrupa produtos por tipo, como figures, roupas e mangas.
- `Product`: item vendavel, associado a uma categoria e a uma franquia.
- `ProductVariant`: SKU vendavel de um produto, com preco, estoque fisico e estoque reservado.
- `StockMovement`: historico de ajustes de estoque.
- `Customer`: cliente comprador.
- `Coupon`: promocao com percentual, vigencia, subtotal minimo e limite de uso.
- `Order`: pedido com status, totais derivados e relacao com cliente/cupom.
- `OrderItem`: itens do pedido, congelando preco e quantidade no momento da compra.
- `Payment`: pagamento unico de um pedido.
- `Shipment`: envio unico de um pedido.
- `AuditLog`: historico de transicoes e eventos relevantes.

## Diagrama ER

```text
Category 1---N Product 1---N ProductVariant 1---N StockMovement
                                      |
                                      N
                                      |
Customer 1---N Order 1---N OrderItem
                 |
                 N---1 Coupon
                 |
                 1---0..1 Payment
                 |
                 1---0..1 Shipment
Order 1---N AuditLog
```

## Estados

Pedido:

```text
draft -> confirmed -> paid -> shipped -> delivered
  |          |          |
  v          v          v
canceled   canceled   canceled
```

Estados terminais: `delivered` e `canceled`. Nao faz sentido retornar desses estados porque entrega concluida ou cancelamento ja comunicam uma decisao final ao cliente e ao estoque.

Pagamento:

```text
pending -> approved
pending -> failed
approved -> refunded
```

Envio:

```text
pending -> posted -> delivered
```

## Regras de Negocio

### RN-001

Nome: Pedido confirmado reserva estoque.
Gatilho: `POST /orders/{id}/transition` com `status=confirmed`.
Pre-condicao: pedido em `draft` e itens ativos.
Acao: soma as quantidades em `reserved_quantity`.
Violacao: HTTP 409

```json
{
  "error": "INSUFFICIENT_STOCK",
  "message": "Estoque disponivel insuficiente para confirmar o pedido.",
  "details": { "variant_id": 1, "available": 0, "requested": 1 }
}
```

### RN-002

Nome: Cupom precisa estar aplicavel ao pedido.
Gatilho: criacao de pedido com `coupon_code`.
Pre-condicao: cupom ativo, vigente, abaixo do limite de uso e subtotal suficiente.
Acao: aplica desconto percentual no subtotal.
Violacao: HTTP 422 com `COUPON_INVALID`, `COUPON_EXPIRED`, `COUPON_USAGE_LIMIT` ou `COUPON_MIN_SUBTOTAL`.

### RN-003

Nome: Transicoes de pedido seguem a maquina de estados.
Gatilho: qualquer transicao de pedido.
Pre-condicao: status atual permite o status solicitado.
Acao: atualiza o status e registra auditoria.
Violacao: HTTP 409

```json
{
  "error": "INVALID_ORDER_TRANSITION",
  "message": "Transicao de estado nao permitida para o pedido.",
  "details": { "current_status": "draft", "requested_status": "delivered" }
}
```

### RN-004

Nome: Pagamento so e aceito para pedido confirmado e com valor exato.
Gatilho: `POST /orders/{id}/payment`.
Pre-condicao: pedido em `confirmed`.
Acao: cria pagamento aprovado e muda pedido para `paid`.
Violacao: HTTP 409 `ORDER_NOT_PAYABLE` ou HTTP 422 `PAYMENT_AMOUNT_MISMATCH`.

### RN-005

Nome: Envio so pode ser criado para pedido pago.
Gatilho: `POST /orders/{id}/shipment`.
Pre-condicao: pedido em `paid`.
Acao: cria envio, muda pedido para `shipped`, baixa estoque fisico e libera reserva.
Violacao: HTTP 409 `ORDER_NOT_SHIPPABLE`.

### RN-006

Nome: Estoque fisico nao pode ficar abaixo do reservado.
Gatilho: ajuste manual de estoque.
Pre-condicao: novo estoque fisico deve ser maior ou igual ao reservado.
Acao: ajusta `stock_quantity` e registra `StockMovement`.
Violacao: HTTP 409 `STOCK_BELOW_RESERVED`.

## Calculos Derivados

- `subtotal`: soma de `quantity * unit_price`.
- `discount_total`: percentual do cupom aplicado sobre o subtotal.
- `shipping_total`: frete gratis a partir de R$ 250,00 apos desconto; senao R$ 18,90.
- `grand_total`: `subtotal - discount_total + shipping_total`.

## Decisoes de Design

- Regras de negocio ficam em `app/services`, e routers apenas recebem HTTP e delegam.
- Validators do Pydantic tratam formato local e invariantes de entrada, como SKU maiusculo e janela de vigencia do cupom. Regras que dependem de banco, estoque ou estado ficam nos services.
- `reserved_quantity` foi adicionado na migration 2 porque a primeira modelagem so tinha estoque fisico. A regra de confirmar pedido mostrou a necessidade de distinguir estoque existente de estoque comprometido.
- `AuditLog` entrou na migration 3 para explicar transicoes durante a apresentacao e preservar historico.
- Em concorrencia real, a confirmacao de pedido deveria travar as linhas de `product_variants` com `SELECT FOR UPDATE` no Postgres. Nesta entrega a regra esta centralizada no service e pronta para receber esse lock.

## Cenarios de Borda

- Se dois pedidos disputam a ultima unidade, o segundo recebe `INSUFFICIENT_STOCK` ao confirmar.
- Se um pedido e cancelado em `confirmed` ou `paid`, a reserva de estoque e liberada.
- Se um ajuste de inventario reduzir estoque abaixo da quantidade reservada, a API recusa o ajuste.
- Se o pagamento divergir em centavos do total do pedido, a API recusa para evitar baixa financeira inconsistente.
- Se o pedido ja esta em estado terminal, nenhuma nova transicao e aceita.

## Migrations

- `0001_initial`: tabelas principais do ecommerce.
- `0002_reserved_stock`: adiciona estoque reservado e indices para consultas por franquia/status.
- `0003_audit`: adiciona historico de estoque e auditoria de eventos.
