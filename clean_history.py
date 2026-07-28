# 기존 electlink_voc.csv를 voc_filters 규칙으로 1회 소급 정리하는 스크립트 (실행 전 백업 생성)
import shutil

import pandas as pd

from voc_filters import is_excluded_post, is_relevant, canonicalize_link

FILE_NAME = "electlink_voc.csv"
BACKUP_NAME = "electlink_voc.cleanup-bak.csv"

df = pd.read_csv(FILE_NAME)
shutil.copyfile(FILE_NAME, BACKUP_NAME)
print(f"백업 생성: {BACKUP_NAME} ({len(df)}행)")

before_counts = df['키워드'].value_counts()

# 1) 링크 정규화 (?art= 토큰 제거)
df['링크'] = df['링크'].astype(str).map(canonicalize_link)

# 2) 필터 적용 — 유튜브(영상/댓글) 행은 주제 검색 기반이라 제외, 네이버 행만 판정
is_naver = ~df['키워드'].astype(str).str.contains("유튜브", na=False)
titles = df['제목'].astype(str)

sale_mask = is_naver & titles.map(is_excluded_post)
relevant_mask = df.apply(lambda r: is_relevant(str(r['키워드']), str(r['제목'])), axis=1)
irrelevant_mask = is_naver & ~sale_mask & ~relevant_mask

df_kept = df[~(sale_mask | irrelevant_mask)].copy()

# 3) 중복 제거 — (키워드, 링크) 기준, 먼저 수집된 행 유지
dup_before = len(df_kept)
df_kept = df_kept.drop_duplicates(subset=['키워드', '링크'], keep='first')
dup_removed = dup_before - len(df_kept)

df_kept.to_csv(FILE_NAME, index=False, encoding="utf-8-sig")

print(f"\n판매/거래/주식 글 제거: {sale_mask.sum()}행")
print(f"브랜드 무관 글 제거: {irrelevant_mask.sum()}행")
print(f"중복 제거: {dup_removed}행")
print(f"합계: {len(df)}행 -> {len(df_kept)}행")

print("\n[키워드별 변화]")
after_counts = df_kept['키워드'].value_counts()
for kw in before_counts.index:
    print(f"  {kw}: {before_counts[kw]} -> {after_counts.get(kw, 0)}")
