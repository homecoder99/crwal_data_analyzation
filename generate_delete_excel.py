"""
삭제용 Excel 파일 생성 스크립트
10_deleted_products.txt의 상품들을 Qoo10_EditItemList.xlsx 형식으로 변환
"""
import pandas as pd
from pathlib import Path
from datetime import datetime
import shutil


def load_deleted_products(deleted_file: str):
    """삭제 대상 상품 ID 로드"""
    deleted_ids = []

    with open(deleted_file, 'r', encoding='utf-8') as f:
        in_id_section = False
        for line in f:
            line = line.strip()

            # ID 목록 섹션 시작
            if '## 상품 ID 목록' in line:
                in_id_section = True
                continue

            # 다음 섹션 시작하면 종료
            if in_id_section and line.startswith('##'):
                break

            # ID 추출
            if in_id_section and line.startswith('oliveyoung_'):
                deleted_ids.append(line)

    return deleted_ids


def create_delete_excel(template_file: str, deleted_ids: list, output_file: str):
    """삭제용 Excel 파일 생성"""

    # output 폴더 생성
    output_path = Path('output') / output_file
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 템플릿 파일 복사
    shutil.copy(template_file, str(output_path))

    # Excel 로드 (헤더는 0행, 설명은 1-3행)
    df = pd.read_excel(str(output_path), engine='openpyxl', header=0)

    # 기존 데이터 제거 (4행부터가 실제 데이터)
    # 헤더 3행(설명 포함)만 남기고 나머지 삭제

    # 새로운 DataFrame 생성
    # 헤더 3행 유지
    header_rows = df.iloc[:3].copy()

    # 삭제할 상품 데이터 생성
    delete_rows = []

    for seller_id in deleted_ids:
        row = {
            'item_number': '',  # 비워둠
            'seller_unique_item_id': seller_id,
            'category_number': '100000001',  # 예시값
            'brand_number': '',
            'item_name': '삭제 대상 상품',  # 아무값
            'item_promotion_name': '',
            'item_status_Y/N/D': 'D',  # 삭제
            'start_date': '',
            'end_date': '2099-12-31',  # 예시값
            'price_yen': 1000,  # 예시값
            'retail_price_yen': '',
            'taxrate': '',
            'quantity': 0,  # 예시값
            'option_info': '',
            'additional_option_info': '',
            'additional_option_text': '',
            'image_main_url': 'https://example.com/image.jpg',  # 예시값
            'image_other_url': '',
            'video_url': '',
            'image_option_info': '',
            'image_additional_option_info': '',
            'header_html': '',
            'footer_html': '',
            'item_description': '삭제 대상 상품',  # 예시값
            'Shipping_number': '1',  # 예시값
            'option_number': '',
            'available_shipping_date': '3',  # 예시값
            'desired_shipping_date': '',
            'search_keyword': '',
            'item_condition_type': '1',  # 예시값 (신품)
            'origin_type': '1',  # 예시값 (국내)
            'origin_region_id': '',
            'origin_country_id': '',
            'origin_others': '',
            'medication_type': '',
            'item_weight': '',
            'item_material': '',
            'model_name': '',
            'external_product_type': '',
            'external_product_id': '',
            'manufacture_date': '',
            'expiration_date_type': '',
            'expiration_date_MFD': '',
            'expiration_date_PAO': '',
            'expiration_date_EXP': '',
            'under18s_display_Y/N': '',
            'A/S_info': '',
            'buy_limit_type': '',
            'buy_limit_date': '',
            'buy_limit_qty': ''
        }
        delete_rows.append(row)

    # DataFrame 생성
    delete_df = pd.DataFrame(delete_rows)

    # 헤더 3행 + 데이터 행 결합
    final_df = pd.concat([header_rows, delete_df], ignore_index=True)

    # Excel 저장
    final_df.to_excel(str(output_path), index=False, engine='openpyxl')

    return len(deleted_ids)


def main():
    template_file = "data/Qoo10_EditItemList.xlsx"
    deleted_file = "output/10_deleted_products.txt"
    output_file = "DELETE_PRODUCTS.xlsx"

    print("🗑️  삭제용 Excel 파일 생성 중...")

    # 파일 존재 확인
    if not Path(template_file).exists():
        print(f"❌ 템플릿 파일을 찾을 수 없습니다: {template_file}")
        return

    if not Path(deleted_file).exists():
        print(f"❌ 삭제 대상 파일을 찾을 수 없습니다: {deleted_file}")
        return

    # 삭제 대상 상품 로드
    print("📋 삭제 대상 상품 로드 중...")
    deleted_ids = load_deleted_products(deleted_file)
    print(f"   총 {len(deleted_ids)}개 상품")

    if not deleted_ids:
        print("⚠️  삭제 대상 상품이 없습니다.")
        return

    # Excel 생성
    print(f"📝 Excel 파일 생성 중: {output_file}")
    count = create_delete_excel(template_file, deleted_ids, output_file)

    print(f"\n✅ 삭제용 Excel 파일 생성 완료!")
    print(f"📄 파일명: {output_file}")
    print(f"📊 총 {count}개 상품")
    print(f"\n💡 사용 방법:")
    print(f"   1. {output_file} 파일을 Qoo10에 업로드")
    print(f"   2. item_status_Y/N/D 컬럼이 'D'로 설정되어 상품 삭제됨")
    print(f"   3. seller_unique_item_id만 확인하면 됩니다")


if __name__ == "__main__":
    main()
