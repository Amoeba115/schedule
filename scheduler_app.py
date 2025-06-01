# File: scheduler_app.py
import streamlit as st
import pandas as pd
from datetime import time, datetime # Import datetime for parsing convenience
from scheduler_logic import create_schedule, parse_time_input # Assuming your logic is in scheduler_logic.py

# \--- Page Configuration (Optional but good practice) ---

st.set\page\_config(page\_title="Employee Scheduler", layout="wide")

st.title("Employee Schedule Generator")
st.write("Fill in the details below to generate the schedule.")

# \--- Consistent Reference Date for Time Parsing ---

REF\_DATE\_FOR\_PARSING = datetime(1970, 1, 1).date()

# \--- Input Sections ---

st.sidebar.header("Configuration")

# Store Hours

st.sidebar.subheader("Store Hours")
store\_open\_time\_str = st.sidebar.text\_input("Store Open Time (e.g., 08:00 AM)", "", placeholder="e.g., 08:00 AM")
store\_close\_time\_str = st.sidebar.text\_input("Store Close Time (e.g., 11:00 PM)", "", placeholder="e.g., 11:00 PM")

# Number of Employees

st.sidebar.subheader("Employees")
num\_employees\_input = st.sidebar.number\_input(
"Number of Employees Working",
min\_value=0,  \# Allow 0 if user wants to clear/start over
value=None,   \# Start with no pre-filled number
step=1,
placeholder="Enter number"
)

employee\_data\_list = []
num\_employees\_for\_loop = 0
if num\_employees\_input is not None and num\_employees\_input \> 0:
num\_employees\_for\_loop = int(num\_employees\_input)

if num\_employees\_for\_loop \> 0:
st.sidebar.markdown("--- **Employee Details** ---")
for i in range(num\_employees\_for\_loop):
st.sidebar.markdown(f"--- **Employee {i+1}** ---")
emp\_name = st.sidebar.text\_input(f"Name (Employee {i+1})", "", key=f"name\_{i}", placeholder="Employee's full name")
shift\_start\_str = st.sidebar.text\_input(f"Shift Start (Employee {i+1})", "", key=f"s\_start\_{i}", placeholder="e.g., 09:00 AM")
shift\_end\_str = st.sidebar.text\_input(f"Shift End (Employee {i+1})", "", key=f"s\_end\_{i}", placeholder="e.g., 05:00 PM")
break\_start\_str = st.sidebar.text\_input(f"Break Start (Employee {i+1}, for 30 min)", "", key=f"break\_{i}", placeholder="e.g., 01:00 PM")

has_tofftl = st.sidebar.checkbox(f"Training Off The Line (ToffTL) for Employee {i+1}?", key=f"has_tofftl_{i}", value=False)
tofftl_start_str = None
tofftl_end_str = None
if has_tofftl:
    tofftl_start_str = st.sidebar.text_input(f"ToffTL Start (Employee {i+1})", "", key=f"tofftl_s_{i}", placeholder="e.g., 10:00 AM")
    tofftl_end_str = st.sidebar.text_input(f"ToffTL End (Employee {i+1})", "", key=f"tofftl_e_{i}", placeholder="e.g., 10:30 AM")

# Collect data only if a name is provided to avoid empty employee entries
# This collection happens dynamically as user types.
# The actual list used for generation is built when the button is pressed.

# \--- Generate Schedule Button ---

if st.sidebar.button("Generate Schedule"):
\# Re-collect and validate employee\_data\_list just before generation
\# This ensures we use the latest values from the input fields
employee\_data\_list\_for\_generation = []
if num\_employees\_for\_loop \> 0:
for i in range(num\_employees\_for\_loop):
\# Retrieve values from session state (Streamlit handles this via keys)
emp\_name\_current = st.session\_state[f"name\_{i}"]
shift\_start\_current = st.session\_state[f"s\_start\_{i}"]
shift\_end\_current = st.session\_state[f"s\_end\_{i}"]
break\_start\_current = st.session\_state[f"break\_{i}"]
has\_tofftl\_current = st.session\_state[f"has\_tofftl\_{i}"]
tofftl\_s\_current = st.session\_state.get(f"tofftl\_s\_{i}", None) if has\_tofftl\_current else None
tofftl\_e\_current = st.session\_state.get(f"tofftl\_e\_{i}", None) if has\_tofftl\_current else None

    if emp_name_current.strip(): # Only process if name is not blank
        employee_data_list_for_generation.append({
            "Name": emp_name_current,
            "Shift Start": shift_start_current, "Shift End": shift_end_current,
            "Break": break_start_current,
            "ToffTL Start": tofftl_s_current, "ToffTL End": tofftl_e_current,
            "has_tofftl_flag_for_validation": has_tofftl_current # For validation step
        })
if num_employees_input is None or num_employees_input &lt; 1:
st.error("Please enter a valid number of employees (at least 1).")
elif not employee_data_list_for_generation and num_employees_input > 0:
st.error(f"Please enter details for the {num_employees_input} employee(s). Ensure names are filled for all.")
else:
store_open_dt = parse_time_input(store_open_time_str, REF_DATE_FOR_PARSING)
store_close_dt = parse_time_input(store_close_time_str, REF_DATE_FOR_PARSING)

if pd.isna(store_open_dt) or pd.isna(store_close_dt):
    st.error("Invalid or missing store open/close time. Please use HH:MM AM/PM or HH:MM format.")
else:
    store_open_time_obj = store_open_dt.time()
    store_close_time_obj = store_close_dt.time()
    
    valid_employee_data = True
    final_employee_list_for_processing = [] # List after validation
    for emp_idx, emp_d in enumerate(employee_data_list_for_generation):
        if not emp_d["Name"].strip(): # Should have been caught, but good to re-check
            st.error(f"Employee {emp_idx+1} name is missing.")
            valid_employee_data = False; break
        if not emp_d["Shift Start"].strip() or not emp_d["Shift End"].strip() or not emp_d["Break"].strip():
            st.error(f"Shift Start, Shift End, and Break Start are required for {emp_d['Name']}.")
            valid_employee_data = False; break
        if emp_d.get("has_tofftl_flag_for_validation", False) and \
           (not emp_d.get("ToffTL Start", "").strip() or not emp_d.get("ToffTL End", "").strip()):
            st.error(f"ToffTL Start and End times are required for {emp_d['Name']} since ToffTL was checked.")
            valid_employee_data = False; break
        
        # Remove the temporary validation flag before passing to scheduler_logic
        emp_d_cleaned = emp_d.copy()
        emp_d_cleaned.pop("has_tofftl_flag_for_validation", None)
        final_employee_list_for_processing.append(emp_d_cleaned)

    if valid_employee_data and final_employee_list_for_processing:
        st.info("Generating schedule... Please wait.")
        try:
            schedule_csv_string = create_schedule(store_open_time_obj, store_close_time_obj, final_employee_list_for_processing)
            st.success("Schedule Generated Successfully!")
            st.subheader("Generated Schedule (CSV Format)")
            st.text_area("CSV Output", schedule_csv_string, height=400)
            st.download_button(
                label="Download Schedule as CSV",
                data=schedule_csv_string,
                file_name="schedule.csv", # Changed filename
                mime="text/csv",
            )
        except Exception as e:
            st.error(f"An error occurred during schedule generation: {e}")
            # import traceback # Uncomment for detailed local debugging
            # st.text(traceback.format_exc()) # Uncomment for detailed local debugging
    elif valid_employee_data and not final_employee_list_for_processing: # All names were blank
         st.error("No employee data was collected. Please ensure names are filled for each employee.")
    # else: errors already shown by validation loop

st.sidebar.markdown("---")
st.sidebar.markdown("Ensure all time inputs are in a recognizable format (e.g., '9:00 AM', '14:30'). Break is 30 minutes from start time.")
