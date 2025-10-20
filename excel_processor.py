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
        self.price_map = {}  # ID별 가격 정보 저장
        self.quantity_map = {}  # ID별 재고 정보 저장 (0 = 품절)

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

    def load_price_info(self):
        """Excel에서 가격 정보 로드 (엔화)"""
        if self.df is None:
            logger.warning("⚠️  Excel 파일이 로드되지 않았습니다")
            return

        if 'price_yen' not in self.df.columns:
            logger.warning(f"⚠️  price_yen 컬럼을 찾을 수 없습니다. 사용 가능한 컬럼: {list(self.df.columns)}")
            return

        logger.info(f"💰 가격 컬럼 발견: price_yen")

        for _, row in self.df.iterrows():
            seller_id = str(row.get('seller_unique_item_id', '')).strip()

            # oliveyoung_ 로 시작하는 ID인 경우
            if seller_id.startswith('oliveyoung_'):
                # oliveyoung_ 접두사 제거
                product_id = seller_id.replace('oliveyoung_', '', 1)
                price_value = row.get('price_yen', 0)

                # 가격이 숫자인지 확인
                try:
                    price_jpy = int(price_value) if price_value else 0
                    self.price_map[product_id] = price_jpy
                except (ValueError, TypeError):
                    logger.debug(f"⚠️  가격 파싱 실패: {seller_id}, {price_value}")

        logger.info(f"✅ 가격 정보 로드 완료: {len(self.price_map)}개")

    def load_quantity_info(self):
        """Excel에서 재고(quantity) 정보 로드"""
        if self.df is None:
            logger.warning("⚠️  Excel 파일이 로드되지 않았습니다")
            return

        if 'quantity' not in self.df.columns:
            logger.warning(f"⚠️  quantity 컬럼을 찾을 수 없습니다. 사용 가능한 컬럼: {list(self.df.columns)}")
            return

        logger.info(f"📦 재고 컬럼 발견: quantity")

        soldout_count = 0
        for _, row in self.df.iterrows():
            seller_id = str(row.get('seller_unique_item_id', '')).strip()

            # oliveyoung_ 로 시작하는 ID인 경우
            if seller_id.startswith('oliveyoung_'):
                # oliveyoung_ 접두사 제거
                product_id = seller_id.replace('oliveyoung_', '', 1)

                # 옵션 정보 확인
                option_info = str(row.get('option', '')).strip()

                if option_info and option_info != 'nan':
                    # 옵션 상품: 각 옵션별 재고 파싱
                    self._parse_option_quantities(product_id, option_info)
                else:
                    # 단품: quantity 컬럼 값 사용
                    quantity_value = row.get('quantity', 0)
                    try:
                        quantity = int(quantity_value) if quantity_value else 0
                        self.quantity_map[product_id] = quantity
                        if quantity == 0:
                            soldout_count += 1
                    except (ValueError, TypeError):
                        logger.debug(f"⚠️  재고 파싱 실패: {seller_id}, {quantity_value}")

        logger.info(f"✅ 재고 정보 로드 완료: {len(self.quantity_map)}개")
        logger.info(f"🛑 품절 상품(quantity=0): {soldout_count}개")

    def _parse_option_quantities(self, product_id: str, option_info: str):
        """옵션 정보에서 각 옵션별 재고 파싱
        형식: Option||*옵션명||*추가가격||*재고||*옵션코드$
        """
        options = option_info.split('$')

        for idx, option_str in enumerate(options, 1):
            option_str = option_str.strip()
            if not option_str or option_str == 'nan':
                continue

            parts = option_str.split('||*')
            if len(parts) >= 4:
                try:
                    # parts[3] = 재고
                    stock_str = parts[3].strip()
                    quantity = int(stock_str)

                    # 옵션 ID: A000000111111_1 형식
                    option_id = f"{product_id}_{idx}"
                    self.quantity_map[option_id] = quantity

                except (ValueError, IndexError) as e:
                    logger.debug(f"⚠️  옵션 재고 파싱 실패: {product_id}, {option_str}")

    def get_price_jpy(self, product_id: str) -> Optional[int]:
        """상품 ID의 엔화 가격 반환"""
        return self.price_map.get(product_id)

    def get_quantity(self, product_id: str) -> Optional[int]:
        """상품 ID의 재고 수량 반환 (0 = 품절)"""
        return self.quantity_map.get(product_id)

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

        # 가격 정보 로드
        self.load_price_info()

        # 재고 정보 로드
        self.load_quantity_info()

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
