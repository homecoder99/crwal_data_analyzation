"""
크롤링 결과 분석 도구
단품/옵션 상품 구분하여 4개 파일 생성
"""
import json
import argparse
from typing import List, Dict, Tuple
from pathlib import Path


class CrawlingResultAnalyzer:
    def __init__(self, result_file: str = "olive_young_products.json"):
        """
        크롤링 결과 분석기 초기화

        Args:
            result_file: 크롤링 결과 JSON 파일 경로
        """
        self.result_file = result_file
        self.data = None

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
                    f.write(f"{product_id}\n")
            print(f"✅ 파일 1 생성: {file1} ({len(single_soldout)}개)")

            # 2. 옵션 판매 종료 상품 (옵션별)
            file2 = output_path / "2_option_soldout_ids.txt"
            with open(file2, 'w', encoding='utf-8') as f:
                f.write("=== 옵션 상품 중 품절된 옵션 ID (옵션별) ===\n")
                f.write(f"총 {len(option_soldout)}개\n\n")
                for option_id in option_soldout:
                    f.write(f"{option_id}\n")
            print(f"✅ ���일 2 생성: {file2} ({len(option_soldout)}개)")

            # 3. 성공한 상품 ID
            file3 = output_path / "3_successful_ids.txt"
            with open(file3, 'w', encoding='utf-8') as f:
                f.write("=== 성공적으로 크롤링된 상품 ID ===\n")
                f.write(f"총 {len(successful)}개\n\n")
                for product_id in successful:
                    f.write(f"{product_id}\n")
            print(f"✅ 파일 3 생성: {file3} ({len(successful)}개)")

            # 4. 전체 통계
            file4 = output_path / "4_statistics.txt"
            with open(file4, 'w', encoding='utf-8') as f:
                f.write("=== 전체 통계 ===\n\n")
                f.write(f"처리된 총 상품 수: {stats['total']}\n\n")

                f.write(f"✅ 성공 ID ({len(stats['successful_ids'])}개)\n")
                for pid in stats['successful_ids']:
                    f.write(f"  {pid}\n")

                f.write(f"\n❌ 실패 ID ({len(stats['failed_ids'])}개)\n")
                for pid in stats['failed_ids']:
                    f.write(f"  {pid}\n")

                f.write(f"\n💚 판매중 ID ({len(stats['on_sale_ids'])}개)\n")
                for pid in stats['on_sale_ids']:
                    f.write(f"  {pid}\n")

                f.write(f"\n🛑 판매종료 단품 ID ({len(stats['soldout_single_ids'])}개)\n")
                for pid in stats['soldout_single_ids']:
                    f.write(f"  {pid}\n")

                f.write(f"\n🔴 판매종료 옵션 ID ({len(stats['soldout_option_ids'])}개)\n")
                for pid in stats['soldout_option_ids']:
                    f.write(f"  {pid}\n")

                f.write(f"\n🔧 수정 상품 ID (일부 옵션 품절) ({len(stats['modified_ids'])}개)\n")
                for pid in stats['modified_ids']:
                    f.write(f"  {pid}\n")

            print(f"✅ 파일 4 생성: {file4}")

            print(f"\n🎉 총 4개 파일 생성 완료!")
            return True

        except Exception as e:
            print(f"❌ 파일 저장 실패: {str(e)}")
            return False


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description='크롤링 결과 분석 및 4개 파일 생성')
    parser.add_argument('input_file', nargs='?', default='olive_young_products.json',
                       help='크롤링 결과 JSON 파일 (기본값: olive_young_products.json)')
    parser.add_argument('--output-dir', '-o', default='.',
                       help='출력 디렉토리 (기본값: 현재 디렉토리)')
    parser.add_argument('--stats-only', action='store_true',
                       help='통계만 출력하고 파일 저장하지 않음')

    args = parser.parse_args()

    # 분석기 초기화 및 데이터 로드
    analyzer = CrawlingResultAnalyzer(args.input_file)

    if not analyzer.load_data():
        return 1

    # 통계 출력
    analyzer.print_statistics()

    if not args.stats_only:
        # 4개 파일 생성
        print(f"\n💾 4개 파일 생성 중...")
        analyzer.save_four_files(args.output_dir)

    return 0


if __name__ == "__main__":
    exit(main())
