"""
일회성 스크립트: 일부 옵션만 품절된 상품의 복구
Excel에서 quantity=0으로 전체 품절 처리되었지만,
실제로는 일부 옵션이 판매 가능한 상품들을 찾아서 복구 목록 생성
"""
import json
import pandas as pd
from pathlib import Path


def find_partial_soldout_products(json_file: str, excel_file: str):
    """일부 옵션만 품절된 상품 찾기"""

    # 크롤링 결과 로드
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Excel 로드
    df = pd.read_excel(excel_file, engine='openpyxl')

    restore_candidates = []

    for product in data['products']:
        product_id = product['product_id']

        # 옵션 상품만 확인
        if not product.get('has_options', False):
            continue

        # Excel에서 해당 상품 찾기
        excel_row = df[df['seller_unique_item_id'] == f'oliveyoung_{product_id}']
        if excel_row.empty:
            continue

        excel_quantity = excel_row.iloc[0].get('quantity', -1)

        # Excel quantity가 0인 경우만 (전체 품절 처리된 경우)
        if excel_quantity != 0:
            continue

        # 옵션 확인
        options = product.get('options', [])
        if not options:
            continue

        # 판매 가능한 옵션 수 확인
        available_options = [opt for opt in options if not opt.get('is_soldout', True)]
        soldout_options = [opt for opt in options if opt.get('is_soldout', True)]

        # 일부 옵션이라도 판매 가능한 경우
        if len(available_options) > 0:
            restore_candidates.append({
                'product_id': product_id,
                'total_options': len(options),
                'available_options': len(available_options),
                'soldout_options': len(soldout_options),
                'available_option_ids': [f"{product_id}_{opt['index']}" for opt in available_options]
            })

    return restore_candidates


def save_restore_list(candidates, output_file: str):
    """복구 대상 목록 저장"""

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("=" * 70 + "\n")
        f.write("일회성 복구: 일부 옵션만 품절된 상품 (Excel quantity=0 복구)\n")
        f.write("=" * 70 + "\n\n")

        f.write(f"총 {len(candidates)}개 상품\n\n")

        f.write("⚠️  주의사항:\n")
        f.write("이 상품들은 Excel에서 quantity=0으로 전체 품절 처리되었지만,\n")
        f.write("실제로는 일부 옵션이 판매 가능합니다.\n")
        f.write("quantity를 복구하여 판매 가능 상태로 변경하세요.\n\n")

        f.write("=" * 70 + "\n")
        f.write("복구 방법:\n")
        f.write("=" * 70 + "\n")
        f.write("1. 아래 상품 ID 목록을 Excel에서 찾기\n")
        f.write("2. quantity를 0 → 1로 변경 (판매 가능 표시)\n")
        f.write("3. 각 옵션별 재고는 option_info에 이미 올바르게 설정되어 있음\n\n")

        f.write("=" * 70 + "\n")
        f.write("상품 ID 목록 (Excel 복사용)\n")
        f.write("=" * 70 + "\n")
        for candidate in candidates:
            f.write(f"oliveyoung_{candidate['product_id']}\n")

        f.write("\n" + "=" * 70 + "\n")
        f.write("상세 정보\n")
        f.write("=" * 70 + "\n\n")

        for candidate in candidates:
            f.write(f"상품 ID: oliveyoung_{candidate['product_id']}\n")
            f.write(f"  전체 옵션: {candidate['total_options']}개\n")
            f.write(f"  판매 가능: {candidate['available_options']}개 ✅\n")
            f.write(f"  품절: {candidate['soldout_options']}개 ❌\n")
            f.write(f"  판매 가능 옵션 ID: {', '.join(candidate['available_option_ids'])}\n")
            f.write("\n")

    print(f"✅ 복구 대상 목록 저장: {output_file}")
    print(f"📊 총 {len(candidates)}개 상품이 복구 대상입니다")


def main():
    json_file = "olive_young_products.json"
    excel_file = "data/Qoo10_ItemInfo.xlsx"
    output_file = "RESTORE_PARTIAL_SOLDOUT.txt"

    print("🔍 일부 옵션만 품절된 상품 검색 중...")
    candidates = find_partial_soldout_products(json_file, excel_file)

    if candidates:
        save_restore_list(candidates, output_file)
        print(f"\n💡 {output_file} 파일을 확인하여 Excel을 업데이트하세요!")
    else:
        print("✅ 복구 대상 상품이 없습니다.")


if __name__ == "__main__":
    main()
