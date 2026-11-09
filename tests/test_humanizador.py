# -*- coding: utf-8 -*-
"""Testes: python -m unittest -v"""
import asyncio
import random
import re
import unittest

from humanizador import Atendente, Config, calcular_atraso, contar_linhas, dividir_em_baloes
from respostas import NAO_ENTENDI, gerar_resposta

CURTO = 'Funcionamos das 9h às 19h.'
LONGO = '\n'.join(['Esta é uma linha comprida o bastante para contar como uma linha.'] * 6)

# Em testes, 1 segundo "de bot" dura 10 ms
RAPIDO = Config(escala_tempo=0.01)


def sem_espacos(texto):
    return re.sub(r'\s+', '', texto)


class TesteAtraso(unittest.TestCase):
    def test_resposta_curta_espera_de_2_a_5_segundos(self):
        rng = random.Random(1)
        for _ in range(200):
            self.assertTrue(2.0 <= calcular_atraso(CURTO, rng=rng) <= 5.0)

    def test_resposta_longa_espera_mais_mas_tem_limite(self):
        rng = random.Random(2)
        cfg = Config(atraso_maximo=100)
        linhas = contar_linhas(LONGO, cfg)
        for _ in range(200):
            atraso = calcular_atraso(LONGO, cfg, rng)
            self.assertTrue(linhas * 1.0 <= atraso <= linhas * 2.0)
        self.assertLessEqual(calcular_atraso(LONGO * 10, rng=rng), Config().atraso_maximo)

    def test_baloes_seguintes_nao_repetem_a_espera_inicial(self):
        rng = random.Random(3)
        atraso = calcular_atraso('ok', rng=rng, primeiro_balao=False)
        self.assertTrue(1.0 <= atraso <= 2.0)


class TesteBaloes(unittest.TestCase):
    def test_texto_curto_vira_um_balao(self):
        self.assertEqual(dividir_em_baloes(CURTO), [CURTO])

    def test_um_balao_por_paragrafo(self):
        self.assertEqual(dividir_em_baloes('Oi!\n\nTudo bem?\n\nComo posso ajudar?'),
                         ['Oi!', 'Tudo bem?', 'Como posso ajudar?'])

    def test_no_maximo_3_baloes_sem_perder_texto(self):
        texto = '\n\n'.join(f'Parágrafo número {n}.' for n in range(1, 8))
        baloes = dividir_em_baloes(texto)
        self.assertEqual(len(baloes), 3)
        self.assertEqual(sem_espacos(''.join(baloes)), sem_espacos(texto))

    def test_paragrafo_unico_longo_e_dividido_por_frase(self):
        texto = ('Recebemos o seu pedido e ele já está em produção na nossa cozinha. '
                 'A previsão de entrega é amanhã à tarde, entre 14h e 17h. '
                 'Se precisar mudar o endereço, me avise até hoje à noite.')
        baloes = dividir_em_baloes(texto)
        self.assertGreater(len(baloes), 1)
        self.assertEqual(sem_espacos(''.join(baloes)), sem_espacos(texto))

    def test_texto_vazio_nao_gera_balao(self):
        self.assertEqual(dividir_em_baloes('   \n '), [])


class Registro:
    """Plataforma falsa que anota tudo o que o bot fez, na ordem."""

    def __init__(self):
        self.eventos = []
        self.pedidos = []

    def gerar(self, mensagens):
        self.pedidos.append(list(mensagens))
        return 'Primeira parte.\n\nSegunda parte.'

    def enviar(self, chat, texto):
        self.eventos.append(('enviar', chat, texto))

    def digitando(self, chat):
        self.eventos.append(('digitando', chat))


class TesteAtendente(unittest.IsolatedAsyncioTestCase):
    def novo(self, cfg=RAPIDO):
        r = Registro()
        return r, Atendente(r.gerar, r.enviar, r.digitando, cfg, random.Random(0))

    async def test_mensagens_seguidas_viram_uma_resposta_so(self):
        r, bot = self.novo()
        for texto in ('oi', 'vocês entregam?', 'quanto custa?'):
            await bot.receber(1, texto)
            await asyncio.sleep(0.02)  # 2 s "de bot": menos que a janela de 6 s
        await bot.concluir()
        self.assertEqual(r.pedidos, [['oi', 'vocês entregam?', 'quanto custa?']])

    async def test_a_espera_reinicia_a_cada_mensagem(self):
        r, bot = self.novo()
        inicio = asyncio.get_running_loop().time()
        await bot.receber(1, 'primeira')
        await asyncio.sleep(0.04)
        await bot.receber(1, 'segunda')  # reinicia: responde ~6 s depois DESTA
        await bot.concluir()
        primeiro_envio = asyncio.get_running_loop().time() - inicio
        self.assertGreaterEqual(primeiro_envio, 0.04 + 0.06)
        self.assertEqual(r.pedidos, [['primeira', 'segunda']])

    async def test_conversas_separadas_tem_respostas_separadas(self):
        r, bot = self.novo()
        await bot.receber(1, 'primeira')
        await bot.concluir()
        await bot.receber(1, 'segunda')
        await bot.concluir()
        self.assertEqual(r.pedidos, [['primeira'], ['segunda']])

    async def test_digitando_antes_de_cada_balao(self):
        r, bot = self.novo()
        await bot.receber(7, 'oi')
        await bot.concluir()
        envios = [e for e in r.eventos if e[0] == 'enviar']
        self.assertEqual([e[2] for e in envios], ['Primeira parte.', 'Segunda parte.'])
        for i, evento in enumerate(r.eventos):
            if evento[0] == 'enviar':
                self.assertEqual(r.eventos[i - 1], ('digitando', 7))

    async def test_digitando_e_renovado_em_esperas_longas(self):
        r, bot = self.novo(Config(escala_tempo=0.01, espera_inicial=(9.0, 9.0),
                                  atraso_maximo=9.0, renovar_digitando=4.0))
        await bot.receber(1, 'oi')
        await bot.concluir()
        antes_do_primeiro = r.eventos[:r.eventos.index(('enviar', 1, 'Primeira parte.'))]
        self.assertEqual(antes_do_primeiro.count(('digitando', 1)), 3)  # 4 s + 4 s + 1 s

    async def test_mensagem_durante_a_resposta_nao_se_perde(self):
        r, bot = self.novo()
        await bot.receber(1, 'primeira')
        await asyncio.sleep(0.08)  # já passou a janela: o bot está "digitando"
        await bot.receber(1, 'chegou no meio')
        await bot.concluir()
        self.assertEqual(r.pedidos, [['primeira'], ['chegou no meio']])
        self.assertEqual(len([e for e in r.eventos if e[0] == 'enviar']), 4)

    async def test_chats_diferentes_nao_se_misturam(self):
        r, bot = self.novo()
        await bot.receber('ana', 'oi')
        await bot.receber('beto', 'olá')
        await bot.concluir()
        self.assertCountEqual(r.pedidos, [['oi'], ['olá']])

    async def test_erro_na_resposta_nao_derruba_o_bot(self):
        r, bot = self.novo()
        chamadas = []

        def gerar(mensagens):
            chamadas.append(mensagens)
            if len(chamadas) == 1:
                raise RuntimeError('falha simulada')
            return 'Tudo certo.'
        bot._gerar = gerar
        await bot.receber(1, 'primeira')
        await bot.concluir()
        await bot.receber(1, 'segunda')
        await bot.concluir()
        self.assertEqual(r.eventos[-1], ('enviar', 1, 'Tudo certo.'))


class TesteRespostas(unittest.TestCase):
    def test_admite_que_e_um_robo(self):
        self.assertIn('assistente automático', gerar_resposta(['você é um robô?']))

    def test_responde_varias_perguntas_de_uma_vez(self):
        resposta = gerar_resposta(['oi', 'vcs entregam?', 'qual o horário?'])
        self.assertEqual(len(dividir_em_baloes(resposta)), 3)
        self.assertIn('Entregamos', resposta)
        self.assertIn('terça a domingo', resposta)

    def test_entende_sem_acento_e_com_maiuscula(self):
        self.assertIn('R$ 45', gerar_resposta(['QUANTO CUSTA O BOLO']))
        self.assertIn('R$ 45', gerar_resposta(['qual o preço']))

    def test_assunto_desconhecido(self):
        self.assertEqual(gerar_resposta(['asdfgh']), NAO_ENTENDI)

    def test_so_saudacao_puxa_conversa(self):
        self.assertIn('Como posso te ajudar', gerar_resposta(['bom dia']))


if __name__ == '__main__':
    unittest.main()
