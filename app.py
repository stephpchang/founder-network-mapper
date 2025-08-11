import streamlit as st
import pandas as pd

st.set_page_config(page_title="Founder Network Mapper")
st.title("Founder Network Mapper")

st.write("Maps relationships, expertise, and shared challenges across a portfolio to uncover opportunities for founder collaboration and support.")

# Sample data
data = {
    "Name": ["Jane Doe", "John Smith", "Alicia Lee"],
    "Company": ["FinTechCo", "HealthAI", "RetailX"],
    "Expertise": ["Payments integration", "Regulatory compliance", "Omnichannel strategy"],
    "Challenges": ["Scaling team", "Clinical trials", "International expansion"]
}

df = pd.DataFrame(data)

need = st.text_input("Describe a founder need or expertise area")

if st.button("Find Matches"):
    if need.strip() == "":
        st.warning("Please enter a need or expertise area.")
    else:
        matches = df[df.apply(lambda row: need.lower() in row.astype(str).str.lower().to_string(), axis=1)]
        if matches.empty:
            st.info("No matches found.")
        else:
            st.success(f"Matches for '{need}':")
            st.dataframe(matches)
