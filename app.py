import streamlit as st
import pandas as pd

# 1. 페이지 설정
st.set_page_config(page_title="EV 충전소 여론 모니터링", layout="wide")

st.title("🔋 EV 충전소 여론 모니터링 Dashboard")
st.caption("전기차 전문 카페의 실시간 반응을 분석합니다. (SK일렉링크 vs 경쟁사)")
st.markdown("---")

# 2. 데이터 불러오기
try:
    df = pd.read_csv("electlink_voc.csv")
    # [에러 방지] 키워드 컬럼 확인
    if "키워드" not in df.columns:
        st.error("⚠️ CSV 파일 양식이 오래되었습니다. 기존 CSV를 삭제 후 crawler.py를 다시 실행해주세요.")
        st.stop()
except FileNotFoundError:
    st.error("데이터 파일이 없습니다. 크롤러를 먼저 실행해주세요.")
    st.stop()

# ---------------------------------------------------------
# [데이터 분리] SK vs 경쟁사
# ---------------------------------------------------------
sk_keywords = ["SK일렉링크", "일렉링크"]
competitor_keywords = ["워터", "채비", "이브이시스"]

# 키워드 컬럼을 기준으로 데이터 나눔
df_sk = df[df['키워드'].isin(sk_keywords)].copy()
df_comp = df[df['키워드'].isin(competitor_keywords)].copy()

# 화면에 보여줄 컬럼 설정
display_columns = ["작성일", "키워드", "카페명", "제목", "링크"]

# =========================================================
# [섹션 1] 🔵 SK일렉링크 (메인)
# =========================================================
st.subheader("🔵 SK일렉링크 최신 여론")

col1, col2, col3 = st.columns(3)
issue_keywords = ["고장", "오류", "실패", "안됨", "불편", "느림", "점검", "대기", "화남", "비싸"]
sk_issue_df = df_sk[df_sk['제목'].str.contains('|'.join(issue_keywords), na=False)]

with col1:
    st.metric("SK 수집 글", f"{len(df_sk)} 건")
with col2:
    st.metric("🚨 이슈 감지", f"{len(sk_issue_df)} 건", delta_color="inverse")
with col3:
    last_time = df['수집시점'].iloc[-1] if '수집시점' in df.columns else "-"
    st.write(f"최근 업데이트: {last_time}")

# SK 리스트 (스크롤 적용: height=300)
st.dataframe(
    df_sk[display_columns],
    column_config={
        "링크": st.column_config.LinkColumn("바로가기", display_text="Link"),
        "제목": st.column_config.TextColumn("제목", width="large"),
    },
    hide_index=True,
    use_container_width=True,
    height=300  # [핵심] 여기가 스크롤 높이 설정입니다
)

st.markdown("---")

# =========================================================
# [섹션 2] ⚔️ 경쟁사 동향 (워터/채비/EVSIS)
# =========================================================
st.subheader("⚔️ 경쟁사 최신 동향")

if not df_comp.empty:
    # 탭으로 깔끔하게 구분
    tab1, tab2, tab3, tab4 = st.tabs(["전체 보기", "워터(WATER)", "채비(CHAEVI)", "이브이시스(EVSIS)"])
    
    # 공통 설정: 경쟁사 글은 많을 수 있으니 height=400으로 스크롤바 생성
    
    with tab1: # 전체
        st.caption(f"총 {len(df_comp)}건의 경쟁사 글이 있습니다.")
        st.dataframe(
            df_comp[display_columns],
            column_config={"링크": st.column_config.LinkColumn("바로가기", display_text="Link")},
            hide_index=True, use_container_width=True, height=400
        )

    def show_competitor(brand_list):
        # 해당 브랜드 글만 필터링
        target_df = df_comp[df_comp['키워드'].isin(brand_list)]
        if target_df.empty:
            st.info("수집된 글이 없습니다.")
        else:
            st.dataframe(
                target_df[display_columns],
                column_config={"링크": st.column_config.LinkColumn("바로가기", display_text="Link")},
                hide_index=True, use_container_width=True, height=400
            )

    with tab2: show_competitor(["워터"])
    with tab3: show_competitor(["채비"])
    with tab4: show_competitor(["이브이시스"])

else:
    st.info("아직 수집된 경쟁사 데이터가 없습니다. 크롤러를 실행해 데이터를 모아주세요.")

# 새로고침
if st.button('데이터 새로고침'):
    st.rerun()