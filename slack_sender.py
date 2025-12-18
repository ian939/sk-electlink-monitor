import pandas as pd
import requests
import json
import os
from datetime import datetime, timedelta

# ======================================================
# [보안 설정] GitHub Secrets에서 'SLACK_WEBHOOK_URLS'라는 이름으로 가져옵니다.
# ======================================================
webhook_env = os.environ.get("SLACK_WEBHOOK_URLS", "")

if webhook_env:
    # 콤마(,)로 구분된 주소를 잘라서 리스트로 만듭니다. (따옴표 제거 로직 포함)
    raw_list = webhook_env.split(',')
    SLACK_WEBHOOK_LIST = []
    for url in raw_list:
        clean_url = url.strip().replace('"', '').replace("'", "")
        if clean_url:
            SLACK_WEBHOOK_LIST.append(clean_url)
else:
    # 만약 Secrets 설정이 없다면 빈 리스트
    SLACK_WEBHOOK_LIST = []

CSV_FILE = "electlink_voc.csv"
DASHBOARD_URL = "https://sk-electlink-monitor-aj2cncmpcwo8rm3muzrylw.streamlit.app/"
# ======================================================

def send_daily_report():
    kst_now = datetime.now() + timedelta(hours=9)
    today_str = kst_now.strftime("%Y-%m-%d")    
    print(f"📅 기준 날짜(한국시간): {today_str}")
    
    if not SLACK_WEBHOOK_LIST:
        print("❌ 오류: 슬랙 웹훅 URL을 찾을 수 없습니다. (GitHub Secrets 설정을 확인하세요)")
        return

    # CSV 파일 읽기
    try:
        df = pd.read_csv(CSV_FILE)
    except FileNotFoundError:
        print("❌ 데이터 파일이 없습니다.")
        return

    # 오늘 날짜 데이터만 필터링
    today_df = df[df['작성일'].str.contains(today_str, na=False)]

    sk_keywords = ["SK일렉링크", "일렉링크"]
    comp_keywords = ["워터", "채비", "이브이시스"]

    # 1. SK일렉링크 데이터 필터링
    sk_df = today_df[today_df['키워드'].isin(sk_keywords)]
    sk_count = len(sk_df)

    # 2. 경쟁사별 상세 카운트 계산 (여기서 수정됨 ✨)
    comp_counts = []
    for comp in comp_keywords:
        # 각 경쟁사 키워드별로 몇 개인지 셉니다.
        count = len(today_df[today_df['키워드'] == comp])
        comp_counts.append(f"{comp} {count}건")
    
    # 예: "워터 1건, 채비 0건, 이브이시스 2건" 처럼 글자로 합칩니다.
    comp_msg_str = ", ".join(comp_counts)


    # 메시지 내용 만들기
    message = f"📢 *[{today_str}] SK일렉링크 일일 모니터링*\n\n"
    
    # 수정된 부분: 경쟁사 통계를 상세 내용으로 교체
    message += f"오늘자 SK일렉링크 커뮤니티 언급된 수는 *{sk_count}건*입니다\n"
    message += f"(경쟁사 현황: {comp_msg_str})\n\n"
    
    message += f"📊 *전체 현황 대시보드 보러가기*:\n{DASHBOARD_URL}\n\n"
    message += "📝 *오늘자 당사로 언급된 키워드*\n"

    if sk_count > 0:
        for index, row in sk_df.iterrows():
            title = row['제목']
            link = row['링크']
            message += f"• <{link}|{title}>\n"
    else:
        message += "• (특이 사항 없음)\n"

    payload = {
        "text": message,
        "unfurl_links": False
    }

    print(f"🚀 총 {len(SLACK_WEBHOOK_LIST)}곳으로 전송을 시작합니다...")
    
    for i, webhook_url in enumerate(SLACK_WEBHOOK_LIST):
        # URL 유효성 간단 체크
        if not webhook_url.startswith("http"):
            continue

        try:
            response = requests.post(webhook_url, json=payload)
            if response.status_code == 200:
                print(f"   ✅ [{i+1}] 전송 성공")
            else:
                print(f"   ❌ [{i+1}] 전송 실패 ({response.status_code})")
        except Exception as e:
            print(f"   ❌ [{i+1}] 에러 발생: {e}")

if __name__ == "__main__":
    send_daily_report()
