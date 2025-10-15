"""
메인 크롤링 실행기
Excel 처리와 크롤링을 통합하여 tqdm 진행률 표시
"""
import asyncio
import logging
import time
from tqdm.asyncio import tqdm
from excel_processor import ExcelProcessor
from crawler import OliveYoungCrawler

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MainCrawler:
    def __init__(self, 
                 excel_path: str = "data/Qoo10_ItemInfo.xlsx",
                 max_concurrent: int = 3,
                 delay_range: tuple = (1, 3),
                 output_file: str = "olive_young_products.json"):
        """
        메인 크롤러 초기화
        
        Args:
            excel_path: Excel 파일 경로
            max_concurrent: 최대 동시 실행 수
            delay_range: 요청 간 딜레이 범위 (초)
            output_file: 결과 저장 파일명
        """
        self.excel_path = excel_path
        self.max_concurrent = max_concurrent
        self.delay_range = delay_range
        self.output_file = output_file
        
        # 컴포넌트 초기화
        self.excel_processor = ExcelProcessor(excel_path)
        self.crawler = OliveYoungCrawler(
            max_concurrent=max_concurrent,
            delay_range=delay_range,
            output_file=output_file
        )
    
    async def run_with_progress(self):
        """진행률 표시와 함께 크롤링 실행"""
        logger.info("🎯 올리브영 상품 크롤링 시작")
        start_time = time.time()
        
        # Step 1: Excel 데이터 처리
        logger.info("📋 Step 1: Excel 데이터 처리")
        product_ids = self.excel_processor.process()
        
        if not product_ids:
            logger.error("❌ Excel에서 유효한 ID를 찾을 수 없습니다")
            return None
        
        total_ids = len(product_ids)
        logger.info(f"✅ 처리할 상품 ID: {total_ids}개")
        
        # Step 2: 크롤링 설정
        logger.info("🔧 Step 2: 크롤링 설정")
        estimated_time = total_ids * sum(self.delay_range) / 2 / self.max_concurrent
        logger.info(f"⏱️  예상 소요 시간: {estimated_time/60:.1f}분")
        
        # Step 3: 크롤링 실행 (tqdm 진행률 표시)
        logger.info("🚀 Step 3: 크롤링 실행")
        
        # tqdm을 위한 진행률 추적 변수
        progress_bar = tqdm(
            total=total_ids,
            desc="크롤링 진행",
            unit="상품",
            colour="green",
            bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]"
        )
        
        # 크롤러 통계 추적을 위한 콜백 설정
        original_check_product_availability = self.crawler.check_product_availability
        
        async def check_product_availability_with_progress(context, product_id):
            result = await original_check_product_availability(context, product_id)
            progress_bar.update(1)  # 진행률 업데이트
            
            # 실시간 통계 업데이트
            stats = self.crawler.stats
            progress_bar.set_postfix({
                '성공': stats['success'],
                '실패': stats['failed']
            })
            
            return result
        
        # 크롤러 메서드 오버라이드
        self.crawler.check_product_availability = check_product_availability_with_progress
        
        try:
            # 크롤링 실행
            results = await self.crawler.crawl_products(product_ids)
            
        finally:
            progress_bar.close()
        
        # Step 4: 결과 요약
        total_time = time.time() - start_time
        
        logger.info("=" * 80)
        logger.info("🏆 크롤링 작업 완료!")
        logger.info("=" * 80)
        logger.info(f"📊 전체 실행 시간: {total_time/60:.2f}분 ({total_time:.1f}초)")
        logger.info(f"📈 처리 속도: {total_ids/total_time:.2f} 상품/초")
        logger.info(f"✅ 성공: {results['stats']['success']}개")
        logger.info(f"❌ 실패: {results['stats']['failed']}개")
        logger.info(f"📊 성공률: {results['stats']['success']/total_ids*100:.1f}%")
        logger.info(f"💾 결과 파일: {self.output_file}")
        logger.info("=" * 80)
        
        return results
    
    def run(self):
        """동기 실행 wrapper"""
        return asyncio.run(self.run_with_progress())

def main():
    """메인 실행 함수"""
    print("🔥 올리브영 상품 크롤러 시작")
    print("=" * 80)
    
    # 설정
    config = {
        'excel_path': 'data/Qoo10_ItemInfo.xlsx',
        'max_concurrent': 5,  # 동시 실행 수 증가 (3 -> 5)
        'delay_range': (0.5, 1.5),  # 요청 간 딜레이 감소 (2-4초 -> 0.5-1.5초)
        'output_file': 'olive_young_products.json'
    }
    
    print("⚙️  크롤링 설정:")
    for key, value in config.items():
        print(f"   {key}: {value}")
    print("=" * 80)
    
    # 크롤러 실행
    main_crawler = MainCrawler(**config)
    
    try:
        results = main_crawler.run()
        
        if results:
            print("\n🎉 크롤링이 성공적으로 완료되었습니다!")
            print(f"📄 결과는 '{config['output_file']}'에서 확인할 수 있습니다.")
        else:
            print("\n❌ 크롤링 실행 중 문제가 발생했습니다.")
            
    except KeyboardInterrupt:
        print("\n⚠️  사용자에 의해 크롤링이 중단되었습니다.")
    except Exception as e:
        print(f"\n💥 예기치 못한 오류가 발생했습니다: {str(e)}")
        logger.error(f"크롤링 실행 중 오류: {str(e)}", exc_info=True)

if __name__ == "__main__":
    main()