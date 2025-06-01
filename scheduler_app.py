# File: scheduler_app.py
import streamlit as st
import pandas as pd
from datetime import time, datetime # Import datetime for parsing convenience
from scheduler_logic import create_schedule, parse_time_input # Assuming your logic is in scheduler_logic.py

# --- Page Configuration (Optional but good practice) ---
st.set_page_config(page_title="Employee Scheduler", layout="wide")

st.title("Employee Schedule Generator")
st.write("Fill in the details below to generate the schedule.")

# --- Consistent Reference Date for Time Parsing ---
REF_DATE_FOR_PARSING = datetime(1970, 1, 1).date()

# --- Input Sections ---
st.sidebar.header("Configuration")

# Store Hours
st.sidebar.subheader("Store Hours")
store_open_time_str = st.sidebar.text_input("Store Open Time (e.g., 08:00 AM)", "")
store_close_time_str = st.sidebar.text_input("Store Close Time (e.g., 11:00 PM)", "")

# Number of Employees
st.sidebar.subheader("Employees")
num_employees = st.sidebar.number_input("Number of Employees Working", min_value=1, value=1, step=1)

employee_data_list = []
for i in range(num_employees):
    st.sidebar.markdown(f"--- **Employee {i+1}** ---")
    emp_name = st.sidebar.text_input(f"Name (Employee {i+1})", key=f"name_{i}")
    shift_start_str = st.sidebar.text_input(f"Shift Start (Employee {i+1}, e.g., 09:00 AM)", "", key=f"s_start_{i}")
    shift_end_str = st.sidebar.text_input(f"Shift End (Employee {i+1}, e.g., 05:00 PM)", "", key=f"s_end_{i}")
    break_start_str = st.sidebar.text_input(f"Break Start (Employee {i+1}, e.g., 01:00 PM, for 30 min)", "", key=f"break_{i}")
    
    has_tofftl = st.sidebar.checkbox(f"Training Off The Line (ToffTL) for Employee {i+1}?", key=f"has_tofftl_{i}")
    tofftl_start_str = None
    tofftl_end_str = None
    if has_tofftl:
        tofftl_start_str = st.sidebar.text_input(f"ToffTL Start (Employee {i+1})", "", key=f"tofftl_s_{i}")
        tofftl_end_str = st.sidebar.text_input(f"ToffTL End (Employee {i+1})", "", key=f"tofftl_e_{i}")

    if emp_name: # Only add if name is provided
        employee_data_list.append({
            "Name": emp_name,
            "Shift Start": shift_start_str, "Shift End": shift_end_str,
            "Break": break_start_str,
            "ToffTL Start": tofftl_start_str, "ToffTL End": tofftl_end_str
        })

# --- Generate Schedule Button ---
if st.sidebar.button("Generate Schedule"):
    if not employee_data_list:
        st.error("Please add at least one employee.")
    else:
        # Validate and parse store times
        store_open_dt = parse_time_input(store_open_time_str, REF_DATE_FOR_PARSING)
        store_close_dt = parse_time_input(store_close_time_str, REF_DATE_FOR_PARSING)

        if pd.isna(store_open_dt) or pd.isna(store_close_dt):
            st.error("Invalid store open or close time format. Please use HH:MM AM/PM or HH:MM.")
        else:
            store_open_time_obj = store_open_dt.time()
            store_close_time_obj = store_close_dt.time()
            
            # Basic validation for employee data before passing to the main logic
            valid_employee_data = True
            for emp_idx, emp_d in enumerate(employee_data_list):
                if not emp_d["Name"].strip():
                    st.error(f"Employee {emp_idx+1} name is missing.")
                    valid_employee_data = False
                    break
                # Add more detailed time validation for each employee if needed here,
                # though parse_time_input in scheduler_logic will handle NaT for bad formats.
                # For Streamlit, it's good to provide immediate feedback if possible.

            if valid_employee_data:
                st.info("Generating schedule... Please wait.")
                try:
                    # Call your scheduling logic
                    schedule_csv_string = create_schedule(store_open_time_obj, store_close_time_obj, employee_data_list)
                    
                    st.success("Schedule Generated Successfully!")
                    
                    # Display the schedule
                    st.subheader("Generated Schedule (CSV Format)")
                    st.text_area("CSV Output", schedule_csv_string, height=400)
                    
                    # Provide download button
                    st.download_button(
                        label="Download Schedule as CSV",
                        data=schedule_csv_string,
                        file_name="schedule.csv",
                        mime="text/csv",
                    )
                except Exception as e:
                    st.error(f"An error occurred during schedule generation: {e}")
                    # You might want to print more detailed traceback for debugging if running locally
                    # import traceback
                    # st.text(traceback.format_exc())
            else:
                st.warning("Please correct the employee data errors above.")


st.sidebar.markdown("---")
st.sidebar.markdown("Ensure all time inputs are in a recognizable format (e.g., '9:00 AM', '14:30').")
