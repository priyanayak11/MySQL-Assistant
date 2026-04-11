import os
import streamlit as st
from sqlalchemy import create_engine
from langchain_google_genai import ChatGoogleGenerativeAI
import google.genai as genai
from langchain_community.utilities import SQLDatabase
from langchain_experimental.sql import SQLDatabaseChain
from langchain_core.prompts import PromptTemplate
from dotenv import load_dotenv
from urllib.parse import quote_plus
from sqlalchemy import text


# Database Configuration
db_user = st.secrets["username"]
db_pass = st.secrets["password"]
db_host = st.secrets["host"]
db_name = st.secrets["database"]
safe_password = quote_plus(db_pass)
engine = create_engine(f"mysql+pymysql://{db_user}:{safe_password}@{db_host}/{db_name}")
db = SQLDatabase(engine,include_tables=["sales_tb"])


# Prompt
template = """
You are a highly skilled data analyst working with a MySQL database.

Given the following database schema:{table_info}

Write a correct MySQL query for the user's question.

Rules:
- Generate a syntactically correct MySQL query
- Use only the tables and columns provided
- Do not assume columns that do not exist
- Use proper Raw MySQL syntax. 
- Strictly return ONLY SQL. No markdown, no explanation, no comments.
- Limit results to {top_k} rows unless specified
- Return ONLY the SQL query. Do not include explanations.

Question:{input}
"""
prompt = PromptTemplate(input_variables=["table_info", "input", "top_k"], template=template)


# Setup LLM 
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash-lite",  
    temperature=0,
    google_api_key=st.secrets["GOOGLE_API_KEY"],
    max_retries=2
)
chain = SQLDatabaseChain.from_llm(llm,db,verbose=True, return_sql=True,return_direct=True )



# Streamlit Interface
st.title("📊 MySQL Query Assistant")
st.caption("Ask questions about your database in natural language")

user_input = st.text_input("Enter your question:")
if st.button("Run Query"):
    with st.spinner("Generating query..."):
        response = llm.invoke(prompt.format(table_info=db.get_table_info(), input=user_input, top_k=5))
        sql_query = response.content
        sql_query = sql_query.replace("```sql", "").replace("```", "").strip()
        st.subheader("Generated SQL Query")
        st.code(sql_query, language="sql")

        try:      
            with engine.connect() as conn:
                result = conn.execute(text(sql_query))
                data = result.fetchall()

                if data:
                    st.subheader("Query Result")
                    st.dataframe(data)
                else:
                    st.warning("No results found for this query.")

        except Exception as e:
            st.error(f"Database Error: {e}")

