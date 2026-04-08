from db import get_connection
from datetime import datetime

# -------------------------------
# UTILIDADES
# -------------------------------

def escolher_opcao(lista, titulo):
    print(f"\n{titulo}")
    for i, item in enumerate(lista, start=1):
        print(f"{i} - {item}")
    
    while True:
        try:
            escolha = int(input("Escolha uma opção: "))
            if 1 <= escolha <= len(lista):
                return escolha - 1
        except:
            pass
        print("Opção inválida, tente novamente.")


# -------------------------------
# SALÁRIO
# -------------------------------

def obter_ou_criar_salario(conn):
    cur = conn.cursor()

    mes = int(input("Mês (1-12): "))
    ano = int(input("Ano (ex: 2026): "))

    # Verifica se já existe
    cur.execute("""
        SELECT id FROM financas.salario_mes
        WHERE mes = %s AND ano = %s
    """, (mes, ano))

    result = cur.fetchone()

    if result:
        print("✔ Salário já cadastrado.")
        return result[0]

    print("⚠ Salário não encontrado. Vamos cadastrar.")

    valor_bruto = float(input("Valor bruto: "))
    valor_liquido = float(input("Valor líquido: "))
    data_recebimento = input("Data de recebimento (YYYY-MM-DD ou ENTER): ")
    observacao = input("Observação (opcional): ")

    cur.execute("""
        INSERT INTO financas.salario_mes
        (mes, ano, valor_bruto, valor_liquido, data_recebimento, observacao)
        VALUES (%s,%s,%s,%s,%s,%s)
        RETURNING id
    """, (
        mes,
        ano,
        valor_bruto,
        valor_liquido,
        data_recebimento if data_recebimento else None,
        observacao if observacao else None
    ))

    salario_id = cur.fetchone()[0]
    conn.commit()

    print("✔ Salário cadastrado com sucesso.")
    return salario_id


# -------------------------------
# CATEGORIA
# -------------------------------

def escolher_categoria(conn):
    cur = conn.cursor()

    cur.execute("""
        SELECT id, nome, icone, cor_hex FROM financas.categoria
        WHERE ativo = TRUE
        ORDER BY nome, icone, cor_hex
    """)

    categorias = [
    ('Alimentação', '🍽️', '#E67E22'),
    ('Moradia', '🏠', '#2ECC71'),
    ('Transporte', '🚗', '#3498DB'),
    ('Saúde', '💊', '#E74C3C'),
    ('Lazer', '🎮', '#9B59B6'),
    ('Educação', '📚', '#1ABC9C'),
    ('Investimento', '📈', '#F1C40F'),
    ('Assinatura', '📱', '#34495E'),
    ('Vestuário', '👕', '#E91E63'),
    ('Outros', '💡', '#95A5A6')
]

    nomes = [c[1] for c in categorias]
    index = escolher_opcao(nomes, "Categorias disponíveis:")

    return categorias[index][0]


# -------------------------------
# FORMA DE PAGAMENTO
# -------------------------------

FORMAS_PGTO = ['pix', 'credito', 'debito', 'dinheiro', 'boleto', 'transferencia']


def escolher_forma_pagamento():
    index = escolher_opcao(FORMAS_PGTO, "Formas de pagamento:")
    return FORMAS_PGTO[index]


# -------------------------------
# GASTO
# -------------------------------

def inserir_gasto():
    conn = get_connection()
    cur = conn.cursor()

    try:
        print("\n=== NOVO GASTO ===")

        # Salário
        salario_id = obter_ou_criar_salario(conn)

        # Dados do gasto
        data_gasto = input("Data do gasto (YYYY-MM-DD): ")
        descricao = input("Descrição: ")
        valor = float(input("Valor: "))

        categoria_id = escolher_categoria(conn)
        forma_pgto = escolher_forma_pagamento()

        # Parcelamento
        parcelado_input = input("Foi parcelado? (s/n): ").lower()
        parcelado = parcelado_input == 's'

        num_parcelas = None
        parcela_atual = None

        if parcelado:
            num_parcelas = int(input("Número de parcelas: "))
            parcela_atual = int(input("Parcela atual: "))

        observacao = input("Observação (opcional): ")

        # INSERT
        cur.execute("""
            INSERT INTO financas.gasto (
                salario_mes_id,
                categoria_id,
                data_gasto,
                descricao,
                valor,
                forma_pagamento,
                parcelado,
                num_parcelas,
                parcela_atual,
                observacao
            )
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            salario_id,
            categoria_id,
            data_gasto,
            descricao,
            valor,
            forma_pgto,
            parcelado,
            num_parcelas,
            parcela_atual,
            observacao if observacao else None
        ))

        conn.commit()
        print("✔ Gasto inserido com sucesso!")

    except Exception as e:
        conn.rollback()
        print("❌ Erro:", e)

    finally:
        cur.close()
        conn.close()


# -------------------------------
# MENU PRINCIPAL
# -------------------------------

def main():
    while True:
        print("\n=== SISTEMA FINANCEIRO ===")
        print("1 - Inserir gasto")
        print("0 - Sair")

        opcao = input("Escolha: ")

        if opcao == "1":
            inserir_gasto()
        elif opcao == "0":
            break
        else:
            print("Opção inválida.")


if __name__ == "__main__":
    main()