# Старт нового учебного проекта из GitHub Template

Этот репозиторий используется как шаблон-заготовка для новых учебных проектов.

Цель: не начинать каждый проект с пустого листа и не копировать вручную `AGENTS.md`, README, настройки, структуру папок и прочие стартовые файлы.

---

## Общая схема

```text
template repo на GitHub
        ↓
новый GitHub repo из шаблона
        ↓
clone на VPS в ~/projects/<project-name>
        ↓
адаптация README.md / AGENTS.md
        ↓
первый коммит проекта
```

Новый репозиторий, созданный из шаблона, не является fork'ом.
Он получает стартовые файлы и структуру, но дальше живёт как самостоятельный проект.

---

## 1. Подготовить VPS

Предполагается, что VPS уже настроена:

* создан пользователь `user`;
* настроен SSH-вход по ключу;
* отключён вход root/password по SSH;
* обновлена система;
* установлен `git`;
* настроен firewall;
* желательно настроен swap.

Для проектов используем директорию:

```bash
mkdir -p ~/projects
cd ~/projects
```

---

## 2. Установить GitHub CLI на VPS

```bash
sudo apt update
sudo apt install -y git curl wget gpg
```

Установка GitHub CLI:

```bash
(type -p wget >/dev/null || (sudo apt update && sudo apt install wget -y)) \
  && sudo mkdir -p -m 755 /etc/apt/keyrings \
  && wget -qO- https://cli.github.com/packages/githubcli-archive-keyring.gpg \
    | sudo tee /etc/apt/keyrings/githubcli-archive-keyring.gpg > /dev/null \
  && sudo chmod go+r /etc/apt/keyrings/githubcli-archive-keyring.gpg \
  && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
    | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null \
  && sudo apt update \
  && sudo apt install gh -y
```

Проверка:

```bash
gh --version
```

---

## 3. Авторизоваться в GitHub

```bash
gh auth login
```

Рекомендуемый сценарий:

```text
GitHub.com
SSH или HTTPS
Login with a web browser
```

После авторизации проверить:

```bash
gh auth status
```

Важно: после авторизации VPS получает доступ к GitHub от имени пользователя.
Не стоит хранить на VPS лишние токены и доступы без необходимости.

---

## 4. Настроить Git-профиль на VPS

```bash
git config --global user.name "AlievRust"
git config --global user.email "rusal@mail.ru"
git config --global init.defaultBranch main
```

Проверить:

```bash
git config --global --list
```

---

## 5. Создать новый учебный репозиторий из шаблона

Перейти в папку проектов:

```bash
mkdir -p ~/projects
cd ~/projects
```

Задать переменные:

```bash
TEMPLATE_REPO="AlievRust/<template-repo-name>"
PROJECT_NAME="<new-study-project-name>"
NEW_REPO="AlievRust/$PROJECT_NAME"
```

Создать новый приватный репозиторий из шаблона и сразу склонировать его на VPS:

```bash
gh repo create "$NEW_REPO" \
  --private \
  --template "$TEMPLATE_REPO" \
  --clone
```

После выполнения появится папка:

```bash
~/projects/<new-study-project-name>
```

Перейти в проект:

```bash
cd "$PROJECT_NAME"
```

---

## 6. Проверить, что шаблон применился

```bash
ls -la
```

Посмотреть файлы верхнего уровня:

```bash
find . -maxdepth 2 -type f | sort
```

Проверить важные файлы:

```bash
test -f AGENTS.md && echo "AGENTS.md есть"
test -f README.md && echo "README.md есть"
```

Проверить remote:

```bash
git remote -v
```

Remote должен указывать на новый репозиторий, а не на template repo.

---

## 7. Адаптировать проект под задачу

Обычно после создания проекта нужно сразу поправить:

```bash
nano README.md
nano AGENTS.md
```

Минимально стоит обновить:

* название проекта;
* цель проекта;
* стек;
* текущую учебную задачу;
* правила работы агента/ассистента;
* TODO / ближайшие шаги.

---

## 8. Сделать первый коммит после адаптации

```bash
git status
git add .
git commit -m "chore: adapt template for learning project"
git push
```

---

## 9. Полный быстрый сценарий

```bash
mkdir -p ~/projects
cd ~/projects

TEMPLATE_REPO="AlievRust/<template-repo-name>"
PROJECT_NAME="<new-study-project-name>"
NEW_REPO="AlievRust/$PROJECT_NAME"

gh repo create "$NEW_REPO" \
  --private \
  --template "$TEMPLATE_REPO" \
  --clone

cd "$PROJECT_NAME"

ls -la
git remote -v
git status

nano README.md
nano AGENTS.md

git add .
git commit -m "chore: adapt template for learning project"
git push
```

---

## 10. Public или private?

Для учебных проектов по умолчанию лучше использовать:

```bash
--private
```

Причины:

* можно спокойно экспериментировать;
* можно не бояться случайных токенов, черновиков и мусора;
* можно позже привести README в порядок и открыть проект публично.

Если проект сразу должен быть публичным:

```bash
gh repo create "$NEW_REPO" \
  --public \
  --template "$TEMPLATE_REPO" \
  --clone
```

---

## 11. Ветки шаблона

Обычно достаточно основной ветки `main`.

Если нужно скопировать все ветки шаблона:

```bash
gh repo create "$NEW_REPO" \
  --private \
  --template "$TEMPLATE_REPO" \
  --include-all-branches \
  --clone
```

Но для учебного проекта лучше не тащить лишние ветки без необходимости.

---

## 12. Рекомендуемый рабочий ритуал

1. Создать новый репозиторий из шаблона через `gh repo create`.
2. Сразу склонировать его на VPS.
3. Проверить `README.md`, `AGENTS.md`, структуру папок.
4. Адаптировать описание проекта.
5. Сделать первый коммит.
6. Дальше работать уже как с обычным самостоятельным репозиторием.

---

## 13. Важные принципы

* Template repo — это стартовая заготовка, а не родительский проект.
* Новый проект должен жить своей историей Git.
* Не нужно вручную копировать `AGENTS.md` и конфиги.
* Не нужно делать fork, если задача — создать самостоятельный учебный проект.
* Не стоит хранить секреты, токены и `.env` в шаблоне.
* Для секретов использовать `.env.example`, а настоящий `.env` держать только локально/на VPS.
* Первый коммит после создания проекта должен фиксировать адаптацию шаблона под конкретную задачу.

---

## 14. Пример

```bash
cd ~/projects

TEMPLATE_REPO="AlievRust/agent-project-template"
PROJECT_NAME="learning-hermes-agent"
NEW_REPO="AlievRust/$PROJECT_NAME"

gh repo create "$NEW_REPO" \
  --private \
  --template "$TEMPLATE_REPO" \
  --clone

cd "$PROJECT_NAME"

nano README.md
nano AGENTS.md

git add .
git commit -m "chore: adapt template for learning project"
git push
```

После этого проект готов к работе.

## 15. Для Win

Установка git и gh

winget install --id Git.Git --source winget
winget install --id GitHub.cli --source winget
git --version
gh --version

Авторизация
gh auth login

Создаем и переходим в целевую папку проекта:
mkdir $HOME\projects
cd $HOME\projects

Клоним

$TemplateRepo = "AlievRust/<template-repo-name>"
$ProjectName = "<new-study-project-name>"
$NewRepo = "AlievRust/$ProjectName"

gh repo create $NewRepo `
  --private `
  --template $TemplateRepo `
  --clone

cd $ProjectName
code .


Помчали:
git status
git add .
git commit -m "chore: adapt template for learning project"
git push
