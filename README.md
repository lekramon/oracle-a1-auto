# Oracle Always Free A1 — criação automática (a cada 5 minutos)

Configuração fixa: **VM.Standard.A1.Flex**, **2 OCPUs**, **12 GB RAM**, **50 GB**, **Ubuntu 26.04 full ARM64**, **São Paulo**. Reutiliza a sub-rede pública da VCN `agents-vcn` e atribui IPv4 público.

## 1. Conta Oracle: criar uma chave de API NOVA

Na Oracle Cloud Console:

1. Perfil (ícone superior direito) → **My Profile** → **API Keys** → **Add API Key**.
2. Escolha **Generate API Key Pair**, baixe a **private key** e adicione a public key à Oracle.
3. Copie os valores do arquivo de configuração exibido: `user`, `tenancy`, `fingerprint`, `region`. A região deve ser `sa-saopaulo-1`.
4. Guarde a chave privada da API com segurança. **Não confunda** com a chave SSH da instância! Não envie chaves privadas por chat, nem para o repositório.

## 2. Encontrar o OCID da sub-rede

**Networking → Virtual Cloud Networks → agents-vcn → Subnets → public subnet-agents-vcn**. Copie o campo **OCID** dessa sub-rede (não é o OCID da VCN).

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
| `OCI_SUBNET_OCID` | OCID da sub-rede **pública** de `agents-vcn` |
| `OCI_SSH_PUBLIC_KEY` | Uma linha inteira do arquivo da chave SSH **pública** que você baixou na criação da instância |

**Importante:** Não escreva esses valores no código ou em mensagens públicas. GitHub Secrets não aparecem como texto no repositório.

## 5. Executar o primeiro teste

GitHub → **Actions → Oracle Free Tier A1 (5 min) → Run workflow**.

- `RESULTADO: unavailable`: a Oracle segue sem capacidade. O cron continuará tentando.
- `RESULTADO: created`: solicitação de VM aceita. O agendamento se desativará automaticamente e você deverá conferir em Compute → Instances.
- `RESULTADO: already_exists`: uma A1 já existe no compartimento; o agendamento também se desativará.
- **Erro**: abra o log para corrigir credenciais, permissões ou imagem. Não é tratado como falta de capacidade.

Se a etapa de desativação falhar por permissão, abra **Settings → Actions → General → Workflow permissions** e confirme que o workflow pode solicitar `Actions: write`. Você também pode desativar manualmente em **Actions → Oracle Free Tier A1 (5 min) → ... → Disable workflow**.

## 6. Observações de segurança e custos

- Conta Oracle Free Tier: os 2 OCPUs, 12 GB e o disco de 50 GB se enquadram nos limites do Always Free **se não houver outros recursos consumindo a mesma franquia**. Não altera o tipo da conta.
- O GitHub executa a tarefa a cada **5 minutos nominais**, mas o agendamento pode atrasar ou pular execuções.
- GitHub Actions de repositórios **públicos** com runners padrão são gratuitos. Repositórios privados têm uma cota mensal e um workflow a cada 5 minutos pode ultrapassá-la.
- Repositório público significa que **código e logs são públicos**, embora Secrets fiquem protegidos. Não habilite execução de código não confiável nesse workflow.
- Depois da criação, restrinja a regra de entrada TCP/22 ao seu IP e faça backups externos. A A1 gratuita pode ser recuperada pela Oracle se considerada ociosa.
- A automação desabilita o workflow quando a API aceita o lançamento. Você ainda precisa confirmar que a VM chega a `Running` no Console.

## 7. Personalizações

O programa usa deliberadamente Ubuntu 26.04, A1.Flex, 2 OCPUs e 12 GB **fixos**; não tenta formatos pagos, não reduz os recursos e não faz upgrade de conta. Se quiser outro nome da VM, altere a constante `INSTANCE_NAME` em `create_vm.py`.

