from typing import Dict, Final, List
from streamlit.runtime.uploaded_file_manager import UploadedFile
import streamlit as st
import os
import duckdb
import pandas as pd
from modules import CSVDataExtractor, ExcelDataExtractor, File, RegFile


FILE_DATA_ALIAS_PREFIX: Final[str] = "table"


@st.dialog(title="Registered files", width="small")
def show_registered_files():
    for file in st.session_state.reg_files.values():
        with st.container(horizontal=True, horizontal_alignment="left"):
            with st.expander(file.fullname, expanded=True):
                st.markdown(f"  **Type:** {file.type}  \n"
                            f"  **Size:** {round(file.size / 1024 / 1024, 2)} MB  \n"
                            f"  **Registered Alias:** {file.tabname}  \n", width=300)
            if st.button("", 
                        type="secondary", 
                        icon=":material/delete:",
                        key=f"delete_{file.fullname}"):
                duckdb.unregister(file.tabname)
                del st.session_state.reg_files[file.fullname]
                st.rerun()
    "######"
    if st.button("Delete all", type="primary", icon=":material/delete:"):
        for file in list(st.session_state.reg_files.values()):
            duckdb.unregister(file.tabname)
            del st.session_state.reg_files[file.fullname]
        st.rerun()


def create_file_name(filename: str, sheetname: str) -> str:
    return f"{filename} - [{sheetname}]"


def extract_filetype(filename: str):
    return os.path.splitext(filename)[1][1::].lower()


def get_multiple_sheets_files() -> Dict[str, list]:
    excel_files = [file for file in st.session_state.files if extract_filetype(file.name) in ["xlsx", "xls"]]
    files_with_sheets = {}
    for file in excel_files:
        xls = pd.ExcelFile(file.data)
        if len(xls.sheet_names) > 1:
            files_with_sheets[file.name] = xls.sheet_names
            files_with_sheets[file.name].sort()
    return files_with_sheets


def register_file(file, sheetname: str = None, tabname: str = None):

    if tabname:
        if tabname.startswith("table"):
            raise ValueError("Alias name 'table' is reserved and cannot be used.")
        reg_alias = tabname
    else:
        reg_alias = f"{FILE_DATA_ALIAS_PREFIX}{len(st.session_state.reg_files) + 1}"

    new_file = RegFile(
        file.name if not sheetname else create_file_name(file.name, sheetname),
        file.name,
        sheetname if sheetname else "",
        file.type,
        file.size,
        file.data,
        reg_alias,
    )

    if new_file.name in st.session_state.reg_files.keys():
        return

    extractor = None
    if new_file.type in ["xlsx", "xls"]:
        extractor = ExcelDataExtractor(new_file.data, sheetname)
    elif new_file.type == "csv":
        extractor = CSVDataExtractor(new_file.data)

    if not extractor:
        raise ValueError(f"Unsupported file type: {new_file.type}")

    dataframe = extractor.create_dataframe()
    duckdb.register(new_file.tabname, dataframe)

    st.session_state.reg_files[new_file.fullname] = new_file


def unregister_file(file: RegFile):
    del st.session_state.reg_files[file.fullname]
    duckdb.unregister(file.tabname)


@st.dialog(title="Error")
def error(message: str):
    st.error(message)


@st.dialog(title="Query used")
def show_query():
    st.code(st.session_state.query_used, language="sql")


@st.dialog(title="Select sheets for registration")
def register_sheets(file_sheets: dict):
    for filename in file_sheets.keys():
        st.subheader(filename)
        for sheetname in file_sheets[filename]:
            st.checkbox(
                sheetname,
                key=f"selsheet_{filename}_{sheetname}",
                disabled=(
                    True if create_file_name(filename, sheetname) in st.session_state.reg_files else False
                ),
            )
    "######"
    if st.button("Confirm sheets", type="primary", icon=":material/check:"):
        sheets_selected = [key for key in st.session_state.keys() if key.startswith("selsheet_") and st.session_state[key]]
        sheets_selected.sort()
        for selection in sheets_selected:
            parts = selection.split("_")
            file_name = parts[1]
            sheet_name = parts[2]
            for file in st.session_state.files:
                if file.name == file_name:
                    register_file(file, sheetname=sheet_name)
        st.rerun()


def get_uploaded_files() -> List[File]:
    files = []
    for file in st.session_state.file_uploader:
        files.append(File(
            file.name,
            extract_filetype(file.name),
            file.size,
            file.read(),
        ))
    return files


def filter_multi_sheets(multi_sheets_files: dict) -> dict:
    filtered = {}
    for filename in multi_sheets_files.keys():
        sheets = []
        for sheetname in multi_sheets_files[filename]:
            if not create_file_name(filename, sheetname) in st.session_state.reg_files:
                sheets.append(sheetname)
        if sheets:
            filtered[filename] = sheets
    return filtered


def change_reg_alias(file: RegFile, new_alias: str):
    if new_alias.startswith("table"):
        raise ValueError("Alias name 'table' is reserved and cannot be used.")
    unregister_file(file)
    file.tabname = new_alias
    new_file = File(
        file.name,
        file.type,
        file.size,
        file.data,
    )
    register_file(new_file, tabname=new_alias, sheetname=file.sheetname)


def clear_query_result():
    st.session_state.query_result = ""
    st.session_state.query_used = None


st.set_page_config(
    page_title="Queryfy",
    page_icon=":streamlit:",
)


if "reg_files" not in st.session_state:
    st.session_state.reg_files = {}


with st.sidebar:
    files = st.file_uploader("File upload", 
                     accept_multiple_files=True,
                     key="file_uploader",
                     type=["xlsx", "xls", "csv"])
    with st.container(horizontal=True, horizontal_alignment="left"):
        if st.button("Register file", 
                    type="primary",
                    disabled=True if not files else False,
                    icon=":material/database:"):
            try:
                clear_query_result()
                st.session_state.files = get_uploaded_files()
                multi_sheets_files = get_multiple_sheets_files()

                # register simple files first
                for file in st.session_state.files:
                    if file.name not in multi_sheets_files.keys():
                        register_file(file)

                # register multiple sheets files (Excel)
                if multi_sheets_files:
                    multi_sheets_files = filter_multi_sheets(multi_sheets_files)
                    if multi_sheets_files:
                        register_sheets(multi_sheets_files)

            except Exception as ex:
                error(f"{ex}")

        if st.button("Show registered files", 
                    type="secondary",
                    icon=":material/list:",
                    disabled=True if "reg_files" not in st.session_state or not st.session_state.reg_files else False):
            show_registered_files()
    "###"
    text = st.text_area("Query input", 
                 height=250, 
                 key="query", 
                 help=f"""
        1. This programme supports structured data files only
        1. Use value from "Referenced Alias" as table name in your SQL queries.  
           Example query: `SELECT * FROM <table1> WHERE column = value`
        1. If column names contain spaces or special characters, use double quotes.  
           Example query: `SELECT * FROM <table1> WHERE "Column Name" = 'value'`
        1. For more information on SQL syntax, visit the [DuckDB Documentation](https://duckdb.org/docs/sql/introduction).
                 """)
    with st.container(horizontal=True, horizontal_alignment="left"):
        if st.button("Run query", 
                    type="primary",
                    icon=":material/play_arrow:"):
            if not st.session_state.query:
                error("Please enter a SQL query.")
            else:
                try:
                    st.session_state.query_result = duckdb.query(st.session_state.query).to_df()
                    st.session_state.query_used = st.session_state.query
                except Exception as ex:
                    error(f"An error occurred while executing the query: {ex}")


if "reg_files" in st.session_state and st.session_state.reg_files:
    st.subheader("Data preview", anchor=False)
    col1, col2, col3 = st.columns([3,1,1])
    with col1:
        options = list(st.session_state.reg_files.keys())
        options.sort()
        file_preview = st.selectbox(
            "File",
            options=options,
        )
    if file_preview:
        file_object: File = st.session_state.reg_files[file_preview]
    else:
        file_object = None
    with col2:
        if reg_alias := st.text_input(
            "Registered alias",
            value=file_object.tabname if file_object else "",
            disabled=True if not file_object else False,
        ):
            if reg_alias != file_object.tabname:
                try:
                    change_reg_alias(file_object, reg_alias)
                except Exception as ex:
                    error(ex)
    with col3:
        st.number_input(
            "Rows", 
            key="preview_row_cnt",
            min_value=0, 
            max_value=100, 
            value=5, 
            step=5, 
            disabled=True if not file_object else False
        )
    if file_object:
        try:
            preview_df = duckdb.query(f"SELECT * FROM {file_object.tabname} LIMIT {st.session_state.preview_row_cnt}").to_df()
            st.dataframe(preview_df, hide_index=True)
        except Exception as ex:
            st.error(ex)

    if "query_result" in st.session_state and st.session_state.query_used:
        st.subheader("Query result", anchor=False)
        st.dataframe(st.session_state.query_result, hide_index=True)
        if st.button("Show used query", type="secondary"):
            show_query()
