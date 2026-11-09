# -*- coding: utf-8 -*-
"""
Bot do Telegram com ritmo humano, usando só a biblioteca padrão do Python.

1. Crie um bot com o @BotFather e copie o token.
2. Copie .env.exemplo para .env e cole o token em TELEGRAM_BOT_TOKEN.
3. python bot_telegram.py
"""
import asyncio
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

from humanizador import Atendente
from respostas import gerar_resposta

for fluxo in (sys.stdout, sys.stderr):
    try:
        fluxo.reconfigure(encoding='utf-8', errors='replace')
    except AttributeError:
        pass


def carregar_env(arquivo=Path(__file__).with_name('.env')):
    """Lê um .env simples (CHAVE=valor) sem bibliotecas extras."""
    if arquivo.exists():
        for linha in arquivo.read_text(encoding='utf-8').splitlines():
            linha = linha.strip()
            if linha and not linha.startswith('#') and '=' in linha:
                chave, valor = linha.split('=', 1)
                os.environ.setdefault(chave.strip(), valor.strip().strip('"\''))


carregar_env()
TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '').strip()
if not TOKEN:
    raise SystemExit("❌ Defina TELEGRAM_BOT_TOKEN (veja o arquivo .env.exemplo).")

API = f"https://api.telegram.org/bot{TOKEN}/"


class ErroDeToken(Exception):
    pass


def chamar_api(metodo, **parametros):
    """Chama um método da Bot API do Telegram e devolve o 'result'."""
    dados = json.dumps(parametros).encode('utf-8')
    pedido = urllib.request.Request(API + metodo, dados, {'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(pedido, timeout=parametros.get('timeout', 0) + 15) as r:
            return json.load(r)['result']
    except urllib.error.HTTPError as e:
        if e.code in (401, 404):
            raise ErroDeToken("token inválido ou revogado") from None
        raise


async def api(metodo, **parametros):
    return await asyncio.to_thread(chamar_api, metodo, **parametros)


async def enviar(chat_id, texto):
    await api('sendMessage', chat_id=chat_id, text=texto)


async def digitando(chat_id):
    await api('sendChatAction', chat_id=chat_id, action='typing')


async def main():
    try:
        eu = await api('getMe')
    except ErroDeToken as e:
        raise SystemExit(f"❌ {e}. Confira o TELEGRAM_BOT_TOKEN ou gere um novo com o @BotFather.")
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise SystemExit(f"❌ Não consegui falar com o Telegram: {e}")
    print(f"✅ Bot @{eu['username']} no ar. Converse com ele no Telegram. (Ctrl+C encerra)")

    bot = Atendente(gerar_resposta, enviar, digitando)
    proximo = None
    while True:
        try:
            atualizacoes = await api('getUpdates', timeout=30, offset=proximo,
                                     allowed_updates=['message'])
        except ErroDeToken as e:
            raise SystemExit(f"❌ {e}. Gere um novo token com o @BotFather.")
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            print(f"⚠️ Sem conexão com o Telegram ({e}). Tentando de novo em 5 s...")
            await asyncio.sleep(5)
            continue

        for atualizacao in atualizacoes:
            proximo = atualizacao['update_id'] + 1
            mensagem = atualizacao.get('message') or {}
            if mensagem.get('text'):
                await bot.receber(mensagem['chat']['id'], mensagem['text'])


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Bot encerrado.")
