# -*- coding: utf-8 -*-
"""
Respostas de exemplo: atendimento de uma confeitaria fictícia, por palavras-chave.

Serve só para demonstrar o ritmo humano. Para usar uma IA (ChatGPT, Gemini, Claude...),
basta trocar gerar_resposta por uma função que receba a lista de mensagens e devolva o texto.
Separe os parágrafos com uma linha em branco: cada parágrafo vira um balão.
"""
import re
import unicodedata

NOME_LOJA = 'Doce Ponto Confeitaria'  # loja fictícia

SAUDACAO = r'\b(oi|ola|opa|eai|bom dia|boa tarde|boa noite)\b'

# (padrão procurado no texto sem acentos, resposta)
REGRAS = [
    (r'\b(robo|bot|humano|pessoa de verdade|inteligencia artificial)\b',
     f'Sou um assistente automático da {NOME_LOJA} 🤖 '
     'Se preferir falar com uma pessoa, é só digitar "atendente".'),
    (r'\batendente\b',
     'Certo! Já avisei a equipe. Em horário comercial, alguém te responde em poucos minutos.'),
    (r'\b(horario|abre|abrem|fecha|fecham|funciona|funcionam)\b',
     'Funcionamos de terça a domingo, das 9h às 19h.'),
    (r'\b(preco|precos|valor|valores|quanto|custa|cardapio)\b',
     'Os bolos começam em R$ 45 e os docinhos em R$ 1,80 a unidade. '
     'Quer que eu te mande o cardápio completo?'),
    (r'\b(entrega|entregam|delivery|frete)\b',
     'Entregamos em toda a cidade. O frete é calculado pelo bairro.'),
    (r'\b(encomenda|encomendar|encomendas|pedido|pedir)\b',
     'As encomendas precisam de 48 horas de antecedência. '
     'Me diga a data e o sabor que eu já anoto para você.'),
]

NAO_ENTENDI = ('Não entendi muito bem 🤔 '
               'Posso te ajudar com horário, preços, entrega ou encomendas.')


def normalizar(texto):
    sem_acento = unicodedata.normalize('NFKD', texto).encode('ascii', 'ignore').decode()
    return sem_acento.lower()


def gerar_resposta(mensagens):
    """
    Recebe TODAS as mensagens que o cliente mandou em sequência e responde tudo
    de uma vez, um parágrafo por assunto.
    """
    texto = normalizar(' '.join(mensagens))
    partes = []

    if re.search(SAUDACAO, texto):
        partes.append('Oi! Tudo bem? 😊')

    partes += [resposta for padrao, resposta in REGRAS if re.search(padrao, texto)]

    if not partes:
        partes.append(NAO_ENTENDI)
    elif len(partes) == 1 and partes[0].startswith('Oi!'):
        partes.append('Como posso te ajudar hoje?')

    return '\n\n'.join(partes)
