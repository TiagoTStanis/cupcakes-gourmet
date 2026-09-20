# Plano de Testes e Qualidade de Software

Este documento formaliza o planejamento e os procedimentos de teste de software do sistema **Cupcakes Gourmet** para a disciplina de PITE II. Ele abrange a estratégia de verificação e validação, a catalogação da suíte completa de testes automatizados, a matriz de rastreabilidade de requisitos, o roteiro de testes com usuários reais e o modelo em branco do laudo de qualidade.

---

## 1. Estratégia de Verificação e Validação

Na disciplina de Engenharia de Software, aprendemos a distinção conceitual fundamental entre **verificação** e **validação**:

- **Verificação ("O sistema está sendo construído corretamente?")**: Processo estritamente técnico que analisa se os artefatos de software atendem com exatidão às especificações e regras de negócio documentadas. No Cupcakes Gourmet, a verificação é realizada por meio da execução automatizada da suíte de testes com `pytest-django`, checagens de validação em formulários e modelos, revisão de código e inspeção das rotas e respostas HTTP.
- **Validação ("O sistema correto está sendo construído?")**: Processo focado no usuário final que avalia se a solução atende às reais necessidades práticas dos clientes e da confeitaria artesanal. No Cupcakes Gourmet, a validação é conduzida por meio de testes supervisionados com 5 usuários reais de perfis variados (técnicos e leigos), operando tarefas práticas em dispositivos móveis ou navegadores e registrando a experiência em um formulário e laudo de qualidade.

---

## 2. Testes Automatizados

Para garantir a confiabilidade do código e a regressão contínua durante as fases de desenvolvimento, implementei testes automatizados cobrindo todas as camadas da aplicação (modelos, serviços, formulários, views e templates).

### 2.1. Como Executar a Suíte

Com o ambiente virtual ativado na raiz do projeto, execute o comando:

```bash
python -m pytest
```

Para obter a listagem detalhada de cada função e parâmetro testado:

```bash
python -m pytest -v
```

Caso queira executar apenas um módulo específico:

```bash
python -m pytest tests/test_usuarios.py
```

### 2.2. Distribuição dos Testes por Área

A suíte completa conta com **156 funções de teste reais (`def test_`)**, totalizando 192 casos de execução graças às parametrizações com `@pytest.mark.parametrize`. A tabela a seguir detalha a quantidade exata de testes por arquivo e as regras cobertas:

Os testes automatizados exercitam as regras de negócio, os serviços e as views, usando o cliente de teste do Django e conferindo o HTML devolvido. O comportamento do JavaScript (busca com debounce, máscaras, contadores) e a aparência no celular não são cobertos por testes automáticos: foram conferidos à mão por mim e vão ser avaliados pelas pessoas que testarem o sistema.

| Área | Arquivo | Qtd. `def test_` | O que cobre | Exemplos de Testes Reais |
|---|---|:---:|---|---|
| **Usuários e Contas** | `tests/test_usuarios.py` | 14 | Validação de senha forte (mínimo 8 caracteres, maiúscula e número), bloqueio de 15 minutos após 3 falhas consecutivas, ativação por token, recuperação de senha com validade de 60 minutos, uso único de token e segurança de endereços no perfil. | `test_rejeita_senha_fora_dos_requisitos`<br>`test_bloqueia_tres_erros_por_exatos_quinze_minutos`<br>`test_token_expira_exatamente_em_sessenta_minutos`<br>`test_fluxo_cadastro_ativacao_login_e_logout` |
| **Catálogo e Busca** | `tests/test_catalogo.py` | 18 | Ocultação de produtos via *soft delete*, busca insensível a maiúsculas e acentos (ex: "limao" encontra "Limão Siciliano"), ordenação por popularidade e preço, filtro por categorias, banner amarelo de alergênicos, bloqueio de compra para estoque zero e validação de imagens (JPG/PNG até 5 MB). | `test_soft_delete_oculta_da_listagem_e_mantem_no_banco`<br>`test_busca_por_limao_encontra_cupcake_com_e_sem_acento_e_caixa_alta`<br>`test_ordenacao_do_catalogo_por_total_vendas_padrao`<br>`test_botao_compra_desabilitado_quando_estoque_zerado` |
| **Carrinho de Compras** | `tests/test_carrinho.py` | 10 | Persistência do carrinho associado à conta do cliente, expiração e renovação em 24h, bloqueio da 11ª unidade do mesmo item, trava contra adição superior ao estoque cadastrado, operações assíncronas via JSON (+, -, remover) e redirecionamento de visitantes com mensagem contextual. | `test_bloqueio_da_11a_unidade_ao_adicionar_ao_carrinho`<br>`test_bloqueio_de_quantidade_acima_do_estoque_disponivel`<br>`test_carrinho_expira_e_zera_itens_apos_24_horas`<br>`test_endpoint_json_adicionar_alterar_e_remover_devolve_totais` |
| **Frete e Cupons** | `tests/test_frete_cupom.py` | 16 | Consulta e autocompletar de CEP via mock da API do ViaCEP, cálculo de frete por UF, frete grátis estritamente para subtotal após cupom superior a R$ 150,00 (testando 150,00 e 150,01), cupons percentuais e fixos, valor mínimo de pedido e bloqueio de reuso pelo mesmo usuário. | `test_frete_gratis_em_150_01_e_nao_em_150_00`<br>`test_frete_gratis_considera_subtotal_apos_cupom`<br>`test_cupom_reutilizado_pelo_mesmo_usuario_e_permitido_para_outro`<br>`test_desconto_nao_incide_no_frete` |
| **Checkout e Estoque** | `tests/test_estoque_checkout.py` | 18 | Reserva temporária de 10 minutos criada ao entrar no checkout, liberação automática de reservas expiradas, dedução de estoque disponível para outros usuários, baixa definitiva protegida contra duplicidade, tratamento de itens esgotados e bloqueio de pulo de etapas do checkout. | `test_reserva_reduz_disponivel_para_outro_usuario`<br>`test_reserva_expirada_libera_unidades`<br>`test_dar_baixa_e_idempotente_e_consome_reservas`<br>`test_resumo_confere_total_com_cupom_e_frete` |
| **Pagamento e Pedido** | `tests/test_pagamento_pedido.py` | 18 | Validação de cartão pelo algoritmo de Luhn, cálculo de parcelas de 1x a 12x com juros compostos de 2,5% a.m. a partir da 4ª parcela, liberação de estoque em cartão recusado, payload SVG de QR Code fictício, reserva de 30 minutos no PIX e cancelamento por expiração. | `test_luhn_confere_numero_do_cartao`<br>`test_cinco_parcelas_aplicam_juros_compostos_exatos`<br>`test_cartao_recusado_libera_reserva_e_preserva_carrinho_e_estoque`<br>`test_pix_reserva_por_trinta_minutos_sem_baixar_estoque` |
| **Status e Notificações** | `tests/test_status_notificacoes.py` | 15 | Transições válidas do ciclo de vida do pedido (`AGUARDANDO_PAGAMENTO` até `ENTREGUE`), gravação de data/hora no `HistoricoStatus`, geração de registros em `Notificacao`, contagem de mensagens não lidas no sino do cabeçalho e exibição da linha do tempo com prazo estimado de entrega. | `test_transicoes_validas_gravam_historico_e_notificacoes`<br>`test_transicao_invalida_preserva_status_estoque_e_avisos`<br>`test_sino_conta_apenas_nao_lidas_do_dono_e_zero_para_visitante`<br>`test_rastreamento_mostra_etapas_horarios_e_prazo_da_uf` |
| **Histórico de Pedidos** | `tests/test_historico.py` | 14 | Paginação do histórico em blocos de 10 pedidos, ordenação do mais recente para o mais antigo, bloqueio de acesso a pedidos alheios e funcionalidade "Repetir Pedido" (com validação de estoque atual, limite de 10 unidades e produtos desativados). | `test_historico_lista_apenas_pedidos_do_proprio_usuario`<br>`test_historico_paginacao_com_dez_por_pagina`<br>`test_repetir_pedido_adiciona_itens_ao_carrinho`<br>`test_repetir_pedido_respeita_estoque_disponivel_e_informa_falta` |
| **Painel Administrativo** | `tests/test_painel.py` | 18 | Restrição de acesso ao painel (`/painel/`) para usuários `is_staff`, CRUD de cupcakes com upload seguro via Pillow, gestão de categorias, filtros de pedidos por status/cliente/período e cancelamento com reposição de estoque permitido apenas para pedidos não despachados. | `test_cliente_comum_recebe_403_em_todas_as_rotas_do_painel`<br>`test_criar_produto_valido_aparece_na_vitrine_imediatamente`<br>`test_desativar_mantem_no_banco_some_da_vitrine_mas_permanece_em_pedidos_antigos`<br>`test_cancelar_em_saiu_para_entrega_e_entregue_e_bloqueado` |
| **Erros e Carga de Dados** | `tests/test_erros_dados.py` | 8 | Renderização das telas de erro customizadas (404, 500 sem dependência do banco, tela de fallback offline), comando de carga `popular_dados` (criação idempotente de 12 cupcakes com imagens reais, categorias, fretes, cupom ativo e credenciais de teste). | `test_pagina_404_renderiza_template_com_status_404`<br>`test_pagina_500_renderiza_template_sem_depender_do_banco`<br>`test_popular_dados_cria_doze_produtos_com_imagem_no_disco`<br>`test_popular_dados_executado_duas_vezes_nao_duplica_registros` |
| **Regressões** | `tests/test_regressoes.py` | 9 | Testes de regressão de problemas achados na revisão do código: preço zero ou negativo, senha do administrador informada ou gerada, PIX vencido cancelado ao listar, erro de estoque no painel e escape de HTML na busca. | `test_preco_zero_ou_negativo_e_rejeitado`<br>`test_pix_vencido_e_cancelado_ao_listar`<br>`test_historico_mostra_pix_vencido_como_cancelado`<br>`test_busca_js_escapa_o_texto_antes_de_inserir_no_html` |
| **TOTAL GERAL** | **11 Arquivos** | **156** | **Cobertura completa de todos os domínios do sistema.** | |

---

## 3. Matriz de Rastreabilidade (História x Critério x Teste Automatizado x Conferência Manual)

| História | Critério de Aceitação Principal | Teste Automatizado | Como Conferir Manualmente |
|---|---|---|---|
| **US01**: Cadastrar-se | Senha com mínimo de 8 caracteres, maiúscula e número; ativação por link. | `tests/test_usuarios.py` (`test_rejeita_senha_fora_dos_requisitos`, `test_fluxo_cadastro_ativacao_login_e_logout`) | Acessar `/usuarios/cadastro/`, preencher formulário, verificar medidor de força da senha e clicar no link exibido no alerta azul de demonstração. |
| **US02**: Entrar na conta | Bloqueio de 15 minutos após 3 falhas consecutivas de senha; mensagem genérica de erro. | `tests/test_usuarios.py` (`test_bloqueia_tres_erros_por_exatos_quinze_minutos`, `test_erro_login_generico`) | Errar a senha 3 vezes seguidas em `/usuarios/login/` e verificar se a conta fica bloqueada mesmo informando a senha correta na 4ª tentativa. |
| **US03**: Recuperar acesso | Token com uso único e validade estrita de 60 minutos; resposta genérica. | `tests/test_usuarios.py` (`test_token_expira_exatamente_em_sessenta_minutos`, `test_recuperacao_uso_unico_e_hash_no_banco`) | Solicitar recuperação em `/usuarios/esqueci-senha/`, abrir o link do alerta azul, cadastrar nova senha e tentar reutilizar o mesmo link (deve acusar inválido). |
| **US04**: Ver o catálogo | Acesso livre a visitantes e clientes; listagem apenas de produtos com `ativo=True`. | `tests/test_catalogo.py` (`test_vitrine_sem_produtos_mostra_mensagem_padrao`, `test_soft_delete_oculta_da_listagem_e_mantem_no_banco`) | Acessar `/` sem estar autenticado e verificar se os 12 cupcakes com fotos, nomes e preços aparecem organizados. |
| **US05**: Filtrar por categoria | Filtragem dos cupcakes pelas categorias do banco de dados (Clássicos, Veganos, Temáticos). | `tests/test_catalogo.py` (`test_filtro_por_categoria`, `test_categoria_sem_produtos_mostra_aviso_especifico`) | Na tela inicial, clicar na pílula "Veganos" e verificar se apenas os doces daquela categoria permanecem na tela. |
| **US06**: Buscar pelo nome | Pesquisa com debounce de 300 ms, insensível a maiúsculas e sem distinção de acentos. | `tests/test_catalogo.py` (`test_busca_por_limao_encontra_cupcake_com_e_sem_acento_e_caixa_alta`, `test_endpoint_api_busca_retorna_json_correto`) | Acessar a aba Busca na barra inferior e digitar "limao" ou "LIMAO": o Cupcake de Limão Siciliano deve ser listado imediatamente. |
| **US07**: Ver detalhes | Exibição de ingredientes completos, alerta de alergênicos e botão desabilitado se estoque zerar. | `tests/test_catalogo.py` (`test_detalhes_exibe_ingredientes_e_banner_alergenicos`, `test_botao_compra_desabilitado_quando_estoque_zerado`) | Abrir qualquer cupcake e checar o banner amarelo de alergênicos. No painel admin, zerar o estoque de um item e verificar se o botão vira "Indisponível". |
| **US08**: Adicionar ao carrinho | Limite de 10 unidades por item, bloqueio acima do estoque físico e expiração após 24h. | `tests/test_carrinho.py` (`test_bloqueio_da_11a_unidade_ao_adicionar_ao_carrinho`, `test_bloqueio_de_quantidade_acima_do_estoque_disponivel`) | Tentar adicionar mais de 10 unidades de um cupcake no carrinho e conferir a mensagem de bloqueio. Atualizar quantidades pelos botões + e -. |
| **US09**: Gerenciar itens do carrinho | Aumentar, diminuir e remover itens com o total recalculado sem recarregar a página; quantidade zero remove o item. | `tests/test_carrinho.py` (`test_remocao_de_item_ao_alterar_quantidade_para_zero`, `test_endpoint_json_adicionar_alterar_e_remover_devolve_totais`) | No carrinho, tocar em + e em - e conferir subtotal e total mudando na hora; remover um item e ver o estado vazio. |
| **US10**: Calcular o frete | Consulta de CEP via ViaCEP, frete por UF e isenção (R$ 0,00) se subtotal líquido > R$ 150,00. | `tests/test_frete_cupom.py` (`test_frete_gratis_em_150_01_e_nao_em_150_00`, `test_views_consultar_cep_com_mock_viacep_e_sessao`) | Digitar o CEP `85884-000` no carrinho e verificar preenchimento automático. Montar pedido de R$ 150,50 e verificar se o frete fica como "Grátis". |
| **US11**: Finalizar o pedido | Fluxo móvel em 3 etapas (Endereço, Pagamento, Resumo) com reserva de estoque de 10 minutos. | `tests/test_estoque_checkout.py` (`test_reserva_reduz_disponivel_para_outro_usuario`, `test_etapas_nao_aceitam_pular_endereco_ou_pagamento`) | Clicar em "Finalizar Compra", selecionar endereço cadastrado ou cadastrar novo, escolher forma de pagamento e conferir a barra de progresso em 3 passos. |
| **US12**: Pagar com cartão | Validação de Luhn, CVV e validade futura; opções de 1x a 12x com juros compostos a partir de 4x. | `tests/test_pagamento_pedido.py` (`test_luhn_confere_numero_do_cartao`, `test_cinco_parcelas_aplicam_juros_compostos_exatos`) | Preencher o cartão `4111 1111 1111 1111`, selecionar 5x e verificar o cálculo das parcelas. Testar o cartão `4000 0000 0000 0002` para simular recusa. |
| **US13**: Pagar com PIX | Geração de payload com 30 min de validade, QR Code SVG fictício e botão para confirmar simulação. | `tests/test_pagamento_pedido.py` (`test_pix_reserva_por_trinta_minutos_sem_baixar_estoque`, `test_qr_ficticio_e_svg_deterministico`) | Escolher PIX no checkout. Na tela do pedido, visualizar o QR Code e temporizador regressivo; clicar em "Confirmar Pagamento (Simulação)". |
| **US14**: Usar cupom | Aplicação de cupom percentual ou fixo com valor mínimo e bloqueio de reuso pelo mesmo usuário. | `tests/test_frete_cupom.py` (`test_cupom_reutilizado_pelo_mesmo_usuario_e_permitido_para_outro`, `test_views_aplicar_e_remover_cupom`) | No carrinho com mais de R$ 30,00, aplicar `CUPCAKE10`. Finalizar o pedido e tentar usar o mesmo cupom em uma segunda compra (deve ser rejeitado). |
| **US15**: Acompanhar o status do pedido | Rastreamento do pedido com data e hora reais de cada transição de status. Avisos gravados a cada mudança de status, com contador visual de não lidas no cabeçalho. | `tests/test_status_notificacoes.py` (`test_transicoes_validas_gravam_historico_e_notificacoes`, `test_rastreamento_mostra_etapas_horarios_e_prazo_da_uf`) | Acessar `/pedidos/pedido/<numero>/` e conferir a marcação do passo atual e o histórico com data/hora em que o pagamento foi registrado. No painel admin, avançar o status do pedido para "Em preparação". No cliente, checar o sino de notificações no topo e abrir `/pedidos/notificacoes/`. |
| **US16**: Histórico e repetir pedido | Listagem paginada de compras anteriores e botão "Repetir Pedido" com checagem de estoque. | `tests/test_historico.py` (`test_historico_paginacao_com_dez_por_pagina`, `test_repetir_pedido_adiciona_itens_ao_carrinho`) | Acessar a aba Pedidos (`/pedidos/`), visualizar os cartões com totais e status e clicar em "Repetir pedido", conferindo se os itens voltam ao carrinho. |
| **US17**: Administrador: produtos | Restrito a `is_staff`; CRUD completo com exclusão lógica (*soft delete*) e validação Pillow de foto. | `tests/test_painel.py` (`test_cliente_comum_recebe_403_em_todas_as_rotas_do_painel`, `test_desativar_mantem_no_banco_some_da_vitrine_mas_permanece_em_pedidos_antigos`) | Entrar com `admin@cupcakesgourmet.com`, acessar `/painel/produtos/`, cadastrar um novo sabor com foto e depois desativá-lo, checando que sumiu da vitrine. |
| **US18**: Administrador: pedidos | Filtros por status, data e cliente; cancelamento com reposição de estoque em aberto/preparo. | `tests/test_painel.py` (`test_filtros_pedidos_por_status_periodo_e_cliente`, `test_cancelar_em_aguardando_pagamento_e_em_preparacao_repoe_estoque_uma_unica_vez`) | No painel, abrir `/painel/pedidos/`, filtrar por status e cancelar um pedido em preparação, conferindo se o estoque dos cupcakes daquele pedido foi recomposto. |

---

## 4. Roteiro dos Testes com Usuários

O teste com usuários visa validar a usabilidade, clareza visual e conforto da experiência de navegação e compra na aplicação.

### 4.1. Perfil dos Participantes
Planejei o teste com **5 pessoas reais**, compondo um perfil misto:
- **Participantes 1 e 2 (Perfil Técnico)**: estudantes de tecnologia ou desenvolvedores habituados a sistemas web, focados em identificar consistência de fluxos, clareza de mensagens de erro e comportamento responsivo;
- **Participantes 3, 4 e 5 (Perfil Leigo)**: consumidores habituais de confeitarias ou usuários comuns de smartphones, focados na facilidade de localização dos produtos, clareza do checkout e compreensão das etapas de pagamento.

### 4.2. Dados de Teste Pré-Configurados
Para orientar a execução sem atritos, os participantes devem utilizar os seguintes dados:
- **Contas de Acesso**:
  - Cliente pré-cadastrado: `cliente@teste.com` / Senha: `Cliente@123456` (endereço pré-configurado: Rua das Flores, 123, Centro, Medianeira/PR - CEP 85884-000);
  - Administrador: `admin@cupcakesgourmet.com`, com a senha definida na carga de dados (informada só a quem for testar o painel).
- **CEP para Cálculo de Frete**: `85884-000` (Medianeira - PR).
- **Cupom de Desconto**: `CUPCAKE10` (10% de desconto em pedidos a partir de R$ 30,00).
- **Cartões de Crédito para Simulação**:
  - Cartão com Aprovação: `4111 1111 1111 1111` (Validade futura, ex: 12/2028; CVV de 3 dígitos);
  - Cartão com Recusa Proposital: `4000 0000 0000 0002`.

### 4.3. Lista de Tarefas do Testador
O aplicador do teste deve solicitar que cada usuário execute as tarefas a seguir em sequência, sem interferência direta:

1. **Tarefa 1 - Cadastro e Ativação**: Criar uma nova conta com e-mail próprio e senha forte. Ativar a conta através do link exibido no alerta azul de demonstração e efetuar login.
2. **Tarefa 2 - Exploração do Catálogo**: Navegar pela vitrine móvel, utilizar a aba Busca para localizar "limão" e abrir os detalhes de um cupcake para inspecionar ingredientes e alerta de alergênicos.
3. **Tarefa 3 - Operações no Carrinho**: Adicionar 2 unidades de dois sabores diferentes ao carrinho. Alterar a quantidade de um deles pelos botões + e -. Tentar elevar um sabor para mais de 10 unidades para observar o tratamento da regra.
4. **Tarefa 4 - Cálculo de Frete e Cupom**: Inserir o CEP `85884-000` para conferir o preenchimento automático do endereço. Aplicar o cupom `CUPCAKE10` e verificar a atualização do valor de desconto no resumo.
5. **Tarefa 5 - Finalização de Compra (Checkout)**: Avançar para o checkout em 3 etapas. Selecionar o endereço, optar por Cartão de Crédito e testar a compra com o cartão simulado aprovado.
6. **Tarefa 6 - Acompanhamento e Simulação PIX**: Acessar o histórico de pedidos na barra inferior, visualizar o rastreamento com horários, consultar as notificações no ícone de sino e testar o botão "Repetir Pedido".

### 4.4. Critérios de Registro de Bugs e Inconsistências
Caso o participante encontre comportamentos anômalos ou dificuldades de uso, a ocorrência deve ser anotada seguindo a classificação:
- **Crítico**: impede a continuidade do fluxo (ex: erro 500, impossibilidade de finalizar compra);
- **Alto**: quebra uma regra de negócio importante sem travar o sistema (ex: desconto calculado incorretamente);
- **Médio**: inconsistência visual ou de mensagem que confunde o usuário mas permite prosseguir;
- **Baixo**: detalhe cosmético, alinhamento ou sugestão de melhoria ergonômica.

---

## 5. Modelo do Laudo de Qualidade (Em Branco)

Abaixo está o modelo formal em branco a ser preenchido após a aplicação prática das sessões de teste com os 5 participantes. Os campos estão identificados como `[preencher]` para garantir a fidedignidade da coleta de dados.

```markdown
# Laudo de Avaliação de Qualidade de Software

## 1. Identificação do Sistema
- Sistema: Cupcakes Gourmet
- Versão: 1.0 (PITE II)
- Disciplina: Projeto Integrador Transdisciplinar em Engenharia de Software II
- Instituição: Universidade Cruzeiro do Sul
- Data da Avaliação: [preencher]
- Responsável Técnico: [preencher]

## 2. Ambiente de Avaliação
- Dispositivos Utilizados: [preencher - ex: Smartphone Android Samsung A52, iPhone 13, Notebook Chrome]
- Resoluções de Tela Testadas: [preencher - ex: 390x844, 412x915, 1920x1080]
- Navegadores: [preencher - ex: Google Chrome Mobile 120, Safari iOS 17, Mozilla Firefox 122]
- Conexão: [preencher - ex: Wi-Fi doméstico 100 Mbps, 4G móvel]

## 3. Método Aplicado
- Descrição: Sessão presencial/remota supervisionada baseada em execução de tarefas orientadas (Roteiro da Seção 4). Os usuários operaram a aplicação de forma independente, registrando impressões sobre facilidade de uso, legibilidade e estabilidade.

## 4. Participantes dos Testes
| ID | Nome do Avaliador | Perfil (Técnico / Leigo) | Data | Tempo Total da Sessão |
|:---:|---|---|:---:|:---:|
| U01 | [preencher] | Técnico | [preencher] | [preencher] |
| U02 | [preencher] | Técnico | [preencher] | [preencher] |
| U03 | [preencher] | Leigo | [preencher] | [preencher] |
| U04 | [preencher] | Leigo | [preencher] | [preencher] |
| U05 | [preencher] | Leigo | [preencher] | [preencher] |

## 5. Ocorrências e Defeitos Identificados
| ID | Descrição do Defeito / Dificuldade | Gravidade (Crítica/Alta/Média/Baixa) | Evidência / Passo a Passo | Correção Aplicada / Recomendada | Status (Aberto/Corrigido) |
|:---:|---|---|---|---|:---:|
| D01 | [preencher] | [preencher] | [preencher] | [preencher] | [preencher] |
| D02 | [preencher] | [preencher] | [preencher] | [preencher] | [preencher] |
| D03 | [preencher] | [preencher] | [preencher] | [preencher] | [preencher] |

## 6. Funcionalidades Não Testadas pelos Usuários
- [preencher - listar módulos que ficaram restritos a testes automatizados ou que não fizeram parte do escopo dos usuários, como painel administrativo restrito]

## 7. Resumo dos Testes Automatizados
- Framework: pytest com pytest-django
- Total de Funções de Teste (`def test_`): 156
- Total de Casos Executados (com parametrização): 192
- Status da Suíte Automatizada: [preencher - ex: 192 aprovados em X segundos]

## 8. Lições Aprendidas e Observações de Usabilidade
- [preencher com apontamentos qualitativos observados durante a interação dos participantes]

## 9. Conclusão e Parecer de Qualidade
- Parecer Final: [preencher - Apto / Necessita de Ajustes / Homologado]
- Data: [preencher]
- Assinatura do Aluno / Responsável: [preencher]
```
