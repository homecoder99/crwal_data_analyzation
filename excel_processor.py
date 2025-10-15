"""
올리브영 크롤러를 위한 Excel 데이터 처리기
seller_unique_item_id 데이터 로드 및 필터링 담당
"""
import pandas as pd
import logging
from typing import List, Optional
from pathlib import Path

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ExcelProcessor:
    def __init__(self, excel_path: str):
        """Excel 처리기 초기화"""
        self.excel_path = Path(excel_path)
        self.df = None
        self.filtered_ids = []
        
    def load_excel(self) -> bool:
        """Excel 파일을 로드하고 기본 정보를 로깅"""
        try:
            logger.info(f"🔄 Excel 파일 로딩 중: {self.excel_path}")
            
            if not self.excel_path.exists():
                logger.error(f"❌ Excel 파일을 찾을 수 없습니다: {self.excel_path}")
                return False
                
            self.df = pd.read_excel(self.excel_path, engine='openpyxl')
            
            logger.info(f"✅ Excel 파일 로드 완료")
            logger.info(f"📊 총 행 수: {len(self.df)}")
            logger.info(f"📋 컬럼 목록: {list(self.df.columns)}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Excel 파일 로드 실패: {str(e)}")
            return False
    
    def validate_columns(self) -> bool:
        """필수 컬럼이 존재하는지 검증"""
        required_column = 'seller_unique_item_id'
        
        if required_column not in self.df.columns:
            logger.error(f"❌ 필수 컬럼 '{required_column}'을 찾을 수 없습니다")
            logger.info(f"사용 가능한 컬럼: {list(self.df.columns)}")
            return False
            
        logger.info(f"✅ 필수 컬럼 '{required_column}' 확인됨")
        return True
    
    def filter_ids_starting_with_a(self) -> List[str]:
        """'oliveyoung_A'로 시작하는 ID를 필터링하고 'oliveyoung_' 접두사 제거"""
        logger.info("🔍 'oliveyoung_A'로 시작하는 seller_unique_item_id 필터링 중")

        # 컬럼 데이터 가져오기
        id_column = self.df['seller_unique_item_id']

        # null 값 제거하고 문자열로 변환
        valid_ids = id_column.dropna().astype(str)

        # 'oliveyoung_A'로 시작하는 ID 필터링
        filtered_ids = valid_ids[valid_ids.str.startswith('oliveyoung_A', na=False)]

        # 'oliveyoung_' 접두사 제거하여 'A...' 형식으로 변환
        self.filtered_ids = [id_str.replace('oliveyoung_', '', 1) for id_str in filtered_ids.tolist()]

        logger.info(f"📈 전체 유효 ID 수: {len(valid_ids)}")
        logger.info(f"✨ 'oliveyoung_A'로 시작하는 ID 수: {len(self.filtered_ids)}")

        if len(self.filtered_ids) > 0:
            logger.info(f"🔍 첫 5개 필터링된 ID (접두사 제거 후): {self.filtered_ids[:5]}")
        else:
            logger.warning("⚠️  'oliveyoung_A'로 시작하는 ID를 찾을 수 없습니다")

        return self.filtered_ids
    
    def get_filtered_ids(self) -> List[str]:
        """필터링된 ID 목록 반환"""
        return self.filtered_ids
    
    def process(self) -> Optional[List[str]]:
        """메인 처리 메소드 - 데이터 로드 및 필터링"""
        logger.info("🚀 Excel 데이터 처리 시작")
        
        # Excel 파일 로드
        if not self.load_excel():
            return None
            
        # 컬럼 검증
        if not self.validate_columns():
            return None
            
        # ID 필터링
        filtered_ids = self.filter_ids_starting_with_a()
        
        if len(filtered_ids) == 0:
            logger.warning("⚠️  처리할 유효한 ID가 없습니다")
            return None
            
        logger.info(f"✅ Excel 처리 완료. {len(filtered_ids)}개 ID 처리 준비됨")
        return filtered_ids

def main():
    """Excel 처리기 테스트"""
    processor = ExcelProcessor("data/Qoo10_ItemInfo.xlsx")
    ids = processor.process()
    
    if ids:
        print(f"성공적으로 {len(ids)}개 ID 처리됨")
    else:
        print("Excel 파일 처리 실패")

if __name__ == "__main__":
    main()