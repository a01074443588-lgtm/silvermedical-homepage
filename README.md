# 실버메디컬복지센터 랜딩페이지

실버메디컬복지센터 공식 홈페이지 제작을 위한 정적 랜딩페이지입니다.

요양원, 주간보호, 방문요양, 단기보호, 통합재가 서비스를 보호자가 한눈에 이해할 수 있도록 구성했습니다. 처음 실습과 배포가 쉽도록 `index.html`, `style.css`, `script.js` 중심의 단순한 정적 웹사이트로 만들었습니다.

## 로컬에서 여는 방법

Windows 파일 탐색기에서 아래 파일을 더블클릭하면 바로 확인할 수 있습니다.

```powershell
C:\Users\jirlm\Documents\홈페이지\index.html
```

또는 VS Code에서 Live Server 확장을 사용해 미리볼 수 있습니다.

## 배포 예정

- GitHub Pages 배포 가능
- Cloudflare Pages 배포 가능
- 추천 GitHub 저장소 이름: `silvermedical-homepage`

## 폴더 구조

```text
/
├─ index.html
├─ style.css
├─ script.js
├─ README.md
└─ assets/
   ├─ image-sources.md
   └─ images/
      ├─ logo.png
      ├─ main-hero.jpg
      ├─ facility-lounge.jpg
      ├─ care-room.jpg
      ├─ rest-room.jpg
      ├─ dining-room.jpg
      ├─ bathroom.jpg
      ├─ rehab-equipment.jpg
      └─ care-bedroom.jpg
```

## GitHub에 올리기 전 TODO

- 공개 가능한 사진 최종 확인
- `og:image` 경로를 배포 주소에 맞게 확인
- 지도 iframe 삽입은 선택 사항입니다. 현재는 네이버 지도 링크로 연결되어 있습니다.

## 반영 완료

- 네이버 블로그 링크: https://blog.naver.com/sil3307
- 주소: 충북 청주시 서원구 구룡산로375
- 전화번호: 043-298-8588
- 네이버 지도 링크: https://naver.me/FDntyyxE
- 카카오톡 채널: https://pf.kakao.com/_Kxjtxhn
- 기관명: 실버메디컬복지센터 노인요양원&재가
- 대표자: 연규항
- 사업자등록번호: 301-80-34268
- 장기요양기관번호: 1-43110-00355 / 3-43110-00356
- 이메일: sil3307@naver.com
- 팩스: 043-235-8577

## Git 시작 명령 예시

Git이 초기화되어 있지 않은 경우:

```powershell
git init
git add .
git commit -m "Initial landing page for Silver Medical Welfare Center"
```

GitHub 원격 저장소를 만든 뒤:

```powershell
git remote add origin https://github.com/계정명/silvermedical-homepage.git
git branch -M main
git push -u origin main
```

비밀번호, 토큰, API 키, `.env` 파일은 저장소에 올리지 마세요.
