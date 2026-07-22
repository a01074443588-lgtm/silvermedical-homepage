# 실버메디컬복지센터 홈페이지

실버메디컬복지센터 공식 홈페이지, 센터소식 게시판, 장기요양 급여비용 계산기, 비공개 상담 접수함을 함께 관리하는 웹사이트입니다. 홈페이지 기본 화면은 정적 HTML/CSS/JS로 제공하고, 센터소식·상담·연도별 급여비용 설정은 Django 관리 기능을 사용합니다.

요양원, 주간보호, 방문요양, 방문목욕, 단기보호, 통합재가 서비스를 보호자가 이해하기 쉽도록 구성했고, 메뉴별 상세 페이지와 `benefits.html` 급여비용 계산기를 함께 제공합니다.

하모니카 서버에서는 Django 기반 비공개 1:1 상담 접수함을 함께 실행합니다. 상담 글목록은 공개하지 않으며 직원 관리 화면에서만 전체 접수 내용을 확인합니다.

신규 상담은 서버에서 웹 푸시와 카카오톡 `나에게 보내기` 알림 작업으로 분리 처리합니다. 직원별 수신 범위, 여러 기기 등록, 미확인 재알림, 상담 처리 이력과 장애 재시도를 지원합니다.

## 로컬에서 여는 방법

Windows 파일 탐색기에서 아래 파일을 더블클릭하면 바로 확인할 수 있습니다.

```powershell
C:\Users\jirlm\Documents\홈페이지\index.html
C:\Users\jirlm\Documents\홈페이지\about.html
C:\Users\jirlm\Documents\홈페이지\services.html
C:\Users\jirlm\Documents\홈페이지\benefits.html
```

또는 VS Code에서 Live Server 확장을 사용해 미리볼 수 있습니다.

파일을 직접 열 때 급여비용 계산기는 내장된 2026년 기본 자료를 사용합니다. 관리자에서 저장한 연도별 자료까지 확인하려면 아래 Docker 실행 방식으로 열어야 합니다.

## 배포

- GitHub Pages 배포 가능
- Cloudflare Pages 배포 가능
- GitHub 저장소 이름: `silvermedical-homepage`
- 공개 주소: `https://silvermedical.kr/`

### 하모니카 서버에서 Docker로 실행

프로젝트 폴더에서 아래 명령을 실행하면 `nginx:alpine` 컨테이너가 8080 포트로 시작됩니다.

```bash
export DJANGO_SECRET_KEY="$(cat /home/silverhome/.config/silvermedical/django_secret_key)"
docker compose up -d --build
docker compose ps
curl -I http://127.0.0.1:8080
```

- 컨테이너 이름: `silvermedical-homepage`
- 상담 컨테이너 이름: `silvermedical-consultation`
- 알림 작업자 이름: `silvermedical-notification-worker`
- 내부망 접속 주소: `http://192.168.30.2:8080`
- 비공개 상담 접수: `http://192.168.30.2:8080/consult/`
- 직원 관리 화면: `http://192.168.30.2:8081/staff/` (내부망 비상 접속 주소)
- 직원 관리 HTTPS 주소: `https://staff.silvermedical.kr/staff/` (Cloudflare Access 설정 후 사용)

공개 홈페이지 포트 `8080`에서는 `/staff/`가 열리지 않습니다. 직원 관리 포트 `8081`은 내부망에서 직접 사용하거나, Cloudflare Access로 보호된 `staff.silvermedical.kr`을 통해서만 사용합니다.
- 재부팅 후 자동 실행: `restart: unless-stopped`

## 센터소식 게시판 사용 방법

- 공개 목록: `https://silvermedical.kr/news/`
- 작성 화면: `https://staff.silvermedical.kr/staff/center_news/post/`
- 분류: 공지사항, 센터 이야기, 영상 소식
- 작성 권한: 최고관리자 또는 `콘텐츠 담당자` 그룹에 지정된 직원만 작성·수정할 수 있습니다.
- 공개 상태가 `작성 중`인 글과 예약 시각 전 글은 홈페이지에 표시되지 않습니다.
- `공개`로 저장한 최신 글 3개는 홈페이지 첫 화면에도 자동으로 표시됩니다.
- 유튜브 영상 주소를 입력하면 상세 화면에서 바로 재생되고, 네이버 블로그 주소를 입력하면 새 창으로 연결됩니다.
- 대표 사진은 JPG·PNG·WebP 형식의 8MB 이하 파일을 사용합니다. 저장할 때 최대 1600px의 WebP 이미지로 자동 최적화됩니다.
- 대표 사진을 사용하는 경우 접근성을 위한 `사진 설명`을 반드시 입력해야 합니다.
- 공개 허가가 확인되지 않은 얼굴, 수급자 정보, 내부 문서가 보이는 사진은 등록하지 않습니다.

센터소식과 첨부 사진은 상담 데이터와 같은 Docker 영구 저장공간 `consultation_data`에 보관됩니다. 서버 백업 시 데이터베이스뿐 아니라 `/data/news-media`도 함께 포함해야 합니다. GitHub Pages만으로는 동적 게시판과 관리자 작성 기능이 작동하지 않으므로 운영 홈페이지는 현재 하모니카 서버 구성을 사용합니다.

`DJANGO_SECRET_KEY`는 저장소에 기록하지 않습니다. 서버의 `/home/silverhome/.config/silvermedical/django_secret_key` 파일에만 보관하며 파일 권한은 소유자 읽기 전용으로 설정합니다.

## Cloudflare Tunnel 운영

공개 도메인은 `compose.tunnel.yaml`을 추가로 사용합니다. Tunnel 토큰은 GitHub나 Compose 파일에 적지 않고 서버의 `/home/silverhome/.config/silvermedical/cloudflared-token`에 권한 `600`으로 보관합니다.

```bash
export DJANGO_SECRET_KEY="$(cat /home/silverhome/.config/silvermedical/django_secret_key)"
export DJANGO_ALLOWED_HOSTS="silvermedical.kr,www.silvermedical.kr,staff.silvermedical.kr,192.168.30.2,127.0.0.1,localhost"
export DJANGO_CSRF_TRUSTED_ORIGINS="https://silvermedical.kr,https://www.silvermedical.kr,https://staff.silvermedical.kr"
export DJANGO_SECURE_COOKIES="true"
export CLOUDFLARED_RUN_AS="$(id -u):$(id -g)"

docker compose -f compose.yaml -f compose.tunnel.yaml up -d --build
```

Cloudflare Tunnel의 홈페이지 서비스 주소는 `http://homepage:80`입니다. 직원 관리 HTTPS 주소는 별도 호스트 `staff.silvermedical.kr`을 `http://homepage:8081`로 연결하고, Cloudflare Access의 허용 이메일 정책을 먼저 적용한 뒤 사용합니다. Access 인증 정보가 없는 외부 관리자 요청은 nginx에서도 `403`으로 차단합니다.

## 상담 접수와 직원 관리

- 보호자 상담 접수: `https://silvermedical.kr/consult/`
- 직원 관리 화면: `https://staff.silvermedical.kr/staff/`
- 내부망 비상 접속: `http://192.168.30.2:8081/staff/`
- 직원 관리 화면은 공개 홈페이지 메뉴에 넣지 않고, 내부 업무용 즐겨찾기로 사용합니다.
- 상담 내용이 10자보다 짧으면 입력칸 아래에 이유와 최소 글자 수를 표시합니다.
- 접수 내용은 공개 게시판에 노출되지 않으며 직원 관리 화면에서만 확인합니다.
- 잠금화면과 카카오톡 알림에는 마스킹한 신청자 이름, 연락처 끝 4자리, 접수 시각만 표시하며 상담 원문은 보내지 않습니다.

## 상담 알림 문서

- [알림 시스템 구조](docs/NOTIFICATION_SYSTEM.md)
- [직원 PC·휴대전화 등록 안내](docs/STAFF_NOTIFICATION_GUIDE.md)
- [카카오톡 나에게 보내기 설정](docs/KAKAO_NOTIFICATION_SETUP.md)
- [서버 운영·장애 대응·백업](docs/NOTIFICATION_OPERATIONS.md)

## 식사·간식비 설정 방법

1. 직원 관리 화면에서 `현재 식사·간식비 설정`을 엽니다.
2. 현재 기관에서 적용하는 식사 1끼와 간식 1회 금액을 입력하고 저장합니다.
3. 이 금액은 기준연도와 관계없이 계산기의 모든 연도에 공통 적용됩니다.

## 연도별 급여수가 설정 방법

1. 직원 관리 HTTPS 주소에 로그인합니다. 내부망에서는 비상 접속 주소도 사용할 수 있습니다.
2. `급여비용 계산기 설정`의 `연도별 장기요양 급여수가`를 엽니다.
3. 새 연도는 직전 연도 자료를 열고 화면 아래의 `새로 저장`을 누른 뒤 기준연도와 적용 시작일을 변경합니다.
4. 공단 고시의 시설급여, 주야간보호, 방문요양 수가와 재가 월 한도액·감경률을 입력합니다.
5. 검토가 끝난 자료만 `홈페이지 공개`를 선택해 저장합니다.
6. 미래 연도 자료는 계산기에서 `(예정)`으로 표시되며, 적용일 전에는 현재 연도가 기본 선택됩니다.

공개된 설정은 `https://silvermedical.kr/benefits-data/`에서 계산기로 전달됩니다. 공식 수가와 비급여 단가는 저장 전 반드시 원문 고시와 기관 내부 결정 자료를 대조해야 합니다.

## 폴더 구조

```text
/
├─ index.html
├─ about.html
├─ services.html
├─ facility.html
├─ stories.html
├─ contact.html
├─ location.html
├─ 404.html
├─ sitemap.xml
├─ robots.txt
├─ favicon.ico
├─ style.css
├─ news.css
├─ script.js
├─ benefits.html
├─ benefits.css
├─ benefits.js
├─ README.md
├─ assets/
   ├─ image-sources.md
   └─ images/
      ├─ logo.png
      ├─ benefits-logo.jpg
      ├─ main-hero.jpg
      ├─ facility-lounge.jpg
      ├─ care-room.jpg
      ├─ dining-room.jpg
      ├─ bathroom.jpg
      ├─ gapo-massage.jpg
      ├─ meal-prep.jpg
      ├─ meal-event.jpg
      ├─ naver-map.png
      ├─ living-room.jpg
      ├─ floor-entrance.jpg
      └─ elevator.jpg
└─ backend/
   └─ center_news/
      ├─ models.py
      ├─ admin.py
      ├─ views.py
      └─ templates/center_news/
```

## 프로젝트 관리 기준

- Codex 작업 기준 프로젝트는 `C:\Users\jirlm\Documents\홈페이지`입니다.
- 별도 폴더였던 `감경률에 따른 한달 본인부담 계산`의 최신 계산기 파일은 이 홈페이지 프로젝트의 `benefits.html`, `benefits.css`, `benefits.js`로 흡수했습니다.
- 앞으로 홈페이지와 본인부담 계산기 수정은 이 프로젝트에서 함께 진행합니다.

## 반영 완료

- 네이버 블로그 링크: https://blog.naver.com/sil3307
- 주소: 충북 청주시 서원구 구룡산로375
- 전화번호: 043-298-8588
- 네이버 지도 링크: https://naver.me/FDntyyxE
- 카카오톡 채널: https://pf.kakao.com/_Kxjtxhn
- 유튜브 채널: https://www.youtube.com/@실버메디컬복지센터
- 기관명: 실버메디컬복지센터 노인요양원&재가
- 대표자: 연규항
- 고유번호증 번호: 301-80-34268
- 장기요양기관번호: 1-43110-00355 / 3-43110-00356
- 이메일: sil3307@naver.com
- 팩스: 043-235-8577

## 확인해야 할 TODO

- 시설장 사진을 사용할 경우 시설장 본인이 사진을 직접 지정
- 새로 추가하는 사진은 어르신·보호자·직원의 얼굴과 개인정보를 매번 확인
- 지도 iframe 삽입은 선택 사항입니다. 현재는 네이버 지도 링크로 연결되어 있습니다.
- 장기요양 급여비용 계산 수가와 감경률은 매년 고시 기준 변경 여부를 확인해야 합니다.

비밀번호, 토큰, API 키, `.env` 파일은 저장소에 올리지 마세요.

## 네이버 블로그 글 시험 이전

네이버 블로그 글은 다음 명령으로 `센터 이야기`의 작성 중 게시글로 가져옵니다. 같은 원문 주소가 이미 등록되어 있으면 중복 생성하지 않습니다.

```bash
python manage.py import_naver_blog --blog-id sil3307 --cutoff 2025-07-16 --limit 10
```

- `2025-07-16` 이후 글만 대상이며 해당 날짜를 포함합니다.
- 가져온 글은 자동 공개되지 않고 모두 `작성 중` 상태로 저장됩니다.
- 원문 작성일과 네이버 블로그 주소를 보존합니다.
- 작은 미리보기는 제외하고 본문에서 처음 확인되는 충분한 크기의 사진을 대표 사진으로 내려받습니다.
- 네이버 사진은 가로 966픽셀 화면용 원본을 요청한 뒤 서버에서 WebP로 최적화합니다.
- 관리자에서 여러 글을 한꺼번에 공개해도 네이버 원문 작성일이 홈페이지 게시일로 유지됩니다.
- 공개 전 어르신·보호자·직원 얼굴, 이름표, 문서와 개인정보 노출 여부를 반드시 확인합니다.
- 저장하지 않고 대상만 확인하려면 명령 끝에 `--dry-run`을 추가합니다.

## 센터소식과 직원자료실 운영

- 센터소식은 카드형과 목록형 보기 중 선택할 수 있으며 선택한 방식은 같은 브라우저에 저장됩니다.
- 게시글 상세 화면에서 이전 글, 목록, 다음 글로 이동할 수 있습니다.
- `영상소식`은 보호자와 방문자에게 공개할 유튜브 영상을 등록하는 공개 메뉴입니다.
- `직원 자료실`은 로그인한 직원만 열 수 있는 내부 자료 공간입니다. 업무안내, 교육자료, 서식, 내부 영상을 분류해 등록할 수 있습니다.
- 민감정보나 수급자 개인정보가 포함된 자료는 직원 자료실에도 올리지 말고 기존 내부 업무시스템에서 관리합니다.

## 관리자 바로가기

관리자 화면 첫 페이지에는 홈페이지, 새 게시글, 상담 접수함, 급여비용 설정, 알림, 직원 자료실로 이동하는 운영 바로가기가 표시됩니다.

Windows 바탕화면 바로가기는 프로젝트 폴더에서 다음 명령으로 만듭니다.

```powershell
.\install-admin-launcher.ps1
```

생성되는 `실버메디컬 관리센터` 바로가기는 Chrome 앱 창으로 직원 관리 화면을 엽니다. 비밀번호나 로그인 정보는 바로가기에 저장하지 않습니다.
