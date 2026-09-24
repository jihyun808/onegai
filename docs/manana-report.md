# manana 운영자 회신용 — 금영 데이터 누락 (2026-08-19 실측)

아래 본문을 그대로 복사해 Discord(https://discord.gg/dZFASsU)로 보내면 된다.

---

확인 감사합니다. 다만 오늘(2026-08-19) 다시 조회해보니 금영 데이터는 아직 갱신 전 상태로 보입니다.

**증상:** 금영 공식(kysing.kr)에는 있는 2024~2026년 등록곡이 API 응답에 없습니다. 가수명이 정확히 일치하는 곡만 센 결과입니다.

| 가수 | 금영 공식 | API 응답 | 누락 |
| --- | --- | --- | --- |
| Ado | 22 | 5 | 17 |
| ヨルシカ | 20 | 10 | 10 |
| 米津玄師 | 30 | 17 | 13 |
| YOASOBI | 26 | 17 | 9 |

**확인한 URL**

```
https://api.manana.kr/karaoke/singer/Ado/kumyoung.json
https://api.manana.kr/karaoke/singer/ヨルシカ/kumyoung.json
https://api.manana.kr/karaoke/singer/米津玄師/kumyoung.json
https://api.manana.kr/karaoke/singer/YOASOBI/kumyoung.json
```

대조에 쓴 금영 공식 검색 (category=7이 아티스트 검색):

```
https://kysing.kr/search/?category=7&keyword=Ado
```

**응답에 없는 금영 곡번호 (전부 2024~2026년 등록)**

```
Ado       76509 逆光 / 76515 私は最強 / 76533 向日葵 / 76547 世界のつづき / 57817 新時代
ヨルシカ   76526 斜陽 / 76542 忘れてください / 57807 火星人 / 57789 都落ち / 57754 DARMA GRAND PRIX
米津玄師   57822 BOW AND ARROW / 57796 M八七 / 57785 IRIS OUT / 57782 1991
YOASOBI   75932 HEART BEAT / 75979 UNDEAD / 76512 舞台に立って / 76524 モノトーン
```

**참고 사항**

- 금영 응답의 최신 출시일이 아이유 기준 `2024-05`이고, 2025년 등록곡은 확인한 가수 전체에서 0건입니다.
- 같은 시각 TJ는 `2026-07-30`, JOYSOUND는 `2026-08-07`까지 정상이라 금영만 멈춘 것으로 보입니다. **JOYSOUND는 말씀하신 대로 문제없이 최신입니다.**
- Ado `2026-03-01`, 米津玄師 `2026-09-01` 항목이 있긴 한데 곡번호가 5만번대 구곡이라 신규 등록은 아닌 듯합니다.

수집 오류를 고치셨다면 앞으로 들어올 데이터는 정상이겠지만, **오류가 나던 2024년 중반~2026년 8월 구간은 자동으로 채워지지 않을 것 같습니다.** 해당 기간 금영 재수집이 가능할지 확인 부탁드립니다.
