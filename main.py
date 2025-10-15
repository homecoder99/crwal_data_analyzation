"""
올리브영 상품 크롤러 메인 실행 파일
"""
from main_crawler import main as run_crawler

def main():
    """메인 실행 함수"""
    print("🌟 올리브영 상품 정보 크롤러")
    print("Excel 파일에서 상품 ID를 추출하여 올리브영 사이트를 크롤링합니다.")
    print()
    
    # 메인 크롤러 실행
    run_crawler()

if __name__ == "__main__":
    main()
