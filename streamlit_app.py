import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, date
import calendar
import io

def get_insurance_bracket(salary, brackets):
    """根據薪資取得適用的投保級距"""
    if salary < brackets[0]:
        return brackets[0]
    for bracket in brackets:
        if salary <= bracket:
            return bracket
    return brackets[-1]
def export_to_csv(results_df, summary_df):
    """匯出計算結果至 CSV"""
    buffer = io.BytesIO()
    buffer.write("費用明細表\n".encode('utf-8-sig'))
    results_df.to_csv(buffer, index=False, encoding='utf-8-sig')
    buffer.write("\n\n".encode('utf-8-sig'))
    buffer.write("費用總表\n".encode('utf-8-sig'))
    summary_df.to_csv(buffer, index=False, encoding='utf-8-sig')
    buffer.seek(0)
    return buffer
def calculate_days_in_period(start_date, end_date):
    """計算投保天數"""
    # 如果是同一個月
    if start_date.year == end_date.year and start_date.month == end_date.month:
        # 如果是2月
        if start_date.month == 2:
            days_in_month = 29 if calendar.isleap(start_date.year) else 28
            if start_date.day == 1 and end_date.day == days_in_month:
                return days_in_month
            return end_date.day - start_date.day + 1
        # 其他月份
        if start_date.day == 1 and end_date.day >= 30:
            return 30
        if end_date.day in [30, 31] and start_date.day == 1:
            return 30
        # 破月計算
        if end_date.day in [30, 31]:
            return 30 - (start_date.day - 1)
        return end_date.day - start_date.day + 1
    
    # 如果跨月
    days = []
    current_date = start_date
    while current_date <= end_date:
        if current_date.month == start_date.month and current_date.year == start_date.year:
            # 第一個月
            if current_date.month == 2:
                days_in_month = 29 if calendar.isleap(current_date.year) else 28
                days.append(days_in_month - start_date.day + 1)
            else:
                days.append(30 - (start_date.day - 1))
        elif current_date.month == end_date.month and current_date.year == end_date.year:
            # 最後一個月
            if current_date.month == 2:
                days.append(end_date.day)
            else:
                days.append(min(30, end_date.day))
        else:
            # 中間的月份
            if current_date.month == 2:
                days.append(29 if calendar.isleap(current_date.year) else 28)
            else:
                days.append(30)
        
        # 移至下個月
        if current_date.month == 12:
            current_date = date(current_date.year + 1, 1, 1)
        else:
            current_date = date(current_date.year, current_date.month + 1, 1)
    
    return days

def calculate_insurance_fees(employee_data, occupational_rate):
    """計算勞健保費用"""
    results = []
    
    for emp in employee_data:
        salary = emp['salary']
        start_date = emp['start_date']
        end_date = emp['end_date']
        name = emp['name']
        is_elderly = emp['is_elderly']
        dependents = emp['dependents']
        dependents_not_counted = emp['dependents_not_counted']
        is_foreign = emp['is_foreign']
        has_health_insurance = emp['has_health_insurance']
        
        # 取得適用的投保級距
        bracket = get_insurance_bracket(salary, st.session_state.brackets)
        
        # 計算投保天數
        days_list = calculate_days_in_period(start_date, end_date)
        current_date = start_date
        
        for days in days_list:
            month_key = f"{current_date.year}-{current_date.month:02d}"
            total_days = 30  # 標準月份天數
            if current_date.month == 2:
                total_days = 29 if calendar.isleap(current_date.year) else 28
            
            # 計算各項保費
            if is_elderly:
                labor_fee = 0
                pension_fee = 0
                # 職災保險費
                occupational_fee = round(bracket * (occupational_rate/100) * days / total_days)
            else:
                # 勞保費 (10.5% * 20%)
                labor_fee = round(bracket * 0.105 * 0.2 * days / total_days)
                # 勞退金 (6%) - 外籍人士無勞退
                pension_fee = 0 if is_foreign else round(salary * 0.06 * days / total_days)
                occupational_fee = 0
            
            # 健保費計算
            if has_health_insurance:
                # 計算有效眷屬人數（最多到4人）
                effective_dependents = min(3, dependents)  # 本人+眷屬最多4人
                health_fee_base = round(bracket * 0.0517 * 0.3 * days / total_days)
                dependent_fee = round(bracket * 0.0517 * 0.3 * days / total_days * effective_dependents)
                total_health_fee_month = health_fee_base + dependent_fee
            else:
                total_health_fee_month = 0
            
            # 加入結果
            results.append({
                "姓名": name,
                "年月": month_key,
                "天數": days,
                "投保級距": bracket,
                "眷屬人數": dependents,
                "不計人數": dependents_not_counted,
                "勞保費": labor_fee,
                "健保費": total_health_fee_month,
                "勞退金": pension_fee,
                "職災保險費": occupational_fee,
                "小計": labor_fee + total_health_fee_month + pension_fee + occupational_fee,
                "備註": "請領老年給付" if is_elderly else ("外籍人士" if is_foreign else "")
            })
            
            # 移至下個月
            if current_date.month == 12:
                current_date = date(current_date.year + 1, 1, 1)
            else:
                current_date = date(current_date.year, current_date.month + 1, 1)
    
    return pd.DataFrame(results)

def main():
    st.set_page_config(
        page_title="台灣勞健保費用計算器",
        page_icon="💰",
        layout="wide"
    )
    
    # 初始化 session state
    if 'brackets' not in st.session_state:
        st.session_state.brackets = [
            26400, 27600, 28800, 30300, 31800, 33300, 34800, 36300, 37800, 39300,
            40800, 42300, 43900, 45400, 46900, 48400, 50000
        ]
    
    if 'employees' not in st.session_state:
        st.session_state.employees = []
    
    st.title("台灣勞健保費用計算器 💰")
    st.caption("計算勞保、健保、勞退費用，支援多人同時計算")
    
    tab1, tab2 = st.tabs(["📊 費用試算", "⚙️ 級距設定"])
    
    with tab1:
            with st.expander("新增員工資料", expanded=True):
                col1, col2 = st.columns(2)
                with col1:
                    occupational_rate = st.number_input(
                        "職災保險費率 (%)",
                        min_value=0.0,
                        max_value=100.0,
                        value=0.21,
                        step=0.01,
                        help="請輸入公司的職災保險費率百分比"
                    )
            
            cols = st.columns([2,2,1,1,1,1,1,1,1,1])
            with cols[0]:
                name = st.text_input("姓名", key="name_input")
            with cols[1]:
                salary = st.number_input(
                    "投保薪資",
                    min_value=26400,
                    max_value=150000,
                    value=26400,
                    step=100,
                    key="salary_input",
                    help="請填入勞健保業務申請單所記金額"
                )
            with cols[2]:
                dependents = st.number_input(
                    "眷屬人數",
                    min_value=0,
                    max_value=10,
                    value=0,
                    step=1,
                    key="dependents_input",
                    help="每戶健保費以4人為上限"
                )
            with cols[3]:
                dependents_not_counted = st.number_input(
                    "不計人數",
                    min_value=0,
                    max_value=10,
                    value=0,
                    step=1,
                    key="dependents_not_counted_input",
                    help="超過4人的眷屬數量"
                )
            with cols[4]:
                is_elderly = st.checkbox(
                    "請領老年給付",
                    key="elderly_input",
                    help="勾選後只計算職災保險和健保費"
                )
            with cols[5]:
                is_foreign = st.checkbox(
                    "外籍人士",
                    key="foreign_input",
                    help="外籍人士無勞退"
                )
            with cols[6]:
                has_health_insurance = st.checkbox(
                    "投保健保",
                    value=True,
                    key="health_insurance_input",
                    help="是否投保健保"
                )
            with cols[7]:
                start_input_type = st.selectbox(
                    "加保日期方式",
                    ["選擇日期", "手動輸入"],
                    key="start_date_type"
                )
            with cols[8]:
                if start_input_type == "選擇日期":
                    start_date = st.date_input(
                        "加保日期",
                        datetime.now(),
                        key="start_date_input"
                    )
                else:
                    start_date_str = st.text_input(
                        "加保日期 (YYYY/MM/DD)",
                        datetime.now().strftime("%Y/%m/%d"),
                        key="start_date_text"
                    )
                    try:
                        start_date = datetime.strptime(start_date_str, "%Y/%m/%d").date()
                    except:
                        st.error("請輸入正確的日期格式 (YYYY/MM/DD)")
                        start_date = None
            
            with cols[9]:
                end_input_type = st.selectbox(
                    "退保日期方式",
                    ["選擇日期", "手動輸入"],
                    key="end_date_type"
                )
            with cols[0]:  # 換到下一行
                if end_input_type == "選擇日期":
                    end_date = st.date_input(
                        "退保日期",
                        datetime.now() + timedelta(days=30),
                        key="end_date_input"
                    )
                else:
                    end_date_str = st.text_input(
                        "退保日期 (YYYY/MM/DD)",
                        (datetime.now() + timedelta(days=30)).strftime("%Y/%m/%d"),
                        key="end_date_text"
                    )
                    try:
                        end_date = datetime.strptime(end_date_str, "%Y/%m/%d").date()
                    except:
                        st.error("請輸入正確的日期格式 (YYYY/MM/DD)")
                        end_date = None

            # 新增按鈕
            if st.button("新增", type="primary"):
                if not start_date or not end_date:
                    st.error("請輸入正確的日期格式")
                elif start_date > end_date:
                    st.error("開始日期不能大於結束日期")
                elif not name:
                    st.error("請輸入姓名")
                else:
                    st.session_state.employees.append({
                        'name': name,
                        'salary': salary,
                        'start_date': start_date,
                        'end_date': end_date,
                        'dependents': dependents,
                        'dependents_not_counted': dependents_not_counted,
                        'is_elderly': is_elderly,
                        'is_foreign': is_foreign,
                        'has_health_insurance': has_health_insurance
                    })
                    st.success(f"已新增 {name} 的資料")

            
            # 顯示已新增的員工資料（注意縮排位置）
            if st.session_state.employees:
                st.subheader("已新增的員工資料")
                emp_df = pd.DataFrame(st.session_state.employees)
                st.dataframe(emp_df, hide_index=True)
                
                col1, col2 = st.columns([6,1])
                with col1:
                    if st.button("計算所有員工費用", type="primary", use_container_width=True):
                            with st.spinner('計算中...'):
                                results_df = calculate_insurance_fees(st.session_state.employees, occupational_rate)
                                
                                summary_df = results_df.groupby('姓名').agg({
                                    '勞保費': 'sum',
                                    '健保費': 'sum',
                                    '勞退金': 'sum',
                                    '職災保險費': 'sum',
                                    '小計': 'sum'
                                }).reset_index()
                            
                            st.subheader("📋 費用明細")
                            st.dataframe(
                                results_df.style.format({
                                    "投保級距": "{:,.0f}",
                                    "勞保費": "{:,.0f}",
                                    "健保費": "{:,.0f}",
                                    "勞退金": "{:,.0f}",
                                    "職災保險費": "{:,.0f}",
                                    "小計": "{:,.0f}"
                                }),
                                use_container_width=True,
                                hide_index=True
                            )
                            
                            st.subheader("💰 費用總計")
                            st.dataframe(
                                summary_df.style.format({
                                    "勞保費": "{:,.0f}",
                                    "健保費": "{:,.0f}",
                                    "勞退金": "{:,.0f}",
                                    "職災保險費": "{:,.0f}",
                                    "小計": "{:,.0f}"
                                }),
                                use_container_width=True,
                                hide_index=True
                            )
                            
                            st.subheader("📥 匯出報表")
                            buffer = export_to_csv(results_df, summary_df)
                            
                            st.download_button(
                                label="📥 下載 CSV 報表",
                                data=buffer,
                                file_name=f"勞健保費用計算表_{datetime.now().strftime('%Y%m%d')}.csv",
                                mime="text/csv",
                                use_container_width=True
                            )
                    
                    with col2:
                        if st.button("清除所有資料", type="secondary", use_container_width=True):
                            st.session_state.employees = []
                            st.experimental_rerun()

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
                new_brackets = [int(x.strip()) for x in new_brackets_text.split(',') if x.strip().isdigit()]
                if new_brackets:
                    st.session_state.brackets = sorted(new_brackets)
                    st.success("級距更新成功！")
                    st.write("目前級距表：")
                    st.write(pd.DataFrame(st.session_state.brackets, columns=["投保金額"]))
                else:
                    st.error("請輸入有效的數字，以逗號分隔")
            except Exception as e:
                st.error(f"更新失敗：{str(e)}")

if __name__ == "__main__":
    main()
