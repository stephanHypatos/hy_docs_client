import streamlit as st
import requests
import pandas as pd
from requests.auth import HTTPBasicAuth
from io import BytesIO

base_url = "https://api.cloud.hypatos.ai/v1" 
# Initialize session state for JIRA API credentials if not already done
if 'username' not in st.session_state:
    st.session_state['username'] = ''
if 'password' not in st.session_state:
    st.session_state['password'] = ''
if 'project_id' not in st.session_state:
    st.session_state['project_id'] = ''

# Function to get document IDs
def get_document_ids(username, password, base_url, project_id, states):
    documents_endpoint = f'{base_url}/projects/{project_id}/documents'
    params = {'state': states}
    response = requests.get(documents_endpoint, params=params, auth=HTTPBasicAuth(username, password))
    response.raise_for_status()
    return [doc['id'] for doc in response.json()['data']]

# Recursive function to extract 'value' keys and flatten nested entities
def extract_values(data, parent_key=''):
    items = {}
    for key, value in data.items():
        new_key = f'{parent_key}{key}_' if parent_key else key
        
        if isinstance(value, dict):
            if 'value' in value:
                items[new_key + 'value'] = value['value']
                
            else:
                items.update(extract_values(value, new_key))
        elif isinstance(value, list):
            for i, item in enumerate(value):
                items.update(extract_values(item, f'{new_key}{i}_'))
        else:
            items[new_key] = value
    return items

# Function to get document details by ID
def get_document_by_id(username, password, base_url, project_id, doc_id, main_keys, entity_keys):
    get_document_by_id_endpoint = f'{base_url}/projects/{project_id}/documents/{doc_id}'
    response = requests.get(get_document_by_id_endpoint, auth=HTTPBasicAuth(username, password))
    response.raise_for_status()
    document = response.json()

    # Filter main keys
    filtered_document = {key: document.get(key) for key in main_keys}
    
    # Filter and flatten entity keys
    if 'entities' in document:
        filtered_entities = {key: document['entities'].get(key) for key in entity_keys}
        flattened_entities = extract_values(filtered_entities)
        filtered_document.update(flattened_entities)

    return filtered_document


# Streamlit app
st.title("Get Documents Tool")

# User inputs
st.session_state['username']= st.text_input("Username")
st.session_state['password']= st.text_input("Password", type="password")
option = st.selectbox(
    "Select the Project",
    ("2.1.Zeit_Rechnungen", "1.1.Handelsblatt_Rechnungen"))
if option.startswith("2.1.Zeit"): 
    st.session_state['project_id'] = '62fac5f1b2ddfb95f3b076e4'
else: 
    st.session_state['project_id'] = '62fac51d68a5582b24f3ef31'


states = st.multiselect("Select one or n Document State(s)", ["reviewRequired", "inCompletion", "extracted"],["reviewRequired", "inCompletion", "extracted"])

# Input for main keys and entity keys
main_keys_input =  st.multiselect("Select metadata", ["state", "projectId","id", "fileName", "uploadedAt"],["id", "fileName", "state"])
entity_keys_input = st.multiselect("Select datapoints", ["deliveredAt", "issuedAt","type", "totals", "number","sender","vendor", "recipientCompany","recipient","ggId"],["type","ggId","number","issuedAt", "totals", "sender","recipient"])

if st.button("Fetch Documents"):
    if st.session_state['username'] and st.session_state['password'] and base_url and st.session_state['project_id'] and states:
        try:
            with st.spinner("Fetching data..."):
                filename_export = st.session_state['project_id']
                document_ids = get_document_ids(st.session_state['username'], st.session_state['password'], base_url, st.session_state['project_id'], states)
                flattened_docs = []

                for doc_id in document_ids:
                    document = get_document_by_id(st.session_state['username'], st.session_state['password'], base_url, st.session_state['project_id'], doc_id,main_keys_input, entity_keys_input)
                    flattened_docs.append(document)

                df = pd.DataFrame(flattened_docs)

                # Convert DataFrame to Excel
                output = BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df.to_excel(writer, index=False, sheet_name='Documents')
                output.seek(0)

                st.success("Data fetched successfully!")
                st.download_button(
                    label="Download Excel",
                    data=output,
                    file_name=f'{filename_export}_documents.xlsx',
                    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                )
        except Exception as e:
            st.error(f"Error fetching data: {e}")
    else:
        st.warning("Please provide all the required inputs.")
