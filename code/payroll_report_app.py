"""
payroll_report_app.py — the quarter at a glance, for someone who never opens a terminal.

Every Friday since September the office manager at Salt City Coffee has downloaded
a payroll export from the Assignment 04 app; before that she typed the same file
by hand. The owner now wants to know where the hours went this quarter, the
accountant wants pay by month and department, and the manager wants to see who
has been missing shifts. This page answers all three from the pile of exports.

Same shape as Assignment 04: the page *assembles* the pipeline — one call to
`build_history` does the cleaning — and then shows the reports, filtered by the
department and dates the user picks.

Run it:  Run and Debug -> "Streamlit Run: Current File"
Test it: pytest tests/test_pipeline.py -k app
"""
# --- The page ---------------------------------------------------------------------
#
# No scaffolding. Every function this page needs already exists in the payroll
# package, and every widget it needs you used in Assignments 03 and 04 — plus two
# new ones, st.date_input and st.bar_chart. README Step 8 has the exact widgets,
# keys and labels; the tests in tests/test_pipeline.py -k app check them.
#
# The shape, in words:
#
#   title and a sentence of instructions
#   roster   <- load_employees()                           (fixed; not uploaded)
#   uploads  <- st.file_uploader, key="exports", accept_multiple_files=True
#               (an empty list until files are chosen)
#   if there are uploads:
#       history <- build_history([load_export(u) for u in uploads], roster)
#       st.warning naming any employeeid with no department (not on the roster);
#           the reports below use only the rows that matched
#       st.selectbox, key="department": "All" plus each department
#       st.date_input, key="dates": a (start, end) range, defaulting to the first
#           and last pay_date — compare against pay_date.dt.date to filter
#       the selection as a subheader
#       four st.metric cards in st.columns(4): Weeks, Employees, Total hours,
#           Total gross pay — counts are .nunique(), totals are .sum()
#       st.bar_chart of pay_by_month(selected), with month as the x axis
#       st.dataframe of summarize_employees(selected)
#       st.dataframe of hours_grid(selected), then of missed_weeks(that grid)
#       st.download_button, key="download": pay_by_month(...).to_csv(index=False)
#
# What the page does NOT do: cleaning, grouping, pivoting. If you find yourself
# writing a groupby or a pivot_table here, that logic belongs in the package.

import streamlit as st
import pandas as pd
from datetime import datetime

from payroll.summarize import build_history, summarize_employees
from payroll.reshape import pay_by_month, hours_grid, missed_weeks
from payroll.extract import load_employees, load_export

roster = load_employees()
departments = list(roster["department"].unique())

st.title("Salt City Coffee — Quarterly Payroll Report")
st.write("Upload the **weekly payroll exports** for the period you want to review — old spreadsheet weeks and new app weeks can be mixed. The roster is loaded automatically.")

uploads = st.file_uploader(key="exports", accept_multiple_files=True, label="Upload weekly payroll exports (CSV)")

if uploads:
    exports = [load_export(u) for u in uploads]
    
    history = build_history(exports, roster)
    unmatched = history[history["department"].isna()]
    if len(unmatched) > 0:
        ids = ", ".join(unmatched["employeeid"].unique())
        st.warning(f"The following employees are not on the roster: {ids}")
    history = history[history["department"].notna()]

    sel_departments = st.selectbox(key="department", label="Department", options=["All"] + departments)

    pay_dates = history["pay_date"].dt.date
    min_date = min(pay_dates)
    max_date = max(pay_dates)
    start, end = st.date_input(label="Pay dates", min_value=min_date, max_value=max_date, value=(min_date,max_date))

    st.subheader(f"{sel_departments} · {start} to {end}")

    # Build filtered DataFrame
    
    filtered = history.copy()
    filtered = filtered[filtered["week_ending"].between(start.isoformat(), end.isoformat())]
    if sel_departments != "All":
        filtered = filtered[filtered["department"] == sel_departments]

    weeks, employees, total_hours, total_gross_pay = st.columns(4)
    with weeks:
        st.metric("Weeks", value=len(filtered["week_ending"].unique()))
    with employees:
        st.metric("Employees", value=len(filtered["employee_id"].unique()))
    
    with total_hours:
        st.metric("Total hours", f"{filtered["hours_worked"].sum():,.2f}")
    with total_gross_pay:
        st.metric("Total gross pay", f"${filtered["gross_pay"].sum().round(2):,.2f}")

    st.subheader("Gross pay by month")
    st.bar_chart(pay_by_month(filtered), x="month")

    st.subheader("Employees")
    st.dataframe(summarize_employees(filtered), hide_index=True)

    st.subheader("Hours by week")
    grid = hours_grid(filtered)
    st.dataframe(grid, hide_index=True)

    st.subheader("Missed weeks")
    st.dataframe(missed_weeks(grid), hide_index=True)

    st.download_button(label="Download pay by month for the accountant (CSV)",
                       key="download",
                       data=pay_by_month(filtered).to_csv(index=False),
                       file_name="pay_by_month.csv")