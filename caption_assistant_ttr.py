import streamlit as st
import random
from langchain.chains import LLMChain, ConversationChain
from langchain.prompts import PromptTemplate
from langchain.memory import ConversationBufferMemory
from langchain.memory.chat_message_histories import StreamlitChatMessageHistory
from langchain.llms import OpenAI
from langchain.chat_models import ChatOpenAI
import mysql.connector
from mysql.connector import Error
import pandas as pd
from pandas import DataFrame, read_csv, read_sql_query

st.set_page_config(layout="wide")
if 'caption' not in st.session_state:
    st.session_state.caption = []
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

#Set some variable for use below
prompt_strategies = [
   'use more specific language',
   'make reference to all important elements of the image',
   'use langauge with more than one interpretation',
   'avoid making the joke too obvious',
   'put the punchline at the end',
   'introduce a tension that is resolved by the joke',
   'imagine it comes from the script of a Seinfeld episode',
   'make reference to unusual elemts of the image',
   'think of what the characters in the image are doing and why'
   'think of how the image differs from a more common situation and why'
   'think of the emotions the characters are feeling and why'
   ]

#Number of strategies
n_strat = len(prompt_strategies)

#Queries sent so far
n_query = 0

#Initialize strings for prompt arguments
current_description = 'None provided.'
current_strategy = 'think harder.'
recent_captions = 'None.'





col1, col2 = st.columns(2)
with col1:
    #Box to enter and submit API key
    apiform = st.form("api_form")
    GPT_API = apiform.text_input('Your GPT API key:', key="API", type="password")
    apiform.form_submit_button("Submit")
    
    #Drop-down box to select which model:
    model_selection = st.selectbox('Choose an AI', ('gpt-3.5-turbo', 'gpt-4'))
    
    #Drop-down box to choose app function:
    option_function = st.selectbox('Choose a function', ('Inspiration', 'Get Help from GPT', 'Funniness prediction','topic model graph'))

with col2:
    if option_function =='Inspiration' and st.button(':red[Give me some inspiration]'):
        random_img = random.randint(509, 853)
        random_integers = [random.randint(0, 19) for _ in range(3)]
        inspiration_URL = select("""SELECT image_url FROM base""")
        inspiration_caption = select(f"""SELECT caption FROM result WHERE contest_num={random_img}""")
        st.image(inspiration_URL.iloc[random_img-1, 0])
        st.write(inspiration_caption.iloc[random_integers[0],0])
        st.write(inspiration_caption.iloc[random_integers[1],0])
        st.write(inspiration_caption.iloc[random_integers[2],0])

    if option_function =='Get Help from GPT':
        if not st.session_state.API:
            st.title(':red[You need to enter the API!]')
        else:
            template = """You are an AI chatbot having a conversation with a human.

            {history}
            Human: {human_input}
            AI: """
            prompt = PromptTemplate(input_variables=["history", "human_input"], template=template)
            msgs = StreamlitChatMessageHistory(key="langchain_messages")
            memory = ConversationBufferMemory(chat_memory=msgs)
            
            #Template for initial prompt:
            template_initial = '''
            You are assisting someone trying to think of funny captions for a New Yorker cartoon. Here is a description of the cartoon image:
            
            {description}

            So far the user has come up with the following captions:
            
            {captions}
            
            Your job is to help the user come up with better captions.
            
            One way of making a caption funnier is to {strategy}.
            
            With this in mind, please talk directly to the user to suggest ways the user can adapt their ideas to create a funnier caption. 
            Respond in no more than three sentences, and avoid repeating any previous advice.
            '''
            #Template for subsequent prompts:
            template_more = """
            {history}
            
            From your prior advice, the user added the following captions:
            
            {captions}
            
            Now the user would like some more advice.
            
            Another way of making a caption funnier is to {strategy}
            
            With this in mind, please talk directly to the user to suggest new ways the user can adapt their ideas to create a funnier caption. 
            Respond in no more than three sentences, and avoid repeating any previous advice.
            """
            
            #Prompt for initial request for advice:
            prompt_initial = PromptTemplate(input_variables=['description', 'captions', 'strategy'], template=template_initial)

            #Prompt for subsequent requests
            prompt_next = PromptTemplate(input_variables = ['history', 'captions', 'strategy'], template = template_more)
            #Define the model:
            llm_chain = LLMChain(llm=ChatOpenAI(openai_api_key=st.session_state.API, model=model_selection), prompt=prompt, memory=memory)

            with st.form(key='description_form'):
                description_location = st.text_area('Please describe the content of the cartoon in as much detail as possible:', height = 2)
                submit_button_description = st.form_submit_button(label='Record the description of the cartoon')
            
            with st.form(key='caption_form'):
                caption_1 = st.text_input('Write a caption:')
                submit_button_caption = st.form_submit_button(label='Record the caption')
                
            if submit_button_caption:
                st.session_state.caption.append(caption_1)
                
            if submit_button_description:
                current_description = description_location
                
            if st.button('Ask for assistance', key = 'help_button'):
                if n_query==0: #If it is the very first request
                    current_strategy = random.choice(prompt_strategies) #Pick a strategy at random
                    current_captions = st.session_state.caption
                    #Construct the prompt using initial template:
                    prompt = prompt_initial.format(description = current_description,\
                        captions = current_captions, strategy=current_strategy)
                    
                    n_query = n_query + 1 #Increment query count
                    st.session_state.caption = [] #Clear list of recent captions
                #If it is not the first request:
                else:
                    #Set history for prompt:
                    current_history=StreamlitChatMessageHistory(key="langchain_messages")
                    current_strategy = random.choice(strategies) #Pick one at random
                    #Construct new prompt using next template:
                    prompt = prompt_next.format(history = current_history,\
                        captions = st.session_state.caption, strategy=current_strategy)
                #Submit prompt to model and record response:
                response = llm_chain.run(prompt)
                #Display response in box
                st.chat_message("ai").write(response)
                
            if st.button('Reset chat'):
                del st.session_state.langchain_messages
                msgs = StreamlitChatMessageHistory(key="langchain_messages")



    if option_function =='Funniness prediction':
        st.title('Wait for further development!')

    if option_function =='topic model graph':
        st.title('Wait for further development!')

if option_function =='Get Help from GPT':
  with col1:
    with st.expander("View your submitted captions:"):
      if st.button("clear caption history"):
        st.session_state.caption = []
      st.write(st.session_state.caption)
  with col2:
    with st.expander("View suggestion history:"):
      count = int(len(msgs.messages)/2)
      for i in range(count):
          st.chat_message(msgs.messages[i*2-1].type).write(msgs.messages[i*2-1].content)
