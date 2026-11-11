
import streamlit as st
import pandas as pd
import sqlite3
from datetime import date
import plotly.express as px

# ---------------- PAGE CONFIG ----------------
st.set_page_config(
    page_title="SpendSmart",
    page_icon="💰",
    layout="wide"
)

st.title("💰 SpendSmart – Expense Tracker")
st.caption("Your personal money management dashboard")

# ---------------- DATABASE ----------------
conn = sqlite3.connect("expenses.db", check_same_thread=False)

conn.execute("""
CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_date TEXT,
    transaction_type TEXT,
    category TEXT,
    amount REAL,
    description TEXT
)
""")

conn.execute("""
CREATE TABLE IF NOT EXISTS budgets (
    category TEXT PRIMARY KEY,
    amount REAL
)
""")
conn.commit()

# ---------------- LOAD DATA ----------------
def load_transactions():
    return pd.read_sql_query(
        "SELECT * FROM transactions ORDER BY entry_date DESC",
        conn
    )

# ---------------- SIDEBAR ----------------
st.sidebar.title("📌 Navigation")

page = st.sidebar.radio(
    "Choose a page",
    ["Dashboard", "Add Transaction",
     "Transaction History", "Budget Manager"]
)

# ---------------- DASHBOARD ----------------
if page == "Dashboard":

    df = load_transactions()

    if not df.empty:
        df["entry_date"] = pd.to_datetime(df["entry_date"])
        current_month = date.today().strftime("%Y-%m")
        month_df = df[
            df["entry_date"].dt.strftime("%Y-%m") == current_month
        ]

        income = month_df.loc[
            month_df["transaction_type"] == "Income", "amount"
        ].sum()

        expenses = month_df.loc[
            month_df["transaction_type"] == "Expense", "amount"
        ].sum()
    else:
        month_df = pd.DataFrame()
        income = 0
        expenses = 0

    balance = income - expenses

    st.subheader("📊 Monthly Overview")

    c1, c2, c3 = st.columns(3)

    c1.metric("Total Income", f"₹{income:,.2f}")
    c2.metric("Total Expenses", f"₹{expenses:,.2f}")
    c3.metric("Remaining Balance", f"₹{balance:,.2f}")

    st.divider()

    if not month_df.empty:
        expense_df = month_df[
            month_df["transaction_type"] == "Expense"
        ]

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Category-wise Expenses")

            if not expense_df.empty:
                category_data = expense_df.groupby(
                    "category"
                )["amount"].sum().reset_index()

                fig = px.pie(
                    category_data,
                    names="category",
                    values="amount",
                    hole=0.45
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No expenses this month.")

        with col2:
            st.subheader("Income vs Expenses")

            chart_data = pd.DataFrame({
                "Type": ["Income", "Expenses"],
                "Amount": [income, expenses]
            })

            fig = px.bar(
                chart_data,
                x="Type",
                y="Amount",
                color="Type"
            )
            st.plotly_chart(fig, use_container_width=True)

        st.subheader("Recent Transactions")
        st.dataframe(
            month_df.sort_values(
                "entry_date", ascending=False
            ).head(5),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("Start by adding your first transaction!")

# ---------------- ADD TRANSACTION ----------------
elif page == "Add Transaction":

    st.subheader("➕ Add New Transaction")

    with st.form("transaction_form"):

        transaction_date = st.date_input(
            "Date", value=date.today()
        )

        transaction_type = st.selectbox(
            "Transaction Type",
            ["Expense", "Income"]
        )

        categories = [
            "Food", "Travel", "Shopping",
            "Education", "Bills", "Health",
            "Entertainment", "Salary", "Other"
        ]

        category = st.selectbox(
            "Category", categories
        )

        amount = st.number_input(
            "Amount (₹)",
            min_value=0.01,
            step=10.0
        )

        description = st.text_input(
            "Description"
        )

        submitted = st.form_submit_button(
            "Save Transaction",
            use_container_width=True
        )

        if submitted:
            conn.execute("""
                INSERT INTO transactions
                (entry_date, transaction_type, category,
                 amount, description)
                VALUES (?, ?, ?, ?, ?)
            """, (
                str(transaction_date),
                transaction_type,
                category,
                amount,
                description
            ))

            conn.commit()
            st.success("Transaction saved successfully!")

# ---------------- TRANSACTION HISTORY ----------------
elif page == "Transaction History":

    st.subheader("📋 Transaction History")

    df = load_transactions()

    if not df.empty:

        search = st.text_input(
            "Search by description or category"
        )

        selected_type = st.selectbox(
            "Filter by type",
            ["All", "Income", "Expense"]
        )

        if search:
            df = df[
                df["description"].str.contains(
                    search, case=False, na=False
                ) |
                df["category"].str.contains(
                    search, case=False, na=False
                )
            ]

        if selected_type != "All":
            df = df[
                df["transaction_type"] == selected_type
            ]

        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True
        )

        csv = df.to_csv(index=False).encode("utf-8")

        st.download_button(
            "⬇️ Download CSV",
            data=csv,
            file_name="my_expenses.csv",
            mime="text/csv"
        )

        st.divider()
        st.subheader("Delete Transaction")

        ids = df["id"].tolist()

        if ids:
            delete_id = st.selectbox(
                "Select transaction ID",
                ids
            )

            if st.button("Delete Selected Transaction"):
                conn.execute(
                    "DELETE FROM transactions WHERE id = ?",
                    (int(delete_id),)
                )
                conn.commit()
                st.success("Transaction deleted!")
                st.rerun()

    else:
        st.info("No transactions available.")

# ---------------- BUDGET MANAGER ----------------
elif page == "Budget Manager":

    st.subheader("🎯 Monthly Budget Manager")

    categories = [
        "Food", "Travel", "Shopping",
        "Education", "Bills", "Health",
        "Entertainment", "Other"
    ]

    with st.form("budget_form"):

        category = st.selectbox(
            "Choose Category", categories
        )

        budget_amount = st.number_input(
            "Monthly Budget (₹)",
            min_value=1.0,
            step=100.0
        )

        save_budget = st.form_submit_button(
            "Save Budget"
        )

        if save_budget:
            conn.execute("""
                INSERT INTO budgets (category, amount)
                VALUES (?, ?)
                ON CONFLICT(category)
                DO UPDATE SET amount = excluded.amount
            """, (category, budget_amount))

            conn.commit()
            st.success("Budget saved!")

    st.divider()
    st.subheader("Budget Overview")

    budget_df = pd.read_sql_query(
        "SELECT * FROM budgets", conn
    )

    transactions = load_transactions()

    if not budget_df.empty:

        if not transactions.empty:
            transactions["entry_date"] = pd.to_datetime(
                transactions["entry_date"]
            )

            current_month = date.today().strftime("%Y-%m")

            transactions = transactions[
                (transactions["entry_date"].dt.strftime("%Y-%m")
                 == current_month) &
                (transactions["transaction_type"] == "Expense")
            ]

        for _, row in budget_df.iterrows():

            spent = 0

            if not transactions.empty:
                spent = transactions.loc[
                    transactions["category"] == row["category"],
                    "amount"
                ].sum()

            budget = row["amount"]
            progress = min(spent / budget, 1.0)

            st.write(
                f"**{row['category']}**: "
                f"₹{spent:,.2f} / ₹{budget:,.2f}"
            )

            st.progress(progress)

            if spent > budget:
                st.warning("Budget exceeded!")
            else:
                st.caption(
                    f"Remaining: ₹{budget - spent:,.2f}"
                )
    else:
        st.info("Set your first monthly budget.")

st.sidebar.divider()
st.sidebar.caption("SpendSmart | Personal Finance App")
