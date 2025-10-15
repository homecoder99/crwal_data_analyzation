"""
pytest 설정 및 공통 픽스처
"""
import pytest
import pandas as pd
import tempfile
import json
from pathlib import Path
from unittest.mock import Mock

@pytest.fixture
def temp_dir():
    """임시 디렉토리 픽스처"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    
    # 테스트 후 정리
    import shutil
    shutil.rmtree(temp_dir, ignore_errors=True)

@pytest.fixture
def sample_excel_data():
    """샘플 Excel 데이터 픽스처"""
    return {
        'seller_unique_item_id': [
            'A123456789',
            'A987654321', 
            'B111111111',  # B로 시작 - 필터링되어야 함
            'A555555555',
            'C222222222',  # C로 시작 - 필터링되어야 함
            'A777777777',
            None,  # null 값 - 필터링되어야 함
            'a888888888',  # 소문자 a - 필터링되어야 함
        ],
        'product_name': [
            '테스트 상품 1',
            '테스트 상품 2',
            '테스트 상품 3',
            '테스트 상품 4',
            '테스트 상품 5',
            '테스트 상품 6',
            '테스트 상품 7',
            '테스트 상품 8',
        ],
        'price': [
            10000,
            20000,
            15000,
            30000,
            25000,
            18000,
            12000,
            22000,
        ]
    }

@pytest.fixture
def sample_excel_file(temp_dir, sample_excel_data):
    """샘플 Excel 파일 픽스처"""
    excel_path = Path(temp_dir) / "sample_data.xlsx"
    df = pd.DataFrame(sample_excel_data)
    df.to_excel(excel_path, index=False)
    return str(excel_path)

@pytest.fixture
def invalid_excel_file(temp_dir):
    """잘못된 Excel 파일 픽스처"""
    invalid_path = Path(temp_dir) / "invalid.xlsx"
    with open(invalid_path, 'w') as f:
        f.write("This is not an Excel file")
    return str(invalid_path)

@pytest.fixture
def empty_excel_file(temp_dir):
    """빈 Excel 파일 픽스처"""
    empty_path = Path(temp_dir) / "empty.xlsx"
    df = pd.DataFrame()
    df.to_excel(empty_path, index=False)
    return str(empty_path)

@pytest.fixture
def excel_without_required_column(temp_dir):
    """필수 컬럼이 없는 Excel 파일 픽스처"""
    excel_path = Path(temp_dir) / "no_required_column.xlsx"
    df = pd.DataFrame({
        'wrong_column': ['A123456', 'B789012'],
        'another_column': ['value1', 'value2']
    })
    df.to_excel(excel_path, index=False)
    return str(excel_path)

@pytest.fixture
def expected_filtered_ids():
    """예상되는 필터링 결과 픽스처"""
    return ['A123456789', 'A987654321', 'A555555555', 'A777777777']

@pytest.fixture
def sample_crawler_results():
    """샘플 크롤러 결과 픽스처"""
    return [
        {
            'product_id': 'A123456789',
            'url': 'https://www.oliveyoung.co.kr/store/goods/getGoodsDetail.do?goodsNo=A123456789',
            'title': '올리브영 테스트 상품 1',
            'product_name': '프리미엄 스킨케어 세트',
            'price': '29,900원',
            'status_code': 200,
            'crawl_time': 2.5,
            'timestamp': '2024-01-01 12:00:00'
        },
        {
            'product_id': 'A987654321',
            'url': 'https://www.oliveyoung.co.kr/store/goods/getGoodsDetail.do?goodsNo=A987654321',
            'title': '올리브영 테스트 상품 2',
            'product_name': '천연 화장품 세트',
            'price': '19,900원',
            'status_code': 200,
            'crawl_time': 1.8,
            'timestamp': '2024-01-01 12:00:05'
        }
    ]

@pytest.fixture
def sample_crawler_stats():
    """샘플 크롤러 통계 픽스처"""
    return {
        'total': 4,
        'success': 3,
        'failed': 1
    }

@pytest.fixture
def sample_output_file(temp_dir, sample_crawler_results, sample_crawler_stats):
    """샘플 출력 파일 픽스처"""
    output_path = Path(temp_dir) / "sample_output.json"
    
    output_data = {
        'metadata': {
            'total_crawled': len(sample_crawler_results),
            'stats': sample_crawler_stats,
            'timestamp': '2024-01-01 12:05:00'
        },
        'products': sample_crawler_results
    }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    return str(output_path)

@pytest.fixture
def mock_playwright_browser():
    """Mock Playwright 브라우저 픽스처"""
    mock_browser = Mock()
    mock_context = Mock()
    mock_page = Mock()
    
    # 비동기 메서드들을 AsyncMock으로 설정
    from unittest.mock import AsyncMock
    
    mock_browser.new_context = AsyncMock(return_value=mock_context)
    mock_browser.close = AsyncMock()
    
    mock_context.new_page = AsyncMock(return_value=mock_page)
    mock_context.close = AsyncMock()
    
    mock_page.goto = AsyncMock()
    mock_page.title = AsyncMock(return_value="Test Page Title")
    mock_page.query_selector = AsyncMock(return_value=None)
    mock_page.text_content = AsyncMock(return_value="Test Content")
    mock_page.close = AsyncMock()
    
    return {
        'browser': mock_browser,
        'context': mock_context,
        'page': mock_page
    }

@pytest.fixture
def mock_response():
    """Mock HTTP 응답 픽스처"""
    response = Mock()
    response.status = 200
    response.url = "https://www.oliveyoung.co.kr/store/goods/getGoodsDetail.do?goodsNo=A123456"
    return response

# 테스트 설정
pytest_plugins = []

def pytest_configure(config):
    """pytest 설정"""
    config.addinivalue_line(
        "markers", "asyncio: 비동기 테스트를 위한 마커"
    )
    config.addinivalue_line(
        "markers", "slow: 느린 테스트를 위한 마커"
    )
    config.addinivalue_line(
        "markers", "integration: 통합 테스트를 위한 마커"
    )

def pytest_collection_modifyitems(config, items):
    """테스트 항목 수정"""
    for item in items:
        # 비동기 테스트 자동 마킹
        if "asyncio" in item.fixturenames:
            item.add_marker(pytest.mark.asyncio)
        
        # 통합 테스트 자동 마킹
        if "integration" in item.name or "test_main" in item.parent.name:
            item.add_marker(pytest.mark.integration)