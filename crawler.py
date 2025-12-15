import time
import os
import pandas as pd
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
SEARCH_KEYWORDS = ["일렉링크"] 
EXCLUDE_WORDS = ["팝니다", "삽니다", "매입", "크레딧", "양도", "쿠폰"]
TARGET_CAFE_KEYWORDS = ["테슬라", "전기차", "EV"] # 카페명 필터
# ======================================================

data_list = []

print(f"🚀 크롤링 시작 (저장 순서: 작성일 / 카페명 / 제목 / 링크)")

options = webdriver.ChromeOptions()
options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
time.sleep(2)

try:
    for keyword in SEARCH_KEYWORDS:
        print(f"\n🔍 '{keyword}' 검색 중...")
        base_url = "https://search.naver.com/search.naver?ssc=tab.cafe.all&st=date&nso=so%3Add%2Cp%3Aall&query="
        driver.get(base_url + keyword)
        time.sleep(3) 

        # 스크롤 다운
        body = driver.find_element(By.TAG_NAME, "body")
        for _ in range(3):
            body.send_keys(Keys.END)
            time.sleep(2)
        time.sleep(2)

        articles = driver.find_elements(By.CSS_SELECTOR, "li.bx")
        
        for article in articles:
            try:
                # 1. 카페명 추출
                cafe_name = ""
                try:
                    cafe_name = article.find_element(By.CSS_SELECTOR, "a.txt_name").text
                except:
                    try: cafe_name = article.find_element(By.CSS_SELECTOR, "a.name").text
                    except: pass

                # 2. 카페명 필터링
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
                
                # 작성일 표기 (오늘 날짜 + 최신)
                date_str = datetime.now().strftime("%Y-%m-%d") + " (New)"

                # 4. 제목 및 링크
                try:
                    title_ele = article.find_element(By.CSS_SELECTOR, "a.title_link")
                    title = title_ele.text
                    link = title_ele.get_attribute("href")
                except: continue

                # 5. 광고 필터링
                if any(bad_word in title for bad_word in EXCLUDE_WORDS): continue

                # [저장] 순서 중요: 작성일 -> 카페명 -> 제목 -> 링크
                data_list.append({
                    "작성일": date_str,
                    "카페명": cafe_name,
                    "제목": title,
                    "링크": link,
                    "수집시점": datetime.now().strftime("%Y-%m-%d %H:%M") # 참고용
                })
                print(f"   ✅ [수집] {cafe_name} | {title[:15]}...")

            except Exception: continue
        time.sleep(2)

except Exception as e:
    print(f"에러 발생: {e}")
finally:
    driver.quit()

# [저장 로직]
if data_list:
    df_new = pd.DataFrame(data_list)
    # 컬럼 순서 강제 지정
    df_new = df_new[["작성일", "카페명", "제목", "링크", "수집시점"]]

    if os.path.exists(FILE_NAME):
        try:
            df_old = pd.read_csv(FILE_NAME)
            existing_links = df_old['링크'].tolist()
            df_final = df_new[~df_new['링크'].isin(existing_links)]
            
            if not df_final.empty:
                df_final.to_csv(FILE_NAME, mode='a', header=False, index=False, encoding="utf-8-sig")
                print(f"\n✅ {len(df_final)}건 추가 저장 완료.")
            else:
                print("\n👌 새로운 글이 없습니다 (중복).")
        except:
            # 파일이 꼬였으면 덮어쓰기
            df_new.to_csv(FILE_NAME, mode='w', header=True, index=False, encoding="utf-8-sig")
            print(f"\n✅ 파일 오류로 새로 생성했습니다.")
    else:
        df_new.to_csv(FILE_NAME, mode='w', header=True, index=False, encoding="utf-8-sig")
        print(f"\n✅ 파일 신규 생성 완료.")
else:
    print("\n💤 수집된 데이터가 없습니다.")