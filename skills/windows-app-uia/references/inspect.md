# 트리 보기 (Windows)

도구: [scripts/uia_dump.py](../scripts/uia_dump.py). Python 3.10+.

```powershell
py scripts\uia_dump.py --list-apps                                   # 창이 있는 프로세스 목록
py scripts\uia_dump.py --process notepad.exe --mode uia --depth 6     # UI Automation 트리 (uiautomation 패키지 필요)
py scripts\uia_dump.py --process notepad.exe --mode win32 --depth 6   # Win32 창 클래스 트리 (추가 설치 없음)
py scripts\uia_dump.py --process notepad.exe --mode win32 --values none > tree.txt
```

## UIA 모드에서 볼 것

| 항목 | 쓰임 |
| --- | --- |
| `ControlType` | Button · Edit · List · ListItem · Document · Pane 등 역할 |
| `AutomationId` | 가장 안정적인 찾기 단서. 비어 있으면 `Name` + 부모 구조 |
| `Name` | 버튼 글자 · 목록 항목 이름. 언어 설정에 따라 바뀐다 |
| 패턴 | `Invoke`(누르기), `Value`(값 넣기), `Text`(긴 본문 읽기), `Scroll`, `SelectionItem` |
| `IsEnabled` · `IsOffscreen` | 비활성 버튼, 화면 밖 항목 |

## Win32 모드에서 볼 것

| 항목 | 쓰임 |
| --- | --- |
| 클래스 이름 | `Edit` · `RICHEDIT50W`(입력창), `#32770`(대화상자), 앱 전용 이름(예: `EVA_...`) |
| 창 제목 | 대화방 · 문서 이름이 제목인 앱이 많다. 동명 창을 꼭 센다 |
| 텍스트 | `WM_GETTEXT`로 읽은 값. 입력창 초안이 보이면 덮어쓰지 않는 근거가 된다 |
| 부모 · 순서 | 같은 클래스가 여러 개면 부모 기준으로 고른다 (예: 두 번째 탭 아래의 `Edit`) |

## 작업을 요소 순서로 적기

1. 사용자가 손으로 하는 순서를 적는다 (예: 검색창 클릭 → 이름 입력 → Enter → 열린 창 확인).
2. 각 단계 전 · 후로 덤프를 떠서 바뀐 요소를 찾는다.
3. 단계마다 찾는 단서 · 동작 방법(패턴 또는 메시지) · 확인 방법(무엇을 다시 읽나)을 표로 남긴다.
4. 직접 그린 목록(UIA에 항목이 없음)은 앱의 복사 · 내보내기 기능처럼 앱이 텍스트로 내주는 길이 있는지 본다.
