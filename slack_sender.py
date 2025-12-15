import pandas as pd
import requests
import json
import os
from datetime import datetime

# ======================================================
# [보안 설정] GitHub Secrets에서 'SLACK_WEBHOOK_URLS'라는 이름으로 가져옵니다.
# ======================================================
webhook_env = os.environ.get("SLACK_WEBHOOK_URLS", "")

if webhook_env:
    # 콤마(,)로 구분된 주소를 잘라서 리스트로 만듭니다.
    SLACK_WEBHOOK_LIST = [url.strip() for url in webhook_env.split(',') if url.strip()]
else:
    # 만약 Secrets 설정이 없다면 빈 리스트
    SLACK_WEBHOOK_LIST = []

CSV_FILE = "electlink_voc.csv"
DASHBOARD_URL = "https://sk-electlink-monitor-aj2cncmpcwo8rm3muzrylw.streamlit.app/"
# ======================================================

def send_daily_report():
    today_str = datetime.now().strftime("%Y-%m-%d")
    print(f"📅 기준 날짜: {today_str}")

    if not SLACK_WEBHOOK_LIST:
        print("❌ 오류: 슬랙 웹훅 URL을 찾을 수 없습니다. (GitHub Secrets 설정을 확인하세요)")
        # 로컬 테스트용이라면 여기에 주소를 임시로 넣어서 테스트하세요.
        return

    # CSV 파일 읽기
    try:
        df = pd.read_csv(CSV_FILE)
    except FileNotFoundError:
        print("❌ 데이터 파일이 없습니다.")
        return

    today_df = df[df['작성일'].str.contains(today_str, na=False)]

    sk_keywords = ["SK일렉링크", "일렉링크"]
    comp_keywords = ["워터", "채비", "이브이시스"]

    sk_df = today_df[today_df['키워드'].isin(sk_keywords)]
    comp_df = today_df[today_df['키워드'].isin(comp_keywords)]

    sk_count = len(sk_df)
    comp_count = len(comp_df)

    message = f"📢 *[{today_str}] SK일렉링크 일일 모니터링*\n\n"
    message += f"오늘자 SK일렉링크 커뮤니티 언급된 수는 *{sk_count}건*입니다 (경쟁사는 {comp_count}건입니다)\n\n"
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