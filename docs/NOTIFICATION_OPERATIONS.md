# 상담 알림 운영·장애 대응

## 서버 비밀키 최초 생성

서버에서 프로젝트 폴더로 이동하고 Django 비밀키를 불러온 뒤 알림용 키를 한 번만 생성합니다. 기존 파일이 있으면 덮어쓰지 않습니다.

```bash
cd /home/silverhome/silvermedical/silvermedical-homepage
export DJANGO_SECRET_KEY="$(cat /home/silverhome/.config/silvermedical/django_secret_key)"
mkdir -p /home/silverhome/.config/silvermedical
docker compose build consultation
docker run --rm --user 0 \
  -v /home/silverhome/.config/silvermedical:/secrets \
  --entrypoint python silvermedical-homepage-consultation \
  manage.py generate_notification_secrets --output /secrets/notifications.env
chmod 600 /home/silverhome/.config/silvermedical/notifications.env
```

VAPID 키를 바꾸면 기존 푸시 기기를 모두 다시 등록해야 하므로 운영 중에는 재생성하지 않습니다. 토큰 암호화 키를 바꾸면 기존 카카오 토큰을 읽을 수 없어 직원별 재연결이 필요합니다.

## 실행과 초기 사용자

```bash
export DJANGO_ALLOWED_HOSTS="silvermedical.kr,www.silvermedical.kr,staff.silvermedical.kr,192.168.30.2,127.0.0.1,localhost"
export DJANGO_CSRF_TRUSTED_ORIGINS="https://silvermedical.kr,https://www.silvermedical.kr,https://staff.silvermedical.kr"
export DJANGO_SECURE_COOKIES="true"
docker compose up -d --build consultation notification-worker homepage
docker compose exec -T consultation python manage.py bootstrap_notification_admin \
  --username silveradmin --name 연규항 --role 대표·시설장
```

## 정상 상태 확인

```bash
docker compose ps
docker compose logs --tail=100 notification-worker
curl -fsS http://127.0.0.1:8080/consult/health/
```

정상 기준은 상담·홈페이지 컨테이너가 `healthy`, 알림 작업자가 `Up`, 상태 확인 결과가 `{"status":"ok"}`인 것입니다. 서버 재부팅 후에도 같은 명령으로 자동 실행 상태를 확인합니다.

관리자 화면에서는 다음을 확인합니다.

- `알림 작업 현황`: 대기, 재시도, 완료, 실패 상태
- `알림 발송 기록`: 채널·기기별 성공과 오류 코드
- `웹 푸시 등록 기기`: 만료·비활성 기기
- `카카오톡 연결 상태`: 토큰 만료, 재연결 필요, 최근 오류

## 재알림 설정

`알림 운영 설정`에서 1차·2차 재알림 시간과 최대 발송 시도 횟수를 변경합니다. 실제 운영 기본값은 20분·60분입니다. 시험할 때만 2분 등으로 낮추고 시험 종료 후 원래 값으로 돌립니다.

## 장애별 확인

- 웹 푸시가 안 옴: 등록 기기, 브라우저 권한, 운영체제 알림 허용, 실패 로그 순으로 확인합니다.
- 카카오톡이 안 옴: 연결 상태와 최근 오류를 확인하고 `재연결 필요`면 직원 본인이 다시 연결합니다.
- 상담은 저장됐지만 알림이 없음: 알림 작업 현황과 작업자 로그를 확인합니다.
- 작업이 계속 재시도됨: 오류 코드와 서버 인터넷 연결을 확인합니다. 원인 해결 후 실패 작업을 선택해 `다시 시도`합니다.
- 서버 재부팅 뒤 알림이 멈춤: `notification-worker` 컨테이너가 실행 중인지 확인합니다.

## 백업

실행 중에도 SQLite 백업 API를 사용해 일관된 복사본을 만들 수 있습니다.

```bash
backup_name="consultations-$(date +%Y%m%d-%H%M%S).sqlite3"
docker compose exec -T consultation python manage.py shell -c \
  "import sqlite3; src=sqlite3.connect('/data/consultations.sqlite3'); dst=sqlite3.connect('/data/${backup_name}'); src.backup(dst); dst.close(); src.close()"
docker cp "silvermedical-consultation:/data/${backup_name}" "/home/silverhome/backups/${backup_name}"
```

백업 파일에는 상담 내용과 암호화된 카카오 토큰이 포함되므로 외부 공유 저장소에 올리지 않고 접근 권한을 제한합니다. 복구는 상담 서비스와 알림 작업자를 중지한 상태에서만 수행하고, 현재 DB를 별도 백업한 뒤 교체합니다.

## 환경변수

- `WEBPUSH_VAPID_PRIVATE_KEY`: 웹 푸시 서명 개인키
- `WEBPUSH_VAPID_PUBLIC_KEY`: 브라우저 등록용 공개키
- `WEBPUSH_VAPID_SUBJECT`: 장애 연락용 `mailto:` 주소
- `NOTIFICATION_TOKEN_ENCRYPTION_KEY`: 카카오 토큰 암호화 키
- `KAKAO_REST_API_KEY`: 카카오 앱 REST API 키
- `KAKAO_CLIENT_SECRET`: 카카오 앱 Client Secret
- `KAKAO_REDIRECT_URI`: 카카오 로그인 완료 주소

비밀값은 로그로 출력하거나 GitHub에 커밋하지 않습니다.
