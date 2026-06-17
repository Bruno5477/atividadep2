# BO Mangas API

API REST em FastAPI para a BO Mangas, uma biblioteca/loja online de mangas. O dominio simula um ecommerce com categorias, produtos, variantes vendaveis por volume ou edicao, estoque fisico, estoque reservado, clientes, cupons, pedidos, pagamentos, envios, auditoria e calculos derivados de totais.

O dominio foi escolhido para fugir de CRUD puro: um pedido depende de estoque disponivel, uso valido de cupom, transicoes permitidas, pagamento com valor exato e baixa de estoque apenas no momento correto.

## Como rodar

```bash
docker compose up --build
```

API: http://localhost:8000
Swagger: http://localhost:8000/docs
Biblioteca HTML integrada: http://localhost:8000/
Adminer: http://localhost:8080

Testes dentro do container:

```bash
docker compose run --rm api pytest -q
```

Guia detalhado para rodar e explicar os testes: `COMO_TESTAR.md`.

## Como testar na apresentacao

### Adminer

Abra http://localhost:8080 e use:

```text
Sistema: PostgreSQL
Servidor: db
Usuario: bo_mangas
Senha: bo_mangas
Banco de dados: bo_mangas
```

Se a pagina nao abrir, provavelmente o servico `adminer` nao esta rodando. Suba ele com:

```bash
docker compose up -d adminer
```

Para conferir se esta ativo:

```bash
docker compose ps
```

No Adminer, as tabelas mais importantes para mostrar sao:

- `categories`
- `products`
- `product_variants`
- `stock_movements`
- `customers`
- `coupons`
- `orders`
- `order_items`
- `payments`
- `shipments`
- `audit_logs`

### Health check

Abra http://localhost:8000/health. Resposta esperada:

```json
{ "status": "ok" }
```

### Swagger

Abra http://localhost:8000/docs. Ordem recomendada para demonstrar o fluxo:

1. `POST /catalog/categories`
2. `POST /catalog/products`
3. `POST /catalog/variants`
4. `POST /customers`
5. `POST /coupons`
6. `POST /orders`
7. `POST /orders/{id}/transition`
8. `POST /orders/{id}/payment`
9. `POST /orders/{id}/shipment`
10. `GET /orders`

Para demonstrar erro de regra de negocio, tente:

- Confirmar dois pedidos disputando a ultima unidade para receber `INSUFFICIENT_STOCK`.
- Pagar um pedido ainda em `draft` para receber `ORDER_NOT_PAYABLE`.
- Pagar com valor diferente do total para receber `PAYMENT_AMOUNT_MISMATCH`.
- Alterar estoque para ficar abaixo da quantidade reservada para receber `STOCK_BELOW_RESERVED`.
- Tentar ir direto de `draft` para `delivered` para receber `INVALID_ORDER_TRANSITION`.

### Biblioteca HTML integrada

Abra http://localhost:8000/. A pagina inicial da loja e servida pelo FastAPI a partir da pasta `static`.

A tela usa capas locais em `static/capas` e representa a vitrine da BO Mangas com exemplos de series como One Piece, Jujutsu Kaisen, Naruto, Blue Lock, Bleach e My Hero Academia. Ela serve como material visual da entrega, enquanto os fluxos principais sao demonstrados pelos endpoints reais no Swagger.

## Migracoes

```bash
docker compose run --rm api alembic upgrade head
docker compose run --rm api alembic downgrade -1
docker compose run --rm api alembic upgrade head
```

## Entidades

### Category

Representa um agrupamento de produtos, como shonen, seinen, esporte, fantasia ou colecoes especiais.

- `id`: inteiro, PK.
- `name`: texto obrigatorio.
- `description`: texto opcional.

Relacionamento: `Category 1:N Product`.

### Product

Representa o manga comercial exibido na loja.

- `category_id`: FK para `Category`.
- `name`: nome do produto.
- `description`: descricao usada no catalogo.
- `franchise`: franquia do manga, como Naruto, One Piece ou Jujutsu Kaisen.
- `active`: define se o produto aparece nas consultas.

Relacionamento: `Product 1:N ProductVariant`.

### ProductVariant

Representa o SKU vendavel do produto, como volume unico, box ou edicao especial.

- `product_id`: FK para `Product`.
- `sku`: codigo unico normalizado em maiusculo.
- `name`: nome da variante.
- `price`: preco de venda.
- `stock_quantity`: estoque fisico.
- `reserved_quantity`: estoque ja comprometido por pedidos confirmados.
- `active`: define se a variante pode ser usada.

Relacionamento: `ProductVariant 1:N OrderItem` e `ProductVariant 1:N StockMovement`.

### StockMovement

Registra ajustes de estoque.

- `variant_id`: FK para `ProductVariant`.
- `quantity_delta`: variacao aplicada.
- `reason`: motivo do ajuste.

### Customer

Representa a pessoa compradora.

- `name`: nome obrigatorio.
- `email`: email obrigatorio e unico.
- `city`: cidade.
- `state`: UF normalizada em maiusculo.

Relacionamento: `Customer 1:N Order`.

### Coupon

Representa uma promocao.

- `code`: codigo unico normalizado em maiusculo.
- `percent_off`: percentual de desconto.
- `min_subtotal`: subtotal minimo.
- `usage_limit`: limite opcional de uso.
- `used_count`: quantidade ja usada.
- `valid_from` e `valid_until`: janela opcional de validade.
- `active`: define se pode ser aplicado.

Relacionamento: `Coupon 1:N Order`.

### Order

Representa o pedido de compra.

- `customer_id`: FK para `Customer`.
- `coupon_id`: FK opcional para `Coupon`.
- `status`: `draft`, `confirmed`, `paid`, `shipped`, `delivered` ou `canceled`.
- `subtotal`: soma dos itens.
- `discount_total`: desconto aplicado.
- `shipping_total`: frete calculado.
- `grand_total`: total final.

Relacionamentos: `Order 1:N OrderItem`, `Order 1:0..1 Payment`, `Order 1:0..1 Shipment` e `Order 1:N AuditLog`.

### OrderItem

Representa um item congelado no momento da compra.

- `order_id`: FK para `Order`.
- `variant_id`: FK para `ProductVariant`.
- `quantity`: quantidade comprada.
- `unit_price`: preco unitario no momento do pedido.
- `line_total`: total da linha.

### Payment

Representa o pagamento do pedido.

- `order_id`: FK para `Order`.
- `amount`: valor pago.
- `status`: `pending`, `approved`, `failed` ou `refunded`.
- `provider_reference`: referencia opcional do provedor.

### Shipment

Representa o envio do pedido.

- `order_id`: FK para `Order`.
- `carrier`: transportadora.
- `tracking_code`: codigo opcional de rastreio.
- `status`: `pending`, `posted` ou `delivered`.

### AuditLog

Registra eventos importantes, principalmente transicoes de pedido.

- `entity_type`: tipo da entidade.
- `entity_id`: id da entidade.
- `event`: nome do evento.
- `payload`: detalhes em JSON.

## Diagrama ER

```text
Category 1 ---- N Product 1 ---- N ProductVariant 1 ---- N StockMovement
                                           |
                                           N
                                           |
Customer 1 ---- N Order 1 ---- N OrderItem
                  |
                  N ---- 1 Coupon
                  |
                  1 ---- 0..1 Payment
                  |
                  1 ---- 0..1 Shipment

Order 1 ---- N AuditLog
```

## Maquina de estados do pedido

```text
draft
  |-- confirmed
  |     |-- paid
  |     |     |-- shipped
  |     |     |     `-- delivered   (terminal)
  |     |     `-- canceled          (terminal)
  |     `-- canceled                (terminal)
  `-- canceled                      (terminal)
```

Estados terminais: `delivered` e `canceled`. Depois deles nao faz sentido voltar, porque uma entrega concluida fecha o ciclo logistico e um cancelamento encerra a intencao de compra.

## Regras de negocio

### RN-001 - Pedido confirmado reserva estoque

- Gatilho: `POST /orders/{id}/transition` com `status=confirmed`.
- Pre-condicao: pedido em `draft` e variantes ativas.
- Acao: soma as quantidades em `reserved_quantity`.
- Violacao: HTTP 409 com `INSUFFICIENT_STOCK`.

```json
{
  "error": "INSUFFICIENT_STOCK",
  "message": "Estoque disponivel insuficiente para confirmar o pedido.",
  "details": {
    "variant_id": 1,
    "available": 0,
    "requested": 1
  }
}
```

### RN-002 - Cupom precisa estar aplicavel ao pedido

- Gatilho: `POST /orders` com `coupon_code`.
- Pre-condicao: cupom ativo, vigente, abaixo do limite de uso e subtotal suficiente.
- Acao: aplica desconto percentual no subtotal.
- Violacao: HTTP 422 com `COUPON_INVALID`, `COUPON_EXPIRED`, `COUPON_USAGE_LIMIT` ou `COUPON_MIN_SUBTOTAL`.

### RN-003 - Transicoes de pedido seguem a maquina de estados

- Gatilho: qualquer transicao de pedido.
- Pre-condicao: status atual permite o status solicitado.
- Acao: atualiza o status e registra auditoria.
- Violacao: HTTP 409 com `INVALID_ORDER_TRANSITION`.

```json
{
  "error": "INVALID_ORDER_TRANSITION",
  "message": "Transicao de estado nao permitida para o pedido.",
  "details": {
    "current_status": "draft",
    "requested_status": "delivered"
  }
}
```

### RN-004 - Pagamento so e aceito para pedido confirmado e com valor exato

- Gatilho: `POST /orders/{id}/payment`.
- Pre-condicao: pedido em `confirmed`.
- Acao: cria pagamento aprovado e muda pedido para `paid`.
- Violacao: HTTP 409 `ORDER_NOT_PAYABLE` ou HTTP 422 `PAYMENT_AMOUNT_MISMATCH`.

### RN-005 - Envio so pode ser criado para pedido pago

- Gatilho: `POST /orders/{id}/shipment`.
- Pre-condicao: pedido em `paid`.
- Acao: cria envio, muda pedido para `shipped`, baixa estoque fisico e libera reserva.
- Violacao: HTTP 409 com `ORDER_NOT_SHIPPABLE`.

### RN-006 - Estoque fisico nao pode ficar abaixo do reservado

- Gatilho: `POST /catalog/variants/{variant_id}/stock`.
- Pre-condicao: novo estoque fisico deve ser maior ou igual ao reservado.
- Acao: ajusta `stock_quantity` e registra `StockMovement`.
- Violacao: HTTP 409 com `STOCK_BELOW_RESERVED`.

## Calculos derivados

```text
subtotal = soma de quantity * unit_price
discount_total = percentual do cupom aplicado sobre o subtotal
shipping_total = 0.00 se subtotal com desconto >= 250.00, senao 18.90
grand_total = subtotal - discount_total + shipping_total
```

## Cenarios de borda tratados

1. Recurso limitado chegando a zero: se dois pedidos disputam a ultima unidade, o segundo recebe `INSUFFICIENT_STOCK` ao confirmar.
2. Estado terminal: pedido `delivered` ou `canceled` nao aceita novas transicoes.
3. Calculo derivado invalido: pagamento com valor diferente de `grand_total` e recusado.
4. Estoque reservado: ajuste manual nao pode reduzir estoque fisico abaixo do reservado.
5. Cupom invalido: cupom fora das regras de subtotal, validade ou limite de uso e rejeitado.
6. Cancelamento com reserva: pedido cancelado em `confirmed` ou `paid` libera estoque reservado.

## Perguntas da secao 5.1

1. Relacionamentos: `Order` nao guarda itens em JSON. Usei `OrderItem`, porque o pedido precisa congelar preco, quantidade e variante no momento da compra.
2. Pydantic versus service: validators cuidam de formato local, como SKU em maiusculo, UF em maiusculo e janela de validade do cupom. Services cuidam de regras que dependem do banco, como estoque, status do pedido e uso de cupom.
3. Migration 2: ela nasceu quando percebi que confirmar pedido nao deveria baixar estoque fisico imediatamente. Por isso entrou `reserved_quantity` e indices para consultas frequentes.
4. Concorrencia: o comportamento correto em duas confirmacoes simultaneas seria travar as linhas de `product_variants` no PostgreSQL com `SELECT ... FOR UPDATE`. Nesta entrega a regra esta centralizada no service e pronta para receber esse lock.
5. Estados terminais: `delivered` e `canceled`. Voltar deles criaria historico falso, porque entrega e cancelamento representam decisoes finais.

## Storytelling das migrations

1. `0001_initial_store_structure`: cria a estrutura principal da loja com clientes, catalogo, cupons, pedidos, pagamentos e envios.
2. `0002_reserved_stock_and_query_indexes`: adiciona estoque reservado e indices para consultas por franquia/status, porque a confirmacao do pedido mostrou que estoque fisico e estoque comprometido sao conceitos diferentes.
3. `0003_stock_movements_and_audit_log`: adiciona historico de movimentos de estoque e auditoria para explicar as transicoes durante a apresentacao.

Downgrade foi escrito nas migrations para permitir rollback incremental.

## Concorrencia

O comportamento correto quando dois operadores tentam confirmar pedidos sobre a mesma ultima unidade ao mesmo tempo seria travar a linha da variante em uma transacao no PostgreSQL (`SELECT ... FOR UPDATE`) ou aplicar controle otimista. Nesta entrega, a regra de disponibilidade esta concentrada no service e valida `stock_quantity - reserved_quantity` antes de reservar.

## Endpoints principais

- `GET /health`
- `POST /catalog/categories`
- `POST /catalog/products`
- `GET /catalog/products?limit=10&offset=0&franchise=One%20Piece&active=true`
- `POST /catalog/variants`
- `POST /catalog/variants/{variant_id}/stock`
- `POST /customers`
- `POST /coupons`
- `POST /orders`
- `GET /orders?status=confirmed&limit=10&offset=0`
- `POST /orders/{id}/transition`
- `POST /orders/{id}/payment`
- `POST /orders/{id}/shipment`
- `GET /`

## Decisoes de design

- `OrderItem` congela preco e quantidade para que alteracoes futuras no catalogo nao mudem pedidos antigos.
- Confirmar pedido reserva estoque, mas nao baixa estoque fisico. A baixa acontece no envio, quando a venda realmente sai do estoque.
- Validacoes locais ficam nos schemas Pydantic. Validacoes que dependem de outras entidades ficam nos services.
- Erros de regra de negocio usam payload padronizado com `error`, `message` e `details`.
- Routers nao contem regra de negocio; eles apenas recebem HTTP e chamam os services.
- A pagina HTML inicial fica integrada ao FastAPI para dar uma vitrine visual ao projeto.

## Registro de evolucao

- Dia 1: modelei catalogo, clientes, cupons e pedidos.
- Dia 2: adicionei variantes para representar SKUs vendaveis, separando produto comercial de item em estoque.
- Dia 3: percebi que confirmar pedido nao deveria baixar estoque fisico; criei `reserved_quantity`.
- Dia 4: adicionei regras de cupom, frete e pagamento com valor exato.
- Dia 5: adicionei envio, baixa de estoque e liberacao de reserva.
- Dia 6: criei auditoria e movimentos de estoque para explicar o historico na apresentacao.
- Dia 7: liguei a vitrine HTML na rota `/` e organizei os testes de regras de negocio.
