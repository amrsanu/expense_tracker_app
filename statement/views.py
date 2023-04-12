"""View for Statement"""

import os
import re

import pandas as pd
from django.shortcuts import render
from django.conf import settings
import plotly.graph_objs as go
import plotly.offline as opy

from .forms import UploadFileForm

# Create your views here.

BANKS = [
    "HDFC",
    "ICICI",
]


def handle_uploaded_file(f):
    """To save the uploaded file"""
    with open(os.path.join(settings.BASE_DIR, "uploads", f.name), "wb") as destination:
        for chunk in f.chunks():
            destination.write(chunk)


def upload_file(request):
    """Upload file helper"""
    if request.method == "POST":
        # Handle form submission here
        bank = request.POST.get("bank")
        statement_file = request.FILES.get("statement")
        handle_uploaded_file(statement_file)
        print(f"---- {bank} ---------------------------")

        # Do something with the bank and statement_file data, such as saving to a database or processing the file
        return render(
            request, "statement/upload_success.html"
        )  # Render a success page after processing the form
    else:
        context = {
            "bank_option": "Select Bank",
            "banks": BANKS,
        }
        return render(request, "statement/upload_file.html", context)


def generate_app_password(request):
    """Help page: /"""
    return render(
        request=request,
        template_name="statement/generate_app_password.html",
    )


def format_statement():
    """Use the statement to return pandas DF"""

    bank_statement_path = os.path.join(
        settings.BASE_DIR, "uploads", "50100356198949_1680754548417.txt"
    )

    statement_df = pd.read_csv(bank_statement_path, header=0)
    statement_df = statement_df.applymap(
        lambda x: x.strip() if isinstance(x, str) else x
    )
    statement_df = statement_df.rename(
        columns={col: col.strip() for col in statement_df.columns}
    )
    statement_df["Date"] = pd.to_datetime(statement_df["Date"], format="%d/%m/%y")
    # statement_df.set_index("Date", inplace=True)
    statement_df = statement_df.reset_index(drop=True)
    return statement_df


def get_debit_statement(statement_df):
    """Get debit from main statement"""
    debit_df = statement_df[statement_df["Debit Amount"] != 0.0]
    debit_df = debit_df.drop(columns="Credit Amount", axis=1)
    return debit_df


def get_credit_statement(statement_df):
    """Get credit from main statement"""
    credit_df = statement_df[statement_df["Credit Amount"] != 0.0]
    credit_df = credit_df.drop(columns="Debit Amount", axis=1)
    return credit_df


def add_category(df):
    """Add Ecpense category"""
    category = [re.split(r" |-|/", narration)[0] for narration in df["Narration"]]
    # df["Mode"] = category
    df.loc[:, "Mode"] = category

    category_list = []
    for narration in df["Narration"]:
        category = narration.split()
        if "-" in category[0]:
            _category = category[0].split("-")
            category_list.append(f"{_category[0]}-{_category[1][:15]}")

        else:
            category_list.append(category[0])

    # df["Category Inner"] = category_list
    df.loc[:, "Category Inner"] = category_list

    return df


def bank_statement(request):
    """Help page: /"""
    statement_table = format_statement()
    statement_table.loc[:] = add_category(statement_table)
    dates = statement_table["Date"]
    # expense_type = list(statement_table.columns)
    # expense_type.append("Credit")
    # expense_type.append("Debit")

    expense_type = set(statement_table["Category Inner"])

    start_date_option = request.GET.get("start_date")
    end_date_option = request.GET.get("end_date")
    expense_type_option = request.GET.get("category")

    mask = pd.Series(
        True, index=statement_table.index
    )  # initialize with all rows selected
    if expense_type_option:
        mask = mask & (statement_table["Category Inner"] == expense_type_option)
    if start_date_option:
        mask = mask & (statement_table["Date"] >= start_date_option)
    if end_date_option:
        mask = mask & (statement_table["Date"] <= end_date_option)

    statement_table_html = (
        statement_table[mask].drop(["Category Inner"], axis=1).to_html()
    )

    return render(
        request=request,
        template_name="statement/bank_statement.html",
        context={
            "statement_table": statement_table_html,
            "min_date": str(dates[0]).split()[0],
            "max_date": str(dates[len(dates) - 1]).split()[0],
            "expense_type_option": expense_type_option,
            "expense_type": expense_type,
        },
    )


def generate_bargraph(credit_by_month, debit_by_month):
    """Returns a graph object"""
    # create a side by side bar plot
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=list(credit_by_month.keys()),
            y=list(credit_by_month.values()),
            # name="Credit",
            marker=dict(color="#53F253"),
            name="Credit",
        )
    )
    fig.add_trace(
        go.Bar(
            x=list(debit_by_month.keys()),
            y=list(debit_by_month.values()),
            # name="Debit",
            marker=dict(color="#EB6632"),
            name="Credit",
        )
    )

    # set the x-axis and y-axis labels
    fig.update_xaxes(title_text="Month")
    fig.update_yaxes(title_text="Amount")

    # set the title of the plot
    # fig.update_layout(title="Monthly Credit and Debit Expenses")

    # add a legend
    fig.update_layout(
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    # display the plot
    return fig


def statement_as_bar(statement_df):
    """To view the Graphs and Bargraphs"""

    # generate the plot
    statement_df.set_index("Date", inplace=True)

    debit_df = statement_df[statement_df["Debit Amount"] != 0.0]
    debit_df = debit_df.drop(columns="Credit Amount", axis=1)
    credit_df = statement_df[statement_df["Credit Amount"] != 0.0]
    credit_df = credit_df.drop(columns="Debit Amount", axis=1)

    aggregare_debit = {}
    months = []
    monthly_debit = debit_df.resample("M")
    for name, data in monthly_debit:
        months.append(f"{name.month} {name.year}")
        aggregare_debit[name] = data["Debit Amount"].sum()

    monthly_credit = credit_df.resample("M")
    aggregare_credit = {}
    for name, data in monthly_credit:
        aggregare_credit[name] = data["Credit Amount"].sum()

    fig = generate_bargraph(aggregare_credit, aggregare_debit)
    # plot_html = fig.to_html(full_html=False, include_plotlyjs=False)
    plot_html = opy.plot(fig, auto_open=False, output_type="div")
    # pass the HTML to the template
    return {"plot_html": plot_html}, months


def debit_pie(last_month_debit):
    """To returnt he debit pie chart for a month"""
    last_month_debit_group = last_month_debit.groupby("Category Inner")
    debit_category_dict = {}
    for name, category in last_month_debit_group:
        debit_category_dict[name] = category["Debit Amount"].sum()

    labels = list([f"{key}: Rs.{value}" for key, value in debit_category_dict.items()])
    values = list(debit_category_dict.values())

    # Create the pie chart
    fig = go.Figure(data=[go.Pie(labels=labels, values=values)])

    # Update the chart layout
    fig.update_layout(title="Debit Distribution")
    fig.update_layout(
        width=700,  # specify width in pixels
        height=700,  # specify height in pixels
    )
    plot_html = opy.plot(fig, auto_open=False, output_type="div")
    # Display the chart
    return plot_html


def credit_pie(last_month_credit):
    """To returnt he credit pie chart for a month"""
    last_month_credit_group = last_month_credit.groupby("Category Inner")
    credit_category_dict = {}
    for name, category in last_month_credit_group:
        credit_category_dict[name] = category["Credit Amount"].sum()

    labels = list([f"{key}: Rs.{value}" for key, value in credit_category_dict.items()])
    values = list(credit_category_dict.values())

    # Create the pie chart
    fig = go.Figure(data=[go.Pie(labels=labels, values=values)])

    # Update the chart layout
    fig.update_layout(title="Credit Distribution")
    fig.update_layout(
        width=700,  # specify width in pixels
        height=700,  # specify height in pixels
    )
    plot_html = opy.plot(fig, auto_open=False, output_type="div")
    # Display the chart
    return plot_html


def statement_as_pichart(statement_df, month):
    """Handler for Months statement PieChart"""
    category = [
        re.split(r" |-|/", narration)[0] for narration in statement_df["Narration"]
    ]

    # df["Mode"] = category
    statement_df.loc[:, "Mode"] = category

    category_list = []
    for narration in statement_df["Narration"]:
        category = narration.split()
        if "-" in category[0]:
            _category = category[0].split("-")
            category_list.append(f"{_category[0]}-{_category[1][:15]}")
        else:
            category_list.append(category[0])

    statement_df.loc[:, "Category Inner"] = category_list

    debit_df = statement_df[statement_df["Debit Amount"] != 0.0]
    debit_df = debit_df.drop(columns="Credit Amount", axis=1)
    credit_df = statement_df[statement_df["Credit Amount"] != 0.0]
    credit_df = credit_df.drop(columns="Debit Amount", axis=1)

    last_month_debit = None
    monthly_debit = debit_df.resample("M")
    for name, data in monthly_debit:
        if month == f"{name.month} {name.year}":
            last_month_debit = data.copy()
            break
    last_month_debit.loc[:] = add_category(last_month_debit)

    last_month_credit = None
    monthly_credit = credit_df.resample("M")
    for name, data in monthly_credit:
        if month == f"{name.month} {name.year}":
            last_month_credit = data.copy()
            break
    last_month_credit.loc[:] = add_category(last_month_credit)

    context = {}
    context["credit_pie"] = credit_pie(last_month_credit)
    context["debit_pie"] = debit_pie(last_month_debit)

    return context


def starting_page(request):
    """Starting page: /"""
    statement_df = format_statement()
    context, months = statement_as_bar(statement_df)
    month_option = request.GET.get("month")
    if month_option is None:
        month_option = months[-1]
    context["months"] = months
    context["month_option"] = month_option
    pie_context = statement_as_pichart(statement_df, month_option)
    context.update(pie_context)

    return render(
        request=request,
        template_name="statement/starting_page.html",
        context=context,
    )
