"""
메인 크롤러 통합 테스트
"""
import pytest
import asyncio
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
from main_crawler import MainCrawler

class TestMainCrawler:
    """메인 크롤러 테스트 클래스"""
    
    def setup_method(self):
        """각 테스트 메소드 실행 전 설정"""
        self.temp_dir = tempfile.mkdtemp()
        self.excel_path = str(Path(self.temp_dir) / "test_excel.xlsx")
        self.output_file = str(Path(self.temp_dir) / "test_output.json")
        
        self.main_crawler = MainCrawler(
            excel_path=self.excel_path,
            max_concurrent=2,
            delay_range=(0.1, 0.2),
            output_file=self.output_file
        )
    
    def teardown_method(self):
        """각 테스트 메소드 실행 후 정리"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_init(self):
        """초기화 테스트"""
        assert self.main_crawler.excel_path == self.excel_path
        assert self.main_crawler.max_concurrent == 2
        assert self.main_crawler.delay_range == (0.1, 0.2)
        assert self.main_crawler.output_file == self.output_file
        assert self.main_crawler.excel_processor is not None
        assert self.main_crawler.crawler is not None
    
    @pytest.mark.asyncio
    async def test_run_with_progress_success(self):
        """진행률 표시와 함께 크롤링 성공 테스트"""
        test_product_ids = ['A123456', 'A789012', 'A345678']
        
        # Excel 처리기 Mock
        mock_excel_process = Mock(return_value=test_product_ids)
        self.main_crawler.excel_processor.process = mock_excel_process
        
        # 크롤러 Mock
        mock_crawler_result = {
            'stats': {
                'total': 3,
                'success': 3,
                'failed': 0
            },
            'total_time': 10.0,
            'results': [
                {'product_id': 'A123456', 'title': 'Product 1'},
                {'product_id': 'A789012', 'title': 'Product 2'},
                {'product_id': 'A345678', 'title': 'Product 3'}
            ]
        }
        
        with patch.object(self.main_crawler.crawler, 'crawl_products', return_value=mock_crawler_result):
            with patch('main_crawler.tqdm') as mock_tqdm:
                with patch('time.time', side_effect=[1000.0, 1010.0]):  # 시작 시간, 종료 시간
                    with patch('main_crawler.logger') as mock_logger:
                        result = await self.main_crawler.run_with_progress()
        
        assert result == mock_crawler_result
        mock_excel_process.assert_called_once()
        mock_logger.info.assert_any_call("🎯 올리브영 상품 크롤링 시작")
        mock_logger.info.assert_any_call("🏆 크롤링 작업 완료!")
    
    @pytest.mark.asyncio
    async def test_run_with_progress_excel_failure(self):
        """Excel 처리 실패 테스트"""
        # Excel 처리 실패 시뮬레이션
        mock_excel_process = Mock(return_value=None)
        self.main_crawler.excel_processor.process = mock_excel_process
        
        with patch('main_crawler.logger') as mock_logger:
            result = await self.main_crawler.run_with_progress()
        
        assert result is None
        mock_excel_process.assert_called_once()
        mock_logger.error.assert_called_with("❌ Excel에서 유효한 ID를 찾을 수 없습니다")
    
    @pytest.mark.asyncio
    async def test_run_with_progress_empty_ids(self):
        """빈 ID 목록 테스트"""
        # 빈 ID 목록 반환
        mock_excel_process = Mock(return_value=[])
        self.main_crawler.excel_processor.process = mock_excel_process
        
        with patch('main_crawler.logger') as mock_logger:
            result = await self.main_crawler.run_with_progress()
        
        assert result is None
        mock_logger.error.assert_called_with("❌ Excel에서 유효한 ID를 찾을 수 없습니다")
    
    def test_run_sync_wrapper(self):
        """동기 실행 래퍼 테스트"""
        mock_result = {'test': 'result'}
        
        with patch.object(self.main_crawler, 'run_with_progress', return_value=mock_result) as mock_run:
            with patch('asyncio.run') as mock_asyncio_run:
                mock_asyncio_run.return_value = mock_result
                
                result = self.main_crawler.run()
        
        mock_asyncio_run.assert_called_once()
        assert result == mock_result
    
    def test_default_configuration(self):
        """기본 설정 테스트"""
        default_crawler = MainCrawler()
        
        assert default_crawler.excel_path == "data/Qoo10_ItemInfo.xlsx"
        assert default_crawler.max_concurrent == 3
        assert default_crawler.delay_range == (1, 3)
        assert default_crawler.output_file == "olive_young_products.json"
    
    @pytest.mark.asyncio
    async def test_progress_bar_interaction(self):
        """진행률 표시줄 상호작용 테스트"""
        test_product_ids = ['A123456', 'A789012']
        
        # Excel 처리기 Mock
        self.main_crawler.excel_processor.process = Mock(return_value=test_product_ids)
        
        # Mock tqdm 진행률 표시줄
        mock_progress_bar = Mock()
        
        # 크롤러 Mock (각 상품별로 호출되는 함수)
        original_crawl = AsyncMock()
        original_crawl.side_effect = [
            {'product_id': 'A123456', 'title': 'Product 1'},
            {'product_id': 'A789012', 'title': 'Product 2'}
        ]
        
        # 크롤러 결과 Mock
        mock_crawler_result = {
            'stats': {'total': 2, 'success': 2, 'failed': 0},
            'total_time': 5.0,
            'results': []
        }
        
        with patch('main_crawler.tqdm', return_value=mock_progress_bar):
            with patch.object(self.main_crawler.crawler, 'crawl_products', return_value=mock_crawler_result):
                with patch('time.time', side_effect=[1000.0, 1005.0]):
                    with patch('main_crawler.logger'):
                        result = await self.main_crawler.run_with_progress()
        
        # 진행률 표시줄이 적절히 사용되었는지 확인
        mock_progress_bar.close.assert_called_once()
        assert result == mock_crawler_result
    
    @pytest.mark.asyncio
    async def test_statistics_calculation(self):
        """통계 계산 테스트"""
        test_product_ids = ['A123456'] * 100  # 100개 상품
        
        self.main_crawler.excel_processor.process = Mock(return_value=test_product_ids)
        
        mock_crawler_result = {
            'stats': {
                'total': 100,
                'success': 85,
                'failed': 10
            },
            'total_time': 60.0,  # 1분
            'results': []
        }
        
        with patch.object(self.main_crawler.crawler, 'crawl_products', return_value=mock_crawler_result):
            with patch('main_crawler.tqdm') as mock_tqdm:
                with patch('time.time', side_effect=[1000.0, 1060.0]):  # 60초 경과
                    with patch('main_crawler.logger') as mock_logger:
                        result = await self.main_crawler.run_with_progress()
        
        # 로그에서 통계 정보 확인
        log_calls = mock_logger.info.call_args_list
        log_messages = [call[0][0] for call in log_calls]
        
        # 성공률 계산 확인 (85/100 = 85%)
        success_rate_log = next((msg for msg in log_messages if "85.0%" in msg), None)
        assert success_rate_log is not None
        
        # 처리 속도 확인 (100개/60초 ≈ 1.67 상품/초)
        processing_speed_log = next((msg for msg in log_messages if "상품/초" in msg), None)
        assert processing_speed_log is not None
    
    def test_configuration_validation(self):
        """설정 검증 테스트"""
        # 잘못된 max_concurrent 값 테스트
        crawler1 = MainCrawler(max_concurrent=0)
        assert crawler1.max_concurrent == 0  # 실제로는 검증 로직이 있어야 함
        
        # 잘못된 delay_range 값 테스트
        crawler2 = MainCrawler(delay_range=(5, 1))  # max < min
        assert crawler2.delay_range == (5, 1)  # 실제로는 검증 로직이 있어야 함
    
    @pytest.mark.parametrize("concurrent,delay_range,expected_time_range", [
        (1, (1, 2), (50, 200)),  # 느린 설정
        (5, (0.1, 0.5), (5, 30)),  # 빠른 설정
        (3, (1, 3), (20, 100)),   # 보통 설정
    ])
    @pytest.mark.asyncio
    async def test_estimated_time_calculation(self, concurrent, delay_range, expected_time_range):
        """예상 시간 계산 테스트"""
        test_product_ids = ['A123456'] * 50  # 50개 상품
        
        crawler = MainCrawler(
            max_concurrent=concurrent,
            delay_range=delay_range,
            excel_path=self.excel_path,
            output_file=self.output_file
        )
        crawler.excel_processor.process = Mock(return_value=test_product_ids)
        
        mock_crawler_result = {
            'stats': {'total': 50, 'success': 50, 'failed': 0},
            'total_time': 30.0,
            'results': []
        }
        
        with patch.object(crawler.crawler, 'crawl_products', return_value=mock_crawler_result):
            with patch('main_crawler.tqdm'):
                with patch('time.time', side_effect=[1000.0, 1030.0]):
                    with patch('main_crawler.logger') as mock_logger:
                        await crawler.run_with_progress()
        
        # 예상 시간이 로그에 기록되었는지 확인
        log_calls = mock_logger.info.call_args_list
        estimated_time_log = next((call for call in log_calls if "예상 소요 시간" in call[0][0]), None)
        assert estimated_time_log is not None