
import streamlit as st
import random
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain.memory import ConversationBufferMemory
from langchain.memory.chat_message_histories import StreamlitChatMessageHistory
from langchain import OpenAI, ConversationChain
import mysql.connector
from mysql.connector import Error
import pandas as pd
from pandas import DataFrame, read_csv,read_sql_query

st.set_page_config(layout="wide")
def create_connection():
    try:
        connection = mysql.connector.connect(host='dbnewyorkcartoon.cgyqzvdc98df.us-east-2.rds.amazonaws.com',
                                             database='new_york_cartoon',
                                             user='dbuser',
                                             password='Sql123456')
        if connection.is_connected():
            db_Info = connection.get_server_info()
            print("Connected to MySQL Server version ", db_Info)
            return connection
    except Error as e:
        print("Error while connecting to MySQL", e)
        return None

def select(q):
    connection = create_connection()
    if connection:
        try:
            df = read_sql_query(q, connection)
            return df
        except Error as e:
            print("Error executing the query:", e)
        finally:
            connection.close()
    return None

col1, col2 = st.columns(2)
with col1:
    form = st.form("my_form")
    GPT_API = form.text_input('Your GPT API:', key="API")
    form.form_submit_button("Submit")
    option_function = st.selectbox('Choose a function', ('Inspiration', 'Get Help from GPT', 'Funniness prediction','topic model graph'))
with col2:
    if option_function =='Inspiration' and st.button(':red[Give me some inspiration]'):
        random_img = random.randint(509, 853)
        random_integers = [random.randint(0, 19) for _ in range(3)]
        inspiration_URL = select("""SELECT image_url FROM base""")
        inspiration_caption = select(f"""SELECT caption FROM result WHERE contest_num={random_img}""")
        st.image(inspiration_URL.iloc[random_img+1, 0])
        st.write(inspiration_caption.iloc[random_integers[0],0])
        st.write(inspiration_caption.iloc[random_integers[1],0])
        st.write(inspiration_caption.iloc[random_integers[2],0])

    if option_function =='Get Help from GPT':
        if not st.session_state.API:
            st.title(':red[You need to enter the API!]')
        else:
            msgs = StreamlitChatMessageHistory(key="langchain_messages")
            memory = ConversationBufferMemory(chat_memory=msgs)
            template = """You are an AI chatbot having a conversation with a human.

            {history}
            Human: {human_input}
            AI: """
            prompt = PromptTemplate(input_variables=["history", "human_input"], template=template)
            prompt_remember = PromptTemplate(
                input_variables=["location", "character","action","uncanny"], 
                template="You are assisting someone trying to think of funny captions for a New York cartoon. Please remember this scene as the description of a cartoon: \nlocation: {location}, characters: {character}, actions: {action}. uncanny content: {uncanny}")
            prompt_suggestion = PromptTemplate(
                input_variables=["suggestion"], 
                template="The user wants some more advice. One way of making a cartoon funnier is to {suggestion} With that in mind, please talk directly to the user to suggest ways the user can adapt their ideas to create a funnier caption. Respond in no more than three sentences.")
            llm_chain = LLMChain(llm=OpenAI(openai_api_key=st.session_state.API), prompt=prompt, memory=memory)
            
            with st.form(key='my_form2'):
                description_location = st.text_input('Where is the location in the cartoon (nouns only, use comma to seperate):')
                description_character = st.text_input('What are the characters in the cartoon (nouns only, use "and" to connect multiple characters):')
                description_action = st.text_input('What are the characters doing in the cartoon (describe actions with related charaters in detail):')
                description_uncanny = st.text_area('What is the uncanny part of the cartoon:',height = 2)
                caption_1 = st.text_input('Write your caption:')
                submit_button = st.form_submit_button(label='Submit the description of the cartoon')
                
            with st.form(key="my_form3"):
                option_help = st.selectbox('Choose a kind of help to ask GPT', ('use more specific language', 'make reference to all important elements of the image', 'use langauge with more than one interpretation','avoid making the joke too obvious'))
                help_button = st.form_submit_button(label='Get help')
            for msg in msgs.messages:
                st.chat_message(msg.type).write(msg.content)            
            if submit_button:
                prompt = prompt_remember.format(location=description_location,character=description_character,action=description_uncanny,uncanny=description_uncanny)
                st.chat_message("human").write(prompt)
                response = llm_chain.run(prompt)
                st.chat_message("ai").write(response)
            if help_button:
                prompt = prompt_suggestion.format(suggestion=option_help)
                st.chat_message("human").write(prompt)
                response = llm_chain.run(prompt)
                st.chat_message("ai").write(response)
    
    if option_function =='Funniness prediction':
        st.title('Wait for further development!')
    
    if option_function =='topic model graph':
        st.title('Wait for further development!')