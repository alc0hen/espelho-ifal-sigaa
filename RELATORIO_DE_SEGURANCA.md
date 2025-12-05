# Relatório de Análise de Segurança

Este documento detalha a análise de segurança realizada na aplicação **Boletim App**, identificando vulnerabilidades, configurações de risco e pontos positivos.

## Resumo Executivo

A aplicação apresenta uma estrutura de segurança baseada em Flask com boas práticas implementadas (CSRF, HttpOnly Cookies), mas possui uma **vulnerabilidade crítica** relacionada à exposição de chaves criptográficas e uma **vulnerabilidade de XSS** no frontend devido à manipulação insegura do DOM.

## 1. Vulnerabilidades Críticas

### 1.1. Chave Secreta Hardcoded (`SECRET_KEY`)
*   **Localização:** `app/__init__.py`
*   **Descrição:** A chave secreta usada para assinar cookies de sessão possui um valor padrão fixo no código: `'8f8914969a6246448a7eed278112ed862b73e5ac11f09943e2b20e6b470fa7f1'`.
*   **Risco:** Se a aplicação for implantada sem definir a variável de ambiente `SECRET_KEY`, um atacante que tenha acesso a este código (que é público/open source) pode forjar cookies de sessão. Isso permitiria a criação de sessões falsas ou a decodificação dos cookies do SIGAA armazenados na sessão do usuário (`session['sigaa_cookies']`), levando ao comprometimento total da conta do aluno.
*   **Recomendação:** Remover o valor padrão hardcoded ou alterá-lo para lançar um erro caso a variável de ambiente não esteja definida em produção.

## 2. Vulnerabilidades de Frontend (Client-Side)

### 2.1. Cross-Site Scripting (XSS) via `innerHTML`
*   **Localização:** `app/templates/dashboard.html` (Funções `renderList`, `handleStreamMessage`, etc.)
*   **Descrição:** O código JavaScript utiliza a propriedade `innerHTML` para renderizar dados recebidos da API (como nomes de disciplinas e observações).
    *   Exemplo: `<div class="subj-name">${item.name}</div>`
*   **Risco:** Se o sistema de origem (SIGAA) retornar dados contendo scripts maliciosos (e.g., um professor cadastra uma observação com `<script>...`), ou se houver uma interceptação na API, esse script será executado no navegador da vítima. Isso pode levar ao roubo de cookies ou redirecionamento de usuários.
*   **Recomendação:** Utilizar `textContent` para inserir texto puro ou usar bibliotecas de sanitização (como DOMPurify) antes de inserir HTML dinâmico.

## 3. Segurança de Backend e Configurações

### 3.1. Validação de Certificados e Cookies Inseguros
*   **Localização:** `app/sigaa_api/session.py`
*   **Descrição:** O uso de `aiohttp.CookieJar(unsafe=True)` é implementado.
*   **Análise:** O código comenta que isso é necessário para compatibilidade com o sistema legado do SIGAA (que provavelmente emite cookies fora do padrão RFC).
*   **Veredito:** **Risco Aceito**. Dado que o alvo é um sistema legado específico, essa configuração é muitas vezes mandatória para o funcionamento. Recomenda-se monitorar se o SIGAA atualizar seus padrões para remover essa flag no futuro.

### 3.2. Gerenciamento de Sessão
*   **Pontos Positivos:**
    *   `SESSION_COOKIE_HTTPONLY = True`: Impede acesso aos cookies via JavaScript.
    *   `SESSION_COOKIE_SAMESITE = 'Lax'`: Protege contra CSRF cross-origin.
    *   Proteção CSRF (`Flask-WTF`) está ativa e implementada no login.
*   **Armazenamento de Credenciais:** As credenciais (usuário/senha) não são persistidas no banco, o que é excelente. Apenas os cookies de sessão do SIGAA são mantidos na sessão do cliente.

### 3.3. Dependências
*   **Arquivo:** `requirements.txt`
*   **Observação:** As dependências não possuem versões fixas (ex: `Flask>=2.0.0` em vez de `Flask==2.0.1`).
*   **Risco:** Atualizações automáticas de pacotes podem introduzir "breaking changes" ou novas vulnerabilidades não testadas.
*   **Recomendação:** Utilizar "pinning" de versões exatas para garantir reprodutibilidade e estabilidade em produção.

## Recomendações de Correção Imediata

1.  **Remover a SECRET_KEY padrão** do código e obrigar o uso de variável de ambiente.
2.  **Sanitizar inputs no JavaScript** ao renderizar o dashboard, evitando o uso direto de template strings em `innerHTML` para dados variáveis.
