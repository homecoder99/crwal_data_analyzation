"""
올리브영 상품 크롤러
CloudFlare Challenge 우회 기능 포함
"""
import asyncio
import logging
import json
import time
import random
import re
from typing import Dict, List, Optional, Any
from pathlib import Path
from playwright.async_api import async_playwright, Browser, Page, BrowserContext, TimeoutError as PlaywrightTimeoutError
from asyncio_throttle import Throttler
import aiofiles

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def clean_text(text: str) -> str:
    """텍스트 정리 헬퍼 함수"""
    if not text:
        return ""
    return text.strip().replace('\n', '').replace('\r', '')

def parse_price(price_text: str) -> int:
    """가격 텍스트를 정수로 파싱"""
    if not price_text:
        return 0
    # "27,600원" -> 27600
    price_str = re.sub(r'[^\d]', '', price_text)
    return int(price_str) if price_str else 0

def convert_krw_to_jpy(krw_price: int) -> int:
    """한화를 엔화로 변환 (배송비, 마진율, 환율, 끝자리 보정 포함)"""
    # 배송비 추가
    shipping_cost = 7500
    price_with_shipping = krw_price + shipping_cost

    # 마진율 적용
    margin_rate = 1.0
    price_with_margin = int(price_with_shipping * margin_rate)

    # 엔화 환율 적용
    krw_to_jpy_rate = 0.11
    price_jpy_raw = int(price_with_margin * krw_to_jpy_rate)

    # 가격 끝자리 보정 (8, 9, 0)
    return adjust_price_ending(price_jpy_raw)

def adjust_price_ending(price: int) -> int:
    """가격을 끝자리가 8, 9, 0인 값으로 자동 보정"""
    rounded_price = round(price)
    last_digit = rounded_price % 10

    if last_digit <= 4:
        adjustment = 0  # 0으로 맞춤
    elif last_digit <= 8:
        adjustment = 8  # 8로 맞춤
    else:
        adjustment = 9  # 9로 맞춤

    adjusted_price = rounded_price - last_digit + adjustment
    return adjusted_price

class OliveYoungPriceExtractor:
    """Oliveyoung 가격 정보 추출 클래스"""

    def __init__(self, logger):
        self.logger = logger

    async def extract_price_info(self, page: Page, product_data: Dict[str, Any]):
        """가격 정보 추출"""
        try:
            # 1. 판매가 추출 (필수)
            await self._extract_sale_price(page, product_data)

            # 2. 정상가 추출 및 할인 여부 판단
            await self._extract_origin_price(page, product_data)

            # 3. 엔화 가격 계산
            if product_data.get("is_discounted", False):
                # 할인가를 엔화로 변환
                krw_price = product_data.get("price", 0)
            else:
                # 정상가를 엔화로 변환
                krw_price = product_data.get("origin_price", product_data.get("price", 0))

            product_data["price_jpy"] = convert_krw_to_jpy(krw_price)
            self.logger.debug(f"Oliveyoung 엔화 가격: {product_data['price_jpy']}엔 (원화: {krw_price}원)")

        except Exception as e:
            self.logger.debug(f"Oliveyoung 가격 정보 추출 실패: {str(e)}")
            product_data["price"] = 0
            product_data["origin_price"] = 0
            product_data["is_discounted"] = False
            product_data["price_jpy"] = 0

    async def _extract_sale_price(self, page: Page, product_data: Dict[str, Any]):
        """판매가 추출"""
        price_element = page.locator('.price-2 strong')
        if await price_element.count() > 0:
            price_text = await price_element.inner_text()
            product_data["price"] = parse_price(price_text)
            self.logger.debug(f"Oliveyoung 판매가 추출: {product_data['price']}")
        else:
            self.logger.debug("Oliveyoung 판매가(.price-2 strong)를 찾을 수 없음")
            product_data["price"] = 0

    async def _extract_origin_price(self, page: Page, product_data: Dict[str, Any]):
        """정상가 추출 및 할인 여부 판단"""
        origin_price_element = page.locator('.price-1 strike')
        if await origin_price_element.count() > 0:
            # 할인 중인 경우
            origin_price_text = await origin_price_element.inner_text()
            product_data["origin_price"] = parse_price(origin_price_text)
            product_data["is_discounted"] = True
            self.logger.debug(f"Oliveyoung 정상가 추출 (할인 중): {product_data['origin_price']}")
        else:
            # 할인 없는 경우
            product_data["origin_price"] = product_data.get("price", 0)
            product_data["is_discounted"] = False
            self.logger.debug("Oliveyoung 할인 없음 - 정상가와 판매가 동일")

class OliveYoungOptionExtractor:
    """Oliveyoung 상품 옵션 정보 추출 클래스"""

    def __init__(self, logger):
        self.logger = logger

    async def extract_option_info(self, page: Page, product_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """옵션 정보 추출 - 각 옵션별 품절 상태 및 가격 검증 포함"""
        options = []

        try:
            option_button = page.locator('#buyOpt')
            if await option_button.count() == 0:
                self.logger.debug("옵션 버튼 없음 - 단품 상품")
                return options

            self.logger.debug("옵션 버튼 클릭")
            await option_button.click()

            # 옵션 목록 로딩 대기
            try:
                await page.wait_for_selector('#option_list li', timeout=8000)
                await asyncio.sleep(2)  # 2초 대기로 변경

                # 옵션 아이템 추출
                option_items = page.locator('#option_list li')
                item_count = await option_items.count()

                if item_count > 0:
                    self.logger.debug(f"옵션 {item_count}개 발견")

                    # 기본 판매가 (가격 검증용)
                    base_price = product_data.get("price", 0)
                    valid_option_count = 0

                    for i in range(min(item_count, 50)):  # 최대 50개
                        item = option_items.nth(i)

                        # 옵션명
                        option_name_element = item.locator('.option_value')
                        if await option_name_element.count() == 0:
                            continue

                        option_name = clean_text(await option_name_element.inner_text())
                        if not option_name:
                            continue

                        # 품절 여부
                        is_soldout = await item.evaluate('el => el.classList.contains("soldout")')

                        # 옵션 가격 (.tx_num 클래스)
                        option_price = 0
                        price_element = item.locator('.tx_num')
                        if await price_element.count() > 0:
                            price_text = clean_text(await price_element.inner_text())
                            price_match = re.search(r'([\d,]+)', price_text)
                            if price_match:
                                option_price = int(price_match.group(1).replace(',', ''))

                        # 가격 검증: ±50% 초과 시 제외
                        if base_price > 0 and option_price > 0:
                            additional_price = option_price - base_price
                            if additional_price < -(base_price * 0.5) or additional_price > base_price * 0.5:
                                self.logger.warning(
                                    f"옵션 가격이 상품 가격 ±50% 초과: {option_name} "
                                    f"(추가금액: {additional_price}) - 상품에서 제외"
                                )
                                continue

                        # 유효한 옵션만 추가
                        options.append({
                            "index": valid_option_count + 1,
                            "name": option_name,
                            "price": option_price,
                            "price_krw": option_price,  # 한화 가격 (옵션)
                            "is_soldout": is_soldout
                        })
                        valid_option_count += 1

                    # 옵션이 1개만 있으면 단품으로 처리
                    if len(options) == 1:
                        self.logger.info(f"옵션 1개만 존재: 단일 상품으로 변경")
                        return []  # 빈 리스트 반환하여 단품 처리

                    self.logger.debug(f"옵션 정보 추출 완료: {len(options)}개 (가격 검증 후)")

            except PlaywrightTimeoutError:
                self.logger.debug("옵션 로딩 타임아웃")

        except Exception as e:
            self.logger.debug(f"옵션 정보 추출 실패: {e}")

        return options

class OliveYoungCrawler:
    def __init__(self, 
                 max_concurrent: int = 3,
                 delay_range: tuple = (1, 3),
                 output_file: str = "crawled_data.json",
                 progress_file: str = "crawling_progress.json"):
        """
        올리브영 크롤러 초기화
        
        Args:
            max_concurrent: 최대 동시 실행 수
            delay_range: 요청 간 딜레이 범위 (초)
            output_file: 결과 저장 파일명
            progress_file: 진행 상황 저장 파일명
        """
        self.max_concurrent = max_concurrent
        self.delay_range = delay_range
        self.output_file = output_file
        self.progress_file = progress_file
        self.base_url = "https://www.oliveyoung.co.kr/store/goods/getGoodsDetail.do"
        
        # 통계 추적
        self.stats = {
            'total': 0,
            'success': 0,
            'failed': 0,
        }
        
        # 중단 플래그
        self.user_interrupted = False
        
        # 결과 저장용
        self.results = []
        
        # Throttler 설정 (동시 요청 제한)
        self.throttler = Throttler(rate_limit=max_concurrent, period=1.0)

        # 가격 추출기
        self.price_extractor = OliveYoungPriceExtractor(logger)

        # 옵션 추출기
        self.option_extractor = OliveYoungOptionExtractor(logger)


    async def create_browser_context(self, browser: Browser) -> BrowserContext:
        """CloudFlare 우회를 위한 브라우저 컨텍스트 생성"""
        logger.info("🌐 브라우저 컨텍스트 생성 중 (CloudFlare 우회 설정)")
        
        # 랜덤 User-Agent 목록
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0"
        ]
        
        context = await browser.new_context(
            user_agent=random.choice(user_agents),
            viewport={'width': 1920, 'height': 1080},
            extra_http_headers={
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'ko-KR,ko;q=0.8,en-US;q=0.5,en;q=0.3',
                'Accept-Encoding': 'gzip, deflate',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
        )
        
        # JavaScript 활성화 및 기본 설정
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });
        """)
        
        return context
    
    
    async def check_product_availability(self, context: BrowserContext, product_id: str) -> Optional[Dict]:
        """상품 판매 가능 여부 확인"""
        page = None
        try:
            async with self.throttler:
                page = await context.new_page()
                
                # 요청 간 랜덤 딜레이
                delay = random.uniform(*self.delay_range)
                await asyncio.sleep(delay)
                
                url = f"{self.base_url}?goodsNo={product_id}"
                
                start_time = time.time()
                logger.info(f"🔍 크롤링 시작: {product_id} ({url})")
                
                # 페이지 로드 (타임아웃 처리) - domcontentloaded로 변경하여 속도 개선
                try:
                    response = await page.goto(url, wait_until='domcontentloaded', timeout=15000)  # 15초 타임아웃
                    # 페이지 안정화를 위한 짧은 대기
                    await asyncio.sleep(0.5)
                except Exception as e:
                    if 'timeout' in str(e).lower():
                        logger.warning(f"⏰ 페이지 로드 타임아웃 (ID: {product_id}): {str(e)} - 다음 상품으로 계속")
                        # 타임아웃은 개별 상품 문제이므로 전체 중단하지 않음
                        return {
                            'product_id': product_id,
                            'url': url,
                            'status': 'timeout',
                            'error': str(e),
                            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                            'crawl_time': time.time() - start_time
                        }
                    else:
                        raise e
                
                if not response:
                    logger.error(f"❌ 페이지 응답 없음 (ID: {product_id})")
                    return None
                
                logger.info(f"📡 HTTP 응답 코드: {response.status} (ID: {product_id})")
                
                
                # 페이지 제목 확인
                title = await page.title()
                
                # 상품 정보 추출 (기본 정보)
                product_data = {
                    'product_id': product_id,
                    'url': url,
                    'title': title,
                    'status_code': response.status,
                    'crawl_time': time.time() - start_time,
                    'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                    'has_options': False,
                    'option_count': 0,
                    'options': []
                }

                # 물품 정상 판매 여부 확인
                try:
                    # 첫 번째 확인: 상품을 찾을 수 없는 에러 페이지
                    error_content = await page.query_selector('#error-contents.error-page.noProduct')
                    if error_content:
                        product_data['product_status'] = 'soldOut'
                        product_data['soldout_reason'] = 'product_not_found'
                    else:
                        # 가격 정보 추출
                        await self.price_extractor.extract_price_info(page, product_data)

                        # 옵션 정보 추출
                        options = await self.option_extractor.extract_option_info(page, product_data)

                        if options:
                            # 옵션 상품
                            product_data['has_options'] = True
                            product_data['option_count'] = len(options)
                            product_data['options'] = options

                            # 각 옵션별 엔화 가격 계산
                            for option in options:
                                option_krw_price = option.get('price_krw', 0)
                                option['price_jpy'] = convert_krw_to_jpy(option_krw_price)

                            # 전체 옵션이 품절인지 확인
                            all_soldout = all(opt['is_soldout'] for opt in options)
                            any_available = any(not opt['is_soldout'] for opt in options)

                            if all_soldout:
                                product_data['product_status'] = 'soldOut'
                                product_data['soldout_reason'] = 'all_options_soldout'
                            elif any_available:
                                product_data['product_status'] = 'saleOn'
                            else:
                                product_data['product_status'] = 'unknown'
                        else:
                            # 단품 상품
                            buy_button = await page.query_selector('button.btnBuy.goods_buy#cartBtn')
                            if buy_button:
                                button_style = await buy_button.get_attribute('style')
                                if button_style and 'display: none' in button_style:
                                    product_data['product_status'] = 'soldOut'
                                    product_data['soldout_reason'] = 'button_hidden'
                                else:
                                    product_data['product_status'] = 'saleOn'
                            else:
                                product_data['product_status'] = 'soldOut'
                                product_data['soldout_reason'] = 'button_not_found'

                except Exception as e:
                    logger.warning(f"⚠️  상품 판매 상태 확인 실패 (ID: {product_id}): {str(e)}")
                    product_data['product_status'] = 'unknown'
                
                logger.info(f"✅ 크롤링 완료: {product_id} ({product_data['crawl_time']:.2f}초)")
                return product_data
                
        except Exception as e:
            logger.error(f"❌ 크롤링 실패 (ID: {product_id}): {str(e)}")
            return None
            
        finally:
            if page:
                await page.close()
    
    async def save_results(self):
        """결과를 JSON 파일로 저장"""
        try:
            logger.info(f"💾 결과 저장 중: {self.output_file}")
            
            output_data = {
                'metadata': {
                    'total_crawled': len(self.results),
                    'stats': self.stats,
                    'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
                },
                'products': self.results
            }
            
            async with aiofiles.open(self.output_file, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(output_data, ensure_ascii=False, indent=2))
            
            logger.info(f"✅ 결과 저장 완료: {self.output_file}")
            
        except Exception as e:
            logger.error(f"❌ 결과 저장 실패: {str(e)}")
    
    async def save_progress(self, product_ids: List[str], processed_items: List[str], current_item: str = None):
        """진행 상황 저장"""
        try:
            # 현재 처리 중인 아이템이 있다면 processed_items에 올리지 않음
            processed_count = len(processed_items)
            remaining_items = []
            
            # 비정상 중단의 경우 현재 아이템을 다시 처리하도록 남겨둘기
            if current_item and current_item not in processed_items:
                # 현재 처리 중인 아이템을 remaining_items 맨 앞에 추가
                remaining_items.append(current_item)
                
            # 나머지 아직 처리하지 않은 아이템들 추가
            for item in product_ids:
                if item not in processed_items and item != current_item:
                    remaining_items.append(item)
            
            progress_data = {
                'total_items': len(product_ids),
                'processed_count': processed_count,
                'processed_items': processed_items,
                'remaining_items': remaining_items,
                'current_item_rescued': current_item is not None,
                'stats': self.stats,
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
            }
            
            async with aiofiles.open(self.progress_file, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(progress_data, ensure_ascii=False, indent=2))
                
        except Exception as e:
            logger.warning(f"⚠️  진행 상황 저장 실패: {str(e)}")
    
    async def load_progress(self) -> Optional[Dict]:
        """진행 상황 불러오기"""
        try:
            if Path(self.progress_file).exists():
                async with aiofiles.open(self.progress_file, 'r', encoding='utf-8') as f:
                    content = await f.read()
                    return json.loads(content)
            return None
        except Exception as e:
            logger.warning(f"⚠️  진행 상황 로드 실패: {str(e)}")
            return None
    
    async def crawl_products(self, product_ids: List[str], resume_from_progress: bool = True) -> Dict:
        """메인 크롤링 함수"""
        
        # 진행 상황에서 재시작하는 경우
        if resume_from_progress:
            progress = await self.load_progress()
            if progress:
                logger.info(f"📂 이전 진행 상황 발견: {progress['processed_count']}/{progress['total_items']} 처리됨")
                product_ids = progress['remaining_items']
                self.stats.update(progress.get('stats', {}))
                
                if not product_ids:
                    logger.info("✅ 모든 상품 처리 완료")
                    return {'stats': self.stats, 'results': self.results}
                    
                logger.info(f"🔄 남은 {len(product_ids)}개 상품부터 재시작")
            else:
                logger.info("📂 이전 진행 상황이 없어 처음부터 시작")
        
        if 'total' not in self.stats or self.stats['total'] == 0:
            self.stats['total'] = len(product_ids)
            
        logger.info(f"🚀 크롤링 시작 - 총 {len(product_ids)}개 상품")
        
        start_time = time.time()
        
        async with async_playwright() as p:
            logger.info("🌐 브라우저 시작 중...")
            
            # Chromium 브라우저 시작 (헤드리스 모드)
            browser = await p.chromium.launch(
                headless=False,
                args=[
                    '--no-sandbox',
                    '--disable-blink-features=AutomationControlled',
                    '--disable-web-security',
                    '--disable-features=VizDisplayCompositor'
                ]
            )
            
            try:
                # KeyboardInterrupt 핸들링을 위한 신호 설정
                import signal
                
                def signal_handler(signum, frame):  # pylint: disable=unused-argument
                    self.user_interrupted = True
                    logger.warning("⚠️  사용자가 크롤링을 중단했습니다. 현재까지의 결과를 저장합니다...")
                
                signal.signal(signal.SIGINT, signal_handler)
                
                context = await self.create_browser_context(browser)
                
                # 세마포어로 동시 실행 제한
                semaphore = asyncio.Semaphore(self.max_concurrent)
                
                processed_items = []
                
                # 현재 처리 중인 아이템 추적용
                current_processing_item = None
                
                async def crawl_with_semaphore(product_id: str):
                    nonlocal current_processing_item
                    
                    # 중단 신호 확인
                    if self.user_interrupted:
                        return
                        
                    async with semaphore:
                        current_processing_item = product_id  # 현재 처리 중인 아이템 설정
                        
                        try:
                            result = await self.check_product_availability(context, product_id)
                            
                            # 중단 신호 확인
                            if self.user_interrupted:
                                # 비정상 중단 - 현재 아이템을 다시 처리하도록 남겨두기
                                return
                            
                            # 정상 처리 완료
                            processed_items.append(product_id)
                            current_processing_item = None  # 처리 완료
                            
                            if result:
                                self.results.append(result)
                                if result.get('status') == 'timeout':
                                    # 타임아웃은 실패로 처리
                                    self.stats['failed'] += 1
                                else:
                                    self.stats['success'] += 1
                            else:
                                self.stats['failed'] += 1
                            
                            # 중간 저장 (10개마다)
                            if len(processed_items) % 10 == 0:
                                await self.save_results()
                                await self.save_progress(product_ids, processed_items)
                                
                        except Exception as e:
                            logger.error(f"예상치 못한 오류 발생: {str(e)}")
                            # 오류 발생 시도 현재 아이템을 다시 처리하도록 남겨두기
                
                # 모든 상품 크롤링 (순차 처리) - 중단 신호 확인
                try:
                    for i, pid in enumerate(product_ids):
                        # 중단 신호 확인
                        if self.user_interrupted:
                            remaining_count = len(product_ids) - i
                            logger.warning(f"⚠️ 사용자 중단으로 남은 {remaining_count}개 작업 중단")
                            break
                            
                        # 순차적으로 처리
                        await crawl_with_semaphore(pid)
                        
                        # 처리 후 중단 신호 재확인
                        if self.user_interrupted:
                            break
                            
                except KeyboardInterrupt:
                    self.user_interrupted = True
                    logger.warning("⚠️  KeyboardInterrupt 신호를 받았습니다.")
                
                # 중단된 경우 즉시 진행 상황 저장
                if self.user_interrupted:
                    await self.save_results()
                    await self.save_progress(product_ids, processed_items, current_processing_item)
                    
                    logger.info(f"💾 사용자 중단 - 진행 상황 저장됨: {len(processed_items)}/{len(product_ids)} 처리 완료")
                    if current_processing_item:
                        logger.info(f"🔄 현재 처리 중이던 아이템 {current_processing_item}이 다음 실행 시 재처리됩니다.")
                
                await context.close()
                
            finally:
                await browser.close()
        
        # 최종 저장 (중단되지 않은 경우에만)
        if not self.user_interrupted:
            await self.save_results()
        
        total_time = time.time() - start_time
        
        # 최종 통계
        logger.info("=" * 60)
        if self.user_interrupted:
            logger.warning("⚠️ 사용자 중단으로 크롤링 중단!")
        else:
            logger.info("🏁 크롤링 완료!")
        logger.info(f"📊 총 처리 시간: {total_time:.2f}초")
        logger.info(f"📈 성공률: {self.stats['success']}/{self.stats['total']} ({self.stats['success']/self.stats['total']*100:.1f}%)")
        logger.info(f"✅ 성공: {self.stats['success']}")
        logger.info(f"❌ 실패: {self.stats['failed']}")
        logger.info(f"💾 결과 파일: {self.output_file}")
        logger.info("=" * 60)
        
        return {
            'stats': self.stats,
            'total_time': total_time,
            'results': self.results,
            'user_interrupted': self.user_interrupted,
            'interrupted': self.user_interrupted
        }

async def main():
    """크롤러 테스트"""
    import sys
    
    # 명령행 인자로 resume 옵션 받기
    resume = '--resume' in sys.argv or '-r' in sys.argv
    
    test_ids = ["A123456", "A789012"]  # 테스트용 ID
    
    crawler = OliveYoungCrawler(
        max_concurrent=2,
        delay_range=(2, 4),
        output_file="test_results.json"
    )
    
    if resume:
        print("🔄 이전 진행 상황에서 크롤링을 재시작합니다...")
    else:
        print("🚀 새로운 크롤링을 시작합니다...")
    
    results = await crawler.crawl_products(test_ids, resume_from_progress=resume)
    
    if results['interrupted']:
        print(f"\n⚠️  크롤링이 중단되었습니다:")
        if results['user_interrupted']:
            print("   - 사용자 중단")
        print(f"\n📊 진행 상황: {results['stats']}")
        print(f"\n🔄 재시작하려면: python {sys.argv[0]} --resume")
    else:
        print(f"\n✅ 크롤링 완료: {results['stats']}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⚠️  크롤링이 사용자에 의해 중단되었습니다.")
        print("🔄 재시작하려면: python crawler.py --resume")