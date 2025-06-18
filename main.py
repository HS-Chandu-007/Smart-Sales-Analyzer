import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from difflib import get_close_matches
import tempfile

st.set_page_config(page_title="Smart Sales Analyzer", layout="centered")
st.title("📊 Smart Sales Analyzer")

# === File Upload ===
upload_file = st.file_uploader("Upload your messy sales data (.csv or .xlsx)", type=["csv", "xlsx"])

# === Helper to guess close column names ===
def guess_column_name(columns, target):
    matches = get_close_matches(target.lower(), [col.lower() for col in columns], n=1, cutoff=0.6)
    if matches:
        for col in columns:
            if col.lower() == matches[0]:
                return col
    return None

# === Main Logic ===
if upload_file is not None:
    try:
        if upload_file.name.endswith(".csv"):
            df = pd.read_csv(upload_file)
        else:
            df = pd.read_excel(upload_file)

        st.subheader("📝 Raw Data Preview")
        st.dataframe(df.head(10))

        # Try to guess important columns
        sales_col = guess_column_name(df.columns, "sales")
        category_col = guess_column_name(df.columns, "category")
        payment_col = guess_column_name(df.columns, "payment")
        date_col = guess_column_name(df.columns, "date")

        if sales_col is None or category_col is None:
            st.error("❌ Could not detect 'Sales' or 'Category' columns. Please check your file.")
            st.stop()

        # Clean Data
        original_count = df.shape[0]
        df_clean = df[[sales_col, category_col]].copy()

        if payment_col:
            df_clean["Payment"] = df[payment_col]
        if date_col:
            df_clean["Date"] = pd.to_datetime(df[date_col], errors="coerce")

        df_clean = df_clean.dropna(subset=[sales_col, category_col])
        df_clean[sales_col] = pd.to_numeric(df_clean[sales_col], errors="coerce")
        df_clean = df_clean.dropna(subset=[sales_col])
        df_clean.columns = ['Sales', 'Category'] + [col for col in ['Payment', 'Date'] if col in df_clean.columns]

        cleaned_count = df_clean.shape[0]
        dropped = original_count - cleaned_count
        if dropped > 0:
            st.warning(f"⚠️ Removed {dropped} rows with missing or invalid data.")

        if df_clean.empty:
            st.error("❌ No valid data left after cleaning. Please check your file.")
            st.stop()

        # === Insights ===
        st.subheader("📈 Insights")
        total_sales = df_clean["Sales"].sum()
        st.write(f"💰 **Total Sales:** ₹{total_sales:,.2f}")

        avg_sales_per_category = df_clean.groupby("Category")["Sales"].mean()
        if not avg_sales_per_category.empty:
            top_category = df_clean.groupby("Category")["Sales"].sum().idxmax()
            st.write(f"🏆 **Top Category:** {top_category}")
            st.write("📊 **Average Sales per Category**:")
            st.dataframe(avg_sales_per_category)
        else:
            st.warning("⚠️ No categories found after cleaning.")

        # === Sales by Category Chart ===
        st.subheader("📊 Total Sales by Category")
        fig1, ax1 = plt.subplots()
        df_clean.groupby("Category")["Sales"].sum().plot(kind="bar", ax=ax1, color="skyblue")
        ax1.set_ylabel("Sales")
        ax1.set_xlabel("Category")
        st.pyplot(fig1)

        # === Average Sales per Category Chart ===
        st.subheader("📊 Average Sales per Category")
        fig2, ax2 = plt.subplots()
        avg_sales_per_category.plot(kind="bar", ax=ax2, color="orange")
        ax2.set_ylabel("Avg Sales")
        ax2.set_xlabel("Category")
        st.pyplot(fig2)

        # === Payment Method Pie Chart ===
        if "Payment" in df_clean.columns:
            st.subheader("💳 Payment Method Distribution")
            payment_counts = df_clean["Payment"].value_counts()
            fig3, ax3 = plt.subplots()
            payment_counts.plot(kind="pie", autopct="%1.1f%%", ax=ax3)
            ax3.set_ylabel("")
            st.pyplot(fig3)

        # === Active Day of Week ===
        if "Date" in df_clean.columns:
            st.subheader("📆 Most Active Days (by Transactions)")
            df_clean["Weekday"] = df_clean["Date"].dt.day_name()
            weekday_counts = df_clean["Weekday"].value_counts().reindex(
                ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'], fill_value=0
            )
            fig4, ax4 = plt.subplots()
            weekday_counts.plot(kind="bar", ax=ax4, color="green")
            ax4.set_ylabel("Number of Transactions")
            ax4.set_xlabel("Day of Week")
            st.pyplot(fig4)

        # === PDF Report Generator ===
        def generate_pdf():
            buffer = BytesIO()
            c = canvas.Canvas(buffer, pagesize=letter)
            width, height = letter

            c.setFont("Helvetica-Bold", 18)
            c.drawString(50, height - 50, "Smart Sales Report")

            c.setFont("Helvetica", 12)
            c.drawString(50, height - 100, f"Total Sales: ₹{total_sales:,.2f}")
            if not avg_sales_per_category.empty:
                c.drawString(50, height - 120, f"Top Category: {top_category}")
            c.drawString(50, height - 140, f"Rows cleaned: {dropped}")

            # Save chart to temp image
            temp_chart = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
            fig1.savefig(temp_chart.name, bbox_inches="tight")
            c.drawImage(temp_chart.name, 50, height - 400, width=400, height=250)

            c.showPage()
            c.save()
            buffer.seek(0)
            return buffer

        pdf = generate_pdf()
        st.download_button("📥 Download PDF Report", data=pdf, file_name="sales_report.pdf", mime="application/pdf")

    except Exception as e:
        st.error(f"❌ Error processing file: {e}")
