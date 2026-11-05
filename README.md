# Violet: Telegram Personal Knowledge Assistant Bot for Obsidian

Violet은 텔레그램 메신저를 통해 모바일 환경에서 생각, 링크, 할 일 및 메모를 전송하면, 로컬 옵시디언(Obsidian) 볼트의 데일리 노트 및 인박스(Inbox)에 실시간으로 구조화하여 저장하는 **비동기 개인 비서 봇**입니다.

---

## 1. 프로젝트 개요 (Overview)

- **배경**: 스마트폰에서 번뜩이는 아이디어나 웹 아티클을 발견했을 때, 무거운 옵시디언 앱을 열어 특정 폴더의 노트를 찾아 작성하는 과정의 마찰(Friction)을 최소화
- **해결책**:
  1. 가장 접근성이 높은 텔레그램 메신저로 텍스트, 링크, 사진을 봇에게 전송
  2. 서버 상주 봇이 메시지 유형(할 일 `/todo`, 빠른 메모, 북마크 링크)을 파싱
  3. 옵시디언 볼트의 해당 날짜 `Daily Note/{YYYY-MM-DD}.md` 또는 지정된 인박스 마크다운 파일에 타임스탬프와 함께 자동 추가
  4. Syncthing을 통해 사용자 PC 및 모바일 기기로 즉시 전파

---

## 2. 시스템 아키텍처 (Architecture)

```
[User: Telegram Mobile / Desktop]
                │
                ▼ (HTTPS Webhook / Polling)
┌────────────────────────────────────────────────────────┐
│                   Violet Bot Daemon                    │
│                                                        │
│  [Message Router] ──► [Command Parser (/todo, /memo)]  │
│          │                                             │
│          ▼                                             │
│  [Obsidian Vault Writer]                               │
│  - Daily Note 타임스탬프 헤더 추가                     │
│  - 마크다운 체크박스 `- [ ]` 포맷팅                     │
│  - URL 메타데이터 파싱                                 │
└────────────────────────────────────────────────────────┘
                │
                ▼ (Local File System Append)
[Obsidian Vault: Daily Note / Inbox Markdown Files]
                │
                ▼ (Syncthing Cluster)
[Synchronized across PC, Phone, Tablet]
```

---

## 3. 핵심 기술 스택 (Tech Stack)

| 영역 | 기술 스택 | 설명 |
|---|---|---|
| **Language** | Python 3.10+, Asyncio | 비동기 이벤트 루프 기반 봇 핸들러 |
| **API** | `python-telegram-bot` | 텔레그램 봇 API 비동기 처리 |
| **Data & Storage** | Markdown, Local File System | 옵시디언 네이티브 마크다운 파일 조작 |
| **Security** | Python-dotenv, User ID Whitelist | 인가된 사용자 ID(관리자 1인)만 접근 허용 |
| **Deployment** | Linux Systemd Daemon | 24/7 상시 백그라운드 프로세스 관리 |

---

## 4. 파일 구성 (Structure)

```
violet/
├── agent/            # 메시지 해석 및 지능형 라우팅 에이전트
├── bot/              # 텔레그램 이벤트 핸들러 및 명령어 라우터
├── config/           # 볼트 경로 및 봇 설정 로더
├── data/             # 로컬 캐시 및 상태 파일
├── main.py           # 데몬 진입점
├── requirements.txt  # 의존성 패키지
└── .env.example      # 환경변수 템플릿
```

---

## 5. 엔지니어링 특징 (Engineering Highlights)

1. **엄격한 화이트리스트 보안**:
   - 텔레그램 봇 토큰 유출 시 타인이 개인 볼트에 임의의 내용을 쓰거나 볼트 내용을 탈취하지 못하도록, 허용된 텔레그램 User ID 외의 모든 수신 메시지를 즉시 차단
2. **원자적 파일 추가(Atomic Append)**:
   - Syncthing이 실시간으로 파일 변경을 감지하고 있는 환경에서 파일 쓰기 충돌을 방지하기 위해 파일 락과 안전한 쓰기 버퍼 적용
