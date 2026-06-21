# 실버메디컬복지센터 홈페이지

실버메디컬복지센터 공식 홈페이지와 장기요양 급여비용 계산기를 함께 관리하는 정적 웹사이트입니다.

요양원, 주간보호, 방문요양, 단기보호, 통합재가 서비스를 보호자가 한눈에 이해할 수 있도록 구성했고, `benefits.html` 하위페이지에서 감경률에 따른 한 달 예상 본인부담금을 계산할 수 있습니다.

## 로컬에서 여는 방법

Windows 파일 탐색기에서 아래 파일을 더블클릭하면 바로 확인할 수 있습니다.

```powershell
C:\Users\jirlm\Documents\홈페이지\index.html
C:\Users\jirlm\Documents\홈페이지\benefits.html
```

또는 VS Code에서 Live Server 확장을 사용해 미리볼 수 있습니다.

## 배포

- GitHub Pages 배포 가능
- Cloudflare Pages 배포 가능
- GitHub 저장소 이름: `silvermedical-homepage`
- 공개 주소: `https://a01074443588-lgtm.github.io/silvermedical-homepage/`

## 폴더 구조

```text
/
├─ index.html
├─ style.css
├─ script.js
├─ benefits.html
├─ benefits.css
├─ benefits.js
├─ README.md
└─ assets/
   ├─ image-sources.md
   └─ images/
      ├─ logo.png
      ├─ benefits-logo.jpg
      ├─ main-hero.jpg
      ├─ facility-lounge.jpg
      ├─ care-room.jpg
      ├─ care-bedroom.jpg
      ├─ dining-room.jpg
      ├─ bathroom.jpg
      ├─ gapo-massage.jpg
      ├─ meal-prep.jpg
      ├─ naver-map.png
      └─ program-room-polished.jpg
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
- 기관명: 실버메디컬복지센터 노인요양원&재가
- 대표자: 연규항
- 사업자등록번호: 301-80-34268
- 장기요양기관번호: 1-43110-00355 / 3-43110-00356
- 이메일: sil3307@naver.com
- 팩스: 043-235-8577

## 확인해야 할 TODO

- 공개 가능한 사진 최종 확인
- `og:image` 경로를 배포 주소에 맞게 확인
- 지도 iframe 삽입은 선택 사항입니다. 현재는 네이버 지도 링크로 연결되어 있습니다.
- 장기요양 급여비용 계산 수가와 감경률은 매년 고시 기준 변경 여부를 확인해야 합니다.

비밀번호, 토큰, API 키, `.env` 파일은 저장소에 올리지 마세요.
