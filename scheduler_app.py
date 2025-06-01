# File: scheduler_app.py
import streamlit as st
import pandas as pd
from datetime import time, datetime # Import datetime for parsing convenience
from scheduler_logic import create_schedule, parse_time_input # Assuming your logic is in scheduler_logic.py

# \--- Page Configuration (Optional but good practice) ---

st.set\_page\_config(page\_title="Employee Scheduler", layout="wide")

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
