# Oracle Always Free A1 — criação e upgrade automáticos

Configuração preferida: **VM.Standard.A1.Flex**, **2 OCPUs**, **12 GB RAM**, **50 GB**, **Ubuntu 26.04 full ARM64**, **São Paulo**. Se faltar capacidade, tenta **1 OCPU e 6 GB RAM** como fallback, sem usar outro shape. Reutiliza a VCN e a sub-rede pública existentes e atribui IPv4 público.

## 1. Conta Oracle: criar uma chave de API NOVA

Na Oracle Cloud Console:

1. Perfil (ícone superior direito) → **My Profile** → **Token and keys** → **Add API Key**.
2. Escolha **Generate API Key Pair**, baixe a **private key** e adicione a public key à Oracle.
3. Copie os valores do arquivo de configuração exibido: `user`, `tenancy`, `fingerprint`, `region`. A região deve ser `sa-saopaulo-1`.
4. Guarde a chave privada da API com segurança. **Não confunda** com a chave SSH da instância! Não envie chaves privadas por chat, nem para o repositório.

## 2. Encontrar o OCID da sub-rede

**Networking → Virtual Cloud Networks → VCN existente → Subnets → sub-rede pública existente**. Copie o campo **OCID** dessa sub-rede (não é o OCID da VCN).

A chave SSH pública que você baixou durante a criação da VM anterior contém uma linha iniciando em `ssh-rsa` (ou `ssh-ed25519`). Ela será usada como segredo `OCI_SSH_PUBLIC_KEY`. **Nunca** coloque a chave SSH privada no GitHub.

## 3. Criar um repositório no GitHub

Crie um repositório chamado `oracle-a1-auto` (público recomendado para não consumir os minutos de repositórios privados). Adicione estes arquivos mantendo seus caminhos:

- `create_vm.py`
- `requirements.txt`
- `.github/workflows/oracle-a1.yml`
- `.gitignore`

Use Git/GitHub Desktop para subir os arquivos, pois o caminho `.github/workflows/` precisa ser preservado. Faça isso na branch principal (`main`). **Não adicione chave `.pem`, `.key` ou configurações da Oracle ao repositório.**

## 4. Configurar os seis Secrets no GitHub

Repositório → **Settings → Secrets and variables → Actions → New repository secret**.

| Nome do secret | Valor |
|---|---|
| `OCI_USER_OCID` | `user=` no arquivo de configuração da API |
| `OCI_TENANCY_OCID` | `tenancy=` no arquivo da API; como seu compartimento é root, é também o compartment OCID |
| `OCI_FINGERPRINT` | `fingerprint=` no arquivo da API |
| `OCI_PRIVATE_KEY` | Conteúdo COMPLETO da chave privada da **API** (`-----BEGIN PRIVATE KEY-----` até `-----END PRIVATE KEY-----`) |
| `OCI_SUBNET_OCID` | OCID da sub-rede **pública** existente |
| `OCI_SSH_PUBLIC_KEY` | Uma linha inteira do arquivo da chave SSH **pública** que você baixou na criação da instância |

**Importante:** Não escreva esses valores no código ou em mensagens públicas. GitHub Secrets não aparecem como texto no repositório.

## 5. Executar o primeiro teste

GitHub → **Actions → Oracle Free Tier A1 (upgrade hourly) → Run workflow**.

- `RESULTADO: created_primary`: a VM foi criada diretamente com 2/12; o agendamento se desativa.
- `RESULTADO: created_fallback`: a VM foi criada com 1/6; o cron horário continuará tentando ampliá-la.
- `RESULTADO: upgrade_unavailable`: ainda não houve capacidade para 2/12; a VM é religada e haverá nova tentativa.
- `RESULTADO: upgraded`: a instância atingiu 2/12; o agendamento se desativa.
- `RESULTADO: pending`: a instância estava em transição; a próxima execução tentará novamente.
- **Erro**: abra o log para corrigir credenciais, permissões ou imagem. Não é tratado como falta de capacidade.

Se a etapa de desativação falhar por permissão, abra **Settings → Actions → General → Workflow permissions** e confirme que o workflow pode solicitar `Actions: write`. Você também pode desativar manualmente em **Actions → Oracle Free Tier A1 (upgrade hourly) → ... → Disable workflow**.

## 6. Observações de segurança e custos

- Conta Oracle Free Tier: os 2 OCPUs, 12 GB e o disco de 50 GB se enquadram nos limites do Always Free **se não houver outros recursos consumindo a mesma franquia**. Não altera o tipo da conta.
- O GitHub agenda uma tentativa de upgrade no minuto `17` de cada hora. O agendamento pode atrasar ou pular execuções.
- GitHub Actions de repositórios **públicos** com runners padrão são gratuitos. Repositórios privados têm uma cota mensal.
- Repositório público significa que **código e logs são públicos**, embora Secrets fiquem protegidos. Não habilite execução de código não confiável nesse workflow.
- Depois da criação, restrinja a regra de entrada TCP/22 ao seu IP e faça backups externos. A A1 gratuita pode ser recuperada pela Oracle se considerada ociosa.
- Para ampliar uma instância 1/6, a automação a para temporariamente, tenta 2/12 e a religa mesmo se faltar capacidade. Ao atingir 2/12, desabilita o workflow.

## 7. Personalizações

O programa tenta primeiro Ubuntu 26.04, A1.Flex, 2 OCPUs e 12 GB; se não houver capacidade em todos os ADs, tenta 1 OCPU e 6 GB. Não tenta formatos pagos, não usa outro shape e não faz upgrade de conta. Se quiser outro nome da VM, altere a constante `INSTANCE_NAME` em `create_vm.py`.

