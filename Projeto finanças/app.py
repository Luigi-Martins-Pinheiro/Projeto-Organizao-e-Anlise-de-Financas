from db import get_connection
from datetime import datetime


# ─────────────────────────────────────────
# UTILIDADES
# ─────────────────────────────────────────

def linha(char="─", n=45):
    print(char * n)

def titulo(texto):
    linha()
    print(f"  {texto}")
    linha()

def escolher_opcao(opcoes, cabecalho="Escolha uma opção:"):
    print(f"\n{cabecalho}")
    for i, op in enumerate(opcoes, 1):
        print(f"  {i} - {op}")
    while True:
        try:
            v = int(input("→ "))
            if 1 <= v <= len(opcoes):
                return v - 1
        except (ValueError, KeyboardInterrupt):
            pass
        print("  ⚠ Opção inválida, tente novamente.")

def input_data(prompt, obrigatorio=True):
    while True:
        raw = input(prompt).strip()
        if not raw and not obrigatorio:
            return None
        try:
            datetime.strptime(raw, "%Y-%m-%d")
            return raw
        except ValueError:
            print("  ⚠ Formato inválido. Use YYYY-MM-DD (ex: 2026-04-08).")

def input_decimal(prompt, minimo=0.01):
    while True:
        try:
            v = float(input(prompt).replace(",", "."))
            if v >= minimo:
                return round(v, 2)
        except ValueError:
            pass
        print(f"  ⚠ Informe um valor numérico maior que {minimo}.")

def input_inteiro(prompt, minimo=1, maximo=None):
    while True:
        try:
            v = int(input(prompt))
            if v >= minimo and (maximo is None or v <= maximo):
                return v
        except ValueError:
            pass
        limite = f"{minimo}–{maximo}" if maximo else f">= {minimo}"
        print(f"  ⚠ Informe um inteiro ({limite}).")

def confirmar(prompt="Confirmar? (s/n): "):
    return input(prompt).strip().lower() == "s"


# ─────────────────────────────────────────
# SALÁRIO
# ─────────────────────────────────────────

def obter_salario_mes(conn):
    """
    Pede mês/ano. Se já existe exibe os dados e retorna (id, mes, ano).
    Se não existe oferece cadastrar. Retorna (None, mes, ano) se o usuário cancelar.
    """
    cur = conn.cursor()

    mes = input_inteiro("Mês (1-12): ", 1, 12)
    ano = input_inteiro("Ano (ex: 2026): ", 2000, 2100)

    cur.execute("""
        SELECT id, valor_bruto, valor_liquido
        FROM financas.salario_mes
        WHERE mes = %s AND ano = %s
    """, (mes, ano))
    row = cur.fetchone()
    cur.close()

    if row:
        print(f"\n  ✔ Salário {mes:02d}/{ano} já cadastrado.")
        print(f"     Bruto  : R$ {row[1]:,.2f}")
        print(f"     Líquido: R$ {row[2]:,.2f}")
        return row[0], mes, ano

    print(f"\n  ⚠ Salário {mes:02d}/{ano} não encontrado.")
    if not confirmar("  Deseja cadastrar o salário deste mês? (s/n): "):
        return None, mes, ano

    cur = conn.cursor()
    valor_bruto   = input_decimal("  Valor bruto (R$): ")
    valor_liquido = input_decimal("  Valor líquido (R$): ")
    data_rec      = input_data("  Data de recebimento (YYYY-MM-DD ou ENTER): ", obrigatorio=False)
    observacao    = input("  Observação (opcional, ENTER para pular): ").strip() or None

    cur.execute("""
        INSERT INTO financas.salario_mes
            (mes, ano, valor_bruto, valor_liquido, data_recebimento, observacao)
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING id
    """, (mes, ano, valor_bruto, valor_liquido, data_rec, observacao))

    salario_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    print(f"  ✔ Salário {mes:02d}/{ano} cadastrado com sucesso!")
    return salario_id, mes, ano


# ─────────────────────────────────────────
# CATEGORIA
# ─────────────────────────────────────────

CATEGORIAS = [
    ("Alimentação",  "🍽️"),
    ("Moradia",      "🏠"),
    ("Transporte",   "🚗"),
    ("Saúde",        "💊"),
    ("Lazer",        "🎮"),
    ("Educação",     "📚"),
    ("Investimento", "📈"),
    ("Assinatura",   "📱"),
    ("Vestuário",    "👕"),
    ("Outros",       "💡"),
]

def escolher_categoria(conn):
    """Exibe lista fixa e retorna o id da categoria no banco."""
    cur = conn.cursor()
    opcoes = [f"{icone}  {nome}" for nome, icone in CATEGORIAS]
    idx = escolher_opcao(opcoes, "Categoria do gasto:")
    nome_escolhido = CATEGORIAS[idx][0]

    cur.execute("""
        SELECT id FROM financas.categoria
        WHERE nome = %s AND ativo = TRUE
    """, (nome_escolhido,))
    row = cur.fetchone()
    cur.close()

    if not row:
        raise RuntimeError(
            f"Categoria '{nome_escolhido}' não encontrada no banco. "
            "Verifique se o SQL da Etapa 1 foi executado."
        )
    return row[0]


# ─────────────────────────────────────────
# FORMA DE PAGAMENTO
# ─────────────────────────────────────────

FORMAS_PGTO = ["pix", "credito", "debito", "dinheiro", "boleto", "transferencia"]
LABELS_PGTO = ["PIX", "Crédito", "Débito", "Dinheiro", "Boleto", "Transferência"]

def escolher_forma_pagamento():
    idx = escolher_opcao(LABELS_PGTO, "Forma de pagamento:")
    return FORMAS_PGTO[idx]


# ─────────────────────────────────────────
# INSERIR GASTO
# ─────────────────────────────────────────

def _formulario_gasto(conn, salario_id):
    """Coleta dados de um gasto e insere. Retorna True se inserido."""
    cur = conn.cursor()

    data_gasto = input_data("  Data do gasto (YYYY-MM-DD): ")

    descricao = ""
    while not descricao:
        descricao = input("  Descrição: ").strip()
        if not descricao:
            print("  ⚠ Descrição obrigatória.")

    valor        = input_decimal("  Valor (R$): ")
    categoria_id = escolher_categoria(conn)
    forma_pgto   = escolher_forma_pagamento()

    parcelado    = confirmar("  Foi parcelado? (s/n): ")
    num_parcelas = parcela_atual = None
    if parcelado:
        num_parcelas  = input_inteiro("  Total de parcelas: ", minimo=2)
        parcela_atual = input_inteiro(f"  Parcela atual (1–{num_parcelas}): ", 1, num_parcelas)

    observacao = input("  Observação (opcional, ENTER para pular): ").strip() or None

    print("\n  ── Resumo ──────────────────────────────────")
    print(f"  Data      : {data_gasto}")
    print(f"  Descrição : {descricao}")
    print(f"  Valor     : R$ {valor:,.2f}")
    print(f"  Pagamento : {forma_pgto}")
    if parcelado:
        print(f"  Parcela   : {parcela_atual}/{num_parcelas}")
    if observacao:
        print(f"  Obs       : {observacao}")
    print("  ────────────────────────────────────────────")

    if not confirmar("  Salvar gasto? (s/n): "):
        print("  ✖ Cancelado.")
        cur.close()
        return False

    cur.execute("""
        INSERT INTO financas.gasto (
            salario_mes_id, categoria_id, data_gasto, descricao,
            valor, forma_pagamento, parcelado,
            num_parcelas, parcela_atual, observacao
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, (
        salario_id, categoria_id, data_gasto, descricao,
        valor, forma_pgto, parcelado,
        num_parcelas, parcela_atual, observacao
    ))
    conn.commit()
    cur.close()
    print("  ✔ Gasto inserido com sucesso!")
    return True


def inserir_gasto():
    conn = get_connection()
    try:
        titulo("INSERIR GASTO")

        salario_id, mes, ano = obter_salario_mes(conn)
        if salario_id is None:
            print("  ⚠ Sem salário cadastrado. Operação cancelada.")
            return

        # Loop: vários gastos no mesmo mês sem voltar ao menu
        while True:
            print(f"\n  → Novo gasto em {mes:02d}/{ano}")
            _formulario_gasto(conn, salario_id)
            if not confirmar("\n  Inserir outro gasto neste mesmo mês? (s/n): "):
                break

    except Exception as e:
        conn.rollback()
        print(f"  ❌ Erro: {e}")
    finally:
        conn.close()


# ─────────────────────────────────────────
# RECEITA EXTRA
# ─────────────────────────────────────────

TIPOS_RECEITA  = ["divida_recebida", "venda", "freelance", "bonus", "outro"]
LABELS_RECEITA = [
    "💸 Dívida recebida   (alguém te pagou de volta)",
    "🛒 Venda             (bem ou produto vendido)",
    "💻 Freelance         (serviço avulso)",
    "🎁 Bônus             (gratificação / extra do trabalho)",
    "📦 Outro             (qualquer outra entrada)",
]

def _formulario_receita(conn, salario_id):
    """Coleta dados de uma receita extra e insere. Retorna True se inserido."""
    cur = conn.cursor()

    descricao = ""
    while not descricao:
        descricao = input("  Descrição: ").strip()
        if not descricao:
            print("  ⚠ Descrição obrigatória.")

    valor    = input_decimal("  Valor (R$): ")
    idx_tipo = escolher_opcao(LABELS_RECEITA, "Tipo de receita extra:")
    tipo     = TIPOS_RECEITA[idx_tipo]
    data_rec = input_data("  Data de recebimento (YYYY-MM-DD ou ENTER): ", obrigatorio=False)

    parcelado    = confirmar("  É parcelado? (ex: venda em parcelas) (s/n): ")
    num_parcelas = parcela_atual = None
    if parcelado:
        num_parcelas  = input_inteiro("  Total de parcelas: ", minimo=2)
        parcela_atual = input_inteiro(f"  Parcela atual (1–{num_parcelas}): ", 1, num_parcelas)

    observacao = input("  Observação (opcional, ENTER para pular): ").strip() or None

    print("\n  ── Resumo ──────────────────────────────────")
    print(f"  Descrição : {descricao}")
    print(f"  Valor     : R$ {valor:,.2f}")
    print(f"  Tipo      : {tipo}")
    if data_rec:
        print(f"  Recebido  : {data_rec}")
    if parcelado:
        print(f"  Parcela   : {parcela_atual}/{num_parcelas}")
    if observacao:
        print(f"  Obs       : {observacao}")
    print("  ────────────────────────────────────────────")

    if not confirmar("  Salvar receita extra? (s/n): "):
        print("  ✖ Cancelado.")
        cur.close()
        return False

    cur.execute("""
        INSERT INTO financas.receita_extra
            (salario_mes_id, descricao, valor, tipo,
             data_recebimento, parcelado, num_parcelas, parcela_atual, observacao)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, (
        salario_id, descricao, valor, tipo,
        data_rec, parcelado, num_parcelas, parcela_atual, observacao
    ))
    conn.commit()
    cur.close()
    print("  ✔ Receita extra inserida com sucesso!")
    return True


def inserir_receita_extra():
    conn = get_connection()
    try:
        titulo("INSERIR RECEITA EXTRA")

        salario_id, mes, ano = obter_salario_mes(conn)
        if salario_id is None:
            print("  ⚠ Sem salário cadastrado. Operação cancelada.")
            return

        while True:
            print(f"\n  → Nova receita extra em {mes:02d}/{ano}")
            _formulario_receita(conn, salario_id)
            if not confirmar("\n  Inserir outra receita extra neste mesmo mês? (s/n): "):
                break

    except Exception as e:
        conn.rollback()
        print(f"  ❌ Erro: {e}")
    finally:
        conn.close()


# ─────────────────────────────────────────
# LISTAR GASTOS DO MÊS
# ─────────────────────────────────────────

def listar_gastos():
    conn = get_connection()
    cur  = conn.cursor()
    try:
        titulo("GASTOS DO MÊS")

        mes = input_inteiro("Mês (1-12): ", 1, 12)
        ano = input_inteiro("Ano (ex: 2026): ", 2000, 2100)

        cur.execute("""
            SELECT
                g.data_gasto,
                c.icone || ' ' || c.nome,
                g.descricao,
                g.valor,
                g.forma_pagamento,
                g.parcelado,
                g.num_parcelas,
                g.parcela_atual
            FROM financas.gasto g
            JOIN financas.categoria   c ON c.id = g.categoria_id
            JOIN financas.salario_mes s ON s.id = g.salario_mes_id
            WHERE s.mes = %s AND s.ano = %s
            ORDER BY g.data_gasto, g.id
        """, (mes, ano))

        rows = cur.fetchall()
        if not rows:
            print(f"  Nenhum gasto registrado em {mes:02d}/{ano}.")
            return

        total = 0
        print(f"\n  {'Data':<12} {'Categoria':<22} {'Descrição':<24} {'Valor':>10}  Pgto")
        linha("─")
        for data, cat, desc, valor, pgto, parcelado, n_parc, p_atual in rows:
            parcela_txt = f" ({p_atual}/{n_parc})" if parcelado else ""
            print(f"  {str(data):<12} {cat:<22} {desc[:23]:<24} "
                  f"R$ {valor:>8,.2f}  {pgto}{parcela_txt}")
            total += valor

        linha("─")
        print(f"  {'TOTAL':>61}  R$ {total:>8,.2f}")

    except Exception as e:
        print(f"  ❌ Erro: {e}")
    finally:
        cur.close()
        conn.close()


# ─────────────────────────────────────────
# RESUMO MENSAL
# ─────────────────────────────────────────

def resumo_mensal():
    conn = get_connection()
    cur  = conn.cursor()
    try:
        titulo("RESUMO MENSAL")

        mes = input_inteiro("Mês (1-12): ", 1, 12)
        ano = input_inteiro("Ano (ex: 2026): ", 2000, 2100)

        cur.execute("""
            SELECT id, valor_bruto, valor_liquido
            FROM financas.salario_mes WHERE mes = %s AND ano = %s
        """, (mes, ano))
        sal = cur.fetchone()
        if not sal:
            print(f"  ⚠ Sem salário cadastrado para {mes:02d}/{ano}.")
            return

        salario_id, bruto, liquido = sal

        # Total de receitas extras
        cur.execute("""
            SELECT COALESCE(SUM(valor), 0)
            FROM financas.receita_extra WHERE salario_mes_id = %s
        """, (salario_id,))
        total_extras = cur.fetchone()[0]

        # Gastos por categoria
        cur.execute("""
            SELECT c.icone || ' ' || c.nome, SUM(g.valor)
            FROM financas.gasto g
            JOIN financas.categoria c ON c.id = g.categoria_id
            WHERE g.salario_mes_id = %s
            GROUP BY c.id, c.nome, c.icone
            ORDER BY SUM(g.valor) DESC
        """, (salario_id,))
        gastos = cur.fetchall()

        # Metas
        cur.execute("""
            SELECT c.icone || ' ' || c.nome, m.valor_limite
            FROM financas.meta_mensal m
            JOIN financas.categoria c ON c.id = m.categoria_id
            WHERE m.salario_mes_id = %s
        """, (salario_id,))
        metas = {r[0]: r[1] for r in cur.fetchall()}

        total_gastos = sum(r[1] for r in gastos) if gastos else 0
        renda_total  = liquido + total_extras
        saldo        = renda_total - total_gastos

        print(f"\n  Período        : {mes:02d}/{ano}")
        print(f"  Salário líquido: R$ {liquido:>10,.2f}  (bruto: R$ {bruto:,.2f})")
        if total_extras > 0:
            print(f"  Receitas extras: R$ {total_extras:>10,.2f}")
        print(f"  Renda total    : R$ {renda_total:>10,.2f}")
        print(f"  Total gasto    : R$ {total_gastos:>10,.2f}")
        emoji = "✔" if saldo >= 0 else "⚠"
        print(f"  Saldo          : R$ {saldo:>10,.2f}  {emoji}")

        if gastos:
            print(f"\n  {'Categoria':<25} {'Gasto':>10}  {'Meta':>10}  Status")
            linha("─")
            for cat, valor in gastos:
                meta     = metas.get(cat)
                meta_txt = f"R$ {meta:>8,.2f}" if meta else "         —"
                status   = ""
                if meta:
                    status = "✔ OK" if valor <= meta else f"⚠ +R$ {valor - meta:,.2f}"
                print(f"  {cat:<25} R$ {valor:>8,.2f}  {meta_txt}  {status}")

        # Detalhe das receitas extras
        if total_extras > 0:
            cur.execute("""
                SELECT descricao, valor, tipo, data_recebimento,
                       parcelado, num_parcelas, parcela_atual
                FROM financas.receita_extra
                WHERE salario_mes_id = %s
                ORDER BY data_recebimento, id
            """, (salario_id,))
            extras = cur.fetchall()
            print(f"\n  Receitas extras:")
            linha("─")
            for desc, val, tipo, data_rec, parcelado, n_parc, p_atual in extras:
                parcela_txt = f" ({p_atual}/{n_parc})" if parcelado else ""
                data_txt    = str(data_rec) if data_rec else "—"
                print(f"  {data_txt:<12} {tipo:<18} {desc[:24]:<25} R$ {val:>8,.2f}{parcela_txt}")

    except Exception as e:
        print(f"  ❌ Erro: {e}")
    finally:
        cur.close()
        conn.close()


# ─────────────────────────────────────────
# GERENCIAR METAS
# ─────────────────────────────────────────

def gerenciar_metas():
    conn = get_connection()
    cur  = conn.cursor()
    try:
        titulo("METAS MENSAIS")
        print("  1 - Definir / atualizar meta")
        print("  2 - Ver metas do mês")
        print("  0 - Voltar")
        op = input("→ ").strip()

        if op == "1":
            salario_id, _, _ = obter_salario_mes(conn)
            if salario_id is None:
                print("  ⚠ Sem salário cadastrado.")
                return
            categoria_id = escolher_categoria(conn)
            limite       = input_decimal("  Valor limite para a categoria (R$): ")

            cur.execute("""
                INSERT INTO financas.meta_mensal
                    (salario_mes_id, categoria_id, valor_limite)
                VALUES (%s, %s, %s)
                ON CONFLICT (salario_mes_id, categoria_id)
                DO UPDATE SET valor_limite = EXCLUDED.valor_limite
            """, (salario_id, categoria_id, limite))
            conn.commit()
            print("  ✔ Meta salva!")

        elif op == "2":
            mes = input_inteiro("Mês (1-12): ", 1, 12)
            ano = input_inteiro("Ano (ex: 2026): ", 2000, 2100)
            cur.execute("""
                SELECT c.icone || ' ' || c.nome, m.valor_limite
                FROM financas.meta_mensal m
                JOIN financas.categoria   c ON c.id = m.categoria_id
                JOIN financas.salario_mes s ON s.id = m.salario_mes_id
                WHERE s.mes = %s AND s.ano = %s
                ORDER BY c.nome
            """, (mes, ano))
            rows = cur.fetchall()
            if not rows:
                print(f"  Nenhuma meta para {mes:02d}/{ano}.")
            else:
                print(f"\n  {'Categoria':<25} {'Limite':>10}")
                linha("─")
                for cat, lim in rows:
                    print(f"  {cat:<25} R$ {lim:>8,.2f}")

    except Exception as e:
        conn.rollback()
        print(f"  ❌ Erro: {e}")
    finally:
        cur.close()
        conn.close()


# ─────────────────────────────────────────
# MENU PRINCIPAL
# ─────────────────────────────────────────

def main():
    while True:
        titulo("SISTEMA FINANCEIRO PESSOAL")
        print("  1 - Inserir gasto")
        print("  2 - Inserir receita extra")
        print("  3 - Listar gastos do mês")
        print("  4 - Resumo mensal")
        print("  5 - Gerenciar metas")
        print("  0 - Sair")
        linha()
        op = input("→ ").strip()

        if   op == "1": inserir_gasto()
        elif op == "2": inserir_receita_extra()
        elif op == "3": listar_gastos()
        elif op == "4": resumo_mensal()
        elif op == "5": gerenciar_metas()
        elif op == "0":
            print("\n  Até logo! 👋\n")
            break
        else:
            print("  ⚠ Opção inválida.")


if __name__ == "__main__":
    main()
