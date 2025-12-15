# app.py (수정 완료 버전)
import streamlit as st
import pandas as pd

# 1. 페이지 설정
st.set_page_config(page_title="SK일렉링크 VOC 대시보드", layout="wide")

st.title("🔋 [SK일렉링크] 커뮤니티 모니터링")
st.caption("전기차 동호회/카페의 1일간 최신 글을 크롤링한 후 보여집니다.")
st.markdown("---")

# 2. 데이터 불러오기
try:
    df = pd.read_csv("electlink_voc.csv")
    
    # [중요] CSV가 꼬였을 경우를 대비해 컬럼 확인
    if "카페명" not in df.columns:
        st.error("CSV 파일 형식이 맞지 않습니다. 기존 'electlink_voc.csv' 파일을 삭제 후 크롤러를 다시 실행해주세요.")
        st.stop()
        
except FileNotFoundError:
    st.error("데이터 파일이 없습니다. 크롤러(crawler.py)를 먼저 실행해주세요.")
    st.stop()

# 3. 화면에 보여줄 컬럼 선택 (순서대로)
# 작성일 | 카페명 | 제목 | 링크
display_columns = ["작성일", "카페명", "제목", "링크"]
df_display = df[display_columns]

# 4. KPI 요약
col1, col2, col3 = st.columns(3)
total_count = len(df)
issue_keywords = ["고장", "오류", "실패", "안됨", "불편", "느림", "점검", "대기", "화남", "비싸"]
issue_df = df[df['제목'].str.contains('|'.join(issue_keywords), na=False)]

with col1:
    st.metric("수집된 최신글", f"{total_count} 건")
with col2:
    st.metric("🚨 이슈 의심", f"{len(issue_df)} 건", delta_color="inverse")
with col3:
    # 수집시점이 있으면 보여주고 없으면 현재 시간 근처로 표시
    last_time = df['수집시점'].iloc[-1] if '수집시점' in df.columns else "방금 전"
    st.write(f"최근 업데이트: {last_time}")

# 5. 🚨 이슈 리스트 (카드 형태)
st.subheader("🚨 주요 이슈 (즉시 확인 필요 - 부정적인 글들)")
if not issue_df.empty:
    for index, row in issue_df.iterrows():
        # 카페명과 제목을 강조해서 보여줌
        with st.expander(f"⚠️ [{row['카페명']}] {row['제목']}"):
            st.write(f"**작성일:** {row['작성일']}")
            st.link_button("게시글 보러가기 👉", row['링크'])
else:
    st.success("현재 발견된 특이 이슈가 없습니다.")

st.markdown("---")

# 6. 📋 전체 리스트 (테이블)
st.subheader("📋 전체 최신 글 리스트")

st.data_editor(
    df_display,
    column_config={
        "링크": st.column_config.LinkColumn(
            "링크", 
            help="클릭하면 해당 카페 글로 이동합니다.",
            display_text="바로가기" 
        ),
        "작성일": st.column_config.TextColumn("작성일", width="medium"),
        "카페명": st.column_config.TextColumn("카페명", width="medium"),
        "제목": st.column_config.TextColumn("제목", width="large"),
    },
    hide_index=True,
    use_container_width=True
)

# 새로고침 버튼
if st.button('데이터 새로고침'):
    st.rerun()