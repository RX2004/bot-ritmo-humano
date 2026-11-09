# -*- coding: utf-8 -*-
"""
Núcleo do bot humanizado: as 4 técnicas de ritmo humano, sem depender de plataforma.

1. Atraso inteligente  - espera de 2 a 5 s, ou 1 a 2 s por linha em respostas longas
2. "Digitando..."      - o indicador fica ativo durante toda a espera
3. Quebra de mensagens - a resposta sai em 2 ou 3 balões curtos, com pausa entre eles
4. Reset na interrupção - cada mensagem nova reinicia a contagem; o bot só responde
                          quando o cliente para de escrever, e responde tudo de uma vez

Qualquer plataforma (Telegram, WhatsApp, console) só precisa fornecer duas funções:
enviar(chat_id, texto) e digitando(chat_id). Podem ser normais ou async.
"""
import asyncio
import inspect
import math
import random
import re
import sys
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    espera_inicial: tuple = (2.0, 5.0)       # atraso antes do primeiro balão (s)
    segundos_por_linha: tuple = (1.0, 2.0)   # tempo de "digitação" por linha (s)
    caracteres_por_linha: int = 45           # quantos caracteres contam como uma linha
    atraso_maximo: float = 8.0               # ninguém espera mais que isso por um balão
    pausa_entre_baloes: tuple = (1.0, 2.0)   # pausa entre um balão e o próximo (s)
    max_baloes: int = 3
    janela_silencio: float = 6.0             # quanto tempo de silêncio antes de responder (s)
    renovar_digitando: float = 4.0           # o Telegram apaga o "digitando" após ~5 s
    escala_tempo: float = 1.0                # 0.1 = 10x mais rápido (útil em testes e demos)


def contar_linhas(texto, cfg=Config()):
    """Linhas como aparecem no celular: quebras de linha + quebra automática por tamanho."""
    return sum(max(1, math.ceil(len(linha) / cfg.caracteres_por_linha))
               for linha in texto.splitlines() or [''])


def calcular_atraso(texto, cfg=Config(), rng=random, primeiro_balao=True):
    """
    Técnica 1 - atraso inteligente.
    Primeiro balão: no mínimo 2 a 5 s ("lendo e pensando"); se o texto for longo,
    vale o tempo de digitação (1 a 2 s por linha). Sempre limitado a atraso_maximo.
    """
    digitacao = contar_linhas(texto, cfg) * rng.uniform(*cfg.segundos_por_linha)
    atraso = max(rng.uniform(*cfg.espera_inicial), digitacao) if primeiro_balao else digitacao
    return min(atraso, cfg.atraso_maximo)


def dividir_em_baloes(texto, cfg=Config()):
    """
    Técnica 3 - quebra de mensagens.
    Divide por parágrafo; se for um parágrafo único e longo, divide por frase.
    Depois junta os pedaços vizinhos menores até sobrarem no máximo max_baloes.
    """
    texto = texto.strip()
    if not texto:
        return []

    partes = [p.strip() for p in re.split(r'\n\s*\n', texto) if p.strip()]
    separador = '\n\n'
    if len(partes) == 1 and len(texto) > cfg.caracteres_por_linha * 3:
        frases = [f.strip() for f in re.split(r'(?<=[.!?…])\s+', texto) if f.strip()]
        if len(frases) > 1:
            partes, separador = frases, ' '

    while len(partes) > cfg.max_baloes:
        i = min(range(len(partes) - 1), key=lambda k: len(partes[k]) + len(partes[k + 1]))
        partes[i:i + 2] = [partes[i] + separador + partes[i + 1]]
    return partes


async def _chamar(funcao, *args):
    resultado = funcao(*args)
    return await resultado if inspect.isawaitable(resultado) else resultado


class Atendente:
    """
    Recebe as mensagens, espera o cliente terminar de escrever e responde com ritmo humano.

    gerar_resposta(lista_de_mensagens) -> texto   (pode ser uma IA, regras, o que for)
    enviar(chat_id, texto)
    digitando(chat_id)
    """

    def __init__(self, gerar_resposta, enviar, digitando, config=None, rng=None):
        self.cfg = config or Config()
        self._gerar = gerar_resposta
        self._enviar = enviar
        self._digitando = digitando
        self._rng = rng or random.Random()
        self._pendentes = {}     # chat_id -> mensagens que ainda não foram respondidas
        self._tarefas = {}       # chat_id -> tarefa que vai responder
        self._respondendo = set()

    async def receber(self, chat_id, texto):
        """Técnica 4 - cada mensagem nova reinicia a contagem de silêncio."""
        self._pendentes.setdefault(chat_id, []).append(texto)
        if chat_id in self._respondendo:
            return  # já está respondendo: esta mensagem entra na próxima rodada
        self._agendar(chat_id)

    async def concluir(self):
        """Espera todas as respostas em andamento terminarem (usado em testes e no encerramento)."""
        while any(not t.done() for t in self._tarefas.values()):
            await asyncio.gather(*self._tarefas.values(), return_exceptions=True)

    # ------------------------------------------------------------------ interno

    def _agendar(self, chat_id):
        anterior = self._tarefas.get(chat_id)
        if anterior and not anterior.done() and anterior is not asyncio.current_task():
            anterior.cancel()  # o cliente escreveu de novo: recomeça a espera
        self._tarefas[chat_id] = asyncio.create_task(self._ciclo(chat_id))

    async def _dormir(self, segundos):
        await asyncio.sleep(segundos * self.cfg.escala_tempo)

    async def _ciclo(self, chat_id):
        await self._dormir(self.cfg.janela_silencio)  # cancelado se chegar mensagem nova

        mensagens = self._pendentes.pop(chat_id, [])
        if not mensagens:
            return
        self._respondendo.add(chat_id)
        try:
            resposta = await _chamar(self._gerar, mensagens)
            await self._entregar(chat_id, resposta or '')
        except Exception as e:  # um erro numa conversa não derruba o bot
            print(f"⚠️ Erro ao responder o chat {chat_id}: {e}", file=sys.stderr)
        finally:
            self._respondendo.discard(chat_id)

        if self._pendentes.get(chat_id):  # chegou mensagem enquanto respondia
            self._agendar(chat_id)

    async def _entregar(self, chat_id, resposta):
        for i, balao in enumerate(dividir_em_baloes(resposta, self.cfg)):
            if i:
                await self._dormir(self._rng.uniform(*self.cfg.pausa_entre_baloes))
            atraso = calcular_atraso(balao, self.cfg, self._rng, primeiro_balao=(i == 0))
            await self._digitar_por(chat_id, atraso)
            await _chamar(self._enviar, chat_id, balao)

    async def _digitar_por(self, chat_id, segundos):
        """Técnica 2 - mantém o "digitando..." aceso durante toda a espera."""
        restante = segundos
        while True:
            await _chamar(self._digitando, chat_id)
            passo = min(self.cfg.renovar_digitando, restante)
            await self._dormir(passo)
            restante -= passo
            if restante <= 0:
                break
