---
name: mac-app-ax
description: "브라우저가 아닌 macOS 앱을 접근성 트리(AX)로 읽고 조작하는 네이티브 헬퍼를 만들고 MCP · 스킬로 에이전트에 연결한다. 사용자가 맥 앱(메신저 · 메모 · 음악 · 사내 도구 등)의 반복 작업을 자동화하거나, 스크린샷 · 좌표 클릭 대신 앱을 직접 조작하는 도구를 원할 때 쓴다. Use when automating a native Mac app through the Accessibility API."
---

# mac-app-ax

맥 앱의 반복 작업을 **접근성 트리(AX)로 읽고 조작하는 헬퍼 함수**로 만들어 에이전트에 붙인다.
에이전트가 스크린샷 → 좌표 클릭 → 다시 스크린샷을 반복하는 대신, 헬퍼 한 번 호출로
요소 찾기 · 상태 확인 · 동작 · 결과 관찰을 끝낸다.

`SKILL_DIR`는 이 스킬 폴더의 절대 경로다.

## 0. 맞는 도구인지 먼저 본다

사용자에게 대상 앱 이름과 자동화할 일(예: "안 읽은 대화 읽기", "메모 하나 추가")을 확인한 뒤 고른다.

- 브라우저 탭 안의 웹페이지 → 이 스킬이 아니라 브라우저 자동화(DOM).
- Windows 앱 → 이 스킬이 아니라 [windows-app-uia](../windows-app-uia/SKILL.md). 헬퍼 설계 · 요청 ID · MCP 연결 원칙은 같다.
- 앱이 공식 API · CLI · AppleScript 스크립팅 사전(`sdef /Applications/앱.app`)을 제공 → 그쪽이 먼저.
- 그 앱 · 서비스의 약관이 자동화를 금지하는지 사용자에게 확인을 권한다. 계정 제한 위험을 말한다.
- 이 스킬은 **실행 중인 앱이 화면에 내보내는 요소만** 다룬다. 앱의 통신이나 내부 저장 파일을 건드리는 방법은 쓰지 않는다.

## 1. 손쉬운 사용 권한

[permissions.md](references/permissions.md). 헬퍼를 실행하는 프로세스(터미널 · 에이전트 앱)가
시스템 설정 → 개인정보 보호 및 보안 → 손쉬운 사용에 켜져 있어야 한다. 헬퍼는 시작할 때
`AXIsProcessTrusted()`를 확인하고, 아니면 `accessibility_permission_required`로 멈춘다.

## 2. 트리를 보고, 사용자 작업 하나를 요소 순서로 적는다

[inspect.md](references/inspect.md).

```bash
swiftc -O SKILL_DIR/scripts/ax_dump.swift -o "$TMPDIR/ax_dump"
"$TMPDIR/ax_dump" --list-apps
"$TMPDIR/ax_dump" --app <번들 ID 또는 앱 이름> --depth 8 --values short
```

- 트리가 거의 비어 있으면(창 하나 · 그룹 하나뿐) 이 앱은 AX로 어렵다고 사용자에게 말하고 멈춘다.
- 사용자가 손으로 하는 순서대로, 동작 전 · 후 덤프를 비교해 각 단계의 요소를 적는다:
  역할(`AXRole`), 찾는 단서(`AXIdentifier` > `AXTitle` · `AXDescription`), 할 수 있는 동작(`AXPress` 등),
  바꿀 수 있는 속성(`settable`).
- 덤프에는 사용자 개인 내용(대화 · 이름)이 들어갈 수 있다. 공유하거나 파일로 남길 때는 `--values none`을 쓴다.

## 3. 자주 하는 동작을 헬퍼 함수로 묶는다

[helper-design.md](references/helper-design.md), 틀: [helper_action.swift](templates/helper_action.swift).

- 한 사용자 동작 = 한 헬퍼 호출. 에이전트가 요소를 하나씩 찾아 누르게 하지 않는다.
- 요소는 매번 다시 찾는다. 좌표 · 화면 순서 번호 · 이전 호출의 요소를 저장하지 않는다.
- 대상이 정확히 하나일 때만 동작한다. 0개 · 2개 이상, 모달 시트, 입력 중인 초안이 있으면 이유 코드로 멈춘다.
- 사용자 텍스트는 명령 인자가 아니라 stdin JSON으로 넘긴다.
- 화면을 바꾸는 동작은 잠금으로 한 번에 하나씩, 읽기만 병렬로.
- 시간 · 방문 노드 수 한도를 둔다. 결과는 항상 JSON 한 줄(`status`, `reason`, 한 동작 기록)로 낸다.

## 4. 결과를 다시 읽어 확인하고, 요청 ID로 중복을 막는다

[verify-and-dedupe.md](references/verify-and-dedupe.md), 틀: [operation_journal.py](templates/operation_journal.py).

- 되돌릴 수 없는 동작(보내기 · 삭제 · 결제 등)은 요청마다 `operation_id`를 받는다.
  동작 전에 기록을 디스크에 먼저 쓰고, 같은 ID가 다시 오면 실행하지 않고 기록된 결과만 돌려준다.
- 동작의 반환값을 성공 근거로 쓰지 않는다. **AX 동작이 오류를 반환해도 앱은 이미 실행했을 수 있다.**
  재시도하지 말고, 화면을 다시 읽어 바뀐 것을 관찰한 뒤 `observed` · `outcome_unknown`으로 기록한다.
- `outcome_unknown`이면 에이전트는 새 ID로 다시 하지 않고 같은 ID로 결과 조회만 한다.

## 5. 에이전트에 연결한다

[agent-wiring.md](references/agent-wiring.md), 틀: [mcp_server.py](templates/mcp_server.py).

- MCP 서버로 헬퍼 함수를 도구 하나씩 내놓는다. 도구 설명에 한계(보이는 범위만 읽음, 결과 관찰의 뜻,
  재시도 금지)를 적는다. 읽기 도구는 `readOnlyHint`, 되돌릴 수 없는 도구는 따로 표시한다.
- 그 앱 전용 스킬(`SKILL.md`)을 하나 더 만들어 "이 앱은 이 도구로만" 규칙과 결과를 읽는 법을 적는다.

## 6. 실제 앱으로 확인한다

- 사용자 본인만 보는 대상(본인에게만 가는 대상, 빈 메모, 테스트 계정)에서 먼저 돌린다.
- 헬퍼 결과를 실제 화면(스크린샷)과 비교한다. 헬퍼와 덤프는 같은 AX 데이터를 보므로 서로의 검증이 되지 않는다.
- 같은 `operation_id`로 두 번 호출해 두 번째에 실행이 0회인지 본다. 초안 · 동명 대상 · 닫힌 창에서 멈추는지 본다.
- 확인 기록에 실제 대화 · 계정 · 이름을 적지 않는다.

## 막히면

[pitfalls.md](references/pitfalls.md)를 먼저 읽는다: 값만 바꾸면 앱이 반응하지 않는 입력창,
오류를 주고도 실행되는 `AXPress`, 큰 목록에서 시간 초과, 노드마다 속성을 따로 읽어 느린 문제,
스크롤 동작이 있다고 나오는데 안 되는 경우 등.
