import streamlit as st
import pandas as pd
from datetime import date
import os
import random

st.set_page_config(page_title="今天吃啥", page_icon="🍚", layout="centered")
st.title("🍚 今天吃啥 · 吃饭不纠结")

SHOPS = "shops.csv" 

st.sidebar.header("👤 用户登录")
user_name = st.sidebar.text_input("请输入你的专属昵称：", "游客")

RECORDS = f"{user_name}_records.csv"

# ---------- 初始化数据文件 ----------
if not os.path.exists(SHOPS):
    pd.DataFrame(columns=["id", "name", "cuisine", "avg_price", "distance", "tags"]).to_csv(SHOPS, index=False)
if not os.path.exists(RECORDS):
    pd.DataFrame(columns=["id", "shop_id", "shop_name", "dish", "price", "date", "rating", "tags"]).to_csv(RECORDS, index=False)

def load_shops():
    return pd.read_csv(SHOPS)

def load_records():
    return pd.read_csv(RECORDS)

tab1, tab2, tab3, tab4 = st.tabs(["🎲 今天吃啥", "📝 记录一餐", "📊 统计", "🏪 店铺库"])

# ---------- Tab1 推荐 ----------
with tab1:
    st.subheader("帮我决定")
    shops = load_shops()
    records = load_records()

    if shops.empty:
        st.info("先去「店铺库」录几家店吧")
    else:
        budget = st.slider("预算上限（元）", 5, 80, 25)
        cuisine_options = cuisine_options = ["不限", "米饭", "面条", "米粉", "麻辣烫", "炸鸡汉堡","饺子馄饨", "包子粥店", "火锅串串","其他"]
        cuisine = st.selectbox("菜系", cuisine_options)
        avoid_recent = st.checkbox("避开最近 3 天吃过的店", value=False)

        filtered = shops[shops["avg_price"] <= budget].copy()
        if cuisine != "不限":
            filtered = filtered[filtered["cuisine"] == cuisine]

        if avoid_recent and not records.empty:
            records["date"] = pd.to_datetime(records["date"], errors="coerce")
            recent = records[records["date"] >= pd.Timestamp(date.today()) - pd.Timedelta(days=3)]
            filtered = filtered[~filtered["name"].isin(recent["shop_name"])]

        if st.button("🎲 摇一摇推荐", use_container_width=True):
            if filtered.empty:
                st.warning("没有符合条件的店，放宽预算或菜系试试")
            else:
                # 评分加权：历史评分高的店更容易被选中
                weights = []
                for name in filtered["name"]:
                    hist = records[records["shop_name"] == name]["rating"]
                    avg = hist.mean() if not hist.empty else 3.0
                    weights.append(max(avg, 0.1))
                pick = random.choices(filtered.to_dict("records"), weights=weights, k=1)[0]
                st.success(f"推荐：**{pick['name']}**（{pick['cuisine']}，人均 {pick['avg_price']} 元，距离约 {pick['distance']} 米）")
                if pick.get("tags"):
                    st.caption(f"标签：{pick['tags']}")

# ---------- Tab2 记录 ----------
with tab2:
    st.subheader("记录这一餐")
    shops = load_shops()
    if shops.empty:
        st.info("先去「店铺库」添加店铺")
    else:
        with st.form("record_form", clear_on_submit=True):
            shop_name = st.selectbox("店铺", shops["name"].tolist())
            dish = st.text_input("吃了什么（可选）")
            price = st.number_input("花了多少（元）", 0.0, 300.0, 20.0, step=1.0)
            rating = st.slider("评分", 1, 5, 4)
            tags = st.text_input("标签（逗号分隔，如：辣,碳水）")
            submitted = st.form_submit_button("保存记录")
            if submitted:
                records = load_records()
                new = pd.DataFrame([{
                    "id": len(records) + 1,
                    "shop_id": "",
                    "shop_name": shop_name,
                    "dish": dish,
                    "price": price,
                    "date": str(date.today()),
                    "rating": rating,
                    "tags": tags,
                }])
                pd.concat([records, new], ignore_index=True).to_csv(RECORDS, index=False)
                st.success("已记录！")

        records = load_records()
        if not records.empty:
            st.markdown("#### 最近记录")
            st.dataframe(records.tail(10).iloc[::-1], use_container_width=True)

# ---------- Tab3 统计 ----------
with tab3:
    st.subheader("统计")
    records = load_records()
    if records.empty:
        st.info("还没有记录，先去记一餐吧")
    else:
        records["date"] = pd.to_datetime(records["date"], errors="coerce")
        records["month"] = records["date"].dt.to_period("M").astype(str)

        st.markdown("#### 月度花费")
        monthly = records.groupby("month")["price"].sum()
        st.bar_chart(monthly)

        col1, col2 = st.columns(2)
        with col1:
            st.metric("总花费", f"{records['price'].sum():.0f} 元")
        with col2:
            st.metric("记录餐数", len(records))

        st.markdown("#### 店铺消费排行")
        rank = records.groupby("shop_name")["price"].agg(["sum", "count"]).sort_values("sum", ascending=False)
        rank.columns = ["总花费", "次数"]
        st.dataframe(rank, use_container_width=True)

        st.markdown("#### 评分分布")
        st.bar_chart(records["rating"].value_counts().sort_index())

# ---------- Tab4 店铺库 ----------
with tab4:
    st.subheader("店铺库")
    shops = load_shops()

    add_tab1, add_tab2 = st.tabs(["单家添加", "批量导入（csv）"])

with add_tab1:
    with st.form("shop_form", clear_on_submit=True):
        name = st.text_input("店名")
        cuisine = st.selectbox("菜系", ["米饭", "面条", "米粉", "麻辣烫", "炸鸡汉堡","饺子馄饨","包子粥店","火锅串串", "其他"])
        avg_price = st.number_input("人均（元）", 0.0, 300.0, 20.0, step=1.0)
        distance = st.number_input("距离（米）", 0, 10000, 500, step=100)
        location = st.selectbox("位置", ["学校食堂", "安逸生活广场", "双铁广场",  "外卖", "其他"])
        tags = st.text_input("标签（逗号分隔，如：辣,清淡）")
        if st.form_submit_button("添加店铺"):
            if not name.strip():
                st.warning("店名不能为空")
            else:
                new = pd.DataFrame([{
                    "id": len(shops) + 1,
                    "name": name.strip(),
                    "cuisine": cuisine,
                    "avg_price": avg_price,
                    "distance": distance,
                    "location": location,
                    "tags": tags,
                }])
                pd.concat([shops, new], ignore_index=True).to_csv(SHOPS, index=False)
                st.success(f"已添加：{name}")
                st.rerun()

with add_tab2:
    st.info("💡 提示：你可以批量导入店铺数据（csv格式），需要包含表头：name, cuisine, avg_price, distance, location, tags")
    upload_file = st.file_uploader("上传店铺数据 (csv)", type="csv")
    
    if upload_file is not None:
        # 用 session_state 记录一下，防止刷新后重复导入
        if 'uploaded_file_name' not in st.session_state or st.session_state['uploaded_file_name'] != upload_file.name:
            try:
                # 读取上传的 CSV
                df_upload = pd.read_csv(upload_file, encoding='utf-8-sig')
                
                if not df_upload.empty:
                    # 自动给导入的数据分配 id，接在原有数据的后面
                    start_id = len(shops) + 1
                    df_upload["id"] = range(start_id, start_id + len(df_upload))
                    
                    # 如果用户没填 location，给个空值防止报错
                    if "location" not in df_upload.columns:
                        df_upload["location"] = ""
                        
                    # 核心：把旧数据（shops）和新数据（df_upload）合并！
                    cols = ["id", "name", "cuisine", "avg_price", "distance", "location", "tags"]
                    combined = pd.concat([shops, df_upload[cols]], ignore_index=True)
                    
                    # 保存回 shops.csv！
                    combined.to_csv(SHOPS, index=False)
                    
                    st.success(f"🎉 成功导入并合并了 {len(df_upload)} 家店铺！")
                    
                    # 记录当前文件名，防止刷新时重复导入
                    st.session_state['uploaded_file_name'] = upload_file.name
                    
                    # 强制刷新页面，让“已有店铺”表格立刻更新
                    st.rerun()
                else:
                    st.warning("导入的文件是空的哦")
            except Exception as e:
                st.error(f"导入失败，请检查 CSV 格式。错误信息：{str(e)}")

    if not shops.empty:
        st.markdown("#### 已有店铺")

        shops_cn = shops.rename(columns={"name": "店名", "cuisine": "菜系", "avg_price": "人均（元）", "distance": "距离（米）", "location": "位置", "tags": "标签"})
        st.dataframe(shops_cn, use_container_width=True)
        if st.button("🗑️ 清空店铺库（谨慎）"):
            pd.DataFrame(columns=[ "ID", "name", "cuisine", "avg_price", "distance", "location", "tags", "标签"]).to_csv(SHOPS, index=False)
            st.rerun()