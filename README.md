# 💬 Bot com ritmo humano (Telegram)

Um bot que conversa no **ritmo de uma pessoa**: espera você terminar de escrever, mostra
"digitando...", responde em mensagens curtas e leva o tempo de quem está digitando.

Em **Python puro**: sem nenhuma biblioteca para instalar. Tem um **simulador no terminal**, para
testar sem token e sem Telegram.

```
[  0.0s] 👤 oi
[  0.0s] 👤 vcs entregam?
[  0.0s] 👤 qual o horário e quanto custa?
[  2.1s] ✍️  bot está digitando...
[  4.3s] 🤖 Oi! Tudo bem? 😊
              Funcionamos de terça a domingo, das 9h às 19h.
[  4.9s] ✍️  bot está digitando...
[  6.1s] 🤖 Os bolos começam em R$ 45 e os docinhos em R$ 1,80 a unidade. Quer que eu te mande o cardápio completo?
[  6.5s] ✍️  bot está digitando...
[  7.4s] 🤖 Entregamos em toda a cidade. O frete é calculado pelo bairro.
```
*(saída real do simulador no modo `--rapido`: três mensagens do cliente, uma resposta só, em três balões)*

## As 4 técnicas

| Técnica | O problema que resolve | Como está implementada |
|---|---|---|
| **1. Atraso inteligente** | Uma resposta instantânea "denuncia" o robô e soa fria | 2 a 5 s antes do primeiro balão; em textos longos, 1 a 2 s **por linha**, com limite de 8 s |
| **2. "Digitando..."** | Durante a espera, o cliente acha que ninguém está lá | O sinal fica ativo durante toda a espera e é **renovado a cada 4 s** (o Telegram o apaga depois de ~5 s) |
| **3. Quebra de mensagens** | Um "textão" cansa e é pouco lido no celular | Divide por parágrafo (ou por frase, se for um bloco só) em **até 3 balões**, com 1 a 2 s entre eles |
| **4. Reset na interrupção** | O bot responde a primeira pergunta enquanto o cliente ainda digita a segunda | Cada mensagem nova **reinicia a contagem** de 6 s de silêncio; depois o bot responde **tudo junto** |

Detalhes que costumam faltar em bots prontos:
- Uma mensagem que chega **enquanto o bot está respondendo** não se perde: entra na próxima rodada.
- Cada conversa tem a sua própria contagem: clientes diferentes não se misturam.
- Um erro numa resposta não derruba o bot.

## Como usar

### Simulador (sem Telegram)
```bash
python simulador.py            # tempo real
python simulador.py --rapido   # 3x mais rápido
python simulador.py --demo     # um cliente simulado conversa sozinho (só assistir)
```
Mande duas ou três mensagens seguidas e veja o bot esperar você terminar.

### Telegram
1. Crie um bot com o [@BotFather](https://t.me/BotFather) e copie o token.
2. Copie `.env.exemplo` para `.env` e cole o token.
3. Rode:
   ```bash
   python bot_telegram.py
   ```

### Testes
```bash
python -m unittest -v
```
São 21 testes, que cobrem os tempos, a divisão em balões, a espera que reinicia, o "digitando" antes de
cada balão, mensagens que chegam no meio da resposta e as respostas de exemplo.

## Ligar em uma IA ou em outra plataforma

O núcleo (`humanizador.py`) não depende do Telegram. Ele só precisa de três funções:

```python
from humanizador import Atendente

bot = Atendente(
    gerar_resposta=minha_ia,      # recebe a lista de mensagens, devolve o texto
    enviar=enviar_mensagem,       # (chat_id, texto)
    digitando=mostrar_digitando,  # (chat_id)
)
await bot.receber(chat_id, texto)  # chame a cada mensagem que chegar
```

- **IA (ChatGPT, Gemini, Claude...):** troque `respostas.gerar_resposta` por uma função que chame a API.
  Peça para a IA separar as ideias em parágrafos: cada parágrafo vira um balão.
- **WhatsApp (Evolution API, Z-API...):** `digitando` envia a presença "composing", e `enviar`
  manda a mensagem de texto.

Todos os tempos ficam em `Config` (`humanizador.py`) e podem ser ajustados.

## Transparência
Ritmo humano é para deixar a conversa agradável, **não para enganar**. O bot de exemplo diz que é
um assistente automático quando perguntam ("você é um robô?") e oferece falar com uma pessoa.
As regras do WhatsApp Business também exigem isso.

## Estrutura
```
humanizador.py   # as 4 técnicas (independente de plataforma)
respostas.py     # respostas de exemplo de uma confeitaria fictícia
simulador.py     # conversa no terminal
bot_telegram.py  # bot real (Bot API do Telegram, só com a biblioteca padrão)
tests/           # testes automáticos
```

## Licença
MIT — veja [LICENSE](LICENSE).
