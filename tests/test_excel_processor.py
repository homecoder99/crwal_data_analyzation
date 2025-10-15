"""
Excel 처리기 테스트
"""
import pytest
import pandas as pd
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
from excel_processor import ExcelProcessor

class TestExcelProcessor:
    """Excel 처리기 테스트 클래스"""
    
    def setup_method(self):
        """각 테스트 메소드 실행 전 설정"""
        self.temp_dir = tempfile.mkdtemp()
        self.test_excel_path = Path(self.temp_dir) / "test_data.xlsx"
    
    def teardown_method(self):
        """각 테스트 메소드 실행 후 정리"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def create_test_excel(self, data):
        """테스트용 Excel 파일 생성"""
        df = pd.DataFrame(data)
        df.to_excel(self.test_excel_path, index=False)
        return str(self.test_excel_path)
    
    def test_init(self):
        """초기화 테스트"""
        processor = ExcelProcessor("test_path.xlsx")
        assert processor.excel_path == Path("test_path.xlsx")
        assert processor.df is None
        assert processor.filtered_ids == []
    
    def test_load_excel_success(self):
        """Excel 파일 로드 성공 테스트"""
        # 테스트 데이터 생성
        test_data = {
            'seller_unique_item_id': ['A123456', 'B789012', 'A345678'],
            'product_name': ['상품1', '상품2', '상품3']
        }
        excel_path = self.create_test_excel(test_data)
        
        processor = ExcelProcessor(excel_path)
        result = processor.load_excel()
        
        assert result is True
        assert processor.df is not None
        assert len(processor.df) == 3
        assert list(processor.df.columns) == ['seller_unique_item_id', 'product_name']
    
    def test_load_excel_file_not_found(self):
        """존재하지 않는 Excel 파일 로드 테스트"""
        processor = ExcelProcessor("nonexistent_file.xlsx")
        
        with patch('excel_processor.logger') as mock_logger:
            result = processor.load_excel()
            
        assert result is False
        mock_logger.error.assert_called()
    
    def test_load_excel_invalid_file(self):
        """잘못된 Excel 파일 로드 테스트"""
        # 잘못된 파일 생성
        invalid_file = Path(self.temp_dir) / "invalid.xlsx"
        with open(invalid_file, 'w') as f:
            f.write("This is not an Excel file")
        
        processor = ExcelProcessor(str(invalid_file))
        
        with patch('excel_processor.logger') as mock_logger:
            result = processor.load_excel()
            
        assert result is False
        mock_logger.error.assert_called()
    
    def test_validate_columns_success(self):
        """컬럼 검증 성공 테스트"""
        test_data = {
            'seller_unique_item_id': ['A123456'],
            'other_column': ['value1']
        }
        excel_path = self.create_test_excel(test_data)
        
        processor = ExcelProcessor(excel_path)
        processor.load_excel()
        
        with patch('excel_processor.logger') as mock_logger:
            result = processor.validate_columns()
            
        assert result is True
        mock_logger.info.assert_called()
    
    def test_validate_columns_missing_column(self):
        """필수 컬럼 누락 테스트"""
        test_data = {
            'wrong_column': ['A123456'],
            'other_column': ['value1']
        }
        excel_path = self.create_test_excel(test_data)
        
        processor = ExcelProcessor(excel_path)
        processor.load_excel()
        
        with patch('excel_processor.logger') as mock_logger:
            result = processor.validate_columns()
            
        assert result is False
        mock_logger.error.assert_called()
    
    def test_filter_ids_starting_with_a(self):
        """'A'로 시작하는 ID 필터링 테스트"""
        test_data = {
            'seller_unique_item_id': [
                'A123456',  # 포함되어야 함
                'B789012',  # 제외되어야 함
                'A345678',  # 포함되어야 함
                'a999999',  # 제외되어야 함 (소문자)
                'C111111',  # 제외되어야 함
                'A567890'   # 포함되어야 함
            ]
        }
        excel_path = self.create_test_excel(test_data)
        
        processor = ExcelProcessor(excel_path)
        processor.load_excel()
        
        filtered_ids = processor.filter_ids_starting_with_a()
        
        expected_ids = ['A123456', 'A345678', 'A567890']
        assert filtered_ids == expected_ids
        assert len(filtered_ids) == 3
    
    def test_filter_ids_with_null_values(self):
        """null 값이 포함된 데이터에서 ID 필터링 테스트"""
        test_data = {
            'seller_unique_item_id': [
                'A123456',
                None,
                'A345678',
                pd.NA,
                'B789012',
                'A567890'
            ]
        }
        excel_path = self.create_test_excel(test_data)
        
        processor = ExcelProcessor(excel_path)
        processor.load_excel()
        
        filtered_ids = processor.filter_ids_starting_with_a()
        
        expected_ids = ['A123456', 'A345678', 'A567890']
        assert filtered_ids == expected_ids
        assert len(filtered_ids) == 3
    
    def test_filter_ids_no_matches(self):
        """'A'로 시작하는 ID가 없는 경우 테스트"""
        test_data = {
            'seller_unique_item_id': ['B123456', 'C789012', 'D345678']
        }
        excel_path = self.create_test_excel(test_data)
        
        processor = ExcelProcessor(excel_path)
        processor.load_excel()
        
        with patch('excel_processor.logger') as mock_logger:
            filtered_ids = processor.filter_ids_starting_with_a()
            
        assert filtered_ids == []
        mock_logger.warning.assert_called()
    
    def test_get_filtered_ids(self):
        """필터링된 ID 반환 테스트"""
        processor = ExcelProcessor("test.xlsx")
        processor.filtered_ids = ['A123456', 'A789012']
        
        result = processor.get_filtered_ids()
        
        assert result == ['A123456', 'A789012']
    
    def test_process_success(self):
        """전체 처리 과정 성공 테스트"""
        test_data = {
            'seller_unique_item_id': ['A123456', 'B789012', 'A345678'],
            'product_name': ['상품1', '상품2', '상품3']
        }
        excel_path = self.create_test_excel(test_data)
        
        processor = ExcelProcessor(excel_path)
        
        with patch('excel_processor.logger') as mock_logger:
            result = processor.process()
            
        expected_ids = ['A123456', 'A345678']
        assert result == expected_ids
        mock_logger.info.assert_any_call("🚀 Excel 데이터 처리 시작")
        mock_logger.info.assert_any_call(f"✅ Excel 처리 완료. {len(expected_ids)}개 ID 처리 준비됨")
    
    def test_process_load_failure(self):
        """Excel 로드 실패 시 처리 테스트"""
        processor = ExcelProcessor("nonexistent.xlsx")
        
        result = processor.process()
        
        assert result is None
    
    def test_process_validation_failure(self):
        """컬럼 검증 실패 시 처리 테스트"""
        test_data = {
            'wrong_column': ['A123456']
        }
        excel_path = self.create_test_excel(test_data)
        
        processor = ExcelProcessor(excel_path)
        
        result = processor.process()
        
        assert result is None
    
    def test_process_no_valid_ids(self):
        """유효한 ID가 없는 경우 처리 테스트"""
        test_data = {
            'seller_unique_item_id': ['B123456', 'C789012']
        }
        excel_path = self.create_test_excel(test_data)
        
        processor = ExcelProcessor(excel_path)
        
        with patch('excel_processor.logger') as mock_logger:
            result = processor.process()
            
        assert result is None
        mock_logger.warning.assert_any_call("⚠️  처리할 유효한 ID가 없습니다")

    @pytest.mark.parametrize("test_input,expected", [
        (['A123456', 'A789012'], ['A123456', 'A789012']),
        (['A123456', 'B789012', 'A345678'], ['A123456', 'A345678']),
        (['B123456', 'C789012'], []),
        (['a123456', 'A789012'], ['A789012']),  # 대소문자 구분
    ])
    def test_filter_ids_parametrized(self, test_input, expected):
        """파라미터화된 ID 필터링 테스트"""
        test_data = {'seller_unique_item_id': test_input}
        excel_path = self.create_test_excel(test_data)
        
        processor = ExcelProcessor(excel_path)
        processor.load_excel()
        
        result = processor.filter_ids_starting_with_a()
        
        assert result == expected