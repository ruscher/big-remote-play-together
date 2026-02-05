# Guia de Contribuição - Big Remote Play Together

Obrigado por considerar contribuir com o Big Remote Play Together! 🎮

## 🤝 Como Contribuir

### Reportar Bugs
1. Verifique se o bug já não foi reportado
2. Abra uma nova issue com:
   - Descrição clara do problema
   - Passos para reproduzir
   - Comportamento esperado vs atual
   - Informações do sistema (OS, versões, etc)
   - Logs relevantes

### Sugerir Funcionalidades
1. Abra uma issue com tag `enhancement`
2. Descreva a funcionalidade desejada
3. Explique o caso de uso
4. Sugira implementação (opcional)

### Contribuir com Código

#### Setup de Desenvolvimento
```bash
# Clone o repositório
git clone https://github.com/biglinux/big-remoteplay-together.git
cd big-remoteplay-together

# Instale dependências
sudo pacman -S python python-gobject gtk4 libadwaita

# Execute em modo desenvolvimento
make dev
```

#### Padrões de Código

**Python**:
- Siga PEP 8
- Use type hints quando possível
- Docstrings em português
- Máximo 100 caracteres por linha

```python
def exemplo_funcao(parametro: str) -> bool:
    """
    Descrição da função
    
    Args:
        parametro: Descrição do parâmetro
        
    Returns:
        Descrição do retorno
    """
    pass
```

**Shell Script**:
- Use bash
- Sempre `set -e` no início
- Comentários em português
- Mensagens de usuário com emojis

```bash
#!/bin/bash
set -e

# Comentário explicativo
echo "✅ Operação concluída"
```

**Git Commits**:
Formato: `tipo: descrição breve`

Tipos:
- `feat`: Nova funcionalidade
- `fix`: Correção de bug
- `docs`: Documentação
- `style`: Formatação
- `refactor`: Refatoração
- `test`: Testes
- `chore`: Manutenção

Exemplos:
```
feat: adicionar suporte a convites por link
fix: corrigir descoberta de hosts IPv6
docs: atualizar guia de instalação
```

#### Processo de PR

1. Fork o repositório
2. Crie uma branch: `git checkout -b minha-feature`
3. Faça commits atômicos
4. Teste suas mudanças
5. Push para seu fork
6. Abra um Pull Request

**Checklist do PR**:
- [ ] Código segue padrões do projeto
- [ ] Funcionalidade testada manualmente
- [ ] Documentação atualizada
- [ ] Sem warnings ou erros

### Tradução

Ajude a traduzir o aplicativo:

1. Copie `po/big-remoteplay.pot`
2. Traduza strings
3. Submeta PR com tradução

## 📁 Estrutura do Projeto

```
big-remote-play-together/
├── src/                # Código Python
│   ├── main.py        # Entry point
│   ├── ui/            # Interface GTK
│   ├── host/          # Módulo Host
│   ├── guest/         # Módulo Guest
│   └── utils/         # Utilitários
├── scripts/           # Scripts shell
├── data/              # Assets
├── docker/            # Docker configs
├── docs/              # Documentação
└── tests/             # Testes
```

## 🧪 Testes

```bash
# Executar testes
make test

# Teste manual
make dev
```

## 📝 Documentação

Mantenha documentação atualizada:
- README.md
- docs/INSTALL.md
- Comentários no código
- Docstrings

## 🎨 UI/UX

Para mudanças na interface:
- Siga HIG do GNOME
- Use componentes Adwaita
- Mantenha consistência visual
- Teste em diferentes temas

## 📄 Licença

Ao contribuir, você concorda que suas contribuições serão licenciadas sob GPL-3.0.

## 💬 Comunicação

- Issues no GitHub
- Email: rruscher@gmail.com

## 🙏 Reconhecimento

Contribuidores são listados no README.md

Obrigado por contribuir! 🚀
