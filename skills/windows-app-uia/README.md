# windows-app-uia

[mac-app-ax](../mac-app-ax/)의 Windows판입니다. 브라우저가 아닌 Windows 앱을 **UI Automation(UIA) 트리나 Win32 창 메시지**로
읽고 조작하는 헬퍼를 만들어, MCP · 스킬로 에이전트에 연결합니다.

에이전트가 스크린샷을 보고 좌표를 클릭하는 대신, 헬퍼 한 번 호출로 "요소 찾기 → 상태 확인 → 동작 → 결과 관찰"을 끝냅니다.
실제 마우스 · 키보드를 움직이지 않아 사용자가 다른 일을 하는 중에도 돌릴 수 있습니다.

## 필요한 것

- Windows 10/11, Python 3.10+
- UIA 덤프 · 동작을 쓰면 `py -m pip install uiautomation` (Win32 방식은 추가 설치 없음)
- 대상 앱을 일반 권한으로 실행 (관리자 권한 앱은 일반 헬퍼가 다룰 수 없음)

## 들어 있는 것

| 경로 | 내용 |
| --- | --- |
| `SKILL.md` | 에이전트가 따르는 순서 |
| `scripts/uia_dump.py` | 앱의 UIA 트리 / Win32 창 클래스 트리 보기 |
| `templates/helper_action.py` | stdin JSON → stdout JSON 헬퍼 틀 (창 찾기 · 초안 보호 · 한 번만 동작) |
| `references/` | 권한, 트리 보기, 헬퍼 설계, 막히기 쉬운 곳 |
| `tests/` | 가짜 창으로 돌리는 헬퍼 틀 테스트 (어느 OS에서나 실행) |

요청 ID 기록(`operation_journal.py`)과 MCP 서버 틀(`mcp_server.py`)은 mac-app-ax의 것을 그대로 씁니다.
`operation_journal.py`는 Windows 잠금도 지원합니다.

## 사용 예

> "$windows-app-uia 스킬로 이 윈도우 앱에서 자주 하는 일을 헬퍼로 만들어줘."

예시 구현: 카카오톡 PC용 [kakaotalk-ax Windows 백엔드](https://github.com/bandz889-chan/kakaotalk-ax/blob/main/src/kakaotalk_windows.py).

## 주의

이 스킬은 실행 중인 앱이 내보내는 요소만 다룹니다. 앱의 통신 · 저장 파일 · 메모리는 건드리지 않습니다.
자동화가 그 앱 · 서비스의 약관에 맞는지, 다른 사람의 정보를 어떻게 다루는지는 쓰는 사람의 책임입니다.
