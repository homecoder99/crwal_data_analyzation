"""
크롤링 결과 분석 도구
단품/옵션 상품 구분하여 4개 파일 생성 + 가격 변경 감지
"""
import json
import argparse
from typing import List, Dict, Tuple
from pathlib import Path
import pandas as pd


class CrawlingResultAnalyzer:
    def __init__(self, result_file: str = "olive_young_products.json", excel_file: str = "data/Qoo10_ItemInfo.xlsx"):
        """
        크롤링 결과 분석기 초기화

        Args:
            result_file: 크롤링 결과 JSON 파일 경로
            excel_file: Excel 파일 경로 (가격 비교용)
        """
        self.result_file = result_file
        self.excel_file = excel_file
        self.data = None
        self.excel_price_map = {}  # Excel의 기존 가격 정보
        self.excel_quantity_map = {}  # Excel의 재고 정보 (0 = 품절)

    def load_data(self) -> bool:
        """크롤링 결과 데이터 로드"""
        try:
            if not Path(self.result_file).exists():
                print(f"❌ 파일을 찾을 수 없습니다: {self.result_file}")
                return False

            with open(self.result_file, 'r', encoding='utf-8') as f:
                self.data = json.load(f)

            print(f"✅ 데이터 로드 완료: {self.result_file}")
            return True

        except Exception as e:
            print(f"❌ 데이터 로드 실패: {str(e)}")
            return False

    def load_excel_prices(self) -> bool:
        """Excel에서 기존 가격 정보 로드 (단품 + 옵션)"""
        try:
            if not Path(self.excel_file).exists():
                print(f"⚠️  Excel 파일을 찾을 수 없습니다: {self.excel_file}")
                return False

            df = pd.read_excel(self.excel_file, engine='openpyxl')

            # 필수 컬럼 확인
            if 'price_yen' not in df.columns:
                print(f"⚠️  price_yen 컬럼을 찾을 수 없습니다. 사용 가능한 컬럼: {list(df.columns)}")
                return False

            if 'quantity' not in df.columns:
                print(f"⚠️  quantity 컬럼을 찾을 수 없습니다. 사용 가능한 컬럼: {list(df.columns)}")
                return False

            if 'option_info' not in df.columns:
                print(f"⚠️  option_info 컬럼을 찾을 수 없습니다. 사용 가능한 컬럼: {list(df.columns)}")
                return False

            print(f"💰 Excel 가격 컬럼: price_yen")
            print(f"📦 Excel 재고 컬럼: quantity")
            print(f"🔧 Excel 옵션 컬럼: option_info")

            # 가격 및 재고 정보 로드
            for _, row in df.iterrows():
                seller_id = str(row.get('seller_unique_item_id', '')).strip()

                if seller_id.startswith('oliveyoung_'):
                    product_id = seller_id.replace('oliveyoung_', '', 1)
                    base_price = row.get('price_yen', 0)
                    quantity = row.get('quantity', 0)

                    try:
                        base_price_jpy = int(base_price) if base_price else 0
                    except (ValueError, TypeError):
                        base_price_jpy = 0

                    try:
                        quantity_value = int(quantity) if quantity else 0
                    except (ValueError, TypeError):
                        quantity_value = 0

                    # 옵션 정보 파싱
                    option_info = str(row.get('option_info', '')).strip()

                    if option_info and option_info != 'nan' and '$$' in option_info:
                        # 옵션 상품: 가격 및 재고 파싱
                        self._parse_option_prices(product_id, base_price_jpy, option_info)
                        self._parse_option_quantities(product_id, option_info)
                    else:
                        # 단품 상품
                        self.excel_price_map[product_id] = base_price_jpy
                        self.excel_quantity_map[product_id] = quantity_value

            print(f"✅ Excel 가격 정보 로드: {len(self.excel_price_map)}개")
            print(f"✅ Excel 재고 정보 로드: {len(self.excel_quantity_map)}개")
            return True

        except Exception as e:
            print(f"❌ Excel 가격 로드 실패: {str(e)}")
            return False

    def _parse_option_prices(self, product_id: str, base_price_jpy: int, option_info: str):
        """옵션 정보 파싱하여 각 옵션별 가격 계산

        형식: Option||*옵션명||*추가가격||*재고||*옵션코드$$
        예: Option||*50ml||*0||*200||*oliveyoung_A000000111111_1$$
        """
        try:
            # $$ 구분자로 분리
            options = option_info.split('$$')

            for option_str in options:
                if not option_str.strip():
                    continue

                # ||* 구분자로 파싱
                parts = option_str.split('||*')
                if len(parts) < 5:
                    continue

                # parts[0] = "Option"
                # parts[1] = 옵션명
                # parts[2] = 추가가격
                # parts[3] = 재고
                # parts[4] = 옵션코드

                additional_price_str = parts[2].strip()
                option_code = parts[4].strip()

                # 옵션 코드에서 ID 추출 (oliveyoung_A000000111111_1 → A000000111111_1)
                if option_code.startswith('oliveyoung_'):
                    option_id = option_code.replace('oliveyoung_', '', 1)
                else:
                    continue

                # 추가 가격 파싱
                try:
                    additional_price = int(additional_price_str)
                except (ValueError, TypeError):
                    additional_price = 0

                # 실제 옵션 가격 = 판매가 + 추가가격
                option_price_jpy = base_price_jpy + additional_price

                self.excel_price_map[option_id] = option_price_jpy

        except Exception as e:
            print(f"⚠️  옵션 가격 파싱 실패 ({product_id}): {str(e)}")

    def _parse_option_quantities(self, product_id: str, option_info: str):
        """옵션 정보에서 각 옵션별 재고 파싱
        형식: Option||*옵션명||*추가가격||*재고||*옵션코드$$
        """
        try:
            options = option_info.split('$$')

            for option_str in options:
                if not option_str.strip():
                    continue

                parts = option_str.split('||*')
                if len(parts) < 5:
                    continue

                # parts[3] = 재고
                # parts[4] = 옵션코드
                stock_str = parts[3].strip()
                option_code = parts[4].strip()

                # 옵션 코드에서 ID 추출
                if option_code.startswith('oliveyoung_'):
                    option_id = option_code.replace('oliveyoung_', '', 1)
                else:
                    continue

                # 재고 파싱
                try:
                    quantity = int(stock_str)
                except (ValueError, TypeError):
                    quantity = 0

                self.excel_quantity_map[option_id] = quantity

        except Exception as e:
            print(f"⚠️  옵션 재고 파싱 실패 ({product_id}): {str(e)}")

    def extract_single_soldout_ids(self) -> List[str]:
        """단품인데 판매 종료된 상품 ID 추출"""
        if not self.data or 'products' not in self.data:
            return []

        soldout_ids = []

        for product in self.data['products']:
            # 단품이면서 품절인 경우
            if (not product.get('has_options', False) and
                product.get('product_status') == 'soldOut'):
                soldout_ids.append(product['product_id'])

        return soldout_ids

    def extract_option_soldout_ids(self) -> List[str]:
        """옵션 상품 중 품절된 옵션 ID 추출 (옵션별로 ID_숫자 형식)"""
        if not self.data or 'products' not in self.data:
            return []

        option_soldout_ids = []

        for product in self.data['products']:
            # 옵션 상품인 경우
            if product.get('has_options', False):
                product_id = product['product_id']
                options = product.get('options', [])

                for option in options:
                    if option.get('is_soldout', False):
                        # 옵션 ID 형식: A000000111111_1
                        option_id = f"{product_id}_{option['index']}"
                        option_soldout_ids.append(option_id)

        return option_soldout_ids

    def extract_successful_ids(self) -> List[str]:
        """성공적으로 크롤링된 상품 ID 추출 (에러 없이 처리됨)"""
        if not self.data or 'products' not in self.data:
            return []

        successful_ids = []

        for product in self.data['products']:
            product_status = product.get('product_status')
            status = product.get('status')

            # 정상적으로 크롤링되고 판매 상태를 확인할 수 있는 경우
            if (product_status in ['saleOn', 'soldOut'] and
                status != 'timeout' and
                product_status != 'unknown'):
                successful_ids.append(product['product_id'])

        return successful_ids

    def extract_price_changed_products(self) -> Dict[str, List[Tuple[str, int, int]]]:
        """가격이 변경된 상품/옵션 추출 (단품/옵션 분리)

        Returns:
            {
                'single': [(product_id, old_price, new_price), ...],
                'option': [(product_id, option_id, old_price, new_price), ...]
            }
        """
        if not self.data or 'products' not in self.data:
            return {'single': [], 'option': []}

        if not self.excel_price_map:
            print("⚠️  Excel 가격 정보가 없어 가격 비교를 수행할 수 없습니다")
            return {'single': [], 'option': []}

        price_changed = {'single': [], 'option': []}

        for product in self.data['products']:
            product_id = product['product_id']

            # 옵션 상품인 경우
            if product.get('has_options', False):
                options = product.get('options', [])
                for option in options:
                    option_id = f"{product_id}_{option['index']}"
                    new_price_jpy = option.get('price_jpy', 0)
                    old_price_jpy = self.excel_price_map.get(option_id, 0)

                    # 가격이 있고, 변경되었으면 추가
                    if new_price_jpy > 0 and old_price_jpy > 0 and new_price_jpy != old_price_jpy:
                        price_changed['option'].append((product_id, option_id, old_price_jpy, new_price_jpy))
            else:
                # 단품 상품인 경우
                new_price_jpy = product.get('price_jpy', 0)
                old_price_jpy = self.excel_price_map.get(product_id, 0)

                # 가격이 있고, 변경되었으면 추가
                if new_price_jpy > 0 and old_price_jpy > 0 and new_price_jpy != old_price_jpy:
                    price_changed['single'].append((product_id, old_price_jpy, new_price_jpy))

        return price_changed

    def extract_restocked_products(self) -> Dict[str, List[Tuple]]:
        """품절→판매중 복구된 상품/옵션 추출

        Excel quantity=0이었는데, 크롤링 결과 판매중인 경우

        Returns:
            {
                'single': [(product_id, old_quantity, new_status), ...],
                'option': [(product_id, option_id, old_quantity, new_status), ...]
            }
        """
        if not self.data or 'products' not in self.data:
            return {'single': [], 'option': []}

        if not self.excel_quantity_map:
            print("⚠️  Excel 재고 정보가 없어 복구 여부를 확인할 수 없습니다")
            return {'single': [], 'option': []}

        restocked = {'single': [], 'option': []}

        for product in self.data['products']:
            product_id = product['product_id']

            # 크롤링 성공한 상품만 확인
            if product.get('status') != 'success':
                continue

            # 옵션 상품인 경우
            if product.get('has_options', False):
                options = product.get('options', [])
                for option in options:
                    option_id = f"{product_id}_{option['index']}"
                    old_quantity = self.excel_quantity_map.get(option_id, -1)
                    is_soldout = option.get('is_soldout', True)

                    # Excel에서 품절(0)이었는데, 현재 판매중인 경우
                    if old_quantity == 0 and not is_soldout:
                        restocked['option'].append((product_id, option_id, old_quantity, 'saleOn'))
            else:
                # 단품 상품인 경우
                old_quantity = self.excel_quantity_map.get(product_id, -1)
                product_status = product.get('product_status', 'unknown')

                # Excel에서 품절(0)이었는데, 현재 판매중인 경우
                if old_quantity == 0 and product_status == 'saleOn':
                    restocked['single'].append((product_id, old_quantity, product_status))

        return restocked

    def extract_deleted_products(self) -> Dict[str, List[Tuple]]:
        """삭제된 상품 감지 (크롤링 실패 + 404 등)

        크롤링 결과 timeout이나 error가 발생한 경우 삭제 가능성

        Returns:
            {
                'single': [(product_id, status, error), ...],
                'option': []  # 옵션 상품은 상품 전체가 삭제되므로 single에만 포함
            }
        """
        if not self.data or 'products' not in self.data:
            return {'single': [], 'option': []}

        deleted = {'single': [], 'option': []}

        for product in self.data['products']:
            product_id = product['product_id']
            status = product.get('status', 'unknown')
            error_msg = product.get('error', '')

            # 크롤링 실패 (timeout, error 등)
            if status in ['timeout', 'error', 'failed']:
                deleted['single'].append((product_id, status, error_msg))

            # product_status가 unknown인 경우도 삭제 가능성
            elif product.get('product_status') == 'unknown':
                deleted['single'].append((product_id, 'unknown', 'product_status unknown'))

        return deleted

    def get_statistics(self) -> Dict:
        """전체 통계 정보"""
        if not self.data or 'products' not in self.data:
            return {}

        single_soldout = self.extract_single_soldout_ids()
        option_soldout = self.extract_option_soldout_ids()
        successful = self.extract_successful_ids()

        # 판매중 ID (성공 - 품절)
        single_soldout_set = set(single_soldout)
        successful_set = set(successful)
        on_sale_ids = list(successful_set - single_soldout_set)

        # 실패 ID (타임아웃, unknown 등)
        failed_ids = []
        for product in self.data['products']:
            product_id = product['product_id']
            if product_id not in successful:
                failed_ids.append(product_id)

        # 수정 필요 상품 ID (옵션 상품 중 일부만 품절)
        modified_ids = []
        for product in self.data['products']:
            if product.get('has_options', False):
                product_id = product['product_id']
                options = product.get('options', [])

                soldout_count = sum(1 for opt in options if opt.get('is_soldout', False))
                total_count = len(options)

                # 일부만 품절인 경우
                if 0 < soldout_count < total_count:
                    modified_ids.append(product_id)

        return {
            'total': len(self.data.get('products', [])),
            'successful': len(successful),
            'failed': len(failed_ids),
            'on_sale': len(on_sale_ids),
            'soldout_single': len(single_soldout),
            'soldout_option': len(option_soldout),
            'modified': len(modified_ids),
            'successful_ids': successful,
            'failed_ids': failed_ids,
            'on_sale_ids': on_sale_ids,
            'soldout_single_ids': single_soldout,
            'soldout_option_ids': option_soldout,
            'modified_ids': modified_ids
        }

    def print_statistics(self):
        """크롤링 결과 통계 출력"""
        if not self.data:
            print("❌ 데이터가 로드되지 않았습니다.")
            return

        stats = self.get_statistics()

        print("\n" + "="*60)
        print("📊 크롤링 결과 통계")
        print("="*60)

        # 메타데이터 정보
        if 'metadata' in self.data:
            metadata = self.data['metadata']
            print(f"📅 크롤링 일시: {metadata.get('timestamp', 'N/A')}")

        print(f"\n🔍 처리된 총 상품 수: {stats['total']}")
        print(f"✅ 성공적으로 처리된 상품: {stats['successful']}")
        print(f"❌ 실패한 상품: {stats['failed']}")
        print(f"\n💚 판매중 상품: {stats['on_sale']}")
        print(f"🛑 단품 품절 상품: {stats['soldout_single']}")
        print(f"🔴 옵션 품절 개수: {stats['soldout_option']}")
        print(f"🔧 수정 필요 상품 (일부 옵션 품절): {stats['modified']}")

    def save_four_files(self, output_dir: str = "."):
        """4개의 분리된 텍스트 파일 생성"""
        if not self.data:
            print("❌ 데이터가 로드되지 않았습니다.")
            return False

        try:
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)

            single_soldout = self.extract_single_soldout_ids()
            option_soldout = self.extract_option_soldout_ids()
            successful = self.extract_successful_ids()
            stats = self.get_statistics()

            # 1. 단품 판매 종료 상품 ID
            file1 = output_path / "1_single_soldout_ids.txt"
            with open(file1, 'w', encoding='utf-8') as f:
                f.write("=== 단품인데 판매 종료된 상품 ID ===\n")
                f.write(f"총 {len(single_soldout)}개\n\n")
                for product_id in single_soldout:
                    f.write(f"oliveyoung_{product_id}\n")
            print(f"✅ 파일 1 생성: {file1} ({len(single_soldout)}개)")

            # 2. 옵션 판매 종료 상품 (옵션별)
            file2 = output_path / "2_option_soldout_ids.txt"
            with open(file2, 'w', encoding='utf-8') as f:
                f.write("=== 옵션 상품 중 품절된 옵션 ID (옵션별) ===\n")
                f.write(f"총 {len(option_soldout)}개\n\n")
                for option_id in option_soldout:
                    f.write(f"oliveyoung_{option_id}\n")
            print(f"✅ ���일 2 생성: {file2} ({len(option_soldout)}개)")

            # 3. 성공한 상품 ID
            file3 = output_path / "3_successful_ids.txt"
            with open(file3, 'w', encoding='utf-8') as f:
                f.write("=== 성공적으로 크롤링된 상품 ID ===\n")
                f.write(f"총 {len(successful)}개\n\n")
                for product_id in successful:
                    f.write(f"oliveyoung_{product_id}\n")
            print(f"✅ 파일 3 생성: {file3} ({len(successful)}개)")

            # 4. 전체 통계
            file4 = output_path / "4_statistics.txt"
            with open(file4, 'w', encoding='utf-8') as f:
                f.write("=== 전체 통계 ===\n\n")
                f.write(f"처리된 총 상품 수: {stats['total']}\n\n")

                f.write(f"✅ 성공 ID ({len(stats['successful_ids'])}개)\n")
                for pid in stats['successful_ids']:
                    f.write(f"  oliveyoung_{pid}\n")

                f.write(f"\n❌ 실패 ID ({len(stats['failed_ids'])}개)\n")
                for pid in stats['failed_ids']:
                    f.write(f"  oliveyoung_{pid}\n")

                f.write(f"\n💚 판매중 ID ({len(stats['on_sale_ids'])}개)\n")
                for pid in stats['on_sale_ids']:
                    f.write(f"  oliveyoung_{pid}\n")

                f.write(f"\n🛑 판매종료 단품 ID ({len(stats['soldout_single_ids'])}개)\n")
                for pid in stats['soldout_single_ids']:
                    f.write(f"  oliveyoung_{pid}\n")

                f.write(f"\n🔴 판매종료 옵션 ID ({len(stats['soldout_option_ids'])}개)\n")
                for pid in stats['soldout_option_ids']:
                    f.write(f"  oliveyoung_{pid}\n")

                f.write(f"\n🔧 수정 상품 ID (일부 옵션 품절) ({len(stats['modified_ids'])}개)\n")
                for pid in stats['modified_ids']:
                    f.write(f"  oliveyoung_{pid}\n")

            print(f"✅ 파일 4 생성: {file4}")

            # 5. 단품 가격 변경 파일
            # 6. 옵션 가격 변경 파일
            if self.excel_price_map:
                price_changed = self.extract_price_changed_products()
                single_changed = price_changed['single']
                option_changed = price_changed['option']

                # 5. 단품 가격 변경
                file5 = output_path / "5_price_changed_single.txt"
                with open(file5, 'w', encoding='utf-8') as f:
                    f.write("=== 단품 상품 가격 변경 ===\n")
                    f.write(f"총 {len(single_changed)}개\n\n")

                    f.write("## 상품 ID 목록 (Excel 복사용)\n")
                    for product_id, old_price, new_price in single_changed:
                        f.write(f"oliveyoung_{product_id}\n")

                    f.write("\n## 새 가격(엔화) 목록 (Excel 복사용)\n")
                    for product_id, old_price, new_price in single_changed:
                        f.write(f"{new_price}\n")

                    f.write("\n## 상세 정보\n")
                    for product_id, old_price, new_price in single_changed:
                        diff = new_price - old_price
                        sign = "+" if diff > 0 else ""
                        f.write(f"oliveyoung_{product_id}: {old_price}엔 → {new_price}엔 ({sign}{diff}엔)\n")

                print(f"✅ 파일 5 생성: {file5} ({len(single_changed)}개)")

                # 6. 옵션 가격 변경
                file6 = output_path / "6_price_changed_option.txt"
                with open(file6, 'w', encoding='utf-8') as f:
                    f.write("=== 옵션 상품 가격 변경 ===\n")
                    f.write(f"총 {len(option_changed)}개\n\n")

                    f.write("## 상품 ID 목록 (Excel 복사용)\n")
                    for product_id, option_id, old_price, new_price in option_changed:
                        f.write(f"oliveyoung_{product_id}\n")

                    f.write("\n## 옵션 ID 목록 (Excel 복사용)\n")
                    for product_id, option_id, old_price, new_price in option_changed:
                        f.write(f"oliveyoung_{option_id}\n")

                    f.write("\n## 새 가격(엔화) 목록 (Excel 복사용)\n")
                    for product_id, option_id, old_price, new_price in option_changed:
                        f.write(f"{new_price}\n")

                    f.write("\n## 상세 정보\n")
                    for product_id, option_id, old_price, new_price in option_changed:
                        diff = new_price - old_price
                        sign = "+" if diff > 0 else ""
                        f.write(f"oliveyoung_{product_id} / oliveyoung_{option_id}: {old_price}엔 → {new_price}엔 ({sign}{diff}엔)\n")

                print(f"✅ 파일 6 생성: {file6} ({len(option_changed)}개)")

            # 7. 단품 복구 상품 (품절→판매중)
            # 8. 옵션 복구 상품
            file_count = 6 if self.excel_price_map else 4

            if self.excel_quantity_map:
                restocked = self.extract_restocked_products()
                single_restocked = restocked['single']
                option_restocked = restocked['option']

                # 7. 단품 복구
                file7 = output_path / "7_restocked_single.txt"
                with open(file7, 'w', encoding='utf-8') as f:
                    f.write("=== 단품 복구 (품절→판매중) ===\n")
                    f.write(f"총 {len(single_restocked)}개\n\n")

                    f.write("## 상품 ID 목록 (Excel 복사용)\n")
                    for product_id, old_qty, new_status in single_restocked:
                        f.write(f"oliveyoung_{product_id}\n")

                    f.write("\n## 상세 정보\n")
                    for product_id, old_qty, new_status in single_restocked:
                        f.write(f"oliveyoung_{product_id}: 품절(재고={old_qty}) → {new_status}\n")

                print(f"✅ 파일 7 생성: {file7} ({len(single_restocked)}개)")

                # 8. 옵션 복구
                file8 = output_path / "8_restocked_option.txt"
                with open(file8, 'w', encoding='utf-8') as f:
                    f.write("=== 옵션 복구 (품절→판매중) ===\n")
                    f.write(f"총 {len(option_restocked)}개\n\n")

                    f.write("## 상품 ID 목록 (Excel 복사용)\n")
                    for product_id, option_id, old_qty, new_status in option_restocked:
                        f.write(f"oliveyoung_{product_id}\n")

                    f.write("\n## 옵션 ID 목록 (Excel 복사용)\n")
                    for product_id, option_id, old_qty, new_status in option_restocked:
                        f.write(f"oliveyoung_{option_id}\n")

                    f.write("\n## 상세 정보\n")
                    for product_id, option_id, old_qty, new_status in option_restocked:
                        f.write(f"oliveyoung_{product_id} / oliveyoung_{option_id}: 품절(재고={old_qty}) → {new_status}\n")

                print(f"✅ 파일 8 생성: {file8} ({len(option_restocked)}개)")

                file_count += 2

            # 9. 삭제 가능성 상품
            deleted = self.extract_deleted_products()
            deleted_products = deleted['single']

            file9 = output_path / "9_deleted_products.txt"
            with open(file9, 'w', encoding='utf-8') as f:
                f.write("=== 삭제 가능성 상품 (크롤링 실패) ===\n")
                f.write(f"총 {len(deleted_products)}개\n\n")

                f.write("## 상품 ID 목록 (Excel 복사용)\n")
                for product_id, status, error in deleted_products:
                    f.write(f"oliveyoung_{product_id}\n")

                f.write("\n## 상세 정보\n")
                for product_id, status, error in deleted_products:
                    f.write(f"oliveyoung_{product_id}: {status} - {error}\n")

            print(f"✅ 파일 9 생성: {file9} ({len(deleted_products)}개)")
            file_count += 1

            print(f"\n🎉 총 {file_count}개 파일 생성 완료!")
            return True

        except Exception as e:
            print(f"❌ 파일 저장 실패: {str(e)}")
            return False


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description='크롤링 결과 분석 및 파일 생성 (가격 비교 포함)')
    parser.add_argument('input_file', nargs='?', default='olive_young_products.json',
                       help='크롤링 결과 JSON 파일 (기본값: olive_young_products.json)')
    parser.add_argument('--excel', '-e', default='data/Qoo10_ItemInfo.xlsx',
                       help='Excel 파일 경로 (기본값: data/Qoo10_ItemInfo.xlsx)')
    parser.add_argument('--output-dir', '-o', default='.',
                       help='출력 디렉토리 (기본값: 현재 디렉토리)')
    parser.add_argument('--stats-only', action='store_true',
                       help='통계만 출력하고 파일 저장하지 않음')

    args = parser.parse_args()

    # 분석기 초기화 및 데이터 로드
    analyzer = CrawlingResultAnalyzer(args.input_file, args.excel)

    if not analyzer.load_data():
        return 1

    # Excel 가격 정보 로드 (옵션)
    analyzer.load_excel_prices()

    # 통계 출력
    analyzer.print_statistics()

    # 가격 변경 통계
    if analyzer.excel_price_map:
        price_changed = analyzer.extract_price_changed_products()
        single_count = len(price_changed['single'])
        option_count = len(price_changed['option'])
        print(f"💰 가격 변경 - 단품: {single_count}개, 옵션: {option_count}개")

    # 복구 상품 통계
    if analyzer.excel_quantity_map:
        restocked = analyzer.extract_restocked_products()
        single_restocked_count = len(restocked['single'])
        option_restocked_count = len(restocked['option'])
        print(f"🔄 품절→판매중 복구 - 단품: {single_restocked_count}개, 옵션: {option_restocked_count}개")

    # 삭제 가능성 통계
    deleted = analyzer.extract_deleted_products()
    deleted_count = len(deleted['single'])
    print(f"🗑️  삭제 가능성 상품: {deleted_count}개")

    if not args.stats_only:
        # 파일 생성
        file_count = '6' if analyzer.excel_price_map else '4'
        print(f"\n💾 {file_count}개 파일 생성 중...")
        analyzer.save_four_files(args.output_dir)

    return 0


if __name__ == "__main__":
    exit(main())
