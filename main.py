import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import tempfile
from difflib import get_close_matches

# Page settings
st.set_page_config(page_title="Smart Sales Analyzer", layout="centered")
st.title("📊 Smart Sales Analyzer")

# File uploader
upload_file = st.file_uploader("Upload your sales data (.csv or .xlsx)", type=["csv", "xlsx"])

# Smarter column name matcher
def guess_column_name(columns, alias_list, field_name):
    clean_names = [col.strip().lower() for col in columns]
    for alias in alias_list:
        match = get_close_matches(alias, clean_names, n=1, cutoff=0.6)
        if match:
            idx = clean_names.index(match[0])
            col = columns[idx]
            st.success(f"✅ Matched '{field_name}' to column: `{col}`")
            return col
    return None

# Main logic
if upload_file is not None:
    try:
        # Read file
        if upload_file.name.endswith(".csv"):
            df = pd.read_csv(upload_file)
        else:
            df = pd.read_excel(upload_file)

        st.write("🧾 Detected Columns in File:")
        st.write(list(df.columns))

        # Match column names
        sales_col = guess_column_name(df.columns, ["sales", "amount", "total", "revenue", "price"], "Sales")
        category_col = guess_column_name(df.columns, ["category", "product", "item", "type", "name"], "Category")
        date_col = guess_column_name(df.columns, ["date", "order date", "timestamp"], "Date")
        payment_col = guess_column_name(df.columns, ["payment", "payment method", "method", "mode"], "Payment Method")

        if sales_col is None or category_col is None:
            st.error("❌ Could not detect 'Sales' or 'Category' columns. Please check your file.")
            st.stop()

        # Clean Data
        df_clean = df[[sales_col, category_col]].copy()
        df_clean.dropna(inplace=True)
        df_clean[sales_col] = pd.to_numeric(df_clean[sales_col], errors='coerce')
        df_clean.dropna(inplace=True)
        df_clean.columns = ["Sales", "Category"]

        st.subheader("🔍 Preview of Cleaned Data")
        st.dataframe(df_clean.head(10))

        # Insights
        st.subheader("📈 Insights")
        total_sales = df_clean["Sales"].sum()
        avg_sales_per_category = df_clean.groupby("Category")["Sales"].mean()
        st.write(f"💰 **Total Sales**: ₹{total_sales:,.2f}")
        if not df_clean.empty:
            top_category = df_clean.groupby("Category")["Sales"].sum().idxmax()
            st.write(f"🏆 **Top Category**: {top_category}")
        st.write("📊 **Average Sales per Category**:")
        st.write(avg_sales_per_category)

        # Charts
        st.subheader("📊 Sales by Category")
        fig1, ax1 = plt.subplots()
        df_clean.groupby("Category")["Sales"].sum().plot(kind="bar", ax=ax1, color="skyblue")
        ax1.set_title("Total Sales by Category")
        st.pyplot(fig1)

        st.subheader("📊 Average Sales per Category")
        fig2, ax2 = plt.subplots()
        avg_sales_per_category.plot(kind="bar", ax=ax2, color="orange")
        ax2.set_title("Average Sales by Category")
        st.pyplot(fig2)

        # Optional: Payment Method Pie
        if payment_col and payment_col in df.columns:
            st.subheader("💳 Payment Method Distribution")
            payment_counts = df[payment_col].value_counts()
            fig3, ax3 = plt.subplots()
            ax3.pie(payment_counts, labels=payment_counts.index, autopct="%1.1f%%", startangle=140)
            ax3.axis("equal")
            st.pyplot(fig3)

        # Optional: Trend over days
        if date_col and date_col in df.columns:
            df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
            df["Day"] = df[date_col].dt.day_name()
            st.subheader("📆 Most Active Days (by Order Count)")
            day_counts = df["Day"].value_counts()
            fig4, ax4 = plt.subplots()
            day_counts.plot(kind="bar", ax=ax4, color="green")
            ax4.set_title("Sales Activity by Day of Week")
            st.pyplot(fig4)

        # === PDF Report ===
        def generate_pdf():
            buffer = BytesIO()
            c = canvas.Canvas(buffer, pagesize=letter)
            width, height = letter

            c.setFont("Helvetica-Bold", 18)
            c.drawString(50, height - 50, "Smart Sales Report")

            c.setFont("Helvetica", 12)
            c.drawString(50, height - 100, f"Total Sales: ₹{total_sales:,.2f}")
            if not df_clean.empty:
                c.drawString(50, height - 120, f"Top Category: {top_category}")
            c.drawString(50, height - 140, "Average Sales per Category:")

            y = height - 160
            for cat, val in avg_sales_per_category.items():
                c.drawString(60, y, f"{cat}: ₹{val:,.2f}")
                y -= 15

            # Save chart to image
            temp_chart = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
            fig1.savefig(temp_chart.name, bbox_inches="tight")

            # Add chart to PDF
            c.drawImage(temp_chart.name, 50, 200, width=400, height=250)
            c.showPage()
            c.save()
            buffer.seek(0)
            return buffer

        pdf = generate_pdf()
        st.download_button("📥 Download PDF Report", data=pdf, file_name="sales_report.pdf", mime="application/pdf")

    except Exception as e:
        st.error(f"❌ Error processing file: {e}")
