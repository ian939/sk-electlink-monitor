import time
import os
import pandas as pd
import subprocess 
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.keys import Keys
from datetime import datetime

# ======================================================
# [설정]
# ======================================================
FILE_NAME = "electlink_voc.csv"
SEARCH_KEYWORDS = ["일렉링크", "워터", "채비", "이브이시스"] 

# [핵심] 검색 결과가 많아 더 깊게(2~3페이지 분량) 찾아볼 키워드 지정
DEEP_SEARCH_KEYWORDS = ["워터", "채비"]

EXCLUDE_WORDS = ["팝니다", "삽니다", "매입", "크레딧", "양도", "쿠폰", "판매", "구매"]
TARGET_CAFE_KEYWORDS = ["테슬라", "전기차", "EV", "아이오닉"] 
# ======================================================

data_list = []

print(f"🚀 고성능 크롤러 시작 (일반/심층 검색 자동 전환)")
print(f"⚠️  주의: 반드시 기존 '{FILE_NAME}' 파일을 삭제하고 실행하세요!")

options = webdriver.ChromeOptions()
options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
options.add_argument("--headless")  # [중요] 화면 없이 실행
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
options.add_argument("--disable-gpu")

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
time.sleep(2)

try:
    for keyword in SEARCH_KEYWORDS:
        print(f"\n🔍 '{keyword}' 검색 중...")
        base_url = "https://search.naver.com/search.naver?ssc=tab.cafe.all&st=date&nso=so%3Add%2Cp%3Aall&query="
        driver.get(base_url + keyword)
        time.sleep(3) 

        # -----------------------------------------------------------
        # [수정] 스크롤 로직 고도화 (일반 vs 심층)
        # -----------------------------------------------------------
        if keyword in DEEP_SEARCH_KEYWORDS:
            print(f"   👉 '{keyword}'는 데이터가 많아 3페이지 분량까지 깊게 팝니다... (약 20초 소요)")
            scroll_times = 15  # [심층] 스크롤 15번 (깊게)
        else:
            scroll_times = 3   # [일반] 스크롤 3번 (빠르게)

        body = driver.find_element(By.TAG_NAME, "body")
        for i in range(scroll_times):
            body.send_keys(Keys.END)
            time.sleep(1.2) # 로딩 시간 확보
        
        time.sleep(2) # 스크롤 끝난 후 데이터 안정화 대기
        # -----------------------------------------------------------

        articles = driver.find_elements(By.CSS_SELECTOR, "li.bx")
        
        keyword_count = 0
        
        for article in articles:
            try:
                # 1. 카페명 추출
                cafe_name = ""
                try: cafe_name = article.find_element(By.CSS_SELECTOR, "a.txt_name").text
                except: 
                    try: cafe_name = article.find_element(By.CSS_SELECTOR, "a.name").text
                    except: pass

                # 2. 카페명 필터 (테슬라, 전기차, EV)
                is_target_cafe = False
                for target in TARGET_CAFE_KEYWORDS:
                    if target in cafe_name:
                        is_target_cafe = True
                        break
                if not is_target_cafe: continue

                # 3. 최신글 확인
                box_text = article.text
                if not any(x in box_text for x in ["분 전", "시간 전", "방금 전"]):
                    continue
                
                date_str = datetime.now().strftime("%Y-%m-%d") + " (New)"

                # 4. 제목/링크
                try:
                    title_ele = article.find_element(By.CSS_SELECTOR, "a.title_link")
                    title = title_ele.text
                    link = title_ele.get_attribute("href")
                except: continue

                if any(bad_word in title for bad_word in EXCLUDE_WORDS): continue

                data_list.append({
                    "작성일": date_str,
                    "키워드": keyword, 
                    "카페명": cafe_name,
                    "제목": title,
                    "링크": link,
                    "수집시점": datetime.now().strftime("%Y-%m-%d %H:%M")
                })
                # 로그가 너무 많으면 진행상황 파악이 어려우므로 5건 단위로만 출력
                # print(f"   ✅ [수집] {cafe_name} | {title[:15]}...")
                keyword_count += 1

            except Exception: continue
            
        if keyword_count == 0:
            print(f"   💨 '{keyword}' 결과 0건. (필터링 됨)")
        else:
            print(f"   ✨ '{keyword}' 완료: 총 {keyword_count}건 수집됨")
            
        time.sleep(1)

except Exception as e:
    print(f"에러 발생: {e}")
finally:
    driver.quit()

# ======================================================
# [저장 및 GitHub 자동 업로드]
# ======================================================
def auto_push_to_github():
    try:
        print("\n🐙 GitHub 업로드 시작...")
        subprocess.run(["git", "add", FILE_NAME], check=True)
        commit_message = f"Update data: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        try:
            subprocess.run(["git", "commit", "-m", commit_message], check=True)
        except subprocess.CalledProcessError:
            print("   -> (GitHub) 변경 사항 없음")
            return
        subprocess.run(["git", "push"], check=True)
        print("✅ GitHub Push 완료!")
    except Exception as e:
        print(f"❌ GitHub 업로드 실패: {e}")

if data_list:
    df_new = pd.DataFrame(data_list)
    # [중요] 컬럼 순서를 고정하여 데이터 밀림 방지
    df_new = df_new[["작성일", "키워드", "카페명", "제목", "링크", "수집시점"]]

    if os.path.exists(FILE_NAME):
        try:
            df_old = pd.read_csv(FILE_NAME)
            # 기존 파일 형식이 맞지 않으면 덮어쓰기 (데이터 밀림 방지)
            if "키워드" not in df_old.columns or "카페명" not in df_old.columns:
                 print("\n⚠️ 구버전 파일 감지! 파일을 새로 생성합니다.")
                 df_new.to_csv(FILE_NAME, mode='w', header=True, index=False, encoding="utf-8-sig")
            else:
                existing_links = df_old['링크'].tolist()
                df_final = df_new[~df_new['링크'].isin(existing_links)]
                if not df_final.empty:
                    df_final.to_csv(FILE_NAME, mode='a', header=False, index=False, encoding="utf-8-sig")
                    print(f"\n✅ 로컬 저장 완료 ({len(df_final)}건 추가)")
                    auto_push_to_github()
                else:
                    print("\n👌 새로운 글이 없습니다 (전체 중복).")
        except:
            df_new.to_csv(FILE_NAME, mode='w', header=True, index=False, encoding="utf-8-sig")
            auto_push_to_github()
    else:
        df_new.to_csv(FILE_NAME, mode='w', header=True, index=False, encoding="utf-8-sig")
        print(f"\n✅ 신규 파일 생성 완료.")
        auto_push_to_github()
else:
    print("\n💤 수집된 데이터가 없습니다.")
