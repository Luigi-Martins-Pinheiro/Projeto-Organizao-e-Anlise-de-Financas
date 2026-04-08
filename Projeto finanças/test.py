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