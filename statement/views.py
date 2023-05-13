"""View for Statement"""

import os
import re
import io

import pandas as pd
from django.shortcuts import render
from django.shortcuts import redirect
from django.core.cache import cache
from django import forms

import plotly.graph_objs as go
import plotly.offline as opy

from statement.static.packages import statement_parser
from expense_tracker_app.settings import BASE_DIR

# Create your views here.

BANKS = [
    "HDFC",
    "ICICI",
]

STATEMENT_FILES = "bank_statements"
IMAGE_PATH = os.path.join(BASE_DIR, "staticfiles", "images")


class BooleanForm(forms.Form):
    """To have a Boolean switch in the form"""

    my_boolean_field = forms.BooleanField(label="detailed_view", required=False)


def ensure_dirs(directory):
    "To create the directory recursively if not found"
    if not os.path.exists(directory):
        os.makedirs(directory)


def verify_uploads(request):
    """To verify if user have already uploaded some files"""
    files = None
    statement_files_string = cache.get(STATEMENT_FILES)

    if statement_files_string is not None and len(statement_files_string.strip()) != 0:
        statement_file = statement_files_string.split(" ")
        files = [f for f in statement_file]

    return files


def upload_file(request):
    """Upload file helper"""
    context = {
        "bank_option": "Select Bank",
        "banks": BANKS,
    }

    if request.method == "POST" and "bank" in request.POST:
        # Handle form submission here
        bank = request.POST.get("bank")
        statement_file = request.FILES.get("statement")
        statement_file_name = statement_file.name

        if not statement_file_name.endswith((".txt", ".csv", ".CSV")):
            context["upload_error"] = True
        else:
            statement_file_df = statement_parser.parse_statement(bank, statement_file)
            if statement_file_df is None:
                context["upload_error"] = True
            else:
                # Convert statement_file_df to html and save to cache
                statement_files_string = cache.get(STATEMENT_FILES)

                if statement_files_string is not None:
                    statement_files_string = (
                        f"{statement_files_string} {statement_file_name}"
                    )
                else:
                    statement_files_string = statement_file_name

                cache.set(STATEMENT_FILES, statement_files_string)

                cache.set(
                    statement_file_name,
                    statement_file_df.to_csv(),
                )

    if request.method == "POST" and "file" in request.POST:
        # Handle file deletion here
        statement_files = cache.get(STATEMENT_FILES).split()

        statement_files_to_delete = request.POST.getlist("file")
        for statement_file_name in statement_files_to_delete:
            cache.delete(statement_file_name)
            statement_files.remove(statement_file_name)

        cache.set(STATEMENT_FILES, " ".join(statement_files))

    statement_files_string = cache.get(STATEMENT_FILES)
    if statement_files_string is not None:
        context["statement_files"] = statement_files_string.split()

    return render(request, "statement/upload_file.html", context)


def no_statement(request):
    """To return a page if no statement is found"""
    return render(request, "statement/no_statement.html")


def help_page(request):
    """Help page: /"""
    return render(
        request=request,
        template_name="statement/help_page.html",
    )


def generate_app_password(request):
    """Help page: /"""
    return render(
        request=request,
        template_name="statement/generate_app_password.html",
    )


def format_statement():
    """Use the statement to return pandas DF"""

    statement_file_string = cache.get(STATEMENT_FILES)
    bank_statement_path = statement_file_string.split()[0]

    statement_csv = cache.get(bank_statement_path)
    statement_df = pd.read_csv(
        io.StringIO(statement_csv),
        index_col=0,
    )
    statement_df["Date"] = pd.to_datetime(statement_df["Date"], format="%d-%m-%Y")

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

    files = verify_uploads(request)
    if files is None:
        return render(
            request=request,
            template_name="statement/bank_statement.html",
        )

    statement_table = format_statement()

    statement_table.loc[:] = add_category(statement_table)
    dates = statement_table["Date"]

    credit_or_debit_option = "All"
    credit_or_debit = [
        "All",
        "Credit",
        "Debit",
    ]

    expense_type = sorted(list(set(statement_table["Category Inner"])))
    expense_type.insert(0, "All")
    start_date_option = request.GET.get("start_date")
    end_date_option = request.GET.get("end_date")
    expense_type_option = request.GET.get("category")
    credit_or_debit_option = request.GET.get("credit_or_debit")

    if expense_type_option is None:
        expense_type_option = "All"
    if credit_or_debit_option is None:
        credit_or_debit_option = "All"

    mask = pd.Series(
        True, index=statement_table.index
    )  # initialize with all rows selected
    if expense_type_option != "All":
        mask = mask & (statement_table["Category Inner"] == expense_type_option)
    if start_date_option:
        mask = mask & (statement_table["Date"] >= start_date_option)
    if end_date_option:
        mask = mask & (statement_table["Date"] <= end_date_option)
    if credit_or_debit_option == "Debit":
        statement_table = statement_table.drop(["Credit Amount"], axis=1)
        mask = mask & (statement_table["Debit Amount"] > 0.0)
    if credit_or_debit_option == "Credit":
        statement_table = statement_table.drop(["Debit Amount"], axis=1)
        mask = mask & (statement_table["Credit Amount"] > 0.0)

    statement_table = statement_table[mask]
    statement_table = statement_table.drop(["Category Inner"], axis=1)

    statement_table_html = statement_table.to_html()

    return render(
        request=request,
        template_name="statement/bank_statement.html",
        context={
            "statement_table": statement_table_html,
            "min_date": str(dates[0]).split()[0],
            "max_date": str(dates[len(dates) - 1]).split()[0],
            "expense_type_option": expense_type_option,
            "credit_or_debit_option": credit_or_debit_option,
            "credit_or_debit": credit_or_debit,
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
            name="Debit",
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
        months.append(f"{name.strftime('%b')} {name.year}")
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


def debit_pie(last_month_debit, detailed_view):
    """To returnt he debit pie chart for a month"""
    if detailed_view:
        last_month_debit_group = last_month_debit.groupby("Category Inner")
    else:
        last_month_debit_group = last_month_debit.groupby("Mode")

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


def credit_pie(last_month_credit, detailed_view):
    """To returnt he credit pie chart for a month"""
    if detailed_view:
        last_month_credit_group = last_month_credit.groupby("Category Inner")
    else:
        last_month_credit_group = last_month_credit.groupby("Mode")

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


def statement_as_pichart(statement_df, month, detailed_view):
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
        if month == f"{name.strftime('%b')} {name.year}":
            last_month_debit = data.copy()
            break
    last_month_debit.loc[:] = add_category(last_month_debit)

    last_month_credit = None
    monthly_credit = credit_df.resample("M")
    for name, data in monthly_credit:
        if month == f"{name.strftime('%b')} {name.year}":
            last_month_credit = data.copy()
            break
    last_month_credit.loc[:] = add_category(last_month_credit)

    context = {}
    context["credit_pie"] = credit_pie(last_month_credit, detailed_view)
    context["debit_pie"] = debit_pie(last_month_debit, detailed_view)

    return context


def starting_page(request):
    """Starting page: /"""
    context = {}
    if request.method == "POST" and "bank" in request.POST:
        # Handle form submission here
        bank = request.POST.get("bank")
        statement_file = request.FILES.get("statement")
        statement_file_name = statement_file.name

        if not statement_file_name.endswith((".txt", ".csv", ".CSV")):
            context["upload_error"] = True
        else:
            statement_file_df = statement_parser.parse_statement(bank, statement_file)
            if statement_file_df is None:
                context["upload_error"] = True
            else:
                # Convert statement_file_df to html and save to cache
                statement_files_string = cache.get(STATEMENT_FILES)

                if statement_files_string is not None:
                    statement_files_string = (
                        f"{statement_files_string} {statement_file_name}"
                    )
                else:
                    statement_files_string = statement_file_name

                cache.set(STATEMENT_FILES, statement_files_string)

                cache.set(
                    statement_file_name,
                    statement_file_df.to_csv(),
                )

    files = verify_uploads(request)

    if files is None:
        images = []
        for image in os.listdir(IMAGE_PATH):
            images.append(
                {
                    "url": os.path.join("staticfiles", "images", image),
                    "name": image,
                }
            )
        context = {
            "bank_option": "Select Bank",
            "banks": BANKS,
            "images": images,
        }

        statement_files_string = cache.get(STATEMENT_FILES)
        if statement_files_string is not None:
            context["statement_files"] = statement_files_string.split()

        return render(
            request=request,
            template_name="statement/no_statement.html",
            context=context,
        )

    statement_df = format_statement()
    context, months = statement_as_bar(statement_df)
    month_option = request.GET.get("month")

    detailed_view = BooleanForm()
    context["detailed_view"] = False

    if request.method == "GET":
        detailed_view = bool(request.GET.get("detailed_view"))
        context["detailed_view"] = detailed_view

    if month_option is None:
        month_option = months[-1]
    context["months"] = months
    context["month_option"] = month_option
    context["detailed_view"] = detailed_view
    pie_context = statement_as_pichart(statement_df, month_option, detailed_view)
    context.update(pie_context)

    return render(
        request=request,
        template_name="statement/starting_page.html",
        context=context,
    )
