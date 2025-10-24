#!/usr/bin/env python3
"""
가격/수량 업데이트 Excel 생성기
Qoo10_EditItemPriceQtyList.xlsx 템플릿을 사용하여 여러 업데이트 파일 생성
"""

import json
import pandas as pd
from pathlib import Path
from typing import Dict, List, Tuple
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


class UpdateExcelGenerator:
    def __init__(self, template_file: str, json_file: str):
        self.template_file = template_file
        self.json_file = json_file
        self.data = self._load_json()

    def _load_json(self) -> dict:
        """크롤링 결과 JSON 로드"""
        with open(self.json_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _parse_price_line(self, line: str) -> Tuple[str, int, int]:
        """
        가격 변경 라인 파싱
        예: oliveyoung_A000000236452: 1880엔 → 1850엔 (-30엔)
        Returns: (seller_id, old_price, new_price)
        """
        parts = line.split(':')
        if len(parts) != 2:
            return None, 0, 0

        seller_id = parts[0].strip()
        price_info = parts[1].strip()

        # 1880엔 → 1850엔 파싱
        prices = price_info.split('→')
        if len(prices) != 2:
            return None, 0, 0

        old_price = int(prices[0].strip().replace('엔', '').replace(',', ''))
        new_price_part = prices[1].split('(')[0].strip()
        new_price = int(new_price_part.replace('엔', '').replace(',', ''))

        return seller_id, old_price, new_price

    def _parse_option_price_line(self, line: str) -> Tuple[str, str, int, int]:
        """
        옵션 가격 변경 라인 파싱
        예: oliveyoung_A000000236716 / oliveyoung_A000000236716_1: 차액 1340엔 → 0엔 (-1340엔)
        Returns: (product_seller_id, option_seller_id, old_additional, new_additional)
        """
        parts = line.split(':')
        if len(parts) != 2:
            return None, None, 0, 0

        ids = parts[0].strip()
        price_info = parts[1].strip()

        # product_id / option_id 분리
        id_parts = ids.split('/')
        if len(id_parts) != 2:
            return None, None, 0, 0

        product_id = id_parts[0].strip()
        option_id = id_parts[1].strip()

        # 차액 1340엔 → 0엔 파싱
        if '차액' not in price_info:
            return None, None, 0, 0

        price_info = price_info.replace('차액', '').strip()
        prices = price_info.split('→')
        if len(prices) != 2:
            return None, None, 0, 0

        old_price = int(prices[0].strip().replace('엔', '').replace(',', ''))
        new_price_part = prices[1].split('(')[0].strip()
        new_price = int(new_price_part.replace('엔', '').replace(',', ''))

        return product_id, option_id, old_price, new_price

    def _create_base_dataframe(self) -> pd.DataFrame:
        """템플릿의 헤더 3행을 읽어서 기본 구조 생성"""
        df = pd.read_excel(self.template_file, engine='openpyxl', header=0)
        # 헤더 3행 보존
        header_rows = df.iloc[:3].copy()
        return header_rows

    def _create_excel(self, rows: List[dict], output_file: str):
        """Excel 파일 생성"""
        if not rows:
            logger.warning(f"⚠️  {output_file}: 생성할 데이터가 없습니다")
            return

        header_rows = self._create_base_dataframe()
        data_df = pd.DataFrame(rows)

        # 헤더와 데이터 결합
        final_df = pd.concat([header_rows, data_df], ignore_index=True)

        # output 폴더 생성
        output_path = Path('output') / output_file
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Excel 저장
        final_df.to_excel(output_path, index=False, engine='openpyxl')
        logger.info(f"✅ {output_file} 생성 완료 ({len(rows)}개)")

    def generate_single_updates(self, output_file: str):
        """
        1단계: 단품 품절/복구/가격변경 (edit_type='g')
        """
        rows = []

        # 1. 단품 품절 (quantity=0)
        soldout_file = 'output/1_single_soldout_ids.txt'
        if Path(soldout_file).exists():
            with open(soldout_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                for line in lines:
                    line = line.strip()
                    if line.startswith('oliveyoung_'):
                        rows.append({
                            'seller_unique_item_id': line,
                            'seller_unique_option_id': '',
                            'edit_type': 'g',
                            'Price': '',  # 품절은 가격 변경 없음
                            'quantity': 0
                        })

        # 2. 단품 복구 (quantity=200)
        restock_file = 'output/8_restocked_single.txt'
        if Path(restock_file).exists():
            with open(restock_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                in_id_section = False
                for line in lines:
                    line = line.strip()
                    # ID 목록 섹션 시작
                    if line == '## 상품 ID 목록 (Excel 복사용)':
                        in_id_section = True
                        continue
                    # 다음 섹션 시작하면 종료
                    if in_id_section and line.startswith('##'):
                        break
                    # ID만 읽기
                    if in_id_section and line.startswith('oliveyoung_'):
                        rows.append({
                            'seller_unique_item_id': line,
                            'seller_unique_option_id': '',
                            'edit_type': 'g',
                            'Price': '',  # 복구는 가격 변경 없음
                            'quantity': 200
                        })

        # 3. 단품 가격 변경
        price_file = 'output/5_price_changed_single.txt'
        if Path(price_file).exists():
            with open(price_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                in_detail = False
                for line in lines:
                    line = line.strip()
                    if line == '## 상세 정보':
                        in_detail = True
                        continue

                    if in_detail and ':' in line and '→' in line:
                        seller_id, old_price, new_price = self._parse_price_line(line)
                        if seller_id:
                            rows.append({
                                'seller_unique_item_id': seller_id,
                                'seller_unique_option_id': '',
                                'edit_type': 'g',
                                'Price': new_price,
                                'quantity': ''
                            })

        self._create_excel(rows, output_file)

    def generate_option_base_price(self, output_file: str):
        """
        2단계: 옵션 기본가격 변경 (edit_type='g')
        """
        rows = []
        price_file = 'output/6_price_changed_option_base.txt'

        if Path(price_file).exists():
            with open(price_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                in_detail = False
                for line in lines:
                    line = line.strip()
                    if line == '## 상세 정보':
                        in_detail = True
                        continue

                    if in_detail and ':' in line and '→' in line:
                        seller_id, old_price, new_price = self._parse_price_line(line)
                        if seller_id:
                            rows.append({
                                'seller_unique_item_id': seller_id,
                                'seller_unique_option_id': '',
                                'edit_type': 'g',
                                'Price': new_price,
                                'quantity': ''
                            })

        self._create_excel(rows, output_file)

    def generate_option_additional_price(self, output_file: str):
        """
        3단��: 옵션 차액 변경 (edit_type='i')
        """
        rows = []
        price_file = 'output/7_price_changed_option_additional.txt'

        if Path(price_file).exists():
            with open(price_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                in_detail = False
                for line in lines:
                    line = line.strip()
                    if line == '## 상세 정보':
                        in_detail = True
                        continue

                    if in_detail and '/' in line and ':' in line and '차액' in line:
                        product_id, option_id, old_add, new_add = self._parse_option_price_line(line)
                        if option_id:
                            rows.append({
                                'seller_unique_item_id': product_id,
                                'seller_unique_option_id': option_id,
                                'edit_type': 'i',
                                'Price': new_add,  # 차액
                                'quantity': ''
                            })

        self._create_excel(rows, output_file)

    def generate_option_soldout(self, output_file: str):
        """
        4단계: 옵션 품절 (edit_type='i', quantity=0)
        """
        rows = []
        soldout_file = 'output/2_option_soldout_ids.txt'

        if Path(soldout_file).exists():
            with open(soldout_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                in_option_ids = False
                product_ids = []
                option_ids = []

                for line in lines:
                    line = line.strip()
                    if line == '## 상품 ID 목록 (Excel 복사용)':
                        in_option_ids = False
                        continue
                    elif line == '## 옵션 ID 목록 (Excel 복사용)':
                        in_option_ids = True
                        continue

                    if line.startswith('oliveyoung_'):
                        if in_option_ids:
                            option_ids.append(line)
                        else:
                            product_ids.append(line)

                # product_ids와 option_ids는 같은 순서로 매칭됨
                for product_id, option_id in zip(product_ids, option_ids):
                    rows.append({
                        'seller_unique_item_id': product_id,
                        'seller_unique_option_id': option_id,
                        'edit_type': 'i',
                        'Price': '',
                        'quantity': 0
                    })

        self._create_excel(rows, output_file)

    def generate_option_restock(self, output_file: str):
        """
        5단계: 옵션 복구 (edit_type='i', quantity=200)
        """
        rows = []
        restock_file = 'output/9_restocked_option.txt'

        if Path(restock_file).exists():
            with open(restock_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                in_detail = False

                for line in lines:
                    line = line.strip()
                    if line == '## 상세 정보':
                        in_detail = True
                        continue

                    if in_detail and '/' in line:
                        # oliveyoung_A000000129694 / oliveyoung_A000000129694_4: 0 → 판매중
                        parts = line.split('/')
                        if len(parts) >= 2:
                            product_id = parts[0].strip()
                            option_part = parts[1].strip()
                            option_id = option_part.split(':')[0].strip()

                            rows.append({
                                'seller_unique_item_id': product_id,
                                'seller_unique_option_id': option_id,
                                'edit_type': 'i',
                                'Price': '',
                                'quantity': 200
                            })

        self._create_excel(rows, output_file)

    def generate_all(self):
        """모든 업데이트 Excel 파일 생성"""
        logger.info("=" * 60)
        logger.info("가격/수량 업데이트 Excel 생성 시작")
        logger.info("=" * 60)

        # 순서대로 생성
        self.generate_single_updates('UPDATE_1_SINGLE.xlsx')
        self.generate_option_base_price('UPDATE_2_OPTION_BASE.xlsx')
        self.generate_option_additional_price('UPDATE_3_OPTION_ADDITIONAL.xlsx')
        self.generate_option_soldout('UPDATE_4_OPTION_SOLDOUT.xlsx')
        self.generate_option_restock('UPDATE_5_OPTION_RESTOCK.xlsx')

        logger.info("=" * 60)
        logger.info("✅ 모든 업데이트 Excel 생성 완료!")
        logger.info("")
        logger.info("⚠️  업데이트 순서:")
        logger.info("  1. UPDATE_1_SINGLE.xlsx (단품 품절/복구/가격변경)")
        logger.info("  2. UPDATE_2_OPTION_BASE.xlsx (옵션 기본가격 변경)")
        logger.info("  3. UPDATE_3_OPTION_ADDITIONAL.xlsx (옵션 차액 변경)")
        logger.info("  4. UPDATE_4_OPTION_SOLDOUT.xlsx (옵션 품절)")
        logger.info("  5. UPDATE_5_OPTION_RESTOCK.xlsx (옵션 복구)")
        logger.info("=" * 60)


def main():
    template_file = 'data/Qoo10_EditItemPriceQtyList.xlsx'
    json_file = 'olive_young_products.json'

    if not Path(template_file).exists():
        logger.error(f"❌ 템플릿 파일을 찾을 수 없습니다: {template_file}")
        return

    if not Path(json_file).exists():
        logger.error(f"❌ JSON 파일을 찾을 수 없습니다: {json_file}")
        return

    generator = UpdateExcelGenerator(template_file, json_file)
    generator.generate_all()


if __name__ == '__main__':
    main()
