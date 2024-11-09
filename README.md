import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import calendar

def get_insurance_bracket(salary, brackets):
    """根據薪資取得適用的投保級距"""
    if salary < brackets[0]:
        return brackets[0]
    for bracket in brackets:
        if salary <= bracket:
            return bracket
    return brackets[-1]

def calculate_insurance_fees(salary, start_date, end_date):
    """計算勞保、健保和勞退費用"""
    # 取得適用的投保級距
    bracket = get_insurance_bracket(salary, st.session_state.brackets)
    
    # 計算每個月的天數
    monthly_days = {}
    current_date = start_date
    while current_date <= end_date:
        month_key = f"{current_date.year}-{current_date.month:02d}"
        days_in_month = calendar.monthrange(current_date.year, current_date.month)[1]
        
        # 計算當月實際天數
        if current_date.month == start_date.month and current_date.year == start_date.year:
            start_day = start_date.day
        else:
            start_day = 1
            
        if current_date.month == end_date.month and current_date.year == end_date.year:
            end_day = end_date.day
        else:
            end_day = days_in_month
            
        monthly_days[month_key] = {
            'days': end_day - start_day + 1,
            'total_days': days_in_month
        }
        
        # 移至下個月
        if current_date.month == 12:
            current_date = datetime(current_date.year + 1, 1, 1)
        else:
            current_date = datetime(current_date.year, current_date.month + 1, 1)

    # 計算各項保費
    monthly_details = []
    total_labor_fee = 0
    total_health_fee = 0
    total_pension_fee = 0
    
    for month, days_info in monthly_days.items():
        days = days_info['days']
        total_days = days_info['total_days']
        
        # 勞保費 (10.5% * 20%)
        labor_fee = round(bracket * 0.105 * 0.2 * days / total_days)
        # 健保費 (5.17% * 30%)
        health_fee = round(bracket * 0.0517 * 0.3 * days / total_days)
        # 勞退金 (6%)
        pension_fee = round(salary * 0.06 * days / total_days)
        
        total_labor_fee += labor_fee
        total_health_fee += health_fee
        total_pension_fee += pension_fee
        
        monthly_details.append({
            "年月": month,
            "天數": days,
            "投保級距": bracket,
            "勞保費": labor_fee,
            "健保費": health_fee,
            "勞退金": pension_fee,
            "小計": labor_fee + health_fee + pension_fee
        })
    
    return {
        "monthly_details": monthly_details,
        "total_labor_fee": total_labor_fee,
        "total_health_fee": total_health_fee,
        "total_pension_fee": total_pension_fee,
        "total_fee": total_labor_fee + total_health_fee + total_pension_fee
    }

def main():
    st.set_page_config(
        page_title="台灣勞健保費用計算器",
        page_icon="💰",
        layout="wide"
    )
    
    # 初始化 session state
    if 'brackets' not in st.session_state:
        # 2024年的投保級距
        st.session_state.brackets = [
            26400, 27600, 28800, 30300, 31800, 33300, 34800, 36300, 37800, 39300,
            40800, 42300, 43900, 45400, 46900, 48400, 50000
        ]
    
    st.title("台灣勞健保費用計算器 💰")
    st.caption("計算勞保、健保、勞退費用，支援非整月計算")
    
    # 建立兩個頁籤
    tab1, tab2 = st.tabs(["📊 費用試算", "⚙️ 級距設定"])
    
    with tab1:
        col1, col2, col3 = st.columns([2,1,1])
        
        with col1:
            salary = st.number_input(
                "請輸入月薪",
                min_value=26400,
                max_value=150000,
                value=26400,
                step=100,
                help="最低投保薪資為26,400元"
            )
            
        with col2:
            start_date = st.date_input(
                "開始日期",
                datetime.now(),
                help="加保起始日"
            )
            
        with col3:
            end_date = st.date_input(
                "結束日期",
                datetime.now() + timedelta(days=30),
                help="退保日期"
            )

        if st.button("計算", type="primary", use_container_width=True):
            if start_date > end_date:
                st.error("開始日期不能大於結束日期")
            else:
                # 計算結果
                with st.spinner('計算中...'):
                    results = calculate_insurance_fees(salary, start_date, end_date)
                
                # 顯示每月詳細資訊
                st.subheader("📋 每月費用明細")
                df = pd.DataFrame(results["monthly_details"])
                st.dataframe(
                    df.style.format({
                        "投保級距": "{:,.0f}",
                        "勞保費": "{:,.0f}",
                        "健保費": "{:,.0f}",
                        "勞退金": "{:,.0f}",
                        "小計": "{:,.0f}"
                    }),
                    use_container_width=True,
                    hide_index=True
                )
                
                # 顯示總費用
                st.subheader("💰 費用總計")
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("勞保費", f"NT$ {results['total_labor_fee']:,}")
                with col2:
                    st.metric("健保費", f"NT$ {results['total_health_fee']:,}")
                with col3:
                    st.metric("勞退金", f"NT$ {results['total_pension_fee']:,}")
                with col4:
                    st.metric("總費用", f"NT$ {results['total_fee']:,}")
    
    with tab2:
        st.subheader("📝 更新投保級距")
        current_brackets = ", ".join(map(str, st.session_state.brackets))
        new_brackets_text = st.text_area(
            "請輸入新的級距資料（以逗號分隔）",
            value=current_brackets,
            height=100,
            help="請從健保署網站複製最新的級距資料，以逗號分隔每個數字"
        )
        
        if st.button("更新級距", type="primary"):
            try:
                # 將輸入的文字轉換為數字列表
                new_brackets = [
                    int(x.strip()) 
                    for x in new_brackets_text.split(',') 
                    if x.strip().isdigit()
                ]
                
                if new_brackets:
                    st.session_state.brackets = sorted(new_brackets)
                    st.success("級距更新成功！")
                    # 顯示新的級距表
                    st.write("目前級距表：")
                    st.write(pd.DataFrame(st.session_state.brackets, columns=["投保金額"]))
                else:
                    st.error("請輸入有效的數字，以逗號分隔")
            except Exception as e:
                st.error(f"更新失敗：{str(e)}")
        
        # 顯示說明
        with st.expander("使用說明"):
            st.markdown("""
            ### 如何更新級距：
            1. 前往[健保署投保金額分級表](https://www.nhi.gov.tw/Content_List.aspx?n=23E5F5217A713E00)
            2. 複製最新的級距資料
            3. 貼到上方文字區域
            4. 點擊「更新級距」按鈕
            
            ### 注意事項：
            - 級距資料必須是數字，以逗號分隔
            - 系統會自動排序級距
            - 更新後的級距會在您重新整理頁面後重置
            """)

if __name__ == "__main__":
    main()
