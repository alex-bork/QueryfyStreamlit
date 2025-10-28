from typing import Final
from streamlit.runtime.uploaded_file_manager import UploadedFile
import streamlit as st
import os
import duckdb
import pandas as pd
from modules import CSVDataExtractor, ExcelDataExtractor, File

@st.dialog(title="Registered Files", width="small")
def show_registered_files():
    for file in st.session_state.files.values():
        with st.container(horizontal=True, horizontal_alignment="left"):
            with st.expander(file.name, expanded=False):
                st.markdown(f"  **Type:** {file.type}  \n"
                            f"  **Size:** {file.size} bytes  \n"
                            f"  **Referenced Alias:** {file.tabname}  \n", width=300)
            if st.button("", 
                        type="secondary", 
                        icon=":material/delete:",
                        key=f"delete_{file.name}"):
                duckdb.unregister(file.tabname)
                del st.session_state.files[file.name]
                st.rerun()
    "######"
    if st.button("Delete all", type="primary", icon=":material/delete:"):
        for file in list(st.session_state.files.values()):
            duckdb.unregister(file.tabname)
            del st.session_state.files[file.name]
        st.rerun()


def load_file(file, tablename: str=None):
    if "files" not in st.session_state:
        st.session_state.files = {}

    new_file = File(
            file.name,
            os.path.splitext(file.name)[1][1::].lower(),
            file.size, 
            file.read(),
            tablename if tablename else f"table_{len(st.session_state.files) + 1}"
            )
    
    extractor = None
    if new_file.type == "xlsx" or new_file.type == "xls":
        extractor = ExcelDataExtractor(new_file.data)
    elif new_file.type == "csv":
        extractor = CSVDataExtractor(new_file.data)

    if not extractor:
        raise ValueError(f"Unsupported file type: {new_file.type}")
    
    dataframe = extractor.create_dataframe()
    duckdb.register(new_file.tabname, dataframe)

    st.session_state.files[new_file.name] = new_file

@st.dialog(title="Error")
def error(message: str):
    st.error(message)

st.set_page_config(
    page_title="File Uploader Example",
    page_icon="📁",
)

with st.sidebar:
    file = st.file_uploader("File upload", 
                     accept_multiple_files=False, 
                     type=["xlsx", "xls", "csv"])
    with st.container(horizontal=True, horizontal_alignment="left"):
        if st.button("Register file", 
                    type="primary",
                    icon=":material/database:"):
            try:
                load_file(file)
            except Exception as ex:
                error(f"An error occurred while registering the file: {ex}")
        if st.button("Show registered files", 
                    type="secondary",
                    icon=":material/list:",
                    disabled=True if "files" not in st.session_state else False):
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
                except Exception as e:
                    error(f"An error occurred while executing the query: {e}")

if "files" in st.session_state and st.session_state.files:
    st.subheader("Data preview", anchor=False)
    col1, col2 = st.columns([3,1])
    with col1:
        file_preview = st.selectbox(
            "Select file to preview", 
            options=list(st.session_state.files.keys()), 
            label_visibility="collapsed", 
        )
    with col2:
        st.number_input(
            "Max rows", 
            key="preview_row_cnt",
            min_value=0, 
            max_value=100, 
            value=5, 
            step=5, 
            label_visibility="collapsed", 
        )
    if file_preview:
        file_object: File = st.session_state.files[file_preview]
        preview_df = duckdb.query(f"SELECT * FROM {file_object.tabname} LIMIT {st.session_state.preview_row_cnt}").to_df()
        st.markdown(f"##### {file_object.tabname}")
        st.dataframe(preview_df, hide_index=True)

    st.subheader("Query result", anchor=False)
    if "query_result" in st.session_state:
        st.dataframe(st.session_state.query_result, hide_index=True)