# Makefile for Olive Young Crawler project

# 가상환경 및 의존성 설치
install:
	uv venv .venv
	source .venv/bin/activate && uv pip install -r requirements.txt
	source .venv/bin/activate && playwright install

# 개발용 의존성 설치
install-dev:
	uv venv .venv
	source .venv/bin/activate && uv pip install -r requirements-dev.txt
	source .venv/bin/activate && playwright install

# 테스트 실행 (가상환경 활성화 필요)
test:
	source .venv/bin/activate && pytest

# 테스트 실행 (상세 출력)
test-verbose:
	source .venv/bin/activate && pytest -v

# 테스트 실행 (커버리지 포함)
test-coverage:
	source .venv/bin/activate && pytest --cov=. --cov-report=html --cov-report=term

# 특정 테스트 실행
test-excel:
	source .venv/bin/activate && pytest tests/test_excel_processor.py -v

test-crawler:
	source .venv/bin/activate && pytest tests/test_crawler.py -v

test-main:
	source .venv/bin/activate && pytest tests/test_main_crawler.py -v

# 통합 테스트만 실행
test-integration:
	source .venv/bin/activate && pytest -m integration -v

# 단위 테스트만 실행  
test-unit:
	source .venv/bin/activate && pytest -m unit -v

# 느린 테스트 제외하고 실행
test-fast:
	source .venv/bin/activate && pytest -m "not slow" -v

# 코드 스타일 검사 (개발용 의존성 필요)
lint:
	source .venv/bin/activate && ruff check . || echo "ruff not installed, run 'make install-dev'"
	source .venv/bin/activate && black --check . || echo "black not installed, run 'make install-dev'"

# 코드 포매팅 (개발용 의존성 필요)
format:
	source .venv/bin/activate && ruff --fix . || echo "ruff not installed, run 'make install-dev'"
	source .venv/bin/activate && black . || echo "black not installed, run 'make install-dev'"

# 타입 체크 (개발용 의존성 필요)
typecheck:
	source .venv/bin/activate && mypy . || echo "mypy not installed, run 'make install-dev'"

# 전체 품질 검사
quality: lint typecheck

# 크롤러 실행
run:
	source .venv/bin/activate && python main.py $(filter-out $@,$(MAKECMDGOALS))

# 중단된 지점에서 크롤러 재시작
resume:
	source .venv/bin/activate && python main.py --resume

# 크롤링 결과 분석 (통계 + ID 추출)
analyze:
	source .venv/bin/activate && python analyze_results.py $(filter-out $@,$(MAKECMDGOALS))

# 크롤링 결과 통계만 확인 (파일 저장 없이)
analyze-stats:
	source .venv/bin/activate && python analyze_results.py --stats-only

# 업데이트용 Excel 파일 생성
generate-excel:
	source .venv/bin/activate && python generate_update_excel.py
	source .venv/bin/activate && python generate_delete_excel.py

# 테스트 데이터 생성
generate-test-data:
	uv run python -c "from tests.test_data.sample_qoo10_data import SampleDataGenerator; import tempfile; import os; temp = tempfile.mkdtemp(); file = SampleDataGenerator.create_test_excel_file(temp, 'basic'); print(f'Test data created: {file}')"

# 테스트 환경 정리
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name ".coverage" -delete
	rm -rf htmlcov/
	rm -rf .pytest_cache/
	rm -rf *.json

# 도움말
help:
	@echo "사용 가능한 명령어:"
	@echo "  install          - 의존성 설치"
	@echo "  test            - 모든 테스트 실행"
	@echo "  test-verbose    - 상세한 테스트 실행"
	@echo "  test-coverage   - 커버리지 포함 테스트 실행"
	@echo "  test-excel      - Excel 처리기 테스트"
	@echo "  test-crawler    - 크롤러 테스트"
	@echo "  test-main       - 메인 크롤러 테스트"
	@echo "  test-integration - 통합 테스트만 실행"
	@echo "  test-unit       - 단위 테스트만 실행"
	@echo "  test-fast       - 빠른 테스트만 실행"
	@echo "  lint            - 코드 스타일 검사"
	@echo "  format          - 코드 포매팅"
	@echo "  typecheck       - 타입 체크"
	@echo "  quality         - 전체 품질 검사"
	@echo "  run             - 크롤러 실행 (make run --resume 가능)"
	@echo "  resume          - 중단된 지점에서 크롤러 재시작"
	@echo "  analyze         - 크롤링 결과 분석 및 ID 추출"
	@echo "  analyze-stats   - 크롤링 결과 통계만 확인"
	@echo "  generate-excel  - 업데이트/삭제용 Excel 파일 생성 (output/ 폴더)"
	@echo "  clean           - 테스트 환경 정리"

# Make가 --resume을 파일명으로 인식하지 않도록 설정
%:
	@:

.PHONY: install test test-verbose test-coverage test-excel test-crawler test-main test-integration test-unit test-fast lint format typecheck quality run resume analyze analyze-stats generate-excel generate-test-data clean help