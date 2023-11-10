from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain.memory import ConversationBufferMemory
from langchain.memory.chat_message_histories import StreamlitChatMessageHistory
from langchain.chat_models import ChatOpenAI

from mysql.connector import Error
import mysql.connector

import pandas as pd
import streamlit as st
import random
from datetime import datetime
import time
import requests

st.set_page_config(layout="wide")

# CSS for some settings
centered_large_bold_css = """
<style>
.centered-text-large-bold {
    text-align: center;
    font-weight: bold;
    font-size: 20px; /* You can adjust the size as needed */
    margin-top: 3px; /* Add some top margin */
    margin-bottom: 5px; /* Add some bottom margin */
}
</style>
"""
bottom_button_css = """
<style>
div.stButton {
    margin-top: 13px;
}
</style>
"""

# cache for the database connection
# @st.cache_resource(hash_funcs={mysql.connector.connection.MySQLConnection: id})

# check if the API key is valid
def is_key_valid(api_key):
    return requests.post(
        'https://api.openai.com/v1/completions',
        headers={'Authorization': f'Bearer {api_key}'},
        json={'model': 'text-davinci-003', 'prompt': 'Hello, world!', 'max_tokens': 1}
    ).ok

# create a class for user authentication
class UserAuthentication:
    def __init__(self):
        pass

    # Function to check user login credentials
    def check_login(username):
        conn = DBConnection.create_connection()
        cursor = conn.cursor(buffered=True)
        cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
        row = cursor.fetchone()
        conn.close()
        if row:
            st.session_state['logged_in'] = True
            st.session_state['user_id'] = row[0]
            return True
        else:
            st.error("Incorrect username")
            return False

    # Function to logout the user
    def logout_user():
        st.session_state['logged_in'] = False
        st.session_state['user_id'] = None

    # Function to register a new user
    def register_user(username):
        # username cannot be empty or only contains spaces
        if username == '' or username.isspace():
            st.error("Username cannot be empty.")
            return False
        else:
            username = username.strip()   # remove spaces at the beginning and end of the username
            conn = DBConnection.create_connection()
            cursor = conn.cursor(buffered=True)
            try:
                cursor.execute("INSERT INTO users (username) VALUES (%s)", (username,))
                conn.commit()
                return True
            except:
                st.error("Error creating account. Username may already exists.")
                return False
            finally:
                cursor.close()
                conn.close()

    # Main function for Streamlit app
    def user_account():
        st.title("User Authentication Service")

        form = st.form(key='user_form')
        username = form.text_input("Username", max_chars=50)
        login = form.form_submit_button("Login")
        signup = form.form_submit_button("Signup")

        if login:
            if UserAuthentication.check_login(username):
                st.success("Logged in successfully!")
                time.sleep(1)
                st.session_state["logged_in"] = True
                st.rerun()   # rerun the app

        if signup:
            if UserAuthentication.register_user(username):
                st.success(f"Account created for {username}!")
                time.sleep(1)
                st.session_state["logged_in"] = True
                st.rerun()   # rerun the app

# create a class for database connection
class DBConnection: 
    def __init__(self):
        pass

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

    def select(query):
        connection = DBConnection.create_connection()
        mycursor = connection.cursor()

        if connection:
            try:
                mycursor.execute(query)
                df = pd.DataFrame(mycursor.fetchall())
                return df
            except Error as e:
                print("Error in executing the query:", e)
            finally:
                connection.close()
        return None
    
    def insert(query):
        connection = DBConnection.create_connection()
        mycursor = connection.cursor()
        
        if connection:
            try:
                mycursor.execute(query)
                connection.commit()
                print("Record inserted successfully into table")
            except Error as e:
                print("Error in executing the query:", e)
            finally:
                connection.close()
        return None
    
    # get the contest number from the database and return a list
    def contest_num_list():
        connection = DBConnection.create_connection()
        mycursor = connection.cursor()
        
        if connection:
            try:
                mycursor.execute("""SELECT contest_num FROM base Where image_url IS NOT NULL""")
                df = pd.DataFrame(mycursor.fetchall(), columns=['contest_num'])
                return df['contest_num'].tolist()
            except Error as e:
                print("Error in executing the query:", e)
            finally:
                connection.close()
        return None



# initialize the session state for login
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'user_id' not in st.session_state:
    st.session_state['user_id'] = None

# initialize the session state for function 1
if 'random_select' not in st.session_state:   # for random select, 0 for no, 1 for yes
    st.session_state.random_select = 0

# initialize the session state for function 2
if 'captions' not in st.session_state:
    st.session_state.captions = []
if 'descriptions' not in st.session_state:
    st.session_state.descriptions = []
if 'methods' not in st.session_state:
    st.session_state.methods = []
if 'num_cleared' not in st.session_state:   # for clear history, the number of cleared records
    st.session_state.num_cleared = 0
if 'draft_val' not in st.session_state:   # for scratch paper, the value of the scratch paper
    st.session_state.draft_val = ''

# extract the valid contest number from the database as a list
contest_num_list = DBConnection.contest_num_list()

# the stragety list for function 2
prompt_strategies = [
   'use more specific language',
   'make reference to all important elements of the image',
   'use langauge with more than one interpretation',
   'avoid making the joke too obvious',
   'put the punchline at the end',
   'introduce a tension that is resolved by the joke',
   'imagine it comes from the script of a Seinfeld episode',
   'make reference to unusual elemts of the image',
   'think of what the characters in the image are doing and why',
   'think of how the image differs from a more common situation and why',
   'think of the emotions the characters are feeling and why'
   ]



# if the user is not logged in, show the login page; otherwise, show the main page
if st.session_state['logged_in'] == False:
    UserAuthentication.user_account()
else:
    # set up the page layout
    col1, col2 = st.columns([1,2], gap="medium")

    with col1:
        option_function = st.selectbox('Choose a function', ('Inspiration', 'Get Help from GPT', 'Funniness prediction', 'topic model graph'))

        if option_function =='Get Help from GPT':
            with st.form("my_form"):
                GPT_API = st.text_input('Your GPT API:', key="API", type="password")
                model_selection = st.selectbox('Choose an AI', ('gpt-3.5-turbo', 'gpt-4'), key="model")
                Key_submit = st.form_submit_button("Submit")

            if Key_submit:
                # check if the API key is valid
                if is_key_valid(GPT_API):
                    st.success("API key is valid!")
                else:
                    st.error("API key is invalid!")
                    st.stop()
                     
    with col2:
        # function 1: get inspiration
        if option_function =='Inspiration':
            st.title('Get some inspiration from previous cartoons! :bulb:')
            # create a select box for contest number from 510 to 863 but not 525, 643, 646, 655 and a random option
            options = contest_num_list
            options.insert(0, 'Random')
            contest_num = st.selectbox('Choose a random contest number or a specific one', options)

            if st.button(':red[Give me some inspiration]'):
                st.session_state.random_select = 0
                
                # if contest number is random, give a random number from 510 to 863 but not 525, 643, 646, 655
                if contest_num == 'Random':
                    contest_num = random.choice(options[1:])
                    st.session_state.random_select = 1
                
                # get the image and caption from the database
                random_integers = [random.randint(0, 19) for _ in range(3)]
                inspiration_URL = DBConnection.select(f"""SELECT image_url FROM base Where contest_num={contest_num}""")
                inspiration_caption = DBConnection.select(f"""SELECT caption FROM result WHERE contest_num={contest_num}""")
                col2_1, col2_2 = st.columns([0.4, 0.6], gap="medium")
                with col2_1:
                    st.image(inspiration_URL.iloc[0, 0], width=360)
                with col2_2:
                    st.write("**Funny Caption 1:**")
                    st.write(inspiration_caption.iloc[random_integers[0], 0])
                    st.write("**Funny Caption 2:**")
                    st.write(inspiration_caption.iloc[random_integers[1], 0])
                    st.write("**Funny Caption 3:**")
                    st.write(inspiration_caption.iloc[random_integers[2], 0])

                # insert the record into the database
                DBConnection.insert(f"""INSERT INTO interface_records (random_select, contest_num, used_function, time, user_id) \
                                    VALUES ({st.session_state.random_select}, {contest_num}, 'Inspiration', '{datetime.now()}', {st.session_state.user_id})""")
        


        # function 2: get help from GPT
        if option_function =='Get Help from GPT':
            if not st.session_state.API:
                st.title(':red[Please enter the API]')
            else:
                # for the layout of the showed cartoon and a scratch paper
                col2_3, col2_4 = st.columns([3,4], gap="small")
                with col2_3:
                    # create a centered title for the cartoon
                    st.markdown(centered_large_bold_css, unsafe_allow_html=True)
                    st.markdown("<div class='centered-text-large-bold'>The Newest New York Cartoon</div>", unsafe_allow_html=True)
                    lastest_contest_num = max(contest_num_list)
                    st.image(f"https://nextml.github.io/caption-contest-data/cartoons/{lastest_contest_num}.jpg")
                with col2_4:
                    current_draft = st.text_area('Free Scratch Paper', height=350, value=st.session_state.draft_val)

                # create a chat box
                msgs = StreamlitChatMessageHistory(key="langchain_messages")
                memory = ConversationBufferMemory(chat_memory=msgs)
                template = """You are an AI chatbot having a conversation with a human. You are assisting me trying to think of funny captions for a cartoon.

                {history}
                Human: {human_input}
                AI: """
                prompt = PromptTemplate(input_variables=["history", "human_input"], template=template)
                llm_chain = LLMChain(llm=ChatOpenAI(openai_api_key=st.session_state.API, model=st.session_state.model), prompt=prompt, memory=memory)

                # create prompt templates
                prompt_initial = PromptTemplate(
                    input_variables=["description", "caption", "suggestion_method"],
                    template="Here is a description of the cartoon image: {description}. \
                        So far I have come up with the following caption: {caption}. \
                        Your job is to help me come up with better captions. \
                        One way of making a cartoon funnier is to {suggestion_method}. \
                        With this way, please directly give me some suggestions that can help me create a funnier caption. \
                        Respond in no more than three sentences.")
                prompt_for_descp_method_change = PromptTemplate(input_variables=["description", "suggestion_method"], 
                                                                template="Based on the new description: {description}. \
                                                                          And another way of making a caption funnier is to {suggestion_method}. \
                                                                          Now I would like some more advice.")
                prompt_for_cap_method_change = PromptTemplate(input_variables=["caption", "suggestion_method"], 
                                                              template="From your prior advice, I added the following caption: {caption}. \
                                                                        And another way of making a caption funnier is to {suggestion_method}. \
                                                                        Now I would like some more advice.")
                prompt_for_method_change = PromptTemplate(input_variables=["suggestion_method"], 
                                                          template="Based on the new method for improve funniness: {suggestion_method}, please give me more suggestions.")
                prompt_complete = PromptTemplate(
                    input_variables=["description", "caption", "suggestion_method"],
                    template="From your prior advice, I added the updated description: {description}. \
                        I also added a new come-up caption: {caption} and another way to make a caption funnier: {suggestion_method}. \
                        With these, please directly give me some suggestions that can help me create a funnier caption. \
                        Respond in no more than three sentences and avoid repeating any previous advice.")
                
                # create a form for each button
                with st.form(key='my_form2'):
                    # create a text input for the description
                    descp = st.text_area('Please describe the content of the cartoon in as much detail as possible:')
                    # create caption text input and record to scratch button
                    col2_5, col2_6 = st.columns([5,1])   # layout
                    with col2_5:
                        cap = st.text_input('Write your caption:')
                    with col2_6:
                        st.markdown(bottom_button_css, unsafe_allow_html=True)
                        reocrd_to_draft_button = st.form_submit_button(label='Record to draft')   # button for recording the caption to the scratch paper
                    # create help button and reset button
                    col2_7, col2_8 = st.columns([1,5])   # layout
                    with col2_7:
                        help_button = st.form_submit_button(label='Ask for assistance')   # button for asking for assistance
                    with col2_8:
                        reset_button = st.form_submit_button(label='Reset chat')   # button for resetting the chat
                
                # run for recording the caption to the scratch paper
                if reocrd_to_draft_button:
                    st.session_state.draft_val = st.session_state.draft_val + cap + '\n'
                    st.rerun()

                # run for each button pressing
                if help_button:
                    # randomly choose a suggestion method
                    if len(st.session_state.methods) == 0:   # if it is the first time to ask for help
                        option_help = random.choice(prompt_strategies)
                    else:
                        # avoid repeating the previous suggestion method
                        option_help = random.choice(prompt_strategies)
                        while option_help in st.session_state.methods:
                            option_help = random.choice(prompt_strategies)

                    # check if any input is empty
                    if descp == '':
                        st.write('Please enter the description!')
                    elif cap == '':
                        st.write('Please enter the caption!')
                    else:
                        # add the caption, description to the captions, descriptions history
                        st.session_state.descriptions.append(descp)
                        st.session_state.captions.append(cap)
                        st.session_state.methods.append(option_help)

                        # run the prompts
                        if len(msgs.messages) == 0:   # running the prompt for the first time
                            prompt = prompt_initial.format(description=descp, caption=cap, suggestion_method=option_help)  
                            response = llm_chain.run(prompt)
                            st.chat_message("ai").write(response)
                            change_type = 0
                        else:
                            # if the description and suggestion method are changed
                            if st.session_state.descriptions[-2] != descp and st.session_state.captions[-2] == cap:  
                                prompt = prompt_for_descp_method_change.format(description=descp, suggestion_method=option_help)
                                response = llm_chain.run(prompt)
                                st.chat_message("ai").write(response)
                                change_type = 1
                            # if the caption and suggestion method are changed
                            elif st.session_state.captions[-2] != cap and st.session_state.descriptions[-2] == descp:  
                                prompt = prompt_for_cap_method_change.format(caption=cap, suggestion_method=option_help)
                                response = llm_chain.run(prompt)
                                st.chat_message("ai").write(response)
                                change_type = 2
                            # if only the suggestion method is changed    
                            elif st.session_state.methods[-2] != option_help and st.session_state.descriptions[-2] == descp and st.session_state.captions[-2] == cap:  
                                prompt = prompt_for_method_change.format(suggestion_method=option_help)
                                response = llm_chain.run(prompt)
                                st.chat_message("ai").write(response)
                                change_type = 3
                            # if two or more items are changed
                            else:
                                prompt = prompt_complete.format(description=descp, caption=cap, suggestion_method=option_help)  
                                response = llm_chain.run(prompt)
                                st.chat_message("ai").write(response)
                                change_type = 4

                    # insert the record into the database (response will be added after solving the insert error)
                    DBConnection.insert(f"""INSERT INTO interface_records (description, caption, method, used_function, change_type, user_id, contest_num, model, time) \
                                        VALUES ('{descp}', '{cap}', '{option_help}', 'Get Help from GPT', {change_type}, {st.session_state.user_id}, {lastest_contest_num}, '{st.session_state.model}', '{datetime.now()}')""")
                
                # reset the chat
                if reset_button:
                    # clean history
                    st.session_state.descriptions = []
                    st.session_state.captions = []
                    st.session_state.methods = []
                    
                    # clean chat
                    del st.session_state.langchain_messages
                    msgs = StreamlitChatMessageHistory(key="langchain_messages")

                # history showing parts
                with col1:
                    with st.expander("View your records:"):
                        for i in range(len(st.session_state.captions) - st.session_state.num_cleared):
                            rid = i+1
                            st.write(f"**Record {rid}:** ")
                            st.write(f"Description: {st.session_state.descriptions[i+st.session_state.num_cleared]}")
                            st.write(f"Caption: {st.session_state.captions[i+st.session_state.num_cleared]}")
                            st.chat_message('ai').write(msgs.messages[(i+st.session_state.num_cleared)*2+1].content)
                        # clear history but not the chat
                        if st.button("Clear history"):
                            st.session_state.num_cleared = len(st.session_state.captions)
                            st.rerun()   # rerun the app
                            

                

        # function 3: funniness prediction
        if option_function =='Funniness prediction':
            st.title('Wait for further development!')



        # function 4: topic model graph
        if option_function =='topic model graph':
            st.title('Wait for further development!')

        
        
        # logout button
        if st.button("Logout"):
            UserAuthentication.logout_user()
            st.info("You have been logged out.")
            time.sleep(1)
            st.rerun()   # rerun the app
            del st.session_state.username
