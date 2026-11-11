# skills

에이전트(Claude Code · Codex 등)에게 주는 스킬 모음입니다. 스킬 하나가 `skills/` 아래 폴더 하나입니다.

## 스킬

| 스킬 | 하는 일 |
|---|---|
| [`mac-app-ax`](skills/mac-app-ax/) | 브라우저가 아닌 맥 앱을 접근성 트리(AX)로 읽고 조작하는 헬퍼를 만들어 에이전트에 연결합니다 |
| [`windows-app-uia`](skills/windows-app-uia/) | mac-app-ax의 Windows판. 윈도우 앱을 UI Automation · Win32 창 메시지로 읽고 조작하는 헬퍼를 만들어 에이전트에 연결합니다 |
| [`terminal-recording`](skills/terminal-recording/) | Claude Code 같은 터미널 프로그램을 전용 창에서 자동으로 입력 · 대기하며 그 창만 녹화합니다 |
| [`keyword-research`](skills/keyword-research/) | 유튜브 제목을 정하기 전에 YouTube · Google 자동완성으로 실제 검색어를 확인합니다 |
| [`thumbnail-checks`](skills/thumbnail-checks/) | 유튜브 썸네일을 TV · 휴대폰 목록 크기로 미리 보고 원칙대로 점검합니다 |
| [`himalaya`](skills/himalaya/) | 로컬 Himalaya CLI로 메일을 검색 · 열람하고 첨부, 초안 · 답장 · 발송, 메일 이동 · 읽음 상태를 처리합니다 |

각 스킬의 조건 · 필요한 것 · 사용 예는 그 폴더의 `README.md`에 있습니다.

## 설치

저장소를 받은 뒤, 쓰려는 스킬 폴더를 에이전트의 스킬 폴더에 링크하거나 복사합니다.

```bash
git clone https://github.com/bandz889-chan/skills.git
```

Claude Code:

```bash
mkdir -p ~/.claude/skills
ln -s "$PWD/skills/skills/<스킬 이름>" ~/.claude/skills/<스킬 이름>
```

Windows(PowerShell)에서는 복사로 둡니다: `Copy-Item -Recurse skills\skills\<스킬 이름> $HOME\.claude\skills\`

Codex는 `~/.codex/skills/`에 같은 방식으로 둡니다. 링크로 두면 `git pull`로 스킬이 갱신됩니다.

## 구조

```
skills/<스킬 이름>/
  SKILL.md        에이전트가 읽는 본문 (이름 · 설명 머리말 포함)
  README.md       사람이 읽는 소개 · 조건
  references/     필요할 때 읽는 자세한 문서
  scripts/        바로 실행하는 도구
  templates/      복사해서 고쳐 쓰는 틀
  tests/          단위 테스트
```

## 라이선스

[MIT](LICENSE). 스킬로 만든 자동화를 어떤 앱 · 서비스에 쓰는지, 그 약관을 지키는지는 쓰는 사람의 책임입니다.
