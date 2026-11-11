# 동작을 헬퍼 함수로 묶기 (Windows)

틀: [templates/helper_action.py](../templates/helper_action.py). 원칙은 [mac-app-ax helper-design](../../mac-app-ax/references/helper-design.md)과 같다.

## 구조

```
Python 래퍼 (인수 검사 · 잠금 · 요청 기록 · 재확인)
  └─ 헬퍼 (stdin JSON → stdout JSON)
       ├─ 실행 확인 (Windows, 대상 프로세스, 권한 수준)
       ├─ 대상 창 정확히 하나 찾기 (프로세스 이름 + 창 제목 + 필수 자식 클래스)
       ├─ 요소 찾기 (UIA: AutomationId/Name, Win32: 클래스 + 부모)
       ├─ 전제 확인 (모달 없음 · 초안 없음 · 버튼 활성)
       ├─ 동작 한 번 (UIA 패턴 또는 PostMessage)
       └─ 결과 JSON (status, reason, dispatchAttempted, elapsedMs)
```

맥은 Swift 바이너리를 컴파일했지만 Windows는 `ctypes`(Win32)와 선택 패키지 `uiautomation`(UIA)으로 Python 안에서 끝낸다.
컴파일러가 필요 없다.

## 동작 고르는 순서

1. **UIA 패턴**: `InvokePattern.Invoke()`, `ValuePattern.SetValue()`, `TextPattern`으로 읽기. 가장 안전하다.
2. **창 메시지**: `WM_SETTEXT` / `WM_GETTEXT`(Edit · RichEdit), `PostMessage(WM_KEYDOWN/UP)`(Enter, 앱 단축키).
   수정 키(Ctrl)가 필요하면 `AttachThreadInput` + `SetKeyboardState`로 그 순간만 눌린 상태를 만든다 ([pitfalls.md](pitfalls.md)).
3. **쓰지 않는 것**: `SendInput` · `mouse_event` · 좌표 클릭. 사용자의 커서 · 포커스를 빼앗고 다른 창에 입력될 수 있다.

## 규칙 (Windows에서 더 신경 쓸 것)

- **창 찾기**: `EnumWindows`로 대상 프로세스의 창만 본다. 다른 프로그램의 같은 제목 창(브라우저 탭 제목 등)을 섞지 않는다.
- **유일성**: 같은 제목 창이 둘이면 `duplicate_window_title`. 같은 클래스 자식이 둘이면 `*_not_unique`.
- **초안 보호**: 입력창을 `WM_GETTEXT`로 먼저 읽어 비어 있지 않으면 `existing_draft_preserved`로 멈춘다.
- **넣은 값 확인**: `WM_SETTEXT` 뒤 다시 읽어 같지 않으면 지우고 `composer_text_mismatch`로 멈춘다. 줄바꿈은 `\r\n`.
- **복사 기능을 읽기에 쓸 때**: 클립보드 순번(`GetClipboardSequenceNumber`)이 바뀐 것을 확인하고, 원래 텍스트를 되돌린다.
- **잠금**: `msvcrt.locking`으로 프로세스 간 잠금. 기다리지 말고 바로 `busy`를 알린다.
- **한도**: 전체 마감(예: 8초), 대기 루프마다 0.1초. 응답 없는 앱에는 `SendMessageTimeout`을 쓴다.
