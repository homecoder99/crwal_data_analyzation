# 🌟 올리브영 상품 크롤러

Excel 파일에서 상품 ID를 추출하여 올리브영 사이트를 크롤링하는 도구입니다.

## 📋 주요 기능

- **Excel 데이터 처리**: Qoo10 아이템 정보에서 'A'로 시작하는 ID만 필터링
- **CloudFlare 우회**: 헤드풀 브라우저와 스텔스 설정으로 차단 방지
- **상품 판매 상태 확인**: 정상 판매 중인 상품과 판매 종료된 상품 구분
- **진행률 시각화**: tqdm을 활용한 실시간 크롤링 진행상황 표시
- **상세 로깅**: 모든 과정의 콘솔 출력과 성공/실패 통계
- **안전한 크롤링**: 적절한 딜레이와 동시 실행 수 제한
- **결과 저장**: JSON 형태로 크롤링 데이터 저장

## 🚀 설치 및 실행

### 1. 의존성 설치

```bash
# 기본 설치
make install

# 개발용 설치 (코드 품질 도구 포함)
make install-dev
```

또는 수동으로:

```bash
# 가상환경 생성
uv venv .venv

# 가상환경 활성화 및 의존성 설치
source .venv/bin/activate
uv pip install -r requirements.txt

# Playwright 브라우저 설치
playwright install
```

### 2. 데이터 준비

`data/Qoo10_ItemInfo.xlsx` 파일을 프로젝트 루트에 준비하세요.

- 파일에는 `seller_unique_item_id` 컬럼이 있어야 합니다.
- 대문자 'A'로 시작하는 ID만 처리됩니다.

### 3. 크롤링 실행

```bash
# 크롤러 실행
make run

# 또는 직접 실행
source .venv/bin/activate
python main.py
```

## 🧪 테스트

```bash
# 전체 테스트 실행
make test

# 상세한 테스트 결과
make test-verbose

# 커버리지 포함 테스트
make test-coverage

# 특정 모듈 테스트
make test-excel      # Excel 처리기만
make test-crawler    # 크롤러만
make test-main       # 메인 크롤러만
```

## 📁 프로젝트 구조

```
marketfit_test/
├── data/
│   └── Qoo10_ItemInfo.xlsx     # 입력 Excel 파일
├── tests/                      # 테스트 파일들
│   ├── test_excel_processor.py
│   ├── test_crawler.py
│   └── test_main_crawler.py
├── excel_processor.py          # Excel 데이터 처리
├── crawler.py                  # 올리브영 크롤러
├── main_crawler.py            # 메인 실행기
├── main.py                    # 진입점
├── requirements.txt           # 의존성
└── Makefile                   # 실행 명령어
```

## ⚙️ 설정

### 크롤링 설정

`main_crawler.py`에서 다음 설정을 변경할 수 있습니다:

- `max_concurrent`: 동시 실행 수 (기본값: 3)
- `delay_range`: 요청 간 딜레이 범위 (기본값: 2-4초)
- `output_file`: 결과 파일명 (기본값: olive_young_products.json)

### 예시 설정

```python
config = {
    'excel_path': 'data/Qoo10_ItemInfo.xlsx',
    'max_concurrent': 5,        # 더 빠른 크롤링 (차단 위험 증가)
    'delay_range': (1, 2),      # 더 짧은 딜레이 (차단 위험 증가)
    'output_file': 'results.json'
}
```

## 📊 결과 파일 형식

크롤링 결과는 다음과 같은 JSON 형식으로 저장됩니다:

```json
{
  "metadata": {
    "total_crawled": 150,
    "stats": {
      "total": 200,
      "success": 150,
      "failed": 45
    },
    "timestamp": "2024-01-01 12:00:00"
  },
  "products": [
    {
      "product_id": "A123456789",
      "url": "https://www.oliveyoung.co.kr/store/goods/getGoodsDetail.do?goodsNo=A123456789",
      "title": "상품 페이지 제목",
      "product_status": "saleOn",
      "status_code": 200,
      "crawl_time": 2.5,
      "timestamp": "2024-01-01 12:00:05"
    },
    {
      "product_id": "A987654321",
      "url": "https://www.oliveyoung.co.kr/store/goods/getGoodsDetail.do?goodsNo=A987654321",
      "title": "상품 페이지 제목",
      "product_status": "soldOut",
      "soldout_reason": "button_hidden",
      "status_code": 200,
      "crawl_time": 1.8,
      "timestamp": "2024-01-01 12:00:07"
    }
  ]
}
```

## 🛡️ 주의사항

1. **속도 제한**: CloudFlare 차단을 피하기 위해 적절한 딜레이를 설정하세요.
2. **동시 실행**: 너무 많은 동시 요청은 차단을 유발할 수 있습니다.
3. **데이터 백업**: 크롤링 도중 중단될 수 있으므로 중간 저장 기능을 활용하세요.
4. **법적 준수**: 사이트 이용약관과 robots.txt를 준수하여 사용하세요.

## 🤝 기여하기

1. 이슈 리포트: 버그나 개선사항을 제보해주세요
2. 코드 품질: `make quality` 명령어로 코드 품질을 확인하세요
3. 테스트: 새로운 기능 추가 시 테스트 코드도 함께 작성해주세요

## 📝 라이선스

이 프로젝트는 교육 및 연구 목적으로만 사용하세요.
