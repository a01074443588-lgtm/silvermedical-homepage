# 카카오톡 나에게 보내기 설정

## 사전 준비

카카오 디벨로퍼스에서 기관용 앱을 만들고 다음 항목을 설정합니다.

- 제품 설정에서 `카카오 로그인` 활성화
- Redirect URI: `https://staff.silvermedical.kr/staff/notifications/kakao/callback/`
- Web 플랫폼 사이트 도메인: `https://staff.silvermedical.kr`
- 동의 항목에서 `카카오톡 메시지 전송` 권한 사용 설정
- 앱의 REST API 키 확인
- 보안을 위해 Client Secret 생성 및 활성화 권장

카카오 검수·권한 정책은 변경될 수 있으므로 실제 운영 전에 카카오 디벨로퍼스 안내에서 `talk_message` 동의 가능 상태를 확인합니다.

## 서버 비밀 설정

다음 값은 `/home/silverhome/.config/silvermedical/notifications.env`에만 입력합니다.

```dotenv
KAKAO_REST_API_KEY=카카오_REST_API_키
KAKAO_CLIENT_SECRET=카카오_Client_Secret
KAKAO_REDIRECT_URI=https://staff.silvermedical.kr/staff/notifications/kakao/callback/
```

파일 권한은 소유자만 읽고 쓸 수 있도록 유지합니다.

```bash
chmod 600 /home/silverhome/.config/silvermedical/notifications.env
```

설정 변경 후 상담 서비스와 알림 작업자를 다시 만듭니다.

```bash
docker compose up -d --build --force-recreate consultation notification-worker homepage
```

## 직원 연결

1. 직원 본인이 `내 알림 설정`을 엽니다.
2. `카카오톡 알림 연결`을 누릅니다.
3. 본인 카카오 계정으로 로그인하고 메시지 전송에 동의합니다.
4. 화면에 `연결됨`이 표시되면 `시험 메시지 보내기`를 누릅니다.
5. 본인 카카오톡의 `나와의 채팅`에서 시험 메시지를 확인합니다.

액세스 토큰은 서버가 리프레시 토큰으로 자동 갱신합니다. 리프레시 토큰까지 만료되거나 동의가 철회되면 `재연결 필요`가 표시되며 직원이 다시 연결해야 합니다.

## 주의사항

- 한 직원의 토큰으로 다른 직원에게 보내지 않습니다.
- 토큰이나 앱 키를 채팅, README, GitHub 이슈에 붙여 넣지 않습니다.
- 카카오 연결 해제는 해당 직원의 앱 연결과 저장 토큰을 함께 제거합니다.
- 알림 메시지에는 상담 본문과 전체 전화번호를 넣지 않습니다.
