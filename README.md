# GSM — downloads e atualizações

O GSM é um clipador desktop para Linux e Windows. Este repositório contém o canal público de distribuição. Os pacotes incluem os avisos de licença e fontes correspondentes.

Versão atual: [GSM 0.14.0-alpha](https://github.com/Ainstem/GSM-downloads/releases/tag/v0.14.0-alpha).

## Instalar

Baixe o instalador da sua plataforma na página [Releases](https://github.com/Ainstem/GSM-downloads/releases).

Linux: execute `bash GSM-Linux-x86_64-0.14.0-alpha.run`. O pacote inclui o motor de captura e as ferramentas de vídeo; não exige instalação manual de GSR/FFmpeg. Drivers e autorização de compartilhamento de tela continuam sendo fornecidos pelo sistema. Depois abra pelo menu ou execute `GSM` em um novo terminal.

Windows: execute `GSM-Setup-0.14.0-alpha.exe` e siga o instalador.

## Atualizar

A partir da 0.5, o app verifica atualizações ao abrir e mostra um aviso central com as novidades da versão e a confirmação para **Atualizar**. Nas configurações, **Buscar atualizações** consulta as versões sem instalar. No Linux também é possível executar `GSM update`.

Quem usa 0.3/0.4 precisa executar o primeiro instalador uma vez para receber o atualizador. Clips e configurações não são apagados.

## Publicar uma versão — mantenedor

1. No build validado de `Ainstem/GSM`, use os instaladores Linux/Windows e fontes correspondentes disponíveis nos artifacts ou no rascunho privado de validação. Confira os hashes registrados no build.
2. [Crie uma Release](https://github.com/Ainstem/GSM-downloads/releases/new) com a tag `v0.14.0-alpha` (ou a versão correspondente).
3. Anexe os arquivos **GSM-Linux-x86_64-0.14.0-alpha.run** e **GSM-Setup-0.14.0-alpha.exe**. Anexe também **GSM-Linux-Media-Sources-0.14.0-alpha.tar.gz**, que oferece as fontes correspondentes. Os três arquivos devem estar anexados antes de publicar.
4. Publique a Release. O workflow **Publish update channel** calcula SHA-256, publica `update.json` e `SHA256SUMS` na Release e atualiza o manifesto público em `main`.
5. Confira o resultado em Actions. Somente depois os apps recebem o aviso. Não precisa criar tokens pessoais.

Para repetir a geração de uma Release já publicada, execute o workflow manualmente informando a tag. Nunca envie uma versão cujo número seja menor que a versão já publicada no canal.

Canal consultado pelos apps: https://raw.githubusercontent.com/Ainstem/GSM-downloads/main/update.json . Antes da primeira Release, o atualizador informa que o canal ainda não foi publicado. Não há uma atualização disponível só por este repositório existir.
