---
name: windows-app-uia
description: "브라우저가 아닌 Windows 앱을 UI Automation(UIA)이나 Win32 창 메시지로 읽고 조작하는 헬퍼를 만들고 MCP · 스킬로 에이전트에 연결한다. 사용자가 윈도우 앱(메신저 · 메모 · 사내 도구 등)의 반복 작업을 자동화하거나, 스크린샷 · 좌표 클릭 대신 앱을 직접 조작하는 도구를 원할 때 쓴다. mac-app-ax의 Windows판. Use when automating a native Windows app through UI Automation or Win32 messages."
---

# windows-app-uia

윈도우 앱의 반복 작업을 **UI Automation 트리나 Win32 창 메시지로 읽고 조작하는 헬퍼 함수**로 만들어 에이전트에 붙인다.
에이전트가 스크린샷 → 좌표 클릭 → 다시 스크린샷을 반복하는 대신, 헬퍼 한 번 호출로
요소 찾기 · 상태 확인 · 동작 · 결과 관찰을 끝낸다. 원칙은 [mac-app-ax](../mac-app-ax/SKILL.md)와 같고, 다루는 장치만 다르다.

`SKILL_DIR`는 이 스킬 폴더의 절대 경로다.

## 0. 맞는 도구인지 먼저 본다

- 브라우저 탭 안의 웹페이지 → 브라우저 자동화(DOM).
- 앱이 공식 API · CLI · COM 자동화를 제공 → 그쪽이 먼저.
- 약관이 자동화를 금지하는지 사용자에게 확인을 권하고, 계정 제한 위험을 말한다.
- **실행 중인 앱이 내보내는 요소만** 다룬다. 앱의 통신 · 내부 저장 파일 · 메모리를 건드리지 않는다.

## 1. 권한과 실행 조건

[permissions.md](references/permissions.md). 맥의 손쉬운 사용 같은 별도 권한 창은 없다. 대신:

- **같은 권한 수준**: 대상 앱이 관리자 권한으로 떠 있으면 일반 권한 헬퍼는 메시지를 못 보낸다(UIPI).
  헬퍼를 관리자 권한으로 올리지 말고, 대상 앱을 일반 권한으로 다시 띄우게 안내한다.
- **잠긴 화면 · 원격 세션 끊김**에서는 UIA 값이 비거나 동작이 무시될 수 있다. 사용자가 로그인한 데스크톱에서만 돌린다.

## 2. 트리를 보고, 사용자 작업 하나를 요소 순서로 적는다

[inspect.md](references/inspect.md).

```powershell
py -m pip install uiautomation          # UIA 덤프용(선택). Win32 덤프는 추가 설치 없음
py SKILL_DIR\scripts\uia_dump.py --list-apps
py SKILL_DIR\scripts\uia_dump.py --process 앱.exe --mode uia --depth 8 --values short
py SKILL_DIR\scripts\uia_dump.py --process 앱.exe --mode win32 --depth 8 --values short
```

- **UIA 모드**를 먼저 본다. `ControlType` · `AutomationId` · `Name` · 지원 패턴(`Invoke` · `Value` · `Text` · `Scroll`)이 나오면 UIA로 만든다.
- UIA 트리가 거의 비어 있으면(창 하나 · Pane 하나뿐, 직접 그린 화면) **Win32 모드**를 본다.
  창 클래스 이름(`Edit`, `RICHEDIT50W`, 앱 전용 클래스)이 보이면 창 메시지(`WM_SETTEXT`, `WM_GETTEXT`, 키 메시지)로 만든다.
- 둘 다 비어 있으면 이 앱은 이 방식으로 어렵다고 사용자에게 말하고 멈춘다.
- 사용자가 손으로 하는 순서대로 동작 전 · 후 덤프를 비교해 각 단계의 요소를 적는다.
- 덤프에 개인 내용이 들어갈 수 있다. 공유할 때는 `--values none`.

## 3. 자주 하는 동작을 헬퍼 함수로 묶는다

[helper-design.md](references/helper-design.md), 틀: [helper_action.py](templates/helper_action.py).

- 한 사용자 동작 = 한 헬퍼 호출. 사용자 텍스트는 stdin JSON으로 받는다.
- 요소는 매번 다시 찾는다. 창 핸들 · 좌표 · 순서 번호를 저장하지 않는다.
- 대상이 정확히 하나일 때만 동작한다. 0개 · 2개 이상, 모달 대화상자, 입력 중인 초안이 있으면 이유 코드로 멈춘다.
- 실제 마우스 · 키보드(`SendInput`)는 쓰지 않는다. 사용자의 커서와 포커스를 빼앗기 때문이다.
  UIA 패턴 → 창 메시지(`PostMessage`) 순으로 고르고, 앱 기능(복사 · 검색)을 메시지로 부르는 것까지만 쓴다.
- 클립보드를 써야 하면 원래 텍스트를 저장했다가 되돌리고, 못 되돌리면 결과에 적는다.
- 화면을 바꾸는 동작은 파일 잠금으로 하나씩, 읽기만 병렬로.

## 4. 결과를 다시 읽어 확인하고, 요청 ID로 중복을 막는다

[mac-app-ax의 verify-and-dedupe.md](../mac-app-ax/references/verify-and-dedupe.md),
틀: [operation_journal.py](../mac-app-ax/templates/operation_journal.py) (Windows 잠금 포함, 그대로 복사해 쓴다).

- 되돌릴 수 없는 동작(보내기 · 삭제 · 결제)은 요청마다 `operation_id`. 동작 전에 기록을 먼저 쓴다.
- `PostMessage`는 "보냈다"만 알려준다. 앱이 처리했는지는 화면을 다시 읽어 관찰한 뒤 `observed` · `outcome_unknown`으로 기록한다.
- `outcome_unknown`이면 새 ID로 다시 하지 않고 같은 ID로 결과 조회만 한다.

## 5. 에이전트에 연결한다

[mac-app-ax의 agent-wiring.md](../mac-app-ax/references/agent-wiring.md), 틀: [mac-app-ax의 mcp_server.py](../mac-app-ax/templates/mcp_server.py).
Swift 바이너리 대신 `helper_action.py`를 같은 프로세스에서 부르거나 `py helper_action.py`로 실행하도록 `binary()` 부분만 바꾼다.

```json
{ "mcpServers": { "myapp-uia": { "command": "C:\\절대경로\\.venv\\Scripts\\python.exe", "args": ["C:\\절대경로\\mcp_server.py"] } } }
```

## 6. 실제 앱으로 확인한다

- 본인만 보는 대상(본인에게 가는 대화, 빈 메모, 테스트 계정)에서 먼저 돌린다.
- 헬퍼 결과를 실제 화면과 비교한다. 같은 `operation_id`로 두 번 호출해 두 번째에 실행 0회인지 본다.
- 앱 업데이트 후에는 2단계 덤프를 다시 떠서 클래스 이름 · AutomationId가 그대로인지 본다.

## 막히면

[pitfalls.md](references/pitfalls.md): 직접 그린 화면이라 UIA가 비어 있음, `WM_SETTEXT`는 들어갔는데 앱이 모름,
수정 키(Ctrl) 조합이 안 먹음, 관리자 권한 앱, 포커스 훔치기 제한, 고해상도(DPI) 좌표 등.

예시 구현: [kakaotalk-ax Windows 백엔드](https://github.com/bandz889-chan/kakaotalk-ax/blob/main/src/kakaotalk_windows.py)
(카카오톡 PC: Win32 창 클래스 + 앱의 전체 선택 · 복사 + 입력창 `WM_SETTEXT` · Enter).
