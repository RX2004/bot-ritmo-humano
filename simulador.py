# -*- coding: utf-8 -*-
"""
Simulador no terminal: teste o ritmo humano sem precisar de Telegram nem de token.

    python simulador.py              # tempo real
    python simulador.py --rapido     # 3x mais rápido
    python simulador.py --demo       # um cliente simulado conversa sozinho

Dica: mande duas ou três mensagens seguidas ("oi", "vcs entregam?", "quanto custa?")
e veja o bot esperar você terminar e responder tudo junto, em balões separados.
Digite "sair" para encerrar.
"""
import asyncio
import sys
import time

from humanizador import Atendente, Config
from respostas import gerar_resposta

for fluxo in (sys.stdout, sys.stderr):
    try:
        fluxo.reconfigure(encoding='utf-8', errors='replace')
    except AttributeError:
        pass
if not sys.stdin.isatty():  # entrada vinda de arquivo ou pipe: lê em UTF-8
    sys.stdin.reconfigure(encoding='utf-8', errors='replace')

CHAT = 'console'


class Tela:
    def __init__(self):
        self.inicio = time.monotonic()
        self.digitando_visivel = False

    def _hora(self):
        return f"[{time.monotonic() - self.inicio:5.1f}s]"

    def digitando(self, _chat):
        if not self.digitando_visivel:  # o bot renova o sinal; na tela basta mostrar uma vez
            print(f"{self._hora()} ✍️  bot está digitando...", flush=True)
            self.digitando_visivel = True

    def enviar(self, _chat, texto):
        self.digitando_visivel = False
        print(f"{self._hora()} 🤖 {texto}", flush=True)


# Conversa de demonstração: (segundos de pausa antes, mensagem do cliente)
DEMO = [
    (0.0, 'oi'),
    (2.0, 'vcs fazem bolo de aniversário?'),   # chega antes de 6 s: a espera reinicia
    (2.5, 'quanto custa?'),
    (16.0, 'entregam no centro?'),
    (13.0, 'você é um robô?'),
]


async def demonstracao(bot, tela):
    print("🎬 Modo demonstração: o cliente abaixo é simulado. Observe:")
    print("   • as 3 primeiras mensagens chegam seguidas → o bot espera e responde tudo junto")
    print("   • 'digitando...' antes de cada balão, e a resposta quebrada em balões curtos\n")
    for pausa, texto in DEMO:
        await bot._dormir(pausa)
        print(f"{tela._hora()} 👤 {texto}", flush=True)
        await bot.receber(CHAT, texto)
    await bot.concluir()


async def main():
    rapido = '--rapido' in sys.argv
    tela = Tela()
    bot = Atendente(gerar_resposta, tela.enviar, tela.digitando,
                    Config(escala_tempo=1 / 3 if rapido else 1.0))

    if '--demo' in sys.argv:
        await demonstracao(bot, tela)
        print("\n✅ Fim da demonstração. Rode sem --demo para conversar você mesmo.")
        return

    print("💬 Simulador do bot humanizado" + (" (3x mais rápido)" if rapido else ""))
    print("Escreva como no WhatsApp: pode mandar várias mensagens seguidas. 'sair' encerra.\n")

    while True:
        try:
            linha = await asyncio.to_thread(input)
        except EOFError:
            break
        if linha.strip().lower() == 'sair':
            break
        if linha.strip():
            print(f"{tela._hora()} 👤 {linha.strip()}", flush=True)
            await bot.receber(CHAT, linha.strip())

    await bot.concluir()  # termina de responder o que ficou pendente
    print("\n👋 Até mais!")


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Encerrado.")
