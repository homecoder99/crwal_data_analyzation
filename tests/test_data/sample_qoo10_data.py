"""
테스트용 샘플 데이터 생성기
"""
import pandas as pd
from pathlib import Path
import tempfile

class SampleDataGenerator:
    """테스트용 샘플 데이터 생성 클래스"""
    
    @staticmethod
    def create_sample_excel_data():
        """기본 샘플 Excel 데이터 생성"""
        return {
            'seller_unique_item_id': [
                'A001234567',  # 유효 (A로 시작)
                'A007890123',  # 유효 (A로 시작)  
                'A005555555',  # 유효 (A로 시작)
                'A009999999',  # 유효 (A로 시작)
                'B001111111',  # 무효 (B로 시작)
                'C002222222',  # 무효 (C로 시작)
                'a003333333',  # 무효 (소문자 a)
                '1004444444',  # 무효 (숫자로 시작)
                None,          # 무효 (null)
                '',            # 무효 (빈 문자열)
            ],
            'product_name': [
                '올리브영 프리미엄 스킨케어 세트',
                '천연 화장품 기초 라인',
                '미네랄 선크림 50ml',
                '비타민 C 에센스 30ml', 
                '헤어케어 샴푸 500ml',
                '바디워시 대용량 1000ml',
                '립밤 보습 타입',
                '클렌징 폼 150ml',
                '토너 200ml',
                '아이크림 30ml',
            ],
            'category': [
                '스킨케어',
                '기초화장품',
                '선케어',
                '에센스',
                '헤어케어',
                '바디케어',
                '립케어',
                '클렌징',
                '토너',
                '아이케어',
            ],
            'price': [
                29900,
                19900,
                15000,
                25000,
                12000,
                8500,
                3500,
                8900,
                18000,
                35000,
            ],
            'brand': [
                '브랜드A',
                '브랜드B', 
                '브랜드C',
                '브랜드D',
                '브랜드E',
                '브랜드F',
                '브랜드G',
                '브랜드H',
                '브랜드I',
                '브랜드J',
            ]
        }
    
    @staticmethod
    def create_large_sample_data(count: int = 100):
        """대용량 샘플 데이터 생성"""
        data = {
            'seller_unique_item_id': [],
            'product_name': [],
            'category': [],
            'price': [],
            'brand': []
        }
        
        categories = ['스킨케어', '메이크업', '헤어케어', '바디케어', '향수']
        brands = ['브랜드A', '브랜드B', '브랜드C', '브랜드D', '브랜드E']
        
        for i in range(count):
            # 80%는 A로 시작, 20%는 다른 문자로 시작
            if i % 5 == 0:
                id_prefix = 'B'  # 무효 ID
            else:
                id_prefix = 'A'  # 유효 ID
                
            data['seller_unique_item_id'].append(f'{id_prefix}{str(i).zfill(9)}')
            data['product_name'].append(f'테스트 상품 {i+1}')
            data['category'].append(categories[i % len(categories)])
            data['price'].append((i % 10 + 1) * 1000)
            data['brand'].append(brands[i % len(brands)])
        
        return data
    
    @staticmethod
    def create_edge_case_data():
        """엣지 케이스 데이터 생성"""
        return {
            'seller_unique_item_id': [
                'A',           # 너무 짧음
                'A' * 20,      # 너무 긴 ID
                'A123',        # 짧은 유효 ID
                'A' + '0' * 15,  # 0으로 채운 ID
                'ABCDEFGHIJ',  # 문자 조합
                ' A123456 ',   # 공백 포함
                'A-123-456',   # 특수문자 포함
                'A_123_456',   # 언더스코어 포함
                None,
                pd.NA,
            ],
            'product_name': [
                '일반 상품명',
                '특수문자 포함 상품명!@#$%',
                '매우 긴 상품명' * 10,
                '',
                None,
                '이모지 포함 상품 😊',
                '숫자123 포함 상품명',
                '    공백상품명    ',
                '줄바꿈\n포함\n상품명',
                'Unicode 테스트 상품명',
            ]
        }
    
    @staticmethod
    def save_to_excel(data: dict, file_path: str):
        """데이터를 Excel 파일로 저장"""
        df = pd.DataFrame(data)
        df.to_excel(file_path, index=False, engine='openpyxl')
        return file_path
    
    @classmethod
    def create_test_excel_file(cls, temp_dir: str, data_type: str = "basic"):
        """테스트용 Excel 파일 생성"""
        if data_type == "basic":
            data = cls.create_sample_excel_data()
        elif data_type == "large":
            data = cls.create_large_sample_data()
        elif data_type == "edge_case":
            data = cls.create_edge_case_data()
        else:
            raise ValueError(f"Unknown data_type: {data_type}")
        
        file_path = Path(temp_dir) / f"test_{data_type}_data.xlsx"
        return cls.save_to_excel(data, str(file_path))

# 테스트용 예상 결과 데이터
EXPECTED_BASIC_FILTERED_IDS = [
    'A001234567',
    'A007890123', 
    'A005555555',
    'A009999999'
]

EXPECTED_LARGE_FILTERED_COUNT = 80  # 100개 중 80개가 A로 시작

EXPECTED_EDGE_CASE_FILTERED_IDS = [
    'A',
    'A' * 20,
    'A123',
    'A' + '0' * 15,
    'ABCDEFGHIJ',
    ' A123456 ',
    'A-123-456',
    'A_123_456'
]