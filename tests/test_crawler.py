"""
크롤러 테스트
"""
import pytest
import asyncio
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from crawler import OliveYoungCrawler

class TestOliveYoungCrawler:
    """올리브영 크롤러 테스트 클래스"""
    
    def setup_method(self):
        """각 테스트 메소드 실행 전 설정"""
        self.temp_dir = tempfile.mkdtemp()
        self.output_file = str(Path(self.temp_dir) / "test_output.json")
        
        self.crawler = OliveYoungCrawler(
            max_concurrent=2,
            delay_range=(0.1, 0.2),  # 테스트용 짧은 딜레이
            output_file=self.output_file
        )
    
    def teardown_method(self):
        """각 테스트 메소드 실행 후 정리"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_init(self):
        """초기화 테스트"""
        assert self.crawler.max_concurrent == 2
        assert self.crawler.delay_range == (0.1, 0.2)
        assert self.crawler.output_file == self.output_file
        assert self.crawler.base_url == "https://www.oliveyoung.co.kr/store/goods/getGoodsDetail.do"
        assert self.crawler.stats['total'] == 0
        assert self.crawler.results == []
    
    @pytest.mark.asyncio
    async def test_create_browser_context(self):
        """브라우저 컨텍스트 생성 테스트"""
        mock_browser = Mock()
        mock_context = AsyncMock()
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        
        with patch('crawler.logger') as mock_logger:
            result = await self.crawler.create_browser_context(mock_browser)
        
        assert result == mock_context
        mock_browser.new_context.assert_called_once()
        mock_logger.info.assert_called_with("🌐 브라우저 컨텍스트 생성 중")
    
    @pytest.mark.asyncio
    async def test_check_product_availability_success(self):
        """상품 페이지 크롤링 성공 테스트"""
        mock_context = Mock()
        mock_page = AsyncMock()
        mock_response = Mock()
        mock_response.status = 200
        
        # Mock 설정
        mock_context.new_page = AsyncMock(return_value=mock_page)
        mock_page.goto = AsyncMock(return_value=mock_response)
        mock_page.title = AsyncMock(return_value="Test Product Title")
        mock_page.close = AsyncMock()
        
        with patch('asyncio.sleep', new_callable=AsyncMock):
            with patch('time.time', return_value=1000.0):
                with patch('time.strftime', return_value='2024-01-01 12:00:00'):
                    result = await self.crawler.check_product_availability(mock_context, "A123456")
        
        assert result is not None
        assert result['product_id'] == 'A123456'
        assert result['status_code'] == 200
        assert result['title'] == 'Test Product Title'
        mock_page.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_check_product_availability_no_response(self):
        """페이지 응답 없음 테스트"""
        mock_context = Mock()
        mock_page = AsyncMock()
        
        mock_context.new_page = AsyncMock(return_value=mock_page)
        mock_page.goto = AsyncMock(return_value=None)  # 응답 없음
        mock_page.close = AsyncMock()
        
        with patch('asyncio.sleep', new_callable=AsyncMock):
            with patch('crawler.logger') as mock_logger:
                result = await self.crawler.check_product_availability(mock_context, "A123456")
        
        assert result is None
        mock_logger.error.assert_called_with("❌ 페이지 응답 없음 (ID: A123456)")
        mock_page.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_check_product_availability_exception(self):
        """크롤링 중 예외 발생 테스트"""
        mock_context = Mock()
        mock_page = AsyncMock()
        
        mock_context.new_page = AsyncMock(return_value=mock_page)
        mock_page.goto = AsyncMock(side_effect=Exception("Test exception"))
        mock_page.close = AsyncMock()
        
        with patch('asyncio.sleep', new_callable=AsyncMock):
            with patch('crawler.logger') as mock_logger:
                result = await self.crawler.check_product_availability(mock_context, "A123456")
        
        assert result is None
        mock_logger.error.assert_called_with("❌ 크롤링 실패 (ID: A123456): Test exception")
        mock_page.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_save_results(self):
        """결과 저장 테스트"""
        # 테스트 결과 데이터 추가
        self.crawler.results = [
            {'product_id': 'A123456', 'title': 'Test Product 1'},
            {'product_id': 'A789012', 'title': 'Test Product 2'}
        ]
        self.crawler.stats = {
            'total': 2,
            'success': 2,
            'failed': 0
        }
        
        with patch('time.strftime', return_value='2024-01-01 12:00:00'):
            with patch('crawler.logger') as mock_logger:
                await self.crawler.save_results()
        
        # 파일이 저장되었는지 확인
        assert Path(self.output_file).exists()
        
        # 저장된 내용 확인
        with open(self.output_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        assert data['metadata']['total_crawled'] == 2
        assert len(data['products']) == 2
        assert data['products'][0]['product_id'] == 'A123456'
        
        mock_logger.info.assert_any_call(f"💾 결과 저장 중: {self.output_file}")
        mock_logger.info.assert_any_call(f"✅ 결과 저장 완료: {self.output_file}")
    
    @pytest.mark.asyncio
    async def test_save_results_exception(self):
        """결과 저장 중 예외 발생 테스트"""
        # 잘못된 경로로 저장 시도
        self.crawler.output_file = "/invalid/path/file.json"
        
        with patch('crawler.logger') as mock_logger:
            await self.crawler.save_results()
        
        mock_logger.error.assert_called()
    
    def test_stats_initialization(self):
        """통계 초기화 테스트"""
        expected_stats = {
            'total': 0,
            'success': 0,
            'failed': 0
        }
        
        assert self.crawler.stats == expected_stats
    
    @pytest.mark.asyncio
    async def test_crawl_products_integration(self):
        """크롤링 통합 테스트 (Mock 사용)"""
        test_product_ids = ["A123456", "A789012"]
        
        # playwright mock
        mock_playwright = AsyncMock()
        mock_browser = AsyncMock()
        mock_context = AsyncMock()
        
        mock_playwright.__aenter__ = AsyncMock(return_value=mock_playwright)
        mock_playwright.__aexit__ = AsyncMock(return_value=None)
        mock_playwright.chromium.launch = AsyncMock(return_value=mock_browser)
        
        mock_browser.__aenter__ = AsyncMock(return_value=mock_browser)
        mock_browser.__aexit__ = AsyncMock(return_value=None)
        
        with patch('crawler.async_playwright', return_value=mock_playwright):
            with patch.object(self.crawler, 'create_browser_context', return_value=mock_context):
                with patch.object(self.crawler, 'check_product_availability') as mock_crawl:
                    with patch.object(self.crawler, 'save_results') as mock_save:
                        with patch('time.time', return_value=1000.0):
                            with patch('crawler.logger'):
                                
                                # Mock check_product_availability 결과
                                mock_crawl.side_effect = [
                                    {'product_id': 'A123456', 'title': 'Product 1'},
                                    {'product_id': 'A789012', 'title': 'Product 2'}
                                ]
                                
                                result = await self.crawler.crawl_products(test_product_ids)
        
        assert result is not None
        assert result['stats']['total'] == 2
        assert result['stats']['success'] == 2
        assert len(result['results']) == 2
        mock_save.assert_called()
    
    @pytest.mark.parametrize("delay_range,expected_min,expected_max", [
        ((1, 3), 1, 3),
        ((0.5, 2.5), 0.5, 2.5),
        ((2, 5), 2, 5),
    ])
    def test_delay_range_configuration(self, delay_range, expected_min, expected_max):
        """딜레이 범위 설정 테스트"""
        crawler = OliveYoungCrawler(delay_range=delay_range)
        assert crawler.delay_range == (expected_min, expected_max)
    
    def test_base_url_configuration(self):
        """기본 URL 설정 테스트"""
        expected_url = "https://www.oliveyoung.co.kr/store/goods/getGoodsDetail.do"
        assert self.crawler.base_url == expected_url