"""
크롤링 결과 분석 도구
soldOut 상품과 에러 발생 상품 ID 추출
"""
import json
import argparse
from typing import List, Dict
from pathlib import Path


class CrawlingResultAnalyzer:
    def __init__(self, result_file: str = "crawled_data.json"):
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
    
    def extract_soldout_ids(self) -> List[str]:
        """판매 종료된 상품 ID 추출"""
        if not self.data or 'products' not in self.data:
            return []
            
        soldout_ids = []
        
        for product in self.data['products']:
            # product_status가 soldOut인 경우
            if product.get('product_status') == 'soldOut':
                soldout_ids.append(product['product_id'])
        
        return soldout_ids
    
    def extract_error_ids(self) -> Dict[str, List[str]]:
        """에러가 발생한 상품 ID를 에러 유형별로 추출"""
        if not self.data or 'products' not in self.data:
            return {}
            
        error_ids = {
            'timeout': [],
            'unknown': [],
            'failed': []
        }
        
        for product in self.data['products']:
            product_id = product['product_id']
            status = product.get('status')
            product_status = product.get('product_status')
            
            # 다양한 에러 상태 확인
            if status == 'timeout':
                error_ids['timeout'].append(product_id)
            elif product_status == 'unknown':
                error_ids['unknown'].append(product_id)
            elif 'error' in product:
                error_ids['failed'].append(product_id)
        
        return error_ids
    
    def get_successful_ids(self) -> List[str]:
        """성공적으로 크롤링된 상품 ID 추출"""
        if not self.data or 'products' not in self.data:
            return []
            
        successful_ids = []
        
        for product in self.data['products']:
            product_status = product.get('product_status')
            status = product.get('status')
            
            # 정상적으로 크롤링되고 판매 상태를 확인할 수 있는 경우
            if (product_status in ['saleOn', 'soldOut'] and 
                status != 'timeout'):
                successful_ids.append(product['product_id'])
        
        return successful_ids
    
    def print_statistics(self):
        """크롤링 결과 통계 출력"""
        if not self.data:
            print("❌ 데이터가 로드되지 않았습니다.")
            return
            
        soldout_ids = self.extract_soldout_ids()
        error_ids = self.extract_error_ids()
        successful_ids = self.get_successful_ids()
        
        total_products = len(self.data.get('products', []))
        total_errors = sum(len(ids) for ids in error_ids.values())
        
        print("\n" + "="*60)
        print("📊 크롤링 결과 통계")
        print("="*60)
        
        # 메타데이터 정보
        if 'metadata' in self.data:
            metadata = self.data['metadata']
            print(f"📅 크롤링 일시: {metadata.get('timestamp', 'N/A')}")
            if 'stats' in metadata:
                stats = metadata['stats']
                print(f"📈 전체 통계: {stats}")
        
        print(f"\n🔍 처리된 총 상품 수: {total_products}")
        print(f"✅ 성공적으로 처리된 상품: {len(successful_ids)}")
        print(f"🛑 판매 종료된 상품: {len(soldout_ids)}")
        print(f"❌ 에러 발생 상품: {total_errors}")
        
        # 에러 유형별 상세 통계
        print(f"\n🔍 에러 유형별 상세:")
        for error_type, ids in error_ids.items():
            if ids:
                print(f"  - {error_type}: {len(ids)}개")
    
    def save_extracted_ids(self, output_file: str = "extracted_ids.json"):
        """추출된 ID들을 파일로 저장"""
        if not self.data:
            print("❌ 데이터가 로드되지 않았습니다.")
            return False
            
        try:
            soldout_ids = self.extract_soldout_ids()
            error_ids = self.extract_error_ids()
            successful_ids = self.get_successful_ids()
            
            extracted_data = {
                'extraction_timestamp': self.data.get('metadata', {}).get('timestamp', 'N/A'),
                'source_file': self.result_file,
                'summary': {
                    'total_products': len(self.data.get('products', [])),
                    'successful_count': len(successful_ids),
                    'soldout_count': len(soldout_ids),
                    'error_count': sum(len(ids) for ids in error_ids.values())
                },
                'soldout_ids': soldout_ids,
                'error_ids': error_ids,
                'successful_ids': successful_ids,
                'soldout_details': []
            }
            
            # 판매 종료 상품의 상세 정보 추가
            for product in self.data.get('products', []):
                if product.get('product_status') == 'soldOut':
                    extracted_data['soldout_details'].append({
                        'product_id': product['product_id'],
                        'soldout_reason': product.get('soldout_reason', 'unknown'),
                        'url': product.get('url', ''),
                        'timestamp': product.get('timestamp', '')
                    })
            
            # JSON 파일 저장
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(extracted_data, f, ensure_ascii=False, indent=2)
                
            print(f"✅ 추출된 데이터 저장 완료: {output_file}")
            
            # 엑셀 복사 전용 텍스트 파일도 생성
            self._save_ids_as_text(soldout_ids, error_ids, successful_ids, output_file)
            
            return True
            
        except Exception as e:
            print(f"❌ 데이터 저장 실패: {str(e)}")
            return False
    
    def _save_ids_as_text(self, soldout_ids: List[str], error_ids: Dict[str, List[str]], 
                         successful_ids: List[str], base_filename: str):
        """ID들을 엑셀 복사용 텍스트 파일로 저장"""
        try:
            # 파일명에서 확장자 제거하고 _for_excel.txt 추가
            base_path = Path(base_filename)
            txt_filename = str(base_path.parent / f"{base_path.stem}_for_excel.txt")
            
            with open(txt_filename, 'w', encoding='utf-8') as f:
                # 판매 종료 ID들
                f.write("=== 판매 종료된 상품 ID ===\n")
                for product_id in soldout_ids:
                    f.write(f"{product_id}\n")
                
                f.write("\n=== 성공적으로 처리된 상품 ID ===\n")
                for product_id in successful_ids:
                    f.write(f"{product_id}\n")
                
                # 에러 유형별 ID들
                for error_type, ids in error_ids.items():
                    if ids:
                        f.write(f"\n=== {error_type.upper()} 에러 상품 ID ===\n")
                        for product_id in ids:
                            f.write(f"{product_id}\n")
                            
                # 전체 ID 목록 (구분 없이)
                f.write("\n=== 모든 ID (엑셀 복사용) ===\n")
                all_ids = soldout_ids + successful_ids
                for error_type_ids in error_ids.values():
                    all_ids.extend(error_type_ids)
                
                for product_id in all_ids:
                    f.write(f"{product_id}\n")
            
            print(f"✅ 엑셀 복사용 텍스트 파일 저장: {txt_filename}")
            
        except Exception as e:
            print(f"⚠️ 텍스트 파일 저장 실패: {str(e)}")


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description='크롤링 결과 분석 및 ID 추출')
    parser.add_argument('input_file', nargs='?', default='crawled_data.json',
                       help='크롤링 결과 JSON 파일 (기본값: crawled_data.json)')
    parser.add_argument('--output', '-o', default='extracted_ids.json',
                       help='추출된 ID 저장 파일 (기본값: extracted_ids.json)')
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
        # ID 추출 및 저장
        print(f"\n💾 추출된 ID를 {args.output} 파일로 저장 중...")
        analyzer.save_extracted_ids(args.output)
        
        # 간단한 요약 출력
        soldout_ids = analyzer.extract_soldout_ids()
        error_ids = analyzer.extract_error_ids()
        
        print(f"\n🔗 빠른 확인:")
        print(f"  - 판매 종료 상품 ID 수: {len(soldout_ids)}")
        if soldout_ids:
            print(f"    예시: {', '.join(soldout_ids[:5])}{'...' if len(soldout_ids) > 5 else ''}")
            
        total_error_count = sum(len(ids) for ids in error_ids.values())
        print(f"  - 에러 발생 상품 ID 수: {total_error_count}")
        for error_type, ids in error_ids.items():
            if ids:
                print(f"    {error_type}: {len(ids)}개")
    
    return 0


if __name__ == "__main__":
    exit(main())