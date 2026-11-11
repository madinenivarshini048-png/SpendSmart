
import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import hashlib
import secrets
import hmac
from datetime import date, timedelta

# =====================================
# PAGE CONFIGURATION
# =====================================
st.set_page_config(
    page_title="SpendSmart Pro",
    page_icon="💰",
    layout="wide"
)

# =====================================
# DATABASE
# =====================================
conn = sqlite3.connect(
    "spendsmart.db",
    check_same_thread=False
)

conn.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    salt TEXT NOT NULL,
    password_hash TEXT NOT NULL
)
""")

conn.execute("""
CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    entry_date TEXT,
    transaction_type TEXT,
    category TEXT,
    amount REAL,
    description TEXT
)
""")

conn.execute("""
CREATE TABLE IF NOT EXISTS budgets (
    user_id INTEGER,
    category TEXT,
    amount REAL,
    PRIMARY KEY(user_id, category)
)
""")

conn.execute("""
CREATE TABLE IF NOT EXISTS savings_goals (
    user_id INTEGER,
    month TEXT,
    amount REAL,
    PRIMARY KEY(user_id, month)
)
""")

conn.execute("""
CREATE TABLE IF NOT EXISTS reminders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    reminder_date TEXT,
    message TEXT,
    completed INTEGER DEFAULT 0
)
""")

conn.commit()

# =====================================
# PASSWORD SECURITY
# =====================================
def hash_password(password, salt):
    return hashlib.pbkdf2_hmac(
        "sha256",
        password.encode(),
        bytes.fromhex(salt),
        200000
    ).hex()


# =====================================
# SESSION STATE
# =====================================
if "user_id" not in st.session_state:
    st.session_state.user_id = None

if "username" not in st.session_state:
    st.session_state.username = None

# =====================================
# LOGIN AND REGISTRATION
# =====================================
def authentication():

    st.title("💰 SpendSmart Pro")
    st.caption("Your money, your control.")

    login_tab, register_tab = st.tabs(
        ["Login", "Register"]
    )

    with register_tab:

        st.subheader("Create Account")

        new_user = st.text_input(
            "Username",
            key="register_user"
        )

        new_password = st.text_input(
            "Password (minimum 8 characters)",
            type="password",
            key="register_password"
        )

        confirm_password = st.text_input(
            "Confirm Password",
            type="password"
        )

        if st.button("Register", use_container_width=True):

            username = new_user.strip()

            if not username or len(username) < 3:
                st.error("Username must have at least 3 characters.")

            elif len(new_password) < 8:
                st.error("Password must have at least 8 characters.")

            elif new_password != confirm_password:
                st.error("Passwords do not match.")

            else:
                salt = secrets.token_bytes(16).hex()
                password_hash = hash_password(
                    new_password, salt
                )

                try:
                    conn.execute("""
                        INSERT INTO users
                        (username, salt, password_hash)
                        VALUES (?, ?, ?)
                    """, (
                        username, salt, password_hash
                    ))

                    conn.commit()
                    st.success("Account created! Please log in.")

                except sqlite3.IntegrityError:
                    st.error("Username already exists.")

    with login_tab:

        st.subheader("Welcome Back")

        username = st.text_input(
            "Username",
            key="login_user"
        )

        password = st.text_input(
            "Password",
            type="password",
            key="login_password"
        )

        if st.button("Login", use_container_width=True):

            user = conn.execute("""
                SELECT id, salt, password_hash
                FROM users
                WHERE username = ?
            """, (username.strip(),)).fetchone()

            if user:
                entered_hash = hash_password(
                    password, user[1]
                )

                if hmac.compare_digest(
                    entered_hash, user[2]
                ):
                    st.session_state.user_id = user[0]
                    st.session_state.username = username.strip()
                    st.rerun()

            st.error("Invalid username or password.")


# =====================================
# AUTHENTICATION CHECK
# =====================================
if st.session_state.user_id is None:
    authentication()
    st.stop()

user_id = st.session_state.user_id

# =====================================
# CUSTOM THEME
# =====================================
st.sidebar.title("⚙️ Settings")

theme = st.sidebar.selectbox(
    "Choose Theme",
    ["Light", "Dark"]
)

if theme == "Dark":
    st.markdown("""
    <style>
    .stApp {
        background-color: #111827;
        color: #F9FAFB;
    }
    [data-testid="stSidebar"] {
        background-color: #1F2937;
    }
    </style>
    """, unsafe_allow_html=True)

else:
    st.markdown("""
    <style>
    .stApp {
        background-color: #F8FAFC;
        color: #111827;
    }
    [data-testid="stSidebar"] {
        background-color: #E2E8F0;
    }
    </style>
    """, unsafe_allow_html=True)

# =====================================
# DATA FUNCTIONS
# =====================================
def load_transactions():

    return pd.read_sql_query("""
        SELECT id, entry_date, transaction_type,
               category, amount, description
        FROM transactions
        WHERE user_id = ?
        ORDER BY entry_date DESC
    """, conn, params=(user_id,))


def current_month_data():

    df = load_transactions()

    if df.empty:
        return df

    df["entry_date"] = pd.to_datetime(df["entry_date"])

    month = date.today().strftime("%Y-%m")

    return df[
        df["entry_date"].dt.strftime("%Y-%m") == month
    ]


# =====================================
# SIDEBAR NAVIGATION
# =====================================
st.sidebar.title("💰 SpendSmart Pro")

st.sidebar.write(
    f"Welcome, **{st.session_state.username}**!"
)

page = st.sidebar.radio(
    "Navigation",
    [
        "Dashboard",
        "Add Transaction",
        "Transaction History",
        "Savings Tracker",
        "Advanced Analytics",
        "Expense Reminders",
        "Budget Manager"
    ]
)

if st.sidebar.button("Logout"):
    st.session_state.user_id = None
    st.session_state.username = None
    st.rerun()

# =====================================
# DASHBOARD
# =====================================
if page == "Dashboard":

    st.title("📊 Financial Dashboard")

    df = current_month_data()

    if df.empty:
        income = 0
        expenses = 0
    else:
        income = df.loc[
            df.transaction_type == "Income",
            "amount"
        ].sum()

        expenses = df.loc[
            df.transaction_type == "Expense",
            "amount"
        ].sum()

    balance = income - expenses

    c1, c2, c3 = st.columns(3)

    c1.metric("💵 Income", f"₹{income:,.2f}")
    c2.metric("💸 Expenses", f"₹{expenses:,.2f}")
    c3.metric("💰 Savings / Balance", f"₹{balance:,.2f}")

    st.divider()

    if not df.empty:

        expense_df = df[
            df.transaction_type == "Expense"
        ]

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Expense Categories")

            if not expense_df.empty:
                category_data = (
                    expense_df.groupby("category")["amount"]
                    .sum().reset_index()
                )

                fig = px.pie(
                    category_data,
                    names="category",
                    values="amount",
                    hole=0.45
                )

                st.plotly_chart(
                    fig, use_container_width=True
                )

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

            st.plotly_chart(
                fig, use_container_width=True
            )

        st.subheader("Recent Transactions")

        st.dataframe(
            df.head(5),
            use_container_width=True,
            hide_index=True
        )

    else:
        st.info("Add your first transaction to see your dashboard.")

    # Budget alerts
    budgets = conn.execute("""
        SELECT category, amount FROM budgets
        WHERE user_id = ?
    """, (user_id,)).fetchall()

    for category, limit in budgets:

        spent = 0

        if not df.empty:
            spent = df.loc[
                (df.category == category) &
                (df.transaction_type == "Expense"),
                "amount"
            ].sum()

        if spent >= limit:
            st.warning(
                f"Budget alert: {category} budget reached or exceeded!"
            )

    # Upcoming reminders
    today = date.today().isoformat()
    upcoming = conn.execute("""
        SELECT reminder_date, message
        FROM reminders
        WHERE user_id = ?
        AND completed = 0
        AND reminder_date <= ?
        ORDER BY reminder_date
    """, (user_id, today)).fetchall()

    if upcoming:
        st.subheader("🔔 Reminders")

        for reminder_date, message in upcoming:
            st.warning(
                f"{reminder_date}: {message}"
            )


# =====================================
# ADD TRANSACTION
# =====================================
elif page == "Add Transaction":

    st.title("➕ Add Transaction")

    with st.form("transaction_form"):

        entry_date = st.date_input("Date", date.today())

        transaction_type = st.selectbox(
            "Transaction Type",
            ["Expense", "Income"]
        )

        category = st.selectbox(
            "Category",
            [
                "Food", "Travel", "Shopping",
                "Education", "Bills", "Health",
                "Entertainment", "Salary", "Other"
            ]
        )

        amount = st.number_input(
            "Amount (₹)",
            min_value=0.01,
            step=10.0
        )

        description = st.text_input("Description")

        submit = st.form_submit_button(
            "Save Transaction"
        )

        if submit:

            conn.execute("""
                INSERT INTO transactions
                (user_id, entry_date, transaction_type,
                 category, amount, description)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                str(entry_date),
                transaction_type,
                category,
                amount,
                description
            ))

            conn.commit()

            st.success("Transaction added successfully!")


# =====================================
# TRANSACTION HISTORY
# =====================================
elif page == "Transaction History":

    st.title("📋 Transaction History")

    df = load_transactions()

    if not df.empty:

        search = st.text_input("Search transactions")

        if search:
            mask = (
                df["category"].str.contains(
                    search, case=False, na=False
                ) |
                df["description"].str.contains(
                    search, case=False, na=False
                )
            )
            df = df[mask]

        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True
        )

        if not df.empty:

            delete_id = st.selectbox(
                "Select transaction to delete",
                df["id"].tolist()
            )

            if st.button("Delete Transaction"):
                conn.execute("""
                    DELETE FROM transactions
                    WHERE id = ? AND user_id = ?
                """, (int(delete_id), user_id))

                conn.commit()
                st.success("Transaction deleted.")
                st.rerun()

    else:
        st.info("No transactions found.")


# =====================================
# MONTHLY SAVINGS TRACKER
# =====================================
elif page == "Savings Tracker":

    st.title("🎯 Monthly Savings Tracker")

    month = date.today().strftime("%Y-%m")

    df = current_month_data()

    if df.empty:
        income = 0
        expenses = 0
    else:
        income = df.loc[
            df.transaction_type == "Income", "amount"
        ].sum()

        expenses = df.loc[
            df.transaction_type == "Expense", "amount"
        ].sum()

    savings = income - expenses

    st.metric(
        "Current Monthly Savings",
        f"₹{savings:,.2f}"
    )

    goal_row = conn.execute("""
        SELECT amount FROM savings_goals
        WHERE user_id = ? AND month = ?
    """, (user_id, month)).fetchone()

    current_goal = goal_row[0] if goal_row else 0

    with st.form("savings_goal_form"):

        goal = st.number_input(
            "Set Monthly Savings Goal (₹)",
            min_value=0.0,
            value=float(current_goal),
            step=100.0
        )

        if st.form_submit_button("Save Savings Goal"):

            conn.execute("""
                INSERT INTO savings_goals
                (user_id, month, amount)
                VALUES (?, ?, ?)
                ON CONFLICT(user_id, month)
                DO UPDATE SET amount = excluded.amount
            """, (user_id, month, goal))

            conn.commit()
            st.success("Savings goal updated!")
            st.rerun()

    if current_goal > 0:

        progress = max(0, savings / current_goal)
        st.subheader("Goal Progress")

        st.progress(min(progress, 1.0))

        st.write(
            f"₹{max(savings, 0):,.2f} / ₹{current_goal:,.2f}"
        )

        if savings >= current_goal:
            st.success("Congratulations! Goal achieved.")
        else:
            st.info(
                f"Remaining to goal: ₹{current_goal - max(savings, 0):,.2f}"
            )


# =====================================
# ADVANCED ANALYTICS
# =====================================
elif page == "Advanced Analytics":

    st.title("📈 Advanced Analytics")

    df = load_transactions()

    if not df.empty:

        df["entry_date"] = pd.to_datetime(df["entry_date"])

        col1, col2 = st.columns(2)

        with col1:
            start_date = st.date_input(
                "Start Date", date.today() - timedelta(days=365)
            )

        with col2:
            end_date = st.date_input(
                "End Date", date.today()
            )

        if start_date > end_date:
            st.error("Start date must be before end date.")
            st.stop()

        filtered = df[
            (df.entry_date.dt.date >= start_date) &
            (df.entry_date.dt.date <= end_date)
        ].copy()

        expenses_df = filtered[
            filtered.transaction_type == "Expense"
        ]

        income_df = filtered[
            filtered.transaction_type == "Income"
        ]

        st.metric(
            "Total Income",
            f"₹{income_df.amount.sum():,.2f}"
        )

        st.metric(
            "Total Expenses",
            f"₹{expenses_df.amount.sum():,.2f}"
        )

        if not expenses_df.empty:

            st.subheader("Category Analysis")

            category_data = expenses_df.groupby(
                "category"
            )["amount"].sum().reset_index()

            fig = px.bar(
                category_data,
                x="category",
                y="amount",
                color="category",
                title="Spending by Category"
            )

            st.plotly_chart(
                fig, use_container_width=True
            )

            st.subheader("Daily Spending Trend")

            daily_data = expenses_df.groupby(
                "entry_date"
            )["amount"].sum().reset_index()

            fig = px.line(
                daily_data,
                x="entry_date",
                y="amount",
                markers=True
            )

            st.plotly_chart(
                fig, use_container_width=True
            )

        monthly = filtered.copy()

        monthly["month"] = (
            monthly.entry_date.dt.to_period("M").astype(str)
        )

        monthly_data = monthly.pivot_table(
            index="month",
            columns="transaction_type",
            values="amount",
            aggfunc="sum",
            fill_value=0
        ).reset_index()

        st.subheader("Monthly Financial Comparison")

        fig = px.bar(
            monthly_data,
            x="month",
            y=[
                c for c in ["Income", "Expense"]
                if c in monthly_data.columns
            ],
            barmode="group"
        )

        st.plotly_chart(
            fig, use_container_width=True
        )

    else:
        st.info("Add transactions to view analytics.")


# =====================================
# EXPENSE REMINDERS
# =====================================
elif page == "Expense Reminders":

    st.title("🔔 Expense Reminders")

    with st.form("reminder_form"):

        reminder_date = st.date_input(
            "Reminder Date", date.today()
        )

        message = st.text_input(
            "Reminder Message",
            placeholder="Example: Pay electricity bill"
        )

        if st.form_submit_button("Add Reminder"):

            if message.strip():

                conn.execute("""
                    INSERT INTO reminders
                    (user_id, reminder_date, message)
                    VALUES (?, ?, ?)
                """, (
                    user_id,
                    str(reminder_date),
                    message.strip()
                ))

                conn.commit()
                st.success("Reminder saved!")
                st.rerun()

            else:
                st.error("Enter a reminder message.")

    st.divider()
    st.subheader("Your Reminders")

    reminder_rows = conn.execute("""
        SELECT id, reminder_date, message, completed
        FROM reminders
        WHERE user_id = ?
        ORDER BY reminder_date
    """, (user_id,)).fetchall()

    if reminder_rows:

        for rid, rdate, msg, completed in reminder_rows:

            with st.container(border=True):

                st.write(f"**{msg}**")
                st.caption(f"Date: {rdate}")

                if completed:
                    st.success("Completed")
                else:
                    if st.button(
                        "Mark Completed",
                        key=f"done_{rid}"
                    ):
                        conn.execute("""
                            UPDATE reminders
                            SET completed = 1
                            WHERE id = ? AND user_id = ?
                        """, (rid, user_id))

                        conn.commit()
                        st.rerun()

                    if rdate < date.today().isoformat():
                        st.warning("Overdue reminder")
                    elif rdate == date.today().isoformat():
                        st.warning("Due today")
                    else:
                        st.info("Upcoming reminder")

    else:
   
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
