# Robô de prospecção: saquinho preto para lojas de Nova Serrana na Shopee

O robô faz duas coisas:

1. **`buscar_lojas.py`**: pesquisa produtos na Shopee (filtrando Minas Gerais) e salva as lojas em `lojas_encontradas.csv`. A Shopee só mostra o **estado** da loja, então cada loja recebe uma classificação:
   - **confirmada**: o nome, a descrição ou algum produto da loja menciona "Nova Serrana";
   - **provável**: loja de calçados de MG que não menciona a cidade. Recebe a `MENSAGEM_PROVAVEL`, que não afirma que a loja é de Nova Serrana. Para mandar só para as confirmadas, use `SOMENTE_CONFIRMADAS = True` no `config.py`.
2. **`enviar_mensagens.py`**: abre o chat de cada loja, envia a mensagem oferecendo o saquinho preto e anexa a **tabela de preços** (o arquivo mais recente da pasta configurada).

Ele usa o seu próprio Chrome, logado na **sua** conta da Shopee.

## Instalação (uma vez)

1. Instale o [Python 3.10+](https://www.python.org/downloads/) e marque **"Add Python to PATH"**.
2. Abra o terminal (Prompt de Comando) dentro desta pasta e rode:
   ```
   pip install -r requirements.txt
   python -m playwright install chromium
   ```

## Configuração

Abra o arquivo **`config.py`** e ajuste:

- `PASTA_TABELA`: a pasta onde fica a tabela de preços. O padrão é a pasta `Tabela Saquinhos` dentro de **Documentos**.
  ⚠️ O chat da Shopee **só aceita imagem**. Se a tabela estiver em Excel ou PDF, salve uma cópia em **JPG/PNG** nessa pasta.
- `MENSAGEM`: o texto enviado (`{loja}` é trocado pelo nome da loja).
- `PALAVRAS_BUSCA`: o que será pesquisado para achar as lojas.
- `LIMITE_POR_DIA`, `ESPERA_MIN` e `ESPERA_MAX`: o ritmo dos envios.

## Uso

```
python buscar_lojas.py              # 1) encontra as lojas (pode rodar várias vezes; não duplica)
python enviar_mensagens.py --teste  # 2) mostra para quem vai mandar, sem enviar nada
python enviar_mensagens.py          # 3) envia de verdade
```

Na primeira vez o navegador abre a Shopee: **faça login**, volte ao terminal e aperte ENTER. O login fica salvo na pasta `perfil_navegador/`.

O envio é automático: ele manda para as lojas da lista, respeitando o limite diário, sem perguntar nada.
Para revisar loja por loja, use `python enviar_mensagens.py --revisar`
(`s` envia · `n` pula · `x` nunca mais contatar essa loja · `q` sai).

## Rodar sozinho todo dia

O arquivo **`rodar_robo.bat`** faz tudo em sequência: busca lojas novas e envia as mensagens do dia. Dá para dar dois cliques nele ou agendar no Windows:

1. Aperte a tecla Windows, digite **Agendador de Tarefas** e abra.
2. Clique em **Criar Tarefa Básica...**, dê o nome **Robô Shopee** e clique em Avançar.
3. Escolha **Diariamente**, defina o horário (por exemplo, 09:00) e clique em Avançar.
4. Escolha **Iniciar um programa**, clique em **Procurar...**, selecione o `rodar_robo.bat` e clique em Avançar.
5. Clique em **Concluir**.

O computador precisa estar ligado e com o Windows desbloqueado nesse horário. Se a Shopee pedir login ou captcha de novo, o robô fica esperando até alguém resolver na janela do navegador.

## Vários perfis / várias contas

Cada perfil é um Chrome separado, com o seu próprio login da Shopee:

```
python enviar_mensagens.py --perfil loja1
python enviar_mensagens.py --perfil loja2
```

Na primeira vez que usar um perfil novo, faça login com a conta dele. O login fica salvo em `perfil_navegador/<nome>/`.
O histórico (`mensagens_enviadas.csv`) é **o mesmo para todos os perfis**: uma loja que já recebeu de um perfil não recebe de novo de outro. O limite diário é contado **separado para cada perfil**.
Os perfis do robô são independentes do seu Chrome do dia a dia e não precisam do Claude: o script roda sozinho, no seu computador.

## Arquivos gerados

| Arquivo | O que é |
|---|---|
| `lojas_encontradas.csv` | lojas de Nova Serrana encontradas (abre no Excel) |
| `mensagens_enviadas.csv` | histórico de envios; quem já recebeu não recebe de novo |
| `nao_contatar.txt` | lojas que não devem ser contatadas (uma por linha: shopid ou usuário) |
| `erros/` | print da tela quando algum envio falha |

## Cuidados importantes

- **Regras da Shopee:** mandar mensagem automática e não solicitada pode ser considerado spam pela Shopee, e ela pode **restringir ou banir a conta**. Por isso o robô já vem com limite diário baixo (15), esperas longas e confirmação manual. Se possível, use uma conta de comprador separada da sua conta de vendedor principal.
- **Várias contas:** a Shopee identifica contas usadas no mesmo computador/internet. Se ela entender como spam, pode punir **todas as contas juntas**. Use só contas que são suas e não aumente os limites.
- **Contato externo:** a Shopee costuma bloquear ou esconder telefone, WhatsApp e links no chat. Escreva o seu contato **dentro da imagem da tabela**.
- Se alguém responder pedindo para não receber mais mensagens, coloque a loja no `nao_contatar.txt`.
- **Mudanças no site:** a Shopee muda o layout com frequência. Se o robô parar de achar o botão de chat ou a caixa de texto, veja o print em `erros/` e ajuste os seletores no topo do `enviar_mensagens.py` (`BOTOES_CHAT`, `CAIXA_TEXTO`).
- Se o filtro de estado deixar a busca vazia, coloque `FILTRO_ESTADO = ""` no `config.py`.
