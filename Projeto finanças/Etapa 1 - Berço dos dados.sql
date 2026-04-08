CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE SCHEMA IF NOT EXISTS financas;

-- criação da tabela categoria
CREATE TYPE financas.tipo_categoria AS ENUM (
    'essencial',      -- moradia, saúde, alimentação básica
    'variavel',       -- lazer, vestuário, compras em geral
    'investimento',   -- aportes, aquisição de bens
    'assinatura',     -- recorrentes fixos: netflix, spotify, etc
    'educacao'        -- cursos, livros, faculdade
);

CREATE TABLE financas.categoria (
    id        SERIAL       PRIMARY KEY,
    nome      VARCHAR(50)  NOT NULL UNIQUE, 
	tipo      financas.tipo_categoria NOT NULL DEFAULT 'variavel',
    icone     VARCHAR(10)  NOT NULL DEFAULT '💰',
    cor_hex   VARCHAR(7)   NOT NULL DEFAULT '#888888',
    ativo     BOOLEAN      NOT NULL DEFAULT TRUE,
    criado_em TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- tabela salario do mês
CREATE TABLE financas.salario_mes (
    id               SERIAL       PRIMARY KEY,
    mes              SMALLINT     NOT NULL CHECK (mes BETWEEN 1 AND 12),
    ano              SMALLINT     NOT NULL CHECK (ano >= 2000),
    valor_bruto      DECIMAL(10,2) NOT NULL CHECK (valor_bruto >= 0),
    valor_liquido    DECIMAL(10,2) NOT NULL CHECK (valor_liquido >= 0),
    data_recebimento DATE,
    observacao       TEXT,
    criado_em        TIMESTAMPTZ  NOT NULL DEFAULT NOW(),

    CONSTRAINT uk_salario_mes_ano UNIQUE (mes, ano)
);

-- Tabela forma de pagamento
CREATE TYPE financas.forma_pgto AS ENUM (
    'pix', 'credito', 'debito',
    'dinheiro', 'boleto', 'transferencia'
);

CREATE TABLE financas.gasto (
    id             SERIAL                PRIMARY KEY,
    salario_mes_id INT                   NOT NULL
                       REFERENCES financas.salario_mes(id)
                       ON DELETE RESTRICT,
    categoria_id   INT                   NOT NULL
                       REFERENCES financas.categoria(id)
                       ON DELETE RESTRICT,
    data_gasto     DATE                  NOT NULL,
    descricao      VARCHAR(200)          NOT NULL,
    valor          DECIMAL(10,2)         NOT NULL CHECK (valor > 0),
    forma_pagamento financas.forma_pgto  NOT NULL DEFAULT 'pix',
    parcelado      BOOLEAN               NOT NULL DEFAULT FALSE,
    num_parcelas   SMALLINT              CHECK (num_parcelas > 1),
    parcela_atual  SMALLINT              CHECK (parcela_atual >= 1),
    observacao     TEXT,
    criado_em      TIMESTAMPTZ           NOT NULL DEFAULT NOW(),

    CONSTRAINT chk_parcelas
        CHECK (
            (parcelado = FALSE AND num_parcelas IS NULL AND parcela_atual IS NULL)
            OR
            (parcelado = TRUE  AND num_parcelas IS NOT NULL AND parcela_atual IS NOT NULL)
        )
);

-- criação da tabela meta mensal
CREATE TABLE financas.meta_mensal (
    id             SERIAL        PRIMARY KEY,
    salario_mes_id INT           NOT NULL
                       REFERENCES financas.salario_mes(id)
                       ON DELETE CASCADE,
    categoria_id   INT           NOT NULL
                       REFERENCES financas.categoria(id)
                       ON DELETE RESTRICT,
    valor_limite   DECIMAL(10,2) NOT NULL CHECK (valor_limite > 0),
    criado_em      TIMESTAMPTZ   NOT NULL DEFAULT NOW(),

    CONSTRAINT uk_meta UNIQUE (salario_mes_id, categoria_id)
);

CREATE TYPE financas.tipo_receita AS ENUM (
    'divida_recebida',   -- alguém te pagou de volta
    'venda',             -- venda de um bem / produto
    'freelance',         -- serviço avulso
    'bonus',             -- bônus / gratificação
    'outro'              -- qualquer outra entrada extra
);

CREATE TABLE financas.receita_extra (
    id               SERIAL          PRIMARY KEY,
    salario_mes_id   INT             NOT NULL
                         REFERENCES financas.salario_mes(id)
                         ON DELETE RESTRICT,
    descricao        VARCHAR(200)    NOT NULL,
    valor            DECIMAL(10,2)   NOT NULL CHECK (valor > 0),
    tipo             financas.tipo_receita NOT NULL DEFAULT 'outro',
    data_recebimento DATE,
    parcelado        BOOLEAN         NOT NULL DEFAULT FALSE,
    num_parcelas     SMALLINT        CHECK (num_parcelas > 1),
    parcela_atual    SMALLINT        CHECK (parcela_atual >= 1),
    observacao       TEXT,
    criado_em        TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    CONSTRAINT chk_parcelas_receita
        CHECK (
            (parcelado = FALSE AND num_parcelas IS NULL AND parcela_atual IS NULL)
            OR
            (parcelado = TRUE  AND num_parcelas IS NOT NULL AND parcela_atual IS NOT NULL)
        )
);

-- índices para performance
CREATE INDEX idx_gasto_salario_mes  ON financas.gasto(salario_mes_id);
CREATE INDEX idx_gasto_categoria    ON financas.gasto(categoria_id);
CREATE INDEX idx_gasto_data         ON financas.gasto(data_gasto);
CREATE INDEX idx_meta_salario_mes   ON financas.meta_mensal(salario_mes_id);
CREATE INDEX idx_receita_extra_salario_mes ON financas.receita_extra(salario_mes_id);

-- CATEGORIAS DISPONIVEIS EM categoria
INSERT INTO financas.categoria (nome, icone, cor_hex) VALUES
    ('Alimentação',   '🍽️',  '#E67E22'),
    ('Moradia',       '🏠',  '#2ECC71'),
    ('Transporte',    '🚗',  '#3498DB'),
    ('Saúde',         '💊',  '#E74C3C'),
    ('Lazer',         '🎮',  '#9B59B6'),
    ('Educação',      '📚',  '#1ABC9C'),
    ('Investimento',  '📈',  '#F1C40F'),
    ('Assinatura',    '📱',  '#34495E'),
    ('Vestuário',     '👕',  '#E91E63'),
    ('Outros',        '💡',  '#95A5A6')
ON CONFLICT (nome) DO NOTHING;

SELECT * FROM financas.salario_mes;

SELECT * FROM financas.gasto;

select * from financas.categoria;

select * from financas.meta_mensal;

select * from financas.receita_extra;

DELETE from financas.salario_mes
WHERE id = 1 ;
