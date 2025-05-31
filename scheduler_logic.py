# File: scheduler_logic.py
import pandas as pd
from io import StringIO
from datetime import datetime, time

# STORE_OPEN_TIME and STORE_CLOSE_TIME will now be passed as arguments
# to the main function.

# Helper function to parse time strings
def parse_time_input(time_val, ref_date_for_parsing):
    if pd.isna(time_val) or str(time_val).strip().upper() == 'N/A' or str(time_val).strip() == '':
        return pd.NaT
    try:
        # Attempt to parse as datetime with a reference date
        dt_obj = pd.to_datetime(f"{ref_date_for_parsing.strftime('%Y-%m-%d')} {str(time_val).strip()}")
        return dt_obj
    except ValueError:
        try:
            # Fallback: attempt to parse as time only and combine with reference date
            time_obj = pd.to_datetime(str(time_val).strip()).time()
            return datetime.combine(ref_date_for_parsing, time_obj)
        except ValueError:
            return pd.NaT # Return NaT if all parsing attempts fail

# Preprocessing function adapted to take a list of employee data dictionaries
def preprocess_employee_data_to_long_format(employee_data_list, ref_date_for_parsing):
    all_employee_slots = []
    activity_definitions = {"ToffTL": ("ToffTL Start", "ToffTL End")}

    for emp_data in employee_data_list:
        name_str = emp_data.get('Name', '')
        first_name, last_name_part = (name_str.split(" ", 1) + [""])[:2] if " " in name_str else (name_str, "")
        emp_name_fml = f"{first_name} {last_name_part[0] + '.' if last_name_part else ''}".strip()

        shift_start_dt = parse_time_input(emp_data.get('Shift Start'), ref_date_for_parsing)
        shift_end_dt = parse_time_input(emp_data.get('Shift End'), ref_date_for_parsing)
        if pd.notna(shift_start_dt) and pd.notna(shift_end_dt) and shift_end_dt < shift_start_dt:
            shift_end_dt += pd.Timedelta(days=1)
        
        activity_times = {}
        for internal_key, (start_col_key, end_col_key) in activity_definitions.items():
            s_dt = parse_time_input(emp_data.get(start_col_key), ref_date_for_parsing)
            e_dt = parse_time_input(emp_data.get(end_col_key), ref_date_for_parsing)
            if pd.notna(s_dt) and pd.notna(e_dt) and e_dt < s_dt: e_dt += pd.Timedelta(days=1)
            activity_times[internal_key] = (s_dt, e_dt)
        
        unpaid_break_start_dt = parse_time_input(emp_data.get('Break'), ref_date_for_parsing)
        unpaid_break_end_dt = None
        if pd.notna(unpaid_break_start_dt):
            unpaid_break_end_dt = unpaid_break_start_dt + pd.Timedelta(minutes=30)

        if pd.notna(shift_start_dt) and pd.notna(shift_end_dt):
            current_time_slot_start = shift_start_dt
            while current_time_slot_start < shift_end_dt:
                slot_time_str = current_time_slot_start.strftime('%I:%M %p').lstrip('0')
                position_scheduled_as = "Available" 
                is_unpaid_break_str = "FALSE" 

                if pd.notna(activity_times['ToffTL'][0]) and pd.notna(activity_times['ToffTL'][1]) and \
                activity_times['ToffTL'][0] <= current_time_slot_start < activity_times['ToffTL'][1]:
                    position_scheduled_as = "ToffTL"
                
                if pd.notna(unpaid_break_start_dt) and pd.notna(unpaid_break_end_dt) and \
                unpaid_break_start_dt <= current_time_slot_start < unpaid_break_end_dt:
                    is_unpaid_break_str = "TRUE"

                all_employee_slots.append({
                    'Time': slot_time_str, 'EmployeeNameFML': emp_name_fml,
                    'Position Scheduled As': position_scheduled_as, 'Unpaid Break': is_unpaid_break_str 
                })
                current_time_slot_start += pd.Timedelta(minutes=30)
    
    return pd.DataFrame(all_employee_slots, columns=['Time','EmployeeNameFML','Position Scheduled As','Unpaid Break']) if all_employee_slots else \
        pd.DataFrame(columns=['Time','EmployeeNameFML','Position Scheduled As','Unpaid Break'])

# This is the main function Streamlit will call
def create_schedule(store_open_time_obj, store_close_time_obj, employee_data_list):
    # Use the passed store hours
    STORE_OPEN_TIME = store_open_time_obj
    STORE_CLOSE_TIME = store_close_time_obj
    REF_DATE_FOR_PARSING = datetime(1970, 1, 1).date() # Consistent ref date

    positions_ordered = ["Handout", "Line Buster 1", "Conductor", "Line Buster 2", "Expo", "Drink Maker 1", "Drink Maker 2", "Line Buster 3", "Break", "ToffTL"]
    work_positions_priority_order = ["Handout", "Line Buster 1", "Conductor", "Line Buster 2", "Expo", "Drink Maker 1", "Drink Maker 2", "Line Buster 3"]
    line_buster_roles = ["Line Buster 1", "Line Buster 2", "Line Buster 3"]
    paired_position_defs = {
        "HLB1": {"pos1": "Handout", "pos2": "Line Buster 1", "emps": (None, None), "emp1_is_pos1_in_first_half": True, "slots_done_this_hour": 0, "is_broken_this_hour": False},
        "LB2E": {"pos1": "Line Buster 2", "pos2": "Expo", "emps": (None, None), "emp1_is_pos1_in_first_half": True, "slots_done_this_hour": 0, "is_broken_this_hour": False}
    }
    essential_positions_for_backfill = ["Handout", "Line Buster 1"]


    df = preprocess_employee_data_to_long_format(employee_data_list, REF_DATE_FOR_PARSING)
    if df.empty: return "No employee slots generated from input."

    try: 
        df['TimeObject'] = pd.to_datetime(df['Time'], format='%I:%M %p', errors='coerce').fillna(pd.to_datetime(df['Time'], errors='coerce'))
        unique_times = df.drop_duplicates(subset=['TimeObject']).sort_values(by='TimeObject')
        all_slots_str, time_map = list(unique_times['Time']), pd.Series(unique_times['TimeObject'].values, index=unique_times['Time']).to_dict()
        if df['TimeObject'].isnull().any(): raise ValueError("Some times still unparsed after fallback.")
    except Exception as e:
        print(f"Time sort warning: {e}. Using string sort as fallback."); all_slots_str = sorted(df['Time'].unique())
        time_map = {ts: parse_time_input(ts, REF_DATE_FOR_PARSING) for ts in all_slots_str}

    emp_info_map = {t: [] for t in all_slots_str}
    for _, r in df.iterrows(): emp_info_map[r['Time']].append({"name":r['EmployeeNameFML'], "role_scheduled_as":str(r['Position Scheduled As']).strip(), "is_unpaid_break":str(r['Unpaid Break']).strip().upper() in ['TRUE','YES','1','X','T']})

    schedule_rows = []
    emp_lb_last = {}; emp_cur_pos = {}; emp_time_cur_pos = {}; emp_last_time_spec_pos = {}
    g_time_step = 0

    for time_slot in all_slots_str:
        g_time_step += 1; cur_assigns = {p:"" for p in positions_ordered}; 
        cur_assigns["Break"]=[]; cur_assigns["ToffTL"]=[]
        
        active_emps_details = emp_info_map.get(time_slot,[])
        processed_this_slot_initially = set() 
        avail_for_work = [] 
        sorted_active_emps = sorted(active_emps_details, key=lambda x: x['name'])

        for emp_d in sorted_active_emps: 
            emp_n = emp_d["name"]
            if emp_d["is_unpaid_break"]: 
                processed_this_slot_initially.add(emp_n); cur_assigns["Break"].append(emp_n)
                emp_lb_last[emp_n]=False; emp_cur_pos[emp_n]=None; emp_time_cur_pos[emp_n]=0
            elif emp_d["role_scheduled_as"] == "ToffTL": 
                processed_this_slot_initially.add(emp_n); cur_assigns["ToffTL"].append(emp_n)
                emp_lb_last[emp_n]=False; emp_cur_pos[emp_n]=None; emp_time_cur_pos[emp_n]=0
        
        for emp_d in sorted_active_emps: 
            if emp_d["name"] not in processed_this_slot_initially:
                avail_for_work.append(emp_d["name"])
        
        currently_assigned_this_slot_overall = processed_this_slot_initially.copy()

        curr_time_obj = time_map.get(time_slot); is_store_open_for_slot = False
        if pd.notna(curr_time_obj):
            current_slot_time_component = curr_time_obj.time()
            if STORE_OPEN_TIME <= STORE_CLOSE_TIME: 
                if STORE_OPEN_TIME <= current_slot_time_component < STORE_CLOSE_TIME:
                    is_store_open_for_slot = True
            else: 
                if current_slot_time_component >= STORE_OPEN_TIME or current_slot_time_component < STORE_CLOSE_TIME:
                    is_store_open_for_slot = True
        
        if is_store_open_for_slot:
            # --- Backfill pass for essential positions has been removed as per latest user prompt
            # --- focusing on the layered ideal -> relax -> relax -> final backfill for all available.
            # --- The "Strict Priority" is handled by order of work_positions_priority_order and the
            # --- higher_priority_pos_filled_in_main_pass flag.
            # TonTL employees are now part of avail_for_work if not on break/ToffTL.
            # No special pre-assignment for TonTL to Line Buster 2.

            higher_priority_pos_filled_in_main_pass = True 
            
            if pd.notna(curr_time_obj) and curr_time_obj.minute == 0: 
                for pair_id in paired_position_defs:
                    paired_position_defs[pair_id]["is_broken_this_hour"] = False
                    if paired_position_defs[pair_id]["slots_done_this_hour"] == 2:
                        paired_position_defs[pair_id]["slots_done_this_hour"] = 0
                        paired_position_defs[pair_id]["emps"] = (None, None)

            for pos_to_fill in work_positions_priority_order:
                if not higher_priority_pos_filled_in_main_pass: 
                    cur_assigns[pos_to_fill] = ""; continue 
                if cur_assigns[pos_to_fill]: 
                    higher_priority_pos_filled_in_main_pass = True; continue 

                chosen_candidate = None
                
                for attempt_level in range(3): # 0: Ideal, 1: Relax Pairs, 2: Relax Conductor Start for Conductor
                    if chosen_candidate: break 
                    
                    current_pair_id = None
                    for pid, pdef_val in paired_position_defs.items(): # Renamed pdef to pdef_val
                        if pos_to_fill == pdef_val["pos1"] or pos_to_fill == pdef_val["pos2"]:
                            current_pair_id = pid; break
                    
                    # --- Attempt to fill pos_to_fill based on attempt_level ---
                    if pos_to_fill == "Conductor":
                        potential_c_cont = [e for e in avail_for_work if e not in currently_assigned_this_slot_overall and emp_cur_pos.get(e)==pos_to_fill and emp_time_cur_pos.get(e,0)==1]
                        if potential_c_cont: chosen_candidate = sorted(potential_c_cont)[0]
                        else:
                            is_on_hour_cond = pd.notna(curr_time_obj) and curr_time_obj.minute == 0
                            can_start_new_conductor = is_on_hour_cond or (attempt_level >= 2) # Relax on-hour for level 2+
                            if can_start_new_conductor:
                                elig_new_c = [e for e in avail_for_work if e not in currently_assigned_this_slot_overall and not (emp_cur_pos.get(e)==pos_to_fill and emp_time_cur_pos.get(e,0)>=2)]
                                if elig_new_c:
                                    temp_c=None; min_lt_c=float('inf')
                                    for c_cand in elig_new_c:
                                        lt=emp_last_time_spec_pos.get(c_cand,{}).get(pos_to_fill,-1)
                                        if lt<min_lt_c:min_lt_c=lt;temp_c=c_cand
                                        elif lt==min_lt_c and (temp_c is None or c_cand<temp_c):temp_c=c_cand
                                    chosen_candidate=temp_c
                    elif current_pair_id and (attempt_level == 0 and not paired_position_defs[current_pair_id]["is_broken_this_hour"]):
                        # Ideal Paired Logic (Simplified for filling one part of the pair at a time)
                        pair_info = paired_position_defs[current_pair_id]; p1, p2 = pair_info["pos1"], pair_info["pos2"]; eA, eB = pair_info["emps"]
                        if pair_info["slots_done_this_hour"] == 1 and eA and eB and eA not in currently_assigned_this_slot_overall and eB not in currently_assigned_this_slot_overall: 
                            # Determine which employee should take pos_to_fill for the swap
                            emp_for_swap = None
                            if pos_to_fill == p1: emp_for_swap = eB if pair_info["emp1_is_pos1_in_first_half"] else eA
                            elif pos_to_fill == p2: emp_for_swap = eA if pair_info["emp1_is_pos1_in_first_half"] else eB
                            if emp_for_swap and not (pos_to_fill in line_buster_roles and emp_lb_last.get(emp_for_swap,False)): chosen_candidate = emp_for_swap
                        elif pair_info["slots_done_this_hour"] == 0 or pair_info["slots_done_this_hour"] == 2: 
                            # Try to find a new person for this part of a new pair (pos_to_fill)
                            elig_for_new_pair_part = [e for e in avail_for_work if e not in currently_assigned_this_slot_overall and not (pos_to_fill in line_buster_roles and emp_lb_last.get(e,False)) and not (emp_cur_pos.get(e)==pos_to_fill and emp_time_cur_pos.get(e,0)>=1)]
                            if elig_for_new_pair_part:
                                cand_part=None;min_lt_part=float('inf')
                                for c_part in elig_for_new_pair_part:
                                    lt_part=emp_last_time_spec_pos.get(c_part,{}).get(pos_to_fill,-1)
                                    if lt_part<min_lt_part:min_lt_part=lt_part;cand_part=c_part
                                    elif lt_part==min_lt_part and (cand_part is None or c_part<cand_part):cand_part=c_part
                                chosen_candidate = cand_part
                    elif current_pair_id and attempt_level == 1: # Relaxed Pair (LRU for this part of pair)
                        paired_position_defs[current_pair_id]["is_broken_this_hour"] = True # Mark pair as broken for this hour
                        elig_relax_pair = [e for e in avail_for_work if e not in currently_assigned_this_slot_overall and not (pos_to_fill in line_buster_roles and emp_lb_last.get(e,False)) and not (emp_cur_pos.get(e)==pos_to_fill and emp_time_cur_pos.get(e,0)>=1)]
                        if elig_relax_pair: 
                            temp_relax=None;min_lt_relax=float('inf')
                            for c_relax in elig_relax_pair:
                                lt_relax=emp_last_time_spec_pos.get(c_relax,{}).get(pos_to_fill,-1)
                                if lt_relax<min_lt_relax:min_lt_relax=lt_relax;temp_relax=c_relax
                                elif lt_relax==min_lt_relax and (temp_relax is None or c_relax<temp_relax):temp_relax=c_relax
                            chosen_candidate=temp_relax
                    elif not current_pair_id : # Individual position (not Conductor, not part of a pair being ideally handled)
                        elig_lru = [e for e in avail_for_work if e not in currently_assigned_this_slot_overall and not (pos_to_fill in line_buster_roles and emp_lb_last.get(e,False)) and not (emp_cur_pos.get(e)==pos_to_fill and emp_time_cur_pos.get(e,0)>=1)]
                        if elig_lru: 
                            temp_lru=None;min_lt_lru=float('inf')
                            for c_lru in elig_lru:
                                lt_lru=emp_last_time_spec_pos.get(c_lru,{}).get(pos_to_fill,-1)
                                if lt_lru<min_lt_lru:min_lt_lru=lt_lru;temp_lru=c_lru
                                elif lt_lru==min_lt_lru and (temp_lru is None or c_lru<temp_lru):temp_lru=c_lru
                            chosen_candidate=temp_lru
                
                # --- Assign if chosen_candidate found in any attempt for this pos_to_fill ---
                if chosen_candidate:
                    emp_assigned = chosen_candidate
                    cur_assigns[pos_to_fill] = emp_assigned; currently_assigned_this_slot_overall.add(emp_assigned) 
                    emp_lb_last[emp_assigned] = (pos_to_fill in line_buster_roles)
                    if emp_cur_pos.get(emp_assigned) == pos_to_fill: emp_time_cur_pos[emp_assigned] = emp_time_cur_pos.get(emp_assigned, 0) + 1
                    else: emp_cur_pos[emp_assigned] = pos_to_fill; emp_time_cur_pos[emp_assigned] = 1
                    emp_last_time_spec_pos.setdefault(emp_assigned, {})[pos_to_fill] = g_time_step
                    higher_priority_pos_filled_in_main_pass = True
                    
                    # Update paired rotation state if this assignment was part of it
                    if current_pair_id and not paired_position_defs[current_pair_id]["is_broken_this_hour"]:
                        pair_info = paired_position_defs[current_pair_id]
                        p1_name = pair_info["pos1"] #; p2_name = pair_info["pos2"] # Not needed here
                        if pair_info["slots_done_this_hour"] == 1: # This was the swap completing the second half for the pair
                            pair_info["slots_done_this_hour"] = 2
                        elif pair_info["slots_done_this_hour"] == 0: # First half of a new pair
                            # This assignment is one half of the pair.
                            # If Handout (p1) was just filled by emp_assigned:
                            if pos_to_fill == p1_name:
                                pair_info["emps"] = (emp_assigned, None)
                                pair_info["emp1_is_pos1_in_first_half"] = True
                            else: # pos_to_fill was p2
                                pair_info["emps"] = (None, emp_assigned) # This assumes p1 would be filled by another iteration
                                pair_info["emp1_is_pos1_in_first_half"] = False # This assignment was p2
                            # If both parts of pair get filled in this time slot (by different iterations of pos_to_fill)
                            # this simplified state update will need adjustment or rely on the next slot to confirm pair.
                            # For now, if either part of a "new" pair is filled, we mark slots_done_this_hour to 1
                            # This means the *next* slot will attempt a swap if the *other half* also gets filled.
                            # This logic for pair formation is simplified and might need more robust handling
                            # to ensure two distinct people are chosen for a new pair simultaneously.
                            # The current loop processes one pos_to_fill at a time.
                            if pair_info["emps"][0] and pair_info["emps"][1]: # If both are somehow filled
                                pair_info["slots_done_this_hour"] = 1
                            elif pair_info["emps"][0] or pair_info["emps"][1]: # If one part is filled
                                # Let's assume if one part is filled, we tentatively start the hour for that person
                                # The other part needs to be filled by its own pos_to_fill iteration.
                                # This state update is tricky with sequential filling.
                                pass # For now, leave slots_done_this_hour as 0 until both are confirmed or reset.
                                    # This implies the paired rotation might not form correctly if p2 doesn't find someone.

                else: # No candidate found for this pos_to_fill even after relaxations
                    higher_priority_pos_filled_in_main_pass = False; cur_assigns[pos_to_fill] = "" 
            
            # --- Final Backfill Pass for any unassigned available employee ---
            still_unassigned_available = [emp for emp in avail_for_work if emp not in currently_assigned_this_slot_overall]
            for emp_to_backfill in still_unassigned_available:
                for pos_bf in work_positions_priority_order: 
                    if not cur_assigns[pos_bf]: 
                        if pos_bf in line_buster_roles and emp_lb_last.get(emp_to_backfill, False): continue 
                        cur_assigns[pos_bf] = emp_to_backfill; currently_assigned_this_slot_overall.add(emp_to_backfill)
                        emp_lb_last[emp_to_backfill] = (pos_bf in line_buster_roles)
                        if emp_cur_pos.get(emp_to_backfill) == pos_bf: emp_time_cur_pos[emp_to_backfill] = emp_time_cur_pos.get(emp_to_backfill, 0) + 1
                        else: emp_cur_pos[emp_to_backfill] = pos_bf; emp_time_cur_pos[emp_to_backfill] = 1
                        emp_last_time_spec_pos.setdefault(emp_to_backfill, {})[pos_bf] = g_time_step
                        break # Employee backfilled, move to next unassigned employee
        
        # --- Final state reset for employees truly unassigned after all passes ---
        for emp_d_final in active_emps_details:
            emp_n_f = emp_d_final["name"]
            assigned_station_finally = any(cur_assigns.get(wp)==emp_n_f for wp in work_positions_priority_order) 
            if not assigned_station_finally: 
                if not emp_d_final["is_unpaid_break"] and emp_d_final["role_scheduled_as"] != "ToffTL":
                    emp_lb_last[emp_n_f]=False; emp_cur_pos[emp_n_f]=None; emp_time_cur_pos[emp_n_f]=0
        
        row_data = {"Time": time_slot}
        for pos_col in positions_ordered:
            if pos_col == "Break" or pos_col == "ToffTL": row_data[pos_col] = ", ".join(sorted(list(set(cur_assigns.get(pos_col,[])))))
            else: row_data[pos_col] = cur_assigns.get(pos_col,"")
        schedule_rows.append(row_data)

    if not schedule_rows: return "No schedule data."
    out_df = pd.DataFrame(schedule_rows, columns=["Time"]+positions_ordered)
    out_df['Break'] = out_df['Break'].apply(lambda x: "" if not x else x)
    out_df['ToffTL'] = out_df['ToffTL'].apply(lambda x: "" if not x else x)
    final_df = out_df.set_index("Time").transpose().reset_index().rename(columns={'index':'Position'})
    return final_df.to_csv(index=False)

# To run this script if it were the main file:
# if __name__ == "__main__":
#     schedule_csv = generate_schedule_interactive()
#     print(schedule_csv)
#     with open("schedule_interactive_output.csv", "w") as f:
#         f.write(schedule_csv)