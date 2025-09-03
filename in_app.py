import streamlit as st
from supabase import create_client, Client
from datetime import datetime
import uuid

# -------------------------
# Supabase Setup
# -------------------------
url = "https://ksmrejkeqpsxyssfidts.supabase.co"
key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImtzbXJlamtlcXBzeHlzc2ZpZHRzIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTY4MTkzNzksImV4cCI6MjA3MjM5NTM3OX0.ahVvOEseVGgleVFKz7Mip37sHj6Hok7t6RIHUN420AM"  # replace with your anon key
supabase: Client = create_client(url, key)

bucket_name = "attendance-photos"

# -------------------------
# Config
# -------------------------
st.set_page_config(page_title="Attendance App", layout="wide")
st.title("📸 Employee Attendance System")

ADMIN_PASSWORD = "mysecret123"  # 🔑 change this before deployment

# -------------------------
# Employee Section
# -------------------------
def show_employee_ui():
    st.header("🕒 Mark Attendance")

    # Fetch stores
    stores_data = supabase.table("stores").select("*").execute().data
    if not stores_data:
        st.error("No stores found in database.")
        return

    store_options = {s["store_name"]: s["id"] for s in stores_data}
    selected_store = st.selectbox("Select Store", list(store_options.keys()))
    store_id = store_options[selected_store]

    # Fetch employees of this store
    employees_data = supabase.table("employees").select("*").eq("store_id", store_id).execute().data
    if not employees_data:
        st.warning("No employees found for this store.")
        return

    employee_options = {e["employee_name"]: e["id"] for e in employees_data}
    selected_employee = st.selectbox("Select Employee", list(employee_options.keys()))
    emp_id = employee_options[selected_employee]

    # Check if already marked today
    today = datetime.now().strftime("%Y-%m-%d")
    existing = supabase.table("attendance").select("*")\
        .eq("employee_id", emp_id)\
        .gte("timestamp", f"{today} 00:00:00")\
        .lte("timestamp", f"{today} 23:59:59")\
        .execute()

    if existing.data:
        st.success("✅ Attendance already submitted for today. No need to submit again.")
        if existing.data[0]["photo_url"]:
            st.image(existing.data[0]["photo_url"], caption="Your submitted selfie", width=200)
    else:
        # Show camera input
        photo = st.camera_input("Take a selfie")

        if st.button("Submit Attendance"):
            if photo is not None:
                file_name = f"{selected_store}_{selected_employee}_{uuid.uuid4().hex}.png"
                supabase.storage.from_(bucket_name).upload(
                    file_name, photo.getvalue(), {"content-type": "image/png"}
                )
                photo_url = supabase.storage.from_(bucket_name).get_public_url(file_name)
            else:
                photo_url = None

            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            result = supabase.table("attendance").insert({
                "employee_id": emp_id,
                "store_id": store_id,
                "timestamp": timestamp,
                "photo_url": photo_url,
                "status": "Present"
            }).execute()

            if result.data:
                st.success("✅ Attendance submitted successfully!")
                if photo_url:
                    st.image(photo_url, caption="Your submitted selfie", width=200)
            else:
                st.error("❌ Failed to mark attendance.")

# -------------------------
# Admin Section
# -------------------------
def show_admin_ui():
    st.header("📊 Admin Dashboard")

    # Filter by date
    date_filter = st.date_input("Select Date", datetime.now().date())

    # Fetch attendance
    data = supabase.table("attendance").select(
        "id, timestamp, status, photo_url, employees(employee_name), stores(store_name)"
    ).gte("timestamp", f"{date_filter} 00:00:00")\
     .lte("timestamp", f"{date_filter} 23:59:59")\
     .execute()

    records = data.data
    if not records:
        st.info("No attendance records for this date.")
    else:
        for rec in records:
            st.markdown(f"""
            **Employee:** {rec['employees']['employee_name']}  
            **Store:** {rec['stores']['store_name']}  
            **Time:** {rec['timestamp']}  
            **Status:** {rec['status']}  
            """)
            if rec["photo_url"]:
                st.image(rec["photo_url"], width=150)

# -------------------------
# Navigation
# -------------------------
menu = st.sidebar.radio("Navigation", ["Employee", "Admin"])

if menu == "Employee":
    show_employee_ui()
elif menu == "Admin":
    pwd = st.sidebar.text_input("Enter Admin Password", type="password")
    if pwd == ADMIN_PASSWORD:
        show_admin_ui()
    elif pwd:
        st.warning("🔒 Wrong password, access denied.")
    else:
        st.info("Please enter password to access Admin Dashboard.")
